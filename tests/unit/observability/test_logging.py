import asyncio
import logging
from datetime import datetime

from src.observability.logging import job_context, setup_logging


async def test_concurrent_jobs_write_isolated_date_log_files(tmp_path):
    log_dir = tmp_path / "logs"
    setup_logging(log_dir=log_dir, console=False)
    logger = logging.getLogger("src.test_worker")

    async def worker(job_id: str, marker: str) -> None:
        with job_context(job_id):
            logger.info("step 1 %s", marker)
            await asyncio.sleep(0.01)
            logger.info("step 2 %s", marker)

    await asyncio.gather(worker("job_alpha", "ALPHA"), worker("job_beta", "BETA"))

    today = datetime.now().strftime("%Y-%m-%d")
    alpha_file = log_dir / today / "job_alpha.log"
    beta_file = log_dir / today / "job_beta.log"

    assert alpha_file.is_file()
    assert beta_file.is_file()

    alpha_text = alpha_file.read_text(encoding="utf-8")
    beta_text = beta_file.read_text(encoding="utf-8")

    assert "[job_alpha]" in alpha_text
    assert "step 1 ALPHA" in alpha_text and "step 2 ALPHA" in alpha_text
    assert "BETA" not in alpha_text

    assert "[job_beta]" in beta_text
    assert "step 1 BETA" in beta_text and "step 2 BETA" in beta_text
    assert "ALPHA" not in beta_text
