"""
05_match_annex_i.py
Link Annex I new initiatives to the procedures that deliver them.

Annex I items have NO procedure number until the Commission tables a proposal,
and in the source data their `title` is only a short policy theme (e.g.
"Competitiveness and Decarbonisation"), so reliable automated title matching is
not possible. The dependable path is a curated override file; this script:

  1. scaffolds data/manual/annex_i_overrides.csv (pre-filled with the unmatched
     Annex I items) if it does not yet exist,
  2. ingests any curated links into procedure_references and fetches their
     status into the procedure_status time series, and
  3. (opt-in, AGENDA_FUZZY=1) writes rapidfuzz title-match *suggestions* to
     data/manual/annex_i_match_candidates.csv for human review - never straight
     into the dataset.

Network access only for ingested overrides and the opt-in fuzzy pass.
"""

import os
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, save_both, as_of_date, fetch_json
from scripts.refs import to_process_id
from scripts.status_fetch import status_row, STATUS_COLS

OVERRIDE_COLS = ["wp_item_id", "title", "interinstitutional_ref", "com_reference", "note"]


def _s(v) -> str:
    if v is None or (isinstance(v, float) and pd.isna(v)):
        return ""
    return str(v).strip()


def _scaffold_overrides(annex_i: pd.DataFrame, logger):
    """Write a ready-to-fill worksheet of Annex I items if none exists."""
    if config.ANNEX_I_OVERRIDES_CSV.exists():
        return
    template = annex_i[["wp_item_id", "title"]].copy()
    template["interinstitutional_ref"] = ""
    template["com_reference"] = ""
    template["note"] = ""
    config.MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    template[OVERRIDE_COLS].to_csv(config.ANNEX_I_OVERRIDES_CSV, index=False,
                                   encoding="utf-8-sig")
    logger.info(f"Scaffolded override worksheet: {config.ANNEX_I_OVERRIDES_CSV.name} "
                f"({len(template)} Annex I items to curate)")


def _append_refs_and_status(links, agenda, logger, today):
    """links: list of (agenda_item_id, ref, com, confidence). Appends to both tables."""
    if not links:
        return 0

    refs = pd.read_csv(config.OUTPUT_DIR / "procedure_references.csv")
    next_n = (refs["procedure_ref_id"].str.extract(r"(\d+)").astype(int).max().iloc[0]
              if len(refs) else 0)

    new_refs, new_status = [], []
    agenda_idx = agenda.set_index("agenda_item_id")
    for aid, ref, com, conf in links:
        next_n += 1
        ref_id = f"PR{next_n:04d}"
        ptype = ref.split("(")[-1].rstrip(")") if "(" in ref else ""
        ref_row = {
            "procedure_ref_id": ref_id, "agenda_item_id": aid,
            "interinstitutional_ref": ref, "process_id_ep": to_process_id(ref),
            "procedure_type": ptype, "com_reference": com, "celex": "",
            "extraction_method": "manual_annex_i", "match_confidence": conf,
        }
        new_refs.append(ref_row)
        timing = agenda_idx.loc[aid, "indicative_timing"] if aid in agenda_idx.index else ""
        new_status.append(status_row(ref_row, timing, today))

    refs = pd.concat([refs, pd.DataFrame(new_refs)], ignore_index=True)
    save_both(refs, "procedure_references")

    status_path = config.OUTPUT_DIR / "procedure_status.csv"
    if status_path.exists():
        status = pd.read_csv(status_path)
        status = pd.concat([status, pd.DataFrame(new_status, columns=STATUS_COLS)],
                           ignore_index=True)
        status = status.drop_duplicates(subset="status_id", keep="last")
        status["on_time"] = status["on_time"].astype("Int64")
        save_both(status, "procedure_status")
    logger.info(f"Ingested {len(links)} curated Annex I link(s).")
    return len(links)


def _fuzzy_candidates(annex_i, logger, today):
    """Opt-in rapidfuzz suggestions against fetched corpus titles (review only)."""
    from rapidfuzz import process, fuzz

    def _en_title(proc):
        t = proc.get("process_title")
        if isinstance(t, dict):
            return str(t.get("en") or next(iter(t.values()), ""))
        if isinstance(t, list):
            return str(t[0] if t else "")
        return str(t or "")

    corpus = pd.read_csv(config.OUTPUT_DIR / "term_legislative_output.csv")
    titles = {}
    logger.info(f"Fetching {len(corpus)} corpus titles for fuzzy matching...")
    for _, c in corpus.iterrows():
        data = fetch_json(f"{config.EP_API_BASE}/procedures/{c['process_id_ep']}",
                          params={"language": "en"})
        proc = (data or {}).get("data") if data else None
        proc = proc[0] if isinstance(proc, list) and proc else None
        if proc:
            t = _en_title(proc)
            if t.strip():
                titles[c["interinstitutional_ref"]] = t

    rows = []
    for _, item in annex_i.iterrows():
        title = _s(item.get("title"))
        if not title or not titles:
            continue
        match = process.extractOne(title, titles, scorer=fuzz.token_set_ratio)
        if match:
            value, score, ref = match
            # similarity_score is a raw token-set ratio (reaches 1.0 on shared
            # tokens alone); it is NOT a validated match confidence.
            rows.append({"wp_item_id": item["wp_item_id"], "annex_i_title": title,
                         "candidate_ref": ref, "candidate_title": value,
                         "similarity_score": round(score / 100, 3), "as_of_date": today})
    cand = pd.DataFrame(rows).sort_values("similarity_score", ascending=False)
    config.MANUAL_DIR.mkdir(parents=True, exist_ok=True)
    cand.to_csv(config.MANUAL_DIR / "annex_i_match_candidates.csv", index=False,
                encoding="utf-8-sig")
    logger.warning(
        "Candidates are a REVIEW AID for manual curation, NOT dataset values. "
        "Brand-name initiatives (e.g. 'EU Space Act') do not reliably match the "
        "formal EP procedure titles, so scores are low and unverified - confirm "
        "each by hand before adding it to annex_i_overrides.csv.")
    return cand


def main():
    logger = setup_logging("05_annex_i")
    ensure_dirs()
    today = as_of_date()

    agenda = pd.read_csv(config.OUTPUT_DIR / "agenda_items.csv")
    annex_i = agenda[agenda["source_scope"] == "cwp_annex_i"].copy()

    _scaffold_overrides(annex_i, logger)

    # Ingest curated links.
    links = []
    if config.ANNEX_I_OVERRIDES_CSV.exists():
        ov = pd.read_csv(config.ANNEX_I_OVERRIDES_CSV)
        by_wp = dict(zip(agenda["wp_item_id"].astype(str), agenda["agenda_item_id"]))
        for _, r in ov.iterrows():
            ref = _s(r.get("interinstitutional_ref"))
            aid = by_wp.get(_s(r.get("wp_item_id")))
            if ref and aid:
                links.append((aid, ref, _s(r.get("com_reference")), 1.0))
    n_linked = _append_refs_and_status(links, agenda, logger, today)

    if os.environ.get("AGENDA_FUZZY") == "1":
        _fuzzy_candidates(annex_i, logger, today)

    logger.info(f"Annex I: {len(annex_i)} items, {n_linked} curated link(s) ingested, "
                f"{len(annex_i) - n_linked} still unmatched.")
    return annex_i


if __name__ == "__main__":
    main()
