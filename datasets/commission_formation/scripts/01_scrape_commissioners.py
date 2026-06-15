"""
01_scrape_commissioners.py
Scrape commissioner profiles from the EC website, with curated fallback.

Attempts to scrape commissioner cards from the EC website. If the page
is JS-rendered or otherwise inaccessible, falls back to the curated
metadata dictionary in config.py.

Output: commissioners.csv + .xlsx
"""

import sys
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pandas as pd
from bs4 import BeautifulSoup
import config
from scripts.utils import setup_logging, ensure_dirs, fetch_url, save_both


def scrape_ec_website(logger) -> Optional[List[Dict]]:
    """
    Attempt to scrape commissioner info from the EC website.
    Returns list of dicts or None if scraping fails.
    """
    try:
        logger.info(f"Scraping {config.EC_COMMISSIONERS_URL}")
        resp = fetch_url(config.EC_COMMISSIONERS_URL,
                         cache_dir=config.RAW_COMMISSIONER_PAGES,
                         timeout=30)

        # Save raw HTML
        html_path = config.RAW_COMMISSIONER_PAGES / "commissioners_page.html"
        html_path.write_text(resp.text, encoding="utf-8")

        soup = BeautifulSoup(resp.text, "lxml")
        records = []

        # Try various selectors for commissioner cards
        # The EC website structure may vary; try common patterns
        selectors = [
            ".ecl-card",
            ".commissioner-card",
            "[data-component='commissioner']",
            ".field--name-field-commissioners .field__item",
            ".views-row",
            "article.node--type-commissioner",
        ]

        cards = []
        for sel in selectors:
            cards = soup.select(sel)
            if cards:
                logger.info(f"Found {len(cards)} cards with selector '{sel}'")
                break

        if not cards:
            logger.warning("No commissioner cards found with any selector. "
                           "Page may be JS-rendered.")
            return None

        for card in cards:
            name_elem = (
                card.select_one("h2, h3, .ecl-card__title, .field--name-title")
            )
            name = name_elem.get_text(strip=True) if name_elem else ""

            link = card.select_one("a[href]")
            profile_url = ""
            if link:
                href = link.get("href", "")
                if href.startswith("/"):
                    profile_url = f"https://commissioners.ec.europa.eu{href}"
                elif href.startswith("http"):
                    profile_url = href

            portfolio_elem = card.select_one(
                ".ecl-card__description, .field--name-field-portfolio"
            )
            portfolio = portfolio_elem.get_text(strip=True) if portfolio_elem else ""

            if name:
                records.append({
                    "full_name": name,
                    "portfolio_title": portfolio,
                    "profile_url": profile_url,
                })

        if len(records) >= 20:
            logger.info(f"Scraped {len(records)} commissioners from website.")
            return records
        else:
            logger.warning(f"Only found {len(records)} records (expected ~27). "
                           f"Falling back to curated data.")
            return None

    except Exception as e:
        logger.warning(f"Scraping failed: {e}. Using curated fallback.")
        return None


def merge_scraped_with_curated(scraped: List[Dict], logger) -> List[Dict]:
    """
    Merge scraped data with curated metadata from config.py.
    Curated data provides fields that can't be scraped (country, party, etc.).
    """
    from scripts.utils import normalize_name

    curated_lookup = {}
    for c in config.COMMISSIONERS_CURATED:
        key = normalize_name(c["full_name"]).lower()
        curated_lookup[key] = c
        # Also index by last name
        key2 = normalize_name(c["last_name"]).lower()
        curated_lookup[key2] = c

    merged = []
    matched_ids = set()

    for sc in scraped:
        sc_key = normalize_name(sc["full_name"]).lower()

        # Try exact match
        curated = curated_lookup.get(sc_key)

        # Try partial match on last name
        if curated is None:
            for word in sc_key.split():
                if word in curated_lookup:
                    curated = curated_lookup[word]
                    break

        if curated is not None:
            record = dict(curated)
            # Prefer scraped profile_url if available
            if sc.get("profile_url"):
                record["profile_url"] = sc["profile_url"]
            merged.append(record)
            matched_ids.add(curated["commissioner_id"])
        else:
            logger.warning(f"No curated match for scraped name: {sc['full_name']}")

    # Add any curated entries that weren't matched
    for c in config.COMMISSIONERS_CURATED:
        if c["commissioner_id"] not in matched_ids:
            merged.append(dict(c))
            logger.info(f"Added unmatched curated entry: {c['full_name']}")

    return merged


def build_from_curated(logger) -> List[Dict]:
    """Build commissioner list entirely from curated config data."""
    logger.info("Building commissioners from curated data (27 entries).")
    return [dict(c) for c in config.COMMISSIONERS_CURATED]


def build_commissioners() -> pd.DataFrame:
    """Main function: scrape or fall back to curated, return DataFrame."""
    logger = setup_logging("01_commissioners")
    ensure_dirs()

    # Try scraping first
    scraped = scrape_ec_website(logger)

    if scraped is not None:
        records = merge_scraped_with_curated(scraped, logger)
    else:
        records = build_from_curated(logger)

    # Add hearing_date from hearings curated data
    hearing_dates = {h["commissioner_id"]: h["hearing_date"]
                     for h in config.HEARINGS_CURATED}

    for record in records:
        cid = record.get("commissioner_id", "")
        record["hearing_date"] = hearing_dates.get(cid, "")

    df = pd.DataFrame(records)

    # Ensure proper column order
    columns = [
        "commissioner_id", "full_name", "last_name", "first_name",
        "country", "country_name", "portfolio_title", "role",
        "ep_party_group", "national_party", "gender",
        "dgs_responsible", "mission_letter_url", "hearing_date", "profile_url",
    ]
    columns = [c for c in columns if c in df.columns]
    df = df[columns]

    # Sort by last name
    df = df.sort_values("last_name").reset_index(drop=True)

    logger.info(f"Commissioner dataset: {len(df)} rows, "
                f"{df['country'].nunique()} countries")
    return df


def main():
    df = build_commissioners()
    save_both(df, "commissioners")
    print(f"commissioners: {len(df)} rows saved.")
    return df


if __name__ == "__main__":
    main()
