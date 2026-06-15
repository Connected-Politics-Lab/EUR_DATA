"""
Shared utilities for the Commission Formation dataset pipeline.

Provides HTTP fetching with retry/caching, PDF download, save helpers,
name normalization, logging setup, and directory creation.
"""

import logging
import time
import unicodedata
from pathlib import Path

import pandas as pd
import requests

import sys
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config


def setup_logging(script_name: str) -> logging.Logger:
    """Configure console + file logging for a pipeline script."""
    logger = logging.getLogger(script_name)
    if logger.handlers:
        return logger
    logger.setLevel(logging.DEBUG)

    # Console handler
    ch = logging.StreamHandler()
    ch.setLevel(logging.INFO)
    ch.setFormatter(logging.Formatter(config.LOG_FORMAT, config.LOG_DATE_FORMAT))
    logger.addHandler(ch)

    # File handler
    log_dir = config.BASE_DIR / "logs"
    log_dir.mkdir(exist_ok=True)
    fh = logging.FileHandler(log_dir / f"{script_name}.log", encoding="utf-8")
    fh.setLevel(logging.DEBUG)
    fh.setFormatter(logging.Formatter(config.LOG_FORMAT, config.LOG_DATE_FORMAT))
    logger.addHandler(fh)

    return logger


def ensure_dirs():
    """Create the full directory tree if it doesn't exist."""
    for d in [
        config.RAW_DIR,
        config.PROCESSED_DIR,
        config.OUTPUT_DIR,
        config.RAW_MISSION_LETTERS,
        config.RAW_EP_XML,
        config.RAW_WORK_PROGRAMME,
        config.RAW_COMMISSIONER_PAGES,
        config.PROCESSED_MISSION_TEXTS,
    ]:
        d.mkdir(parents=True, exist_ok=True)


def fetch_url(url: str, cache_dir: Path = None, retries: int = 3,
              backoff: float = 2.0, timeout: int = 30) -> requests.Response:
    """
    GET a URL with retry logic, exponential backoff, and optional local caching.

    If cache_dir is provided, responses are cached as files keyed by URL hash.
    Returns the requests.Response object.
    """
    logger = logging.getLogger("utils.fetch_url")

    # Check cache
    if cache_dir is not None:
        cache_dir = Path(cache_dir)
        cache_dir.mkdir(parents=True, exist_ok=True)
        import hashlib
        url_hash = hashlib.md5(url.encode()).hexdigest()
        cache_path = cache_dir / f"{url_hash}.cache"
        if cache_path.exists():
            logger.debug(f"Cache hit for {url}")
            # Return a mock-like response with cached content
            resp = requests.Response()
            resp.status_code = 200
            resp._content = cache_path.read_bytes()
            resp.encoding = "utf-8"
            return resp

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (research-pipeline; commission-formation-dataset) "
            "Python-requests"
        )
    }

    last_exc = None
    for attempt in range(1, retries + 1):
        try:
            logger.debug(f"Fetching {url} (attempt {attempt}/{retries})")
            resp = requests.get(url, headers=headers, timeout=timeout)
            resp.raise_for_status()

            # Save to cache
            if cache_dir is not None:
                cache_path.write_bytes(resp.content)
                logger.debug(f"Cached response for {url}")

            return resp

        except requests.RequestException as e:
            last_exc = e
            logger.warning(f"Attempt {attempt} failed for {url}: {e}")
            if attempt < retries:
                wait = backoff ** attempt
                logger.info(f"Retrying in {wait:.1f}s...")
                time.sleep(wait)

    raise last_exc


def download_pdf(url: str, output_path: Path, retries: int = 3) -> bool:
    """
    Download a PDF file and validate it starts with %PDF magic bytes.
    Returns True on success, False on failure.
    """
    logger = logging.getLogger("utils.download_pdf")
    output_path = Path(output_path)
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if output_path.exists() and output_path.stat().st_size > 1000:
        logger.debug(f"PDF already exists: {output_path}")
        return True

    try:
        resp = fetch_url(url, retries=retries, timeout=60)
        content = resp.content

        # Validate PDF magic bytes
        if not content[:5] == b"%PDF-":
            logger.error(f"Downloaded file is not a valid PDF: {url}")
            return False

        output_path.write_bytes(content)
        logger.info(f"Downloaded PDF: {output_path.name} ({len(content):,} bytes)")
        return True

    except Exception as e:
        logger.error(f"Failed to download PDF from {url}: {e}")
        return False


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


def normalize_name(name: str) -> str:
    """
    Normalize a person's name: strip accents, normalize whitespace, title-case.
    Useful for matching names across different sources.
    """
    if not name:
        return ""
    # Decompose unicode and strip combining characters (accents)
    nfkd = unicodedata.normalize("NFKD", name)
    ascii_name = "".join(c for c in nfkd if not unicodedata.combining(c))
    # Normalize whitespace
    ascii_name = " ".join(ascii_name.split())
    return ascii_name.strip()
