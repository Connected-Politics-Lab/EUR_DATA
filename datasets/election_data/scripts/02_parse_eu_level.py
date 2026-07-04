"""
02_parse_eu_level.py
Parse the EU&I 2024 general codesheet workbook into four tidy tables:
eu_parties, eu_statements, eu_positions, eu_salience.

Covers 10 EU-level political party families. Final placement only.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from scripts.utils import setup_logging, ensure_dirs
from scripts.build_tables import build_dataset


def main():
    logger = setup_logging("02_eu_level")
    ensure_dirs()
    tables = build_dataset(
        entities=config.EU_ENTITIES,
        workbook=config.EU_WORKBOOK,
        prefix="eu",
        country="EU",
        level="european",
        country_token="EU Member States",
        logger=logger,
        # Statement 24 contains "EU Member States" with identical wording in
        # every country edition (verified against the Irish catalogue), so the
        # token heuristic false-positives on it.
        non_templated=frozenset({24}),
    )
    print(f"eu_positions: {len(tables['positions'])} rows saved.")
    return tables["positions"]


if __name__ == "__main__":
    main()
