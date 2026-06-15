# EUR_DATA: Commission Formation Dataset (2024-2029)

Structured dataset on the 2024-2029 European Commission formation process and work programme negotiations. Deliverable D1.2 / Milestone MS3.

## Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run the full pipeline
python run_pipeline.py

# Run a single step
python run_pipeline.py --step 5    # investiture vote only

# Skip PDF downloads (if already cached)
python run_pipeline.py --skip-download

# Run tests
pytest tests/ -v
```

## Dataset at a Glance

Six interlinked tables covering the full arc of Commission formation, from the June 2024 European Parliament elections through the adoption of the 2025 Commission Work Programme in February 2025.

| Table | Rows | What it captures |
|-------|------|------------------|
| `commissioners.csv` | 27 | The College: one row per member state, with portfolio, party, gender, and DG assignments |
| `mission_letter_commitments.csv` | 721 | Policy commitments extracted from 26 presidential mission letters |
| `hearings.csv` | 26 | Confirmation hearing dates, responsible committees, and outcomes |
| `investiture_vote.csv` | 688 | MEP-level roll-call votes on the full College (27 Nov 2024) |
| `work_programme_items.csv` | 113 | Legislative and policy items from the Commission Work Programme 2025 |
| `formation_timeline.csv` | 13 | Key institutional milestones from elections to CWP adoption |

All tables are linked through `commissioner_id` (a 3-letter key per commissioner). The vote table uses `ep_party_group` as a shared dimension with the commissioner table.

## What's in the Data

### The College of Commissioners

The 27-member College reflects the political balance of the 2024-2029 Parliament:

- **Party composition**: EPP dominates with 15 commissioners (56%), followed by S&D and Renew with 5 each, plus 1 ECR (Fitto, Italy) and 1 PfE (Varhelyi, Hungary).
- **Gender split**: 11 women (41%) and 16 men (59%).
- **Role hierarchy**: 1 President (von der Leyen), 5 Executive Vice-Presidents, 1 High Representative/Vice-President (Kallas), and 20 Commissioners.
- **Coverage**: All 27 EU member states, one commissioner per country.

Each row includes the commissioner's portfolio title, responsible DGs, EP party group, national party, mission letter URL, and hearing date.

### The Investiture Vote

On 27 November 2024, the European Parliament voted to approve the full College: **370 for, 282 against, 36 abstentions** (688 MEPs participating).

The vote data reveals the coalition structure underlying the Commission's mandate:

| Party group | For | Against | Abstain | Total |
|-------------|-----|---------|---------|-------|
| PPE | 151 | 25 | 2 | 178 |
| S&D | 90 | 25 | 18 | 133 |
| PfE | 0 | 84 | 0 | 84 |
| ECR | 33 | 39 | 4 | 76 |
| Renew | 67 | 0 | 6 | 73 |
| Verts/ALE | 27 | 19 | 6 | 52 |
| The Left | 0 | 43 | 0 | 43 |
| NI | 2 | 24 | 0 | 26 |
| ESN | 0 | 23 | 0 | 23 |

The supporting coalition (PPE + S&D + Renew) provided the bulk of "for" votes, while PfE, The Left, and ESN voted unanimously against. ECR was divided: Italy's 24 Fratelli d'Italia MEPs voted for (reflecting PM Meloni's support for EVP Fitto), while Poland's 20 PiS MEPs voted against.

Notable national patterns:
- **France** voted 61-18 against — the most lopsided national delegation, driven by PfE (Rassemblement National), S&D, and The Left opposition.
- **Italy** voted 52-23 in favour, with ECR (Fratelli d'Italia) support proving pivotal.
- **Spain** voted 37-21 against, unusually including all 21 Spanish PPE members (Partido Popular) breaking the group line.
- **Germany** (largest delegation, 92 votes cast) voted 51-28-13, with S&D members abstaining rather than voting for.

Country enrichment covers 100% of MEPs (688 of 688). The `national_party` field is not populated in the current pipeline version.

### Mission Letter Commitments

721 specific policy commitments extracted from the 26 mission letters issued by President von der Leyen to each commissioner-designate (von der Leyen herself, as President, has no mission letter).

- **Extraction confidence**: 440 high-confidence commitments (extracted from bullet-point lists) and 281 medium-confidence (from directive sentences and legislative references).
- **Commitment types**: coordination (216), policy (135), report (34), review (12), legislative (11), other (313).
- **Top commissioners by commitment count**: Sefcovic (40), Brunner (38), Jorgensen (38), Lahbib (37), McGrath (37). The fewest: Kos (17).
- Average: ~28 commitments per commissioner.

Each commitment includes the full text, a short summary, the section heading from the letter, and the surrounding paragraph for context.

### Hearings

26 confirmation hearings held over 4-12 November 2024. All commissioners-designate were approved.

- **Main week**: 4-7 November (23 hearings across four days, 5-6 per day).
- **Late hearings**: Albuquerque on 11 Nov; Ribera and Fitto on 12 Nov — the two politically controversial Executive Vice-President nominations held last.
- Each row records the responsible and associated EP committees, enabling analysis of committee scrutiny patterns.

### Commission Work Programme 2025

113 items from the four annexes of the CWP 2025, adopted 11 February 2025:

| Annex | Items | Content |
|-------|-------|---------|
| I — New initiatives | 35 | New legislative proposals and policy actions |
| II — REFIT | 34 | Evaluations and fitness checks of existing legislation |
| III — Interim evaluations | 3 | Mid-term reviews in progress |
| IV — Withdrawals and repeals | 41 | Obsolete legislation to be removed |

Annex I policy areas span competitiveness, security, decarbonisation, innovation, migration, and social fairness. Annex IV includes 25 regulations, 10 directives, 5 decisions, and 1 recommendation marked for repeal.

### Formation Timeline

13 institutional milestones spanning 250 days from the EP elections (6 June 2024) to the adoption of the CWP (11 February 2025):

1. EP elections (6-9 Jun 2024)
2. European Council nominates von der Leyen (27 Jun)
3. EP constitutive session / Metsola re-elected (16 Jul)
4. EP elects von der Leyen as President (18 Jul, 401 votes)
5. Commissioners-designate announced & mission letters published (17 Sep)
6. Confirmation hearings (4-12 Nov)
7. Conference of Presidents endorses College (21 Nov)
8. EP investiture vote (27 Nov, 370-282-36)
9. Commission takes office (1 Dec)
10. CWP 2025 adopted (11 Feb 2025)

## Cross-Table Relationships

```
commissioners (27)
├── commissioner_id ──→ mission_letter_commitments (721)  [1:many]
├── commissioner_id ──→ hearings (26)                     [1:1, excl. President]
└── ep_party_group  ──→ investiture_vote (688)            [shared dimension]

