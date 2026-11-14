"""Unit tests for TTS Normalizer evaluating against `data/evaluation/tts_cases.json`."""

import json
from pathlib import Path

import pytest

from src.guardrails.tts_normalizer import normalize_for_tts

BASE_DIR = Path(__file__).resolve().parents[3]
TTS_CASES_PATH = BASE_DIR / "data" / "evaluation" / "tts_cases.json"
CASES = json.loads(TTS_CASES_PATH.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["id"] for c in CASES])
def test_tts_normalization_matches_expected(case: dict):
    input_text = case["input"]
    expected = case["expected"]
    actual = normalize_for_tts(input_text)
    assert actual == expected, f"Failed on case {case['id']} ({case.get('tag')}): expected '{expected}', got '{actual}'"


def test_empty_string_returns_empty():
    assert normalize_for_tts("") == ""
