"""
test_counts.py
Validate row counts, the coding scale, and per-entity coverage.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest
import config

OUTPUT_DIR = config.OUTPUT_DIR
PREFIXES = ["ie", "eu"]
EXPECTED_ENTITIES = {"ie": config.IE_EXPECTED_ENTITIES, "eu": config.EU_EXPECTED_ENTITIES}


def load_csv(filename: str) -> pd.DataFrame:
    path = OUTPUT_DIR / filename
    if not path.exists():
        pytest.skip(f"{filename} not found")
    return pd.read_csv(path)


class TestRowCounts:

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_entity_count(self, prefix):
        df = load_csv(f"{prefix}_parties.csv")
        assert len(df) == EXPECTED_ENTITIES[prefix], (
            f"Expected {EXPECTED_ENTITIES[prefix]} {prefix} entities, got {len(df)}"
        )

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_statement_count(self, prefix):
        df = load_csv(f"{prefix}_statements.csv")
        assert len(df) == config.N_STATEMENTS, (
            f"Expected {config.N_STATEMENTS} statements, got {len(df)}"
        )

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_positions_is_entities_times_statements(self, prefix):
        parties = load_csv(f"{prefix}_parties.csv")
        positions = load_csv(f"{prefix}_positions.csv")
        expected = len(parties) * config.N_STATEMENTS
        assert len(positions) == expected, (
            f"Expected {expected} positions, got {len(positions)}"
        )

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_every_entity_has_full_statement_set(self, prefix):
        positions = load_csv(f"{prefix}_positions.csv")
        per_entity = positions.groupby("party_id").size()
        off = per_entity[per_entity != config.N_STATEMENTS]
        assert off.empty, f"{prefix} entities without {config.N_STATEMENTS} positions: {dict(off)}"

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_salience_at_most_three_per_entity(self, prefix):
        salience = load_csv(f"{prefix}_salience.csv")
        per_entity = salience.groupby("party_id").size()
        too_many = per_entity[per_entity > 3]
        assert too_many.empty, f"{prefix} entities with >3 salience picks: {dict(too_many)}"


class TestCodingScale:

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_position_labels_valid(self, prefix):
        df = load_csv(f"{prefix}_positions.csv")
        labels = set(df["position_label"].dropna().unique())
        invalid = labels - config.VALID_POSITION_LABELS
        assert not invalid, f"{prefix} invalid position labels: {invalid}"

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_position_numeric_in_range(self, prefix):
        df = load_csv(f"{prefix}_positions.csv")
        vals = set(df["position_numeric"].dropna().unique())
        assert vals <= {-2, -1, 0, 1, 2}, f"{prefix} numeric out of range: {vals}"

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_numeric_matches_label(self, prefix):
        df = load_csv(f"{prefix}_positions.csv")
        for _, row in df.iterrows():
            label = row["position_label"]
            if pd.isna(label):
                continue
            expected = config.POSITION_SCALE.get(label)
            actual = row["position_numeric"]
            if expected is None:
                assert pd.isna(actual), f"{label!r} should map to NA, got {actual}"
            else:
                assert actual == expected, (
                    f"{label!r} should map to {expected}, got {actual}"
                )

    @pytest.mark.parametrize("prefix", PREFIXES)
    def test_salience_rank_valid(self, prefix):
        df = load_csv(f"{prefix}_salience.csv")
        ranks = set(df["salience_rank"].dropna().unique())
        assert ranks <= {1, 2, 3}, f"{prefix} salience ranks out of range: {ranks}"
