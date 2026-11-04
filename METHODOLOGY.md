# Methodology

## 1. Purpose

> **Which Philippine regions experienced both heavy typhoon warnings (2024–2025) and unstable rice prices, and to what extent did those traits overlap?**

This is a descriptive screen. It describes warning exposure, regular-milled rice prices, and where the two traits overlap. It cannot establish that warnings changed prices, and warnings are not damage.

## 2. The data

The notebook finds the project root by walking upward until `data/processed/project.db` exists, then opens that SQLite database read-only. It reads only:

- `province_signals(sid, season, name, issued_time, tcws_1..tcws_5)`;
- `provincial_boundaries(province, region, lat, lon)`; and
- `rice_prices(province, phase, period_start, regular_milled_price)`.

The database contains a `typhoon_forecast` table, but it is **not used** in this analysis. No CSV is read. Rice rows represent a half-month period (1st or 2nd phase). Sulu and Batanes have no regular-milled readings and are excluded from volatility calculations.

## 3. Reshaping and exposure

The five signal columns are split on semicolons and reshaped to one row per province listed in a bulletin. For each `(sid, province)` pair, peak signal is the highest level reached in any bulletin for that storm. `n_severe` counts storms whose peak signal is at least 3. A never-warned province has `n_severe = 0`. Duration is not measured because provinces can drop in and out of bulletins.

## 4. Descriptive (EDA) charts

EDA is completed before overlap is counted. A storm is counted once, in the month of its first bulletin (the earliest `issued_time` for that `sid`). Storm type is based on the highest signal listed for any province: **never warned** means no province is listed in any bulletin; **Signal 1–2 only** means the highest listed signal is 1 or 2; **Signal 3+** means at least one province reached Signal 3 or higher. For example, a storm with several bulletins and a highest listed signal of 4 is counted once as Signal 3+ in the month of its earliest bulletin.

**First severe listing and repeat hit.** The first severe listing of a `(storm, province)` is the earliest bulletin issue time at which that province is listed at Signal 3 or higher. A repeat hit is a Signal 3+ storm whose first severe listing for a province is within 14 days of that province's previous first severe listing. Fourteen days is a chosen default. For example, first severe listings on June 1 and June 12 are one repeat hit; June 1 and June 16 are not. These are bulletin-time measures and do not measure damage, recovery time, or storm strength.

**Chart 1 — Typhoons.** The top part is a stacked monthly bar chart of the three storm types, with months with no storms shown as zero. The bottom part lists provinces with at least four Signal 3+ storms: the left panel shows `n_severe`, and the right panel puts one dot at each first severe listing on the same month axis. Filled dots are repeat hits and open dots are not repeat hits. Batanes remains in this warning chart even though it has no price data.

**Monthly national price.** Each monthly point is the median of all regular-milled readings from both phases in that month. The band is the 10th to 90th percentile of those same readings. For example, the January 2024 point combines every available first- and second-phase regular-milled reading in January.

**Price level by region.** This is the median of all regular-milled readings from the region's provinces over all months. It is a two-year level, not a measure of price spikes. Chart 2 shows the national price path and regional upside-spike levels. Charts 3 and 4 show regional and provincial overlap grids. Chart 5 is a standalone descriptive view of province-level upside swing. These are the five charts saved to `output/figures/`.

## 5. Price volatility

Prices are sorted by province, period, and phase. **Upside swing** is the root-mean-square of percentage rises between consecutive readings, with falls counted as zero. The main calculation uses all 48 readings in the price table. A robustness check applies the same formula to the 24 first-of-month readings. Measures of overall spread were not used because a steady decline inflates them; 75 of 81 provinces ended lower. Total change is printed only as a descriptive end-versus-start summary, and reporting rhythm is described by the share of months with identical first- and second-phase prices.

## 6. Rolling up to regions

Every region is summarized with the median of its province values. This includes zero exposure for never-warned provinces. Region sizes range from 1 to 7, so regional medians can hide province-level variation. Short labels are used for readable chart axes.

## 7. The 2×2 grid

