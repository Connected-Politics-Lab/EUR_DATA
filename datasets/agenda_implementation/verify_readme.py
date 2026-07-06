"""
Verify the numerical claims in README.md, CODEBOOK.md and SUMMARY.md against
the actual CSV data.

Usage:
    python verify_readme.py          # report only
    python verify_readme.py --fix    # report + fix mismatches in-place

Note: the term-corpus and status figures are snapshots of live data; re-running
the network steps may change them, after which `--fix` updates the docs.
"""

import argparse
import re
import sys
from pathlib import Path

import pandas as pd

from config import BASE_DIR, OUTPUT_DIR

DOC_PATHS = {
    "README": BASE_DIR / "README.md",
    "CODEBOOK": BASE_DIR / "CODEBOOK.md",
    "SUMMARY": BASE_DIR / "SUMMARY.md",
}


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
    a["scope_annex_iv"] = sc.get("cwp_annex_iv", 0)
    a["scope_annex_v"] = sc.get("cwp_annex_v", 0)
    a["scope_mission"] = sc.get("mission_letter", 0)
    a["cwp_total"] = sum(v for k, v in sc.items() if k.startswith("cwp_annex"))
    a["refs_total"] = len(pr)
    a["celex_resolved"] = int(pr["celex"].notna().sum())
    a["term_corpus"] = len(tlo)
    a["evaluations_total"] = len(ev)
    a["status_rows"] = len(ps)
    a["delivered"] = int(ps["delivered"].sum())
    a["ep_resolved"] = int((ps["status"] != "not_found").sum())
    # Latest snapshot (SUMMARY figures use it).
    latest = ps[ps["as_of_date"] == ps["as_of_date"].max()]
    a["latest_first_read"] = int((latest["status"] == "ep_1st_read").sum())
    a["latest_not_found"] = int((latest["status"] == "not_found").sum())
    resolved = latest[latest["status"] != "not_found"]
    a["latest_resolved"] = len(resolved)
    a["latest_dated_first_event"] = int(
        pd.to_datetime(resolved["proposed_date"], errors="coerce").notna().sum()
    )
    return a


def _int(s):
    return int(s.replace(",", ""))


