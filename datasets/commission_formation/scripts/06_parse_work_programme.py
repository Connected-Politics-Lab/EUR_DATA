"""
06_parse_work_programme.py
Extract legislative initiatives from the Commission Work Programme 2025 PDF.

Uses pdfplumber table extraction on annex pages. Falls back to text-based
regex parsing if tables don't extract cleanly.

The CWP 2025 annexes document (COM(2025) 45 final, ANNEXES 1 to 5) contains:
  I   - New initiatives (numbered rows may hold several initiatives)
  II  - Annual plan on evaluations and fitness checks
  III - Pending proposals (NOT extracted: out of scope for this dataset;
        pending files are tracked in the agenda_implementation term corpus)
  IV  - Withdrawals (of pending proposals)
  V   - Envisaged repeals

Annex headings can fall mid-page (e.g. the last Annex II items share a page
with the Annex III heading), so tables are assigned to annexes by the vertical
position of the nearest preceding heading, not per page.

Output: work_programme_items.csv + .xlsx
"""

import re
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, fetch_url, download_pdf, save_both

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


CWP_FILENAME = "COM_2025_45_1_EN.pdf"
CWP_ANNEXES_FILENAME = "COM_2025_45_1_annexes_EN.pdf"

# Annex heading pattern; longest roman numerals first so "III" wins over "II".
ANNEX_HEADING_RE = re.compile(r"Annex\s+(III|II|IV|V|I)\s*:", re.IGNORECASE)

# Annexes whose items ship in the dataset. Official Annex III (pending
# proposals) is deliberately excluded: those are files carried over from
# earlier terms, tracked separately in agenda_implementation.
EXTRACTED_ANNEXES = ["I", "II", "IV", "V"]

ANNEX_TITLES = {
    "I": "New initiatives",
    "II": "Annual plan on evaluations and fitness checks",
    "III": "Pending proposals (not extracted)",
    "IV": "Withdrawals",
    "V": "Envisaged repeals",
}

# Column semantics of the sparse-grid annex tables, in official header order
# (after the "No." column): Annex II is "Full Title | Indicative finalisation
# time"; Annex IV is "References | Title | Reasons for withdrawal"; Annex V is
# "Policy area | Title | Reasons for repeal".
ANNEX_COLUMN_SEMANTICS = {
    "II": ["title", "indicative_timing"],
    "IV": ["references", "title", "reasons"],
    "V": ["policy_area", "title", "reasons"],
}

# Legal instrument named in a withdrawal/repeal title.
INSTRUMENT_RE = re.compile(
    r"(Regulation|Directive|Decision|Recommendation|Communication)",
    re.IGNORECASE)


def download_cwp(logger) -> Path:
    """Download the CWP 2025 PDFs (main + annexes). Returns annexes path (has tables)."""
    import time

    # Download main document
    main_path = config.RAW_WORK_PROGRAMME / CWP_FILENAME
    if not (main_path.exists() and main_path.stat().st_size > 10000):
        logger.info("Downloading CWP 2025 main PDF...")
        download_pdf(config.CWP_2025_PDF_URL, main_path)
        time.sleep(3)

    # Download annexes (this contains the actual tables)
    annexes_path = config.RAW_WORK_PROGRAMME / CWP_ANNEXES_FILENAME
    if not (annexes_path.exists() and annexes_path.stat().st_size > 10000):
        logger.info("Downloading CWP 2025 annexes PDF...")
        annexes_url = getattr(config, "CWP_2025_ANNEXES_PDF_URL", "")
        if annexes_url:
            download_pdf(annexes_url, annexes_path)

    # Prefer annexes (has the structured tables), fall back to main
    if annexes_path.exists() and annexes_path.stat().st_size > 10000:
        logger.info("Using annexes PDF for table extraction.")
        return annexes_path
    elif main_path.exists() and main_path.stat().st_size > 10000:
        logger.info("Annexes not available, using main PDF.")
        return main_path
    else:
        raise RuntimeError("Failed to download CWP 2025 PDF")


