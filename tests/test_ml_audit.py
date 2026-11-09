"""Tests for machine learning architecture, datasets, algorithms and fallback contracts.

Zero live API calls and zero credit consumption.
"""
import csv
import os
import sys
from unittest.mock import MagicMock

import pytest

import llm_judge
import matcher
import reranker

ROOT_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def test_ml_phrases_glossary_integrity():
    """Verify that ml/phrases.csv contains valid schema, non-empty text, and supported places."""
    csv_path = os.path.join(ROOT_DIR, "ml", "phrases.csv")
    assert os.path.isfile(csv_path), "ml/phrases.csv must exist"

    with open(csv_path, encoding="utf-8") as f:
        reader = csv.DictReader(f)
        required_cols = {"phrase_id", "hindi", "latin", "meaning_en", "place"}
        assert required_cols.issubset(set(reader.fieldnames or [])), f"Missing required columns in {csv_path}"

        rows = list(reader)
        assert len(rows) == 310, f"Expected 310 phrases in glossary, found {len(rows)}"

        valid_places = {"home", "hospital", "market", "any"}
        seen_ids = set()
        for r in rows:
            assert r["phrase_id"] not in seen_ids, f"Duplicate phrase_id: {r['phrase_id']}"
            seen_ids.add(r["phrase_id"])
            assert r["hindi"].strip(), "Hindi text must not be empty"
            assert r["latin"].strip(), "Latin text must not be empty"
            assert r["meaning_en"].strip(), "English meaning must not be empty"
            assert r["place"].strip() in valid_places, f"Invalid place: {r['place']}"


def test_matcher_normalization_and_phonetic_equivalence():
    """Verify that matcher normalizes Hindi and Latin forms into equivalent phonetic representations."""
    # Test Devanagari to ITRANS transliteration equivalence
    assert matcher.normalize("पानी चाहिए") == matcher.normalize("pAnI chAhie") == "pani chahie"
    assert matcher.normalize("मैं ठीक हूँ।") == "maim thika hun"

    # Test punctuation and whitespace normalization
    assert matcher.normalize("  नमस्ते, मुझे   पानी चाहिए!  । ") == "namaste mujhe pani chahie"

    # Test similarity bounds
    assert matcher.similarity("पानी चाहिए", "Pani Chahie!") == 100.0
    assert matcher.similarity("पानी चाहिए", "paani chahiye") > 84.0
    assert matcher.similarity("मदद चाहिए", "madad chahiye") > 80.0
    assert matcher.similarity("पानी चाहिए", "डॉक्टर को बुलाओ") < 30.0


def test_matcher_ranking_and_usage_priors():
    """Verify that ranking applies contextual boosts and frequency without overturning dominant similarity."""
    candidates = [
        {"key": 1, "fingerprints": ["paani chahiye"], "contexts": ["home"]},
        {"key": 2, "fingerprints": ["chai chahiye"], "contexts": ["hospital"]},
        {"key": 3, "fingerprints": ["madad chahiye"], "contexts": ["hospital"]},
    ]

    # Test exact match dominates even with different context
    ranked = matcher.rank("paani chahiye", candidates, context="hospital")
    assert ranked[0]["key"] == 1
    assert ranked[0]["parts"]["similarity"] == 100.0
    assert ranked[0]["parts"]["context"] == 0

    # Test context boost breaks near ties
    tied_candidates = [
        {"key": 10, "fingerprints": ["dard ho raha hai"], "contexts": ["home"]},
        {"key": 20, "fingerprints": ["dard ho raha hai"], "contexts": ["hospital"]},
    ]
    ranked_tied = matcher.rank("dard ho raha hai", tied_candidates, context="hospital")
    assert ranked_tied[0]["key"] == 20
    assert ranked_tied[0]["parts"]["context"] == matcher.CONTEXT_BOOST


def test_reranker_graceful_fallback_when_disabled(monkeypatch):
    """Verify that reranker remains off and returns unperturbed ranking when RERANKER_ENABLED is unset."""
    monkeypatch.delenv("RERANKER_ENABLED", raising=False)
    monkeypatch.setattr(reranker, "_model", None)

    reranker.load()
    assert not reranker.on()

    input_ranked = [
        {"phrase_id": 1, "text": "पानी चाहिए", "score": 90.0, "parts": {"similarity": 90.0}},
        {"phrase_id": 2, "text": "खाना चाहिए", "score": 80.0, "parts": {"similarity": 80.0}},
    ]
    rescored = reranker.rescore("paani", input_ranked)
    assert rescored == input_ranked
    assert not any("rerank" in c["parts"] for c in rescored)


def test_llm_judge_uncertainty_thresholds(monkeypatch):
    """Verify that llm_judge asks the model only when candidate margin is within the uncertainty window."""
    monkeypatch.setenv("LLM_ENABLED", "1")
    monkeypatch.setenv("LLM_MODE", "uncertain")

    # Definite lead: margin = 30 points (85 vs 55) and heard has >2 words -> should NOT ask
    heard_long = "mujhe thoda paani chahiye"
    confident_ranked = [
        {"phrase_id": 1, "text": "पानी चाहिए", "score": 85.0, "parts": {"similarity": 85.0}},
        {"phrase_id": 2, "text": "खाना चाहिए", "score": 55.0, "parts": {"similarity": 55.0}},
    ]
    assert not llm_judge.should_ask(heard_long, confident_ranked)

    # Ambiguous lead: margin = 2 points (82 vs 80) -> SHOULD ask
    ambiguous_ranked = [
        {"phrase_id": 1, "text": "पानी चाहिए", "score": 82.0, "parts": {"similarity": 82.0}},
        {"phrase_id": 2, "text": "बानी चाहिए", "score": 80.0, "parts": {"similarity": 80.0}},
    ]
    assert llm_judge.should_ask(heard_long, ambiguous_ranked)


def test_cross_platform_path_handling():
    """Verify that all core ML modules use os.path functions and avoid platform-specific path assumptions."""
    assert os.path.exists(matcher.GLOSSARY)
    assert os.path.isabs(matcher.GLOSSARY)
    assert not "\\" in matcher.GLOSSARY.replace(os.sep, "/")
