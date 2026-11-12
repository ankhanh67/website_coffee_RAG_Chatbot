import pytest

from src.observability.logging import setup_logging


@pytest.fixture(autouse=True)
def _isolate_job_logs(tmp_path):
    setup_logging(log_dir=tmp_path / "logs", console=False)

