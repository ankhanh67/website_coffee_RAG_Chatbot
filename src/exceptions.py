"""Domain exceptions shared across layers."""


class AppError(Exception):
    """Base class for application errors."""


class RouterOutputError(AppError):
    """Router LLM returned output that failed schema validation."""


class AgentExecutionError(AppError):
    """A subagent failed while handling a request."""


class RetrievalError(AppError):
    """Graph/vector retrieval from Neo4j failed."""


class QueueTimeoutError(AppError):
    """A request waited too long in the request queue."""


class ModelServiceUnavailableError(AppError):
    """LLM API is unreachable or keeps failing after retries."""