High means **strictly above** the median across units; ties are low. The box definitions are:

| Exposure | Instability | Box |
|---|---|---|
| High | High | Most vulnerable (red circle) |
| High | Low | Exposed but stable (blue square) |
| Low | High | Unstable not storm-driven (orange triangle) |
| Low | Low | Low concern (light-blue diamond) |

Province grids draw the vertical line at 1.5. Deterministic sideways jitter is display-only, never crosses that line, and does not change calculations. Stars mark units that are also Most vulnerable under the one-reading-per-month check. Regions within 0.01 of the main price-spike median are listed as borderline; Caraga sits on the median line and counts as low.

## 8. How overlap is counted

At each level, a unit is Most vulnerable when it is above the median on both `n_severe` and upside swing. The scorecard prints province count, median `n_severe`, median upside swing, the box, and whether the unit is also Most vulnerable under one reading per month, with Most vulnerable regions first.

Regional shares are printed as `k/n`: the number of Most vulnerable provinces divided by the region's provinces with price data. For example, `3/6` means three of six price-covered provinces are in the box. The robustness summary compares the all-reading box assignment with the one-reading-per-month assignment; this is a descriptive check, not a test.

## 9. Chart guide

**Typhoons:** Chart 1 shows storm timing, storm type, frequent severe-warning provinces, and repeat-hit timing.  
**Prices:** Chart 2 shows the national price path and two-year regional price levels; Chart 5 shows province-level upside swing alone for descriptive purposes.  
**Overlap:** Charts 3 and 4 are single-panel grids using upside swing across all 48 readings. Stars show units that also pass the one-reading-per-month check. Labels are centered directly beneath their dots without leader lines. Every grid uses the same four box shapes.

## 10. Findings and decisions

The run checks 2,717 long warning rows, 63 provinces ever warned, 29 warned storms out of 41, 568 province-storm pairs, and peak counts of 260, 168, 75, 54, and 11 for Signals 1 through 5. Storms occur in 14 of 24 months. There are 28 repeat hits across 16 provinces; Rizal has 4, while Cagayan and Ilocos Sur have 3 each.

The national regular-milled price ends lower for 75 of 81 provinces. Upside swing has a median of about 1.98 across all 48 readings and about 2.11 under one reading per month. The regional Most vulnerable list is Bicol, CAR, and Cagayan Valley; CAR and Cagayan Valley also pass the monthly check. Twelve provinces are Most vulnerable in the all-reading version, and 10 are Most vulnerable under both versions.

| Decision | Choice |
|---|---|
| Price-spike measure | Upside swing across all 48 readings |
| Exposure axis | `n_severe` only |
| Overlap | Above-median exposure and upside swing |
| Robustness check | Same formula on 24 first-of-month readings |
| Monthly national price | Median of all regular-milled readings from both phases |
| Regional roll-up | Province median |
| Repeat hit | Within 14 days, based on bulletin issue times |
| Missing prices | Exclude Sulu and Batanes from volatility |
| Forecast table | `typhoon_forecast` not used |

## 11. Known limitations

The data cover two years, counts are small, and region sizes range from 1 to 7 provinces. Twenty provinces were never warned. Warnings are not damage. Sulu and Batanes have missing regular-milled prices. Provinces drop in and out of bulletins, so warning duration was not measured. The 14-day repeat-hit window is a chosen default. The analysis is descriptive and makes no causal claim.

## 12. Glossary

- **Signal:** Warning level from 1 to 5.
- **Peak:** Highest signal level for a province during one storm.
- **n_severe:** Number of storms with peak signal at least 3.
- **Upside swing:** Root-mean-square percentage rise, with falls counted as zero.
- **Overlap:** Above-median exposure and above-median upside swing.
- **Borderline:** Within 0.01 of an instability median.
- **Robustness check:** Comparison with the one-reading-per-month box assignment.
- **EDA:** Descriptive exploratory data analysis.
- **Repeat hit:** A Signal 3+ storm within 14 days of the same province's previous first severe listing.
