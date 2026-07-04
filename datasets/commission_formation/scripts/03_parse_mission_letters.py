"""
03_parse_mission_letters.py
Extract text from mission letter PDFs and parse policy commitments.

Three extraction strategies (ordered by confidence):
  1. High confidence: Bullet points (lines starting with -, --, *)
  2. Medium confidence: Directive sentences (I want you to..., ensure that...)
  3. Medium confidence: Legislative references (propose/review ... Regulation/Directive)

Each commitment is classified as: legislative, policy, coordination,
review, report, or other.

Output: mission_letter_commitments.csv + .xlsx
"""

import re
import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, save_both
from scripts import llm_classify

try:
    import pdfplumber
except ImportError:
    pdfplumber = None


# ============================================================
# Text extraction
# ============================================================

def extract_text_from_pdf(pdf_path: Path, logger) -> List[Dict]:
    """
    Extract text from a mission letter PDF using pdfplumber.
    Returns list of {page_number, text} dicts.
    """
    if pdfplumber is None:
        logger.error("pdfplumber not installed. Run: pip install pdfplumber")
        return []

    pages = []
    try:
        with pdfplumber.open(pdf_path) as pdf:
            for i, page in enumerate(pdf.pages, 1):
                text = page.extract_text()
                if text:
                    pages.append({"page_number": i, "text": text})
    except Exception as e:
        logger.error(f"Failed to extract text from {pdf_path.name}: {e}")

    return pages


def save_extracted_text(commissioner_id: str, pages: List[Dict], logger):
    """Save extracted text to a .txt file in processed directory."""
    output_path = config.PROCESSED_MISSION_TEXTS / f"{commissioner_id}_text.txt"
    with open(output_path, "w", encoding="utf-8") as f:
        for page in pages:
            f.write(f"\n--- PAGE {page['page_number']} ---\n")
            f.write(page["text"])
            f.write("\n")
    logger.debug(f"Saved text for {commissioner_id}: {len(pages)} pages")


# ============================================================
# Section heading detection
# ============================================================

def detect_section_heading(lines: List[str], line_idx: int) -> str:
    """
    Look backwards from current line to find the nearest section heading.
    Headings are typically short lines in title case or ALL CAPS.
    """
    for i in range(line_idx - 1, max(line_idx - 15, -1), -1):
        if i < 0:
            break
        line = lines[i].strip()
        # Heading heuristics: short, title-case or all-caps, no ending period
        if (
            10 < len(line) < 100
            and not line.endswith(".")
            and not line.startswith(("-", "*", "–"))
            and (line == line.upper() or line == line.title() or line[0].isupper())
        ):
            # Skip lines that look like regular text
            word_count = len(line.split())
            if word_count <= 10:
                return line
    return ""


# ============================================================
# Commitment extraction strategies
# ============================================================

# Patterns for directive sentences
DIRECTIVE_PATTERNS = [
    # Bound to a single sentence (`[^.]+\.`) rather than a greedy `.+`, which
    # otherwise runs to the end of the page and swallows many unrelated bullets.
    re.compile(r"I (?:want|would like|expect|ask|am asking) you to\s+([^.]+\.)", re.IGNORECASE),
    re.compile(r"You (?:should|will|must|are expected to)\s+([^.]+\.)", re.IGNORECASE),
    re.compile(r"I (?:want|would like) you to (?:also\s+)?([^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(ensure (?:that\s+)?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(propose (?:a |an |the )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(launch (?:a |an |the )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(review (?:the |a |an )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(present (?:a |an |the )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(develop (?:a |an |the )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(strengthen (?:the |a |an )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(work (?:on |towards |with )[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(put forward (?:a |an |the )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(take forward [^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(deliver (?:on |a |an |the )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(prepare (?:a |an |the )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(lead (?:the |a |an |on )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(drive (?:the |a |an )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(set up (?:a |an |the )?[^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(coordinate [^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(implement [^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(promote [^.]+\.)", re.IGNORECASE),
    re.compile(r"(?:^|\.\s+)(support [^.]+\.)", re.IGNORECASE),
]

