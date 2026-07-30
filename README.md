# Rice Price Spike and Recovery Across Philippine Regions After Typhoons

## Problem Statement
How do rice prices across Philippine regions respond to typhoons between 2021 and 2025 — and how quickly do they return to normal?

## Audience
DEP Cohort builders, civic tech practitioners, and policymakers interested in food security and disaster resilience in the Philippines.

## KPIs / Key Metrics

**Primary**
- How much do rice prices rise when a typhoon hits a region?
- How long does it take for prices to go back to normal after a typhoon?

**Secondary**
- Which regions bounce back the fastest — and which struggle the most?
- Are regions getting more or less resilient to typhoons over time?

## Likely Data Sources
- **PSA Price Situationer** — bi-monthly Excel files with region-level retail rice prices (well-milled), available at [psa.gov.ph](https://psa.gov.ph/statistics/price-situationer/selected-agri-commodities)
- **IBTrACS (NOAA)** — historical typhoon track data for the Western Pacific basin, available at [ncei.noaa.gov](https://www.ncei.noaa.gov/data/international-best-track-archive-for-climate-stewardship-ibtracs/v04r01/access/csv/)

## Ingestion
- The raw data for IBTrACS can be ingested through NOAA's API while the PSA excel files can be downloaded manually at psa.gov.ph

## Possible Final Dashboard
An interactive dashboard hosted on GitHub Pages with two views — a heatmap showing all regions compared by percentage price spikes across typhoon events, and an annotated time series showing per-region price history with typhoon periods highlighted and recovery points marked.
