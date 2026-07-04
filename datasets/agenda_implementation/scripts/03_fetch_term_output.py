"""
03_fetch_term_output.py
Catalogue the 2024-2029 term's legislative procedures from the EP Open Data API
(the baseline corpus), flagging which ones appear in the CWP agenda.

This is the denominator for "how much of all legislative activity is planned
agenda vs not". Detailed per-procedure status is resolved only for agenda-linked
procedures (script 04), so this table is a catalogue, not a status table.
Network access; responses cached under data/raw/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, save_both, fetch_json, as_of_date

OUTPUT_COLS = [
    "proc_output_id", "interinstitutional_ref", "process_id_ep",
    "procedure_type", "year", "is_in_agenda", "as_of_date",
]


def _list_procedures(ptype: str, year: int, logger):
    """Page through the listing endpoint for one procedure type and year."""
    items = []
    offset = 0
    while True:
        data = fetch_json(
            f"{config.EP_API_BASE}/procedures",
            params={"process-type": ptype, "year": year,
                    "limit": config.EP_API_PAGE_LIMIT, "offset": offset},
        )
        page = (data or {}).get("data", []) if data else []
        if not page:
            break
        items.extend(page)
        if len(page) < config.EP_API_PAGE_LIMIT:
            break
        offset += config.EP_API_PAGE_LIMIT
    logger.info(f"  {ptype} {year}: {len(items)} procedures")
    return items


def main():
    logger = setup_logging("03_term_output")
    ensure_dirs()
    today = as_of_date()

    # Agenda-linked process ids, for the is_in_agenda flag.
    refs = pd.read_csv(config.OUTPUT_DIR / "procedure_references.csv")
    agenda_pids = set(refs["process_id_ep"].dropna().astype(str))

    rows = []
    counter = 0
    seen_pids = set()
    for ptype in config.PROCEDURE_TYPES:
        for year in config.TERM_YEARS:
            for proc in _list_procedures(ptype, year, logger):
                pid = str(proc.get("process_id", ""))
                # A procedure re-referenced under a second type (e.g. a CNS
                # relaunched as NLE) is listed by the API once per type; keep
                # one row per procedure.
                if pid and pid in seen_pids:
                    continue
                seen_pids.add(pid)
                # label is usually a single ref string, but is a list when the
                # procedure carries refs under more than one type; prefer the
                # ref matching the type being listed.
                label = proc.get("label", "")
                if isinstance(label, list):
                    matching = [l for l in label if f"({ptype})" in str(l)]
                    label = (matching or label)[0]
                counter += 1
                rows.append({
                    "proc_output_id": f"TO{counter:05d}",
                    "interinstitutional_ref": label,
                    "process_id_ep": pid,
                    "procedure_type": ptype,
                    "year": year,
                    "is_in_agenda": pid in agenda_pids,
                    "as_of_date": today,
                })

    df = pd.DataFrame(rows, columns=OUTPUT_COLS)
    save_both(df, "term_legislative_output")
    logger.info(
        f"term_legislative_output: {len(df)} procedures "
        f"({int(df['is_in_agenda'].sum())} in CWP agenda). "
        f"By type: {df['procedure_type'].value_counts().to_dict()}"
    )
    return df


if __name__ == "__main__":
    main()
