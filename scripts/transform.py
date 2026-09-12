"""Transform all raw project data into the files used by the dashboard.

Run from the repository root or from this directory:
	python scripts/transform.py

Each output is written only once.  This makes the script safe to rerun after
new raw data is added without duplicating an existing processed dataset.
"""

import csv
import glob
import hashlib
import json
import os
import re
from pathlib import Path

import numpy as np
import pandas as pd
import pdfplumber


ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT / "data" / "raw"
PROCESSED = ROOT / "data" / "processed"
RICE_ROOT = RAW / "Rice Prices"
BOUNDARIES_SOURCE = RAW / "Provincial Boundaries" / "phl_admin_boundaries.xlsx"
ALLOWLIST = ROOT / "scripts" / "config" / "province_allowlist.csv"
TYPHOON_DIR = RAW / "Typhoon and Coordinates"

RICE_OUTPUT = PROCESSED / "rice_data.csv"
BOUNDARIES_OUTPUT = PROCESSED / "provincial_boundaries.csv"
TYPHOON_OUTPUT = PROCESSED / "typhoon_tracks.csv"
MANIFEST_DIR = PROCESSED / ".manifests"
RICE_MANIFEST = MANIFEST_DIR / "rice.json"
BOUNDARIES_MANIFEST = MANIFEST_DIR / "provincial_boundaries.json"
TYPHOON_MANIFEST = MANIFEST_DIR / "typhoon.json"


def file_hash(path):
	"""Create a fingerprint so changed source files are processed again."""
	hasher = hashlib.sha256()
	with path.open("rb") as source:
		for chunk in iter(lambda: source.read(1024 * 1024), b""):
			hasher.update(chunk)
	return hasher.hexdigest()


def load_manifest(path):
	if not path.exists():
		return {}
	return json.loads(path.read_text(encoding="utf-8"))


def save_manifest(path, values):
	MANIFEST_DIR.mkdir(parents=True, exist_ok=True)
	path.write_text(json.dumps(values, indent=2, sort_keys=True), encoding="utf-8")


# ---------------------------------------------------------------------------
# Rice prices: read the PSA spreadsheets and make one tidy table.
# ---------------------------------------------------------------------------

MONTHS = {
	"january": 1, "jan": 1, "february": 2, "feb": 2,
	"march": 3, "mar": 3, "april": 4, "apr": 4, "may": 5,
	"june": 6, "jun": 6, "july": 7, "jul": 7, "august": 8,
	"aug": 8, "september": 9, "sept": 9, "sep": 9,
	"october": 10, "oct": 10, "november": 11, "nov": 11,
	"december": 12, "dec": 12,
}


def get_year_month(filename):
	name = filename.lower()
	year_match = re.search(r"20\d{2}", name)
	if not year_match:
		raise ValueError(f"Could not find year in {filename}")
	month = next((number for month_name, number in MONTHS.items()
				  if month_name in name), None)
	if month is None:
		raise ValueError(f"Could not find month in {filename}")
	return int(year_match.group()), month


def normalize_province(value):
	if pd.isna(value):
		return ""
	value = str(value).upper().strip().replace("’", "'")
	value = re.sub(r"\bPROVINCE OF\b|\bPROVINCE\b", "", value)
	return re.sub(r"\s+", " ", re.sub(r"[^A-Z0-9]+", " ", value)).strip()


def find_price_header(df):
	for row_number in range(min(30, len(df))):
		row = df.iloc[row_number].astype(str).str.strip().str.upper()
		if row.eq("REGION / PROVINCE").any():
			return row_number
	raise ValueError("Could not find 'Region / Province' header.")


def validate_price_header(df, header_row, column, commodity, periods):
	commodity_row = header_row - 1
	period_row = header_row + 1
	low = max(0, column - 5)
	nearby = df.iloc[commodity_row, low:column + 1].fillna("").astype(str).str.upper()
	period = str(df.iloc[period_row, column] if pd.notna(df.iloc[period_row, column]) else "").upper()
	if not (any(commodity in text for text in nearby) and all(period_key in period for period_key in periods)):
		raise ValueError(
			f"Header validation failed at column {column}: expected {commodity} and {periods}; "
			f"found period '{period}' and nearby commodity values {nearby.tolist()}"
		)


