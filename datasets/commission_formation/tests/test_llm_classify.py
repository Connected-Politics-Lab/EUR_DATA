"""
test_llm_classify.py
Offline tests for the LLM commitment classifier. The API itself is mocked, so
these run without an ANTHROPIC_API_KEY and validate the cache, the enum
constraint, and the no-key fallback behaviour.
"""

import sys
import types
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

import pytest
from scripts import llm_classify


@pytest.fixture
def tmp_cache(tmp_path, monkeypatch):
    """Point the classifier's cache at a throwaway file."""
    monkeypatch.setattr(llm_classify, "CACHE_PATH", tmp_path / "cache.json")
    return tmp_path / "cache.json"


def _fake_client(returns):
    """A stand-in Anthropic client whose parse() returns canned outputs.

    `returns` maps the commitment text -> (commitment_type, rationale).
    """
    def parse(model, max_tokens, system, messages, output_format):
        text = messages[0]["content"]
        for key, (ctype, rat) in returns.items():
            if key in text:
                parsed = output_format(commitment_type=ctype, rationale=rat)
                return types.SimpleNamespace(parsed_output=parsed)
        parsed = output_format(commitment_type="other", rationale="default")
        return types.SimpleNamespace(parsed_output=parsed)

    return types.SimpleNamespace(messages=types.SimpleNamespace(parse=parse))


def test_cache_roundtrip(tmp_cache):
    llm_classify.save_cache({"abc": {"commitment_type": "policy", "rationale": "x"}})
    assert llm_classify.load_cache()["abc"]["commitment_type"] == "policy"


def test_classify_calls_api_and_caches(tmp_cache, monkeypatch):
    monkeypatch.setattr(llm_classify, "_client",
                        lambda: _fake_client({"revise the Directive": ("legislative", "names a Directive")}))
    texts = ["You will revise the Directive on X."]
    res = llm_classify.classify_texts(texts)
    assert res[texts[0]]["commitment_type"] == "legislative"
    assert res[texts[0]]["method"] == "llm"
    # Result is now cached: a second call with no client still resolves it.
    monkeypatch.setattr(llm_classify, "_client", lambda: None)
    res2 = llm_classify.classify_texts(texts)
    assert res2[texts[0]]["commitment_type"] == "legislative"


def test_no_key_returns_empty_for_uncached(tmp_cache, monkeypatch):
    monkeypatch.setattr(llm_classify, "_client", lambda: None)
    res = llm_classify.classify_texts(["a brand new uncached commitment text"])
    assert res == {}  # caller will apply its keyword fallback


def test_invalid_enum_coerced_to_other(tmp_cache, monkeypatch):
    monkeypatch.setattr(llm_classify, "_client",
                        lambda: _fake_client({"weird": ("nonsense_category", "bad")}))
    res = llm_classify.classify_texts(["this is a weird commitment"])
    assert res["this is a weird commitment"]["commitment_type"] == "other"


def test_all_types_are_valid_enum():
    assert set(llm_classify.COMMITMENT_TYPES) == {
        "legislative", "policy", "coordination", "review", "report", "other"}