# Pattern for legislative references
LEGISLATIVE_PATTERN = re.compile(
    r"((?:propose|present|review|revise|update|adopt|table|put forward)"
    r"\s+(?:a |an |the )?(?:new )?"
    r"(?:[\w\s,]+)?"
    r"(?:Regulation|Directive|legislation|legislative\s+proposal|"
    r"Communication|Action Plan|Strategy|Recommendation|White Paper|Green Paper)"
    r"[^.]*\.)",
    re.IGNORECASE,
)

# Bullet point pattern
BULLET_PATTERN = re.compile(r"^\s*[-–—*•]\s+(.+)")


def _looks_like_heading(line: str) -> bool:
    """A short title-case / all-caps line with no terminal full stop."""
    s = line.strip()
    if not (10 < len(s) < 100) or s.endswith("."):
        return False
    if s.startswith(("-", "*", "–", "—", "•")):
        return False
    return (s == s.upper() or s == s.title()) and len(s.split()) <= 10


def extract_bullet_commitments(text: str, lines: List[str], page_number: int) -> List[Dict]:
    """Strategy 1: Extract bullet-pointed commitments (high confidence).

    A bullet's text frequently wraps across several physical lines in the PDF.
    Gather those continuation lines (until a blank line, the next bullet, or a
    heading that follows a completed sentence) so the commitment is captured in
    full rather than truncated at the first line.
    """
    commitments = []
    n = len(lines)
    i = 0
    while i < n:
        match = BULLET_PATTERN.match(lines[i])
        if not match:
            i += 1
            continue

        bullet_idx = i
        parts = [match.group(1).strip()]
        raw_lines = [lines[i].strip()]
        j = i + 1
        while j < n and (j - i) <= 8:
            raw = lines[j]
            nxt = raw.strip()
            if not nxt or BULLET_PATTERN.match(raw):
                break  # blank line or next bullet ends this commitment
            acc = " ".join(parts).rstrip()
            # A heading only ends the bullet once the current sentence is complete;
            # otherwise the line is a mid-sentence continuation.
            if _looks_like_heading(raw) and acc and acc[-1] in ".!?:":
                break
            parts.append(nxt)
            raw_lines.append(nxt)
            j += 1
        i = max(j, i + 1)

        commitment_text = re.sub(r"\s+", " ", " ".join(parts)).strip()
        # Skip very short bullets (likely sub-bullets or noise)
        if len(commitment_text) < 20:
            continue
        # Skip bullets that are just names or headers
        if commitment_text == commitment_text.upper() and len(commitment_text) < 50:
            continue

        section = detect_section_heading(lines, bullet_idx)
        commitments.append({
            "commitment_text": commitment_text,
            "section_heading": section,
            "extraction_method": "bullet_point",
            "confidence": "high",
            "page_number": page_number,
            "raw_paragraph": " ".join(raw_lines),
        })

    return commitments


def extract_directive_commitments(text: str, lines: List[str], page_number: int) -> List[Dict]:
    """Strategy 2: Extract directive sentence commitments (medium confidence)."""
    commitments = []
    seen_texts = set()

    full_text = " ".join(lines)

    for pattern in DIRECTIVE_PATTERNS:
        for match in pattern.finditer(full_text):
            commitment_text = match.group(0).strip()

            # Skip duplicates
            norm = commitment_text.lower()[:80]
            if norm in seen_texts:
                continue
            seen_texts.add(norm)

            if len(commitment_text) < 25:
                continue

            # Find approximate line number for section heading
            match_start = match.start()
            char_count = 0
            line_idx = 0
            for idx, line in enumerate(lines):
                char_count += len(line) + 1
                if char_count >= match_start:
                    line_idx = idx
                    break

            section = detect_section_heading(lines, line_idx)

            # Get surrounding paragraph for context
            para_start = max(0, match.start() - 100)
            para_end = min(len(full_text), match.end() + 100)
            raw_para = full_text[para_start:para_end].strip()

            commitments.append({
                "commitment_text": commitment_text,
                "section_heading": section,
                "extraction_method": "directive_sentence",
                "confidence": "medium",
                "page_number": page_number,
                "raw_paragraph": raw_para,
            })

    return commitments


