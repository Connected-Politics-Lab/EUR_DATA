"""
Map an EP Open Data API procedure to the normalised status enum.

The EP API gives each dossier a `current_stage` (a procedure-phase authority
URI) plus a `consists_of` list of dated activities. We normalise the stage code
to our ordered status ladder (see config.STATUS_LADDER), using an exact lookup
first and a substring fallback for code variants.
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def _last_segment(uri: str) -> str:
    return (uri or "").rstrip("/").rsplit("/", 1)[-1].upper()


def stage_to_status(stage_uri: str) -> str:
    """Normalise a procedure-phase URI / code to a status enum value."""
    code = _last_segment(stage_uri)
    if not code:
        return config.STATUS_UNKNOWN
    if code in config.PHASE_CODE_TO_STATUS:
        return config.PHASE_CODE_TO_STATUS[code]
    # Substring fallback for unseen variants.
    if "WITHDRAWN" in code:
        return "withdrawn"
    if "REJECTED" in code:
        return "rejected"
    if "LAPSED" in code:
        return "lapsed"
    if "COMPLETED" in code or "SIGNATURE" in code or "ADOPTED" in code:
        return "adopted"
    if "RDG3" in code or "CONCILIATION" in code:
        return "ep_3rd_read"
    if "RDG2" in code or "2ND_READING" in code:
        return "ep_2nd_read"
    if "COUNCIL_1ST" in code:
        return "council_1st"
    if "RDG1" in code or "1ST_READING" in code:
        return "ep_1st_read"
    if "AWAITING" in code or "PROPOSAL" in code:
        return "proposed"
    return config.STATUS_UNKNOWN


def _events(procedure: Dict) -> List[Dict]:
    ev = procedure.get("consists_of", []) or []
    return [e for e in ev if isinstance(e, dict)]


def summarise(procedure: Dict) -> Dict:
    """
    Reduce an EP API procedure object to the fields the status table needs.

    Returns a dict: status, ep_stage_code, latest_event_type,
    latest_event_date, proposed_date.
    """
    stage_uri = procedure.get("current_stage", "")
    status = stage_to_status(stage_uri)

    dated = [(e.get("activity_date"), e.get("had_activity_type"))
             for e in _events(procedure) if e.get("activity_date")]
    dated.sort(key=lambda t: t[0])

    proposed_date = dated[0][0] if dated else None
    latest_date = dated[-1][0] if dated else None
    latest_type = _last_segment(dated[-1][1]) if dated and dated[-1][1] else None

    return {
        "status": status,
        "ep_stage_code": _last_segment(stage_uri) or None,
        "latest_event_type": latest_type,
        "latest_event_date": latest_date,
        "proposed_date": proposed_date,
    }


def ladder_rank(status: str) -> Optional[int]:
    """Position on the progress ladder, or None for off-ladder/terminal states."""
    return config.STATUS_LADDER.index(status) if status in config.STATUS_LADDER else None
