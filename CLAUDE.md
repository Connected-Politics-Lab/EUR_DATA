# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

EUR_DATA is a mono-repo holding the outputs of the EUR_DATA Erasmus+ Jean Monnet Module (grant 101127178), maintained by the Connected Politics Lab. It contains the Quarto project website, the open-access dataset pipelines and their published outputs, and open educational resources. The repository is hosted at https://github.com/Connected-Politics-Lab/EUR_DATA and the site is served at https://connected-politics-lab.github.io/EUR_DATA/.

## Tech Stack

- **Quarto** static website (project type: `website`)
- Theme: `cosmo` (Bootstrap)
- Output rendered to `docs/` for GitHub Pages deployment

## Project Structure

```
EUR_DATA/                       # repo root (Pages serves from docs/)
├── _quarto.yml                 # Site configuration (navbar, theme, output-dir)
├── styles.css                  # Custom CSS overrides
├── index.qmd                   # Home page
├── data.qmd                    # Data & Outputs (visualisations go here)
├── about.qmd                   # About the project
├── oer.qmd                     # Open educational resources
├── .nojekyll                   # Tells GitHub Pages to skip Jekyll processing
├── .gitignore                  # Ignores .quarto/, caches, dataset raw/logs
├── LICENSE / LICENSE-DATA.md   # Apache-2.0 (code) / CC-BY-4.0 (data)
├── CITATION.cff / .zenodo.json # Citation and Zenodo deposit metadata
├── datasets/
│   └── commission_formation/   # Pipeline code, codebook, data/output/ (raw gitignored)
├── oer/                        # Open educational resources (syllabi, slides, briefs)
└── docs/                       # Rendered output (committed for GitHub Pages)
```

## Build Commands

```bash
# Preview locally (live reload)
quarto preview

# Render site into docs/
quarto render
```

If `quarto` is not on PATH, use the RStudio-bundled binary:

```bash
/Applications/RStudio.app/Contents/Resources/app/quarto/bin/quarto render
```

## Deployment

GitHub Pages serves from the `docs/` directory on the main branch. After making changes:

1. Edit `.qmd` files
2. Run `quarto render`
3. Commit the updated `docs/` directory
4. Push to main

## Key Conventions

- Output directory is `docs/` (not `_site/`) — do NOT add `docs/` to `.gitignore`
- All pages use the `cosmo` theme; custom styles go in `styles.css`
- The `.nojekyll` file must remain in the project root for GitHub Pages

## License

Dual-licensed: code (pipeline scripts, website source) under Apache License 2.0; data under `datasets/**/data/output/` under CC-BY-4.0. See `LICENSE` and `LICENSE-DATA.md`. Contributions must be compatible with the applicable licence.
