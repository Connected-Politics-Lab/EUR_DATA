"""
llm_classify.py
LLM-based classification of mission-letter commitments using Claude Sonnet 4.6.

Replaces the brittle keyword classifier with a model that reads the whole
commitment and assigns one of six mutually-exclusive types, with a short
rationale. Results are cached on disk (keyed by a hash of the text) so the
pipeline is reproducible and re-runs are free; ship the cache to let the dataset
rebuild without re-calling the API.

The model output is constrained to the enum via structured outputs
(`messages.parse` with a Pydantic schema), so an invalid type is impossible.

Requires an API key to classify uncached texts, read from
`EURDATA_ANTHROPIC_API_KEY` (preferred - a dedicated name that does NOT collide
with Claude Code's own `ANTHROPIC_API_KEY` auth) or, failing that,
`ANTHROPIC_API_KEY`. If neither the cache nor a key is available, callers fall
back to the keyword classifier.
"""

import hashlib
import json
import logging
import sys
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path
from typing import Dict, List, Optional

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
import config

try:
    import anthropic
    from pydantic import BaseModel
except ImportError:  # pragma: no cover - anthropic/pydantic are runtime deps
    anthropic = None
    BaseModel = object

MODEL = "claude-sonnet-4-6"
CACHE_PATH = config.PROCESSED_DIR / "llm_classification_cache.json"

# Dedicated key name (avoids clobbering Claude Code's own ANTHROPIC_API_KEY
# auth); ANTHROPIC_API_KEY is accepted as a fallback.
API_KEY_ENV = "EURDATA_ANTHROPIC_API_KEY"

COMMITMENT_TYPES = [
    "legislative", "policy", "coordination", "review", "report", "other",
]

SYSTEM_PROMPT = """\
You classify single policy commitments taken from European Commissioners'
mission letters into exactly one category. Read the whole commitment and choose
the category that best describes its PRIMARY action. The categories are mutually
exclusive; pick the single dominant one.

Categories:
- legislative: commits to proposing, revising, amending, repealing, codifying or
  adopting a binding EU legal act (a Regulation, Directive or Decision). The act
  itself is the deliverable. NOT the mere enforcement or application of existing
  law, and NOT a non-binding strategy.
- policy: commits to a NON-binding policy instrument - a strategy, action plan,
  roadmap, communication, white/green paper, agenda or vision. The deliverable is
  a plan or document, not a law.
- coordination: the primary action is working with, coordinating, consulting or
  building partnerships across other Commissioners, institutions, member states
  or stakeholders. Collaboration is the substance, not a specific deliverable.
- review: commits to evaluating, assessing, reviewing, monitoring the
  performance of, or running a fitness check or impact assessment on existing
  measures.
- report: commits to reporting, publishing a report, or establishing ongoing
  monitoring/reporting outputs.
- other: anything that does not clearly fit the above - vague aspirations,
  enforcement of existing rules, administrative or oversight duties, or general
  guidance.

Give a one-sentence rationale naming the decisive cue."""


if BaseModel is not object:
    class CommitmentClassification(BaseModel):
        commitment_type: str  # validated against COMMITMENT_TYPES below
        rationale: str
else:  # pragma: no cover
    CommitmentClassification = None


def _key(text: str) -> str:
    return hashlib.sha256(text.strip().encode("utf-8")).hexdigest()


def load_cache() -> Dict[str, Dict]:
    if CACHE_PATH.exists():
        return json.loads(CACHE_PATH.read_text(encoding="utf-8"))
    return {}


def save_cache(cache: Dict[str, Dict]):
    CACHE_PATH.parent.mkdir(parents=True, exist_ok=True)
    CACHE_PATH.write_text(json.dumps(cache, ensure_ascii=False, indent=0,
                                     sort_keys=True), encoding="utf-8")


_DOTENV_LOADED = False


def _load_dotenv_once():
    """Load a nearby `.env` (searching up from cwd and this module) into the
    environment, without overwriting variables already set. Dependency-free, so
    the key can live in a gitignored `.env` at the project root."""
    global _DOTENV_LOADED
    if _DOTENV_LOADED:
        return
    _DOTENV_LOADED = True
    import os
    candidates = []
    for base in (Path.cwd(), Path(__file__).resolve().parent):
        candidates += [d / ".env" for d in [base, *list(base.parents)[:5]]]
    for env_path in candidates:
        if not env_path.is_file():
            continue
        for line in env_path.read_text(encoding="utf-8").splitlines():
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            k, v = line.split("=", 1)
            k, v = k.strip(), v.strip().strip('"').strip("'")
            if k and k not in os.environ:
                os.environ[k] = v
        break  # first .env found wins


def _api_key() -> Optional[str]:
    import os
    _load_dotenv_once()
    return os.environ.get(API_KEY_ENV) or os.environ.get("ANTHROPIC_API_KEY")


def _client() -> Optional["anthropic.Anthropic"]:
    """Return an Anthropic client, or None if the SDK/key are unavailable."""
    if anthropic is None:
        return None
    key = _api_key()
    if not key:
        return None
    return anthropic.Anthropic(api_key=key, max_retries=4)


def classify_one(client, text: str) -> Dict[str, str]:
    """Classify a single commitment via the API. Returns {type, rationale}."""
    resp = client.messages.parse(
        model=MODEL,
        max_tokens=512,
        system=SYSTEM_PROMPT,
        messages=[{"role": "user", "content": f"Commitment:\n{text}"}],
        output_format=CommitmentClassification,
    )
    out = resp.parsed_output
    ctype = out.commitment_type.strip().lower()
    if ctype not in COMMITMENT_TYPES:
        ctype = "other"
    return {"commitment_type": ctype, "rationale": out.rationale.strip()}


def classify_texts(texts: List[str], logger: logging.Logger = None,
                   max_workers: int = 8) -> Dict[str, Dict[str, str]]:
    """
    Classify many commitment texts, cache-first.

    Returns a dict mapping each text -> {commitment_type, rationale, method}.
    Cached texts are returned immediately; uncached texts are classified via the
    API (concurrently) when a key is available. Texts that can be classified by
    neither route are omitted, leaving the caller to apply its keyword fallback.
    """
    logger = logger or logging.getLogger("llm_classify")
    cache = load_cache()
    results: Dict[str, Dict[str, str]] = {}
    todo = []

    for text in texts:
        cached = cache.get(_key(text))
        if cached:
            results[text] = {**cached, "method": "llm"}
        else:
            todo.append(text)

    if not todo:
        logger.info(f"All {len(texts)} commitments served from LLM cache.")
        return results

    client = _client()
    if client is None:
        logger.warning(
            f"{len(todo)} commitments are not in the LLM cache and no API key "
            f"({API_KEY_ENV} or ANTHROPIC_API_KEY) is set; falling back to keywords.")
        return results

    logger.info(f"Classifying {len(todo)} uncached commitments via {MODEL}...")

    def _do(text):
        try:
            return text, classify_one(client, text)
        except Exception as e:  # pragma: no cover - network/runtime guard
            logger.warning(f"Classification failed for one commitment: {e}")
            return text, None

    with ThreadPoolExecutor(max_workers=max_workers) as pool:
        for text, res in pool.map(_do, todo):
            if res is None:
                continue
            cache[_key(text)] = res
            results[text] = {**res, "method": "llm"}

    save_cache(cache)
    logger.info(f"Cached {len(todo)} new classifications -> {CACHE_PATH.name}")
    return results
