"""
make_summary.py
Generate the reproducible figures for the agenda-implementation summary.

Reads data/output/*.csv and writes PNGs to figures/. Uses the latest snapshot in
procedure_status.csv. Deterministic. Run after the pipeline:

    python make_summary.py
"""

from pathlib import Path

import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

import config

OUT = config.OUTPUT_DIR
FIG = config.BASE_DIR / "figures"

plt.rcParams.update({
    "figure.dpi": 130, "savefig.dpi": 130, "font.size": 11,
    "axes.titlesize": 13, "axes.titleweight": "bold",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "grid.alpha": 0.25, "figure.autolayout": True,
})

ACCENT = "#34618E"
SCOPE_LABELS = {
    "cwp_annex_i": "Annex I\nNew initiatives", "cwp_annex_ii": "Annex II\nREFIT",
    "cwp_annex_iii": "Annex III\nEvaluations", "cwp_annex_iv": "Annex IV\nRepeals",
    "mission_letter": "Mission-letter\ncommitments",
}
STATUS_COLOURS = {
    "not_started": "#BDBDBD", "proposed": "#9ECAE1", "ep_1st_read": "#4292C6",
    "council_1st": "#2171B5", "ep_2nd_read": "#6A51A3", "ep_3rd_read": "#807DBA",
    "adopted": "#74C476", "in_force": "#238B45", "withdrawn": "#E2001A",
    "rejected": "#A50F15", "lapsed": "#FB6A4A", "in_progress": "#FD8D3C",
    "not_found": "#D9D9D9",
}


def _labels(ax, bars, horizontal=False):
    for b in bars:
        if horizontal:
            ax.annotate(f"{int(b.get_width())}", (b.get_width(), b.get_y() + b.get_height() / 2),
                        xytext=(3, 0), textcoords="offset points", va="center", fontsize=9)
        else:
            ax.annotate(f"{int(b.get_height())}", (b.get_x() + b.get_width() / 2, b.get_height()),
                        xytext=(0, 3), textcoords="offset points", ha="center", fontsize=9)


def _latest_status():
    ps = pd.read_csv(OUT / "procedure_status.csv")
    return ps[ps["as_of_date"] == ps["as_of_date"].max()].copy()


def fig_scope():
    ai = pd.read_csv(OUT / "agenda_items.csv")
    order = list(SCOPE_LABELS)
    counts = ai["source_scope"].value_counts().reindex(order).fillna(0)
    fig, ax = plt.subplots(figsize=(10, 5))
    bars = ax.bar([SCOPE_LABELS[s] for s in counts.index], counts.values, color=ACCENT)
    _labels(ax, bars)
    ax.set_title("Tracked agenda items by source (124 total)")
    ax.set_ylabel("Items")
    fig.savefig(FIG / "agenda_scope.png", bbox_inches="tight")
    plt.close(fig)


def fig_status():
    ps = _latest_status()
    snap = ps["as_of_date"].iloc[0]
    # Plot the full ladder (plus withdrawn / not_found) so the empty stages
    # make the "stuck early, nothing delivered" finding visually explicit.
    order = config.STATUS_LADDER + ["withdrawn", "not_found"]
    counts = ps["status"].value_counts().reindex(order, fill_value=0)
    colours = [STATUS_COLOURS.get(s, ACCENT) for s in order]

    fig, ax = plt.subplots(figsize=(12, 5.2))
    bars = ax.bar(order, counts.values, color=colours,
                  edgecolor=["none" if v else "#BBBBBB" for v in counts.values])
    _labels(ax, bars)
    # Mark where "delivered" begins.
    ax.axvline(config.STATUS_LADDER.index("adopted") - 0.5, color="#999",
               ls="--", lw=1)
    ax.text(config.STATUS_LADDER.index("adopted") - 0.45, counts.max() * 0.9,
            "delivered →", fontsize=9, color="#555")
    ax.set_title(f"Status of agenda-linked procedures (snapshot {snap})")
    ax.set_ylabel("Procedures")
    ax.tick_params(axis="x", rotation=35)
    for lbl in ax.get_xticklabels():
        lbl.set_ha("right")
    ax.text(0.99, 0.97,
            "All resolved procedures sit at first reading; none reached\n"
            "adoption. Annex IV files are pending withdrawals, and a\n"
            "Commission withdrawal is not an EP procedure stage.",
            transform=ax.transAxes, ha="right", va="top", fontsize=8.5,
            bbox=dict(boxstyle="round", fc="#F4F6F8", ec="#CCC"))
    fig.savefig(FIG / "procedure_status.png", bbox_inches="tight")
    plt.close(fig)


def fig_corpus():
    tlo = pd.read_csv(OUT / "term_legislative_output.csv")
    pivot = (tlo.groupby(["year", "procedure_type"]).size().unstack(fill_value=0)
             .reindex(columns=config.PROCEDURE_TYPES, fill_value=0))
    fig, ax = plt.subplots(figsize=(10, 5))
    x = range(len(pivot.index))
    width = 0.2
    type_colour = {"COD": "#34618E", "CNS": "#C06C2E", "NLE": "#4F8A6B", "APP": "#8B5E8B"}
    for i, ptype in enumerate(config.PROCEDURE_TYPES):
        ax.bar([p + (i - 1.5) * width for p in x], pivot[ptype], width,
               label=ptype, color=type_colour.get(ptype, ACCENT))
    ax.set_xticks(list(x))
    ax.set_xticklabels(pivot.index)
    ax.set_xlabel("Procedure year")
    ax.set_ylabel("Procedures opened")
    ax.set_title(f"Term legislative output by type and year ({len(tlo)} procedures)")
    ax.legend(title="Procedure type", frameon=False, ncol=4)
    if 2026 in list(pivot.index):
        ax.text(0.99, 0.02, "2026 is a partial year (snapshot to date).",
                transform=ax.transAxes, ha="right", va="bottom", fontsize=8.5,
                style="italic", color="#666")
    fig.savefig(FIG / "term_corpus.png", bbox_inches="tight")
    plt.close(fig)


def fig_annex_iv_age():
    ps = _latest_status()
    yrs = pd.to_datetime(ps["proposed_date"], errors="coerce").dt.year.dropna().astype(int)
    if yrs.empty:
        return
    counts = yrs.value_counts().sort_index()
    full = range(int(counts.index.min()), int(counts.index.max()) + 1)
    counts = counts.reindex(full, fill_value=0)
    fig, ax = plt.subplots(figsize=(11, 4.6))
    bars = ax.bar(counts.index.astype(str), counts.values, color="#A56B8A")
    _labels(ax, bars)
    ax.set_title("Age of the proposals on the withdrawal list (by year first tabled)")
    ax.set_xlabel("Year the proposal was originally tabled")
    ax.set_ylabel("Proposals")
    ax.tick_params(axis="x", rotation=45)
    span = f"{int(yrs.min())}-{int(yrs.max())}"
    ax.text(0.02, 0.95, f"These files have been pending for up to ~{2025 - int(yrs.min())} years "
            f"({span}).", transform=ax.transAxes, va="top", fontsize=9,
            bbox=dict(boxstyle="round", fc="#F4F6F8", ec="#CCC"))
    fig.savefig(FIG / "annex_iv_age.png", bbox_inches="tight")
    plt.close(fig)


def main():
    FIG.mkdir(exist_ok=True)
    fig_scope()
    fig_status()
    fig_corpus()
    fig_annex_iv_age()
    print(f"Wrote figures to {FIG}/")


if __name__ == "__main__":
    main()
