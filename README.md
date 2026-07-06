# EUR_DATA

Open data, code, and educational resources from the **EUR_DATA** project:
*Integrating EU studies and Data Analytics using a Project-based Learning
Approach*. EUR_DATA is an Erasmus+ Jean Monnet Module (grant 101127178),
coordinated by [James Cross](https://orcid.org/0000-0001-8042-1099) at
University College Dublin and maintained by the
[Connected Politics Lab](https://github.com/Connected-Politics-Lab).

The project website is published at
<https://connected-politics-lab.github.io/EUR_DATA/>.

## What's here

```
EUR_DATA/
├── index.qmd, data.qmd, about.qmd, oer.qmd   # Quarto website source
├── docs/                                      # Rendered site (GitHub Pages)
├── datasets/
│   ├── commission_formation/                  # Dataset pipeline, codebook, and outputs
│   ├── election_data/                         # euandi 2024 VAA coding (Ireland + EU-level)
│   └── agenda_implementation/                 # Legislative-agenda implementation tracking
├── oer/                                        # Open educational resources
├── LICENSE                                     # Apache-2.0 (code)
├── CITATION.cff                                # How to cite
└── .zenodo.json                               # Zenodo deposit metadata
```

## Datasets

| Dataset | Description | Docs |
|---------|-------------|------|
| **Commission Formation (2024-2029)** | The formation of the von der Leyen II Commission: the College (27), mission-letter commitments (1057), confirmation hearings (26), the investiture vote (688 MEPs), the 2025 Work Programme (130 items), and a formation timeline (13 events). | [README](datasets/commission_formation/README.md) · [Codebook](datasets/commission_formation/CODEBOOK.md) |
| **euandi 2024 (EP election)** | euandi 2024 Voting Advice Application coding for the June 2024 European Parliament election: 19 Irish parties and candidates and 10 EU-level party families placed on 36 policy statements, with salience. | [README](datasets/election_data/README.md) · [Codebook](datasets/election_data/CODEBOOK.md) |
| **Commission Agenda Implementation** | Implementation tracking of the Commission's legislative agenda: 193 agenda items (130 CWP 2025 items + 63 legislative mission-letter commitments), 38 tracked procedures with dated status snapshots, and a 169-procedure term corpus. | [README](datasets/agenda_implementation/README.md) · [Codebook](datasets/agenda_implementation/CODEBOOK.md) |

Each dataset ships with reproducible pipeline code, a column-level codebook, and
a test suite. Published outputs live under `data/output/` as CSV and XLSX.

## Reproducing a dataset

```bash
cd datasets/commission_formation
pip install -r requirements.txt
python run_pipeline.py        # rebuild all outputs from source
pytest tests/ -v              # validate row counts and schemas
python verify_readme.py       # check documented figures against the data
```

## Licensing

This repository is dual-licensed:

- **Code** (pipeline scripts, website source): [Apache License 2.0](LICENSE).
- **Data** (everything under `datasets/**/data/output/`): [Creative Commons
  Attribution 4.0 International (CC-BY-4.0)](https://creativecommons.org/licenses/by/4.0/).
- **Educational resources** (`oer/`): CC-BY-4.0 unless a resource states otherwise.

## Citing

If you use EUR_DATA, please cite it. See [CITATION.cff](CITATION.cff) or the
"Cite this repository" link on GitHub. A DOI is minted for each release via
Zenodo; the concept DOI
[10.5281/zenodo.21221494](https://doi.org/10.5281/zenodo.21221494) always
resolves to the latest release.

[![DOI](https://zenodo.org/badge/DOI/10.5281/zenodo.21221494.svg)](https://doi.org/10.5281/zenodo.21221494)

## Acknowledgement

Co-funded by the European Union under the Erasmus+ Programme, Jean Monnet
Actions (grant 101127178). Views and opinions expressed are those of the
author(s) only and do not necessarily reflect those of the European Union or
the European Education and Culture Executive Agency (EACEA). Neither the
European Union nor EACEA can be held responsible for them.
