"""
test_counts.py
Validate row counts and cross-table consistency.
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


class TestRowCounts:
    """Validate expected row count ranges."""

    def test_commissioners_count(self):
        df = load_csv("commissioners.csv")
        assert len(df) == 27, f"Expected 27 commissioners, got {len(df)}"

    def test_hearings_count(self):
        df = load_csv("hearings.csv")
        assert len(df) == 26, f"Expected 26 hearings, got {len(df)}"

    def test_investiture_vote_count(self):
        df = load_csv("investiture_vote.csv")
        assert 680 <= len(df) <= 720, (
            f"Expected 680-720 MEP votes, got {len(df)}"
        )

    def test_commitments_count(self):
        df = load_csv("mission_letter_commitments.csv")
        assert len(df) >= 200, (
            f"Expected >=200 commitments, got {len(df)}"
        )

    def test_work_programme_count(self):
        df = load_csv("work_programme_items.csv")
        assert len(df) >= 30, (
            f"Expected >=30 work programme items, got {len(df)}"
        )

    def test_timeline_count(self):
        df = load_csv("formation_timeline.csv")
        assert len(df) >= 10, (
            f"Expected >=10 timeline events, got {len(df)}"
        )


class TestVoteTotals:
    """Validate investiture vote arithmetic."""

    def test_vote_for_count(self):
        df = load_csv("investiture_vote.csv")
        actual = (df["vote"] == "for").sum()
        expected = config.INVESTITURE_EXPECTED["for"]
        assert actual == expected, (
            f"Expected {expected} 'for' votes, got {actual}"
        )

    def test_vote_against_count(self):
        df = load_csv("investiture_vote.csv")
        actual = (df["vote"] == "against").sum()
        expected = config.INVESTITURE_EXPECTED["against"]
        assert actual == expected, (
            f"Expected {expected} 'against' votes, got {actual}"
        )

    def test_vote_abstain_count(self):
        df = load_csv("investiture_vote.csv")
        actual = (df["vote"] == "abstain").sum()
        expected = config.INVESTITURE_EXPECTED["abstain"]
        assert actual == expected, (
            f"Expected {expected} 'abstain' votes, got {actual}"
        )


class TestCrossTableConsistency:
    """Validate foreign key relationships between tables."""

    def test_hearing_commissioner_ids_valid(self):
        """All hearing commissioner_ids should exist in commissioners table."""
        hearings = load_csv("hearings.csv")
        commissioners = load_csv("commissioners.csv")
        valid_ids = set(commissioners["commissioner_id"])
        hearing_ids = set(hearings["commissioner_id"])
        invalid = hearing_ids - valid_ids
        assert not invalid, (
            f"Hearing commissioner_ids not in commissioners: {invalid}"
        )

    def test_commitment_commissioner_ids_valid(self):
        """All commitment commissioner_ids should exist in commissioners table."""
        commitments = load_csv("mission_letter_commitments.csv")
        if commitments.empty:
            pytest.skip("No commitments")
        commissioners = load_csv("commissioners.csv")
        valid_ids = set(commissioners["commissioner_id"])
        commitment_ids = set(commitments["commissioner_id"])
        invalid = commitment_ids - valid_ids
        assert not invalid, (
            f"Commitment commissioner_ids not in commissioners: {invalid}"
        )

    def test_all_countries_have_commissioner(self):
        """All 27 EU member states should have a commissioner."""
        commissioners = load_csv("commissioners.csv")
        countries = set(commissioners["country"])
        expected = set(config.COUNTRY_NAMES.keys())
        missing = expected - countries
        assert not missing, (
            f"Countries without commissioner: {missing}"
        )

    def test_commissioner_countries_valid(self):
        """All commissioner countries should be valid EU-27 codes."""
        commissioners = load_csv("commissioners.csv")
        valid = set(config.COUNTRY_NAMES.keys())
        actual = set(commissioners["country"])
        invalid = actual - valid
        assert not invalid, (
            f"Invalid country codes: {invalid}"
        )
