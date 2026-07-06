"""
Verify every numerical claim in README.md, CODEBOOK.md, and SUMMARY.md
against the actual CSV data, and check that the figures exist.

Usage:
    python verify_readme.py          # report only
    python verify_readme.py --fix    # report + fix README mismatches in-place
"""

import argparse
import re
import sys
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import pandas as pd

from config import BASE_DIR, OUTPUT_DIR

README_PATH = BASE_DIR / "README.md"
CODEBOOK_PATH = BASE_DIR / "CODEBOOK.md"
SUMMARY_PATH = BASE_DIR / "SUMMARY.md"
FIGURES_DIR = BASE_DIR / "figures"

FIGURE_FILES = [
    "college_composition.png",
    "investiture_vote.png",
    "mission_commitments.png",
    "work_programme.png",
    "formation_timeline.png",
]

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
    actuals["comm_independent_count"] = int(party_counts.get("Independent", 0))
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

    # Rank-and-file female commissioners (for SUMMARY's "6 of 20")
    rank_file = comm[comm["role"] == "Commissioner"]
    actuals["comm_rankfile_female"] = int((rank_file["gender"] == "F").sum())

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

    actuals["cmt_section_nulls"] = int(cmt["section_heading"].isna().sum())

    # Boilerplate
    boiler = cmt[cmt["is_boilerplate"]]
    actuals["cmt_boiler_count"] = len(boiler)
    actuals["cmt_boiler_pct"] = round(len(boiler) / len(cmt) * 100)
    actuals["cmt_boiler_templates"] = boiler["commitment_text"].nunique()
    actuals["cmt_distinct_texts"] = cmt["commitment_text"].nunique()
    boiler_types = boiler["commitment_type"].value_counts()
    actuals["cmt_boiler_legislative"] = int(boiler_types.get("legislative", 0))
    actuals["cmt_boiler_report"] = int(boiler_types.get("report", 0))
    actuals["cmt_boiler_review"] = int(boiler_types.get("review", 0))

    by_comm = cmt.groupby("commissioner_id").size().sort_values(ascending=False)
    actuals["cmt_per_comm_min"] = int(by_comm.min())
    actuals["cmt_per_comm_max"] = int(by_comm.max())
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

    day_counts = hear["hearing_date"].value_counts()
    actuals["hearing_nov04"] = int(day_counts.get("2024-11-04", 0))
    actuals["hearing_nov05"] = int(day_counts.get("2024-11-05", 0))
    actuals["hearing_nov06"] = int(day_counts.get("2024-11-06", 0))
    actuals["hearing_nov07"] = int(day_counts.get("2024-11-07", 0))
    actuals["hearing_nov12"] = int(day_counts.get("2024-11-12", 0))

    main_week = hear[
        (hear["hearing_date"] >= "2024-11-04")
        & (hear["hearing_date"] <= "2024-11-07")
    ]
    actuals["hearing_main_week_count"] = len(main_week)

    # --- I. Work programme annex breakdown ---
    annex_counts = wp["annex"].value_counts()
    actuals["wp_annex_I"] = int(annex_counts.get("I", 0))
    actuals["wp_annex_II"] = int(annex_counts.get("II", 0))
    actuals["wp_annex_IV"] = int(annex_counts.get("IV", 0))
    actuals["wp_annex_V"] = int(annex_counts.get("V", 0))

    # Annex I nature of act and numbered-row unpacking
    annex_i = wp[wp["annex"] == "I"]
    i_types = annex_i["type_of_act"].value_counts()
    actuals["wp_i_legislative"] = int(i_types.get("Legislative", 0))
    actuals["wp_i_nonlegislative"] = int(i_types.get("Non-legislative", 0))
    actuals["wp_i_either"] = int(
        i_types.get("Non-legislative or legislative", 0)
    )
    actuals["wp_i_numbered_rows"] = int(annex_i["item_number"].nunique())

    # type_of_act null count (should be exactly the Annex II rows)
    actuals["wp_typeact_nulls"] = int(wp["type_of_act"].isna().sum())
    actuals["wp_timing_nulls"] = int(wp["indicative_timing"].isna().sum())
    actuals["wp_description_nulls"] = int(wp["description"].isna().sum())
    actuals["wp_policyarea_nulls"] = int(wp["policy_area"].isna().sum())

    # Annex IV / V instrument breakdowns (upper-cased in data)
    annex_iv = wp[wp["annex"] == "IV"]
    iv_types = annex_iv["type_of_act"].str.strip().str.title().value_counts()
    actuals["wp_iv_regulation"] = int(iv_types.get("Regulation", 0))
    actuals["wp_iv_directive"] = int(iv_types.get("Directive", 0))
    actuals["wp_iv_decision"] = int(iv_types.get("Decision", 0))
    actuals["wp_iv_recommendation"] = int(iv_types.get("Recommendation", 0))

    annex_v = wp[wp["annex"] == "V"]
    v_types = annex_v["type_of_act"].str.strip().str.title().value_counts()
    actuals["wp_v_regulation"] = int(v_types.get("Regulation", 0))
    actuals["wp_v_decision"] = int(v_types.get("Decision", 0))

    # --- J. Timeline ---
    tl_dates = pd.to_datetime(tl["date"])
    actuals["timeline_date_min"] = tl_dates.min().strftime("%Y-%m-%d")
    actuals["timeline_date_max"] = tl_dates.max().strftime("%Y-%m-%d")
    actuals["timeline_day_span"] = (tl_dates.max() - tl_dates.min()).days

    return actuals


