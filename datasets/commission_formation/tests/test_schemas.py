"""
test_schemas.py
Validate output CSV schemas: column names, types, no all-null columns.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest
import config

OUTPUT_DIR = config.OUTPUT_DIR


# Expected schemas: {filename: [required_columns]}
SCHEMAS = {
    "commissioners.csv": [
        "commissioner_id", "full_name", "last_name", "first_name",
        "country", "country_name", "portfolio_title", "role",
        "ep_party_group", "national_party", "gender",
        "dgs_responsible", "mission_letter_url", "hearing_date", "profile_url",
    ],
    "mission_letter_commitments.csv": [
        "commitment_id", "commissioner_id", "commissioner_name",
        "portfolio_title", "commitment_text", "commitment_short",
        "section_heading", "commitment_type", "extraction_method",
        "confidence", "page_number", "raw_paragraph",
    ],
    "hearings.csv": [
        "hearing_id", "commissioner_id", "commissioner_name",
        "hearing_date", "committees_responsible", "committees_associated",
        "outcome", "evaluation_letter_url", "written_questions_url", "video_url",
    ],
    "investiture_vote.csv": [
        "mep_id", "full_name", "last_name", "first_name",
        "country", "country_name", "ep_party_group", "ep_party_group_full",
        "national_party", "vote", "vote_numeric", "vote_date",
    ],
    "work_programme_items.csv": [
        "item_id", "annex", "item_number", "title", "description",
        "policy_area", "type_of_act", "indicative_timing",
    ],
    "formation_timeline.csv": [
        "event_id", "date", "event_name", "event_description",
        "event_type", "institution", "document_url",
    ],
}


def load_csv(filename: str) -> pd.DataFrame:
    """Load a CSV from the output directory."""
    path = OUTPUT_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not found (pipeline may not have run yet)")
    return pd.read_csv(path)


class TestSchemas:
    """Test that all output CSVs have the expected columns."""

    @pytest.mark.parametrize("filename,expected_cols", list(SCHEMAS.items()))
    def test_columns_present(self, filename, expected_cols):
        df = load_csv(filename)
        missing = set(expected_cols) - set(df.columns)
        assert not missing, f"{filename} missing columns: {missing}"

    @pytest.mark.parametrize("filename", list(SCHEMAS.keys()))
    def test_no_all_null_columns(self, filename):
        df = load_csv(filename)
        if df.empty:
            pytest.skip(f"{filename} is empty")
        all_null = [col for col in df.columns if df[col].isna().all()]
        # Allow URL columns and enrichment columns to be all null
        # (enrichment via external API may fail due to rate limits / 403s)
        allowed_null = {c for c in all_null
                        if "url" in c.lower()
                        or c in ("national_party",)}
        non_allowed_null = set(all_null) - allowed_null
        assert not non_allowed_null, (
            f"{filename} has all-null non-enrichment columns: {non_allowed_null}"
        )

    @pytest.mark.parametrize("filename", list(SCHEMAS.keys()))
    def test_no_duplicate_ids(self, filename):
        df = load_csv(filename)
        id_cols = [c for c in df.columns if c.endswith("_id") and c != "commissioner_id"]
        if not id_cols:
            pytest.skip(f"No ID column found in {filename}")
        # Use the first *_id column as the primary key
        primary_id = id_cols[0]
        # For investiture_vote, mep_id may not be unique if MEP voted multiple times
        if filename == "investiture_vote.csv" and primary_id == "mep_id":
            return
        dupes = df[df[primary_id].duplicated()]
        assert dupes.empty, (
            f"{filename} has {len(dupes)} duplicate {primary_id} values"
        )


class TestDataTypes:
    """Test that key columns have correct data types."""

    def test_vote_numeric_is_numeric(self):
        df = load_csv("investiture_vote.csv")
        assert pd.api.types.is_numeric_dtype(df["vote_numeric"]), (
            "vote_numeric should be numeric"
        )

    def test_vote_values_valid(self):
        df = load_csv("investiture_vote.csv")
        valid_votes = {"for", "against", "abstain", "did_not_vote"}
        actual = set(df["vote"].unique())
        invalid = actual - valid_votes
        assert not invalid, f"Invalid vote values: {invalid}"

    def test_dates_valid_format(self):
        df = load_csv("formation_timeline.csv")
        # Check date format YYYY-MM-DD
        for date_str in df["date"]:
            assert len(str(date_str)) == 10, f"Invalid date format: {date_str}"
            pd.to_datetime(date_str, format="%Y-%m-%d")

    def test_commissioner_gender_valid(self):
        df = load_csv("commissioners.csv")
        valid = {"M", "F"}
        actual = set(df["gender"].unique())
        invalid = actual - valid
        assert not invalid, f"Invalid gender values: {invalid}"

    def test_hearing_outcome_valid(self):
        df = load_csv("hearings.csv")
        valid = {"approved", "rejected", "pending", "second_hearing"}
        actual = set(df["outcome"].unique())
        invalid = actual - valid
        assert not invalid, f"Invalid outcome values: {invalid}"
