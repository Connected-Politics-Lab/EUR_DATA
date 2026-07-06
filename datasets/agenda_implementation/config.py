"""
Configuration for the Commission Legislative-Agenda Implementation Dataset.

This dataset measures how far the 2024-2029 von der Leyen II Commission has
implemented the legislative agenda it set itself. It links each planned agenda
item (from the sibling `commission_formation` dataset) to its real legislative
fate, resolved against the EP Open Data API and cross-checked in EUR-Lex.

Contains path constants, the sibling-dataset links, API endpoints, the curated
procedure-phase -> status mapping, and logging config.
"""

from pathlib import Path
from typing import Dict, List

# ============================================================
# Path constants
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"            # API response cache
OUTPUT_DIR = DATA_DIR / "output"     # the published CSV/XLSX tables
MANUAL_DIR = DATA_DIR / "manual"     # curated, hand-coded inputs

# Sibling dataset (read-only inputs; we link to it, never duplicate it).
COMMISSION_FORMATION_DIR = BASE_DIR.parent / "commission_formation"
WORK_PROGRAMME_CSV = COMMISSION_FORMATION_DIR / "data" / "output" / "work_programme_items.csv"
MISSION_COMMITMENTS_CSV = COMMISSION_FORMATION_DIR / "data" / "output" / "mission_letter_commitments.csv"

# Curated input files (script 07 / 05 read these; templates are scaffolded if
# absent so Phase 1 runs without them).
ANNEX_I_OVERRIDES_CSV = MANUAL_DIR / "annex_i_overrides.csv"
ANNEX_II_EVALUATIONS_CSV = MANUAL_DIR / "annex_ii_evaluations.csv"
LEGISLATIVE_COMMITMENTS_CSV = MANUAL_DIR / "legislative_commitments.csv"

# ============================================================
# External sources
# ============================================================

# EP Open Data API v2 (the machine-readable backend of the Legislative
# Observatory / OEIL). Requires the JSON-LD Accept header.
EP_API_BASE = "https://data.europarl.europa.eu/api/v2"
EP_API_ACCEPT = "application/ld+json"
EP_API_PAGE_LIMIT = 100          # max items per listing page
EP_API_SLEEP = 0.4               # polite delay between requests (~750 req/5 min)

# EUR-Lex Cellar SPARQL endpoint (cross-check: COM -> CELEX, in-force, OJ date).
EURLEX_SPARQL = "http://publications.europa.eu/webapi/rdf/sparql"

# ============================================================
# Term & corpus scope
# ============================================================

# The 2024-2029 term: proposals are tabled from 2024 onwards. CWP 2025 is the
# planning document under study.
TERM_YEARS: List[int] = [2024, 2025, 2026]

# Procedure tracks whose dossiers the EP API exposes (the corpus generator).
PROCEDURE_TYPES: List[str] = ["COD", "CNS", "NLE", "APP"]

# ============================================================
# Procedure reference parsing
# ============================================================

# Interinstitutional reference "YYYY/NNNN(TYPE)" -> EP process_id "YYYY-NNNN".
# Recognised procedure-type tokens (the parenthesised suffix).
PROCEDURE_TYPE_TOKENS = [
    "COD", "CNS", "NLE", "APP", "SYN", "BUD", "DEC", "AVC", "RSP", "INI",
]

# ============================================================
# Status enum (ordered ladder + off-ladder terminal states)
# ============================================================

# The ordered "ladder" of normal progress. Used by the monotonicity test: a
# procedure's status should not move backwards down this ladder across dated
# snapshots. Terminal states below sit off the ladder.
STATUS_LADDER: List[str] = [
    "not_started",   # no procedure number yet (Annex I before tabling)
    "proposed",      # COM proposal tabled; awaiting committee/first reading
    "ep_1st_read",   # first reading
    "council_1st",   # Council first-reading position
    "ep_2nd_read",   # second reading
    "ep_3rd_read",   # third reading / conciliation
    "adopted",       # act adopted (procedure completed / awaiting signature)
    "in_force",      # confirmed in force via EUR-Lex
]

# Off-ladder terminal outcomes (a procedure may jump to any of these).
STATUS_TERMINAL: List[str] = ["withdrawn", "rejected", "lapsed"]

# Catch-all when an EP phase code is unrecognised.
STATUS_UNKNOWN = "in_progress"

# A reference that did not resolve in the EP API (e.g. an old proposal absent
# from the Observatory, or a repeal of in-force law with no procedure number).
STATUS_NOT_FOUND = "not_found"

ALL_STATUSES: List[str] = (
    STATUS_LADDER + STATUS_TERMINAL + [STATUS_UNKNOWN, STATUS_NOT_FOUND]
)

# Exact EP procedure-phase authority code (last URI segment, upper-case) ->
# status. The substring fallback in scripts/status_map.py handles variants and
# codes not listed here, so this map need not be exhaustive; it keeps runs
# deterministic offline.
PHASE_CODE_TO_STATUS: Dict[str, str] = {
    "PROPOSAL": "proposed",
    "AWAITING_COMMITTEE_DECISION": "proposed",
    "AWAITING_PARLIAMENT_1ST_READING": "proposed",
    "RDG1": "ep_1st_read",
    "AWAITING_COUNCIL_1ST_READING": "council_1st",
    "RDG2": "ep_2nd_read",
    "AWAITING_PARLIAMENT_2ND_READING": "ep_2nd_read",
    "RDG3": "ep_3rd_read",
    "CONCILIATION": "ep_3rd_read",
    "AWAITING_SIGNATURE": "adopted",
    "PROCEDURE_COMPLETED": "adopted",
    "PROCEDURE_COMPLETED_ACT_ADOPTED": "adopted",
    "PROCEDURE_REJECTED": "rejected",
    "PROCEDURE_WITHDRAWN": "withdrawn",
    "PROCEDURE_LAPSED": "lapsed",
    "PROCEDURE_LAPSED_OR_WITHDRAWN": "lapsed",
}

# Source-scope enum for the agenda_items spine. The official CWP Annex III
# (pending priority proposals) is deliberately out of scope of the sibling
# dataset, so there is no cwp_annex_iii scope; those procedures are covered by
# this dataset's term corpus instead.
SOURCE_SCOPES = [
    "cwp_annex_i", "cwp_annex_ii", "cwp_annex_iv", "cwp_annex_v",
    "mission_letter",
]

# Evaluation types for the curated evaluations table (Annex II).
EVALUATION_TYPES = [
    "refit", "fitness_check", "interim_evaluation", "evaluation",
]

# ============================================================
# Logging config
# ============================================================

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