# ============================================================
# Extract claims via targeted regex
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
    ("Independent count", "comm_independent_count",
     r"(\d+) independent \(Kadis", 1, _int, "Commissioner Breakdowns"),
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
    ("Top 2 count (Virkkunen)", "cmt_top2_count",
     r"Virkkunen \((\d+)\)", 1, _int, "Commitments"),
    ("Top 3 count (Brunner)", "cmt_top3_count",
     r"Brunner \((\d+)\)", 1, _int, "Commitments"),
    ("Top 4 count (Sejourne)", "cmt_top4_count",
     r"Sejourne \((\d+)\)", 1, _int, "Commitments"),
    ("Top 5 count (Minzatu)", "cmt_top5_count",
     r"Minzatu \((\d+)\)", 1, _int, "Commitments"),
    ("Bottom count (Kos)", "cmt_bottom_count",
     r"Kos \((\d+)\)", 1, _int, "Commitments"),
    ("Average commitments", "cmt_average",
     r"Average: ~(\d+) commitments", 1, _int, "Commitments"),
    ("High confidence in code comment", "cmt_high",
     r"# (\d+) rows", 1, _int, "Commitments"),

    # Boilerplate claims
    ("Boilerplate count", "cmt_boiler_count",
     r"(\d+) of the \d+ rows \(\d+%\) are boilerplate", 1, _int, "Commitments"),
    ("Boilerplate total", "rows_commitments",
     r"\d+ of the (\d+) rows \(\d+%\) are boilerplate", 1, _int, "Commitments"),
    ("Boilerplate pct", "cmt_boiler_pct",
     r"\d+ of the \d+ rows \((\d+)%\) are boilerplate", 1, _int, "Commitments"),
    ("Boilerplate template count", "cmt_boiler_templates",
     r"covering just (\d+) distinct template texts", 1, _int, "Commitments"),
    ("Distinct commitment texts", "cmt_distinct_texts",
     r"(\d+) distinct commitment texts overall", 1, _int, "Commitments"),
    ("Boilerplate legislative", "cmt_boiler_legislative",
     r"includes (\d+) of the \d+ legislative", 1, _int, "Commitments"),
    ("Boilerplate legislative total", "cmt_type_legislative",
     r"includes \d+ of the (\d+) legislative", 1, _int, "Commitments"),
    ("Boilerplate report", "cmt_boiler_report",
     r"(\d+) of the \d+ report", 1, _int, "Commitments"),
    ("Boilerplate report total", "cmt_type_report",
     r"\d+ of the (\d+) report", 1, _int, "Commitments"),
    ("Boilerplate review", "cmt_boiler_review",
     r"(\d+) of the \d+ review", 1, _int, "Commitments"),
    ("Boilerplate review total", "cmt_type_review",
     r"\d+ of the (\d+) review", 1, _int, "Commitments"),
    ("Boilerplate rows (table 2)", "cmt_boiler_count",
     r"more than 13 of the 26 letters \((\d+) rows\)", 1, _int, "Commitments"),

    # --- H. Hearings ---
    ("Hearings count (prose)", "rows_hearings",
     r"(\d+) confirmation hearings held", 1, _int, "Hearings"),
    ("Hearings main block count", "hearing_main_week_count",
     r"4-7 November \((\d+) hearings", 1, _int, "Hearings"),
    ("Hearings on 4 Nov", "hearing_nov04",
     r"hearings: (\d+) on 4 Nov, \d+ on 5 Nov, \d+ on 6 Nov, \d+ on 7 Nov",
     1, _int, "Hearings"),
    ("Hearings on 5 Nov", "hearing_nov05",
     r"hearings: \d+ on 4 Nov, (\d+) on 5 Nov, \d+ on 6 Nov, \d+ on 7 Nov",
     1, _int, "Hearings"),
    ("Hearings on 6 Nov", "hearing_nov06",
     r"hearings: \d+ on 4 Nov, \d+ on 5 Nov, (\d+) on 6 Nov, \d+ on 7 Nov",
     1, _int, "Hearings"),
    ("Hearings on 7 Nov", "hearing_nov07",
     r"hearings: \d+ on 4 Nov, \d+ on 5 Nov, \d+ on 6 Nov, (\d+) on 7 Nov",
     1, _int, "Hearings"),
    ("Hearings on 12 Nov", "hearing_nov12",
     r"on 12 November \((\d+) hearings\)", 1, _int, "Hearings"),

    # --- I. Work programme annex breakdown ---
    ("WP total (prose)", "rows_wp",
     r"(\d+) items from the annexes of the CWP 2025", 1, _int, "Work Programme"),
    ("WP Annex I", "wp_annex_I",
     r"\| I \(New initiatives\) \| (\d+) \|", 1, _int, "Work Programme"),
    ("WP Annex II", "wp_annex_II",
     r"\| II \(Evaluations and fitness checks\) \| (\d+) \|", 1, _int, "Work Programme"),
    ("WP Annex IV", "wp_annex_IV",
     r"\| IV \(Withdrawals\) \| (\d+) \|", 1, _int, "Work Programme"),
    ("WP Annex V", "wp_annex_V",
     r"\| V \(Envisaged repeals\) \| (\d+) \|", 1, _int, "Work Programme"),
    ("WP Annex I initiatives (prose)", "wp_annex_I",
     r"Annex I's (\d+) initiatives are unpacked", 1, _int, "Work Programme"),
    ("WP Annex I numbered rows", "wp_i_numbered_rows",
     r"unpacked from (\d+) numbered rows", 1, _int, "Work Programme"),
    ("WP Annex I non-legislative", "wp_i_nonlegislative",
     r"(\d+) Non-legislative, \d+ Legislative \(matching", 1, _int, "Work Programme"),
    ("WP Annex I legislative", "wp_i_legislative",
     r"\d+ Non-legislative, (\d+) Legislative \(matching", 1, _int, "Work Programme"),
    ("WP Annex I new initiatives (use case)", "wp_annex_I",
     r"the (\d+) new CWP initiatives in Annex I", 1, _int, "Work Programme"),
    ("WP IV Regulations", "wp_iv_regulation",
     r"naming (\d+) regulations", 1, _int, "Work Programme"),
    ("WP IV Directives", "wp_iv_directive",
     r"naming \d+ regulations, (\d+) directives", 1, _int, "Work Programme"),
    ("WP IV Decisions", "wp_iv_decision",
     r"naming \d+ regulations, \d+ directives, (\d+) decisions", 1, _int, "Work Programme"),
    ("WP IV Recommendation", "wp_iv_recommendation",
     r"and (\d+) recommendation in the withdrawn", 1, _int, "Work Programme"),
    ("WP V Regulations", "wp_v_regulation",
     r"acts in force \((\d+) regulations, \d+ decision\)", 1, _int, "Work Programme"),
    ("WP V Decisions", "wp_v_decision",
     r"acts in force \(\d+ regulations, (\d+) decision\)", 1, _int, "Work Programme"),
    ("WP type_of_act nulls (table 5)", "wp_typeact_nulls",
     r"null exactly for the (\d+) Annex II rows", 1, _int, "Work Programme"),

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


