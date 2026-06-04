"""Execute phase2_analysis.ipynb and export to HTML."""
import os
import subprocess
import sys
from pathlib import Path

NOTEBOOK = Path(__file__).parent / "phase2_analysis.ipynb"
OUTPUT = Path(__file__).parent / "phase2_report.html"
# Project root contains .env; inject its contents into the environment so that
# pydantic-settings picks them up regardless of the kernel's working directory.
PROJECT_ROOT = Path(__file__).parent.parent


def _load_dotenv(env: dict) -> None:
    """Parse .env and merge into env dict (does not overwrite existing vars)."""
    dotenv = PROJECT_ROOT / ".env"
    if not dotenv.exists():
        return
    for line in dotenv.read_text().splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key = key.strip()
        if key not in env:
            env[key] = value.strip()


def main() -> None:
    env = os.environ.copy()
    _load_dotenv(env)
    result = subprocess.run(
        [
            sys.executable, "-m", "nbconvert",
            "--to", "html",
            "--execute",
            "--ExecutePreprocessor.timeout=600",
            "--ExecutePreprocessor.kernel_name=python3",
            "--output", str(OUTPUT),
            str(NOTEBOOK),
        ],
        capture_output=True,
        text=True,
        env=env,
    )
    if result.returncode != 0:
        print(result.stderr)
        sys.exit(result.returncode)
    print(f"Report saved to {OUTPUT}")


if __name__ == "__main__":
    main()
