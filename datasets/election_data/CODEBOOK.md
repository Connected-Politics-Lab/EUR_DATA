# Codebook - euandi 2024 Ireland Election Dataset

Variable-level documentation for the eight output tables in `data/output/`.
The dataset is derived from the EU&I (euandi) 2024 Voting Advice Application
coding workbooks for the June 2024 European Parliament election.

The Ireland (`ie_*`) and EU-level (`eu_*`) datasets share an identical schema;
they are kept separate because their units of analysis differ (national
parties/candidates vs European party families) and because the statement
wording is templated differently (see Known Limitations).

All CSVs are encoded UTF-8 with BOM (Excel-friendly; `readr`/pandas handle it
transparently, base R `read.csv` needs `fileEncoding = "UTF-8-BOM"`).

---

## 1. `{ie,eu}_parties.csv` - coded entities

IE: 19 rows (13 parties + 6 independent candidates). EU: 10 rows.

| Column | Type | Description |
|--------|------|-------------|
| `party_id` | string | **Primary key.** Stable short code (e.g. `SF`, `EPP`, `WALLACE`). |
| `sheet_name` | string | Exact source-workbook tab name (provenance). |
| `acronym` | string | Party acronym. Blank for independent candidates. |
| `full_name` | string | Clean display name of the party / candidate / family. |
| `entity_type` | string | `party`, `independent_candidate`, or `eu_party_family`. |
| `affiliation` | string | Independent candidate's stated affiliation (e.g. `Independents 4 Change`); blank otherwise. |
| `constituency` | string | 2024 EP constituency for independents (`Dublin`, `South`, `Midlands-North-West`); blank otherwise. |
| `country` | string | `IE` (Ireland dataset) or `EU` (EU-level dataset). |
| `level` | string | `national` or `european`. |

---

## 2. `{ie,eu}_statements.csv` - statement catalogue

36 rows each. The euandi battery for the 2024 EP election.

| Column | Type | Description |
|--------|------|-------------|
| `statement_id` | int | **Primary key.** Statement number 1-36 (stable within a dataset). |
| `statement_text` | string | Full statement wording (as coded). |
| `is_country_specific` | bool | Heuristic flag: the statement is templated with the country/region name (`Ireland` / `EU Member States`). See Known Limitations. |

---

## 3. `{ie,eu}_positions.csv` - positions (core fact table)

One row per entity x statement, **final placement only**. IE: 684 rows
(19 x 36). EU: 360 rows (10 x 36).

| Column | Type | Description |
|--------|------|-------------|
| `position_id` | string | **Primary key.** Sequential code (`IEP0001...` / `EUP0001...`). |
| `party_id` | string | **Foreign key** -> `parties.party_id`. |
| `statement_id` | int | **Foreign key** -> `statements.statement_id`. |
| `position_label` | string | Likert label (`Completely disagree` ... `Completely agree`, or `No opinion`). Rarely blank where the coder left the final cell empty (1 row in IE, `IEP0495`; 0 in EU). |
| `position_numeric` | Int64 | -2..+2; blank for `No opinion` and missing labels. |
| `source_type` | string | Evidence type backing the placement. Not a strict controlled vocabulary (see Known Limitations). Usually blank where `No opinion` (19 No-opinion rows carry source fields; see the snippet caveat below). |
| `text_snippet` | string | Verbatim quote justifying the placement, where provided. |
| `source_link` | string | Free-text citation of the source, where provided: usually a URL (sometimes several, space-separated), but also values like `Self-placement`, `Manifesto`, or a document title, and occasionally a page-reference prefix before the URL. Machine-parse as a URL field with care. |

---

## 4. `{ie,eu}_salience.csv` - most salient statements

Up to three rows per entity (the statements each party flagged as most
salient). IE: 57 rows. EU: 30 rows.

| Column | Type | Description |
|--------|------|-------------|
| `salience_id` | string | **Primary key.** Sequential code (`IES0001...` / `EUS0001...`). |
| `party_id` | string | **Foreign key** -> `parties.party_id`. |
| `salience_rank` | int | 1, 2 or 3 (the party's ranking of its salient statements). |
| `statement_id` | Int64 | **Foreign key** -> `statements.statement_id`, resolved by matching the salience text back to the statement battery. |
| `statement_text` | string | The salient statement as recorded on the salience row. |

---

## Cross-Table Keys

```
parties.party_id      <-  positions.party_id     [1:many]
statements.statement_id <- positions.statement_id [1:many]
parties.party_id      <-  salience.party_id      [1:many, <=3]
statements.statement_id <- salience.statement_id  [1:many]
```

The `ie_*` and `eu_*` tables are independent. `statement_id` values are shared
*by number* across the two datasets but the wording differs, so do not join
Ireland positions to the EU statement catalogue (or vice versa).

---

## Known Limitations

- **Final placement only.** The source workbooks also record the coder
  placement and the party self-placement (each with its own source, snippet and
  link). This release keeps only the final calibrated placement; the other two
  blocks are dropped.
- **`source_type` is not a clean controlled vocabulary.** The template offers
  seven categories, but where coders selected "Other (please specify)" they
  often typed free text directly (e.g. "Website", "Blog", "Leader statement"),
  so the raw value is preserved as-is rather than coerced.
- **`is_country_specific` is a heuristic.** It flags statements whose text
  contains the country/region token (`Ireland` / `EU Member States`). It
  approximates, but does not authoritatively define, the country-templated
  subset of the euandi battery.
- **Statement wording is templated per dataset.** Common-battery items
  substitute the country/region name (e.g. "Immigration into **Ireland**" vs
  "Immigration into **EU Member States**"), and statements 31-36 are
  country/EP-specific. The two statement catalogues therefore differ in wording
  even where `statement_id` matches.
- **Sparse `text_snippet` / `source_link`.** These are blank wherever the coder
  recorded a position without attaching a quote or URL, and usually blank for
  `No opinion` (19 No-opinion rows do carry source fields).
- **Placeholder snippets for one candidate.** The independent candidate Punch
  (`PUNCH`) has 15 `No opinion` rows whose `text_snippet` is the coder's note
  "New Candidate - No public information available". Treat these as metadata
  about evidence availability, not as substantive quotes: filter on
  `position_numeric` (or exclude `No opinion`) rather than snippet presence.

---

## Provenance and Licence

Source: euandi 2024 Voting Advice Application expert coding (euandi 2024 team,
European University Institute), published under CC BY 4.0 via EUI Cadmus:
<https://cadmus.eui.eu/entities/publication/6bd21956-5731-4a7b-be18-c24bba63a2aa>.
This dataset is a derivative work, redistributed under CC BY 4.0 with attribution
to the original authors. Statistics in [README.md](README.md) are verified
against the CSVs by `verify_readme.py`. Derived data: CC-BY-4.0; pipeline code:
Apache-2.0.
