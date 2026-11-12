"""Per-job (per-request) file logging organized by date: logs/YYYY-MM-DD/<job_id>.log."""

import json
import logging
from collections.abc import Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

DEFAULT_LOG_DIR = Path(__file__).resolve().parents[2] / "logs"
LOG_FORMAT = "%(asctime)s | %(levelname)-7s | [%(job_id)s] %(name)s | %(message)s"

_current_job_id: ContextVar[str | None] = ContextVar("current_job_id", default=None)
_current_job_date: ContextVar[str | None] = ContextVar("current_job_date", default=None)


def dump_json(data: Any) -> str:
    """Serialize any dict/model/value as single-line UTF-8 JSON for detailed stage logs."""
    return json.dumps(data, ensure_ascii=False, default=str)


def get_job_id() -> str | None:
    return _current_job_id.get()


@contextmanager
def job_context(job_id: str | None = None) -> Iterator[str]:
    """Bind a job_id for the duration of a request/task so all logs go to its own file."""
    now = datetime.now()
    active_id = job_id or f"{now.strftime('%H%M%S')}_{uuid4().hex[:8]}"
    tok_id = _current_job_id.set(active_id)
    tok_date = _current_job_date.set(now.strftime("%Y-%m-%d"))
    try:
        yield active_id
    finally:
        _current_job_id.reset(tok_id)
        _current_job_date.reset(tok_date)


class JobContextFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        record.job_id = _current_job_id.get() or "-"
        return True


class JobFileHandler(logging.Handler):
    """Writes log records emitted inside a job_context to <log_dir>/<YYYY-MM-DD>/<job_id>.log."""

    def __init__(self, log_dir: Path = DEFAULT_LOG_DIR) -> None:
        super().__init__()
        self.log_dir = Path(log_dir)

    def emit(self, record: logging.LogRecord) -> None:
        job_id = _current_job_id.get()
        if not job_id:
            return
        try:
            date_folder = _current_job_date.get() or datetime.now().strftime("%Y-%m-%d")
            target_dir = self.log_dir / date_folder
            target_dir.mkdir(parents=True, exist_ok=True)
            msg = self.format(record)
            with (target_dir / f"{job_id}.log").open("a", encoding="utf-8") as f:
                f.write(msg + "\n")
        except OSError:
            self.handleError(record)


def setup_logging(
    log_dir: Path = DEFAULT_LOG_DIR,
    level: int = logging.INFO,
    console: bool = True,
) -> JobFileHandler:
    """Configure the `src` logger with per-job file output and optional console output."""
    pkg_logger = logging.getLogger("src")
    pkg_logger.setLevel(level)
    pkg_logger.propagate = False

    for h in list(pkg_logger.handlers):
        pkg_logger.removeHandler(h)

    formatter = logging.Formatter(LOG_FORMAT)
    ctx_filter = JobContextFilter()

    file_handler = JobFileHandler(log_dir=log_dir)
    file_handler.setFormatter(formatter)
    file_handler.addFilter(ctx_filter)
    pkg_logger.addHandler(file_handler)

    if console:
        stream_handler = logging.StreamHandler()
        stream_handler.setFormatter(formatter)
        stream_handler.addFilter(ctx_filter)
        pkg_logger.addHandler(stream_handler)

    return file_handler