def identify_annex_tables(pdf_path: Path, logger):
    """
    Assign every table in the PDF to an annex by the vertical position of the
    nearest preceding "Annex N:" heading. A heading mid-page (e.g. Annex III
    on the page carrying the last Annex II rows) therefore splits that page's
    tables correctly instead of relabelling the whole page.

    Returns (annex_tables, annex_pages):
      annex_tables: dict annex -> list of tables, each a list of rows
                    (each row a list of raw cell values)
      annex_pages:  dict annex -> sorted list of page indices holding those
                    tables (used by the text fallback)
    """
    annex_tables = {k: [] for k in ANNEX_TITLES}
    annex_pages = {k: set() for k in ANNEX_TITLES}
    current_annex = None

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            # Locate annex headings on this page with their vertical position.
            headings = []  # (top, annex_numeral)
            for hit in page.search(ANNEX_HEADING_RE.pattern) or []:
                m = ANNEX_HEADING_RE.search(hit.get("text", ""))
                if m:
                    headings.append((hit["top"], m.group(1).upper()))
            headings.sort()

            for table in page.find_tables():
                table_top = table.bbox[1]
                annex = current_annex
                for top, numeral in headings:
                    if top < table_top:
                        annex = numeral
                if annex:
                    annex_tables[annex].append(table.extract())
                    annex_pages[annex].add(i)

            if headings:
                current_annex = headings[-1][1]

    for annex in ANNEX_TITLES:
        if annex_tables[annex]:
            pages = sorted(annex_pages[annex])
            logger.info(
                f"Annex {annex} ({ANNEX_TITLES[annex]}): "
                f"{len(annex_tables[annex])} tables on pages "
                f"{pages[0]+1}-{pages[-1]+1}")

    return annex_tables, {k: sorted(v) for k, v in annex_pages.items()}


def parse_annex_sparse(tables: List[List], annex: str, logger) -> List[Dict]:
    """
    Parse the sparse-grid annex tables (II, IV, V): pdfplumber returns them as
    wide grids with most cells empty and wrapped text spread over several rows,
    so rows are grouped by their "N." cell and cell text re-joined column-wise
    (the same technique as parse_annex_i). Column meanings follow the official
    table headers (ANNEX_COLUMN_SEMANTICS). Full-width section banners land in
    columns that are empty on the numbered row and are dropped.
    """
    def _cell(c):
        return (c or "").replace("\n", " ").strip()

    semantics = ANNEX_COLUMN_SEMANTICS[annex]
    groups = []
    current = None
    for table in tables:
        for row in table:
            cells = [_cell(c) for c in row]
            row_join = " ".join(c for c in cells if c).lower()
            # Skip column-header rows (repeated on continuation pages)
            if "no." in row_join and ("title" in row_join or "policy" in row_join):
                continue
            num = next((c for c in cells if re.fullmatch(r"\d{1,3}\.", c)), "")
            if num:
                if current:
                    groups.append(current)
                current = {"num": num.rstrip("."), "cols": {}, "num_row_cols": set()}
            if current:
                for ci, c in enumerate(cells):
                    if not c or c == num:
                        continue
                    current["cols"].setdefault(ci, []).append(c)
                    if num:
                        current["num_row_cols"].add(ci)
    if current:
        groups.append(current)

    items = []
    for g in groups:
        cols = []
        dropped = []
        for ci in sorted(g["cols"]):
            text = re.sub(r"\s+", " ", " ".join(g["cols"][ci])).strip()
            if ci in g["num_row_cols"]:
                cols.append(text)
            else:
                dropped.append(text)
        if dropped:
            logger.debug(
                f"Annex {annex} row {g['num']}: dropped section banner text "
                f"{' / '.join(d[:60] for d in dropped)!r}")

        if len(cols) == len(semantics):
            fields = dict(zip(semantics, cols))
        else:
            logger.warning(
                f"Annex {annex} row {g['num']}: expected {len(semantics)} "
                f"columns, found {len(cols)}; joining into title")
            fields = {"title": " ".join(cols)}

        title = fields.get("title", "")
        desc_bits = []
        if fields.get("references"):
            desc_bits.append(f"References: {fields['references']}")
        if fields.get("reasons"):
            label = ("Reasons for repeal" if annex == "V"
                     else "Reasons for withdrawal")
            desc_bits.append(f"{label}: {fields['reasons']}")

        # Normalise the legal instrument named in a withdrawal/repeal title so
        # downstream counts (REGULATION vs Regulation) are consistent.
        type_of_act = ""
        if annex in ("IV", "V"):
            m = INSTRUMENT_RE.search(title)
            if m:
                type_of_act = m.group(1).upper()

        items.append({
            "annex": annex,
            "item_number": g["num"],
            "title": title,
            "description": " ".join(desc_bits),
            "policy_area": fields.get("policy_area", ""),
            "type_of_act": type_of_act,
            "indicative_timing": fields.get("indicative_timing", ""),
        })

    logger.info(f"Annex {annex}: parsed {len(items)} items from sparse tables")
    return items


