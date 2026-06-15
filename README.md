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
│   └── commission_formation/                  # Dataset pipeline, codebook, and outputs
├── oer/                                        # Open educational resources
├── LICENSE                                     # Apache-2.0 (code)
├── CITATION.cff                                # How to cite
└── .zenodo.json                               # Zenodo deposit metadata
```

## Datasets

| Dataset | Description | Docs |
|---------|-------------|------|
| **Commission Formation (2024-2029)** | The formation of the von der Leyen II Commission: the College, mission-letter commitments, confirmation hearings, the investiture vote, the 2025 Work Programme, and a formation timeline. | [README](datasets/commission_formation/README.md) · [Codebook](datasets/commission_formation/CODEBOOK.md) |

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
Zenodo.

## Acknowledgement

Co-funded by the European Union under the Erasmus+ Programme, Jean Monnet
Actions (grant 101127178). Views and opinions expressed are those of the
author(s) only and do not necessarily reflect those of the European Union or
the European Education and Culture Executive Agency (EACEA). Neither the
European Union nor EACEA can be held responsible for them.
