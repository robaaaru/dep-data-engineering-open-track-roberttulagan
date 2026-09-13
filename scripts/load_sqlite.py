"""Load processed CSV datasets into a local SQLite database.

Run from the repository root:
    python scripts/load_sqlite.py

The loader is intentionally idempotent. It uses metadata stored inside the
database (file hashes and per-row content hashes) to detect changes. When a
CSV is modified, only the rows that actually changed are upserted and rows
no longer present in the CSV are deleted — without recreating tables.
"""

import argparse
import hashlib
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
		"primary_key": ["province", "phase", "period_start"],
		"schema": """
			CREATE TABLE IF NOT EXISTS rice_prices (
				province TEXT NOT NULL,
				phase TEXT NOT NULL CHECK (phase IN ('1st', '2nd')),
				period_start TEXT NOT NULL,
				well_milled_price REAL,
				regular_milled_price REAL,
				_row_hash TEXT NOT NULL,
				PRIMARY KEY (province, phase, period_start)
			)
		""",
	},
	"provincial_boundaries": {
		"csv": PROCESSED / "provincial_boundaries.csv",
		"columns": ["province", "region", "lat", "lon", "province_pcode"],
		"primary_key": ["province"],
		"schema": """
			CREATE TABLE IF NOT EXISTS provincial_boundaries (
				province TEXT PRIMARY KEY,
				region TEXT NOT NULL,
				lat REAL,
				lon REAL,
				province_pcode TEXT NOT NULL UNIQUE,
				_row_hash TEXT NOT NULL
			)
		""",
	},
	"typhoon_forecast": {
		"csv": PROCESSED / "typhoon_forecast.csv",
		"columns": [
			"sid", "season", "name", "forecast_time",
			"latitude", "longitude", "msw_kmh", "cat",
		],
		"primary_key": ["sid", "forecast_time"],
		"schema": """
			CREATE TABLE IF NOT EXISTS typhoon_forecast (
				sid TEXT NOT NULL,
				season INTEGER NOT NULL,
				name TEXT NOT NULL,
				forecast_time TEXT NOT NULL,
				latitude REAL NOT NULL,
				longitude REAL NOT NULL,
				msw_kmh REAL,
				cat TEXT,
				_row_hash TEXT NOT NULL,
				PRIMARY KEY (sid, forecast_time)
			)
		""",
	},
	"province_signals": {
		"csv": PROCESSED / "province_signals.csv",
		"columns": [
			"sid", "season", "name", "issued_time",
			"tcws_1", "tcws_2", "tcws_3", "tcws_4", "tcws_5",
		],
		"primary_key": ["sid", "issued_time"],
		"schema": """
			CREATE TABLE IF NOT EXISTS province_signals (
				sid TEXT NOT NULL,
				season INTEGER NOT NULL,
				name TEXT NOT NULL,
				issued_time TEXT NOT NULL,
				tcws_1 TEXT,
				tcws_2 TEXT,
				tcws_3 TEXT,
				tcws_4 TEXT,
				tcws_5 TEXT,
				_row_hash TEXT NOT NULL,
				PRIMARY KEY (sid, issued_time)
			)
		""",
	},
}


def file_hash(path):
	"""Create a fingerprint to track if the CSV has changed."""
	hasher = hashlib.sha256()
	with path.open("rb") as source:
		for chunk in iter(lambda: source.read(1024 * 1024), b""):
			hasher.update(chunk)
	return hasher.hexdigest()


def row_hash(values):
	"""Create a content hash for a single row to detect value-level changes."""
	encoded = "|".join("" if v is None else str(v) for v in values)
	return hashlib.sha256(encoded.encode("utf-8")).hexdigest()[:16]


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


def get_stored_hash(connection, table_name):
	"""Read the CSV file hash from the load_metadata table in the database."""
	cursor = connection.execute(
		"SELECT source_hash FROM load_metadata WHERE table_name = ?",
		(table_name,),
	)
	row = cursor.fetchone()
	return row[0] if row else None


def ensure_row_hash_column(connection, table_name):
	"""Add the _row_hash column to an existing table that lacks it."""
	cursor = connection.execute(f"PRAGMA table_info({table_name})")
	columns = {row[1] for row in cursor.fetchall()}
	if "_row_hash" in columns:
		return
	connection.execute(f"ALTER TABLE {table_name} ADD COLUMN _row_hash TEXT NOT NULL DEFAULT ''")


