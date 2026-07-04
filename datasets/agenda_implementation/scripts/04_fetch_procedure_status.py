"""
04_fetch_procedure_status.py
Resolve each agenda-linked procedure reference to its current legislative stage
via the EP Open Data API, and APPEND a dated snapshot to procedure_status.csv.

This is the core deliverable: the implementation-success time series. Re-runs on
a later date append a new snapshot (same-day re-runs are idempotent). Derives
`delivered`, `withdrawn`, and `on_time` (vs the item's indicative timing).
Network access; responses cached under data/raw/.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, save_both, as_of_date
from scripts.status_fetch import status_row, STATUS_COLS


def main():
    logger = setup_logging("04_procedure_status")
    ensure_dirs()
    today = as_of_date()

    refs = pd.read_csv(config.OUTPUT_DIR / "procedure_references.csv")
    agenda = pd.read_csv(config.OUTPUT_DIR / "agenda_items.csv").set_index("agenda_item_id")

    new_rows = []
    for _, ref in refs.iterrows():
        aid = ref["agenda_item_id"]
        timing = agenda.loc[aid, "indicative_timing"] if aid in agenda.index else ""
        new_rows.append(status_row(ref.to_dict(), timing, today))

    new_df = pd.DataFrame(new_rows, columns=STATUS_COLS)

    # Append to the time series; replace any existing rows for today (idempotent).
    out_path = config.OUTPUT_DIR / "procedure_status.csv"
    if out_path.exists():
        prior = pd.read_csv(out_path)
        prior = prior[prior["as_of_date"] != today]
        combined = pd.concat([prior, new_df], ignore_index=True)
    else:
        combined = new_df
    combined["on_time"] = combined["on_time"].astype("Int64")
    save_both(combined, "procedure_status")

    snapshots = combined["as_of_date"].nunique()
    delivered = int(new_df["delivered"].sum())
    logger.info(
        f"procedure_status: +{len(new_df)} rows for {today} "
        f"({snapshots} snapshot(s) total). This snapshot: {delivered} delivered, "
        f"status mix {new_df['status'].value_counts().to_dict()}"
    )
    return new_df


if __name__ == "__main__":
    main()
