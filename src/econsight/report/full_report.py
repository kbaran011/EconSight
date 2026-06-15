from __future__ import annotations

from pathlib import Path

from econsight.config import get_logger
from econsight.db.connection import PROJECT_ROOT

logger = get_logger(__name__)

_HTML_REPORT = PROJECT_ROOT / "notebooks" / "phase2_report.html"


def generate_full_report() -> bytes:
    """Convert the pre-generated Phase 2 HTML report to PDF via WeasyPrint.

    The HTML report is committed to the repo and included in the Docker image.
    Always call as: await asyncio.to_thread(generate_full_report)
    """
    from weasyprint import HTML

    if not _HTML_REPORT.exists():
        raise FileNotFoundError(
            f"Pre-generated report not found at {_HTML_REPORT}. "
            "Run the Phase 2 notebook locally and commit notebooks/phase2_report.html."
        )

    logger.info("full_report.start", path=str(_HTML_REPORT))
    pdf_bytes = bytes(
        HTML(filename=str(_HTML_REPORT), base_url=str(_HTML_REPORT.parent)).write_pdf()
    )
    logger.info("full_report.done", size_kb=len(pdf_bytes) // 1024)
    return pdf_bytes