# --- CODEBOOK.md checks (same tuple format) ---
CODEBOOK_CHECKS = [
    ("commissioners rows (heading)", "rows_commissioners",
     r"## 1\. `commissioners\.csv` \((\d+) rows\)", 1, _int, "Codebook Row Counts"),
    ("commitments rows (heading)", "rows_commitments",
     r"## 2\. `mission_letter_commitments\.csv` \((\d+) rows\)", 1, _int, "Codebook Row Counts"),
    ("hearings rows (heading)", "rows_hearings",
     r"## 3\. `hearings\.csv` \((\d+) rows\)", 1, _int, "Codebook Row Counts"),
    ("vote rows (heading)", "rows_vote",
     r"## 4\. `investiture_vote\.csv` \((\d+) rows\)", 1, _int, "Codebook Row Counts"),
    ("wp rows (heading)", "rows_wp",
     r"## 5\. `work_programme_items\.csv` \((\d+) rows\)", 1, _int, "Codebook Row Counts"),
    ("timeline rows (heading)", "rows_timeline",
     r"## 6\. `formation_timeline\.csv` \((\d+) rows\)", 1, _int, "Codebook Row Counts"),

    ("EPP count (coding note)", "comm_epp_count",
     r"EPP therefore has (\d+)\s+of 27 members", 1, _int, "Codebook Commissioners"),
    ("EPP pct (coding note)", "comm_epp_pct",
     r"EPP therefore has \d+\s+of 27 members \((\d+)%\)", 1, _int, "Codebook Commissioners"),

    ("section_heading nulls", "cmt_section_nulls",
     r"\| `section_heading` \| string \| (\d+) \|", 1, _int, "Codebook Commitments"),
    ("high confidence rows", "cmt_high",
     r"`high` \(bullet-point extraction, (\d+) rows\)", 1, _int, "Codebook Commitments"),
    ("medium confidence rows", "cmt_medium",
     r"`medium` \(directive/legislative, (\d+) rows\)", 1, _int, "Codebook Commitments"),
    ("distinct texts", "cmt_distinct_texts",
     r"(\d+) distinct texts across the", 1, _int, "Codebook Commitments"),
    ("boilerplate count", "cmt_boiler_count",
     r"\*\*(\d+) of the \d+ rows \(\d+%\) are boilerplate\*\*", 1, _int, "Codebook Commitments"),
    ("boilerplate total", "rows_commitments",
     r"\*\*\d+ of the (\d+) rows \(\d+%\) are boilerplate\*\*", 1, _int, "Codebook Commitments"),
    ("boilerplate pct", "cmt_boiler_pct",
     r"\*\*\d+ of the \d+ rows \((\d+)%\) are boilerplate\*\*", 1, _int, "Codebook Commitments"),
    ("boilerplate templates", "cmt_boiler_templates",
     r"covering just (\d+) distinct\s+template texts", 1, _int, "Codebook Commitments"),
    ("boilerplate legislative", "cmt_boiler_legislative",
     r"includes (\d+) of the\s+\d+ `legislative`", 1, _int, "Codebook Commitments"),
    ("boilerplate legislative total", "cmt_type_legislative",
     r"includes \d+ of the\s+(\d+) `legislative`", 1, _int, "Codebook Commitments"),
    ("boilerplate report", "cmt_boiler_report",
     r"(\d+) of the\s+\d+ `report`", 1, _int, "Codebook Commitments"),
    ("boilerplate report total", "cmt_type_report",
     r"\d+ of the\s+(\d+) `report`", 1, _int, "Codebook Commitments"),
    ("boilerplate review", "cmt_boiler_review",
     r"(\d+) of the\s+\d+ `review`", 1, _int, "Codebook Commitments"),
    ("boilerplate review total", "cmt_type_review",
     r"\d+ of the\s+(\d+) `review`", 1, _int, "Codebook Commitments"),
    ("per-commissioner min", "cmt_per_comm_min",
     r"per-commissioner totals \((\d+)-\d+ per letter\)", 1, _int, "Codebook Commitments"),
    ("per-commissioner max", "cmt_per_comm_max",
     r"per-commissioner totals \(\d+-(\d+) per letter\)", 1, _int, "Codebook Commitments"),

    ("hearings on 4 Nov", "hearing_nov04",
     r"(\d+) hearings on 4 Nov, \d+ on 5 Nov", 1, _int, "Codebook Hearings"),
    ("hearings on 5 Nov", "hearing_nov05",
     r"\d+ hearings on 4 Nov, (\d+) on 5 Nov", 1, _int, "Codebook Hearings"),
    ("hearings on 6 Nov", "hearing_nov06",
     r"on 5 Nov,\s+(\d+) on 6 Nov", 1, _int, "Codebook Hearings"),
    ("hearings on 7 Nov", "hearing_nov07",
     r"on 6 Nov, (\d+) on 7 Nov", 1, _int, "Codebook Hearings"),
    ("hearings on 12 Nov", "hearing_nov12",
     r"on 7 Nov, and (\d+) on 12 Nov", 1, _int, "Codebook Hearings"),

    ("WP annex I count", "wp_annex_I",
     r"`I` \(new initiatives, (\d+)\)", 1, _int, "Codebook Work Programme"),
    ("WP annex II count", "wp_annex_II",
     r"`II` \(annual plan on evaluations and fitness checks, (\d+)\)", 1, _int, "Codebook Work Programme"),
    ("WP annex IV count", "wp_annex_IV",
     r"`IV` \(withdrawals of pending proposals, (\d+)\)", 1, _int, "Codebook Work Programme"),
    ("WP annex V count", "wp_annex_V",
     r"`V` \(envisaged repeals of acts in force, (\d+)\)", 1, _int, "Codebook Work Programme"),
    ("WP annex I unpacked", "wp_annex_I",
     r"(\d+) initiatives\s+are unpacked from \d+ numbered rows", 1, _int, "Codebook Work Programme"),
    ("WP annex I numbered rows", "wp_i_numbered_rows",
     r"\d+ initiatives\s+are unpacked from (\d+) numbered rows", 1, _int, "Codebook Work Programme"),
    ("WP annex I legislative", "wp_i_legislative",
     r"`Legislative` (\d+), `Non-legislative` \d+", 1, _int, "Codebook Work Programme"),
    ("WP annex I non-legislative", "wp_i_nonlegislative",
     r"`Legislative` \d+, `Non-legislative` (\d+)", 1, _int, "Codebook Work Programme"),
    ("WP type_of_act nulls (column)", "wp_typeact_nulls",
     r"\| `type_of_act` \| string \| (\d+) \|", 1, _int, "Codebook Work Programme"),
    ("WP type_of_act nulls (note)", "wp_typeact_nulls",
     r"exactly for the (\d+) Annex II rows", 1, _int, "Codebook Work Programme"),
    ("WP indicative_timing nulls", "wp_timing_nulls",
     r"\| `indicative_timing` \| string \| (\d+) \|", 1, _int, "Codebook Work Programme"),
    ("WP description nulls", "wp_description_nulls",
     r"\| `description` \| string \| (\d+) \|", 1, _int, "Codebook Work Programme"),
    ("WP policy_area nulls", "wp_policyarea_nulls",
     r"\| `policy_area` \| string \| (\d+) \|", 1, _int, "Codebook Work Programme"),
    ("WP IV regulations", "wp_iv_regulation",
     r"(\d+) `REGULATION`, \d+\s+`DIRECTIVE`", 1, _int, "Codebook Work Programme"),
    ("WP IV directives", "wp_iv_directive",
     r"\d+ `REGULATION`, (\d+)\s+`DIRECTIVE`", 1, _int, "Codebook Work Programme"),
    ("WP IV decisions", "wp_iv_decision",
     r"`DIRECTIVE`, (\d+) `DECISION`, \d+ `RECOMMENDATION`", 1, _int, "Codebook Work Programme"),
    ("WP IV recommendations", "wp_iv_recommendation",
     r"`DIRECTIVE`, \d+ `DECISION`, (\d+) `RECOMMENDATION`", 1, _int, "Codebook Work Programme"),
    ("WP V regulations", "wp_v_regulation",
     r"\((\d+) `REGULATION`, \d+ `DECISION`\)", 1, _int, "Codebook Work Programme"),
    ("WP V decisions", "wp_v_decision",
     r"\(\d+ `REGULATION`, (\d+) `DECISION`\)", 1, _int, "Codebook Work Programme"),

    ("boilerplate rows (limitations)", "cmt_boiler_count",
     r"(\d+) of the \d+ commitment rows", 1, _int, "Codebook Limitations"),
    ("boilerplate rows total (limitations)", "rows_commitments",
     r"\d+ of the (\d+) commitment rows", 1, _int, "Codebook Limitations"),
]


