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

# CSV file basenames
CSV_FILES = {
    "commissioners": "commissioners.csv",
    "commitments": "mission_letter_commitments.csv",
    "hearings": "hearings.csv",
    "vote": "investiture_vote.csv",
    "wp": "work_programme_items.csv",
    "timeline": "formation_timeline.csv",
}


# ============================================================
# Data loading
# ============================================================


def load_data() -> Dict[str, pd.DataFrame]:
    """Load all 6 CSVs into a dict of DataFrames."""
    data = {}
    for key, fname in CSV_FILES.items():
        path = OUTPUT_DIR / fname
        data[key] = pd.read_csv(path)
    return data


# ============================================================
# Compute actual values from data
# ============================================================


def compute_actuals(data: Dict[str, pd.DataFrame]) -> Dict[str, Any]:
    """Compute every verifiable statistic from the data."""
    actuals = {}
    comm = data["commissioners"]
    vote = data["vote"]
    cmt = data["commitments"]
    hear = data["hearings"]
    wp = data["wp"]
    tl = data["timeline"]

    # --- A. Row counts ---
    actuals["rows_commissioners"] = len(comm)
    actuals["rows_commitments"] = len(cmt)
    actuals["rows_hearings"] = len(hear)
    actuals["rows_vote"] = len(vote)
    actuals["rows_wp"] = len(wp)
    actuals["rows_timeline"] = len(tl)

    # --- B. Commissioner breakdowns ---
    party_counts = comm["ep_party_group"].value_counts()
    actuals["comm_epp_count"] = int(party_counts.get("EPP", 0))
    actuals["comm_sd_count"] = int(party_counts.get("S&D", 0))
    actuals["comm_renew_count"] = int(party_counts.get("Renew", 0))
    actuals["comm_ecr_count"] = int(party_counts.get("ECR", 0))
    actuals["comm_pfe_count"] = int(party_counts.get("PfE", 0))
    actuals["comm_epp_pct"] = round(
        actuals["comm_epp_count"] / len(comm) * 100
    )

    gender_counts = comm["gender"].value_counts()
    actuals["comm_female_count"] = int(gender_counts.get("F", 0))
    actuals["comm_female_pct"] = round(
        actuals["comm_female_count"] / len(comm) * 100
    )
    actuals["comm_male_count"] = int(gender_counts.get("M", 0))
    actuals["comm_male_pct"] = round(
        actuals["comm_male_count"] / len(comm) * 100
    )

    role_counts = comm["role"].value_counts()
    actuals["comm_president_count"] = int(role_counts.get("President", 0))
    actuals["comm_evp_count"] = int(
        role_counts.get("Executive Vice-President", 0)
    )
    actuals["comm_hrvp_count"] = int(
        role_counts.get("High Representative/Vice-President", 0)
    )
    actuals["comm_commissioner_count"] = int(
        role_counts.get("Commissioner", 0)
    )
    actuals["comm_countries"] = comm["country"].nunique()

    # --- C. Investiture vote totals ---
    vote_counts = vote["vote"].value_counts()
    actuals["vote_for"] = int(vote_counts.get("for", 0))
    actuals["vote_against"] = int(vote_counts.get("against", 0))
    actuals["vote_abstain"] = int(vote_counts.get("abstain", 0))
    actuals["vote_total"] = len(vote)

    # Per-party-group breakdown
    party_groups_ordered = [
        "PPE", "S&D", "PfE", "ECR", "Renew", "Verts/ALE",
        "The Left", "NI", "ESN",
    ]
    for pg in party_groups_ordered:
        pg_data = vote[vote["ep_party_group"] == pg]
        pg_votes = pg_data["vote"].value_counts()
        key = pg.replace("/", "_").replace(" ", "_").replace("&", "and")
        actuals[f"party_{key}_for"] = int(pg_votes.get("for", 0))
        actuals[f"party_{key}_against"] = int(pg_votes.get("against", 0))
        actuals[f"party_{key}_abstain"] = int(pg_votes.get("abstain", 0))
        actuals[f"party_{key}_total"] = len(pg_data)

    # --- D. National vote patterns ---
    # France
    fr = vote[vote["country"] == "FR"]
    actuals["france_for"] = int((fr["vote"] == "for").sum())
    actuals["france_against"] = int((fr["vote"] == "against").sum())

    # Italy
    it = vote[vote["country"] == "IT"]
    actuals["italy_for"] = int((it["vote"] == "for").sum())
    actuals["italy_against"] = int((it["vote"] == "against").sum())

    # Spain
    es = vote[vote["country"] == "ES"]
    actuals["spain_for"] = int((es["vote"] == "for").sum())
    actuals["spain_against"] = int((es["vote"] == "against").sum())

    es_ppe = vote[(vote["country"] == "ES") & (vote["ep_party_group"] == "PPE")]
    actuals["spain_ppe_against"] = int((es_ppe["vote"] == "against").sum())

    # Germany
    de = vote[vote["country"] == "DE"]
    actuals["germany_total"] = len(de)
    actuals["germany_for"] = int((de["vote"] == "for").sum())
    actuals["germany_against"] = int((de["vote"] == "against").sum())
    actuals["germany_abstain"] = int((de["vote"] == "abstain").sum())

    # --- E. Country enrichment ---
    enriched = vote["country"].notna().sum() - (vote["country"] == "").sum()
    actuals["enriched_count"] = int(enriched)
    actuals["enriched_pct"] = round(enriched / len(vote) * 100, 1)
    actuals["enriched_pct_rounded"] = round(enriched / len(vote) * 100)

    # --- F. ECR sub-national splits ---
    it_ecr = vote[(vote["country"] == "IT") & (vote["ep_party_group"] == "ECR")]
    actuals["italy_ecr_for"] = int((it_ecr["vote"] == "for").sum())

    pl_ecr = vote[(vote["country"] == "PL") & (vote["ep_party_group"] == "ECR")]
    actuals["poland_ecr_against"] = int((pl_ecr["vote"] == "against").sum())

    ppe = vote[vote["ep_party_group"] == "PPE"]
    ppe_for = int((ppe["vote"] == "for").sum())
    actuals["ppe_cohesion_pct"] = round(ppe_for / len(ppe) * 100)

    # --- G. Mission letter commitments ---
    conf_counts = cmt["confidence"].value_counts()
    actuals["cmt_high"] = int(conf_counts.get("high", 0))
    actuals["cmt_medium"] = int(conf_counts.get("medium", 0))

    type_counts = cmt["commitment_type"].value_counts()
    actuals["cmt_type_coordination"] = int(type_counts.get("coordination", 0))
    actuals["cmt_type_policy"] = int(type_counts.get("policy", 0))
    actuals["cmt_type_report"] = int(type_counts.get("report", 0))
    actuals["cmt_type_review"] = int(type_counts.get("review", 0))
    actuals["cmt_type_legislative"] = int(type_counts.get("legislative", 0))
    actuals["cmt_type_other"] = int(type_counts.get("other", 0))

    by_comm = cmt.groupby("commissioner_id").size().sort_values(ascending=False)
    # Map commissioner_id to last name for the top commissioners
    comm_lookup = dict(
        zip(comm["commissioner_id"], comm["last_name"])
    )
    top5 = by_comm.head(5)
    actuals["cmt_top1_name"] = comm_lookup.get(top5.index[0], top5.index[0])
    actuals["cmt_top1_count"] = int(top5.iloc[0])
    actuals["cmt_top2_name"] = comm_lookup.get(top5.index[1], top5.index[1])
    actuals["cmt_top2_count"] = int(top5.iloc[1])
    actuals["cmt_top3_name"] = comm_lookup.get(top5.index[2], top5.index[2])
    actuals["cmt_top3_count"] = int(top5.iloc[2])
    actuals["cmt_top4_name"] = comm_lookup.get(top5.index[3], top5.index[3])
    actuals["cmt_top4_count"] = int(top5.iloc[3])
    actuals["cmt_top5_name"] = comm_lookup.get(top5.index[4], top5.index[4])
    actuals["cmt_top5_count"] = int(top5.iloc[4])

    bottom = by_comm.tail(1)
    actuals["cmt_bottom_name"] = comm_lookup.get(bottom.index[0], bottom.index[0])
    actuals["cmt_bottom_count"] = int(bottom.iloc[0])

    actuals["cmt_distinct_commissioners"] = cmt["commissioner_id"].nunique()
    actuals["cmt_average"] = round(len(cmt) / cmt["commissioner_id"].nunique())

    # --- H. Hearings ---
    hear_dates = pd.to_datetime(hear["hearing_date"])
    actuals["hearing_date_min"] = hear_dates.min().strftime("%Y-%m-%d")
    actuals["hearing_date_max"] = hear_dates.max().strftime("%Y-%m-%d")
    actuals["hearing_all_approved"] = (hear["outcome"] == "approved").all()

    main_week = hear[
        (hear["hearing_date"] >= "2024-11-04")
        & (hear["hearing_date"] <= "2024-11-07")
    ]
    actuals["hearing_main_week_count"] = len(main_week)

    # --- I. Work programme annex breakdown ---
    annex_counts = wp["annex"].value_counts()
    actuals["wp_annex_I"] = int(annex_counts.get("I", 0))
    actuals["wp_annex_II"] = int(annex_counts.get("II", 0))
    actuals["wp_annex_III"] = int(annex_counts.get("III", 0))
    actuals["wp_annex_IV"] = int(annex_counts.get("IV", 0))

    # Annex IV type breakdown (case-insensitive via title case)
    annex_iv = wp[wp["annex"] == "IV"]
    iv_types = annex_iv["type_of_act"].str.strip().str.title().value_counts()
    actuals["wp_iv_regulation"] = int(iv_types.get("Regulation", 0))
    actuals["wp_iv_directive"] = int(iv_types.get("Directive", 0))
    actuals["wp_iv_decision"] = int(iv_types.get("Decision", 0))
    actuals["wp_iv_recommendation"] = int(iv_types.get("Recommendation", 0))

    # --- J. Timeline ---
    tl_dates = pd.to_datetime(tl["date"])
    actuals["timeline_date_min"] = tl_dates.min().strftime("%Y-%m-%d")
    actuals["timeline_date_max"] = tl_dates.max().strftime("%Y-%m-%d")
    actuals["timeline_day_span"] = (tl_dates.max() - tl_dates.min()).days

    return actuals