def load_allowlist_names():
	return set(pd.read_csv(ALLOWLIST)["province"].dropna().astype(str).str.strip())


def process_price_file(filepath, province_allowlist):
	print(f"Processing rice prices: {filepath.name}")
	df = pd.read_excel(filepath, header=None, dtype=str, engine="openpyxl")
	header_row = find_price_header(df)
	validate_price_header(df, header_row, 12, "WELL MILLED", ["1ST PHASE", "CURRENT MONTH"])
	validate_price_header(df, header_row, 14, "WELL MILLED", ["2ND PHASE", "CURRENT MONTH"])
	validate_price_header(df, header_row, 19, "REGULAR MILLED", ["1ST PHASE", "CURRENT MONTH"])
	validate_price_header(df, header_row, 21, "REGULAR MILLED", ["2ND PHASE", "CURRENT MONTH"])

	year, month = get_year_month(filepath.name)
	records = []
	for _, row in df.iloc[header_row + 3:].iterrows():
		if len(row) < 22:
			continue
		first = "" if pd.isna(row.iloc[0]) else str(row.iloc[0]).strip()
		province = "" if pd.isna(row.iloc[1]) else str(row.iloc[1]).strip()
		if province.upper() in {"NCR", "NATIONAL CAPITAL REGION"} or first.upper() in {"NCR", "NATIONAL CAPITAL REGION"}:
			province = "NCR"
		if not province or normalize_province(province) == "PHILIPPINES" or province not in province_allowlist:
			continue
		records.append({
			"province": province,
			"period_start_1st": pd.Timestamp(year=year, month=month, day=1),
			"period_start_2nd": pd.Timestamp(year=year, month=month, day=16),
			"well_milled_price_1st": row.iloc[12],
			"well_milled_price_2nd": row.iloc[14],
			"regular_milled_price_1st": row.iloc[19],
			"regular_milled_price_2nd": row.iloc[21],
		})
	if not records:
		raise ValueError(f"No data extracted from {filepath.name}")

	result = pd.DataFrame(records)
	for column in ["well_milled_price_1st", "well_milled_price_2nd", "regular_milled_price_1st", "regular_milled_price_2nd"]:
		result[column] = pd.to_numeric(result[column], errors="coerce")
		result.loc[result[column] <= 0, column] = np.nan

	first = result[["province", "period_start_1st", "well_milled_price_1st", "regular_milled_price_1st"]].rename(columns={
		"period_start_1st": "period_start", "well_milled_price_1st": "well_milled_price", "regular_milled_price_1st": "regular_milled_price",
	})
	first["phase"] = "1st"
	second = result[["province", "period_start_2nd", "well_milled_price_2nd", "regular_milled_price_2nd"]].rename(columns={
		"period_start_2nd": "period_start", "well_milled_price_2nd": "well_milled_price", "regular_milled_price_2nd": "regular_milled_price",
	})
	second["phase"] = "2nd"
	return pd.concat([first, second], ignore_index=True)


