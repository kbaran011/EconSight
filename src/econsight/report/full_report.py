from __future__ import annotations

import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from econsight.config import get_logger
from econsight.db.connection import PROJECT_ROOT

logger = get_logger(__name__)

_NOTEBOOK = PROJECT_ROOT / "notebooks" / "phase2_analysis.ipynb"
_LATEX_AVAILABLE: bool = shutil.which("xelatex") is not None


def generate_full_report() -> bytes:
    """Produce a PDF of the Phase 2 notebook via nbconvert.

    Always call as: await asyncio.to_thread(generate_full_report)
    This function is blocking — do not call directly from async code.
    """
    with tempfile.TemporaryDirectory() as tmpdir:
        output_stem = "phase2_analysis"
        to_fmt = "pdf" if _LATEX_AVAILABLE else "html"
        if not _LATEX_AVAILABLE:
            logger.warning("full_report.latex_unavailable", fallback="html+weasyprint")

        result = subprocess.run(
            [
                sys.executable, "-m", "nbconvert",
                "--execute",
                "--to", to_fmt,
                "--ExecutePreprocessor.timeout=600",
                "--output", output_stem,
                "--output-dir", tmpdir,
                str(_NOTEBOOK),
            ],
            capture_output=True,
            text=True,
            timeout=660,
        )
        if result.returncode != 0:
            raise RuntimeError(f"nbconvert failed:\n{result.stderr[:500]}")

        if to_fmt == "pdf":
            return (Path(tmpdir) / f"{output_stem}.pdf").read_bytes()
        else:
            from weasyprint import HTML
            html_path = Path(tmpdir) / f"{output_stem}.html"
            return bytes(HTML(filename=str(html_path)).write_pdf())
