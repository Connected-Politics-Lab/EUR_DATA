"""
06_parse_work_programme.py
Extract legislative initiatives from the Commission Work Programme 2025 PDF.

Uses pdfplumber table extraction on annex pages. Falls back to text-based
regex parsing if tables don't extract cleanly.

The CWP typically has 4 annexes:
  I   - New initiatives
  II  - REFIT initiatives
  III - Withdrawals
  IV  - Repeals

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

# Annex identification patterns
ANNEX_PATTERNS = {
    "I": re.compile(r"ANNEX\s+I\b(?!\s*[IV])", re.IGNORECASE),
    "II": re.compile(r"ANNEX\s+II\b", re.IGNORECASE),
    "III": re.compile(r"ANNEX\s+III\b", re.IGNORECASE),
    "IV": re.compile(r"ANNEX\s+IV\b", re.IGNORECASE),
}

ANNEX_TITLES = {
    "I": "New initiatives",
    "II": "REFIT initiatives",
    "III": "Pending proposals to be withdrawn",
    "IV": "Pending proposals to be repealed",
}

# Indicative timing strings look like "Q2 2025", "Q1/Q2 2025", "Q3 / Q4 2025".
# In some annex tables (II/III) this value lands in the column that otherwise
# carries the legal instrument, so we detect it and route it to the right field.
TIMING_RE = re.compile(r"^\s*Q[1-4]\b", re.IGNORECASE)


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


def identify_annex_pages(pdf_path: Path, logger) -> Dict[str, List[int]]:
    """
    Scan the PDF to identify which pages belong to which annex.
    Returns dict of annex_number -> list of page indices (0-based).
    """
    annex_pages = {k: [] for k in ANNEX_PATTERNS}
    current_annex = None

    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            first_lines = text[:500]

            # Check if this page starts a new annex
            for annex_num, pattern in ANNEX_PATTERNS.items():
                if pattern.search(first_lines):
                    current_annex = annex_num
                    logger.debug(f"Page {i+1}: Start of Annex {annex_num}")
                    break

            if current_annex:
                annex_pages[current_annex].append(i)

    for annex, pages in annex_pages.items():
        if pages:
            logger.info(f"Annex {annex}: pages {pages[0]+1}-{pages[-1]+1} "
                        f"({len(pages)} pages)")

    return annex_pages


def extract_tables_from_pages(pdf_path: Path, page_indices: List[int],
                               logger) -> List[List]:
    """
    Extract tables from specified pages using pdfplumber.
    Returns list of rows (each row is a list of cell values).
    """
    all_rows = []

    with pdfplumber.open(pdf_path) as pdf:
        for page_idx in page_indices:
            page = pdf.pages[page_idx]
            tables = page.extract_tables()

            if tables:
                for table in tables:
                    for row in table:
                        if row and any(cell and cell.strip() for cell in row if cell):
                            # Clean cells
                            cleaned = [
                                (cell.strip().replace("\n", " ") if cell else "")
                                for cell in row
                            ]
                            all_rows.append(cleaned)

    logger.debug(f"Extracted {len(all_rows)} table rows from {len(page_indices)} pages")
    return all_rows


def parse_table_rows(rows: List[List], annex: str, logger) -> List[Dict]:
    """
    Parse table rows into structured items.
    CWP tables typically have columns: No., Title, Type/Description, Timing.
    """
    items = []
    item_counter = 0

    # Try to detect header row
    header_idx = -1
    for i, row in enumerate(rows):
        row_text = " ".join(row).lower()
        if any(kw in row_text for kw in ["title", "initiative", "no.", "objective"]):
            header_idx = i
            break

    data_rows = rows[header_idx + 1:] if header_idx >= 0 else rows

    for row in data_rows:
        # Skip empty or header-like rows
        if not row or len(row) < 2:
            continue

        row_text = " ".join(row).strip()
        if len(row_text) < 10:
            continue

        # Skip section headers within tables
        if row_text == row_text.upper() and len(row_text) < 80:
            continue

        item_counter += 1

        # Map columns based on count
        item_number = ""
        title = ""
        description = ""
        policy_area = ""
        type_of_act = ""
        timing = ""

        if len(row) >= 5:
            item_number = row[0].strip()
            policy_area = row[1].strip() if row[1] else ""
            title = row[2].strip() if row[2] else ""
            type_of_act = row[3].strip() if row[3] else ""
            timing = row[4].strip() if row[4] else ""
        elif len(row) >= 4:
            item_number = row[0].strip()
            title = row[1].strip() if row[1] else ""
            type_of_act = row[2].strip() if row[2] else ""
            timing = row[3].strip() if row[3] else ""
        elif len(row) >= 3:
            item_number = row[0].strip()
            title = row[1].strip() if row[1] else ""
            description = row[2].strip() if row[2] else ""
        elif len(row) >= 2:
            title = row[0].strip() if row[0] else ""
            description = row[1].strip() if row[1] else ""

        # Try to extract item number if embedded in title
        if not item_number and title:
            num_match = re.match(r"^(\d+)\.\s*(.+)", title)
            if num_match:
                item_number = num_match.group(1)
                title = num_match.group(2)

        # Some annex tables (II/III) place the indicative timing in the column
        # that otherwise carries the legal instrument. Route any timing string
        # (e.g. "Q2 2025") to indicative_timing and keep type_of_act for the
        # legal instrument only.
        if type_of_act and TIMING_RE.match(type_of_act):
            if not timing:
                timing = type_of_act
            type_of_act = ""

        # The Annex II table has only three populated cells (No. / Full Title /
        # Indicative finalisation time), which the five-column mapping reads as
        # item_number / policy_area / title. If the mapped title is itself a
        # timing string, the real title is sitting in policy_area: shift it
        # back and route the timing to indicative_timing.
        if TIMING_RE.match(title) and policy_area and not TIMING_RE.match(policy_area):
            if not timing:
                timing = title.strip()
            title = policy_area
            policy_area = ""

        # Normalise the legal instrument to a single case so downstream counts
        # (e.g. REGULATION vs Regulation) are consistent.
        if type_of_act:
            type_of_act = type_of_act.upper()

        if title:
            items.append({
                "annex": annex,
                "item_number": item_number,
                "title": title,
                "description": description,
                "policy_area": policy_area,
                "type_of_act": type_of_act,
                "indicative_timing": timing,
            })

    logger.info(f"Annex {annex}: parsed {len(items)} items from tables")
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
# table; each initiative carries its (non-)legislative nature and indicative
# quarter in brackets. A numbered row may hold several initiatives, and the
# policy objective can wrap across table rows, so we group by number.
ANNEX_I_INITIATIVE_RE = re.compile(
    r"\((non-legislative or legislative|non-legislative|legislative)\b"
    r"[\s\S]*?(Q[1-4](?:\s*/\s*Q[1-4])?\s*20\d{2}|20\d{2})\s*\)"
)


def parse_annex_i(pdf_path: Path, page_indices: List[int], logger) -> List[Dict]:
    """Parse Annex I into one row per initiative (name, objective, type, timing)."""
    def _cell(c):
        return (c or "").replace("\n", " ").strip()

    groups = []
    current = None
    with pdfplumber.open(pdf_path) as pdf:
        for page_idx in page_indices:
            for table in pdf.pages[page_idx].extract_tables() or []:
                for row in table:
                    cells = [_cell(c) for c in row]
                    num = next((c for c in cells if re.fullmatch(r"\d{1,2}\.", c)), "")
                    init = next((c for c in cells if ANNEX_I_INITIATIVE_RE.search(c)), "")
                    obj = next((c for c in cells[1:] if c
                                and not ANNEX_I_INITIATIVE_RE.search(c)
                                and not re.fullmatch(r"\d{1,2}\.", c)
                                and c not in ("Policy objective", "Initiatives", "No.")), "")
                    if num:
                        if current:
                            groups.append(current)
                        current = {"num": num.rstrip("."),
                                   "obj": [obj] if obj else [],
                                   "inits": [init] if init else []}
                    elif current:
                        if obj:
                            current["obj"].append(obj)
                        if init:
                            current["inits"].append(init)
        if current:
            groups.append(current)

    type_norm = {"legislative": "Legislative", "non-legislative": "Non-legislative",
                 "non-legislative or legislative": "Non-legislative or legislative"}
    items = []
    for g in groups:
        objective = " ".join(g["obj"]).strip()
        for init in g["inits"]:
            m = ANNEX_I_INITIATIVE_RE.search(init)
            items.append({
                "annex": "I",
                "item_number": g["num"],
                "title": init[:m.start()].strip(" ."),
                "description": "",
                "policy_area": objective,
                "type_of_act": type_norm.get(m.group(1), m.group(1)),
                "indicative_timing": re.sub(r"\s+", " ", m.group(2)).strip(),
            })
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

    # Identify annex pages
    annex_pages = identify_annex_pages(pdf_path, logger)

    all_items = []
    item_id_counter = 0

    for annex_num in ["I", "II", "III", "IV"]:
        pages = annex_pages.get(annex_num, [])
        if not pages:
            logger.warning(f"No pages identified for Annex {annex_num}")
            continue

        # Annex I has a bespoke initiative-level layout; parse it directly.
        if annex_num == "I":
            items = parse_annex_i(pdf_path, pages, logger)
            for item in items:
                item_id_counter += 1
                item["item_id"] = f"WP{item_id_counter:03d}"
            all_items.extend(items)
            continue

        # Try table extraction first
        rows = extract_tables_from_pages(pdf_path, pages, logger)
        items = parse_table_rows(rows, annex_num, logger)

        # If table extraction yielded too few items, try text fallback
        if len(items) < 3:
            logger.info(f"Table extraction for Annex {annex_num} yielded only "
                        f"{len(items)} items. Trying text fallback...")
            text_items = extract_text_fallback(pdf_path, pages, annex_num, logger)
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