# ============================================================
# Extract README claims via targeted regex
# ============================================================


# Each check: (check_name, actual_key, regex_pattern, group_index, transform)
# transform converts the captured string to the same type as the actual value
def _int(s: str) -> int:
    return int(s.replace(",", ""))


def _float1(s: str) -> float:
    return float(s)


def _str(s: str) -> str:
    return s


def _bool_true(_s: str) -> bool:
    return True  # presence of the match means "all approved"


# Each entry: (check_name, actual_key, pattern, group_index, transform, section_label)
CHECK_DEFINITIONS = [
    # --- A. Row counts (Dataset at a Glance table) ---
    ("commissioners.csv rows (glance)", "rows_commissioners",
     r"\| `commissioners\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("mission_letter_commitments.csv rows (glance)", "rows_commitments",
     r"\| `mission_letter_commitments\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("hearings.csv rows (glance)", "rows_hearings",
     r"\| `hearings\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("investiture_vote.csv rows (glance)", "rows_vote",
     r"\| `investiture_vote\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("work_programme_items.csv rows (glance)", "rows_wp",
     r"\| `work_programme_items\.csv` \| (\d+) \|", 1, _int, "Row Counts"),
    ("formation_timeline.csv rows (glance)", "rows_timeline",
     r"\| `formation_timeline\.csv` \| (\d+) \|", 1, _int, "Row Counts"),

    # Row counts in Output Tables headings
    ("commissioners.csv rows (output heading)", "rows_commissioners",
     r"### 1\. `commissioners\.csv` \((\d+) rows\)", 1, _int, "Row Counts"),
    ("commitments rows (output heading)", "rows_commitments",
     r"### 2\. `mission_letter_commitments\.csv` \((\d+) rows\)", 1, _int, "Row Counts"),
    ("hearings rows (output heading)", "rows_hearings",
     r"### 3\. `hearings\.csv` \((\d+) rows\)", 1, _int, "Row Counts"),
    ("vote rows (output heading)", "rows_vote",
     r"### 4\. `investiture_vote\.csv` \((\d+) rows\)", 1, _int, "Row Counts"),
    ("wp rows (output heading)", "rows_wp",
     r"### 5\. `work_programme_items\.csv` \((\d+) rows\)", 1, _int, "Row Counts"),
    ("timeline rows (output heading)", "rows_timeline",
     r"### 6\. `formation_timeline\.csv` \((\d+) rows\)", 1, _int, "Row Counts"),

    # Row counts in Cross-Table Relationships diagram
    ("commissioners rows (diagram)", "rows_commissioners",
     r"commissioners \((\d+)\)", 1, _int, "Row Counts"),
    ("commitments rows (diagram)", "rows_commitments",
     r"mission_letter_commitments \((\d+)\)", 1, _int, "Row Counts"),
    ("hearings rows (diagram)", "rows_hearings",
     r"hearings \((\d+)\)", 1, _int, "Row Counts"),
    ("vote rows (diagram)", "rows_vote",
     r"investiture_vote \((\d+)\)", 1, _int, "Row Counts"),
    ("wp rows (diagram)", "rows_wp",
     r"work_programme_items \((\d+)\)", 1, _int, "Row Counts"),
    ("timeline rows (diagram)", "rows_timeline",
     r"formation_timeline \((\d+)\)", 1, _int, "Row Counts"),

    # --- B. Commissioner breakdowns ---
    ("EPP count", "comm_epp_count",
     r"EPP dominates with (\d+) commissioners", 1, _int, "Commissioner Breakdowns"),
    ("EPP percentage", "comm_epp_pct",
     r"EPP dominates with \d+ commissioners \((\d+)%\)", 1, _int, "Commissioner Breakdowns"),
    ("S&D count", "comm_sd_count",
     r"S&D and Renew with (\d+) each", 1, _int, "Commissioner Breakdowns"),
    ("Gender female count", "comm_female_count",
     r"(\d+) women \(\d+%\)", 1, _int, "Commissioner Breakdowns"),
    ("Gender female pct", "comm_female_pct",
     r"\d+ women \((\d+)%\)", 1, _int, "Commissioner Breakdowns"),
    ("Gender male count", "comm_male_count",
     r"(\d+) men \(\d+%\)", 1, _int, "Commissioner Breakdowns"),
    ("Gender male pct", "comm_male_pct",
     r"\d+ men \((\d+)%\)", 1, _int, "Commissioner Breakdowns"),
    ("EVP count", "comm_evp_count",
     r"(\d+) Executive Vice-Presidents", 1, _int, "Commissioner Breakdowns"),
    ("Commissioner count", "comm_commissioner_count",
     r"and (\d+) Commissioners", 1, _int, "Commissioner Breakdowns"),
    ("Country count", "comm_countries",
     r"All (\d+) EU member states", 1, _int, "Commissioner Breakdowns"),
    ("College size", "rows_commissioners",
     r"The (\d+)-member College", 1, _int, "Commissioner Breakdowns"),

    # --- C. Investiture vote totals ---
    ("Vote for (prose)", "vote_for",
     r"\*\*(\d+) for, \d+ against, \d+ abstentions\*\*", 1, _int, "Investiture Vote"),
    ("Vote against (prose)", "vote_against",
     r"\*\*\d+ for, (\d+) against, \d+ abstentions\*\*", 1, _int, "Investiture Vote"),
    ("Vote abstain (prose)", "vote_abstain",
     r"\*\*\d+ for, \d+ against, (\d+) abstentions\*\*", 1, _int, "Investiture Vote"),
    ("Vote total (prose)", "vote_total",
     r"\*\*\d+ for, \d+ against, \d+ abstentions\*\* \((\d+) MEPs", 1, _int, "Investiture Vote"),

    # Vote totals in Output Tables section
    ("Vote for (output totals)", "vote_for",
     r"\*\*Totals\*\*: (\d+) for", 1, _int, "Investiture Vote"),
    ("Vote against (output totals)", "vote_against",
     r"\*\*Totals\*\*: \d+ for \+ (\d+) against", 1, _int, "Investiture Vote"),
    ("Vote abstain (output totals)", "vote_abstain",
     r"\*\*Totals\*\*: \d+ for \+ \d+ against \+ (\d+) abstain", 1, _int, "Investiture Vote"),
    ("Vote total (output totals)", "vote_total",
     r"\*\*Totals\*\*: \d+ for \+ \d+ against \+ \d+ abstain = (\d+)", 1, _int, "Investiture Vote"),

    # Vote totals in manual review checklist
    ("Vote for (checklist)", "vote_for",
     r"Verify vote totals: (\d+) \+ \d+ \+ \d+ = \d+", 1, _int, "Investiture Vote"),
    ("Vote against (checklist)", "vote_against",
     r"Verify vote totals: \d+ \+ (\d+) \+ \d+ = \d+", 1, _int, "Investiture Vote"),
    ("Vote abstain (checklist)", "vote_abstain",
     r"Verify vote totals: \d+ \+ \d+ \+ (\d+) = \d+", 1, _int, "Investiture Vote"),
    ("Vote total (checklist)", "vote_total",
     r"Verify vote totals: \d+ \+ \d+ \+ \d+ = (\d+)", 1, _int, "Investiture Vote"),

    # Party group vote table rows
    ("PPE for", "party_PPE_for",
     r"\| PPE \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("PPE against", "party_PPE_against",
     r"\| PPE \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("PPE abstain", "party_PPE_abstain",
     r"\| PPE \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("PPE total", "party_PPE_total",
     r"\| PPE \| \d+ \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),

    ("S&D for", "party_SandD_for",
     r"\| S&D \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("S&D against", "party_SandD_against",
     r"\| S&D \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("S&D abstain", "party_SandD_abstain",
     r"\| S&D \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("S&D total", "party_SandD_total",
     r"\| S&D \| \d+ \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),

    ("PfE for", "party_PfE_for",
     r"\| PfE \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("PfE against", "party_PfE_against",
     r"\| PfE \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("PfE abstain", "party_PfE_abstain",
     r"\| PfE \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("PfE total", "party_PfE_total",
     r"\| PfE \| \d+ \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),

    ("ECR for", "party_ECR_for",
     r"\| ECR \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("ECR against", "party_ECR_against",
     r"\| ECR \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("ECR abstain", "party_ECR_abstain",
     r"\| ECR \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("ECR total", "party_ECR_total",
     r"\| ECR \| \d+ \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),

    ("Renew for", "party_Renew_for",
     r"\| Renew \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("Renew against", "party_Renew_against",
     r"\| Renew \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("Renew abstain", "party_Renew_abstain",
     r"\| Renew \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("Renew total", "party_Renew_total",
     r"\| Renew \| \d+ \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),

    ("Verts/ALE for", "party_Verts_ALE_for",
     r"\| Verts/ALE \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("Verts/ALE against", "party_Verts_ALE_against",
     r"\| Verts/ALE \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("Verts/ALE abstain", "party_Verts_ALE_abstain",
     r"\| Verts/ALE \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("Verts/ALE total", "party_Verts_ALE_total",
     r"\| Verts/ALE \| \d+ \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),

    ("The Left for", "party_The_Left_for",
     r"\| The Left \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("The Left against", "party_The_Left_against",
     r"\| The Left \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("The Left abstain", "party_The_Left_abstain",
     r"\| The Left \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("The Left total", "party_The_Left_total",
     r"\| The Left \| \d+ \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),

    ("NI for", "party_NI_for",
     r"\| NI \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("NI against", "party_NI_against",
     r"\| NI \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("NI abstain", "party_NI_abstain",
     r"\| NI \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("NI total", "party_NI_total",
     r"\| NI \| \d+ \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),

    ("ESN for", "party_ESN_for",
     r"\| ESN \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("ESN against", "party_ESN_against",
     r"\| ESN \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("ESN abstain", "party_ESN_abstain",
     r"\| ESN \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),
    ("ESN total", "party_ESN_total",
     r"\| ESN \| \d+ \| \d+ \| \d+ \| (\d+) \|", 1, _int, "Party Vote Table"),

    # --- D. National vote patterns ---
    ("France against", "france_against",
     r"\*\*France\*\* voted (\d+)-\d+ against", 1, _int, "National Patterns"),
    ("France for", "france_for",
     r"\*\*France\*\* voted \d+-(\d+) against", 1, _int, "National Patterns"),
    ("Italy for", "italy_for",
     r"\*\*Italy\*\* voted (\d+)-\d+ in favour", 1, _int, "National Patterns"),
    ("Italy against", "italy_against",
     r"\*\*Italy\*\* voted \d+-(\d+) in favour", 1, _int, "National Patterns"),
    ("Spain against", "spain_against",
     r"\*\*Spain\*\* voted (\d+)-\d+ against", 1, _int, "National Patterns"),
    ("Spain for", "spain_for",
     r"\*\*Spain\*\* voted \d+-(\d+) against", 1, _int, "National Patterns"),
    ("Spain PPE against", "spain_ppe_against",
     r"all (\d+) Spanish PPE members", 1, _int, "National Patterns"),
    ("Germany total", "germany_total",
     r"\*\*Germany\*\* \(largest delegation, (\d+) votes cast\)", 1, _int, "National Patterns"),
    ("Germany for", "germany_for",
     r"\*\*Germany\*\*.*voted (\d+)-\d+-\d+", 1, _int, "National Patterns"),
    ("Germany against", "germany_against",
     r"\*\*Germany\*\*.*voted \d+-(\d+)-\d+", 1, _int, "National Patterns"),
    ("Germany abstain", "germany_abstain",
     r"\*\*Germany\*\*.*voted \d+-\d+-(\d+)", 1, _int, "National Patterns"),

    # --- E. Country enrichment ---
    ("Enriched count", "enriched_count",
     r"(\d+) of \d+.*country-enriched", 1, _int, "Country Enrichment"),
    ("Enriched total", "vote_total",
     r"\d+ of (\d+).*country-enriched", 1, _int, "Country Enrichment"),
    ("Enriched pct", "enriched_pct",
     r"(\d+\.?\d*)% of MEPs", 1, _float1, "Country Enrichment"),
    ("Enriched pct (accuracy table)", "enriched_pct_rounded",
     r"~?(\d+)%.*MEPs country-enriched", 1, _int, "Country Enrichment"),

    # --- F. ECR sub-national splits ---
    ("Italy ECR for", "italy_ecr_for",
     r"Italy's (\d+) Fratelli", 1, _int, "ECR Splits"),
    ("Poland ECR against", "poland_ecr_against",
     r"Poland's (\d+) PiS MEPs voted against", 1, _int, "ECR Splits"),
    ("PPE cohesion pct", "ppe_cohesion_pct",
     r"PPE's (\d+)% cohesion", 1, _int, "ECR Splits"),

    # --- G. Mission letter commitments ---
    ("Commitments total (prose)", "rows_commitments",
     r"^(\d+) specific policy commitments", 1, _int, "Commitments"),
    ("Commitments total (prose 2)", "rows_commitments",
     r"The (\d+) mission letter commitments", 1, _int, "Commitments"),
    ("Mission letters count", "cmt_distinct_commissioners",
     r"from the (\d+) mission letters", 1, _int, "Commitments"),
    ("High confidence count", "cmt_high",
     r"(\d+) high-confidence", 1, _int, "Commitments"),
    ("Medium confidence count", "cmt_medium",
     r"(\d+) medium-confidence", 1, _int, "Commitments"),
    ("Type coordination", "cmt_type_coordination",
     r"coordination \((\d+)\)", 1, _int, "Commitments"),
    ("Type policy", "cmt_type_policy",
     r"policy \((\d+)\)", 1, _int, "Commitments"),
    ("Type report", "cmt_type_report",
     r"report \((\d+)\)", 1, _int, "Commitments"),
    ("Type review", "cmt_type_review",
     r"review \((\d+)\)", 1, _int, "Commitments"),
    ("Type legislative", "cmt_type_legislative",
     r"legislative \((\d+)\)", 1, _int, "Commitments"),
    ("Type other", "cmt_type_other",
     r"other \((\d+)\)", 1, _int, "Commitments"),
    ("Top 1 count (Sefcovic)", "cmt_top1_count",
     r"Sefcovic \((\d+)\)", 1, _int, "Commitments"),
    ("Top 2 count (Brunner)", "cmt_top2_count",
     r"Brunner \((\d+)\)", 1, _int, "Commitments"),
    ("Top 3 count (Jorgensen)", "cmt_top3_count",
     r"Jorgensen \((\d+)\)", 1, _int, "Commitments"),
    ("Top 4 count (Lahbib)", "cmt_top4_count",
     r"Lahbib \((\d+)\)", 1, _int, "Commitments"),
    ("Top 5 count (McGrath)", "cmt_top5_count",
     r"McGrath \((\d+)\)", 1, _int, "Commitments"),
    ("Bottom count (Kos)", "cmt_bottom_count",
     r"Kos \((\d+)\)", 1, _int, "Commitments"),
    ("Average commitments", "cmt_average",
     r"Average: ~(\d+) commitments", 1, _int, "Commitments"),
    ("High confidence in code comment", "cmt_high",
     r"# (\d+) rows", 1, _int, "Commitments"),

    # --- H. Hearings ---
    ("Hearings count (prose)", "rows_hearings",
     r"(\d+) confirmation hearings held", 1, _int, "Hearings"),
    ("Hearings main week count", "hearing_main_week_count",
     r"4-7 November \((\d+) hearings", 1, _int, "Hearings"),

    # --- I. Work programme annex breakdown ---
    ("WP total (prose)", "rows_wp",
     r"(\d+) items from the four annexes", 1, _int, "Work Programme"),
    ("WP Annex I", "wp_annex_I",
     r"\| I .* \| (\d+) \|", 1, _int, "Work Programme"),
    ("WP Annex II", "wp_annex_II",
     r"\| II .* \| (\d+) \|", 1, _int, "Work Programme"),
    ("WP Annex III", "wp_annex_III",
     r"\| III .* \| (\d+) \|", 1, _int, "Work Programme"),
    ("WP Annex IV", "wp_annex_IV",
     r"\| IV .* \| (\d+) \|", 1, _int, "Work Programme"),
    ("WP Annex I new initiatives", "wp_annex_I",
     r"the (\d+) new CWP initiatives in Annex I", 1, _int, "Work Programme"),
    ("WP IV Regulations", "wp_iv_regulation",
     r"(\d+) regulations", 1, _int, "Work Programme"),
    ("WP IV Directives", "wp_iv_directive",
     r"(\d+) directives", 1, _int, "Work Programme"),
    ("WP IV Decisions", "wp_iv_decision",
     r"(\d+) decisions", 1, _int, "Work Programme"),
    ("WP IV Recommendation", "wp_iv_recommendation",
     r"(\d+) recommendation", 1, _int, "Work Programme"),

    # --- J. Timeline ---
    ("Timeline count", "rows_timeline",
     r"(\d+) institutional milestones", 1, _int, "Timeline"),
    ("Timeline day span", "timeline_day_span",
     r"spanning (\d+) days", 1, _int, "Timeline"),

    # Timeline vote totals: "370-282-36"
    ("Timeline vote for", "vote_for",
     r"investiture vote \(27 Nov, (\d+)-\d+-\d+\)", 1, _int, "Timeline"),
    ("Timeline vote against", "vote_against",
     r"investiture vote \(27 Nov, \d+-(\d+)-\d+\)", 1, _int, "Timeline"),
    ("Timeline vote abstain", "vote_abstain",
     r"investiture vote \(27 Nov, \d+-\d+-(\d+)\)", 1, _int, "Timeline"),
]


def extract_readme_claims(
    readme_text: str,
) -> List[Tuple[str, str, str, Optional[Any], str]]:
    """
    Parse README and extract claimed values.

    Returns list of (check_name, actual_key, claimed_value_or_None, section_label).
    None means the pattern was not found.
    """
    results = []
    for check_name, actual_key, pattern, group_idx, transform, section in CHECK_DEFINITIONS:
        m = re.search(pattern, readme_text, re.MULTILINE)
        if m:
            raw = m.group(group_idx)
            try:
                claimed = transform(raw)
            except (ValueError, TypeError):
                claimed = None
        else:
            claimed = None
        results.append((check_name, actual_key, claimed, section))
    return results


# ============================================================
# Compare actuals vs claims
# ============================================================


def compare(
    actuals: Dict[str, Any],
    claims: List[Tuple[str, str, Optional[Any], str]],
) -> List[Tuple[str, Any, Any, bool, str]]:
    """
    Compare actuals vs claims.

    Returns list of (check_name, expected, claimed, passed, section).
    """
    results = []
    for check_name, actual_key, claimed, section in claims:
        expected = actuals.get(actual_key)
        if claimed is None:
            # Pattern not found — treat as a skip, not a failure
            results.append((check_name, expected, "NOT FOUND", False, section))
        else:
            passed = claimed == expected
            results.append((check_name, expected, claimed, passed, section))
    return results


# ============================================================
# Fix README in-place
# ============================================================


def fix_readme(
    readme_text: str,
    actuals: Dict[str, Any],
    failures: List[Tuple[str, Any, Any, bool, str]],
) -> Tuple[str, List[str]]:
    """
    For each failure, apply regex substitution to README text.

    Returns (fixed_text, list_of_fix_descriptions).
    """
    fixed = readme_text
    fixes = []

    for check_name, actual_key, pattern, group_idx, transform, section in CHECK_DEFINITIONS:
        expected = actuals.get(actual_key)
        m = re.search(pattern, fixed, re.MULTILINE)
        if not m:
            continue

        raw = m.group(group_idx)
        try:
            claimed = transform(raw)
        except (ValueError, TypeError):
            continue

        if claimed == expected:
            continue

        # Build replacement: substitute only the captured group
        expected_str = str(expected)
        # Replace the specific group in the match
        full_match = m.group(0)
        start_of_group = m.start(group_idx) - m.start(0)
        end_of_group = m.end(group_idx) - m.start(0)
        new_match = (
            full_match[:start_of_group]
            + expected_str
            + full_match[end_of_group:]
        )
        fixed = fixed[:m.start(0)] + new_match + fixed[m.end(0):]
        fixes.append(f"{check_name}: {claimed} -> {expected}")

    return fixed, fixes


# ============================================================
# Main
# ============================================================


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Verify README.md statistics against CSV data."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix mismatches in README.md in-place.",
    )
    args = parser.parse_args()

    print("README Statistics Verification")
    print("=" * 40)
    print()

    # Load data
    data = load_data()
    actuals = compute_actuals(data)

    # Read README
    readme_text = README_PATH.read_text(encoding="utf-8")

    # Extract claims and compare
    claims = extract_readme_claims(readme_text)
    results = compare(actuals, claims)

    # Print report grouped by section
    current_section = None
    total = 0
    passed = 0
    failed = 0
    not_found = 0

    for check_name, expected, claimed, ok, section in results:
        if section != current_section:
            current_section = section
            print(f"{section}")

        total += 1
        if claimed == "NOT FOUND":
            not_found += 1
            print(f"  [SKIP] {check_name}: pattern not found in README")
        elif ok:
            passed += 1
            print(f"  [PASS] {check_name}: {expected} == {claimed}")
        else:
            failed += 1
            print(
                f"  [FAIL] {check_name}: README says {claimed}, "
                f"data has {expected}"
            )

    print()
    print("-" * 40)
    print(
        f"Summary: {passed} passed, {failed} failed, "
        f"{not_found} skipped ({total} total checks)"
    )

    if args.fix and failed > 0:
        failure_set = [
            (name, exp, claimed, ok, sec)
            for name, exp, claimed, ok, sec in results
            if not ok and claimed != "NOT FOUND"
        ]
        fixed_text, fixes = fix_readme(readme_text, actuals, failure_set)
        if fixes:
            README_PATH.write_text(fixed_text, encoding="utf-8")
            print()
            print(f"Fixed {len(fixes)} values in README.md:")
            for fix_desc in fixes:
                print(f"  - {fix_desc}")
        else:
            print("\nNo fixable mismatches found.")
    elif args.fix and failed == 0:
        print("\nAll checks passed — nothing to fix.")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