work_programme_items (113)   ← standalone (linkable to commissioners via policy_area)
formation_timeline (13)      ← standalone (institutional chronology)
```

**Key joins:**
- `commissioners` + `investiture_vote` on `ep_party_group`: analyse how each commissioner's party group voted on the College.
- `commissioners` + `mission_letter_commitments` on `commissioner_id`: connect commitments to commissioner attributes (country, party, gender, portfolio).
- `commissioners` + `hearings` on `commissioner_id`: link hearing committees and dates to commissioner profiles.

## Working with the Data

```python
import pandas as pd

# Load core tables
comm = pd.read_csv("data/output/commissioners.csv")
votes = pd.read_csv("data/output/investiture_vote.csv")
commitments = pd.read_csv("data/output/mission_letter_commitments.csv")
wp = pd.read_csv("data/output/work_programme_items.csv")

# Party group vote breakdown
votes.groupby("ep_party_group")["vote"].value_counts().unstack(fill_value=0)

# High-confidence commitments only
high_conf = commitments[commitments["confidence"] == "high"]  # 440 rows
high_conf.groupby("commissioner_id").size().sort_values(ascending=False)

# Join commitments to commissioner metadata
merged = commitments.merge(
    comm[["commissioner_id", "country_name", "ep_party_group", "gender"]],
    on="commissioner_id"
)

# Commitments by party group
merged.groupby("ep_party_group").size()

# Gender split in commitment types
merged.groupby(["gender", "commitment_type"]).size().unstack(fill_value=0)