# --- SUMMARY.md checks (same tuple format) ---
SUMMARY_CHECKS = [
    ("EPP members", "comm_epp_count",
     r"EPP \((\d+) members, \d+%\)", 1, _int, "Summary College"),
    ("EPP pct", "comm_epp_pct",
     r"EPP \(\d+ members, (\d+)%\)", 1, _int, "Summary College"),
    ("women pct", "comm_female_pct",
     r"(\d+)% women \(\d+ of \d+\)", 1, _int, "Summary College"),
    ("women count", "comm_female_count",
     r"\d+% women \((\d+) of \d+\)", 1, _int, "Summary College"),
    ("college size", "rows_commissioners",
     r"\d+% women \(\d+ of (\d+)\)", 1, _int, "Summary College"),
    ("EVP count", "comm_evp_count",
     r"(\d+) Executive Vice-Presidencies", 1, _int, "Summary College"),
    ("rank-and-file women", "comm_rankfile_female",
     r"only \*\*(\d+)\s+of \d+\*\* rank-and-file", 1, _int, "Summary College"),
    ("rank-and-file total", "comm_commissioner_count",
     r"only \*\*\d+\s+of (\d+)\*\* rank-and-file", 1, _int, "Summary College"),

    ("vote for", "vote_for",
     r"\*\*(\d+) for / \d+ against / \d+ abstain\*\*", 1, _int, "Summary Vote"),
    ("vote against", "vote_against",
     r"\*\*\d+ for / (\d+) against / \d+ abstain\*\*", 1, _int, "Summary Vote"),
    ("vote abstain", "vote_abstain",
     r"\*\*\d+ for / \d+ against / (\d+) abstain\*\*", 1, _int, "Summary Vote"),
    ("PPE for", "party_PPE_for",
     r"PPE \((\d+) of \d+\)", 1, _int, "Summary Vote"),
    ("PPE total", "party_PPE_total",
     r"PPE \(\d+ of (\d+)\)", 1, _int, "Summary Vote"),
    ("S&D for", "party_SandD_for",
     r"S&D \((\d+)\s+of \d+\)", 1, _int, "Summary Vote"),
    ("S&D total", "party_SandD_total",
     r"S&D \(\d+\s+of (\d+)\)", 1, _int, "Summary Vote"),
    ("Renew for", "party_Renew_for",
     r"Renew \((\d+) of \d+\)", 1, _int, "Summary Vote"),
    ("Renew total", "party_Renew_total",
     r"Renew \(\d+ of (\d+)\)", 1, _int, "Summary Vote"),
    ("Greens for", "party_Verts_ALE_for",
     r"Greens/EFA \((\d+) of \d+\)", 1, _int, "Summary Vote"),
    ("Greens total", "party_Verts_ALE_total",
     r"Greens/EFA \(\d+ of (\d+)\)", 1, _int, "Summary Vote"),
    ("ECR for", "party_ECR_for",
     r"split \((\d+) for, \d+ against, \d+ abstentions\)", 1, _int, "Summary Vote"),
    ("ECR against", "party_ECR_against",
     r"split \(\d+ for, (\d+) against, \d+ abstentions\)", 1, _int, "Summary Vote"),
    ("ECR abstain", "party_ECR_abstain",
     r"split \(\d+ for, \d+ against, (\d+) abstentions\)", 1, _int, "Summary Vote"),

    ("commitments total", "rows_commitments",
     r"\*\*(\d+) commitments\*\*", 1, _int, "Summary Commitments"),
    ("mission letters", "cmt_distinct_commissioners",
     r"extracted from the (\d+) mission letters", 1, _int, "Summary Commitments"),
    ("type other", "cmt_type_other",
     r"`other` (\d+)", 1, _int, "Summary Commitments"),
    ("type coordination", "cmt_type_coordination",
     r"`coordination` (\d+)", 1, _int, "Summary Commitments"),
    # Matches the figure annotation in mission_commitments.png, which derives
    # the same number from the data at plot time.
    ("legislative count (figure claim)", "cmt_type_legislative",
     r"only \*\*(\d+) are explicitly", 1, _int, "Summary Commitments"),
    ("per-portfolio min", "cmt_per_comm_min",
     r"by portfolio \((\d+) to \d+\)", 1, _int, "Summary Commitments"),
    ("per-portfolio max", "cmt_per_comm_max",
     r"by portfolio \(\d+ to (\d+)\)", 1, _int, "Summary Commitments"),
    ("boilerplate count", "cmt_boiler_count",
     r"(\d+) of the \d+ rows \(\d+%\) are\s+such boilerplate", 1, _int, "Summary Commitments"),
    ("boilerplate total", "rows_commitments",
     r"\d+ of the (\d+) rows \(\d+%\) are\s+such boilerplate", 1, _int, "Summary Commitments"),
    ("boilerplate pct", "cmt_boiler_pct",
     r"\d+ of the \d+ rows \((\d+)%\) are\s+such boilerplate", 1, _int, "Summary Commitments"),

    # Matches the figure title in work_programme.png (derived from data).
    ("WP total (figure claim)", "rows_wp",
     r"\*\*(\d+) items\*\*: \d+ new initiatives", 1, _int, "Summary Work Programme"),
    ("WP annex I", "wp_annex_I",
     r"\*\*\d+ items\*\*: (\d+) new initiatives", 1, _int, "Summary Work Programme"),
    ("WP annex II", "wp_annex_II",
     r"(\d+) evaluations and fitness checks \(II\)", 1, _int, "Summary Work Programme"),
    ("WP annex IV", "wp_annex_IV",
     r"\*\*(\d+) withdrawals of\s+pending proposals \(IV\)\*\*", 1, _int, "Summary Work Programme"),
    ("WP annex V", "wp_annex_V",
     r"\*\*(\d+) envisaged repeals of acts in force \(V\)\*\*", 1, _int, "Summary Work Programme"),
    ("WP annex I legislative", "wp_i_legislative",
     r"only \*\*(\d+) are legislative\*\*", 1, _int, "Summary Work Programme"),

    ("timeline span", "timeline_day_span",
     r"\*\*(\d+) days\*\*", 1, _int, "Summary Timeline"),
]


