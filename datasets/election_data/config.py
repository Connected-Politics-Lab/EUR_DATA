"""
Configuration for the euandi 2024 Ireland Election Dataset.

The source is the EU&I (euandi) 2024 Voting Advice Application coding for the
June 2024 European Parliament election. Two Excel workbooks are processed into
two parallel tidy datasets:

  * Ireland           - 13 national parties + 6 independent candidates
  * EU-level parties  - 10 European political party families

Only the *final* (calibrated) placement is retained for each statement.

Contains path constants, curated entity metadata, the position scale, and
logging config. No network access is required: the source workbooks are static
files in data/raw/.
"""

from pathlib import Path

# ============================================================
# Path constants
# ============================================================

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
RAW_DIR = DATA_DIR / "raw"
OUTPUT_DIR = DATA_DIR / "output"

# Source workbooks (immutable inputs, kept in data/raw/)
IE_WORKBOOK = RAW_DIR / "EU&I 2024 Ireland - Final coding.xlsx"
EU_WORKBOOK = RAW_DIR / "EU&I 2024 general codesheet + salience_EU_Level_parties.xlsx"

# ============================================================
# Sheet layout (euandi coding template)
# ============================================================

# Every sheet shares a fixed layout. Rather than hard-code row indices (one
# sheet is off by one), the parser anchors on these marker strings in column 0.
HEADER_MARKER = "Statement #"   # row above the 36 statement rows
SALIENCE_MARKER = "Salience:"   # row above the (up to) 3 salience rows

# Column indices for the FINAL (calibrated) placement block.
COL_STATEMENT_NUM = 0
COL_STATEMENT_TEXT = 1
COL_FINAL_POSITION = 10
COL_FINAL_SOURCE_TYPE = 11
COL_FINAL_SNIPPET = 12
COL_FINAL_LINK = 13

# Number of policy statements per sheet (statements 1-36).
N_STATEMENTS = 36

# ============================================================
# Position scale (5-point Likert + "No opinion")
# ============================================================

# Maps the coded label to a numeric score. "No opinion" (and blank/missing)
# map to NA - they are not points on the agree-disagree scale.
POSITION_SCALE = {
    "Completely disagree": -2,
    "Tend to disagree": -1,
    "Neutral": 0,
    "Tend to agree": 1,
    "Completely agree": 2,
    "No opinion": None,
}

# Valid position labels (everything the recode step expects to see).
VALID_POSITION_LABELS = set(POSITION_SCALE.keys())

# The seven controlled source-type categories offered by the coding template.
# Note: where coders selected "Other (please specify)" they often typed free
# text directly, so the source_type field is NOT a strict controlled
# vocabulary in the final data. See CODEBOOK.md.
SOURCE_TYPE_CATEGORIES = [
    "2024 EP election manifesto of the party",
    "Latest national election manifesto of the party",
    "Other programmatic and official party documentation",
    "Recent interviews, press releases and social media communication "
    "(from party, party leader and/or leading candidates)",
    "Older national or European election manifestos",
    "2024 EP election manifesto of the respective Europarty",
    "Other (please specify)",
]

# ============================================================
# Curated Ireland entities (13 parties + 6 independent candidates)
# ============================================================
# party_id    - stable primary key
# sheet_name  - exact tab name in the source workbook
# acronym     - party acronym (blank for independents)
# full_name   - clean display name
# entity_type - "party" | "independent_candidate"
# affiliation - independent's stated affiliation (blank for parties)
# constituency- 2024 EP constituency (independents only)

