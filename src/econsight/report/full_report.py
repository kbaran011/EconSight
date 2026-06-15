from __future__ import annotations

from pathlib import Path

from econsight.config import get_logger
from econsight.db.connection import PROJECT_ROOT

logger = get_logger(__name__)

_NOTEBOOK = PROJECT_ROOT / "notebooks" / "phase2_analysis.ipynb"


def generate_full_report() -> bytes:
    """Execute the Phase 2 notebook and return a PDF via WeasyPrint.

    Always call as: await asyncio.to_thread(generate_full_report)
    This function is blocking — do not call directly from async code.
    """
    import nbformat
    from nbconvert import HTMLExporter
    from nbconvert.preprocessors import ExecutePreprocessor
    from weasyprint import HTML

    logger.info("full_report.start", notebook=str(_NOTEBOOK))

    with open(_NOTEBOOK) as f:
        nb = nbformat.read(f, as_version=4)

    ep = ExecutePreprocessor(timeout=600, kernel_name="python3")
    ep.preprocess(nb, {"metadata": {"path": str(_NOTEBOOK.parent)}})
    logger.info("full_report.executed")

    exporter = HTMLExporter()
    exporter.exclude_input = True  # cleaner output — hide code cells
    body, _resources = exporter.from_notebook_node(nb)
    logger.info("full_report.converted_html")

    pdf_bytes = bytes(HTML(string=body, base_url=str(_NOTEBOOK.parent)).write_pdf())
    logger.info("full_report.pdf_done", size_kb=len(pdf_bytes) // 1024)
    return pdf_bytes