def transform_rice_prices():
	rice_dirs = sorted(path for path in RICE_ROOT.iterdir() if path.is_dir())
	files = sorted(path for directory in rice_dirs for path in directory.glob("*.xlsx"))
	if not files:
		raise FileNotFoundError(f"No rice price XLSX files found in {RICE_ROOT}")
	allowlist = load_allowlist_names()
	manifest = load_manifest(RICE_MANIFEST)
	frames = []
	for filepath in files:
		key = str(filepath.relative_to(ROOT))
		fingerprint = file_hash(filepath)
		if manifest.get(key) == fingerprint:
			continue
		try:
			frames.append(process_price_file(filepath, allowlist))
			manifest[key] = fingerprint
		except Exception as error:
			print(f"SKIPPED {filepath.name}: {error}")
	if not frames:
		print(f"No new rice price files; {RICE_OUTPUT.name} is up to date.")
		return
	if RICE_OUTPUT.exists():
		frames.insert(0, pd.read_csv(RICE_OUTPUT))
	final = pd.concat(frames, ignore_index=True)
	final["period_start"] = pd.to_datetime(final["period_start"]).dt.strftime("%Y-%m-%d")
	final = final[["province", "phase", "period_start", "well_milled_price", "regular_milled_price"]]
	final.drop_duplicates(subset=["province", "period_start", "phase"], inplace=True)
	final.sort_values(["period_start", "phase", "province"], inplace=True)

	# Validation: these checks prove that every row is an allowed province,
	# has a valid date/phase key, and has no duplicate observation.
	if not set(final["province"]).issubset(allowlist):
		raise ValueError("Rice output contains a province outside the allowlist.")
	if final[["province", "phase", "period_start"]].duplicated().any():
		raise ValueError("Rice output contains duplicate province/date/phase rows.")
	if final.empty or final["period_start"].isna().any():
		raise ValueError("Rice output is empty or contains an invalid date.")
	PROCESSED.mkdir(parents=True, exist_ok=True)
	final.to_csv(RICE_OUTPUT, index=False, float_format="%.2f")
	save_manifest(RICE_MANIFEST, manifest)
	print(f"Created {RICE_OUTPUT} ({len(final):,} rows).")


# ---------------------------------------------------------------------------
# Provincial boundaries: use the allowlist as the definitive province list.
# ---------------------------------------------------------------------------

PCODE_NAME_OVERRIDE = {"PH13039": "NCR", "PH19087": "Maguindanao"}
DROP_PCODES = {"PH19099", "PH13074", "PH13075", "PH13076", "PH19088"}


def extract_alias(name):
	if pd.isna(name):
		return "", None
	match = re.match(r"^(.*?)\s*\((.*?)\)\s*$", str(name).strip())
	return (match.group(1).strip(), match.group(2).strip()) if match else (str(name).strip(), None)


def normalize_name(value):
	return "" if pd.isna(value) else re.sub(r"\s+", " ", str(value).strip().lower())


def match_to_allowlist(name, lookup):
	main, alias = extract_alias(name)
	for candidate in (main, alias):
		if candidate and normalize_name(candidate) in lookup:
			return lookup[normalize_name(candidate)]
	return None


def transform_boundaries():
	manifest = load_manifest(BOUNDARIES_MANIFEST)
	source_key = str(BOUNDARIES_SOURCE.relative_to(ROOT))
	source_fingerprint = file_hash(BOUNDARIES_SOURCE)
	if BOUNDARIES_OUTPUT.exists() and manifest.get(source_key) == source_fingerprint:
		print(f"Skipping provincial boundaries; {BOUNDARIES_OUTPUT.name} is up to date.")
		return
	allowlist_names = load_allowlist_names()
	lookup = {normalize_name(name): name for name in allowlist_names}
	phl = pd.read_excel(BOUNDARIES_SOURCE, sheet_name="phl_admin2")
	phl = phl[~phl["adm2_pcode"].isin(DROP_PCODES)].copy()
	phl["adm2_name"] = phl.apply(lambda row: PCODE_NAME_OVERRIDE.get(row["adm2_pcode"], row["adm2_name"]), axis=1)
	phl["province"] = phl["adm2_name"].apply(lambda name: match_to_allowlist(name, lookup))
	phl = phl[phl["province"].notna()].copy()
	missing_region = phl[phl["adm1_name"].isna()]
	if not missing_region.empty:
		raise ValueError(f"Matched provinces without a region: {missing_region[['province', 'adm2_pcode']].to_dict('records')}")
	phl["region"] = phl["adm1_name"].astype(str).str.strip()
	result = phl[["province", "region", "center_lat", "center_lon", "adm2_pcode"]].rename(columns={
		"center_lat": "lat", "center_lon": "lon", "adm2_pcode": "province_pcode",
	})

	# Validation: compare the output with the allowlist like checking a guest
	# list. Every allowed province must appear once, and no extra province may enter.
	missing = allowlist_names - set(result["province"])
	extra = set(result["province"]) - allowlist_names
	duplicates = result[result["province"].duplicated(keep=False)]
	if missing or extra or not duplicates.empty:
		raise ValueError(f"Boundary validation failed: missing={sorted(missing)}, extra={sorted(extra)}, duplicates={duplicates.to_dict('records')}")
	result = result.sort_values(["region", "province"]).reset_index(drop=True)
	PROCESSED.mkdir(parents=True, exist_ok=True)
	result.to_csv(BOUNDARIES_OUTPUT, index=False)
	save_manifest(BOUNDARIES_MANIFEST, {source_key: source_fingerprint})
	print(f"Created {BOUNDARIES_OUTPUT} ({len(result):,} rows).")