IE_ENTITIES = [
    {"party_id": "SF", "sheet_name": "SF", "acronym": "SF",
     "full_name": "Sinn Féin", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "SD", "sheet_name": "SD", "acronym": "SD",
     "full_name": "Social Democrats", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "IF", "sheet_name": "IF", "acronym": "IF",
     "full_name": "Ireland First", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "PBP", "sheet_name": "PBP", "acronym": "PBP",
     "full_name": "Solidarity–People Before Profit", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "RG", "sheet_name": "RG", "acronym": "RG",
     "full_name": "Rabharta Glas", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "IFP", "sheet_name": "IFP", "acronym": "IFP",
     "full_name": "Irish Freedom Party", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "ATU", "sheet_name": "ATU", "acronym": "ATU",
     "full_name": "Aontú", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "LP", "sheet_name": "LP", "acronym": "LP",
     "full_name": "The Labour Party", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "NP", "sheet_name": "NP", "acronym": "NP",
     "full_name": "National Party", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "GP", "sheet_name": "GP", "acronym": "GP",
     "full_name": "Green Party", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "FG", "sheet_name": "FG", "acronym": "FG",
     "full_name": "Fine Gael", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "FF", "sheet_name": "FF", "acronym": "FF",
     "full_name": "Fianna Fáil", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "II", "sheet_name": "II", "acronym": "II",
     "full_name": "Independent Ireland", "entity_type": "party",
     "affiliation": "", "constituency": ""},
    {"party_id": "WALLACE", "sheet_name": "Wallace (I4C- South)", "acronym": "",
     "full_name": "Mick Wallace", "entity_type": "independent_candidate",
     "affiliation": "Independents 4 Change", "constituency": "South"},
    {"party_id": "DEBARRA", "sheet_name": "De Barra (IND - South)", "acronym": "",
     "full_name": "Graham De Barra", "entity_type": "independent_candidate",
     "affiliation": "Independent", "constituency": "South"},
    {"party_id": "PUNCH", "sheet_name": "Punch (IND - South)", "acronym": "",
     "full_name": "Eddie Punch", "entity_type": "independent_candidate",
     "affiliation": "Independent", "constituency": "South"},
    {"party_id": "FLANAGAN", "sheet_name": "Flanagan (IND - Midlands NW)", "acronym": "",
     "full_name": "Luke Flanagan", "entity_type": "independent_candidate",
     "affiliation": "Independent", "constituency": "Midlands-North-West"},
    {"party_id": "DALY", "sheet_name": "Daly (I4C - Dublin)", "acronym": "",
     "full_name": "Clare Daly", "entity_type": "independent_candidate",
     "affiliation": "Independents 4 Change", "constituency": "Dublin"},
    {"party_id": "OROURKE", "sheet_name": "O'Rourke - (IND - Dublin)", "acronym": "",
     "full_name": "Stephen O'Rourke", "entity_type": "independent_candidate",
     "affiliation": "Independent", "constituency": "Dublin"},
]

# ============================================================
# Curated EU-level party families (10)
# ============================================================

EU_ENTITIES = [
    {"party_id": "ALDE", "sheet_name": "ALDE", "acronym": "ALDE",
     "full_name": "Alliance of Liberals and Democrats for Europe"},
    {"party_id": "EFA", "sheet_name": "EFA", "acronym": "EFA",
     "full_name": "European Free Alliance"},
    {"party_id": "EGP", "sheet_name": "Greens", "acronym": "EGP",
     "full_name": "European Green Party"},
    {"party_id": "EDP", "sheet_name": "EDP", "acronym": "EDP",
     "full_name": "European Democratic Party"},
    {"party_id": "PEL", "sheet_name": "PEL", "acronym": "PEL",
     "full_name": "Party of the European Left"},
    {"party_id": "ECPM", "sheet_name": "ECPM", "acronym": "ECPM",
     "full_name": "European Christian Political Movement"},
    {"party_id": "ECR", "sheet_name": "ECR", "acronym": "ECR",
     "full_name": "European Conservatives and Reformists Party"},
    {"party_id": "PES", "sheet_name": "PES", "acronym": "PES",
     "full_name": "Party of European Socialists"},
    {"party_id": "ID", "sheet_name": "ID", "acronym": "ID",
     "full_name": "Identity and Democracy Party"},
    {"party_id": "EPP", "sheet_name": "EPP", "acronym": "EPP",
     "full_name": "European People's Party"},
]

# Expected entity counts (for validation).
IE_EXPECTED_ENTITIES = len(IE_ENTITIES)   # 19
EU_EXPECTED_ENTITIES = len(EU_ENTITIES)   # 10

# ============================================================
# Logging config
# ============================================================

LOG_FORMAT = "%(asctime)s [%(levelname)s] %(name)s: %(message)s"
LOG_DATE_FORMAT = "%Y-%m-%d %H:%M:%S"
