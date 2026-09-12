# Rice Price Spike and Recovery Across Philippine Regions After Typhoons

## Problem Statement

How do rice prices across Philippine regions respond to typhoons between 2022 and 2025 — and how quickly do they return to normal?

## Audience

DEP Cohort builders, civic tech practitioners, and policymakers interested in food security and disaster resilience in the Philippines.

## KPIs / Key Metrics

**Primary**

- How much do rice prices rise when a typhoon hits a region?
- How long does it take for prices to go back to normal after a typhoon?

**Secondary**

- Which regions bounce back the fastest — and which struggle the most?
- Are regions getting more or less resilient to typhoons over time?

## Data Sources

- **PSA Price Situationer** — bi-monthly Excel files with region-level retail rice prices (well-milled), available at [psa.gov.ph](https://psa.gov.ph/statistics/price-situationer/selected-agri-commodities). Files must be manually downloaded due to Cloudflare restrictions on automated access.
- **IBTrACS (NOAA)** — historical typhoon track data for the Western Pacific basin, available at [ncei.noaa.gov](https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/). Downloaded automatically via the ingestion script.

## Ingestion

Run the ingestion script to download the IBTrACS typhoon dataset:

python scripts/ingest.py

This will download `IBTrACS.WP.v04r01.csv` into `./data/raw/`.

For PSA rice price data, manually download the bi-monthly Excel files for 2021–2025 from [psa.gov.ph](https://psa.gov.ph/statistics/price-situationer/selected-agri-commodities) and place them in `./data/raw/`.

## Possible Final Dashboard

An interactive dashboard hosted on GitHub Pages with two views — a heatmap showing all regions compared by percentage price spikes across typhoon events, and an annotated time series showing per-region price history with typhoon periods highlighted and recovery points marked.

## SQLite Staging Layer

After the processed CSVs have been generated, load them into SQLite:

```bash
python scripts/load_sqlite.py
```

This creates `data/processed/project.db` with these tables:

- `rice_prices`: one row per province, price phase, and observation date.
- `provincial_boundaries`: one row per province with region and representative coordinates.
- `typhoon_tracks`: one row per storm and forecast time, including wind-signal provinces.
- `load_metadata`: source CSV and row count for each loaded table.

The loader reads the processed CSVs with pandas' normal missing-value parsing.
Blank fields, `NaN`, `NaT`, and pandas missing scalars are inserted as SQL
`NULL`; valid values, including zero, are retained. It does not impute or
silently replace missing observations. The three data tables are dropped and
recreated inside one SQLite transaction on each run, making reruns idempotent
and ensuring stale rows are removed when the CSVs change. Primary keys and
`NOT NULL` constraints protect the grain and required fields while nullable
measurements remain available for later gold-layer decisions.

To write a database somewhere else:

```bash
python scripts/load_sqlite.py --database path/to/project.db
```
