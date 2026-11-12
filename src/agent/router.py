"""Route a customer message to order / consultant / faq / ignore using Jev."""

import logging

from pydantic import ValidationError

from src.exceptions import ModelServiceUnavailableError, RouterOutputError
from src.infrastructure.model_client import ModelClient
from src.observability.logging import dump_json
from src.prompt.router import ROUTE_QUESTION_KEY, build_router_questions
from src.schema.router import RouterAction, RouterDecision

logger = logging.getLogger(__name__)


class Router:
    def __init__(self, client: ModelClient, model: str, confidence_threshold: float):
        self._client = client
        self._model = model
        self._threshold = confidence_threshold
        self._questions = build_router_questions()

    async def route(self, message: str) -> RouterDecision:
        logger.info(
            "STAGE Router.route INPUT: %s",
            dump_json({"message": message, "model": self._model, "threshold": self._threshold}),
        )
        try:
            raw = await self._client.decide(self._model, {"message": message}, self._questions)
            decision = self._parse(raw)
        except (ModelServiceUnavailableError, RouterOutputError) as e:
            fallback = RouterDecision(action=RouterAction.IGNORE, confidence=0.0, is_fallback=True)
            logger.warning(
                "STAGE Router.route FALLBACK (error=%s) OUTPUT: %s",
                e,
                dump_json(fallback.model_dump(mode="json")),
            )
            return fallback

        if decision.confidence < self._threshold:
            fallback = decision.model_copy(update={"action": RouterAction.IGNORE, "is_fallback": True})
            logger.info(
                "STAGE Router.route FALLBACK (low_confidence=%.2f < %.2f) OUTPUT: %s",
                decision.confidence,
                self._threshold,
                dump_json(fallback.model_dump(mode="json")),
            )
            return fallback
        logger.info("STAGE Router.route OUTPUT: %s", dump_json(decision.model_dump(mode="json")))
        return decision

    @staticmethod
    def _parse(raw: dict) -> RouterDecision:
        try:
            answer = raw["answers"][ROUTE_QUESTION_KEY]
            return RouterDecision(
                action=answer["choice"],
                confidence=answer["confidence"],
                probabilities=answer.get("probabilities", {}),
            )
        except (KeyError, TypeError, ValidationError) as e:
            raise RouterOutputError(f"Unexpected Jev response: {raw!r:.300}") from e