def upsert_changed_rows(connection, table_name, specification, dataset):
	"""Compare row hashes and only upsert rows that actually changed.

	Returns (upserted, deleted, unchanged) counts.
	"""
	columns = specification["columns"]
	pk_cols = specification["primary_key"]

	# Build a lookup of existing row hashes keyed by primary key
	pk_list = ", ".join(pk_cols)
	cursor = connection.execute(f"SELECT {pk_list}, _row_hash FROM {table_name}")
	existing_hashes = {}
	for row in cursor:
		pk_values = row[:-1]
		existing_hashes[pk_values] = row[-1]

	# Prepare rows from CSV with their hashes
	csv_pk_set = set()
	rows_to_upsert = []
	unchanged = 0

	for raw_row in dataset.itertuples(index=False, name=None):
		values = tuple(sqlite_value(v) for v in raw_row)
		pk_values = tuple(values[columns.index(k)] for k in pk_cols)
		content_hash = row_hash(values)
		csv_pk_set.add(pk_values)

		if existing_hashes.get(pk_values) == content_hash:
			unchanged += 1
			continue

		rows_to_upsert.append(values + (content_hash,))

	# Upsert only changed/new rows
	upserted = 0
	if rows_to_upsert:
		all_cols = columns + ["_row_hash"]
		col_list = ", ".join(all_cols)
		placeholders = ", ".join("?" for _ in all_cols)
		connection.executemany(
			f"INSERT OR REPLACE INTO {table_name} ({col_list}) VALUES ({placeholders})",
			rows_to_upsert,
		)
		upserted = len(rows_to_upsert)

	# Delete rows whose PK is no longer in the CSV
	deleted = 0
	pks_to_delete = [pk for pk in existing_hashes if pk not in csv_pk_set]
	if pks_to_delete:
		where = " AND ".join(f"{k} = ?" for k in pk_cols)
		connection.executemany(
			f"DELETE FROM {table_name} WHERE {where}",
			pks_to_delete,
		)
		deleted = len(pks_to_delete)

	return upserted, deleted, unchanged


def load_database(database_path):
	database_path.parent.mkdir(parents=True, exist_ok=True)
	counts = {}

	with sqlite3.connect(database_path) as connection:
		connection.execute("PRAGMA foreign_keys = ON")

		# Metadata table stores file hashes and row counts inside the database
		# — no external manifest files needed.
		connection.execute("""
			CREATE TABLE IF NOT EXISTS load_metadata (
				table_name TEXT PRIMARY KEY,
				source_csv TEXT NOT NULL,
				source_hash TEXT NOT NULL DEFAULT '',
				row_count INTEGER NOT NULL
			)
		""")

		# Ensure source_hash column exists (upgrade from older schema)
		cursor = connection.execute("PRAGMA table_info(load_metadata)")
		meta_columns = {row[1] for row in cursor.fetchall()}
		if "source_hash" not in meta_columns:
			connection.execute(
				"ALTER TABLE load_metadata ADD COLUMN source_hash TEXT NOT NULL DEFAULT ''"
			)

		for table_name, specification in TABLES.items():
			csv_path = specification["csv"]
			if not csv_path.exists():
				raise FileNotFoundError(f"Missing processed dataset: {csv_path}")

			current_hash = file_hash(csv_path)

			# Create the table if it doesn't exist
			connection.execute(specification["schema"])

			# Add _row_hash column if upgrading an older database
			ensure_row_hash_column(connection, table_name)

			# Check the hash stored *in the database* — not an external file
			stored_hash = get_stored_hash(connection, table_name)
			if stored_hash == current_hash:
				cursor = connection.execute(f"SELECT COUNT(*) FROM {table_name}")
				counts[table_name] = cursor.fetchone()[0]
				print(f"Skipping {table_name}; CSV is unmodified.")
				continue

			dataset = read_dataset(table_name, specification)
			upserted, deleted, unchanged = upsert_changed_rows(
				connection, table_name, specification, dataset,
			)

			cursor = connection.execute(f"SELECT COUNT(*) FROM {table_name}")
			counts[table_name] = cursor.fetchone()[0]

			# Store the new hash in the database metadata
			connection.execute(
				"INSERT OR REPLACE INTO load_metadata "
				"(table_name, source_csv, source_hash, row_count) VALUES (?, ?, ?, ?)",
				(table_name, str(csv_path.relative_to(ROOT)), current_hash, counts[table_name]),
			)

			print(
				f"Synced {table_name}: "
				f"{upserted} upserted, {deleted} deleted, {unchanged} unchanged."
			)

		connection.commit()

	return counts


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