def extract_text_fallback(pdf_path: Path, page_indices: List[int],
                          annex: str, logger) -> List[Dict]:
    """
    Fallback: extract items from text using regex patterns when tables fail.
    """
    items = []
    item_counter = 0

    with pdfplumber.open(pdf_path) as pdf:
        full_text = ""
        for page_idx in page_indices:
            page = pdf.pages[page_idx]
            text = page.extract_text() or ""
            full_text += text + "\n"

    # Try to find numbered items
    # Pattern: number followed by title text
    numbered_pattern = re.compile(
        r"(?:^|\n)\s*(\d{1,3})\.\s+(.+?)(?=\n\s*\d{1,3}\.\s|\Z)",
        re.DOTALL
    )

    for match in numbered_pattern.finditer(full_text):
        item_counter += 1
        num = match.group(1)
        text = match.group(2).strip()

        # Split into title and rest
        lines = text.split("\n")
        title = lines[0].strip() if lines else text
        description = " ".join(line.strip() for line in lines[1:]).strip()

        # Try to extract type of act
        type_of_act = ""
        type_match = re.search(
            r"(Regulation|Directive|Decision|Communication|Recommendation|"
            r"Action Plan|Strategy|Legislative|Non-legislative)",
            text, re.IGNORECASE
        )
        if type_match:
            type_of_act = type_match.group(1).upper()

        # Try to extract timing
        timing = ""
        timing_match = re.search(
            r"(Q[1-4]\s*20\d{2}|20\d{2}|first|second|third|fourth quarter)",
            text, re.IGNORECASE
        )
        if timing_match:
            timing = timing_match.group(1)

        items.append({
            "annex": annex,
            "item_number": num,
            "title": title,
            "description": description,
            "policy_area": "",
            "type_of_act": type_of_act,
            "indicative_timing": timing,
        })

    logger.info(f"Annex {annex}: extracted {len(items)} items via text fallback")
    return items


# Annex I lists individual initiatives in a "No. | Policy objective | Initiatives"
# table; each initiative carries its (non-)legislative nature and, usually, an
# indicative quarter in brackets ("tbd" for row 45). A numbered row may hold
# several initiatives, the policy objective can wrap across table rows, and an
# initiative's bracket can itself split across rows (row 6 ends "... Q4" with
# "2025)" on the next line), so we group rows by number and join cell text
# column-wise within each group before extracting initiatives.
ANNEX_I_INITIATIVE_OPEN_RE = re.compile(
    r"\((non-legislative or legislative|non-legislative|legislative)\b"
)
ANNEX_I_INITIATIVE_RE = re.compile(
    r"\((non-legislative or legislative|non-legislative|legislative)\b"
    r"[\s\S]*?(Q[1-4](?:\s*[/-]\s*Q[1-4])?\s*20\d{2}|20\d{2}|tbd)\s*\)",
    re.IGNORECASE
)

ANNEX_I_HEADER_CELLS = {"No.", "Policy objective", "Initiatives"}


