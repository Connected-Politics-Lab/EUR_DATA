"""
Shared per-reference status fetching, used by scripts 04 and 05.

Fetches one procedure from the EP Open Data API, normalises its stage, and
derives the snapshot fields (delivered / on_time / withdrawn).
"""

import calendar
import re
import sys
from pathlib import Path
from typing import Dict, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from scripts.utils import fetch_json
from scripts.status_map import summarise

_QUARTER_RE = re.compile(r"Q([1-4])\s*(?:/\s*Q[1-4]\s*)?(\d{4})")


def target_date(timing: str) -> Optional[str]:
    """End-of-quarter target date from an indicative-timing string, or None.

    Only quarter-form timings (e.g. 'Q2 2025') are delivery targets; a bare year
    (an Annex IV origin year) is not a deadline.
    """
    if not isinstance(timing, str):
        return None
    m = _QUARTER_RE.search(timing)
    if not m:
        return None
    q, year = int(m.group(1)), int(m.group(2))
    month = q * 3
    return f"{year}-{month:02d}-{calendar.monthrange(year, month)[1]:02d}"


def on_time(timing: str, proposed_date, today: str) -> int:
    """1 = on/before target, -1 = late/overdue, 0 = no target / n/a."""
    target = target_date(timing)
    if target is None:
        return 0
    if proposed_date:
        return 1 if proposed_date <= target else -1
    return -1 if today > target else 0


def fetch_procedure(process_id_ep: str) -> Optional[Dict]:
    """Fetch and unwrap a single EP procedure object, or None."""
    pid = (process_id_ep or "").strip()
    if not pid:
        return None
    data = fetch_json(f"{config.EP_API_BASE}/procedures/{pid}",
                      params={"language": "en"})
    if not data:
        return None
    payload = data.get("data", data)
    if isinstance(payload, list):
        return payload[0] if payload else None
    return payload if isinstance(payload, dict) else None


def status_row(ref: Dict, indicative_timing: str, today: str) -> Dict:
    """Build a procedure_status row dict for one procedure reference."""
    proc = fetch_procedure(ref.get("process_id_ep"))
    if proc:
        summary = summarise(proc)
    else:
        summary = {"status": config.STATUS_NOT_FOUND, "ep_stage_code": None,
                   "latest_event_type": None, "latest_event_date": None,
                   "proposed_date": None}
    status = summary["status"]
    return {
        "status_id": f"{ref['procedure_ref_id']}_{today}",
        "procedure_ref_id": ref["procedure_ref_id"],
        "agenda_item_id": ref["agenda_item_id"],
        "as_of_date": today,
        "status": status,
        "ep_stage_code": summary["ep_stage_code"],
        "latest_event_type": summary["latest_event_type"],
        "latest_event_date": summary["latest_event_date"],
        "proposed_date": summary["proposed_date"],
        "delivered": status in ("adopted", "in_force"),
        "on_time": on_time(indicative_timing, summary["proposed_date"], today),
        "withdrawn": status == "withdrawn",
    }


STATUS_COLS = [
    "status_id", "procedure_ref_id", "agenda_item_id", "as_of_date", "status",
    "ep_stage_code", "latest_event_type", "latest_event_date", "proposed_date",
    "delivered", "on_time", "withdrawn",
]