# Work programme by annex
wp["annex"].value_counts()
```

## Research Use Cases

### Coalition and Voting Behaviour

The investiture vote table enables analysis of the coalition dynamics behind the Commission's mandate. Party discipline can be measured by comparing within-group vote shares (e.g., PPE's 85% cohesion vs. ECR's split). National delegation behaviour reveals cross-cutting cleavages — Spain's PPE members breaking the group line, Italy's ECR backing the Commission, France's near-unanimous opposition across left and right.

### Gender and Representation

With 11 women among 27 commissioners, the data supports analysis of gendered portfolio assignment patterns. Joining commissioners to mission letter commitments allows comparison of commitment volumes and types by gender. The hearing data can reveal whether female commissioners were assigned to different committee configurations.

### Policy Priority Analysis

The 721 mission letter commitments represent the President's policy expectations for each portfolio. Comparing commitment counts and types across commissioners reveals variation in workload and policy ambition. Linking commitments thematically to the 35 new CWP initiatives in Annex I shows how mission letter priorities translate into the legislative agenda.

### Institutional Process

The timeline and hearing data together capture the procedural rhythm of Commission formation. The 250-day span from elections to work programme, the scheduling of politically sensitive hearings (Ribera, Fitto) last, and the unanimous approval of all 26 commissioners-designate are all observable in the data.

### Computational Text Analysis

The commitment texts (721 rows of natural-language policy statements) and work programme titles/descriptions are suitable for NLP applications: topic modelling across portfolios, keyword extraction, semantic similarity between mission letter commitments and CWP items, or network analysis based on coordination mentions ("work closely with...") in the mission letters.

## Output Tables

All outputs saved as CSV + XLSX in `data/output/`.

### 1. `commissioners.csv` (27 rows)

| Column | Type | Description |
|--------|------|-------------|
| `commissioner_id` | str | 3-letter identifier |
| `full_name` | str | Full name |
| `last_name` | str | Surname |
| `first_name` | str | Given name(s) |
| `country` | str | ISO 2-letter country code |
| `country_name` | str | Full country name |
| `portfolio_title` | str | Official portfolio title |
| `role` | str | President / Executive Vice-President / High Representative/Vice-President / Commissioner |
| `ep_party_group` | str | EP party group (EPP, S&D, Renew, ECR, PfE) |
| `national_party` | str | National party abbreviation |
| `gender` | str | M / F |
| `dgs_responsible` | str | Comma-separated DG codes |
| `mission_letter_url` | str | URL to mission letter PDF |
| `hearing_date` | str | YYYY-MM-DD of confirmation hearing |
| `profile_url` | str | URL to EC profile page |

### 2. `mission_letter_commitments.csv` (721 rows)

| Column | Type | Description |
|--------|------|-------------|
| `commitment_id` | str | C0001-format identifier |
| `commissioner_id` | str | FK to commissioners |
| `commissioner_name` | str | Commissioner full name |
| `portfolio_title` | str | Portfolio title |
| `commitment_text` | str | Full extracted commitment text |
| `commitment_short` | str | Short description (<=100 chars) |
| `section_heading` | str | Detected section heading from letter |
| `commitment_type` | str | legislative / policy / coordination / review / report / other |
| `extraction_method` | str | bullet_point / directive_sentence / legislative_reference |
| `confidence` | str | high / medium |
| `page_number` | int | PDF page number |
| `raw_paragraph` | str | Surrounding paragraph context |

### 3. `hearings.csv` (26 rows)

| Column | Type | Description |
|--------|------|-------------|
| `hearing_id` | str | H01-H26 identifier |
| `commissioner_id` | str | FK to commissioners |
| `commissioner_name` | str | Commissioner full name |
| `hearing_date` | str | YYYY-MM-DD |
| `committees_responsible` | str | Lead EP committee(s) |
| `committees_associated` | str | Associated EP committee(s) |
| `outcome` | str | approved / rejected / pending / second_hearing |
| `evaluation_letter_url` | str | URL to evaluation letter (if found) |
| `written_questions_url` | str | URL to written Q&A (if found) |
| `video_url` | str | URL to hearing video (if found) |

### 4. `investiture_vote.csv` (688 rows)

| Column | Type | Description |
|--------|------|-------------|
| `mep_id` | str | EP MEP identifier |
| `full_name` | str | MEP full name (from XML) |
| `last_name` | str | Parsed surname |
| `first_name` | str | Parsed given name |
| `country` | str | ISO 2-letter country code |
| `country_name` | str | Full country name |
| `ep_party_group` | str | EP party group short code |
| `ep_party_group_full` | str | EP party group full name |
| `national_party` | str | National party (from API) |
| `vote` | str | for / against / abstain / did_not_vote |
| `vote_numeric` | int | 1 (for) / -1 (against) / 0 (abstain) |
| `vote_date` | str | 2024-11-27 |

**Totals**: 370 for + 282 against + 36 abstain = 688

### 5. `work_programme_items.csv` (113 rows)

| Column | Type | Description |
|--------|------|-------------|
| `item_id` | str | WP001-format identifier |
| `annex` | str | I (new) / II (REFIT) / III (withdrawals) / IV (repeals) |
| `item_number` | str | Numbered item within annex |
| `title` | str | Initiative title |
| `description` | str | Description or objective |
| `policy_area` | str | Policy area (if detected) |
| `type_of_act` | str | Regulation / Directive / Communication / etc. |
| `indicative_timing` | str | Expected timing (Q1 2025, etc.) |

### 6. `formation_timeline.csv` (13 rows)

| Column | Type | Description |
|--------|------|-------------|
| `event_id` | str | T01-format identifier |
| `date` | str | YYYY-MM-DD |
| `event_name` | str | Short event name |
| `event_description` | str | Detailed description |
| `event_type` | str | election / nomination / institutional / vote / hearing / document |
| `institution` | str | European Parliament / European Council / Council of the EU / European Commission |
| `document_url` | str | URL to associated document (if any) |

## Data Sources

| Table | Source | Method |
|-------|--------|--------|
| Commissioners | EC website + curated | BeautifulSoup scrape with curated fallback |
| Mission letters | EC PDF downloads | pdfplumber text extraction + regex/heuristic parsing |
| Hearings | EP timeline (curated) | config.py dict + optional EP URL enrichment |
| Investiture vote | EP roll-call XML | xml.etree parsing + EP Open Data API enrichment |
| Work programme | CWP 2025 PDF | pdfplumber table extraction with text fallback |
| Timeline | Curated | Fully manual in config.py |

## Accuracy & Limitations

| Component | Estimated Accuracy | Notes |
|-----------|-------------------|-------|
| Commissioner basic info | ~100% | Curated data |
| Mission letter text extraction | ~95% | pdfplumber handles digital PDFs well |
| Mission letter commitments | ~75-85% | `confidence` field enables targeted manual review |
| Hearing core data | ~100% | Curated data |
| Investiture vote | ~100% | Structured XML source |
| MEP enrichment (country/party) | 100% | 688 of 688 MEPs country-enriched; `national_party` not yet populated |
| Work programme items | ~70-85% | PDF table extraction; manual QA recommended |
| Timeline | ~100% | Curated data |

## Manual Review Checklist

- [ ] Compare `commissioners.csv` against EC website
- [ ] Spot-check 5 mission letter commitments against original PDFs
- [ ] Verify vote totals: 370 + 282 + 36 = 688
- [ ] Cross-check sample MEP votes against EP HTML results page
- [ ] Compare work programme items against CWP PDF annex

## Pipeline Steps

| Step | Script | Description |
|------|--------|-------------|
| 1 | `01_scrape_commissioners.py` | Commissioner profiles |
| 2 | `02_download_mission_letters.py` | Download 27 mission letter PDFs |
| 3 | `03_parse_mission_letters.py` | Extract and parse commitments |
| 4 | `04_scrape_hearings.py` | Hearing schedule and outcomes |
| 5 | `05_fetch_investiture_vote.py` | MEP-level investiture vote |
| 6 | `06_parse_work_programme.py` | CWP 2025 legislative items |
| 7 | `07_build_timeline.py` | Formation timeline |

## Requirements

- Python 3.9+
- See `requirements.txt` for package dependencies
