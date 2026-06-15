# EUR_DATA Commission Formation: Codebook

Column-level data dictionary for the six output tables in `data/output/`. For
narrative context, coverage notes, and research use cases, see [README.md](README.md).

All files are UTF-8 CSV with a header row. Empty cells denote missing values
(read as `NaN` by pandas). Primary keys are unique and non-null unless noted.

---

## 1. `commissioners.csv` (27 rows)

One row per member of the 2024-2029 College of Commissioners (one per member state).

| Column | Type | Null | Description |
|--------|------|------|-------------|
| `commissioner_id` | string | 0 | **Primary key.** Three-letter code per commissioner (e.g. `MAS`). Foreign key target for `hearings` and `mission_letter_commitments`. |
| `full_name` | string | 0 | Commissioner's full name. |
| `last_name` | string | 0 | Surname. |
| `first_name` | string | 0 | Given name(s). |
| `country` | string | 0 | ISO-style 2-letter member-state code (e.g. `PT`). |
| `country_name` | string | 0 | Member-state name in English. |
| `portfolio_title` | string | 0 | Full portfolio title (e.g. *Commissioner for Financial Services*). |
| `role` | string | 0 | One of `President`, `Executive Vice-President`, `High Representative/Vice-President`, `Commissioner`. |
| `ep_party_group` | string | 0 | EP political group affiliation. One of `EPP`, `S&D`, `Renew`, `ECR`, `PfE`. **Note the label mismatch with `investiture_vote` (see Join Caveats).** |
| `national_party` | string | 0 | National party abbreviation (e.g. `PSD`). |
| `gender` | string | 0 | `F` or `M`. |
| `dgs_responsible` | string | 0 | Directorate(s)-General the commissioner oversees (e.g. `FISMA`). |
| `mission_letter_url` | string | 1 | URL of the presidential mission letter PDF. Null for the President (no mission letter). |
| `hearing_date` | date (YYYY-MM-DD) | 1 | Confirmation hearing date. Null for the President (no hearing). |
| `profile_url` | string | 0 | URL of the commissioner's official EC profile page. |

---

## 2. `mission_letter_commitments.csv` (721 rows)

Policy commitments extracted from the 26 presidential mission letters.

| Column | Type | Null | Description |
|--------|------|------|-------------|
| `commitment_id` | string | 0 | **Primary key.** Sequential code (`C0001`...). |
| `commissioner_id` | string | 0 | **Foreign key** to `commissioners.commissioner_id`. 26 distinct values (no President). |
| `commissioner_name` | string | 0 | Denormalised commissioner full name. |
| `portfolio_title` | string | 0 | Denormalised portfolio title. |
| `commitment_text` | string | 0 | Full text of the commitment as extracted. |
| `commitment_short` | string | 0 | Truncated summary of the commitment. |
| `section_heading` | string | 475 | Heading of the letter section the commitment falls under, where one could be identified. |
| `commitment_type` | string | 0 | One of `coordination`, `policy`, `report`, `review`, `legislative`, `other`. |
| `extraction_method` | string | 0 | How the commitment was identified: `bullet_point`, `directive_sentence`, `legislative_reference`. |
| `confidence` | string | 0 | `high` (bullet-point extraction, 440 rows) or `medium` (directive/legislative, 281 rows). |
| `page_number` | integer | 0 | Page of the source PDF the commitment appears on. |
| `raw_paragraph` | string | 0 | Surrounding source paragraph, retained for context. |

---

## 3. `hearings.csv` (26 rows)

Confirmation hearings held 4-12 November 2024.

| Column | Type | Null | Description |
|--------|------|------|-------------|
| `hearing_id` | string | 0 | **Primary key.** Sequential code (`H01`...). |
| `commissioner_id` | string | 0 | **Foreign key** to `commissioners.commissioner_id` (1:1, excluding the President). |
| `commissioner_name` | string | 0 | Denormalised commissioner full name. |
| `hearing_date` | date (YYYY-MM-DD) | 0 | Date of the hearing. |
| `committees_responsible` | string | 0 | Lead EP committee(s); multiple values separated by a delimiter. |
| `committees_associated` | string | 4 | Associated EP committee(s), where applicable. |
| `outcome` | string | 0 | Hearing outcome. All 26 are `approved`. |
| `evaluation_letter_url` | string | 26 | **Reserved, not yet populated.** Intended for the committee evaluation letter URL. |
| `written_questions_url` | string | 26 | **Reserved, not yet populated.** |
| `video_url` | string | 26 | **Reserved, not yet populated.** |

---

## 4. `investiture_vote.csv` (688 rows)

MEP-level roll-call votes on the full College, 27 November 2024 (370 for, 282 against, 36 abstain).

