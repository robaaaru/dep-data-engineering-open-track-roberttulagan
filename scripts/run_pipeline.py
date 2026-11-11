"""Run the complete project pipeline from source data to analysis outputs.

Run from the repository root:
    python scripts/run_pipeline.py

Use --skip-ingest when the local PAGASA archive is already complete.
"""

import argparse
import subprocess
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PYTHON = ROOT / "venv" / "Scripts" / "python.exe"
PROCESSED = ROOT / "data" / "processed"
OUTPUT = ROOT / "output"
NOTEBOOK = ROOT / "notebooks" / "kpi_and_segmentation_analysis.ipynb"
REQUIRED_OUTPUTS = (
    PROCESSED / "rice_data.csv",
    PROCESSED / "provincial_boundaries.csv",
    PROCESSED / "typhoon_forecast.csv",
    PROCESSED / "province_signals.csv",
)
ANALYSIS_OUTPUTS = (
    OUTPUT / "kpi_definitions.csv",
    OUTPUT / "kpi_trends.csv",
    OUTPUT / "repeat_hit_provinces.csv",
    OUTPUT / "province_groups.csv",
    OUTPUT / "region_groups.csv",
)


def run_step(label, command):
    """Run one pipeline step and stop with a useful error if it fails."""
    print(f"\n== {label} ==")
    subprocess.run(command, cwd=ROOT, check=True)


def main():
    if not PYTHON.is_file():
        raise RuntimeError(
            f"Project virtual-environment interpreter was not found: {PYTHON}. "
            "Create it with `python -m venv venv` and install requirements first."
        )

    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-ingest",
        action="store_true",
        help="Skip downloading PAGASA bulletins and use the local raw archive.",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Redownload existing PAGASA bulletins during ingestion.",
    )
    args = parser.parse_args()
    python_command = str(PYTHON)
    print(f"\n== Using project interpreter: {python_command} ==")

    if not args.skip_ingest:
        ingest_command = [python_command, "scripts/ingest.py"]
        if args.overwrite:
            ingest_command.append("--overwrite")
        run_step("Ingesting PAGASA bulletins", ingest_command)
    else:
        print("\n== Ingestion skipped; using local raw data ==")

    run_step("Transforming raw data", [python_command, "scripts/transform.py"])

    missing = [path for path in REQUIRED_OUTPUTS if not path.exists()]
    if missing:
        missing_names = ", ".join(str(path.relative_to(ROOT)) for path in missing)
        raise RuntimeError(
            "Transformation did not produce the required processed files: "
            f"{missing_names}"
        )

    run_step("Loading SQLite database", [python_command, "scripts/load_sqlite.py"])
    run_step(
        "Running analysis notebook",
        [
            python_command,
            "-m",
            "jupyter",
            "nbconvert",
            "--to",
            "notebook",
            "--execute",
            "--inplace",
            "--ExecutePreprocessor.allow_errors=False",
            "--ExecutePreprocessor.timeout=600",
            str(NOTEBOOK),
        ],
    )
    missing_outputs = [path for path in ANALYSIS_OUTPUTS if not path.exists()]
    if missing_outputs:
        missing_names = ", ".join(str(path.relative_to(ROOT)) for path in missing_outputs)
        raise RuntimeError(
            "Analysis notebook did not produce the required output files: "
            f"{missing_names}"
        )
    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"\nPipeline failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
