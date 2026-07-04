"""
01_build_agenda_items.py
Build the agenda-item spine from the sibling commission_formation dataset.

One row per tracked agenda item:
  * every CWP 2025 work-programme item (Annex I-IV), and
  * the legislative mission-letter commitments.

Links back via wp_item_id / commitment_id; never duplicates sibling content.
No network access.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, save_both

AGENDA_COLS = [
    "agenda_item_id", "source_scope", "wp_item_id", "commitment_id",
    "title", "policy_area", "indicative_timing", "expected_act_type",
]

ANNEX_TO_SCOPE = {
    "I": "cwp_annex_i",
    "II": "cwp_annex_ii",
    "III": "cwp_annex_iii",
    "IV": "cwp_annex_iv",
}


def _s(value) -> str:
    """Clean a cell to a string; NaN/blank -> ''."""
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def main():
    logger = setup_logging("01_agenda_items")
    ensure_dirs()

    if not config.WORK_PROGRAMME_CSV.exists():
        raise FileNotFoundError(
            f"Sibling input missing: {config.WORK_PROGRAMME_CSV}. "
            "Run the commission_formation pipeline first."
        )

    wp = pd.read_csv(config.WORK_PROGRAMME_CSV)
    rows = []
    counter = 0

    # CWP work-programme items (all four annexes).
    for _, r in wp.iterrows():
        counter += 1
        annex = _s(r.get("annex"))
        rows.append({
            "agenda_item_id": f"AI{counter:04d}",
            "source_scope": ANNEX_TO_SCOPE.get(annex, "cwp_annex_i"),
            "wp_item_id": _s(r.get("item_id")),
            "commitment_id": "",
            "title": _s(r.get("title")),
            "policy_area": _s(r.get("policy_area")),
            "indicative_timing": _s(r.get("indicative_timing")),
            "expected_act_type": _s(r.get("type_of_act")),
        })

    # Legislative mission-letter commitments (the only tractable subset).
    n_commitments = 0
    if config.MISSION_COMMITMENTS_CSV.exists():
        cmt = pd.read_csv(config.MISSION_COMMITMENTS_CSV)
        legislative = cmt[cmt["commitment_type"].astype(str).str.lower() == "legislative"]
        for _, r in legislative.iterrows():
            counter += 1
            n_commitments += 1
            title = _s(r.get("commitment_short")) or _s(r.get("commitment_text"))[:200]
            rows.append({
                "agenda_item_id": f"AI{counter:04d}",
                "source_scope": "mission_letter",
                "wp_item_id": "",
                "commitment_id": _s(r.get("commitment_id")),
                "title": title,
                "policy_area": _s(r.get("portfolio_title")),
                "indicative_timing": "",
                "expected_act_type": "",
            })
    else:
        logger.warning("Mission commitments CSV not found; skipping that scope.")

    df = pd.DataFrame(rows, columns=AGENDA_COLS)
    save_both(df, "agenda_items")
    logger.info(
        f"agenda_items: {len(df)} rows "
        f"({len(wp)} CWP items + {n_commitments} legislative commitments). "
        f"By scope: {df['source_scope'].value_counts().to_dict()}"
    )
    return df


if __name__ == "__main__":
    main()
