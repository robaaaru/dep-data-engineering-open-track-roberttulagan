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
PROCESSED = ROOT / "data" / "processed"
NOTEBOOK = ROOT / "notebooks" / "kpi_and_segmentation_analysis.ipynb"
REQUIRED_OUTPUTS = (
    PROCESSED / "rice_data.csv",
    PROCESSED / "provincial_boundaries.csv",
    PROCESSED / "typhoon_forecast.csv",
    PROCESSED / "province_signals.csv",
)


def run_step(label, command):
    """Run one pipeline step and stop with a useful error if it fails."""
    print(f"\n== {label} ==")
    subprocess.run(command, cwd=ROOT, check=True)


def main():
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

    if not args.skip_ingest:
        ingest_command = [sys.executable, "scripts/ingest.py"]
        if args.overwrite:
            ingest_command.append("--overwrite")
        run_step("Ingesting PAGASA bulletins", ingest_command)
    else:
        print("\n== Ingestion skipped; using local raw data ==")

    run_step("Transforming raw data", [sys.executable, "scripts/transform.py"])

    missing = [path for path in REQUIRED_OUTPUTS if not path.exists()]
    if missing:
        missing_names = ", ".join(str(path.relative_to(ROOT)) for path in missing)
        raise RuntimeError(
            "Transformation did not produce the required processed files: "
            f"{missing_names}"
        )

    run_step("Loading SQLite database", [sys.executable, "scripts/load_sqlite.py"])
    run_step(
        "Running analysis notebook",
        [
            sys.executable,
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
    print("\nPipeline completed successfully.")


if __name__ == "__main__":
    try:
        main()
    except (OSError, RuntimeError, subprocess.CalledProcessError) as error:
        print(f"\nPipeline failed: {error}", file=sys.stderr)
        raise SystemExit(1) from error
