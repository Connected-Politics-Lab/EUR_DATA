"""
Procedure-reference parsing.

The CWP work-programme rows embed COM document references and interinstitutional
procedure numbers inside the `title`/`description` prose (they are NOT in clean
columns). These helpers extract and canonicalise them, and convert an
interinstitutional reference to the EP API `process_id` form.

  interinstitutional ref : "2018/0063B(COD)"   <->  EP process_id : "2018-0063B"
"""

import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

# Interinstitutional procedure reference: YYYY/NNNN[letter] (TYPE)
# Anchored on the parenthesised type token because the surrounding text is prose.
_TYPE_ALT = "|".join(config.PROCEDURE_TYPE_TOKENS)
PROCEDURE_RE = re.compile(
    r"(?P<year>\d{4})\s*/\s*(?P<num>\d{3,4}[A-Z]?)\s*\(\s*(?P<type>" + _TYPE_ALT + r")\s*\)"
)

# COM/JOIN document reference: COM(YYYY)NNN  /  JOIN(YYYY)NNN
COM_RE = re.compile(r"(?P<kind>COM|JOIN)\s*\(\s*(?P<year>\d{4})\s*\)\s*(?P<num>\d{1,4})")


def canonical_ref(year: str, num: str, ptype: str) -> str:
    """-> 'YYYY/NNNN(TYPE)' with the number zero-padded to 4 digits."""
    digits = re.match(r"(\d+)([A-Z]?)", num)
    padded = f"{int(digits.group(1)):04d}{digits.group(2)}"
    return f"{year}/{padded}({ptype})"


def to_process_id(interinstitutional_ref: str) -> Optional[str]:
    """'2018/0063B(COD)' -> '2018-0063B' (EP API process_id form)."""
    m = re.match(r"(\d{4})/(\d{3,4}[A-Z]?)\(", interinstitutional_ref)
    if not m:
        return None
    return f"{m.group(1)}-{m.group(2)}"


def extract_refs(text: str) -> List[Dict[str, str]]:
    """
    Extract every distinct procedure reference found in a block of text.

    Returns a list of dicts with keys: interinstitutional_ref, process_id_ep,
    procedure_type, com_reference (the nearest preceding COM/JOIN ref, if any).
    Order-preserving and de-duplicated on interinstitutional_ref.
    """
    if not text:
        return []

    # Collect COM references with their positions so we can attach the nearest
    # preceding one to each procedure number.
    com_hits = [
        (m.start(), f"{m.group('kind')}({m.group('year')}){m.group('num')}")
        for m in COM_RE.finditer(text)
    ]

    out: List[Dict[str, str]] = []
    seen = set()
    for m in PROCEDURE_RE.finditer(text):
        ref = canonical_ref(m.group("year"), m.group("num"), m.group("type"))
        if ref in seen:
            continue
        seen.add(ref)
        preceding = [c for pos, c in com_hits if pos <= m.start()]
        out.append({
            "interinstitutional_ref": ref,
            "process_id_ep": to_process_id(ref),
            "procedure_type": m.group("type"),
            "com_reference": preceding[-1] if preceding else "",
        })
    return out