def extract_legislative_commitments(text: str, lines: List[str], page_number: int) -> List[Dict]:
    """Strategy 3: Extract legislative reference commitments (medium confidence)."""
    commitments = []
    seen_texts = set()

    full_text = " ".join(lines)

    for match in LEGISLATIVE_PATTERN.finditer(full_text):
        commitment_text = match.group(0).strip()

        norm = commitment_text.lower()[:80]
        if norm in seen_texts:
            continue
        seen_texts.add(norm)

        if len(commitment_text) < 25:
            continue

        # Find line index
        match_start = match.start()
        char_count = 0
        line_idx = 0
        for idx, line in enumerate(lines):
            char_count += len(line) + 1
            if char_count >= match_start:
                line_idx = idx
                break

        section = detect_section_heading(lines, line_idx)
        para_start = max(0, match.start() - 100)
        para_end = min(len(full_text), match.end() + 100)
        raw_para = full_text[para_start:para_end].strip()

        commitments.append({
            "commitment_text": commitment_text,
            "section_heading": section,
            "extraction_method": "legislative_reference",
            "confidence": "medium",
            "page_number": page_number,
            "raw_paragraph": raw_para,
        })

    return commitments


# ============================================================
# Commitment classification
# ============================================================

CLASSIFICATION_KEYWORDS = {
    "legislative": [
        "regulation", "directive", "legislation", "legislative",
        "legal framework", "legal basis", "amend", "repeal",
        "transpose", "codif",
    ],
    "policy": [
        "strategy", "action plan", "roadmap", "framework",
        "initiative", "programme", "plan", "agenda",
        "communication", "white paper", "green paper",
    ],
    "coordination": [
        "coordinate", "cooperation", "work with", "together with",
        "dialogue", "partnership", "stakeholder", "consult",
        "align", "liaise",
    ],
    "review": [
        "review", "evaluate", "assess", "fitness check",
        "impact assessment", "stock-taking", "audit",
    ],
    "report": [
        "report", "reporting", "monitor", "monitoring",
        "annual report", "progress report", "publish",
    ],
}


def classify_commitment(text: str) -> str:
    """Classify a commitment by keyword matching. Returns type string."""
    text_lower = text.lower()
    scores = {}
    for ctype, keywords in CLASSIFICATION_KEYWORDS.items():
        scores[ctype] = sum(1 for kw in keywords if kw in text_lower)

    if max(scores.values()) == 0:
        return "other"

    return max(scores, key=scores.get)


def make_short_description(text: str, max_len: int = 100) -> str:
    """Create a short summary of a commitment text."""
    # Remove leading verbs like "I want you to"
    short = re.sub(
        r"^(I (?:want|would like|expect|ask) you to\s+)",
        "", text, flags=re.IGNORECASE
    ).strip()
    short = re.sub(
        r"^(You (?:should|will|must)\s+)",
        "", short, flags=re.IGNORECASE
    ).strip()

    if len(short) <= max_len:
        return short

    # Truncate at word boundary
    truncated = short[:max_len].rsplit(" ", 1)[0]
    return truncated + "..."


# ============================================================
# Deduplication
# ============================================================

def deduplicate_commitments(commitments: List[Dict]) -> List[Dict]:
    """Remove duplicate commitments within one commissioner's letter.

    The three strategies overlap heavily: a directive/legislative sentence is
    often also part of a bullet. We keep the higher-confidence and fuller version
    and drop any commitment whose text is contained within one already kept.
    """
    if not commitments:
        return commitments

    # Bullets (high confidence) first, then longer text first, so the fullest
    # version of an overlapping commitment is the one retained.
    confidence_order = {"high": 0, "medium": 1, "low": 2}
    commitments.sort(
        key=lambda c: (confidence_order.get(c["confidence"], 3),
                       -len(c["commitment_text"]))
    )

    def _norm(text: str) -> str:
        return re.sub(r"\W+", " ", text.lower()).strip()

    kept = []
    kept_norms = []
    for c in commitments:
        norm = _norm(c["commitment_text"])
        if len(norm) < 15:
            continue
        # Drop if this text is contained in an already-kept (fuller) commitment.
        if any(norm in k for k in kept_norms):
            continue
        kept.append(c)
        kept_norms.append(norm)

    return kept


# ============================================================
# Main pipeline
# ============================================================

