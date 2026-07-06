"""
test_counts.py
Validate row counts and deterministic invariants. Counts derived from the
(static) sibling work-programme are exact; the live EP corpus is range-checked.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest
import config

OUTPUT_DIR = config.OUTPUT_DIR


def load_csv(filename: str) -> pd.DataFrame:
    path = OUTPUT_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not found")
    return pd.read_csv(path)


class TestDeterministicCounts:
    """These derive from the static sibling CSVs, so they are exact."""

    def test_agenda_items_total(self):
        df = load_csv("agenda_items.csv")
        # 130 CWP items + 63 legislative mission-letter commitments.
        assert len(df) == 193, f"Expected 193 agenda items, got {len(df)}"

    def test_agenda_items_by_scope(self):
        df = load_csv("agenda_items.csv")
        counts = df["source_scope"].value_counts().to_dict()
        assert counts.get("cwp_annex_i") == 52
        assert counts.get("cwp_annex_ii") == 37
        assert counts.get("cwp_annex_iv") == 37
        assert counts.get("cwp_annex_v") == 4
        assert counts.get("mission_letter") == 63

    def test_procedure_refs_all_have_process_id(self):
        df = load_csv("procedure_references.csv")
        assert len(df) >= 37, f"Expected >=37 parsed refs, got {len(df)}"
        assert df["process_id_ep"].notna().all(), "Some refs lack a process_id_ep"

    def test_evaluations_cover_annex_ii(self):
        df = load_csv("evaluations.csv")
        assert len(df) == 37, f"Expected 37 evaluations (Annex II), got {len(df)}"


class TestLiveCorpus:
    """The EP corpus grows over the term, so range-check rather than fix."""

    def test_term_output_nontrivial(self):
        df = load_csv("term_legislative_output.csv")
        assert len(df) >= 100, f"Expected a sizeable corpus, got {len(df)}"

    def test_is_in_agenda_subset(self):
        df = load_csv("term_legislative_output.csv")
        assert df["is_in_agenda"].sum() >= 0  # flag present and boolean
        assert df["is_in_agenda"].dropna().isin([True, False]).all()


class TestStatusSnapshot:

    def test_status_rows_match_refs_per_snapshot(self):
        refs = load_csv("procedure_references.csv")
        status = load_csv("procedure_status.csv")
        # Each snapshot should cover every reference exactly once.
        per_snapshot = status.groupby("as_of_date")["procedure_ref_id"].nunique()
        assert (per_snapshot == len(refs)).all(), (
            f"Snapshot coverage != {len(refs)} refs: {per_snapshot.to_dict()}"
        )

    def test_delivered_consistent_with_status(self):
        status = load_csv("procedure_status.csv")
        delivered = status[status["delivered"] == True]  # noqa: E712
        bad = set(delivered["status"].unique()) - {"adopted", "in_force"}
        assert not bad, f"delivered=True with non-delivered status: {bad}"
