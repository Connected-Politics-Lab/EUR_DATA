"""
Shared table-assembly logic for the euandi 2024 dataset.

Both parse steps (01 Ireland, 02 EU-level) call build_dataset() with their
curated entity list and source workbook. It produces four tidy tables -
parties, statements, positions, salience - and writes each as CSV + XLSX.

Only the FINAL (calibrated) placement is retained, per dataset scope.
"""

import re
import sys
from pathlib import Path
from typing import Dict, List

import pandas as pd

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config
from scripts.utils import (
    save_both,
    read_euandi_sheet,
    build_statement_lookup,
    match_salience_statement,
)

# Standard column orders.
PARTIES_COLS = [
    "party_id", "sheet_name", "acronym", "full_name", "entity_type",
    "affiliation", "constituency", "country", "level",
]
STATEMENTS_COLS = ["statement_id", "statement_text", "is_country_specific"]
POSITIONS_COLS = [
    "position_id", "party_id", "statement_id", "position_label",
    "position_numeric", "source_type", "text_snippet", "source_link",
]
SALIENCE_COLS = [
    "salience_id", "party_id", "salience_rank", "statement_id", "statement_text",
]


def _is_country_specific(text: str, token: str) -> bool:
    """Heuristic flag: statement was templated with the country/region name."""
    return bool(re.search(rf"\b{re.escape(token)}\b", text, re.IGNORECASE))


def build_dataset(entities: List[Dict], workbook: Path, prefix: str,
                  country: str, level: str, country_token: str,
                  logger, non_templated: frozenset = frozenset()) -> Dict[str, pd.DataFrame]:
    """
    Build and save the four tables for one dataset.

    prefix        - output filename prefix and id stub ("ie" / "eu")
    country/level - constant dimension values for every entity
    country_token - word marking a country-templated statement
    non_templated - statement ids exempt from the token heuristic (statements
                    that contain the token with identical wording in every
                    country edition, i.e. heuristic false positives)
    Returns a dict of the four DataFrames.
    """
    tag = prefix.upper()

    parties_rows = []
    positions_rows = []
    salience_rows = []
    statements_catalogue = None

    pos_counter = 0
    sal_counter = 0

    for ent in entities:
        sheet = ent["sheet_name"]
        data = read_euandi_sheet(workbook, sheet)
        statements = data["statements"]

        if len(statements) != config.N_STATEMENTS:
            logger.warning(
                f"{sheet!r}: expected {config.N_STATEMENTS} statements, "
                f"got {len(statements)}"
            )

        # The statement battery is shared across all sheets in a dataset; build
        # the catalogue once from the first entity and reuse its ids.
        if statements_catalogue is None:
            statements_catalogue = [
                {
                    "statement_id": s["statement_num"],
                    "statement_text": s["statement_text"],
                    "is_country_specific": (
                        s["statement_num"] not in non_templated
                        and _is_country_specific(
                            s["statement_text"], country_token
                        )
                    ),
                }
                for s in statements
            ]
        lookup = build_statement_lookup(statements)

        # Entity (party) row.
        parties_rows.append({
            "party_id": ent["party_id"],
            "sheet_name": sheet,
            "acronym": ent.get("acronym", ""),
            "full_name": ent["full_name"],
            "entity_type": ent.get("entity_type", "eu_party_family"),
            "affiliation": ent.get("affiliation", ""),
            "constituency": ent.get("constituency", ""),
            "country": country,
            "level": level,
        })

        # Position rows (final placement only).
        for s in statements:
            pos_counter += 1
            label = s["position_label"]
            numeric = config.POSITION_SCALE.get(label, None)
            positions_rows.append({
                "position_id": f"{tag}P{pos_counter:04d}",
                "party_id": ent["party_id"],
                "statement_id": s["statement_num"],
                "position_label": label,
                "position_numeric": numeric,
                "source_type": s["source_type"],
                "text_snippet": s["text_snippet"],
                "source_link": s["source_link"],
            })

        # Salience rows (top-3 most salient statements).
        for sal in data["salience"]:
            sal_counter += 1
            stmt_id = match_salience_statement(sal["statement_text"], lookup)
            if stmt_id is None:
                logger.warning(
                    f"{sheet!r}: salience rank {sal['salience_rank']} text did "
                    f"not match any statement"
                )
            salience_rows.append({
                "salience_id": f"{tag}S{sal_counter:04d}",
                "party_id": ent["party_id"],
                "salience_rank": sal["salience_rank"],
                "statement_id": stmt_id,
                "statement_text": sal["statement_text"],
            })

    parties = pd.DataFrame(parties_rows, columns=PARTIES_COLS)
    statements_df = pd.DataFrame(statements_catalogue, columns=STATEMENTS_COLS)
    positions = pd.DataFrame(positions_rows, columns=POSITIONS_COLS)
    salience = pd.DataFrame(salience_rows, columns=SALIENCE_COLS)

    # Nullable integer dtypes so "No opinion"/unmatched stay as NA (not float).
    positions["position_numeric"] = positions["position_numeric"].astype("Int64")
    positions["statement_id"] = positions["statement_id"].astype("Int64")
    salience["statement_id"] = salience["statement_id"].astype("Int64")
    statements_df["statement_id"] = statements_df["statement_id"].astype("Int64")

    save_both(parties, f"{prefix}_parties")
    save_both(statements_df, f"{prefix}_statements")
    save_both(positions, f"{prefix}_positions")
    save_both(salience, f"{prefix}_salience")

    logger.info(
        f"{prefix}: {len(parties)} entities, {len(statements_df)} statements, "
        f"{len(positions)} positions, {len(salience)} salience picks"
    )

    return {
        "parties": parties,
        "statements": statements_df,
        "positions": positions,
        "salience": salience,
    }
