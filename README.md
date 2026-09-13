# Rice Price Spikes vs. Typhoon Severity: A Province-Level Deviation Analysis

## Problem Statement

Among Philippine provinces directly hit by a typhoon (2024–2025), which provinces exhibit rice price spikes larger than typhoon severity alone would predict?

## Audience

DEP Cohort builders, civic tech practitioners, and policymakers interested in food security and disaster resilience in the Philippines.

## KPIs / Key Metrics

**Primary**

- Regression of rice price spike (%) on typhoon severity (wind speed, distance-to-track at closest approach), across typhoon-hit provinces.
- Residuals: provinces spiking higher than predicted (flagged for investigation) vs. lower (well-supported).

**Secondary**

- Which provinces are repeat outliers across multiple 2024–2025 typhoon events?
- Is the spread of residuals narrowing or widening across the two years?

## Data Sources

- **PSA Price Situationer** — bi-monthly Excel files, retail rice prices (well-milled and regular-milled), province-level, [psa.gov.ph](https://psa.gov.ph/statistics/price-situationer/selected-agri-commodities). Site is Cloudflare-blocked, so files are downloaded manually and dropped into `data/raw/Rice Prices/<year>/`.
- **PAGASA Bulletin Archive** — tropical cyclone bulletins (track forecasts + wind signal warnings) for the 2024–2025 seasons, mirrored as PDFs on GitHub (`pagasa-parser/bulletin-archive`). Downloaded automatically via `ingest.py`.
- **PSA Provincial Boundaries** — admin boundary reference file (`phl_admin_boundaries.xlsx`), used to attach region and lat/lon to each province, and to validate that every province we track has a matching boundary record.
- **Province allowlist** (`scripts/config/province_allowlist.csv`) — the canonical list of provinces this project tracks. Every transform checks its output against this list rather than trusting whatever names show up in the raw source files (province names in PSA/PAGASA data aren't always spelled consistently).

## Project structure

```
scripts/
  ingest.py                    # pulls raw PAGASA bulletin PDFs from GitHub
  transform.py                 # parses raw sources into tidy CSVs
  load_sqlite.py                # loads processed CSVs into SQLite
  config/province_allowlist.csv # canonical province names
data/
  raw/
    Rice Prices/<year>/         # PSA Excel files, dropped in manually
    Typhoon and Coordinates/    # PAGASA bulletin PDFs, downloaded by ingest.py
    Provincial Boundaries/      # admin boundaries xlsx
  processed/
    rice_data.csv
    provincial_boundaries.csv
    typhoon_forecast.csv
    province_signals.csv
    project.db
    .manifests/                 # tracks which source files were already processed
```

## Requirements

```
pip install -r requirements.txt
```

Python 3.10+. No API keys needed — `ingest.py` hits GitHub's public API, which is rate-limited to 60 unauthenticated requests/hour; the whole download only needs one Trees API call plus one request per file, so this is rarely an issue.

## How to run

**1. Ingest** — download raw PAGASA bulletins:

```
python scripts/ingest.py
```

Files land in `data/raw/Typhoon and Coordinates/`, one subfolder per storm. Already-downloaded files are skipped by default, so re-running is cheap; pass `--overwrite` to force a fresh download of everything. Use `-o <path>` to change the output folder.

For rice prices, there's no script — manually download the bi-monthly PSA Excel files for the months you need and place them in `data/raw/Rice Prices/<year>/`. The transform step picks up whatever's in that folder.

**2. Transform** — parse everything into tidy CSVs:

```
python scripts/transform.py
```

This runs three independent transforms; if one fails, the others still complete (check the console output for `FAILED <name>: <error>`):

- **Rice prices** → `rice_data.csv`. One row per `(province, phase, period_start)`. Reshapes the wide PSA sheet (1st/2nd phase side-by-side) into long format, keeps only allowlisted provinces, and treats zero/negative prices as missing data rather than real values.
- **Provincial boundaries** → `provincial_boundaries.csv`. One row per province, matched against the allowlist by name (handling name aliases like `"Main Name (Alt Name)"`).
- **Typhoon tracks** → two files:
  - `typhoon_forecast.csv` — one row per `(sid, forecast_time)`: storm position, wind speed, category at each forecast horizon.
  - `province_signals.csv` — one row per `(sid, issued_time)`: which provinces were under wind signals 1–5 at that advisory.

Only new or changed source files get reprocessed on re-run — a hash of each source file is kept in `data/processed/.manifests/`. Every transform validates its own output before writing (no duplicate keys, no out-of-range coordinates, no province outside the allowlist) and will raise an error rather than write bad data.

**3. Load** — build the queryable SQLite database:

```
python scripts/load_sqlite.py
```

Writes `data/processed/project.db` with four tables (`rice_prices`, `provincial_boundaries`, `typhoon_forecast`, `province_signals`), matching the four processed CSVs. Uses file- and row-level hashing to only insert/update/delete rows that actually changed since the last run — safe to run after every `transform.py` run, even if nothing changed.

## Output schema (quick reference)

| Table                   | Key                           | Notable columns                                     |
| ----------------------- | ----------------------------- | --------------------------------------------------- |
| `rice_prices`           | province, phase, period_start | well_milled_price, regular_milled_price             |
| `provincial_boundaries` | province                      | region, lat, lon, province_pcode                    |
| `typhoon_forecast`      | sid, forecast_time            | latitude, longitude, msw_kmh, cat                   |
| `province_signals`      | sid, issued_time              | tcws_1..tcws_5 (semicolon-separated province lists) |

`sid` is the storm ID (e.g. `24-TC01`); `season` is the year.

## Validation notes

Each transform checks its own output before writing anything to disk — bad data raises an error instead of getting silently written.

- **Rice prices**: header structure is checked (expected commodity/phase labels found at the expected columns) before any row is trusted; output must have no `(province, phase, period_start)` duplicates, every province must be in the allowlist, and no missing dates.
- **Provincial boundaries**: every allowlisted province must appear exactly once (no missing, no extra, no duplicates); every matched province must have a non-null region.
- **Typhoon forecast**: no duplicate `(sid, forecast_time)`; latitude/longitude must fall within valid physical ranges (−90 to 90 / −180 to 180) — catches PDF-parsing errors that would otherwise produce garbage coordinates.
- **Province signals**: no duplicate `(sid, issued_time)`.
- **SQLite load**: enforced at the schema level — `NOT NULL` on identifying columns, `CHECK (phase IN ('1st','2nd'))` on `rice_prices`, `UNIQUE` on `province_pcode`. A row that violates these stops the load rather than getting dropped quietly.

## Logic notes

- **Incremental processing (ingest + transform)**: a hash of each source file is stored in a manifest (`data/processed/.manifests/`). Re-running only reprocesses files that are new or changed — unchanged files are skipped.
- **Incremental loading (SQLite)**: two-level hashing — a whole-file hash decides whether a table needs touching at all, then a per-row hash decides which individual rows to upsert or delete. Keeps re-runs cheap and idempotent (same input → same end state, no duplicate rows).
- **Signal-per-advisory, not per-forecast-row**: a bulletin's wind signals (`tcws_1..5`) describe the whole advisory, not any single forecast horizon, so they're split into their own table (`province_signals.csv`) keyed by `issued_time` instead of staying duplicated across every `forecast_time` row.
- **Highest-signal-wins dedup**: if a province is listed under more than one signal number within the same bulletin, only the highest signal is kept for that province — a place isn't allowed to sit under two signal levels in one advisory.
- **Allowlist-driven matching**: rice, boundaries, and typhoon signal parsing all resolve province names against the same allowlist, using word-boundary matching (so "Leyte" doesn't false-match inside "Southern Leyte") and alias handling (`"Main Name (Alt Name)"`) — one canonical list, checked in three unrelated places.
- **Distance-to-track at closest approach** (used as a severity input in the KPI section) isn't computed by the current pipeline yet — `(TODO)`, would need to be derived from `typhoon_forecast.csv` positions against each province's centroid in `provincial_boundaries.csv`.

## Possible Final Dashboard

GitHub Pages dashboard: scatter plot of severity vs. price spike with fitted regression line, points color-coded by residual, plus a map view highlighting provinces that are repeat outliers.
