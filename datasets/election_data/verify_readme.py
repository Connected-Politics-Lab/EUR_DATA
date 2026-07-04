"""
Verify every numerical claim in README.md against the actual CSV data.

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

README_PATH = BASE_DIR / "README.md"


def load_data() -> Dict[str, pd.DataFrame]:
    data = {}
    for prefix in ["ie", "eu"]:
        for table in ["parties", "statements", "positions", "salience"]:
            key = f"{prefix}_{table}"
            data[key] = pd.read_csv(OUTPUT_DIR / f"{key}.csv")
    return data


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
    a["ie_coded_pct"] = round((ipo["position_label"] != "No opinion").mean() * 100)

    # EU-level
    a["eu_entities"] = len(eup)
    a["eu_statements"] = len(d["eu_statements"])
    a["eu_positions"] = len(epo)
    a["eu_salience"] = len(esa)
    a["eu_coded_pct"] = round((epo["position_label"] != "No opinion").mean() * 100)

    # Combined
    a["total_positions"] = len(ipo) + len(epo)
    return a


def _int(s: str) -> int:
    return int(s.replace(",", ""))


# (check_name, actual_key, pattern, group_index, transform, section)
CHECK_DEFINITIONS = [
    # Dataset-at-a-glance row counts (Ireland)
    ("ie_parties.csv rows (glance)", "ie_entities",
     r"\| `ie_parties\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("ie_statements.csv rows (glance)", "ie_statements",
     r"\| `ie_statements\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("ie_positions.csv rows (glance)", "ie_positions",
     r"\| `ie_positions\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("ie_salience.csv rows (glance)", "ie_salience",
     r"\| `ie_salience\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    # Dataset-at-a-glance row counts (EU)
    ("eu_parties.csv rows (glance)", "eu_entities",
     r"\| `eu_parties\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("eu_statements.csv rows (glance)", "eu_statements",
     r"\| `eu_statements\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("eu_positions.csv rows (glance)", "eu_positions",
     r"\| `eu_positions\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("eu_salience.csv rows (glance)", "eu_salience",
     r"\| `eu_salience\.csv` \| (\d+) \|", 1, _int, "Row Counts"),

    # Ireland prose
    ("Ireland entities (prose)", "ie_entities",
     r"(\d+) coded entities", 1, _int, "Ireland"),
    ("Ireland parties (prose)", "ie_parties_only",
     r"(\d+) national parties", 1, _int, "Ireland"),
    ("Ireland independents (prose)", "ie_independents",
     r"(\d+) independent candidates", 1, _int, "Ireland"),
    ("Ireland positions (prose)", "ie_positions",
     r"(\d+)\s+party-statement positions", 1, _int, "Ireland"),
    ("Ireland coded pct (prose)", "ie_coded_pct",
     r"(\d+)%\s+of\s+Irish placements", 1, _int, "Ireland"),

    # EU prose
    ("EU families (prose)", "eu_entities",
     r"(\d+) EU-level party families", 1, _int, "EU-level"),
    ("EU positions (prose)", "eu_positions",
     r"(\d+)\s+family-statement positions", 1, _int, "EU-level"),
    ("EU coded pct (prose)", "eu_coded_pct",
     r"(\d+)%\s+of\s+EU-level placements", 1, _int, "EU-level"),

    # Common battery / combined
    ("Statements per sheet", "ie_statements",
     r"(\d+) policy statements", 1, _int, "Coding Scheme"),
    ("Total positions", "total_positions",
     r"(\d+) total placements", 1, _int, "Coding Scheme"),
]


def extract_claims(text: str):
    results = []
    for name, key, pattern, gi, tf, section in CHECK_DEFINITIONS:
        m = re.search(pattern, text, re.MULTILINE)
        if m:
            try:
                claimed = tf(m.group(gi))
            except (ValueError, TypeError):
                claimed = None
        else:
            claimed = None
        results.append((name, key, claimed, section))
    return results


def compare(actuals, claims):
    out = []
    for name, key, claimed, section in claims:
        expected = actuals.get(key)
        if claimed is None:
            out.append((name, expected, "NOT FOUND", False, section))
        else:
            out.append((name, expected, claimed, claimed == expected, section))
    return out


def fix_readme(text, actuals):
    fixed = text
    fixes = []
    for name, key, pattern, gi, tf, section in CHECK_DEFINITIONS:
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
        fixes.append(f"{name}: {claimed} -> {expected}")
    return fixed, fixes


def main():
    parser = argparse.ArgumentParser(
        description="Verify README.md statistics against CSV data."
    )
    parser.add_argument("--fix", action="store_true",
                        help="Fix mismatches in README.md in-place.")
    args = parser.parse_args()

    print("README Statistics Verification")
    print("=" * 40)
    print()

    data = load_data()
    actuals = compute_actuals(data)
    readme_text = README_PATH.read_text(encoding="utf-8")
    results = compare(actuals, extract_claims(readme_text))

    current_section = None
    passed = failed = not_found = 0
    for name, expected, claimed, ok, section in results:
        if section != current_section:
            current_section = section
            print(section)
        if claimed == "NOT FOUND":
            not_found += 1
            print(f"  [SKIP] {name}: pattern not found in README")
        elif ok:
            passed += 1
            print(f"  [PASS] {name}: {expected} == {claimed}")
        else:
            failed += 1
            print(f"  [FAIL] {name}: README says {claimed}, data has {expected}")

    print()
    print("-" * 40)
    print(f"Summary: {passed} passed, {failed} failed, {not_found} skipped "
          f"({len(results)} total checks)")

    if args.fix and failed > 0:
        fixed_text, fixes = fix_readme(readme_text, actuals)
        if fixes:
            README_PATH.write_text(fixed_text, encoding="utf-8")
            print(f"\nFixed {len(fixes)} values in README.md:")
            for f in fixes:
                print(f"  - {f}")
    elif args.fix:
        print("\nAll checks passed - nothing to fix.")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
