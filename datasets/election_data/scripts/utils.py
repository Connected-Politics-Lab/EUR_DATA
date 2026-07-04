"""
Shared utilities for the euandi 2024 election dataset pipeline.

Provides logging setup, directory creation, the CSV/XLSX save helper, and the
core euandi sheet reader used by both the Ireland and EU-level parse steps.
"""

import logging
import re
import sys
import unicodedata
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def setup_logging(script_name: str) -> logging.Logger:
    """Configure console + file logging for a pipeline script."""
    logger = logging.getLogger(script_name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(config.LOG_FORMAT, config.LOG_DATE_FORMAT))
    logger.addHandler(ch)

    log_dir = config.BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    fh = logging.FileHandler(log_dir / f"{script_name}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(config.LOG_FORMAT, config.LOG_DATE_FORMAT))
    logger.addHandler(fh)

    return logger


def ensure_dirs():
    """Create the directory tree if it doesn't exist."""
    for d in [config.RAW_DIR, config.OUTPUT_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def save_both(df: pd.DataFrame, basename: str, output_dir: Path = None):
    """Save a DataFrame as both CSV and XLSX to the output directory."""
    logger = logging.getLogger("utils.save_both")
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"{basename}.csv"
    xlsx_path = output_dir / f"{basename}.xlsx"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False, engine="openpyxl")

    logger.info(f"Saved {basename}: {len(df)} rows -> {csv_path.name}, {xlsx_path.name}")
    return csv_path, xlsx_path


def _clean(value) -> str:
    """Trim a cell to a clean string; blanks/NaN become ''."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    text = str(value).strip()
    if text.lower() == "nan":
        return ""
    # Collapse internal newlines/whitespace runs introduced by the spreadsheet.
    return re.sub(r"\s+", " ", text)


def _norm(text: str) -> str:
    """Normalise text for fuzzy matching (lowercase, strip accents/space)."""
    nfkd = unicodedata.normalize("NFKD", text or "")
    ascii_text = "".join(c for c in nfkd if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", ascii_text).strip().lower()


def _find_marker_rows(df: pd.DataFrame) -> Tuple[Optional[int], Optional[int]]:
    """
    Locate the statement-header row and the salience-marker row by scanning
    column 0 for the marker strings, rather than assuming fixed indices.
    """
    header_row = salience_row = None
    for r in range(df.shape[0]):
        cell = _clean(df.iat[r, config.COL_STATEMENT_NUM])
        if cell == config.HEADER_MARKER:
            header_row = r
        elif cell == config.SALIENCE_MARKER:
            salience_row = r
    return header_row, salience_row


def read_euandi_sheet(workbook: Path, sheet_name: str) -> Dict[str, List[Dict]]:
    """
    Read one euandi coding sheet into structured statement + salience records.

    Returns a dict with two lists:
      "statements" - one record per policy statement (the FINAL placement)
      "salience"   - one record per salience pick (rank 1-3)

    Statement record keys: statement_num, statement_text, position_label,
        source_type, text_snippet, source_link
    Salience record keys:  salience_rank, statement_text
    """
    df = pd.read_excel(workbook, sheet_name=sheet_name, header=None)
    header_row, salience_row = _find_marker_rows(df)
    if header_row is None:
        raise ValueError(f"{sheet_name!r}: could not find '{config.HEADER_MARKER}' row")

    # Statements run from header_row+1 up to the salience marker (or sheet end).
    stmt_end = salience_row if salience_row is not None else df.shape[0]

    statements = []
    for r in range(header_row + 1, stmt_end):
        num = _clean(df.iat[r, config.COL_STATEMENT_NUM])
        # Statement rows are numbered 1..N; skip anything else (blank rows etc.).
        if not re.fullmatch(r"\d+(?:\.0)?", num):
            continue
        statement_num = int(float(num))
        statements.append({
            "statement_num": statement_num,
            "statement_text": _clean(df.iat[r, config.COL_STATEMENT_TEXT]),
            "position_label": _clean(df.iat[r, config.COL_FINAL_POSITION]),
            "source_type": _clean(df.iat[r, config.COL_FINAL_SOURCE_TYPE]),
            "text_snippet": _clean(df.iat[r, config.COL_FINAL_SNIPPET]),
            "source_link": _clean(df.iat[r, config.COL_FINAL_LINK]),
        })

    salience = []
    if salience_row is not None:
        for r in range(salience_row + 1, df.shape[0]):
            rank = _clean(df.iat[r, config.COL_STATEMENT_NUM])
            text = _clean(df.iat[r, config.COL_STATEMENT_TEXT])
            if not re.fullmatch(r"\d+(?:\.0)?", rank) or not text:
                continue
            salience.append({
                "salience_rank": int(float(rank)),
                "statement_text": text,
            })

    return {"statements": statements, "salience": salience}


def build_statement_lookup(statements: List[Dict]) -> Dict[str, int]:
    """Map normalised statement text -> statement_num for salience matching."""
    return {_norm(s["statement_text"]): s["statement_num"] for s in statements}


def match_salience_statement(text: str, lookup: Dict[str, int]) -> Optional[int]:
    """
    Resolve a salience statement to its statement_num via the text lookup.
    Falls back to a prefix match if the salience text was truncated.
    """
    key = _norm(text)
    if key in lookup:
        return lookup[key]
    for cand_key, num in lookup.items():
        if cand_key.startswith(key) or key.startswith(cand_key):
            return num
    return None
