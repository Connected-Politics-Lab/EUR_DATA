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


class TestWorkProgramme:
    """Pin the corrected CWP 2025 annex structure (COM(2025) 45 annexes doc)."""

    def test_total_items(self):
        df = load_csv("work_programme_items.csv")
        assert len(df) == 130, f"Expected 130 WP items, got {len(df)}"

    def test_annex_vocabulary(self):
        """Annexes I, II, IV, V only: the official Annex III (pending
        proposals) is deliberately not extracted."""
        df = load_csv("work_programme_items.csv")
        assert set(df["annex"]) == {"I", "II", "IV", "V"}, (
            f"Unexpected annex vocabulary: {set(df['annex'])}"
        )

    def test_per_annex_counts(self):
        df = load_csv("work_programme_items.csv")
        counts = df["annex"].value_counts().to_dict()
        expected = {"I": 52, "II": 37, "IV": 37, "V": 4}
        assert counts == expected, (
            f"Expected annex counts {expected}, got {counts}"
        )

    def test_type_of_act_null_only_for_annex_ii(self):
        """type_of_act is null exactly for the 37 Annex II rows."""
        df = load_csv("work_programme_items.csv")
        null_annexes = df[df["type_of_act"].isna()]["annex"]
        assert (null_annexes == "II").all() and len(null_annexes) == 37, (
            "type_of_act should be null exactly for the 37 Annex II rows"
        )

    def test_annex_iv_instruments(self):
        """Annex IV withdrawals of pending proposals, by named instrument."""
        df = load_csv("work_programme_items.csv")
        iv = df[df["annex"] == "IV"]["type_of_act"].value_counts().to_dict()
        expected = {"REGULATION": 22, "DIRECTIVE": 10, "DECISION": 4,
                    "RECOMMENDATION": 1}
        assert iv == expected, f"Expected Annex IV {expected}, got {iv}"

    def test_annex_v_instruments(self):
        """Annex V envisaged repeals of acts in force."""
        df = load_csv("work_programme_items.csv")
        v = df[df["annex"] == "V"]["type_of_act"].value_counts().to_dict()
        expected = {"REGULATION": 3, "DECISION": 1}
        assert v == expected, f"Expected Annex V {expected}, got {v}"

    def test_annex_i_act_nature(self):
        df = load_csv("work_programme_items.csv")
        i = df[df["annex"] == "I"]["type_of_act"].value_counts().to_dict()
        expected = {"Non-legislative": 33, "Legislative": 18,
                    "Non-legislative or legislative": 1}
        assert i == expected, f"Expected Annex I {expected}, got {i}"


class TestHearings:
    """Pin the verified hearing schedule (EP adopted calendar + press releases)."""

    def test_per_day_distribution(self):
        df = load_csv("hearings.csv")
        counts = df["hearing_date"].value_counts().to_dict()
        expected = {
            "2024-11-04": 4,
            "2024-11-05": 6,
            "2024-11-06": 6,
            "2024-11-07": 4,
            "2024-11-12": 6,
        }
        assert counts == expected, (
            f"Expected hearing distribution {expected}, got {counts}"
        )

    def test_source_url_fully_populated(self):
        df = load_csv("hearings.csv")
        assert df["source_url"].notna().all(), (
            "Every hearing row should carry its EP press-release source_url"
        )


class TestCommitments:
    """Pin the boilerplate columns on mission_letter_commitments."""

    def test_boilerplate_count(self):
        df = load_csv("mission_letter_commitments.csv")
        actual = int(df["is_boilerplate"].sum())
        assert actual == 515, f"Expected 515 boilerplate rows, got {actual}"

    def test_boilerplate_consistent_with_share_count(self):
        """is_boilerplate must equal (n_letters_sharing_text > 13)."""
        df = load_csv("mission_letter_commitments.csv")
        derived = df["n_letters_sharing_text"] > 13
        assert (df["is_boilerplate"] == derived).all(), (
            "is_boilerplate inconsistent with n_letters_sharing_text > 13"
        )

    def test_commitment_short_max_length(self):
        df = load_csv("mission_letter_commitments.csv")
        max_len = int(df["commitment_short"].str.len().max())
        assert max_len <= 100, (
            f"commitment_short should be <=100 chars, longest is {max_len}"
        )


class TestCommissionerCoding:
    """Pin the corrected party coding of the College."""

    def test_epp_count(self):
        df = load_csv("commissioners.csv")
        epp = int((df["ep_party_group"] == "EPP").sum())
        assert epp == 14, f"Expected 14 EPP commissioners, got {epp}"

    def test_kadis_independent(self):
        """Kadis is a non-partisan technocrat: Independent/Independent."""
        df = load_csv("commissioners.csv")
        kadis = df[df["last_name"] == "Kadis"]
        assert len(kadis) == 1, "Expected exactly one Kadis row"
        assert kadis.iloc[0]["ep_party_group"] == "Independent"
        assert kadis.iloc[0]["national_party"] == "Independent"


class TestInvestitureGroups:
    """Pin the corrected ep_party_group_full mapping."""

    def test_full_name_never_equals_short_code(self):
        df = load_csv("investiture_vote.csv")
        same = df["ep_party_group_full"] == df["ep_party_group"]
        assert not same.any(), (
            f"{int(same.sum())} rows have ep_party_group_full equal to the "
            "short code"
        )

    def test_full_name_covers_all_groups(self):
        df = load_csv("investiture_vote.csv")
        assert df["ep_party_group_full"].notna().all(), (
            "ep_party_group_full has missing values"
        )
        # Each short code maps to exactly one full name
        mapping = df.groupby("ep_party_group")["ep_party_group_full"].nunique()
        assert (mapping == 1).all(), (
            f"Short codes with multiple full names: "
            f"{mapping[mapping > 1].to_dict()}"
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