def parse_mission_letters() -> pd.DataFrame:
    """Parse all downloaded mission letter PDFs and extract commitments."""
    logger = setup_logging("03_parse_mission_letters")
    ensure_dirs()

    all_commitments = []
    commitment_counter = 0

    for comm in config.COMMISSIONERS_CURATED:
        cid = comm["commissioner_id"]
        name = comm["full_name"]
        portfolio = comm["portfolio_title"]

        if not comm.get("mission_letter_url"):
            logger.info(f"No mission letter for {name} - skipping.")
            continue

        # Find the PDF
        safe_name = comm["last_name"].replace(" ", "_").replace("'", "")
        pdf_path = config.RAW_MISSION_LETTERS / f"{cid}_{safe_name}_mission_letter.pdf"

        if not pdf_path.exists():
            logger.warning(f"PDF not found for {name}: {pdf_path}")
            continue

        logger.info(f"Parsing mission letter for {name}...")

        # Extract text
        pages = extract_text_from_pdf(pdf_path, logger)
        if not pages:
            logger.warning(f"No text extracted from {pdf_path.name}")
            continue

        # Save extracted text
        save_extracted_text(cid, pages, logger)

        # Extract commitments from each page
        page_commitments = []
        for page_data in pages:
            page_num = page_data["page_number"]
            text = page_data["text"]
            lines = text.split("\n")

            # Apply all three strategies
            bullets = extract_bullet_commitments(text, lines, page_num)
            directives = extract_directive_commitments(text, lines, page_num)
            legislative = extract_legislative_commitments(text, lines, page_num)

            page_commitments.extend(bullets)
            page_commitments.extend(directives)
            page_commitments.extend(legislative)

        # Deduplicate
        page_commitments = deduplicate_commitments(page_commitments)

        # Add commissioner metadata (classification happens in one pass below).
        for c in page_commitments:
            commitment_counter += 1
            c["commitment_id"] = f"C{commitment_counter:04d}"
            c["commissioner_id"] = cid
            c["commissioner_name"] = name
            c["portfolio_title"] = portfolio
            c["commitment_short"] = make_short_description(c["commitment_text"])

        all_commitments.extend(page_commitments)
        logger.info(f"  {name}: {len(page_commitments)} commitments extracted")

    # Classify every commitment in one cache-first LLM pass (Sonnet 4.6), with
    # the keyword classifier as a fallback for texts neither cached nor reachable.
    texts = [c["commitment_text"] for c in all_commitments]
    llm_results = llm_classify.classify_texts(texts, logger)
    for c in all_commitments:
        res = llm_results.get(c["commitment_text"])
        if res:
            c["commitment_type"] = res["commitment_type"]
            c["classification_method"] = "llm"
        else:
            c["commitment_type"] = classify_commitment(c["commitment_text"])
            c["classification_method"] = "keyword"
    n_llm = sum(1 for c in all_commitments if c["classification_method"] == "llm")
    logger.info(f"Classification: {n_llm}/{len(all_commitments)} via LLM, "
                f"{len(all_commitments) - n_llm} via keyword fallback.")

    if not all_commitments:
        logger.warning("No commitments extracted from any mission letter!")
        # Return empty DataFrame with correct schema
        return pd.DataFrame(columns=[
            "commitment_id", "commissioner_id", "commissioner_name",
            "portfolio_title", "commitment_text", "commitment_short",
            "section_heading", "commitment_type", "extraction_method",
            "confidence", "page_number", "raw_paragraph",
        ])

    df = pd.DataFrame(all_commitments)

    # Column ordering
    columns = [
        "commitment_id", "commissioner_id", "commissioner_name",
        "portfolio_title", "commitment_text", "commitment_short",
        "section_heading", "commitment_type", "classification_method",
        "extraction_method", "confidence", "page_number", "raw_paragraph",
    ]
    columns = [c for c in columns if c in df.columns]
    df = df[columns]

    # Summary stats
    logger.info(f"Total commitments: {len(df)}")
    logger.info(f"By confidence: {df['confidence'].value_counts().to_dict()}")
    logger.info(f"By type: {df['commitment_type'].value_counts().to_dict()}")
    logger.info(f"By method: {df['extraction_method'].value_counts().to_dict()}")

    return df


def main():
    df = parse_mission_letters()
    save_both(df, "mission_letter_commitments")
    print(f"mission_letter_commitments: {len(df)} rows saved.")
    return df


if __name__ == "__main__":
    main()
