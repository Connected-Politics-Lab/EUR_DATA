"""
test_schemas.py
Validate output CSV schemas: column names, primary-key uniqueness, and that
no column is unexpectedly all-null.
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
    "{p}_parties.csv": [
        "party_id", "sheet_name", "acronym", "full_name", "entity_type",
        "affiliation", "constituency", "country", "level",
    ],
    "{p}_statements.csv": [
        "statement_id", "statement_text", "is_country_specific",
    ],
    "{p}_positions.csv": [
        "position_id", "party_id", "statement_id", "position_label",
        "position_numeric", "source_type", "text_snippet", "source_link",
    ],
    "{p}_salience.csv": [
        "salience_id", "party_id", "salience_rank", "statement_id",
        "statement_text",
    ],
}

PREFIXES = ["ie", "eu"]

# Columns allowed to be entirely empty (structurally optional / sparse).
ALLOWED_NULL = {
    "acronym",          # blank for independent candidates
    "affiliation",      # parties / EU families have none
    "constituency",     # parties / EU families have none
    "source_type",      # blank when position is "No opinion"
    "text_snippet",
    "source_link",
}

# Primary-key column per table stem.
PRIMARY_KEY = {
    "parties": "party_id",
    "statements": "statement_id",
    "positions": "position_id",
    "salience": "salience_id",
}


def load_csv(filename: str) -> pd.DataFrame:
    path = OUTPUT_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not found (pipeline may not have run yet)")
    return pd.read_csv(path)


def _all_files():
    return [tmpl.format(p=p) for p in PREFIXES for tmpl in SCHEMAS]


class TestSchemas:

    @pytest.mark.parametrize("prefix", PREFIXES)
    @pytest.mark.parametrize("template,cols", list(SCHEMAS.items()))
    def test_columns_present(self, prefix, template, cols):
        df = load_csv(template.format(p=prefix))
        missing = set(cols) - set(df.columns)
        assert not missing, f"{template.format(p=prefix)} missing columns: {missing}"

    @pytest.mark.parametrize("filename", _all_files())
    def test_no_unexpected_all_null_columns(self, filename):
        df = load_csv(filename)
        if df.empty:
            pytest.skip(f"{filename} is empty")
        all_null = {c for c in df.columns if df[c].isna().all()}
        unexpected = all_null - ALLOWED_NULL
        assert not unexpected, f"{filename} has unexpected all-null columns: {unexpected}"

    @pytest.mark.parametrize("filename", _all_files())
    def test_no_duplicate_primary_keys(self, filename):
        df = load_csv(filename)
        stem = filename.split("_", 1)[1].replace(".csv", "")
        pk = PRIMARY_KEY[stem]
        dupes = df[df[pk].duplicated()]
        assert dupes.empty, f"{filename} has {len(dupes)} duplicate {pk} values"


class TestForeignKeys:
    """Referential integrity between fact and dimension tables."""

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_positions_party_ids_valid(self, prefix):
        parties = load_csv(f"{prefix}_parties.csv")
        positions = load_csv(f"{prefix}_positions.csv")
        invalid = set(positions["party_id"]) - set(parties["party_id"])
        assert not invalid, f"{prefix}_positions party_ids not in parties: {invalid}"

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_positions_statement_ids_valid(self, prefix):
        statements = load_csv(f"{prefix}_statements.csv")
        positions = load_csv(f"{prefix}_positions.csv")
        invalid = set(positions["statement_id"]) - set(statements["statement_id"])
        assert not invalid, f"{prefix}_positions statement_ids not in statements: {invalid}"

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_salience_ids_valid(self, prefix):
        parties = load_csv(f"{prefix}_parties.csv")
        statements = load_csv(f"{prefix}_statements.csv")
        salience = load_csv(f"{prefix}_salience.csv")
        bad_party = set(salience["party_id"]) - set(parties["party_id"])
        assert not bad_party, f"{prefix}_salience party_ids not in parties: {bad_party}"
        matched = salience["statement_id"].dropna()
        bad_stmt = set(matched) - set(statements["statement_id"])
        assert not bad_stmt, f"{prefix}_salience statement_ids not in statements: {bad_stmt}"
