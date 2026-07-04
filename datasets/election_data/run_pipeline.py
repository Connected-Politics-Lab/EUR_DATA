"""
run_pipeline.py
Orchestration script for the euandi 2024 election dataset pipeline.

Runs the parse steps in sequence, tracks timing, and reports results. The
pipeline is purely a parse of the static workbooks in data/raw/ - no network
access is required, so it is fast and deterministic.

Usage:
    python run_pipeline.py             # Run all steps
    python run_pipeline.py --step 1    # Run only step 1 (Ireland)
    python run_pipeline.py --from 2    # Run from step 2 onwards
"""

import argparse
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.utils import setup_logging, ensure_dirs


STEPS = {
    1: ("01_parse_ireland", "Parsing Ireland parties & candidates"),
    2: ("02_parse_eu_level", "Parsing EU-level party families"),
}

LAST_STEP = max(STEPS)


def run_step(step_num: int, logger):
    """Run a single pipeline step. Returns (success, elapsed_seconds, rows)."""
    module_name, description = STEPS[step_num]
    logger.info("=" * 60)
    logger.info(f"Step {step_num}: {description}")
    logger.info("=" * 60)

    start = time.time()
    try:
        module = __import__(f"scripts.{module_name}", fromlist=["main"])
        result = module.main()
        elapsed = time.time() - start
        row_count = len(result) if hasattr(result, "__len__") else 0
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
        description="Run the euandi 2024 election dataset pipeline."
    )
    parser.add_argument("--step", type=int, help="Run only this step number")
    parser.add_argument("--from", type=int, dest="from_step",
                        help="Start from this step number")
    args = parser.parse_args()

    logger = setup_logging("pipeline")
    ensure_dirs()

    logger.info("=" * 60)
    logger.info("euandi 2024 Election Dataset Pipeline")
    logger.info("=" * 60)

    if args.step:
        steps_to_run = [args.step]
    elif args.from_step:
        steps_to_run = list(range(args.from_step, LAST_STEP + 1))
    else:
        steps_to_run = list(range(1, LAST_STEP + 1))

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
