"""
01_parse_ireland.py
Parse the EU&I 2024 Ireland workbook into four tidy tables:
ie_parties, ie_statements, ie_positions, ie_salience.

Covers 13 national parties + 6 independent candidates. Final placement only.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from scripts.utils import setup_logging, ensure_dirs
from scripts.build_tables import build_dataset


def main():
    logger = setup_logging("01_ireland")
    ensure_dirs()
    tables = build_dataset(
        entities=config.IE_ENTITIES,
        workbook=config.IE_WORKBOOK,
        prefix="ie",
        country="IE",
        level="national",
        country_token="Ireland",
        logger=logger,
    )
    print(f"ie_positions: {len(tables['positions'])} rows saved.")
    return tables["positions"]


if __name__ == "__main__":
    main()