# ---------------------------------------------------------------------------
# PAGASA tracks: parse every matching storm folder into one CSV.
# ---------------------------------------------------------------------------

LATLON_RE = re.compile(r'\((\d+\.\d+)\s*°?N,\s*(\d+\.\d+)\s*°?E\)')
DATE_RE = re.compile(r'(\d{1,2})\s+(January|February|March|April|May|June|July|August|September|October|November|December)\s+(\d{4})', re.IGNORECASE)
TIME_RE = re.compile(r'(\d{1,2}):(\d{2})\s*([AP]M)', re.IGNORECASE)
FORECAST_RE = re.compile(r'(\d{1,3})-Hour Forecast', re.IGNORECASE)
FORECAST_LATLON_RE = re.compile(r'\b(\d{1,3}\.\d)\s+(\d{1,3}\.\d)\b')
FORECAST_MSW_CAT_RE = re.compile(r'\b(\d{1,3}|-)\s+(TD|TS|STS|TY|STY|LOW|-)\b', re.IGNORECASE)
ISSUED_RE = re.compile(r'Issued at ([\d:]+\s*[AP]M),\s*(\d{1,2}\s+\w+\s+\d{4})')
TCWS_SECTION_RE = re.compile(r'TROPICAL CYCLONE WIND SIGNALS.*?(?=HAZARDS AFFECTING|OTHER HAZARDS|$)', re.IGNORECASE | re.DOTALL)
TCWS_ROW_RE = re.compile(r'^\s*([1-5])\s+(?=\S)', re.MULTILINE)
TCWS_ROW_END_RE = re.compile(r'\n\s*Wind threat:', re.IGNORECASE)
FILENAME_RE = re.compile(r'PAGASA_(\d{2})-TC(\d{2})_([A-Za-z]+)_(TCB|SWB|TCA)[#_](\d+[A-Za-z]?)(?:-FINAL)?\.pdf', re.IGNORECASE)
FOLDER_RE = re.compile(r'^pagasa-(\d{2})-tc-?(\d{2})$', re.IGNORECASE)
NCR_PLACE_NAMES = {"caloocan", "las pinas", "makati", "malabon", "mandaluyong", "manila", "marikina", "muntinlupa", "navotas", "paranaque", "pasay", "pasig", "pateros", "quezon city", "san juan", "taguig", "valenzuela", "metro manila", "national capital region", "ncr"}


def sql_time(day, month, year, hour, minute, ampm):
	hour = int(hour)
	if ampm.upper() == "PM" and hour != 12:
		hour += 12
	elif ampm.upper() == "AM" and hour == 12:
		hour = 0
	month_number = MONTHS[month.lower()]
	return f"{int(year):04d}-{month_number:02d}-{int(day):02d} {hour:02d}:{int(minute):02d}:00"


def normalize_place_text(text):
	return re.sub(r"\s+", " ", re.sub(r"[^\w\s]", " ", text, flags=re.UNICODE)).strip().casefold()


def contains_place(text, name):
	return re.search(rf"(?<!\w){re.escape(normalize_place_text(name))}(?!\w)", text) is not None