# (name, actuals key, regex with one capture group, section, doc)
CHECK_DEFINITIONS = [
    # --- README: glance table ---
    ("agenda_items rows (glance)", "agenda_total",
     r"\| `agenda_items\.csv` \| (\d+) \|", "README glance table", "README"),
    ("procedure_references rows (glance)", "refs_total",
     r"\| `procedure_references\.csv` \| (\d+) \|", "README glance table", "README"),
    ("procedure_status rows (glance)", "status_rows",
     r"\| `procedure_status\.csv` \| (\d+) \|", "README glance table", "README"),
    ("term_legislative_output rows (glance)", "term_corpus",
     r"\| `term_legislative_output\.csv` \| (\d+) \|", "README glance table", "README"),
    ("evaluations rows (glance)", "evaluations_total",
     r"\| `evaluations\.csv` \| (\d+) \|", "README glance table", "README"),

    # --- README: scope prose ---
    ("Agenda total (prose)", "agenda_total",
     r"(\d+) tracked agenda items", "README scope", "README"),
    ("CWP total (prose)", "cwp_total",
     r"the (\d+) CWP 2025 work-programme\s*items", "README scope", "README"),
    ("Annex I (prose)", "scope_annex_i",
     r"(\d+)\s+new initiatives", "README scope", "README"),
    ("Annex II (prose)", "scope_annex_ii",
     r"(\d+)\s+evaluations and fitness checks", "README scope", "README"),
    ("Annex IV (prose)", "scope_annex_iv",
     r"(\d+)\s+withdrawals", "README scope", "README"),
    ("Annex V (prose)", "scope_annex_v",
     r"(\d+)\s+envisaged repeals", "README scope", "README"),
    ("Mission commitments (prose)", "scope_mission",
     r"(\d+)\s+legislative mission-letter", "README scope", "README"),

    # --- README: status prose ---
    ("Resolvable refs (prose)", "refs_total",
     r"Of the (\d+) procedure\s+references", "README status", "README"),
    ("EP-resolved refs (prose)", "ep_resolved",
     r"references, (\d+) resolved against the EP API", "README status", "README"),
    ("CELEX resolved (prose)", "celex_resolved",
     r"(\d+) of the \d+ resolved to a EUR-Lex CELEX", "README status", "README"),
    ("Delivered (prose)", "delivered",
     r"(\d+) had been adopted or entered into force", "README status", "README"),

    # --- README: corpus & evaluations ---
    ("Term corpus (prose)", "term_corpus",
     r"catalogue of (\d+) distinct term\s+procedures", "README corpus", "README"),
    ("Evaluations (prose)", "evaluations_total",
     r"(\d+) Annex II evaluations", "README evaluations", "README"),

    # --- CODEBOOK key numbers ---
    ("Agenda total (spine header)", "agenda_total",
     r"One row per tracked agenda item \((\d+):", "CODEBOOK", "CODEBOOK"),
    ("CWP items (spine header)", "cwp_total",
     r"\(\d+: (\d+) CWP work-programme items", "CODEBOOK", "CODEBOOK"),
    ("Mission commitments (spine header)", "scope_mission",
     r"\+ (\d+)\s*legislative mission-letter commitments\)", "CODEBOOK", "CODEBOOK"),
    ("Procedure refs rows", "refs_total",
     r"interinstitutional procedure reference\)\. (\d+) rows", "CODEBOOK", "CODEBOOK"),
    ("Evaluations rows", "evaluations_total",
     r"One row per Annex II [^.]*evaluation[^.]*\.\s*(\d+) rows", "CODEBOOK", "CODEBOOK"),
    ("Annex IV items with refs", "scope_annex_iv",
     r"The\s+(\d+) Annex IV items", "CODEBOOK", "CODEBOOK"),
    ("Annex V items without refs", "scope_annex_v",
     r"The\s+(\d+) Annex V items", "CODEBOOK", "CODEBOOK"),

    # --- SUMMARY key numbers ---
    ("Agenda total", "agenda_total",
     r"\*\*(\d+) agenda items\*\* are tracked", "SUMMARY", "SUMMARY"),
    ("CWP items", "cwp_total",
     r"the (\d+) CWP 2025 work-programme items", "SUMMARY", "SUMMARY"),
    ("Mission commitments", "scope_mission",
     r"plus the (\d+) legislative mission-letter commitments", "SUMMARY", "SUMMARY"),
    ("Agenda-linked procedures", "refs_total",
     r"The (\d+) agenda-linked procedures", "SUMMARY", "SUMMARY"),
    ("At first reading (latest snapshot)", "latest_first_read",
     r"\*\*(\d+) at\s+first reading", "SUMMARY", "SUMMARY"),
    ("Not found (latest snapshot)", "latest_not_found",
     r"and (\d+) not found\*\*", "SUMMARY", "SUMMARY"),
    ("Dated first events (age figure)", "latest_dated_first_event",
     r"(\d+) of \d+ resolved\s+procedures carry a dated\s+first event",
     "SUMMARY", "SUMMARY"),
    ("Resolved procedures (age figure)", "latest_resolved",
     r"\d+ of (\d+) resolved\s+procedures carry a dated\s+first event",
     "SUMMARY", "SUMMARY"),
]


def extract_claims(texts):
    out = []
    for name, key, pattern, section, doc in CHECK_DEFINITIONS:
        m = re.search(pattern, texts[doc], re.MULTILINE)
        claimed = None
        if m:
            try:
                claimed = _int(m.group(1))
            except (ValueError, TypeError):
                claimed = None
        out.append((name, key, claimed, section, doc))
    return out


def fix_doc(text, doc, actuals):
    fixed, fixes = text, []
    for name, key, pattern, section, target_doc in CHECK_DEFINITIONS:
        if target_doc != doc:
            continue
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

    print("Documentation Statistics Verification")
    print("=" * 40)
    print()

    actuals = compute_actuals(load_data())
    texts = {doc: path.read_text(encoding="utf-8")
             for doc, path in DOC_PATHS.items()}
    claims = extract_claims(texts)

    current_section = None
    passed = failed = not_found = 0
    for name, key, claimed, section, doc in claims:
        if section != current_section:
            current_section = section
            print(section)
        expected = actuals.get(key)
        if claimed is None:
            not_found += 1
            print(f"  [SKIP] {name}: pattern not found in {doc}.md")
        elif claimed == expected:
            passed += 1
            print(f"  [PASS] {name}: {expected} == {claimed}")
        else:
            failed += 1
            print(f"  [FAIL] {name}: {doc}.md says {claimed}, data has {expected}")

    print()
    print("-" * 40)
    print(f"Summary: {passed} passed, {failed} failed, {not_found} skipped "
          f"({len(claims)} total checks)")

    if args.fix and failed > 0:
        for doc, path in DOC_PATHS.items():
            fixed_text, fixes = fix_doc(texts[doc], doc, actuals)
            if fixes:
                path.write_text(fixed_text, encoding="utf-8")
                print(f"\nFixed {len(fixes)} value(s) in {path.name}:")
                for f in fixes:
                    print(f"  - {f}")

    sys.exit(1 if failed > 0 or not_found > 0 else 0)


if __name__ == "__main__":
    main()
