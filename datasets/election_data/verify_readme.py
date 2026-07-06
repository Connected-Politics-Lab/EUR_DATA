"""
Verify every numerical claim in README.md, CODEBOOK.md and SUMMARY.md
against the actual CSV data.

Usage:
    python verify_readme.py          # report only
    python verify_readme.py --fix    # report + fix mismatches in-place
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from config import BASE_DIR, OUTPUT_DIR

# Documents whose quantitative claims are verified.
DOC_PATHS = {
    "README": BASE_DIR / "README.md",
    "CODEBOOK": BASE_DIR / "CODEBOOK.md",
    "SUMMARY": BASE_DIR / "SUMMARY.md",
}


def load_data() -> Dict[str, pd.DataFrame]:
    data = {}
    for prefix in ["ie", "eu"]:
        for table in ["parties", "statements", "positions", "salience"]:
            key = f"{prefix}_{table}"
            data[key] = pd.read_csv(OUTPUT_DIR / f"{key}.csv")
    return data


def _substantive_pct(positions: pd.DataFrame) -> int:
    """Share of placements with a substantive position: a label that is
    present (notna) and not "No opinion". Strict: NaN labels do not count."""
    labels = positions["position_label"]
    return round((labels.notna() & (labels != "No opinion")).mean() * 100)


def _no_opinion_with_source(positions: pd.DataFrame) -> int:
    """No-opinion rows that nevertheless carry at least one source field."""
    noop = positions[positions["position_label"] == "No opinion"]
    src_cols = ["source_type", "text_snippet", "source_link"]
    return int(noop[src_cols].notna().any(axis=1).sum())


def compute_actuals(d: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    a = {}
    iep, ipo, isa = d["ie_parties"], d["ie_positions"], d["ie_salience"]
    eup, epo, esa = d["eu_parties"], d["eu_positions"], d["eu_salience"]

    # Ireland
    a["ie_entities"] = len(iep)
    a["ie_parties_only"] = int((iep["entity_type"] == "party").sum())
    a["ie_independents"] = int((iep["entity_type"] == "independent_candidate").sum())
    a["ie_statements"] = len(d["ie_statements"])
    a["ie_positions"] = len(ipo)
    a["ie_salience"] = len(isa)
    a["ie_coded_pct"] = _substantive_pct(ipo)
    a["ie_noop_with_source"] = _no_opinion_with_source(ipo)

    # EU-level
    a["eu_entities"] = len(eup)
    a["eu_statements"] = len(d["eu_statements"])
    a["eu_positions"] = len(epo)
    a["eu_salience"] = len(esa)
    a["eu_coded_pct"] = _substantive_pct(epo)
    a["eu_noop_with_source"] = _no_opinion_with_source(epo)

    # Combined
    a["total_positions"] = len(ipo) + len(epo)
    a["total_noop_with_source"] = (
        a["ie_noop_with_source"] + a["eu_noop_with_source"]
    )
    return a


def _int(s: str) -> int:
    return int(s.replace(",", ""))


# (doc, check_name, actual_key, pattern, group_index, transform, section)
CHECK_DEFINITIONS = [
    # ---------------- README.md ----------------
    # Dataset-at-a-glance row counts (Ireland)
    ("README", "ie_parties.csv rows (glance)", "ie_entities",
     r"\| `ie_parties\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("README", "ie_statements.csv rows (glance)", "ie_statements",
     r"\| `ie_statements\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("README", "ie_positions.csv rows (glance)", "ie_positions",
     r"\| `ie_positions\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("README", "ie_salience.csv rows (glance)", "ie_salience",
     r"\| `ie_salience\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    # Dataset-at-a-glance row counts (EU)
    ("README", "eu_parties.csv rows (glance)", "eu_entities",
     r"\| `eu_parties\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("README", "eu_statements.csv rows (glance)", "eu_statements",
     r"\| `eu_statements\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("README", "eu_positions.csv rows (glance)", "eu_positions",
     r"\| `eu_positions\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("README", "eu_salience.csv rows (glance)", "eu_salience",
     r"\| `eu_salience\.csv` \| (\d+) \|", 1, _int, "Row Counts"),

    # Ireland prose
    ("README", "Ireland entities (prose)", "ie_entities",
     r"(\d+) coded entities", 1, _int, "Ireland"),
    ("README", "Ireland parties (prose)", "ie_parties_only",
     r"(\d+) national parties", 1, _int, "Ireland"),
    ("README", "Ireland independents (prose)", "ie_independents",
     r"(\d+) independent candidates", 1, _int, "Ireland"),
    ("README", "Ireland positions (prose)", "ie_positions",
     r"(\d+)\s+party-statement positions", 1, _int, "Ireland"),
    ("README", "Ireland coded pct (prose)", "ie_coded_pct",
     r"(\d+)%\s+of\s+Irish placements", 1, _int, "Ireland"),

    # EU prose
    ("README", "EU families (prose)", "eu_entities",
     r"(\d+) EU-level party families", 1, _int, "EU-level"),
    ("README", "EU positions (prose)", "eu_positions",
     r"(\d+)\s+family-statement positions", 1, _int, "EU-level"),
    ("README", "EU coded pct (prose)", "eu_coded_pct",
     r"(\d+)%\s+of\s+EU-level placements", 1, _int, "EU-level"),

    # Common battery / combined
    ("README", "Statements per sheet", "ie_statements",
     r"(\d+) policy statements", 1, _int, "Coding Scheme"),
    ("README", "Total positions", "total_positions",
     r"(\d+) total placements", 1, _int, "Coding Scheme"),

    # ---------------- CODEBOOK.md ----------------
    # Parties table
    ("CODEBOOK", "IE entity rows", "ie_entities",
     r"IE: (\d+) rows \((\d+) parties \+ (\d+) independent candidates\)\. "
     r"EU: (\d+) rows\.", 1, _int, "Parties"),
    ("CODEBOOK", "IE parties split", "ie_parties_only",
     r"IE: (\d+) rows \((\d+) parties \+ (\d+) independent candidates\)\. "
     r"EU: (\d+) rows\.", 2, _int, "Parties"),
    ("CODEBOOK", "IE independents split", "ie_independents",
     r"IE: (\d+) rows \((\d+) parties \+ (\d+) independent candidates\)\. "
     r"EU: (\d+) rows\.", 3, _int, "Parties"),
    ("CODEBOOK", "EU entity rows", "eu_entities",
     r"IE: (\d+) rows \((\d+) parties \+ (\d+) independent candidates\)\. "
     r"EU: (\d+) rows\.", 4, _int, "Parties"),
    # Statements table
    ("CODEBOOK", "Statement rows", "ie_statements",
     r"(\d+) rows each\. The euandi battery", 1, _int, "Statements"),
    # Positions table
    ("CODEBOOK", "IE position rows", "ie_positions",
     r"IE: (\d+) rows\s*\(\d+ x \d+\)\. EU: (\d+) rows", 1, _int, "Positions"),
    ("CODEBOOK", "EU position rows", "eu_positions",
     r"IE: (\d+) rows\s*\(\d+ x \d+\)\. EU: (\d+) rows", 2, _int, "Positions"),
    # No-opinion rows carrying source fields (source_type column note)
    ("CODEBOOK", "No-opinion rows with source (total)", "total_noop_with_source",
     r"(\d+) No-opinion rows carry source fields: (\d+) in the Ireland "
     r"dataset, (\d+) in the EU-level dataset", 1, _int, "Positions"),
    ("CODEBOOK", "No-opinion rows with source (IE)", "ie_noop_with_source",
     r"(\d+) No-opinion rows carry source fields: (\d+) in the Ireland "
     r"dataset, (\d+) in the EU-level dataset", 2, _int, "Positions"),
    ("CODEBOOK", "No-opinion rows with source (EU)", "eu_noop_with_source",
     r"(\d+) No-opinion rows carry source fields: (\d+) in the Ireland "
     r"dataset, (\d+) in the EU-level dataset", 3, _int, "Positions"),
    # Salience table
    ("CODEBOOK", "IE salience rows", "ie_salience",
     r"IE: (\d+) rows\. EU: (\d+) rows\.", 1, _int, "Salience"),
    ("CODEBOOK", "EU salience rows", "eu_salience",
     r"IE: (\d+) rows\. EU: (\d+) rows\.", 2, _int, "Salience"),
    # Same split, as restated under Known Limitations
    ("CODEBOOK", "No-opinion split restated (total)", "total_noop_with_source",
     r"(\d+) No-opinion rows do carry source fields: (\d+) in the Ireland\s+"
     r"dataset, (\d+) in the EU-level dataset", 1, _int, "Known Limitations"),
    ("CODEBOOK", "No-opinion split restated (IE)", "ie_noop_with_source",
     r"(\d+) No-opinion rows do carry source fields: (\d+) in the Ireland\s+"
     r"dataset, (\d+) in the EU-level dataset", 2, _int, "Known Limitations"),
    ("CODEBOOK", "No-opinion split restated (EU)", "eu_noop_with_source",
     r"(\d+) No-opinion rows do carry source fields: (\d+) in the Ireland\s+"
     r"dataset, (\d+) in the EU-level dataset", 3, _int, "Known Limitations"),

    # ---------------- SUMMARY.md ----------------
    ("SUMMARY", "Statements (intro)", "ie_statements",
     r"on (\d+) policy statements", 1, _int, "Intro"),
    ("SUMMARY", "Irish substantive pct", "ie_coded_pct",
     r"(\d+)% of Irish placements are substantive", 1, _int, "Ireland"),
    ("SUMMARY", "EU families", "eu_entities",
     r"the (\d+) EU-level party families", 1, _int, "EU-level"),
]


def extract_claims(doc_texts: Dict[str, str]):
    results = []
    for doc, name, key, pattern, gi, tf, section in CHECK_DEFINITIONS:
        m = re.search(pattern, doc_texts[doc], re.MULTILINE)
        if m:
            try:
                claimed = tf(m.group(gi))
            except (ValueError, TypeError):
                claimed = None
        else:
            claimed = None
        results.append((doc, name, key, claimed, section))
    return results


def compare(actuals, claims):
    out = []
    for doc, name, key, claimed, section in claims:
        expected = actuals.get(key)
        if claimed is None:
            out.append((doc, name, expected, "NOT FOUND", False, section))
        else:
            out.append((doc, name, expected, claimed,
                        claimed == expected, section))
    return out


def fix_doc(doc: str, text: str, actuals):
    fixed = text
    fixes = []
    for cdoc, name, key, pattern, gi, tf, section in CHECK_DEFINITIONS:
        if cdoc != doc:
            continue
        expected = actuals.get(key)
        m = re.search(pattern, fixed, re.MULTILINE)
        if not m:
            continue
        try:
            claimed = tf(m.group(gi))
        except (ValueError, TypeError):
            continue
        if claimed == expected:
            continue
        full = m.group(0)
        s = m.start(gi) - m.start(0)
        e = m.end(gi) - m.start(0)
        new = full[:s] + str(expected) + full[e:]
        fixed = fixed[:m.start(0)] + new + fixed[m.end(0):]
        fixes.append(f"{doc} / {name}: {claimed} -> {expected}")
    return fixed, fixes


def main():
    parser = argparse.ArgumentParser(
        description="Verify README/CODEBOOK/SUMMARY statistics against CSV data."
    )
    parser.add_argument("--fix", action="store_true",
                        help="Fix mismatches in the documents in-place.")
    args = parser.parse_args()

    print("Documentation Statistics Verification")
    print("=" * 40)
    print()

    data = load_data()
    actuals = compute_actuals(data)
    doc_texts = {doc: path.read_text(encoding="utf-8")
                 for doc, path in DOC_PATHS.items()}
    results = compare(actuals, extract_claims(doc_texts))

    current_doc = current_section = None
    passed = failed = not_found = 0
    for doc, name, expected, claimed, ok, section in results:
        if doc != current_doc:
            current_doc = doc
            current_section = None
            print(f"{doc}.md")
        if section != current_section:
            current_section = section
            print(f"  {section}")
        if claimed == "NOT FOUND":
            not_found += 1
            print(f"    [SKIP] {name}: pattern not found in {doc}.md")
        elif ok:
            passed += 1
            print(f"    [PASS] {name}: {expected} == {claimed}")
        else:
            failed += 1
            print(f"    [FAIL] {name}: {doc}.md says {claimed}, "
                  f"data has {expected}")

    print()
    print("-" * 40)
    print(f"Summary: {passed} passed, {failed} failed, {not_found} skipped "
          f"({len(results)} total checks)")

    if args.fix and failed > 0:
        all_fixes = []
        for doc, path in DOC_PATHS.items():
            fixed_text, fixes = fix_doc(doc, doc_texts[doc], actuals)
            if fixes:
                path.write_text(fixed_text, encoding="utf-8")
                all_fixes.extend(fixes)
        if all_fixes:
            print(f"\nFixed {len(all_fixes)} values:")
            for f in all_fixes:
                print(f"  - {f}")
    elif args.fix:
        print("\nAll checks passed - nothing to fix.")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