def parse_tcws_places(text, province_allowlist):
	places = {number: "" for number in range(1, 6)}
	section_match = TCWS_SECTION_RE.search(text)
	if not section_match:
		return places
	section = section_match.group(0)
	rows = list(TCWS_ROW_RE.finditer(section))
	for index, row_match in enumerate(rows):
		end = rows[index + 1].start() if index + 1 < len(rows) else len(section)
		row_text = section[row_match.end():end]
		wind_threat = TCWS_ROW_END_RE.search(row_text)
		if wind_threat:
			row_text = row_text[:wind_threat.start()]
		flat = " ".join(row_text.split())
		normalized = normalize_place_text(flat)
		ncr_matches = [name for name in NCR_PLACE_NAMES if contains_place(normalized, name)]
		matches = [name for name in province_allowlist if name.casefold() != "ncr" and contains_place(normalized, name) and not any(normalize_place_text(name) in normalize_place_text(ncr_name) for ncr_name in ncr_matches)]
		if ncr_matches:
			matches.insert(0, "NCR")
		places[int(row_match.group(1))] = "; ".join(matches)
	highest = {}
	for number in range(1, 6):
		for name in filter(None, places[number].split("; ")):
			highest[name] = number
	for number in range(1, 6):
		places[number] = "; ".join(name for name in places[number].split("; ") if name and highest[name] == number)
	return places


def parse_forecast_rows(text, storm_name, issued_time, province_allowlist):
	start = re.search(r"TRACK AND INTENSITY FORECAST", text, re.IGNORECASE)
	if not start:
		return []
	section = text[start.end():]
	ends = [m.start() for marker in ("TROPICAL CYCLONE WIND SIGNALS", "HAZARDS AFFECTING", "OTHER HAZARDS") if (m := re.search(marker, section, re.IGNORECASE))]
	if ends:
		section = section[:min(ends)]
	headers = list(FORECAST_RE.finditer(section))
	rows = []
	places = parse_tcws_places(text, province_allowlist)
	for index, header in enumerate(headers):
		end = headers[index + 1].start() if index + 1 < len(headers) else len(section)
		flat = " ".join(section[header.end():end].split())
		time_match, date_match, position_match = TIME_RE.search(flat), DATE_RE.search(flat), FORECAST_LATLON_RE.search(flat)
		if not (time_match and date_match and position_match):
			continue
		hour, minute, ampm = time_match.groups()
		day, month, year = date_match.groups()
		intensity = FORECAST_MSW_CAT_RE.search(flat)
		msw = None if not intensity or intensity.group(1) == "-" else int(intensity.group(1))
		category = "" if not intensity or intensity.group(2) == "-" else intensity.group(2).upper()
		row = {"sid": None, "season": None, "name": storm_name.upper(), "issued_time": issued_time, "forecast_time": sql_time(day, month, year, hour, minute, ampm), "latitude": float(position_match.group(1)), "longitude": float(position_match.group(2)), "msw_kmh": msw, "cat": category}
		row.update({f"tcws_{number}": places[number] for number in range(1, 6)})
		rows.append(row)
	return rows


def parse_bulletin(pdf_path, province_allowlist):
	filename = os.path.basename(pdf_path)
	match = FILENAME_RE.search(filename)
	if not match or match.group(4).upper() != "TCB":
		return []
	season_code, storm_number, storm_name, _, _ = match.groups()
	with pdfplumber.open(pdf_path) as pdf:
		text = "\n".join(page.extract_text(layout=True) or "" for page in pdf.pages)
	issued_time = None
	issued = ISSUED_RE.search(text)
	if issued:
		issue_clock = TIME_RE.fullmatch(issued.group(1).replace(" ", ""))
		issue_date = DATE_RE.fullmatch(issued.group(2))
		if issue_clock and issue_date:
			hour, minute, ampm = issue_clock.groups()
			day, month, year = issue_date.groups()
			issued_time = sql_time(day, month, year, hour, minute, ampm)
	rows = parse_forecast_rows(text, storm_name, issued_time, province_allowlist)
	for row in rows:
		row["sid"] = f"{season_code}-TC{storm_number}"
		row["season"] = 2000 + int(season_code)
	return rows


