"""
Verify every numerical claim in README.md against the actual CSV data.

Usage:
    python verify_readme.py          # report only
    python verify_readme.py --fix    # report + fix mismatches in-place

Note: the term-corpus and status figures are snapshots of live data; re-running
the network steps may change them, after which `--fix` updates the README.
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from config import BASE_DIR, OUTPUT_DIR

README_PATH = BASE_DIR / "README.md"


def load_data():
    d = {}
    for name in ["agenda_items", "procedure_references", "procedure_status",
                 "term_legislative_output", "evaluations"]:
        d[name] = pd.read_csv(OUTPUT_DIR / f"{name}.csv")
    return d


def compute_actuals(d):
    a = {}
    ai, pr = d["agenda_items"], d["procedure_references"]
    ps, tlo, ev = d["procedure_status"], d["term_legislative_output"], d["evaluations"]
    sc = ai["source_scope"].value_counts().to_dict()
    a["agenda_total"] = len(ai)
    a["scope_annex_i"] = sc.get("cwp_annex_i", 0)
    a["scope_annex_ii"] = sc.get("cwp_annex_ii", 0)
    a["scope_annex_iii"] = sc.get("cwp_annex_iii", 0)
    a["scope_annex_iv"] = sc.get("cwp_annex_iv", 0)
    a["scope_mission"] = sc.get("mission_letter", 0)
    a["refs_total"] = len(pr)
    a["celex_resolved"] = int(pr["celex"].notna().sum())
    a["term_corpus"] = len(tlo)
    a["evaluations_total"] = len(ev)
    a["status_rows"] = len(ps)
    a["delivered"] = int(ps["delivered"].sum())
    a["ep_resolved"] = int((ps["status"] != "not_found").sum())
    return a


def _int(s):
    return int(s.replace(",", ""))


CHECK_DEFINITIONS = [
    ("agenda_items rows (glance)", "agenda_total",
     r"\| `agenda_items\.csv` \| (\d+) \|", "Row Counts"),
    ("procedure_references rows (glance)", "refs_total",
     r"\| `procedure_references\.csv` \| (\d+) \|", "Row Counts"),
    ("term_legislative_output rows (glance)", "term_corpus",
     r"\| `term_legislative_output\.csv` \| (\d+) \|", "Row Counts"),
    ("evaluations rows (glance)", "evaluations_total",
     r"\| `evaluations\.csv` \| (\d+) \|", "Row Counts"),

    ("Agenda total (prose)", "agenda_total",
     r"(\d+) tracked agenda items", "Scope"),
    ("Annex I (prose)", "scope_annex_i",
     r"(\d+)\s+new initiatives", "Scope"),
    ("Annex IV (prose)", "scope_annex_iv",
     r"(\d+)\s+repeals/withdrawals", "Scope"),
    ("Mission commitments (prose)", "scope_mission",
     r"(\d+)\s+legislative mission-letter", "Scope"),

    ("Resolvable refs (prose)", "refs_total",
     r"Of the (\d+) procedure\s+references", "Status"),
    ("EP-resolved refs (prose)", "ep_resolved",
     r"references, (\d+) resolved against the EP API", "Status"),
    ("CELEX resolved (prose)", "celex_resolved",
     r"(\d+) of the \d+ resolved to a EUR-Lex CELEX", "Status"),
    ("Delivered (prose)", "delivered",
     r"(\d+) had been adopted or entered into force", "Status"),

    ("Term corpus (prose)", "term_corpus",
     r"catalogue of (\d+) distinct term\s+procedures", "Corpus"),
    ("Evaluations (prose)", "evaluations_total",
     r"(\d+) Annex II/III evaluations", "Evaluations"),
]


def extract_claims(text):
    out = []
    for name, key, pattern, section in CHECK_DEFINITIONS:
        m = re.search(pattern, text, re.MULTILINE)
        claimed = None
        if m:
            try:
                claimed = _int(m.group(1))
            except (ValueError, TypeError):
                claimed = None
        out.append((name, key, claimed, section))
    return out


def fix_readme(text, actuals):
    fixed, fixes = text, []
    for name, key, pattern, section in CHECK_DEFINITIONS:
        expected = actuals.get(key)
        m = re.search(pattern, fixed, re.MULTILINE)
        if not m:
            continue
        try:
            claimed = _int(m.group(1))
        except (ValueError, TypeError):
            continue
        if claimed == expected:
            continue
        full = m.group(0)
        s, e = m.start(1) - m.start(0), m.end(1) - m.start(0)
        fixed = fixed[:m.start(0)] + full[:s] + str(expected) + full[e:] + fixed[m.end(0):]
        fixes.append(f"{name}: {claimed} -> {expected}")
    return fixed, fixes


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--fix", action="store_true")
    args = parser.parse_args()

    print("README Statistics Verification")
    print("=" * 40)
    print()

    actuals = compute_actuals(load_data())
    readme = README_PATH.read_text(encoding="utf-8")
    claims = extract_claims(readme)

    current_section = None
    passed = failed = not_found = 0
    for name, key, claimed, section in claims:
        if section != current_section:
            current_section = section
            print(section)
        expected = actuals.get(key)
        if claimed is None:
            not_found += 1
            print(f"  [SKIP] {name}: pattern not found")
        elif claimed == expected:
            passed += 1
            print(f"  [PASS] {name}: {expected} == {claimed}")
        else:
            failed += 1
            print(f"  [FAIL] {name}: README says {claimed}, data has {expected}")

    print()
    print("-" * 40)
    print(f"Summary: {passed} passed, {failed} failed, {not_found} skipped "
          f"({len(claims)} total checks)")

    if args.fix and failed > 0:
        fixed_text, fixes = fix_readme(readme, actuals)
        if fixes:
            README_PATH.write_text(fixed_text, encoding="utf-8")
            print(f"\nFixed {len(fixes)} values in README.md:")
            for f in fixes:
                print(f"  - {f}")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
