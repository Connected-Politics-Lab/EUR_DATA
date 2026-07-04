"""
make_summary.py
Generate the reproducible figures for the Commission Formation summary.

Reads data/output/*.csv and writes PNGs to figures/. Deterministic: no random
state, fixed category ordering. Run after the pipeline:

    python make_summary.py
"""

import sys
from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import config

OUT = config.OUTPUT_DIR
FIG = config.BASE_DIR / "figures"

# ------------------------------------------------------------------
# Shared style
# ------------------------------------------------------------------
plt.rcParams.update({
    "figure.dpi": 130,
    "savefig.dpi": 130,
    "font.size": 11,
    "axes.titlesize": 13,
    "axes.titleweight": "bold",
    "axes.spines.top": False,
    "axes.spines.right": False,
    "axes.grid": True,
    "grid.alpha": 0.25,
    "grid.linestyle": "-",
    "figure.autolayout": True,
})

# Conventional EP political-group colours.
GROUP_COLOURS = {
    "EPP": "#3399FF", "PPE": "#3399FF",
    "S&D": "#E2001A", "PES": "#E2001A",
    "Renew": "#FFD43B", "ALDE": "#FFD43B",
    "Greens/EFA": "#57B45F", "Verts/ALE": "#57B45F",
    "ECR": "#1C4E9C", "PfE": "#1B3A6B", "ID": "#2B3856",
    "The Left": "#8B1E3F", "ESN": "#5A5A5A", "NI": "#9E9E9E",
}
VOTE_COLOURS = {"for": "#57B45F", "against": "#E2001A", "abstain": "#BDBDBD"}
ACCENT = "#34618E"


def _bar_labels(ax, bars, horizontal=False, fmt="{:.0f}", pad=3):
    """Annotate bars with their value. Orientation is explicit, not guessed."""
    for b in bars:
        if horizontal:
            v = b.get_width()
            ax.annotate(fmt.format(v), (v, b.get_y() + b.get_height() / 2),
                        xytext=(pad, 0), textcoords="offset points",
                        va="center", fontsize=9)
        else:
            v = b.get_height()
            ax.annotate(fmt.format(v), (b.get_x() + b.get_width() / 2, v),
                        xytext=(0, pad), textcoords="offset points",
                        ha="center", fontsize=9)


def fig_college():
    comm = pd.read_csv(OUT / "commissioners.csv")
    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8))

    # Party group
    pg = comm["ep_party_group"].value_counts()
    colours = [GROUP_COLOURS.get(g, ACCENT) for g in pg.index]
    bars = axes[0].bar(pg.index, pg.values, color=colours)
    _bar_labels(axes[0], bars)
    axes[0].set_title("By EP political group")
    axes[0].set_ylabel("Commissioners")
    axes[0].tick_params(axis="x", rotation=30)

    # Role and gender (stacked) - reveals the seniority/gender pattern.
    role_order = ["President", "High Representative/Vice-President",
                  "Executive Vice-President", "Commissioner"]
    short = {"President": "President", "High Representative/Vice-President": "HR/VP",
             "Executive Vice-President": "EVP", "Commissioner": "Commissioner"}
    ct = pd.crosstab(comm["role"], comm["gender"]).reindex(role_order).fillna(0)
    labels = [short[r] for r in role_order][::-1]
    men = list(ct.get("M", pd.Series(0, index=role_order)))[::-1]
    women = list(ct.get("F", pd.Series(0, index=role_order)))[::-1]
    axes[1].barh(labels, men, color="#6699CC", label="Men")
    axes[1].barh(labels, women, left=men, color="#CC6699", label="Women")
    for y, (m, w) in enumerate(zip(men, women)):
        if m:
            axes[1].text(m / 2, y, f"{int(m)}", ha="center", va="center",
                         color="white", fontsize=9)
        if w:
            axes[1].text(m + w / 2, y, f"{int(w)}", ha="center", va="center",
                         color="white", fontsize=9)
    axes[1].set_title("By role and gender")
    axes[1].set_xlabel("Commissioners")
    axes[1].legend(frameon=False, ncol=1, fontsize=9, loc="center right")

    fig.suptitle("The von der Leyen II College (27 members; 11 women, 41%)",
                 fontsize=15, fontweight="bold")
    fig.savefig(FIG / "college_composition.png", bbox_inches="tight")
    plt.close(fig)


def fig_investiture():
    vote = pd.read_csv(OUT / "investiture_vote.csv")
    order = ["PPE", "S&D", "PfE", "ECR", "Renew", "Verts/ALE", "The Left", "NI", "ESN"]
    tab = (vote.groupby("ep_party_group")["vote"].value_counts().unstack(fill_value=0)
           .reindex(order).dropna(how="all"))
    for col in ("for", "against", "abstain"):
        if col not in tab:
            tab[col] = 0

    fig, ax = plt.subplots(figsize=(10, 5.2))
    bottom = pd.Series(0, index=tab.index, dtype=float)
    for outcome in ("for", "against", "abstain"):
        ax.bar(tab.index, tab[outcome], bottom=bottom,
               label=outcome.capitalize(), color=VOTE_COLOURS[outcome])
        bottom += tab[outcome]
    ax.set_title("Investiture vote by political group (27 November 2024)")
    ax.set_ylabel("MEPs")
    ax.legend(title="Vote", frameon=False)
    ax.tick_params(axis="x", rotation=20)
    total = vote["vote"].value_counts()
    ax.text(0.99, 0.97,
            f"College approved: {total.get('for',0)} for / "
            f"{total.get('against',0)} against / {total.get('abstain',0)} abstain",
            transform=ax.transAxes, ha="right", va="top", fontsize=9,
            bbox=dict(boxstyle="round", fc="#F4F6F8", ec="#CCC"))
    fig.savefig(FIG / "investiture_vote.png", bbox_inches="tight")
    plt.close(fig)


