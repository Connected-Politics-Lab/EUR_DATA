"""
run_pipeline.py
Orchestration for the agenda-implementation dataset pipeline.

Usage:
    python run_pipeline.py             # Run all steps
    python run_pipeline.py --step 4    # Run only step 4
    python run_pipeline.py --from 3    # Run from step 3 onwards
    python run_pipeline.py --offline   # Skip the network steps (3, 4, 6)

Network steps (03 term output, 04 procedure status, 06 EUR-Lex enrichment)
cache to data/raw/, so re-runs are cheap and replayable offline.
"""

import argparse
import sys
import time
from pathlib import Path
from typing import Tuple

sys.path.insert(0, str(Path(__file__).resolve().parent))

from scripts.utils import setup_logging, ensure_dirs


STEPS = {
    1: ("01_build_agenda_items", "Building agenda-item spine"),
    2: ("02_parse_procedure_refs", "Parsing embedded procedure references"),
    3: ("03_fetch_term_output", "Fetching term legislative output (EP API)"),
    4: ("04_fetch_procedure_status", "Fetching procedure status snapshot (EP API)"),
    5: ("05_match_annex_i", "Matching Annex I new initiatives"),
    6: ("06_enrich_eurlex", "Cross-checking final acts (EUR-Lex)"),
    7: ("07_build_evaluations", "Building curated evaluations & commitments"),
}
NETWORK_STEPS = {3, 4, 6}
LAST_STEP = max(STEPS)


def run_step(step_num: int, logger) -> Tuple[bool, float, int]:
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
        logger.info(f"Step {step_num} completed in {elapsed:.1f}s ({row_count} rows/items)")
        return True, elapsed, row_count
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"Step {step_num} FAILED after {elapsed:.1f}s: {e}")
        import traceback
        logger.debug(traceback.format_exc())
        return False, elapsed, 0


def main():
    parser = argparse.ArgumentParser(
        description="Run the agenda-implementation dataset pipeline."
    )
    parser.add_argument("--step", type=int, help="Run only this step number")
    parser.add_argument("--from", type=int, dest="from_step",
                        help="Start from this step number")
    parser.add_argument("--offline", action="store_true",
                        help="Skip the network steps (3, 4, 6)")
    args = parser.parse_args()

    logger = setup_logging("pipeline")
    ensure_dirs()

    logger.info("=" * 60)
    logger.info("Agenda-Implementation Dataset Pipeline")
    logger.info("=" * 60)

    if args.step:
        steps_to_run = [args.step]
    elif args.from_step:
        steps_to_run = list(range(args.from_step, LAST_STEP + 1))
    else:
        steps_to_run = list(range(1, LAST_STEP + 1))

    if args.offline:
        skipped = [s for s in steps_to_run if s in NETWORK_STEPS]
        steps_to_run = [s for s in steps_to_run if s not in NETWORK_STEPS]
        if skipped:
            logger.info(f"Offline mode: skipping network steps {skipped}")

    results = {}
    total_start = time.time()
    for step_num in steps_to_run:
        if step_num not in STEPS:
            logger.warning(f"Unknown step: {step_num}")
            continue
        success, elapsed, rows = run_step(step_num, logger)
        results[step_num] = {"name": STEPS[step_num][1], "success": success,
                             "elapsed": elapsed, "rows": rows}

    total_elapsed = time.time() - total_start
    logger.info("")
    logger.info("=" * 60)
    logger.info("PIPELINE SUMMARY")
    logger.info("=" * 60)
    for step_num, r in sorted(results.items()):
        status = "OK" if r["success"] else "FAIL"
        logger.info(f"  Step {step_num}: [{status}] {r['name']} "
                    f"({r['rows']} rows, {r['elapsed']:.1f}s)")

    succeeded = sum(1 for r in results.values() if r["success"])
    total = len(results)
    logger.info(f"\n  {succeeded}/{total} steps succeeded in {total_elapsed:.1f}s total.")
    if succeeded < total:
        logger.warning("Some steps failed. Check logs for details.")
        sys.exit(1)
    logger.info("Pipeline completed successfully!")


if __name__ == "__main__":
    main()
