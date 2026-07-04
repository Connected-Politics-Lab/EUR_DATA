"""
test_status_monotonic.py
A procedure's status should not move backwards down the progress ladder across
dated snapshots. Off-ladder states (withdrawn / rejected / lapsed / not_found /
in_progress) are exempt - a procedure may jump to those at any time.
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import pytest
import config
from scripts.status_map import ladder_rank

OUTPUT_DIR = config.OUTPUT_DIR


def test_status_does_not_regress():
    path = OUTPUT_DIR / "procedure_status.csv"
    if not path.exists():
        pytest.skip("procedure_status.csv not found")
    df = pd.read_csv(path)
    if df["as_of_date"].nunique() < 2:
        pytest.skip("Only one snapshot; monotonicity is trivially satisfied")

    failures = []
    for ref_id, grp in df.groupby("procedure_ref_id"):
        grp = grp.sort_values("as_of_date")
        prev_rank = None
        for _, row in grp.iterrows():
            rank = ladder_rank(row["status"])
            if rank is None:
                prev_rank = None  # off-ladder; reset
                continue
            if prev_rank is not None and rank < prev_rank:
                failures.append(
                    f"{ref_id} regressed to {row['status']} on {row['as_of_date']}"
                )
            prev_rank = rank
    assert not failures, "Status regressions detected:\n" + "\n".join(failures)
