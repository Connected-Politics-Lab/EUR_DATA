"""
06_enrich_eurlex.py
Cross-check the procedure references against EUR-Lex: resolve each COM/JOIN
document reference to its CELEX number via the Cellar SPARQL endpoint and write
it back into procedure_references.celex.

Best-effort enrichment: any failure leaves `celex` blank and never breaks the
pipeline. The EP API remains authoritative for procedure stage; EUR-Lex adds the
stable document identifier (and a basis for future in-force checks).
Network access; SPARQL responses cached under data/raw/.
"""

import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, save_both, sparql_query

# COM -> "PC" (legislative proposal), JOIN -> "JC" (joint proposal) CELEX descriptor.
_COM_RE = re.compile(r"(COM|JOIN)\((\d{4})\)(\d+)")
_DESCRIPTOR = {"COM": "PC", "JOIN": "JC"}


def _candidate_celex(com_reference: str):
    m = _COM_RE.search(com_reference or "")
    if not m:
        return None
    kind, year, num = m.group(1), m.group(2), int(m.group(3))
    return f"5{year}{_DESCRIPTOR[kind]}{num:04d}"


def _celex_exists(celex: str) -> bool:
    q = (
        "PREFIX cdm: <http://publications.europa.eu/ontology/cdm#>\n"
        "SELECT ?work WHERE { ?work cdm:resource_legal_id_celex ?c .\n"
        f'  FILTER(STR(?c) = "{celex}") }} LIMIT 1'
    )
    return len(sparql_query(q)) > 0


def main():
    logger = setup_logging("06_eurlex")
    ensure_dirs()

    refs = pd.read_csv(config.OUTPUT_DIR / "procedure_references.csv")
    if "celex" not in refs.columns:
        refs["celex"] = ""

    def _empty(v) -> bool:
        return v is None or (isinstance(v, float) and pd.isna(v)) or not str(v).strip()

    resolved = 0
    for idx, r in refs.iterrows():
        if not _empty(r.get("celex")):
            continue  # already resolved (cache-friendly)
        com = r.get("com_reference")
        celex = _candidate_celex("" if _empty(com) else str(com))
        if celex and _celex_exists(celex):
            refs.at[idx, "celex"] = celex
            resolved += 1

    save_both(refs, "procedure_references")
    logger.info(f"EUR-Lex: resolved CELEX for {resolved}/{len(refs)} references.")
    return refs


if __name__ == "__main__":
    main()
