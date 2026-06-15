"""
02_download_mission_letters.py
Download mission letter PDFs for all 27 Commissioners-designate.

Uses URLs from the commissioners dataset (scraped or curated in config.py).
Saves PDFs to data/raw/mission_letters/.

Output: Downloaded PDFs (no CSV output from this script).
"""

import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import config
from scripts.utils import setup_logging, ensure_dirs, download_pdf


def download_mission_letters() -> dict:
    """
    Download all mission letter PDFs.
    Returns dict of commissioner_id -> {path, success}.
    """
    logger = setup_logging("02_mission_letters_download")
    ensure_dirs()

    results = {}
    success_count = 0
    skip_count = 0
    fail_count = 0

    for comm in config.COMMISSIONERS_CURATED:
        cid = comm["commissioner_id"]
        name = comm["full_name"]
        url = comm.get("mission_letter_url", "")

        if not url:
            logger.info(f"No mission letter URL for {name} ({cid}) - skipping "
                        f"(President has no mission letter).")
            skip_count += 1
            results[cid] = {"path": None, "success": False, "reason": "no_url"}
            continue

        # Create a clean filename
        safe_name = comm["last_name"].replace(" ", "_").replace("'", "")
        filename = f"{cid}_{safe_name}_mission_letter.pdf"
        output_path = config.RAW_MISSION_LETTERS / filename

        logger.info(f"Downloading mission letter for {name}...")
        # Rate-limit requests to avoid 429 from EC servers
        time.sleep(3)
        success = download_pdf(url, output_path)

        if success:
            success_count += 1
            results[cid] = {"path": str(output_path), "success": True}
        else:
            fail_count += 1
            results[cid] = {"path": None, "success": False, "reason": "download_failed"}

    logger.info(f"Mission letter downloads complete: "
                f"{success_count} success, {skip_count} skipped, {fail_count} failed")

    return results


def main():
    results = download_mission_letters()
    success = sum(1 for r in results.values() if r["success"])
    total = len(results)
    print(f"Mission letters: {success}/{total} downloaded successfully.")
    return results


if __name__ == "__main__":
    main()
