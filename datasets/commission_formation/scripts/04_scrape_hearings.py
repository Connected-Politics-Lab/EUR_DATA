"""
04_scrape_hearings.py
Build the hearings dataset from curated schedule data.

Core data is curated in config.py from the EP timeline.
Optionally enriches with EP document URLs (evaluation letters,
written Q&A, video links) if EP pages are accessible.

Output: hearings.csv + .xlsx
"""

import sys
from pathlib import Path
from typing import Dict, List

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from bs4 import BeautifulSoup
import config
from scripts.utils import setup_logging, ensure_dirs, fetch_url, save_both


EP_HEARINGS_BASE_URL = (
    "https://www.europarl.europa.eu/committees/en/hearings-of-the-commissioners-designa/product-details/20240924CDT13060"
)


def enrich_hearing_urls(hearings: List[Dict], logger) -> List[Dict]:
    """
    Attempt to scrape EP hearing pages for document URLs.
    Falls back gracefully if pages are inaccessible.
    """
    try:
        logger.info("Attempting to enrich hearing data from EP website...")
        resp = fetch_url(EP_HEARINGS_BASE_URL,
                         cache_dir=config.RAW_DIR / "hearing_pages",
                         timeout=30)
        soup = BeautifulSoup(resp.text, "lxml")

        # Try to find hearing detail links
        links = soup.select("a[href*='hearing'], a[href*='commissioner']")
        logger.info(f"Found {len(links)} potential hearing links on EP page")

        # The EP page structure may vary; attempt to match commissioners
        # This is best-effort enrichment
        for hearing in hearings:
            name = hearing["commissioner_name"].lower()
            last_name = name.split()[-1] if name else ""

            for link in links:
                href = link.get("href", "")
                link_text = link.get_text(strip=True).lower()

                if last_name and last_name in link_text:
                    full_url = href if href.startswith("http") else f"https://www.europarl.europa.eu{href}"

                    # Categorize the link
                    if "evaluation" in link_text or "letter" in link_text:
                        hearing["evaluation_letter_url"] = full_url
                    elif "question" in link_text or "written" in link_text:
                        hearing["written_questions_url"] = full_url
                    elif "video" in link_text or "webstream" in link_text:
                        hearing["video_url"] = full_url
                    elif not hearing.get("evaluation_letter_url"):
                        hearing["evaluation_letter_url"] = full_url

    except Exception as e:
        logger.warning(f"EP hearing enrichment failed: {e}. Using curated data only.")

    return hearings


def build_hearings() -> pd.DataFrame:
    """Main function: build hearings dataset from curated + enriched data."""
    logger = setup_logging("04_hearings")
    ensure_dirs()

    # Start with curated data
    hearings = [dict(h) for h in config.HEARINGS_CURATED]
    logger.info(f"Loaded {len(hearings)} curated hearings.")

    # Attempt enrichment
    hearings = enrich_hearing_urls(hearings, logger)

    df = pd.DataFrame(hearings)

    # Ensure proper column order
    columns = [
        "hearing_id", "commissioner_id", "commissioner_name",
        "hearing_date", "committees_responsible", "committees_associated",
        "outcome", "source_url", "evaluation_letter_url",
        "written_questions_url", "video_url",
    ]
    columns = [c for c in columns if c in df.columns]
    df = df[columns]

    # Sort by date
    df = df.sort_values("hearing_date").reset_index(drop=True)

    logger.info(f"Hearings dataset: {len(df)} rows, "
                f"outcomes: {df['outcome'].value_counts().to_dict()}")
    return df


def main():
    df = build_hearings()
    save_both(df, "hearings")
    print(f"hearings: {len(df)} rows saved.")
    return df


if __name__ == "__main__":
    main()