def select_pdfs(pdfs):
	groups = {}
	unmatched = []
	for path in pdfs:
		filename = os.path.basename(path)
		match = FILENAME_RE.search(filename)
		if not match:
			unmatched.append(path)
			continue
		groups.setdefault(match.groups(), []).append((path, filename.upper().replace(".PDF", "").endswith("-FINAL")))
	selected = list(unmatched)
	for entries in groups.values():
		finals = [path for path, is_final in entries if is_final]
		selected.append(finals[0] if finals else entries[0][0])
	return sorted(selected)


def build_track(folder, province_allowlist, pdfs=None):
	pdfs = select_pdfs(sorted(glob.glob(f"{folder}/*.pdf"))) if pdfs is None else pdfs
	if not pdfs:
		raise FileNotFoundError(f"No PDFs found in {folder}")
	rows = []
	for pdf in pdfs:
		print(f"Processing PAGASA bulletin: {os.path.basename(pdf)}")
		rows.extend(parse_bulletin(pdf, province_allowlist))
	if not rows:
		raise ValueError(f"No bulletins could be parsed from {folder}")
	result = pd.DataFrame(rows)
	result["issued_time"] = pd.to_datetime(result["issued_time"])
	return result.sort_values(["sid", "forecast_time", "issued_time"]).drop_duplicates(["sid", "forecast_time"], keep="last").sort_values("forecast_time").reset_index(drop=True)


def transform_typhoon_tracks():
	folders = [str(TYPHOON_DIR / name) for name in sorted(os.listdir(TYPHOON_DIR)) if (TYPHOON_DIR / name).is_dir() and FOLDER_RE.match(name)]
	if not folders:
		raise FileNotFoundError(f"No PAGASA storm folders found under {TYPHOON_DIR}")
	allowlist = sorted(load_allowlist_names(), key=lambda name: (-len(name), name.casefold()))
	manifest = load_manifest(TYPHOON_MANIFEST)
	tracks = []
	for folder in folders:
		try:
			selected = select_pdfs(sorted(glob.glob(f"{folder}/*.pdf")))
			changed = []
			for pdf in selected:
				key = str(Path(pdf).resolve().relative_to(ROOT))
				fingerprint = file_hash(Path(pdf))
				if manifest.get(key) != fingerprint:
					changed.append(pdf)
					manifest[key] = fingerprint
			if changed:
				tracks.append(build_track(folder, allowlist, changed))
		except (FileNotFoundError, ValueError) as error:
			print(f"SKIPPED {os.path.basename(folder)}: {error}")
	if not tracks:
		print(f"No new PAGASA bulletins; {TYPHOON_OUTPUT.name} is up to date.")
		return
	if TYPHOON_OUTPUT.exists():
		tracks.insert(0, pd.read_csv(TYPHOON_OUTPUT))
	final = pd.concat(tracks, ignore_index=True)
	final["issued_time"] = pd.to_datetime(final["issued_time"])
	final["forecast_time"] = pd.to_datetime(final["forecast_time"])
	final = final.sort_values(["sid", "forecast_time", "issued_time"]).drop_duplicates(["sid", "forecast_time"], keep="last").sort_values(["sid", "forecast_time"]).reset_index(drop=True)

	# Validation: make sure the parser produced usable coordinates and one
	# record per storm/forecast time, rather than silently writing bad tracks.
	if final.empty or final[["sid", "forecast_time"]].duplicated().any():
		raise ValueError("PAGASA output is empty or contains duplicate track times.")
	if not final["latitude"].between(-90, 90).all() or not final["longitude"].between(-180, 180).all():
		raise ValueError("PAGASA output contains invalid coordinates.")
	PROCESSED.mkdir(parents=True, exist_ok=True)
	final.to_csv(TYPHOON_OUTPUT, index=False)
	save_manifest(TYPHOON_MANIFEST, manifest)
	print(f"Created {TYPHOON_OUTPUT} ({len(final):,} rows).")


def main():
	"""Run each independent transformation; an existing output is skipped."""
	for transform in (transform_rice_prices, transform_boundaries, transform_typhoon_tracks):
		try:
			transform()
		except Exception as error:
			print(f"FAILED {transform.__name__}: {error}")


if __name__ == "__main__":
	main()
