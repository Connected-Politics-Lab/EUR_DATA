# Codebook - Commission Legislative-Agenda Implementation Dataset

Variable-level documentation for the five output tables in `data/output/`. The
dataset links the planned agenda from the sibling `commission_formation` dataset
to its real legislative fate, resolved against the EP Open Data API and EUR-Lex.
All CSVs are encoded UTF-8 with BOM (Excel-friendly).

---

## 1. `agenda_items.csv` - the agenda spine

One row per tracked agenda item (190: 127 CWP work-programme items + 63
legislative mission-letter commitments).

| Column | Type | Description |
|--------|------|-------------|
| `agenda_item_id` | string | **Primary key** (`AI0001`...). |
| `source_scope` | enum | `cwp_annex_i` / `cwp_annex_ii` / `cwp_annex_iii` / `cwp_annex_iv` / `mission_letter`. |
| `wp_item_id` | string | **FK** -> `commission_formation/.../work_programme_items.csv:item_id`. Blank for mission-letter rows. |
| `commitment_id` | string | **FK** -> `mission_letter_commitments.csv:commitment_id`. Blank for CWP rows. |
| `title` | string | Item title (or commitment short text). |
| `policy_area` | string | Policy area / portfolio, where available. |
| `indicative_timing` | string | Carried from the work programme (`Q2 2025`, or an Annex IV origin year). |
| `expected_act_type` | string | REGULATION / DIRECTIVE / ... where stated. |

---

## 2. `procedure_references.csv` - parsed procedure identifiers

One row per (agenda item x interinstitutional procedure reference). 38 rows.

| Column | Type | Description |
|--------|------|-------------|
| `procedure_ref_id` | string | **Primary key** (`PR0001`...). |
| `agenda_item_id` | string | **FK** -> `agenda_items`. |
| `interinstitutional_ref` | string | Canonical `YYYY/NNNN(TYPE)`, e.g. `2011/0314(CNS)`. Split procedures carry a letter suffix on the number (`2018/0063B(COD)`). |
| `process_id_ep` | string | EP API form, `YYYY-NNNN`, e.g. `2011-0314`. The API lookup key. |
| `procedure_type` | enum | `COD`/`CNS`/`NLE`/`APP`/... |
| `com_reference` | string | Originating `COM(YYYY)NNN` / `JOIN(YYYY)NNN` document, where present. |
| `celex` | string | EUR-Lex CELEX of the proposal document (script 06). Blank if unresolved. |
| `extraction_method` | enum | `regex_interleaved` (parsed from CWP prose), `manual` / `manual_annex_i` (curated). |
| `match_confidence` | float | 1.0 for parsed/curated references; reserved for uncertain Annex I links. |

---

## 3. `procedure_status.csv` - the implementation time series (core)

Append-only; one row per (procedure reference x snapshot date). Re-runs append a
new `as_of_date` rather than overwriting.

| Column | Type | Description |
|--------|------|-------------|
| `status_id` | string | **Primary key** (`PR0001_2026-06-22`). |
| `procedure_ref_id` | string | **FK** -> `procedure_references`. |
| `agenda_item_id` | string | **FK** -> `agenda_items`. |
| `as_of_date` | date | Snapshot date. |
| `status` | enum | Normalised stage (see ladder below). |
| `ep_stage_code` | string | Raw EP `procedure-phase` code (audit), e.g. `RDG1`. |
| `latest_event_type` | string | Most recent EP activity type. |
| `latest_event_date` | date | Date of the most recent event. |
| `proposed_date` | date | Earliest event (proxy for tabling). |
| `delivered` | bool | `status in {adopted, in_force}`. |
| `on_time` | Int64 | 1 = on/before indicative timing, -1 = late/overdue, 0 = no target / n.a. |
| `withdrawn` | bool | `status == withdrawn`. |

**Status ladder** (ordered): `not_started -> proposed -> ep_1st_read ->
council_1st -> ep_2nd_read -> ep_3rd_read -> adopted -> in_force`. Off-ladder
terminal states: `withdrawn`, `rejected`, `lapsed`. `not_found` = the reference
did not resolve in the EP API; `in_progress` = an EP phase code we do not map.
The phase-code -> status map lives in `config.PHASE_CODE_TO_STATUS` with a
substring fallback in `scripts/status_map.py`.

---

## 4. `term_legislative_output.csv` - baseline corpus

Catalogue of every COD/CNS/NLE/APP procedure opened in 2024-2026 (the
denominator). One row per procedure.

