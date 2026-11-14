"""Service for normalizing generated responses for Text-To-Speech (TTS)."""

import logging

from src.guardrails.tts_normalizer import normalize_for_tts

logger = logging.getLogger(__name__)


class TTSService:
    @staticmethod
    def normalize(text: str) -> str:
        """Normalize conversational text for natural Vietnamese TTS audio synthesis."""
        return normalize_for_tts(text)
