"""
test_schemas.py
Validate output CSV schemas: column presence, primary-key uniqueness, enum
domains, and that no column is unexpectedly all-null.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest
import config

OUTPUT_DIR = config.OUTPUT_DIR

SCHEMAS = {
    "agenda_items.csv": [
        "agenda_item_id", "source_scope", "wp_item_id", "commitment_id",
        "title", "policy_area", "indicative_timing", "expected_act_type",
    ],
    "procedure_references.csv": [
        "procedure_ref_id", "agenda_item_id", "interinstitutional_ref",
        "process_id_ep", "procedure_type", "com_reference", "celex",
        "extraction_method", "match_confidence",
    ],
    "procedure_status.csv": [
        "status_id", "procedure_ref_id", "agenda_item_id", "as_of_date",
        "status", "ep_stage_code", "latest_event_type", "latest_event_date",
        "proposed_date", "delivered", "on_time", "withdrawn",
    ],
    "term_legislative_output.csv": [
        "proc_output_id", "interinstitutional_ref", "process_id_ep",
        "procedure_type", "year", "is_in_agenda", "as_of_date",
    ],
    "evaluations.csv": [
        "evaluation_id", "agenda_item_id", "evaluation_type", "swd_celex",
        "published_date", "delivered", "as_of_date",
    ],
}

PRIMARY_KEY = {
    "agenda_items.csv": "agenda_item_id",
    "procedure_references.csv": "procedure_ref_id",
    "procedure_status.csv": "status_id",
    "term_legislative_output.csv": "proc_output_id",
    "evaluations.csv": "evaluation_id",
}

# Columns that may legitimately be entirely empty (sparse / awaiting curation).
ALLOWED_NULL = {
    "commitment_id", "wp_item_id", "policy_area", "indicative_timing",
    "expected_act_type", "com_reference", "celex", "ep_stage_code",
    "latest_event_type", "latest_event_date", "proposed_date",
    "swd_celex", "published_date",
}


def load_csv(filename: str) -> pd.DataFrame:
    path = OUTPUT_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not found (pipeline may not have run yet)")
    return pd.read_csv(path)


class TestSchemas:

    @pytest.mark.parametrize("filename,cols", list(SCHEMAS.items()))
    def test_columns_present(self, filename, cols):
        df = load_csv(filename)
        missing = set(cols) - set(df.columns)
        assert not missing, f"{filename} missing columns: {missing}"

    @pytest.mark.parametrize("filename", list(SCHEMAS))
    def test_no_unexpected_all_null(self, filename):
        df = load_csv(filename)
        if df.empty:
            pytest.skip(f"{filename} is empty")
        all_null = {c for c in df.columns if df[c].isna().all()}
        unexpected = all_null - ALLOWED_NULL
        assert not unexpected, f"{filename} has unexpected all-null columns: {unexpected}"

    @pytest.mark.parametrize("filename,pk", list(PRIMARY_KEY.items()))
    def test_primary_key_unique(self, filename, pk):
        df = load_csv(filename)
        dupes = df[df[pk].duplicated()]
        assert dupes.empty, f"{filename} has {len(dupes)} duplicate {pk} values"


class TestEnums:

    def test_source_scope_domain(self):
        df = load_csv("agenda_items.csv")
        invalid = set(df["source_scope"].unique()) - set(config.SOURCE_SCOPES)
        assert not invalid, f"Invalid source_scope values: {invalid}"

    def test_status_domain(self):
        df = load_csv("procedure_status.csv")
        invalid = set(df["status"].dropna().unique()) - set(config.ALL_STATUSES)
        assert not invalid, f"Invalid status values: {invalid}"

    def test_procedure_type_domain(self):
        df = load_csv("procedure_references.csv")
        invalid = set(df["procedure_type"].dropna().unique()) - set(config.PROCEDURE_TYPE_TOKENS)
        assert not invalid, f"Invalid procedure_type values: {invalid}"

    def test_evaluation_type_domain(self):
        df = load_csv("evaluations.csv")
        invalid = set(df["evaluation_type"].dropna().unique()) - set(config.EVALUATION_TYPES)
        assert not invalid, f"Invalid evaluation_type values: {invalid}"

    def test_on_time_domain(self):
        df = load_csv("procedure_status.csv")
        invalid = set(df["on_time"].dropna().unique()) - {-1, 0, 1}
        assert not invalid, f"Invalid on_time values: {invalid}"

    def test_as_of_date_parses(self):
        df = load_csv("procedure_status.csv")
        for d in df["as_of_date"].dropna().unique():
            pd.to_datetime(str(d), format="%Y-%m-%d")
