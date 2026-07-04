# Commission Legislative-Agenda Implementation Dataset

How far has the 2024-2029 von der Leyen II Commission implemented the
legislative agenda it set itself? This dataset links each planned agenda item
to its real legislative fate, resolved against the **European Parliament Open
Data API** (the machine-readable backend of the Legislative Observatory / OEIL)
and cross-checked in **EUR-Lex**. It is the first dataset in this repo to track
*outcomes* rather than intentions, and it is built as a **time series**: each
status row carries an `as_of_date`, and re-runs append dated snapshots.

It sits on top of the sibling [`commission_formation`](../commission_formation)
dataset: every agenda item links back to that dataset's `work_programme_items`
or `mission_letter_commitments` via a foreign key, and no sibling content is
duplicated.

## Dataset at a Glance

| File | Rows | Description |
|------|------|-------------|
| `agenda_items.csv` | 190 | The agenda spine - every CWP item + legislative commitment |
| `procedure_references.csv` | 38 | Interinstitutional procedure references parsed from the agenda |
| `procedure_status.csv` | 38 | **Core deliverable**: dated status snapshot per procedure |
| `term_legislative_output.csv` | 169 | Baseline corpus of all term procedures (the denominator) |
| `evaluations.csv` | 37 | Curated Annex II/III evaluation tracking |

## Scope

The dataset tracks **190 tracked agenda items**: the 127 CWP 2025 work-programme
items plus the 63 legislative mission-letter commitments. By source:

- **49 new initiatives** (CWP Annex I),
- 34 REFIT evaluations (Annex II),
- 3 interim evaluations (Annex III),
- **41 repeals/withdrawals** of obsolete proposals (Annex IV),
- **63 legislative mission-letter** commitments.

The ~1,000 non-legislative mission-letter pledges (coordination, reports, vague
"other") are deliberately out of scope: they have no resolvable legislative
identifier and cannot be tracked as a pipeline.

## How implementation is measured

Each procedure with a resolvable reference is placed on an ordered **status
ladder** read from the EP API:

```
not_started -> proposed -> ep_1st_read -> council_1st -> ep_2nd_read
-> ep_3rd_read -> adopted -> in_force        (off-ladder: withdrawn / rejected / lapsed)
```

From this we derive `delivered` (= adopted or in force), `withdrawn`, and
`on_time` (delivery vs the item's indicative timing). Of the 38 procedure
references, 35 resolved against the EP API (3 return `not_found`; one of these,
`2024/0094(NLE)`, appears in neither the EP API nor EUR-Lex and may be
unresolvable). 37 of the 38 resolved to a EUR-Lex CELEX identifier. As of the
latest snapshot, 0 had been adopted or entered into force
- which is expected: the Annex IV references are all *old proposals the
Commission plans to withdraw*, and they sit formally pending at first reading in
Parliament (withdrawal is a Commission act, not an EP stage). This is the honest
signal the dataset is designed to capture.

The baseline corpus is a catalogue of 169 distinct term procedures (all
COD/CNS/NLE/APP dossiers for 2024-2026, one row per procedure; a procedure
re-referenced under a second type is counted once), flagged `is_in_agenda`,
giving the denominator for "planned agenda vs total legislative activity".

## Phasing and curation

- **Phase 1 (automated):** Annex IV procedure status (all 38 embedded
  procedure references sit in Annex IV), the term corpus, and the EUR-Lex CELEX
  cross-check. Replayable from the cached API responses; see the snapshot note
  below.
- **Phase 2 (curated):** Annex I new initiatives have no procedure number until
  tabled. The initiative names are now captured (e.g. "EU Space Act", "Digital
  Networks Act"), but these are *policy brand names* that do not reliably match
  the formal legal titles the EP uses for procedures, so automated linking is not
  dependable (an opt-in fuzzy suggester, `AGENDA_FUZZY=1`, writes a low-confidence
  review aid to `data/manual/annex_i_match_candidates.csv`). Authoritative links
  must be curated by hand in `data/manual/annex_i_overrides.csv` (scaffolded on
  first run); the pipeline then resolves their status.
- **Phase 3 (curated):** the 37 Annex II/III evaluations are tracked in
  `data/manual/annex_ii_evaluations.csv` (scaffolded), since the Commission
  evaluation register has no public API; `delivered` defaults to False until
  curated.

This release ships **Phase 1**: the automated Annex IV status and term corpus,
with the improved agenda spine. Annex I links and evaluation outcomes are
scaffolded for curation (`data/manual/`, keyed on the stable `wp_item_id`) and
marked forthcoming; mission-letter commitment links are planned but not yet
scaffolded.

## Reproducing

```bash
pip install -r requirements.txt
python run_pipeline.py            # steps 01-07; network steps cache to data/raw/
python run_pipeline.py --offline  # re-run from cache, no network
python -m pytest tests/ -v        # schema + counts + FK + monotonicity + parser
python verify_readme.py           # verify the figures above against the CSVs
```

The published outputs are a **frozen snapshot taken on 2026-06-22** (the
`as_of_date` stamped in the status tables). The API response cache
(`data/raw/`) is not part of the published repository, so a fresh clone
re-fetches live data and will reflect the state of the EP API and EUR-Lex at
run time, not reproduce this snapshot byte-for-byte. `AGENDA_AS_OF=YYYY-MM-DD`
pins the snapshot date *label* for reproducible runs and tests; it does not pin
the underlying data. Re-running step 04 on a later date appends a new dated
snapshot to `procedure_status.csv`.

## Provenance and Licence

Sources: EP Open Data API v2 (`data.europarl.europa.eu/api/v2`) and the EUR-Lex
Cellar SPARQL endpoint, both accessed 2026-06-22. Parliamentary data (c) European
Union, sourced from the European Parliament Open Data Portal; EUR-Lex data (c)
European Union, https://eur-lex.europa.eu. Both are reused under the Commission
Decision 2011/833/EU reuse policy, which requires acknowledgement of the source;
please retain this attribution in derived work. The status enum, parser, and
curation provenance are documented in [CODEBOOK.md](CODEBOOK.md). Derived data
released under CC-BY-4.0; pipeline code under Apache-2.0. All CSVs are encoded
UTF-8 with BOM (Excel-friendly; `readr`/pandas handle it transparently, base R
`read.csv` needs `fileEncoding = "UTF-8-BOM"`).