def parse_annex_i(tables: List[List], logger) -> List[Dict]:
    """Parse Annex I into one row per initiative (name, objective, type, timing)."""
    def _cell(c):
        return (c or "").replace("\n", " ").strip()

    # Group rows by the numbered cell; keep every non-empty cell with its
    # column index so wrapped text can be re-joined column-wise. Columns
    # populated on the numbered row itself are recorded so that full-width
    # section banners appearing in *other* columns of continuation rows
    # (the CWP chapter headings) can be told apart from the group's own
    # policy objective.
    groups = []
    current = None
    for table in tables:
        for row in table:
            cells = [_cell(c) for c in row]
            num = next((c for c in cells if re.fullmatch(r"\d{1,2}\.", c)), "")
            if num:
                if current:
                    groups.append(current)
                current = {"num": num.rstrip("."), "cols": {}, "num_row_cols": set()}
            if current:
                for ci, c in enumerate(cells):
                    if not c or c == num or c in ANNEX_I_HEADER_CELLS:
                        continue
                    current["cols"].setdefault(ci, []).append(c)
                    if num:
                        current["num_row_cols"].add(ci)
    if current:
        groups.append(current)

    type_norm = {"legislative": "Legislative", "non-legislative": "Non-legislative",
                 "non-legislative or legislative": "Non-legislative or legislative"}
    items = []
    for g in groups:
        obj_parts = []
        init_texts = []
        dropped = []
        for ci in sorted(g["cols"]):
            text = re.sub(r"\s+", " ", " ".join(g["cols"][ci])).strip()
            if ANNEX_I_INITIATIVE_OPEN_RE.search(text):
                init_texts.append(text)
            elif ci in g["num_row_cols"]:
                obj_parts.append(text)
            else:
                # Non-initiative text in a column empty on the numbered row:
                # a full-width section banner (CWP chapter heading), not this
                # row's policy objective.
                dropped.append(text)
        if not obj_parts and dropped:
            obj_parts, dropped = dropped, []
        if dropped:
            logger.debug(
                f"Annex I row {g['num']}: dropped section banner text "
                f"{' / '.join(d[:60] for d in dropped)!r}")
        objective = " ".join(obj_parts).strip()

        for text in init_texts:
            prev_end = 0
            for m in ANNEX_I_INITIATIVE_RE.finditer(text):
                # A row may list several initiatives joined by "and"/"or";
                # strip the leading conjunction from continuation titles.
                title = text[prev_end:m.start()].strip(" .")
                title = re.sub(r"^(?:and|or)\s+", "", title)
                items.append({
                    "annex": "I",
                    "item_number": g["num"],
                    "title": title,
                    "description": "",
                    "policy_area": objective,
                    "type_of_act": type_norm.get(m.group(1).lower(), m.group(1)),
                    "indicative_timing": re.sub(r"\s+", " ", m.group(2)).strip(),
                })
                prev_end = m.end()
            leftover = text[prev_end:].strip(" .")
            if leftover:
                logger.warning(
                    f"Annex I row {g['num']}: unparsed initiative text left over: "
                    f"{leftover[:80]!r}")

    logger.info(f"Annex I: parsed {len(items)} initiatives from {len(groups)} numbered rows")
    return items


def parse_work_programme() -> pd.DataFrame:
    """Main function: download, extract, and parse CWP 2025."""
    logger = setup_logging("06_work_programme")
    ensure_dirs()

    if pdfplumber is None:
        logger.error("pdfplumber not installed. Run: pip install pdfplumber")
        return pd.DataFrame()

    # Download PDF
    pdf_path = download_cwp(logger)

    # Assign every table to its annex by heading position
    annex_tables, annex_pages = identify_annex_tables(pdf_path, logger)

    if annex_tables.get("III"):
        skipped = sum(
            1 for table in annex_tables["III"] for row in table
            if row and re.fullmatch(r"\d{1,3}\.?", (row[0] or "").strip())
        )
        logger.info(
            f"Annex III (pending proposals): out of scope, skipping "
            f"{skipped}+ tabled proposals (tracked in agenda_implementation).")

    all_items = []
    item_id_counter = 0

    for annex_num in EXTRACTED_ANNEXES:
        tables = annex_tables.get(annex_num, [])
        if not tables:
            logger.warning(f"No tables identified for Annex {annex_num}")
            continue

        # Annex I has a bespoke initiative-level layout; parse it directly.
        if annex_num == "I":
            items = parse_annex_i(tables, logger)
            for item in items:
                item_id_counter += 1
                item["item_id"] = f"WP{item_id_counter:03d}"
            all_items.extend(items)
            continue

        # Try table extraction first
        items = parse_annex_sparse(tables, annex_num, logger)

        # If table extraction yielded too few items, try text fallback
        if len(items) < 3:
            logger.info(f"Table extraction for Annex {annex_num} yielded only "
                        f"{len(items)} items. Trying text fallback...")
            text_items = extract_text_fallback(
                pdf_path, annex_pages.get(annex_num, []), annex_num, logger)
            if len(text_items) > len(items):
                items = text_items

        # Assign item IDs
        for item in items:
            item_id_counter += 1
            item["item_id"] = f"WP{item_id_counter:03d}"

        all_items.extend(items)

    if not all_items:
        logger.warning("No work programme items extracted!")
        return pd.DataFrame(columns=[
            "item_id", "annex", "item_number", "title", "description",
            "policy_area", "type_of_act", "indicative_timing",
        ])

    df = pd.DataFrame(all_items)

    # Column ordering
    columns = [
        "item_id", "annex", "item_number", "title", "description",
        "policy_area", "type_of_act", "indicative_timing",
    ]
    columns = [c for c in columns if c in df.columns]
    df = df[columns]

    logger.info(f"Work programme: {len(df)} items total")
    logger.info(f"By annex: {df['annex'].value_counts().to_dict()}")

    return df


def main():
    df = parse_work_programme()
    save_both(df, "work_programme_items")
    print(f"work_programme_items: {len(df)} rows saved.")
    return df


if __name__ == "__main__":
    main()
