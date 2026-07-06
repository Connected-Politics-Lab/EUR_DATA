"""
07_build_evaluations.py
Build the curated evaluations table for the CWP Annex II items (the annual
plan on evaluations and fitness checks, including the interim/mid-term
evaluations).

These are evaluations, not legislative procedures, so they have no EP procedure
stage: "implemented" means the evaluation/SWD was published. There is no public
API for the Commission evaluation register, so this scope is curated. The script
scaffolds a worksheet pre-filled with the relevant agenda items if none exists,
then ingests whatever the researcher has coded. No network access.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, save_both, as_of_date

EVAL_COLS = [
    "evaluation_id", "agenda_item_id", "evaluation_type", "swd_celex",
    "published_date", "delivered", "as_of_date",
]
# The worksheet is keyed on wp_item_id, not agenda_item_id: AIxxxx ids are
# positional and renumber whenever the spine changes, so a committed worksheet
# keyed on them silently mis-attaches curation after a re-run. WPxxx ids are
# stable across spine rebuilds.
WORKSHEET_COLS = [
    "wp_item_id", "title", "evaluation_type", "swd_celex",
    "published_date", "delivered", "note",
]


def _s(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _infer_type(title: str) -> str:
    """Infer evaluation_type from the item title (documented in CODEBOOK.md).

    "fitness check" -> fitness_check; "interim" / "mid-term" ->
    interim_evaluation; anything else (including ex-post evaluations) ->
    evaluation. "refit" is checked for completeness but does not occur in the
    Annex II titles; the refit type is otherwise reserved for curation.
    """
    t = title.lower()
    if "fitness check" in t:
        return "fitness_check"
    if "interim" in t or "mid-term" in t:
        return "interim_evaluation"
    if "refit" in t:
        return "refit"
    return "evaluation"


def main():
    logger = setup_logging("07_evaluations")
    ensure_dirs()
    today = as_of_date()

    agenda = pd.read_csv(config.OUTPUT_DIR / "agenda_items.csv")
    evals = agenda[agenda["source_scope"] == "cwp_annex_ii"].copy()
    evals["evaluation_type"] = evals["title"].fillna("").map(_infer_type)

    # Scaffold the curation worksheet if absent.
    if not config.ANNEX_II_EVALUATIONS_CSV.exists():
        ws = evals[["wp_item_id", "title", "evaluation_type"]].copy()
        ws["swd_celex"] = ""
        ws["published_date"] = ""
        ws["delivered"] = ""
        ws["note"] = ""
        config.MANUAL_DIR.mkdir(parents=True, exist_ok=True)
        ws[WORKSHEET_COLS].to_csv(config.ANNEX_II_EVALUATIONS_CSV, index=False,
                                  encoding="utf-8-sig")
        logger.info(f"Scaffolded evaluation worksheet: "
                    f"{config.ANNEX_II_EVALUATIONS_CSV.name} ({len(ws)} items)")

    # Ingest curated values, defaulting uncoded items to not-yet-delivered.
    # Joined on the stable wp_item_id (see WORKSHEET_COLS note).
    curated = {}
    if config.ANNEX_II_EVALUATIONS_CSV.exists():
        cur = pd.read_csv(config.ANNEX_II_EVALUATIONS_CSV)
        if "wp_item_id" not in cur.columns:
            raise SystemExit(
                f"{config.ANNEX_II_EVALUATIONS_CSV.name} has no wp_item_id "
                "column: it predates the stable-key worksheet format. Delete "
                "it and re-run to scaffold a fresh worksheet."
            )
        for _, r in cur.iterrows():
            curated[_s(r.get("wp_item_id"))] = r

    rows = []
    counter = 0
    for _, item in evals.iterrows():
        counter += 1
        aid = item["agenda_item_id"]
        c = curated.get(_s(item["wp_item_id"]))
        delivered_raw = _s(c.get("delivered")) if c is not None else ""
        delivered = delivered_raw.lower() in ("true", "1", "yes", "y")
        rows.append({
            "evaluation_id": f"EV{counter:04d}",
            "agenda_item_id": aid,
            "evaluation_type": (_s(c.get("evaluation_type")) if c is not None else "")
                                or item["evaluation_type"],
            "swd_celex": _s(c.get("swd_celex")) if c is not None else "",
            "published_date": _s(c.get("published_date")) if c is not None else "",
            "delivered": delivered,
            "as_of_date": today,
        })

    df = pd.DataFrame(rows, columns=EVAL_COLS)
    save_both(df, "evaluations")
    logger.info(f"evaluations: {len(df)} rows "
                f"({int(df['delivered'].sum())} coded as delivered). "
                f"By type: {df['evaluation_type'].value_counts().to_dict()}")
    return df


if __name__ == "__main__":
    main()
