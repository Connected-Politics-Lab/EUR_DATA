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
| `commissioner_id` | string | 0 | **Primary key.** Three-letter code per commissioner (e.g. `MAS`). Foreign key target for `hearings` and `mission_letter_commitments`. **IDs are not surname prefixes; see the mapping table below.** |
| `full_name` | string | 0 | Commissioner's full name. |
| `last_name` | string | 0 | Surname. |
| `first_name` | string | 0 | Given name(s). |
| `country` | string | 0 | 2-letter member-state code, EU convention (`EL` for Greece, not ISO `GR`). |
| `country_name` | string | 0 | Member-state name in English. |
| `portfolio_title` | string | 0 | Full portfolio title (e.g. *Commissioner for Financial Services*). |
| `role` | string | 0 | One of `President`, `Executive Vice-President`, `High Representative/Vice-President`, `Commissioner`. |
| `ep_party_group` | string | 0 | EP political group affiliation. One of `EPP`, `S&D`, `Renew`, `ECR`, `PfE`, `Independent`. **Note the label mismatch with `investiture_vote` (see Join Caveats).** |
| `national_party` | string | 0 | National party abbreviation (e.g. `PSD`); `Independent` for Kadis. |
| `gender` | string | 0 | `F` or `M`. |
| `dgs_responsible` | string | 0 | Directorate(s)-General the commissioner oversees (e.g. `FISMA`). |
| `mission_letter_url` | string | 1 | URL of the presidential mission letter PDF. Null for the President (no mission letter). |
| `hearing_date` | date (YYYY-MM-DD) | 1 | Confirmation hearing date, verified against the EP press releases (see `hearings.source_url`). Null for the President (no hearing). |
| `profile_url` | string | 0 | URL of the commissioner's official EC profile page. |

### Coding notes

- **Party affiliation is coded as at nomination.** Sefcovic is coded `S&D`
  although his national party (Smer) has been suspended from the PES since
  October 2023; this is a deliberate coding decision.
- **Kadis (Cyprus) is a non-partisan technocrat**, coded
  `Independent`/`Independent` (national party / EP group). EPP therefore has 14
  of 27 members (52%).
- **EVP counting convention.** This dataset codes 5 `Executive Vice-President`
  rows and records the High Representative/Vice-President (Kallas) as a
  separate role. The Commission's own communications count six EVPs including
  Kallas; under that convention women hold 4 of 6 EVP posts (under the dataset
  convention: 3 of 5). Both statements describe the same College.

### Commissioner ID mapping

**Warning: `commissioner_id` values are NOT surname prefixes.** Several codes
collide with *other* commissioners' names: `FIT` is Ribera (not Fitto, who is
`RAF`); `KOS` is Kallas (Kos is `MAR`); `SEJ` is Virkkunen (Sejourne is `STE`);
`DUB` is Sefcovic (Suica is `DUP`). The IDs are stable pipeline keys and are
deliberately documented rather than renamed. Always join through this table;
never infer identity from the code.

| `commissioner_id` | Commissioner | Role |
|-------------------|--------------|------|
| `AND` | Andrius Kubilius | Commissioner |
| `APO` | Apostolos Tzitzikostas | Commissioner |
| `CHR` | Christophe Hansen | Commissioner |
| `COS` | Costas Kadis | Commissioner |
| `DAN` | Dan Jorgensen | Commissioner |
| `DUB` | Maros Sefcovic | Commissioner |
| `DUP` | Dubravka Suica | Commissioner |
| `EKA` | Ekaterina Zaharieva | Commissioner |
| `FIT` | Teresa Ribera | Executive Vice-President |
| `GLE` | Glenn Micallef | Commissioner |
| `HAD` | Hadja Lahbib | Commissioner |
| `JES` | Jessika Roswall | Commissioner |
| `JOZ` | Jozef Sikela | Commissioner |
| `KOS` | Kaja Kallas | High Representative/Vice-President |
| `MAG` | Magnus Brunner | Commissioner |
| `MAR` | Marta Kos | Commissioner |
| `MAS` | Maria Luis Albuquerque | Commissioner |
| `MIC` | Michael McGrath | Commissioner |
| `OLI` | Oliver Varhelyi | Commissioner |
| `PIO` | Piotr Serafin | Commissioner |
| `RAF` | Raffaele Fitto | Executive Vice-President |
| `ROS` | Roxana Minzatu | Executive Vice-President |
| `SEJ` | Henna Virkkunen | Executive Vice-President |
| `STE` | Stephane Sejourne | Executive Vice-President |
| `VAL` | Valdis Dombrovskis | Commissioner |
| `VDL` | Ursula von der Leyen | President |
| `WOP` | Wopke Hoekstra | Commissioner |

---

## 2. `mission_letter_commitments.csv` (1057 rows)

Policy commitments extracted from the 26 presidential mission letters.

