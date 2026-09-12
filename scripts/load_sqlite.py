"""Load processed CSV datasets into a local SQLite database.

Run from the repository root:
    python scripts/load_sqlite.py

The loader is intentionally idempotent. It replaces the three staging tables
from the current processed CSVs in one transaction, so the database cannot be
left half-loaded if a validation or insert fails.
"""

import argparse
import math
import sqlite3
from datetime import date, datetime
from pathlib import Path

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
PROCESSED = ROOT / "data" / "processed"
DEFAULT_DATABASE = PROCESSED / "project.db"


TABLES = {
	"rice_prices": {
		"csv": PROCESSED / "rice_data.csv",
		"columns": [
			"province", "phase", "period_start", "well_milled_price",
			"regular_milled_price",
		],
		"schema": """
			CREATE TABLE rice_prices (
				province TEXT NOT NULL,
				phase TEXT NOT NULL CHECK (phase IN ('1st', '2nd')),
				period_start TEXT NOT NULL,
				well_milled_price REAL,
				regular_milled_price REAL,
				PRIMARY KEY (province, phase, period_start)
			)
		""",
	},
	"provincial_boundaries": {
		"csv": PROCESSED / "provincial_boundaries.csv",
		"columns": ["province", "region", "lat", "lon", "province_pcode"],
		"schema": """
			CREATE TABLE provincial_boundaries (
				province TEXT PRIMARY KEY,
				region TEXT NOT NULL,
				lat REAL,
				lon REAL,
				province_pcode TEXT NOT NULL UNIQUE
			)
		""",
	},
	"typhoon_tracks": {
		"csv": PROCESSED / "typhoon_tracks.csv",
		"columns": [
			"sid", "season", "name", "issued_time", "forecast_time",
			"latitude", "longitude", "msw_kmh", "cat", "tcws_1", "tcws_2",
			"tcws_3", "tcws_4", "tcws_5",
		],
		"schema": """
			CREATE TABLE typhoon_tracks (
				sid TEXT NOT NULL,
				season INTEGER NOT NULL,
				name TEXT NOT NULL,
				issued_time TEXT,
				forecast_time TEXT NOT NULL,
				latitude REAL NOT NULL,
				longitude REAL NOT NULL,
				msw_kmh REAL,
				cat TEXT,
				tcws_1 TEXT,
				tcws_2 TEXT,
				tcws_3 TEXT,
				tcws_4 TEXT,
				tcws_5 TEXT,
				PRIMARY KEY (sid, forecast_time)
			)
		""",
	},
}


def sqlite_value(value):
	"""Convert pandas missing values to SQL NULL without changing valid values."""
	if value is None or value is pd.NA or value is pd.NaT:
		return None
	if isinstance(value, float) and math.isnan(value):
		return None
	if isinstance(value, (pd.Timestamp, datetime, date)):
		return value.isoformat(sep=" ") if isinstance(value, (pd.Timestamp, datetime)) else value.isoformat()
	if hasattr(value, "item"):
		return value.item()
	return value


def read_dataset(table_name, specification):
	filepath = specification["csv"]
	if not filepath.exists():
		raise FileNotFoundError(f"Missing processed dataset: {filepath}")
	frame = pd.read_csv(filepath, keep_default_na=True)
	missing_columns = set(specification["columns"]) - set(frame.columns)
	if missing_columns:
		raise ValueError(f"{table_name} is missing columns: {sorted(missing_columns)}")
	return frame[specification["columns"]]


def load_database(database_path):
	datasets = {name: read_dataset(name, specification) for name, specification in TABLES.items()}
	database_path.parent.mkdir(parents=True, exist_ok=True)
	with sqlite3.connect(database_path) as connection:
		connection.execute("PRAGMA foreign_keys = ON")
		for table_name, specification in TABLES.items():
			connection.execute(f"DROP TABLE IF EXISTS {table_name}")
			connection.execute(specification["schema"])
			columns = specification["columns"]
			placeholders = ", ".join("?" for _ in columns)
			column_list = ", ".join(columns)
			rows = (
				tuple(sqlite_value(value) for value in row)
				for row in datasets[table_name].itertuples(index=False, name=None)
			)
			connection.executemany(
				f"INSERT INTO {table_name} ({column_list}) VALUES ({placeholders})",
				rows,
			)
		connection.execute("DROP TABLE IF EXISTS load_metadata")
		connection.execute("""
			CREATE TABLE load_metadata (
				table_name TEXT PRIMARY KEY,
				source_csv TEXT NOT NULL,
				row_count INTEGER NOT NULL
			)
		""")
		connection.executemany(
			"INSERT INTO load_metadata VALUES (?, ?, ?)",
			[
				(table_name, str(specification["csv"].relative_to(ROOT)), len(datasets[table_name]))
				for table_name, specification in TABLES.items()
			],
		)
		connection.commit()

	return {name: len(frame) for name, frame in datasets.items()}


def main():
	parser = argparse.ArgumentParser(description=__doc__)
	parser.add_argument(
		"--database",
		type=Path,
		default=DEFAULT_DATABASE,
		help=f"SQLite output path (default: {DEFAULT_DATABASE})",
	)
	args = parser.parse_args()
	counts = load_database(args.database.resolve())
	print(f"Loaded {args.database.resolve()}")
	for table_name, count in counts.items():
		print(f"  {table_name}: {count:,} rows")


if __name__ == "__main__":
	main()