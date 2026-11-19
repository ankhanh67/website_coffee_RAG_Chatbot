"""Route a customer message to order / consultant / faq / ignore using Jev."""

import logging
from collections.abc import Mapping

from pydantic import ValidationError

from src.exceptions import ModelServiceUnavailableError, RouterOutputError
from src.infrastructure.model_client import ModelClient
from src.observability.logging import dump_json
from src.observability.tracing import trace_observation
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
        input_payload = {"message": message, "model": self._model, "threshold": self._threshold}
        logger.info("STAGE Router.route INPUT: %s", dump_json(input_payload))
        with trace_observation("Router.route", as_type="span", input=input_payload) as span:
            try:
                raw = await self._client.decide(self._model, {"message": message}, self._questions)
                decision = self._parse(raw)
            except (ModelServiceUnavailableError, RouterOutputError) as e:
                fallback = RouterDecision(
                    action=RouterAction.IGNORE, confidence=0.0, is_fallback=True
                )
                span.update(
                    output=fallback.model_dump(mode="json"),
                    level="WARNING",
                    status_message=str(e),
                )
                logger.warning(
                    "STAGE Router.route FALLBACK (error=%s) OUTPUT: %s",
                    e,
                    dump_json(fallback.model_dump(mode="json")),
                )
                return fallback

            if decision.confidence < self._threshold:
                fallback = decision.model_copy(
                    update={"action": RouterAction.IGNORE, "is_fallback": True}
                )
                span.update(output=fallback.model_dump(mode="json"))
                logger.info(
                    "STAGE Router.route FALLBACK (low_confidence=%.2f < %.2f) OUTPUT: %s",
                    decision.confidence,
                    self._threshold,
                    dump_json(fallback.model_dump(mode="json")),
                )
                return fallback
            span.update(output=decision.model_dump(mode="json"))
            logger.info("STAGE Router.route OUTPUT: %s", dump_json(decision.model_dump(mode="json")))
            return decision

    @staticmethod
    def _parse(raw: Mapping[str, object]) -> RouterDecision:
        try:
            answers = raw["answers"]
            if not isinstance(answers, Mapping):
                raise TypeError("answers must be a mapping")
            answer = answers[ROUTE_QUESTION_KEY]
            if not isinstance(answer, Mapping):
                raise TypeError("route answer must be a mapping")
            probabilities = answer.get("probabilities", {})
            return RouterDecision(
                action=answer["choice"],
                confidence=answer["confidence"],
                probabilities=probabilities if isinstance(probabilities, Mapping) else {},
            )
        except (KeyError, TypeError, ValidationError) as e:
            raise RouterOutputError(f"Unexpected Jev response: {raw!r:.300}") from e

