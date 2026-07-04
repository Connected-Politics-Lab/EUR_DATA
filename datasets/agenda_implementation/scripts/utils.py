"""
Shared utilities for the agenda-implementation pipeline.

Logging, directory creation, the CSV/XLSX save helper, the as-of-date helper,
and the cached HTTP helpers for the EP Open Data API (JSON-LD) and the EUR-Lex
SPARQL endpoint. The cache (keyed by URL hash, under data/raw/) makes re-runs
cheap and replayable offline.
"""

import hashlib
import json
import logging
import os
import sys
import time
from datetime import date
from pathlib import Path
from typing import Dict, List, Optional

import pandas as pd
import requests

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def setup_logging(script_name: str) -> logging.Logger:
    """Configure console + file logging for a pipeline script."""
    logger = logging.getLogger(script_name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(config.LOG_FORMAT, config.LOG_DATE_FORMAT))
    logger.addHandler(ch)

    log_dir = config.BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    fh = logging.FileHandler(log_dir / f"{script_name}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(config.LOG_FORMAT, config.LOG_DATE_FORMAT))
    logger.addHandler(fh)

    return logger


def ensure_dirs():
    """Create the directory tree if it doesn't exist."""
    for d in [config.RAW_DIR, config.OUTPUT_DIR, config.MANUAL_DIR]:
        d.mkdir(parents=True, exist_ok=True)


def as_of_date() -> str:
    """
    The snapshot date stamped on every status row (ISO yyyy-mm-dd).

    Overridable via the AGENDA_AS_OF env var so re-runs and tests are
    reproducible; otherwise today's date.
    """
    return os.environ.get("AGENDA_AS_OF", date.today().isoformat())


def save_both(df: pd.DataFrame, basename: str, output_dir: Path = None):
    """Save a DataFrame as both CSV and XLSX to the output directory."""
    logger = logging.getLogger("utils.save_both")
    if output_dir is None:
        output_dir = config.OUTPUT_DIR
    output_dir.mkdir(parents=True, exist_ok=True)

    csv_path = output_dir / f"{basename}.csv"
    xlsx_path = output_dir / f"{basename}.xlsx"

    df.to_csv(csv_path, index=False, encoding="utf-8-sig")
    df.to_excel(xlsx_path, index=False, engine="openpyxl")

    logger.info(f"Saved {basename}: {len(df)} rows -> {csv_path.name}, {xlsx_path.name}")
    return csv_path, xlsx_path


def _cache_path(key: str) -> Path:
    config.RAW_DIR.mkdir(parents=True, exist_ok=True)
    return config.RAW_DIR / f"{hashlib.md5(key.encode()).hexdigest()}.json"


def fetch_json(url: str, params: Optional[Dict] = None, accept: str = None,
               retries: int = 3, backoff: float = 2.0, timeout: int = 30,
               use_cache: bool = True) -> Optional[Dict]:
    """
    GET a URL and parse the JSON body, with retry/backoff and a local file
    cache keyed by the full request URL. Returns the parsed object, or None on
    a clean 404 / persistent failure.

    The EP Open Data API needs the JSON-LD Accept header (it returns 406
    otherwise); that is the default.
    """
    logger = logging.getLogger("utils.fetch_json")
    accept = accept or config.EP_API_ACCEPT

    prepared = requests.Request("GET", url, params=params).prepare()
    full_url = prepared.url
    cache = _cache_path(full_url)
    if use_cache and cache.exists():
        logger.debug(f"Cache hit: {full_url}")
        return json.loads(cache.read_text(encoding="utf-8"))

    headers = {"Accept": accept, "User-Agent": "agenda-implementation-dataset"}
    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            logger.debug(f"GET {full_url} (attempt {attempt}/{retries})")
            resp = requests.get(url, params=params, headers=headers, timeout=timeout)
            if resp.status_code == 404:
                logger.debug(f"404 for {full_url}")
                return None
            resp.raise_for_status()
            # The EP API returns 200 with an empty body for zero-result pages.
            if not resp.content.strip():
                logger.debug(f"Empty body (no results) for {full_url}")
                return None
            try:
                data = resp.json()
            except ValueError:
                logger.debug(f"Non-JSON body (treated as no results) for {full_url}")
                return None
            if use_cache:
                cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
            time.sleep(config.EP_API_SLEEP)
            return data
        except requests.RequestException as e:
            last_exc = e
            logger.warning(f"Attempt {attempt} failed for {full_url}: {e}")
            if attempt < retries:
                time.sleep(backoff ** attempt)

    logger.error(f"Giving up on {full_url}: {last_exc}")
    return None


def sparql_query(query: str, retries: int = 3, timeout: int = 60,
                 use_cache: bool = True) -> List[Dict]:
    """
    Run a SPARQL query against the EUR-Lex Cellar endpoint and return the
    bindings as a list of {var: value} dicts. Cached by query text. Returns []
    on failure (enrichment is best-effort and must never break the pipeline).
    """
    logger = logging.getLogger("utils.sparql")
    params = {"query": query, "format": "application/sparql-results+json"}
    prepared = requests.Request("GET", config.EURLEX_SPARQL, params=params).prepare()
    cache = _cache_path(prepared.url)
    if use_cache and cache.exists():
        data = json.loads(cache.read_text(encoding="utf-8"))
    else:
        data = None
        for attempt in range(1, retries + 1):
            try:
                resp = requests.get(config.EURLEX_SPARQL, params=params,
                                    headers={"Accept": "application/sparql-results+json"},
                                    timeout=timeout)
                resp.raise_for_status()
                data = resp.json()
                if use_cache:
                    cache.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
                time.sleep(config.EP_API_SLEEP)
                break
            except (requests.RequestException, ValueError) as e:
                logger.warning(f"SPARQL attempt {attempt} failed: {e}")
                if attempt < retries:
                    time.sleep(2.0 ** attempt)
        if data is None:
            return []

    out = []
    for b in data.get("results", {}).get("bindings", []):
        out.append({k: v.get("value") for k, v in b.items()})
    return out