| Column | Type | Null | Description |
|--------|------|------|-------------|
| `commitment_id` | string | 0 | **Primary key.** Sequential code (`C0001`...). |
| `commissioner_id` | string | 0 | **Foreign key** to `commissioners.commissioner_id`. 26 distinct values (no President). |
| `commissioner_name` | string | 0 | Denormalised commissioner full name. |
| `portfolio_title` | string | 0 | Denormalised portfolio title. |
| `commitment_text` | string | 0 | Full text of the commitment as extracted. 562 distinct texts across the 1057 rows (see `is_boilerplate`). |
| `commitment_short` | string | 0 | Truncated summary; guaranteed <=100 characters including the ellipsis. |
| `section_heading` | string | 564 | Heading of the letter section the commitment falls under, where one could be identified. |
| `commitment_type` | string | 0 | One of `coordination`, `policy`, `report`, `review`, `legislative`, `other`. Assigned by an LLM classifier (Claude Sonnet 4.6) reading the full commitment; a keyword classifier is the fallback when the model is unavailable (see `classification_method`). |
| `classification_method` | string | 0 | How `commitment_type` was assigned: `llm` (Sonnet 4.6, cached) or `keyword` (heuristic fallback). |
| `extraction_method` | string | 0 | How the commitment was identified: `bullet_point`, `directive_sentence`, `legislative_reference`. |
| `confidence` | string | 0 | `high` (bullet-point extraction, 440 rows) or `medium` (directive/legislative, 617 rows). |
| `page_number` | integer | 0 | Page of the source PDF the commitment appears on. |
| `raw_paragraph` | string | 0 | Surrounding source paragraph, retained for context. |
| `n_letters_sharing_text` | integer | 0 | Number of the 26 mission letters whose text contains this exact commitment text (1 = unique to one letter, 26 = present in all). |
| `is_boilerplate` | boolean | 0 | `True` where the commitment text is shared by more than 13 of the 26 letters, i.e. `n_letters_sharing_text > 13`. |

### Boilerplate

Every mission letter closes with a near-identical block of roughly 20 shared
commitments (working methods, coordination duties, reporting obligations).
**515 of the 1057 rows (49%) are boilerplate**, covering just 20 distinct
template texts. The boilerplate includes 26 of the 63 `legislative`, 26 of the
33 `report`, and 26 of the 51 `review` commitments (one template text each),
so raw type counts and per-commissioner totals (31-59 per letter) sit on a
common floor. Filter `is_boilerplate == False` to isolate portfolio-specific
pledges.

---

## 3. `hearings.csv` (26 rows)

Confirmation hearings held 4-12 November 2024: 4 hearings on 4 Nov, 6 on 5 Nov,
6 on 6 Nov, 4 on 7 Nov, and 6 on 12 Nov (all six EVP-level nominees, heard
last). No hearings took place on 8-11 November. The schedule is verified
row-by-row against the EP's adopted hearings calendar and press releases.

| Column | Type | Null | Description |
|--------|------|------|-------------|
| `hearing_id` | string | 0 | **Primary key.** Sequential code (`H01`...). |
| `commissioner_id` | string | 0 | **Foreign key** to `commissioners.commissioner_id` (1:1, excluding the President). |
| `commissioner_name` | string | 0 | Denormalised commissioner full name. |
| `hearing_date` | date (YYYY-MM-DD) | 0 | Date of the hearing, verified against the EP press release in `source_url`. |
| `committees_responsible` | string | 0 | Lead EP committee(s). Joint-committee hearings list every lead committee (e.g. McGrath `LIBE, IMCO, JURI`; Ribera `ENVI, ECON, ITRE`). |
| `committees_associated` | string | 0 | Associated EP committee(s), where applicable. |
| `outcome` | string | 0 | Hearing outcome. All 26 are `approved`. **Note:** committee approvals are majority votes and `approved` conceals contested cases; Ribera, Fitto, and Varhelyi required further written procedures and political negotiation before the EVP evaluations were concluded as a package on 20-21 November 2024. |
| `source_url` | string | 0 | **EP press release for the hearing**: the source against which the date and committee format of each row were verified. |
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
| `country` | string | 0 | 2-letter member-state code, EU convention (`EL` for Greece). 100% populated. |
| `country_name` | string | 0 | Member-state name in English. |
| `ep_party_group` | string | 0 | EP political group. One of `PPE`, `S&D`, `Renew`, `ECR`, `PfE`, `Verts/ALE`, `The Left`, `ESN`, `NI`. |
| `ep_party_group_full` | string | 0 | Full group name (e.g. `European People's Party` for `PPE`); never equal to the short code. |
| `national_party` | string | 688 | **Not populated in the current pipeline version.** |
| `vote` | string | 0 | `for`, `against`, or `abstain`. Only these three values occur: MEPs who did not vote are simply absent from the table (there are no `did_not_vote` rows). |
| `vote_numeric` | integer | 0 | Numeric encoding: `1` (for), `-1` (against), `0` (abstain). |
| `vote_date` | date (YYYY-MM-DD) | 0 | Date of the vote (`2024-11-27` for all rows). |