DOC_CHECKS = [
    ("README.md", README_PATH, CHECK_DEFINITIONS),
    ("CODEBOOK.md", CODEBOOK_PATH, CODEBOOK_CHECKS),
    ("SUMMARY.md", SUMMARY_PATH, SUMMARY_CHECKS),
]


def extract_claims(
    text: str,
    definitions: List[Tuple],
) -> List[Tuple[str, str, Optional[Any], str]]:
    """
    Parse a document and extract claimed values.

    Returns list of (check_name, actual_key, claimed_value_or_None, section_label).
    None means the pattern was not found.
    """
    results = []
    for check_name, actual_key, pattern, group_idx, transform, section in definitions:
        m = re.search(pattern, text, re.MULTILINE)
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
            # Pattern not found — treat as a failure so a doc rewrite that
            # silently drops a checked claim cannot produce a green run.
            results.append((check_name, expected, "NOT FOUND", False, section))
        else:
            passed = claimed == expected
            results.append((check_name, expected, claimed, passed, section))
    return results


# ============================================================
# Figure checks
# ============================================================


def check_figures() -> List[Tuple[str, Any, Any, bool, str]]:
    """Verify the summary figures exist and are non-empty.

    The numbers embedded in the figures (annotation text, titles) are derived
    from the CSVs at plot time by make_summary.py; the SUMMARY.md checks above
    pin the same quantities, so existence plus the SUMMARY prose checks cover
    the figure-embedded numbers.
    """
    results = []
    for fname in FIGURE_FILES:
        path = FIGURES_DIR / fname
        exists = path.exists() and path.stat().st_size > 0
        results.append((
            f"figure {fname}", "present, non-empty",
            "present, non-empty" if exists else "MISSING/EMPTY",
            exists, "Figures",
        ))
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
        description="Verify README/CODEBOOK/SUMMARY statistics against CSV data."
    )
    parser.add_argument(
        "--fix",
        action="store_true",
        help="Fix mismatches in README.md in-place (README only).",
    )
    args = parser.parse_args()

    print("Documentation Statistics Verification")
    print("=" * 40)
    print()

    # Load data
    data = load_data()
    actuals = compute_actuals(data)

    total = 0
    passed = 0
    failed = 0
    readme_results = None

    for doc_name, doc_path, definitions in DOC_CHECKS:
        text = doc_path.read_text(encoding="utf-8")
        claims = extract_claims(text, definitions)
        results = compare(actuals, claims)
        if doc_name == "README.md":
            readme_results = results

        print(f"=== {doc_name} ===")
        current_section = None
        for check_name, expected, claimed, ok, section in results:
            if section != current_section:
                current_section = section
                print(f"{section}")

            total += 1
            if claimed == "NOT FOUND":
                failed += 1
                print(f"  [FAIL] {check_name}: pattern not found in {doc_name}")
            elif ok:
                passed += 1
                print(f"  [PASS] {check_name}: {expected} == {claimed}")
            else:
                failed += 1
                print(
                    f"  [FAIL] {check_name}: {doc_name} says {claimed}, "
                    f"data has {expected}"
                )
        print()

    # Figures
    print("=== figures/ ===")
    for check_name, expected, claimed, ok, section in check_figures():
        total += 1
        if ok:
            passed += 1
            print(f"  [PASS] {check_name}: {claimed}")
        else:
            failed += 1
            print(f"  [FAIL] {check_name}: {claimed}")
    print()

    print("-" * 40)
    print(f"Summary: {passed} passed, {failed} failed ({total} total checks)")

    if args.fix and failed > 0 and readme_results is not None:
        readme_text = README_PATH.read_text(encoding="utf-8")
        failure_set = [
            (name, exp, claimed, ok, sec)
            for name, exp, claimed, ok, sec in readme_results
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
            print("\nNo fixable README mismatches found "
                  "(CODEBOOK/SUMMARY must be fixed by hand).")
    elif args.fix and failed == 0:
        print("\nAll checks passed — nothing to fix.")

    sys.exit(1 if failed > 0 else 0)


if __name__ == "__main__":
    main()
