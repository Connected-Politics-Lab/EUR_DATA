"""
02_parse_procedure_refs.py
Extract the COM / interinstitutional procedure references embedded in the CWP
work-programme prose and emit one row per (agenda_item x procedure reference).

These references (the Annex IV withdrawals) are the join key to the EP Open
Data API; they sit in the "References: ..." part of the description text.
Annex I new initiatives carry no reference yet and are handled later (script 05);
manual references in data/manual/legislative_commitments.csv are also merged.
No network access.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, save_both
from scripts.refs import extract_refs, to_process_id

REF_COLS = [
    "procedure_ref_id", "agenda_item_id", "interinstitutional_ref",
    "process_id_ep", "procedure_type", "com_reference", "celex",
    "extraction_method", "match_confidence",
]


def _s(value) -> str:
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return ""
    return str(value).strip()


def main():
    logger = setup_logging("02_procedure_refs")
    ensure_dirs()

    agenda = pd.read_csv(config.OUTPUT_DIR / "agenda_items.csv")
    wp = pd.read_csv(config.WORK_PROGRAMME_CSV).set_index("item_id")

    rows = []
    counter = 0
    items_with_ref = 0

    for _, item in agenda.iterrows():
        wp_id = _s(item.get("wp_item_id"))
        # Build the source text: WP title + description carry the refs.
        if wp_id and wp_id in wp.index:
            wp_row = wp.loc[wp_id]
            text = f"{_s(wp_row.get('title'))} {_s(wp_row.get('description'))}"
        else:
            text = _s(item.get("title"))

        found = extract_refs(text)
        if found:
            items_with_ref += 1
        for ref in found:
            counter += 1
            rows.append({
                "procedure_ref_id": f"PR{counter:04d}",
                "agenda_item_id": item["agenda_item_id"],
                "interinstitutional_ref": ref["interinstitutional_ref"],
                "process_id_ep": ref["process_id_ep"],
                "procedure_type": ref["procedure_type"],
                "com_reference": ref["com_reference"],
                "celex": "",
                "extraction_method": "regex_interleaved",
                "match_confidence": 1.0,
            })

    # Merge any manually curated references (commitment -> procedure links).
    if config.LEGISLATIVE_COMMITMENTS_CSV.exists():
        manual = pd.read_csv(config.LEGISLATIVE_COMMITMENTS_CSV)
        agenda_by_commitment = dict(
            zip(agenda["commitment_id"].astype(str), agenda["agenda_item_id"])
        )
        for _, r in manual.iterrows():
            ref = _s(r.get("interinstitutional_ref"))
            cmt = _s(r.get("commitment_id"))
            aid = agenda_by_commitment.get(cmt)
            if not ref or not aid:
                continue
            counter += 1
            rows.append({
                "procedure_ref_id": f"PR{counter:04d}",
                "agenda_item_id": aid,
                "interinstitutional_ref": ref,
                "process_id_ep": to_process_id(ref),
                "procedure_type": ref.split("(")[-1].rstrip(")") if "(" in ref else "",
                "com_reference": _s(r.get("com_reference")),
                "celex": "",
                "extraction_method": "manual",
                "match_confidence": 1.0,
            })

    df = pd.DataFrame(rows, columns=REF_COLS)
    save_both(df, "procedure_references")
    logger.info(
        f"procedure_references: {len(df)} refs from {items_with_ref} agenda items. "
        f"By type: {df['procedure_type'].value_counts().to_dict()}"
    )
    return df


if __name__ == "__main__":
    main()