| Column | Type | Description |
|--------|------|-------------|
| `proc_output_id` | string | **Primary key** (`TO00001`...). |
| `interinstitutional_ref` | string | `YYYY/NNNN(TYPE)`; may carry a split-procedure suffix (`2016/0400B(COD)`) or a renewal/amendment suffix (`2024/0101R(NLE)`, `...M(NLE)`). |
| `process_id_ep` | string | EP API id. |
| `procedure_type` | enum | COD/CNS/NLE/APP. |
| `year` | int | Procedure year. |
| `is_in_agenda` | bool | True if this procedure is referenced by a CWP agenda item. |
| `as_of_date` | date | Snapshot date. |

This is a catalogue, not a status table: detailed stage is resolved only for
agenda-linked procedures (table 3) in this release.

---

## 5. `evaluations.csv` - curated Annex II/III evaluations

One row per Annex II (REFIT / fitness check) or Annex III (interim) evaluation.
37 rows. Curated via `data/manual/annex_ii_evaluations.csv` (scaffolded on
first run, keyed on the stable `wp_item_id`); uncoded items default to
`delivered = False`. **In this release nothing has been curated yet**: every
`swd_celex` and `published_date` is blank and every `delivered = False` is the
uncoded default, not an observed non-delivery. `evaluation_type` is inferred
from the item title (`fitness_check` / `interim_evaluation` / `evaluation`;
`refit` is reserved for curation and does not occur in v1).

| Column | Type | Description |
|--------|------|-------------|
| `evaluation_id` | string | **Primary key** (`EV0001`...). |
| `agenda_item_id` | string | **FK** -> `agenda_items`. |
| `evaluation_type` | enum | `refit` / `fitness_check` / `interim_evaluation` / `evaluation`. |
| `swd_celex` | string | CELEX of the evaluation Staff Working Document, where coded. |
| `published_date` | date | Publication date, where coded. |
| `delivered` | bool | Whether the evaluation has been published. |
| `as_of_date` | date | Snapshot date. |

---

## Source-data reconciliation (important)

Two aspects of the sibling `work_programme_items.csv` matter when joining
across the two datasets:

- **Annex III is evaluations, not withdrawals.** The three Annex III rows are
  *interim/mid-term evaluations* (Horizon Europe, ERDF/CF/JTF, ESF+). They
  carry no procedure number, so they are tracked as evaluations (table 5), not
  procedures. (Earlier sibling documentation mislabelled Annex III as
  withdrawals; corrected upstream 2026-07-04, along with a column swap that had
  placed Annex II titles in `policy_area` and timings in `title`.)
- **Procedure references are interleaved with prose.** The COM and
  interinstitutional references in Annex III/IV live inside the `title` /
  `description` text, not in clean columns, so `02_parse_procedure_refs.py`
  extracts them with a regex anchored on the parenthesised procedure-type token.

## Known limitations

- **Withdrawal is not an EP stage.** Annex IV items are proposals the Commission
  intends to withdraw. The EP API reports their stage as still pending (commonly
  `ep_1st_read`); it does not record the Commission's withdrawal. So a "stuck at
  first reading" status for an Annex IV item is the expected signal, and
  `delivered`/`withdrawn` will read False/False until a withdrawal is confirmed
  (a future EUR-Lex-based check). Of 41 Annex IV items, 37 carry a resolvable
  procedure reference; the other 4 are "envisaged repeals" of in-force law,
  identified in the CWP text by CELEX number only. Those CELEX identifiers are
  not extracted in this release, so the 4 items have no row in
  `procedure_references.csv`.
- **Annex I matching is curated.** New initiatives have no procedure number
  until tabled. Their names are now captured (e.g. "EU Space Act"), but these are
  policy brand names that do not reliably match the formal legal titles the EP
  uses, so automated matching is unreliable (a correct link scores no higher than
  spurious ones). Links come from a curated override file; the opt-in fuzzy
  suggester is review-only and never writes to the dataset.
- **`on_time` is meaningful only for quarter-form timings.** Annex IV
  `indicative_timing` is the *origin year* of the old proposal, not a delivery
  deadline, so `on_time` is 0 (n.a.) for those rows by design.
- **The corpus and status tables are live snapshots.** Counts change as the term
  progresses; `verify_readme.py --fix` re-aligns the README after a re-fetch.

---

## Provenance and Licence

Sources: EP Open Data API v2 and the EUR-Lex Cellar SPARQL endpoint. Figures in
[README.md](README.md) are verified against the CSVs by `verify_readme.py`.
Derived data under CC-BY-4.0; pipeline code under Apache-2.0.
