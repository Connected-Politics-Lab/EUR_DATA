"""
07_build_timeline.py
Build formation timeline from curated data in config.py.

Output: formation_timeline.csv + .xlsx
"""

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
import config
from scripts.utils import setup_logging, ensure_dirs, save_both


def build_timeline() -> pd.DataFrame:
    """Create the formation timeline DataFrame from curated events."""
    logger = setup_logging("07_build_timeline")
    logger.info("Building formation timeline from curated data...")

    df = pd.DataFrame(config.TIMELINE_EVENTS)

    # Ensure date column is proper datetime then format as string
    df["date"] = pd.to_datetime(df["date"]).dt.strftime("%Y-%m-%d")

    # Sort by date
    df = df.sort_values("date").reset_index(drop=True)

    logger.info(f"Timeline contains {len(df)} events "
                f"from {df['date'].iloc[0]} to {df['date'].iloc[-1]}")

    return df


def main():
    ensure_dirs()
    df = build_timeline()
    save_both(df, "formation_timeline")
    print(f"formation_timeline: {len(df)} rows saved.")
    return df


if __name__ == "__main__":
    main()