def fig_commitments():
    cmt = pd.read_csv(OUT / "mission_letter_commitments.csv")
    comm = pd.read_csv(OUT / "commissioners.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 5))

    by_type = cmt["commitment_type"].value_counts()
    # Highlight the 11 trackable legislative pledges; mute the vague types.
    vague = {"other", "coordination"}
    colours = ["#C0392B" if t == "legislative"
               else "#A9BCD0" if t in vague else ACCENT for t in by_type.index]
    bars = axes[0].bar(by_type.index, by_type.values, color=colours)
    _bar_labels(axes[0], bars)
    axes[0].set_title("Commitments by type")
    axes[0].set_ylabel("Commitments")
    axes[0].tick_params(axis="x", rotation=25)
    axes[0].text(0.97, 0.95,
                 "Only 11 are explicitly\n'legislative' (red); most\nare vague or"
                 " non-legislative\n(muted).",
                 transform=axes[0].transAxes, ha="right", va="top", fontsize=8.5,
                 bbox=dict(boxstyle="round", fc="#F4F6F8", ec="#CCC"))

    names = dict(zip(comm["commissioner_id"], comm["last_name"]))
    top = cmt["commissioner_id"].value_counts().head(10)
    labels = [names.get(i, i) for i in top.index]
    bars = axes[1].barh(labels[::-1], top.values[::-1], color="#7A9E7E")
    _bar_labels(axes[1], bars, horizontal=True)
    axes[1].set_title("Top 10 commissioners by commitments")
    axes[1].set_xlabel("Commitments")

    fig.suptitle(f"Mission-letter commitments ({len(cmt)} extracted)",
                 fontsize=15, fontweight="bold")
    fig.savefig(FIG / "mission_commitments.png", bbox_inches="tight")
    plt.close(fig)


def fig_work_programme():
    wp = pd.read_csv(OUT / "work_programme_items.csv")
    fig, axes = plt.subplots(1, 2, figsize=(13, 4.8))

    annex_names = {"I": "I\nNew", "II": "II\nREFIT", "III": "III\nEval.", "IV": "IV\nRepeal"}
    ac = wp["annex"].value_counts().reindex(["I", "II", "III", "IV"]).fillna(0)
    bars = axes[0].bar([annex_names[a] for a in ac.index], ac.values, color=ACCENT)
    _bar_labels(axes[0], bars)
    axes[0].set_title("Work-programme items by annex")
    axes[0].set_ylabel("Items")

    iv = (wp[wp["annex"] == "IV"]["type_of_act"].str.title().value_counts())
    bars = axes[1].bar(iv.index, iv.values, color="#A56B8A")
    _bar_labels(axes[1], bars)
    axes[1].set_title("Annex IV repeals by legal instrument")
    axes[1].set_ylabel("Items")
    axes[1].tick_params(axis="x", rotation=20)

    fig.suptitle(f"CWP 2025 legislative agenda ({len(wp)} items)",
                 fontsize=15, fontweight="bold")
    fig.savefig(FIG / "work_programme.png", bbox_inches="tight")
    plt.close(fig)


def fig_timeline():
    tl = pd.read_csv(OUT / "formation_timeline.csv").sort_values("date")
    tl["date"] = pd.to_datetime(tl["date"])
    type_colour = {"election": "#34618E", "nomination": "#C06C2E", "vote": "#8B1E3F",
                   "hearing": "#4F8A6B", "institutional": "#6A6A6A", "document": "#7A6FA8"}

    fig, ax = plt.subplots(figsize=(13, 5.6))
    # Cycle six distinct heights so date-adjacent events separate vertically.
    cycle = [1.0, -1.6, 2.2, -1.0, 1.6, -2.2]
    levels = [cycle[i % len(cycle)] for i in range(len(tl))]
    ax.axhline(0, color="#BBB", lw=1, zorder=0)
    for (_, row), lev in zip(tl.iterrows(), levels):
        col = type_colour.get(row["event_type"], ACCENT)
        ax.plot([row["date"], row["date"]], [0, lev], color=col, lw=1.2, zorder=1)
        ax.scatter(row["date"], lev, color=col, s=45, zorder=2)
        ax.annotate(row["event_name"], (row["date"], lev),
                    xytext=(0, 8 if lev > 0 else -8), textcoords="offset points",
                    ha="center", va="bottom" if lev > 0 else "top", fontsize=7.6)
    ax.set_ylim(-3.0, 3.0)
    ax.get_yaxis().set_visible(False)
    ax.spines["left"].set_visible(False)
    span = (tl["date"].max() - tl["date"].min()).days
    ax.set_title(f"Formation timeline: EP elections to CWP adoption ({span} days)")
    handles = [plt.Line2D([0], [0], marker="o", color="w", markerfacecolor=c,
               markersize=8, label=t) for t, c in type_colour.items()]
    ax.legend(handles=handles, ncol=6, frameon=False, fontsize=8,
              loc="lower center", bbox_to_anchor=(0.5, -0.12))
    fig.savefig(FIG / "formation_timeline.png", bbox_inches="tight")
    plt.close(fig)


def main():
    FIG.mkdir(exist_ok=True)
    fig_college()
    fig_investiture()
    fig_commitments()
    fig_work_programme()
    fig_timeline()
    print(f"Wrote figures to {FIG}/")


if __name__ == "__main__":
    main()
