"""
make_summary.py
Generate the reproducible figures for the euandi 2024 summary.

Reads data/output/*.csv and writes PNGs to figures/. Deterministic.
Run after the pipeline:

    python make_summary.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.colors import BoundaryNorm
from matplotlib.patches import Patch
import numpy as np
import pandas as pd

import config

OUT = config.OUTPUT_DIR
FIG = config.BASE_DIR / "figures"

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 10,
    "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "figure.autolayout": True,
})

# Diverging 5-point scale (RdYlBu): disagree (blue) -> neutral (pale yellow)
# -> agree (red). Pale-yellow neutral stays distinct from the grey "missing".
SCALE_COLOURS = ["#2C7BB6", "#ABD9E9", "#FFFFBF", "#FDAE61", "#D7191C"]
LABEL_ORDER = ["Completely disagree", "Tend to disagree", "Neutral",
               "Tend to agree", "Completely agree"]
NO_OPINION_COLOUR = "#BDBDBD"


def _cluster_order(mat: pd.DataFrame):
    """Order rows so similar parties are adjacent (hierarchical clustering).

    Missing positions are imputed to 0 (Neutral) for the distance calculation
    only; the displayed matrix keeps them as NaN. Deterministic.
    """
    from scipy.cluster.hierarchy import linkage, leaves_list
    if len(mat) < 3:
        return list(mat.index)
    filled = mat.fillna(0.0).values
    link = linkage(filled, method="ward", optimal_ordering=True)
    return [mat.index[i] for i in leaves_list(link)]


def _heatmap(prefix: str, title: str, fname: str):
    parties = pd.read_csv(OUT / f"{prefix}_parties.csv")
    pos = pd.read_csv(OUT / f"{prefix}_positions.csv")

    names = dict(zip(parties["party_id"], parties["full_name"]))
    mat = (pos.pivot(index="party_id", columns="statement_id",
                     values="position_numeric").reindex(parties["party_id"].tolist()))
    # Reorder rows by similarity so left/right blocs read as contiguous bands.
    order = _cluster_order(mat)
    mat = mat.reindex(order)

    cmap = matplotlib.colors.ListedColormap(SCALE_COLOURS)
    cmap.set_bad(NO_OPINION_COLOUR)
    norm = BoundaryNorm([-2.5, -1.5, -0.5, 0.5, 1.5, 2.5], cmap.N)
    data = np.ma.masked_invalid(mat.values.astype(float))

    fig, ax = plt.subplots(figsize=(14, 0.42 * len(order) + 2))
    ax.imshow(data, cmap=cmap, norm=norm, aspect="auto")
    ax.set_xticks(range(mat.shape[1]))
    ax.set_xticklabels(mat.columns, fontsize=7)
    ax.set_yticks(range(len(order)))
    ax.set_yticklabels([names[p] for p in order], fontsize=9)
    ax.set_xlabel("Statement number")
    ax.set_title(title)
    ax.set_xticks(np.arange(-0.5, mat.shape[1], 1), minor=True)
    ax.set_yticks(np.arange(-0.5, len(order), 1), minor=True)
    ax.grid(which="minor", color="white", lw=1)
    ax.tick_params(which="minor", length=0)

    handles = [Patch(facecolor=c, label=l) for c, l in zip(SCALE_COLOURS, LABEL_ORDER)]
    handles.append(Patch(facecolor=NO_OPINION_COLOUR, label="No opinion / missing"))
    ax.legend(handles=handles, ncol=6, frameon=False, fontsize=8,
              loc="upper center", bbox_to_anchor=(0.5, -0.12))
    fig.savefig(FIG / fname, bbox_inches="tight")
    plt.close(fig)


def fig_label_distribution():
    parties = pd.read_csv(OUT / "ie_parties.csv")
    pos = pd.read_csv(OUT / "ie_positions.csv")
    names = dict(zip(parties["party_id"], parties["full_name"]))

    cats = LABEL_ORDER + ["No opinion"]
    colours = SCALE_COLOURS + [NO_OPINION_COLOUR]
    counts = (pos.groupby("party_id")["position_label"].value_counts()
              .unstack(fill_value=0).reindex(columns=cats, fill_value=0))
    share = counts.div(counts.sum(axis=1), axis=0) * 100
    # Order parties by net agreement (agree share minus disagree share).
    agree = share["Completely agree"] + share["Tend to agree"]
    disagree = share["Completely disagree"] + share["Tend to disagree"]
    share = share.loc[(agree - disagree).sort_values().index]

    fig, ax = plt.subplots(figsize=(11, 7))
    left = np.zeros(len(share))
    for cat, col in zip(cats, colours):
        ax.barh([names[p] for p in share.index], share[cat], left=left,
                color=col, label=cat, edgecolor="white", lw=0.4)
        left += share[cat].values
    ax.set_xlim(0, 100)
    ax.set_xlabel("Share of statements (%)")
    ax.set_title("Irish parties: distribution of final positions")
    ax.legend(ncol=3, frameon=False, fontsize=8, loc="upper center",
              bbox_to_anchor=(0.5, -0.08))
    fig.savefig(FIG / "ie_position_distribution.png", bbox_inches="tight")
    plt.close(fig)


def fig_salience():
    sal = pd.read_csv(OUT / "ie_salience.csv")
    stmts = pd.read_csv(OUT / "ie_statements.csv")
    text = dict(zip(stmts["statement_id"], stmts["statement_text"]))
    top = sal["statement_id"].value_counts().head(10).sort_values()
    labels = [f"{int(i)}. " + (text.get(i, "")[:58] + ("..." if len(text.get(i, "")) > 58 else ""))
              for i in top.index]

    fig, ax = plt.subplots(figsize=(11, 5.5))
    bars = ax.barh(labels, top.values, color="#4F8A6B")
    for b in bars:
        ax.annotate(f"{int(b.get_width())}", (b.get_width(), b.get_y() + b.get_height() / 2),
                    xytext=(3, 0), textcoords="offset points", va="center", fontsize=9)
    ax.set_xlabel("Number of parties ranking it a top-3 salient statement")
    ax.set_title("Most salient statements for Irish parties")
    fig.savefig(FIG / "ie_salience_top.png", bbox_inches="tight")
    plt.close(fig)


def main():
    FIG.mkdir(exist_ok=True)
    _heatmap("ie", "Irish parties & candidates: final positions on 36 statements",
             "ie_position_heatmap.png")
    _heatmap("eu", "EU-level party families: final positions on 36 statements",
             "eu_position_heatmap.png")
    fig_label_distribution()
    fig_salience()
    print(f"Wrote figures to {FIG}/")


if __name__ == "__main__":
    main()
