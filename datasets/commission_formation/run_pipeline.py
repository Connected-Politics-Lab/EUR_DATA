"""
run_pipeline.py
Orchestration script for the Commission Formation dataset pipeline.

Runs all 7 pipeline scripts in sequence, tracks timing, and reports results.

Usage:
    python run_pipeline.py             # Run all steps
    python run_pipeline.py --step 1    # Run only step 1 (commissioners)
    python run_pipeline.py --from 3    # Run from step 3 onwards
    python run_pipeline.py --skip-download  # Skip PDF downloads (02)
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.utils import setup_logging, ensure_dirs


STEPS = {
    1: ("01_scrape_commissioners", "Scraping commissioner profiles"),
    2: ("02_download_mission_letters", "Downloading mission letter PDFs"),
    3: ("03_parse_mission_letters", "Parsing mission letter commitments"),
    4: ("04_scrape_hearings", "Building hearings dataset"),
    5: ("05_fetch_investiture_vote", "Fetching investiture vote data"),
    6: ("06_parse_work_programme", "Parsing Commission Work Programme"),
    7: ("07_build_timeline", "Building formation timeline"),
}


def run_step(step_num: int, logger) -> tuple[bool, float, int]:
    """
    Run a single pipeline step.
    Returns (success, elapsed_seconds, row_count).
    """
    module_name, description = STEPS[step_num]
    logger.info(f"{'='*60}")
    logger.info(f"Step {step_num}: {description}")
    logger.info(f"{'='*60}")

    start = time.time()
    try:
        module = __import__(f"scripts.{module_name}", fromlist=["main"])
        result = module.main()
        elapsed = time.time() - start

        row_count = len(result) if hasattr(result, "__len__") else 0
        if isinstance(result, dict):
            row_count = sum(1 for v in result.values()
                           if isinstance(v, dict) and v.get("success"))

        logger.info(f"Step {step_num} completed in {elapsed:.1f}s "
                     f"({row_count} rows/items)")
        return True, elapsed, row_count

    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"Step {step_num} FAILED after {elapsed:.1f}s: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False, elapsed, 0


def main():
    parser = argparse.ArgumentParser(
        description="Run the Commission Formation dataset pipeline."
    )
    parser.add_argument("--step", type=int, help="Run only this step number (1-7)")
    parser.add_argument("--from", type=int, dest="from_step",
                        help="Start from this step number")
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip step 2 (mission letter PDF downloads)")
    args = parser.parse_args()

    logger = setup_logging("pipeline")
    ensure_dirs()

    logger.info("=" * 60)
    logger.info("Commission Formation Dataset Pipeline")
    logger.info("=" * 60)

    # Determine which steps to run
    if args.step:
        steps_to_run = [args.step]
    elif args.from_step:
        steps_to_run = list(range(args.from_step, 8))
    else:
        steps_to_run = list(range(1, 8))

    if args.skip_download and 2 in steps_to_run:
        steps_to_run.remove(2)
        logger.info("Skipping step 2 (mission letter downloads)")

    results = {}
    total_start = time.time()

    for step_num in steps_to_run:
        if step_num not in STEPS:
            logger.warning(f"Unknown step: {step_num}")
            continue

        success, elapsed, rows = run_step(step_num, logger)
        results[step_num] = {
            "name": STEPS[step_num][1],
            "success": success,
            "elapsed": elapsed,
            "rows": rows,
        }

    total_elapsed = time.time() - total_start

    # Summary report
    logger.info("")
    logger.info("=" * 60)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 60)

    for step_num, result in sorted(results.items()):
        status = "OK" if result["success"] else "FAIL"
        logger.info(
            f"  Step {step_num}: [{status}] {result['name']} "
            f"({result['rows']} rows, {result['elapsed']:.1f}s)"
        )

    succeeded = sum(1 for r in results.values() if r["success"])
    total = len(results)
    logger.info(f"\n  {succeeded}/{total} steps succeeded "
                f"in {total_elapsed:.1f}s total.")

    if succeeded < total:
        logger.warning("Some steps failed. Check logs for details.")
        sys.exit(1)
    else:
        logger.info("Pipeline completed successfully!")


if __name__ == "__main__":
    main()