| Column | Type | Null | Description |
|--------|------|------|-------------|
| `mep_id` | integer | 0 | **Primary key.** EP `PersId` identifier (matches the EP Open Data API `identifier`). |
| `full_name` | string | 0 | MEP name as recorded in the roll-call. |
| `last_name` | string | 0 | Surname. |
| `first_name` | string | 0 | Given name(s). |
| `country` | string | 0 | 2-letter member-state code (e.g. `EL`). 100% populated. |
| `country_name` | string | 0 | Member-state name in English. |
| `ep_party_group` | string | 0 | EP political group. One of `PPE`, `S&D`, `Renew`, `ECR`, `PfE`, `Verts/ALE`, `The Left`, `ESN`, `NI`. |
| `ep_party_group_full` | string | 0 | Full group name. |
| `national_party` | string | 688 | **Not populated in the current pipeline version.** |
| `vote` | string | 0 | `for`, `against`, or `abstain`. |
| `vote_numeric` | integer | 0 | Numeric encoding: `1` (for), `-1` (against), `0` (abstain). |
| `vote_date` | date (YYYY-MM-DD) | 0 | Date of the vote (`2024-11-27` for all rows). |

---

## 5. `work_programme_items.csv` (113 rows)

Items from the four annexes of the Commission Work Programme 2025 (adopted 11 Feb 2025).

| Column | Type | Null | Description |
|--------|------|------|-------------|
| `item_id` | string | 0 | **Primary key.** Sequential code (`WP001`...). |
| `annex` | string | 0 | Source annex: `I` (new initiatives, 35), `II` (REFIT, 34), `III` (interim evaluations, 3), `IV` (withdrawals/repeals, 41). |
| `item_number` | float | 0 | Row number within the source annex table. |
| `title` | string | 0 | Item title. For Annex IV this contains the COM document reference plus a status description. |
| `description` | string | 72 | Additional descriptive text, where present. |
| `policy_area` | string | 79 | Policy area, where the source table provided one. |
| `type_of_act` | string | 69 | Legal instrument for the item (`REGULATION`, `DIRECTIVE`, `DECISION`, `RECOMMENDATION`), populated mainly for Annex IV. **See Known Limitations:** label casing is inconsistent, and three rows carry a timing string here instead of an instrument. |
| `indicative_timing` | float | 73 | For Annex IV items, the year of the original COM proposal (parsed from `COM(YYYY)`). Sparsely populated; not a planned-delivery quarter. |

---

## 6. `formation_timeline.csv` (13 rows)

Key institutional milestones from the EP elections to CWP adoption (250-day span).

| Column | Type | Null | Description |
|--------|------|------|-------------|
| `event_id` | string | 0 | **Primary key.** Sequential code (`T01`...). |
| `date` | date (YYYY-MM-DD) | 0 | Event date (start date for multi-day events). |
| `event_name` | string | 0 | Short event name. |
| `event_description` | string | 0 | One-sentence description. |
| `event_type` | string | 0 | One of `election`, `nomination`, `vote`, `hearing`, `institutional`, `document`. |
| `institution` | string | 0 | Lead institution: `European Parliament`, `European Council`, `European Commission`, `Council of the EU`. |
| `document_url` | string | 12 | URL of an associated document, where one exists. |

---

## Cross-Table Keys and Join Caveats

```
commissioners.commissioner_id  ──→  mission_letter_commitments.commissioner_id   [1:many]
commissioners.commissioner_id  ──→  hearings.commissioner_id                     [1:1, excl. President]
commissioners.ep_party_group   ──→  investiture_vote.ep_party_group              [shared dimension*]
```

\* **EPP / PPE label mismatch.** The EPP group is labelled `EPP` in
`commissioners.csv` but `PPE` in `investiture_vote.csv`. A naive merge on
`ep_party_group` will not match these two. Harmonise the labels before joining,
e.g.:

```python
votes["ep_party_group"] = votes["ep_party_group"].replace({"PPE": "EPP"})
```

All other shared group labels (`S&D`, `Renew`, `ECR`, `PfE`) match across the
two tables. Groups present only among MEPs (`Verts/ALE`, `The Left`, `ESN`,
`NI`) have no commissioner counterpart.

`work_programme_items` and `formation_timeline` are standalone tables with no
foreign key into the others.

---

## Known Limitations

- **`investiture_vote.national_party`** is empty in this release; only EP group
  affiliation is provided.
- **`hearings`** URL columns (`evaluation_letter_url`, `written_questions_url`,
  `video_url`) are reserved placeholders and are not yet populated.
- **`work_programme_items.type_of_act`** has inconsistent casing (e.g.
  `REGULATION` vs `Regulation`); normalise with `.str.upper()` before counting.
  Three Annex II/III rows additionally carry a timing string (`Q2 2025`) in this
  field rather than a legal instrument.
- **`work_programme_items.indicative_timing`** holds the year of the original
  proposal for Annex IV withdrawals, not a forward-looking delivery date.

---

## Provenance and Licence

Sources, extraction methods, and accuracy notes are documented in
[README.md](README.md). Data is released under CC-BY-4.0; pipeline code under
Apache-2.0.
