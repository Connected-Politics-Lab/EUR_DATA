# euandi 2024 Ireland Election Dataset

Tidy, analysis-ready tables derived from the **EU&I (euandi) 2024** Voting
Advice Application coding for the June 2024 European Parliament election. The
application places parties and candidates on a battery of policy statements;
this dataset reshapes the original coding workbooks into long-format CSV/XLSX
tables that follow the same conventions as the companion `commission_formation`
dataset.

Two parallel datasets are produced:

- **Ireland** (`ie_*`) - 13 national parties + 6 independent candidates.
- **EU-level** (`eu_*`) - 10 European political party families.

Only the **final (calibrated) placement** is retained for each statement (the
headline euandi position, reconciled from coder judgement and party
self-placement).

## Dataset at a Glance

| File | Rows | Description |
|------|------|-------------|
| `ie_parties.csv` | 19 | Irish parties & independent candidates (the coded entities) |
| `ie_statements.csv` | 36 | Policy-statement catalogue (Ireland wording) |
| `ie_positions.csv` | 684 | Final position of each entity on each statement (long) |
| `ie_salience.csv` | 57 | Each entity's three most salient statements |
| `eu_parties.csv` | 10 | EU-level party families |
| `eu_statements.csv` | 36 | Policy-statement catalogue (EU wording) |
| `eu_positions.csv` | 360 | Final position of each family on each statement (long) |
| `eu_salience.csv` | 30 | Each family's three most salient statements |

## Coding Scheme

Each sheet codes **36 policy statements** on a five-point Likert scale, plus an
explicit "No opinion" option:

| Label | `position_numeric` |
|-------|--------------------|
| Completely disagree | -2 |
| Tend to disagree | -1 |
| Neutral | 0 |
| Tend to agree | +1 |
| Completely agree | +2 |
| No opinion | *(blank)* |

Statements 1-30 are the common euandi battery (statements 11 and 15 are
templated with the country name); statements 31-36 are additions specific to
the 2024 EP election, of which only 34 and 36 are country-templated (31, 32, 33
and 35 are worded identically across editions). Across both datasets there are
**1044 total placements**.

## Ireland

The Irish dataset covers **19 coded entities** - **13 national parties** and
**6 independent candidates** running in the 2024 EP election - across the three
constituencies (Dublin, South, Midlands-North-West). It records **684
party-statement positions**; **79% of Irish placements** take a substantive
(non-"No opinion") position.

## EU-level

The EU-level dataset covers the **10 EU-level party families** that field or
endorse candidates across member states (EPP, PES, ALDE, Greens/EGP, ECR, ID,
EFA, EDP, PEL, ECPM). It records **360 family-statement positions**; **82% of
EU-level placements** are substantive.

## Output Tables

### Entities - `ie_parties.csv` / `eu_parties.csv`
`party_id` (PK), `sheet_name`, `acronym`, `full_name`, `entity_type`,
`affiliation`, `constituency`, `country`, `level`.

### Statements - `ie_statements.csv` / `eu_statements.csv`
`statement_id` (PK), `statement_text`, `is_country_specific`.

### Positions - `ie_positions.csv` / `eu_positions.csv`
`position_id` (PK), `party_id` -> entity, `statement_id` -> statement,
`position_label`, `position_numeric`, `source_type`, `text_snippet`,
`source_link`. **One row per entity x statement** (final placement only).

### Salience - `ie_salience.csv` / `eu_salience.csv`
`salience_id` (PK), `party_id` -> entity, `salience_rank` (1-3),
`statement_id` -> statement, `statement_text`.

## Reproducing

Requires Python 3.9 or newer.

```bash
pip install -r requirements.txt
python run_pipeline.py            # parse both workbooks -> data/output/
python -m pytest tests/ -v        # schema + count + scale checks
python verify_readme.py           # verify the figures above against the CSVs
```

The pipeline reads only the two static workbooks in `data/raw/`; no network
access is required, so runs are fully deterministic.

### Raw data availability

The two source workbooks ("EU&I 2024 Ireland - Final coding.xlsx" and "EU&I
2024 general codesheet + salience_EU_Level_parties.xlsx") are **not shipped**
in the public repository: `data/raw/` is gitignored. To re-run the pipeline,
obtain the euandi 2024 dataset from the EUI Cadmus release cited under
*Provenance and Licence* below (CC BY 4.0) and place the two workbooks in
`data/raw/`. Without them `run_pipeline.py` fails at the workbook-read step.
All derived outputs (`data/output/`), figures and documentation are shipped,
so the dataset itself is usable without the raw workbooks.

## Provenance and Licence

**Source data:** euandi 2024 Voting Advice Application expert coding, prepared
for the June 2024 European Parliament election by the euandi 2024 team at the
European University Institute (EUI), and published under a **Creative Commons
Attribution 4.0 International (CC BY 4.0)** licence via the EUI research
repository (Cadmus):
<https://cadmus.eui.eu/entities/publication/6bd21956-5731-4a7b-be18-c24bba63a2aa>.

This dataset reshapes that source coding into tidy tables; it is a derivative
work and is redistributed under the same CC BY 4.0 licence, with attribution to
the original euandi 2024 authors as required. The parse extracts the **final
placement only** for each party-statement pair as recorded in the source
workbooks ("EU&I 2024 Ireland - Final coding" and "EU&I 2024 general codesheet +
salience, EU Level parties", both dated April 2024); the euandi team's internal
calibration between coder placement and party self-placement happened upstream
and is documented in the euandi 2024 release, not here. Column semantics and
known limitations are documented in [CODEBOOK.md](CODEBOOK.md). Derived tables:
CC-BY-4.0; pipeline code: Apache-2.0. All CSVs are encoded UTF-8 with BOM
(Excel-friendly).
