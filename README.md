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
-

## Data Sources

- **PSA Price Situationer** — bi-monthly Excel files, retail rice prices (well-milled), province-level, psa.gov.ph. Manual download (Cloudflare-blocked).
- **IBTrACS (NOAA)** — historical typhoon track data for the Western Pacific basin, available at [ncei.noaa.gov](https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/). Downloaded automatically via the ingestion script.

## Ingestion

Run the ingestion script to download the IBTrACS typhoon dataset:

python scripts/ingest.py

This will download `IBTrACS.WP.v04r01.csv` into `./data/raw/`.

For PSA rice price data, manually download the bi-monthly Excel files for 2021–2025 from [psa.gov.ph](https://psa.gov.ph/statistics/price-situationer/selected-agri-commodities) and place them in `./data/raw/`.

## Possible Final Dashboard

GitHub Pages dashboard: scatter plot of severity vs. price spike with fitted regression line, points color-coded by residual, plus a map view highlighting provinces that are repeat outliers.