---

## 5. `work_programme_items.csv` (130 rows)

Items from the Commission Work Programme 2025 (COM(2025) 45, adopted 11 Feb
2025), extracted from the official annexes document ("ANNEXES 1 to 5"). The
dataset covers Annexes I (52 items), II (37), IV (37), and V (4). The official
**Annex III (Pending proposals, 123 dossiers) is deliberately not extracted**:
it is out of scope here, and pending files are tracked in the
agenda_implementation dataset's term corpus.

| Column | Type | Null | Description |
|--------|------|------|-------------|
| `item_id` | string | 0 | **Primary key.** Sequential code (`WP001`...). |
| `annex` | string | 0 | Source annex: `I` (new initiatives, 52), `II` (annual plan on evaluations and fitness checks, 37), `IV` (withdrawals of pending proposals, 37), `V` (envisaged repeals of acts in force, 4). |
| `item_number` | integer | 0 | Row number within the source annex table. Annex I numbers repeat where one numbered entry lists several initiatives: 52 initiatives are unpacked from 45 numbered rows. |
| `title` | string | 0 | Item title. For Annex I this is the initiative name; for Annexes IV and V it names the instrument and subject of the proposal or act. |
| `description` | string | 89 | Empty for Annexes I and II. For Annex IV: `References: ... Reasons for withdrawal: ...` (COM references plus the Commission's stated reasons); for Annex V: `Reasons for repeal: ...`. |
| `policy_area` | string | 74 | Policy area / objective. Populated for Annexes I and V; empty for II and IV, whose source tables carry no policy-area column. |
| `type_of_act` | string | 37 | Null **exactly for the 37 Annex II rows** (the source table carries no act type for evaluations). Annex I: the initiative's nature (`Legislative` 18, `Non-legislative` 33, `Non-legislative or legislative` 1). Annexes IV and V: the legal instrument named in the title, upper-cased (`REGULATION`, `DIRECTIVE`, `DECISION`, `RECOMMENDATION`). |
| `indicative_timing` | string | 41 | Annex I: the planned quarter (e.g. `Q2 2025`); one Annex I row (`An EU fit for enlargement`) is `tbd`. Annex II: the indicative finalisation quarter. Empty for Annexes IV and V (the source tables carry no timing). |

**Withdrawals are not repeals.** Annex IV withdraws *pending proposals* that
were never adopted (instruments named in titles: 22 `REGULATION`, 10
`DIRECTIVE`, 4 `DECISION`, 1 `RECOMMENDATION`); Annex V envisages repeals of
*acts in force* (3 `REGULATION`, 1 `DECISION`).

---

## 6. `formation_timeline.csv` (13 rows)

Key institutional milestones from the EP elections to CWP adoption (250-day span).

| Column | Type | Null | Description |
|--------|------|------|-------------|
| `event_id` | string | 0 | **Primary key.** Sequential code (`T01`...). |
| `date` | date (YYYY-MM-DD) | 0 | Event date (start date for multi-day events). |
| `event_name` | string | 0 | Short event name. `T10` records the Conference of Presidents formally concluding the hearings process on 27 November 2024 (after the Conference of Committee Chairs on 26 November). |
| `event_description` | string | 0 | One-sentence description. `T09` names all six EVP-level nominees heard on the final hearing day. |
| `event_type` | string | 0 | One of `election`, `nomination`, `vote`, `hearing`, `institutional`, `document`. |
| `institution` | string | 0 | Lead institution: `European Parliament`, `European Council`, `European Commission`, `Council of the EU`. |
| `document_url` | string | 12 | URL of an associated document, where one exists. `T13` (CWP adoption) links to EUR-Lex (CELEX:52025DC0045). |

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
`NI`) have no commissioner counterpart, and the `Independent` label (Kadis)
has no MEP counterpart.

`work_programme_items` and `formation_timeline` are standalone tables with no
foreign key into the others.

---

## Known Limitations

- **Commitment boilerplate**: 515 of the 1057 commitment rows (49%) are
  template text shared across letters; use `is_boilerplate` (or
  `n_letters_sharing_text`) to separate portfolio-specific pledges from the
  shared closing block.
- **`investiture_vote.national_party`** is empty in this release; only EP group
  affiliation is provided.
- **`hearings`** URL columns (`evaluation_letter_url`, `written_questions_url`,
  `video_url`) are reserved placeholders and are not yet populated.
- **`hearings.outcome`** records only the final result; it conceals the
  contested and delayed approvals documented in the column note above.
- **`work_programme_items`** excludes the official CWP Annex III (pending
  proposals) by design; see table 5.

---

## Provenance and Licence

Sources, extraction methods, and accuracy notes are documented in
[README.md](README.md). Data is released under CC BY 4.0; pipeline code under
Apache-2.0. EP and EC source documents are © European Union, reused under
Commission Decision 2011/833/EU.
