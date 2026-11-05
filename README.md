# Rice Price Spikes vs. Typhoon Warnings: A Province-Level Overlap Analysis

## Problem Statement

Which Philippine regions experienced both heavy typhoon warnings (2024–2025) and unstable rice prices, and to what extent did those traits overlap?

## Audience

DEP Cohort builders, civic tech practitioners, and policymakers interested in food security and disaster resilience in the Philippines.

## KPIs / Key Metrics

**Primary**

- Exposure: `n_severe`, the number of storms for which a province reached Signal 3 or higher.
- Price spikes: upside swing, with falls counted as zero.
- Regional grid: strict above-median exposure and instability boxes.
- **Overlap:** above the median on both traits.

**Secondary**

- Which regions and provinces are Most vulnerable under the all-reading and one-reading-per-month versions.
- The share of each region's provinces in that box.
- The number of regions and provinces that keep the same box in the one-reading-per-month robustness check.

**Research question**

Which Philippine regions experienced both heavy typhoon warnings (2024–2025) and unstable rice prices, and to what extent did those traits overlap?

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

**4. Analysis notebook** — open `notebooks/exposure_vs_volatility.ipynb`. It has three analytical parts plus a standalone price-ranking view, with five charts saved to `output/figures/` and a written interpretation under every chart. The notebook reads only the SQLite database read-only. The only price measure is upside swing across 48 readings; a one-reading-per-month version is used only as a printed robustness check and for stars on Charts 3 and 4. Charts 3 and 4 are single-panel grids with labels centered beneath their dots and no leader lines. Chart 4 uses deterministic display-only sideways jitter for province dots, keeps the province reference line at 1.5, and places legends below the plot. Chart 5 is explicitly documented as a province-level upside-swing ranking.

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

- **Incremental processing (ingest + transform):** a hash of each source file is stored in a manifest (`data/processed/.manifests/`).
- **Incremental loading (SQLite):** file- and row-level hashes make re-runs idempotent.
- **EDA first:** warnings and prices are described separately before overlap. **Meaning:** the notebook first explains each dataset on its own before combining them.
- **`n_severe`:** the number of storms in which a province reached Wind Signal 3 or higher. **Meaning:** how many storms brought that province a relatively high warning level.
- **Repeat hit:** a Signal 3+ warning within 14 days of the same province’s previous one (a chosen default, based on bulletin times). **Meaning:** the province was listed for high warning levels again soon after an earlier high-warning listing; this does not measure damage or recovery.
- **Upside swing:** percentage rises between consecutive readings, with falls set to zero, summarized as a root-mean-square rise. The main version uses all 48 readings; the robustness check uses the 24 first-of-month readings. **Meaning:** how sharply rice prices tended to rise; falling prices do not add to the price-spike score.
- **Median:** the middle value after all provinces or regions are ordered from lowest to highest. **Meaning:** a typical value; half of the units are below it and half are above it.
- **Interquartile range (IQR):** the range containing the middle 50% of observations. **Meaning:** where the central group of provinces sits, without letting the highest or lowest values dominate the description.
- **Right-skewed:** a distribution with many lower values and a smaller number of higher values. **Meaning:** most provinces had lower exposure or price rises, while a few had much higher values.
- **Outlier:** a value unusually far from the rest of the data. **Meaning:** a result worth checking, but not automatically a mistake.
- **Overlap:** above-median exposure and upside swing, counted at region level, province level, and as a share of price-covered provinces per region; no statistical tests are used. **Meaning:** a province or region has relatively high values for both measures in this dataset, not that typhoons caused price increases.
- **Most vulnerable:** the screening label for units above both medians. **Meaning:** a place to consider for closer monitoring, not a claim that it experienced the most physical damage or that its prices were caused by storms.
- **Robustness check:** comparison of the all-reading result with a calculation using one price reading per month. **Meaning:** a test of whether the broad result stays similar when the price data are sampled differently.
- **Descriptive analysis:** an analysis that summarizes patterns without proving cause and effect. **Meaning:** the notebook shows what happened together in the data, but cannot prove why it happened.
- **Chart readability:** province-point jitter, labels placed beneath dots, stars, and legend placement are display-only; they do not alter any numbers, classifications, or definitions.

## Findings and limits (summary)

The warning data contain 2,717 long rows, 63 provinces ever warned, 29 warned storms out of 41, and 568 province-storm pairs. Peak counts for Signals 1–5 are 260, 168, 75, 54, and 11. Storms occurred in 14 of 24 months, with no storms from January through April in either year. There were 28 repeat hits across 16 provinces; Rizal had 4, while Cagayan and Ilocos Sur had 3 each.

The national regular-milled price ended lower for 75 of 81 provinces. Upside swing has a median of about 1.98 percentage points across all 48 readings; the top five are Masbate, Batangas, Marinduque, Occidental Mindoro, and Aurora. Regional Most vulnerable units are Bicol, CAR, and Cagayan Valley; CAR and Cagayan Valley also pass the one-reading-per-month check. Twelve provinces are Most vulnerable in the all-reading version, and 10 are also Most vulnerable under the monthly check.

This is a two-year descriptive screen. Region sizes range from 1 to 7, warnings are not damage, some provinces have zero severe-warning exposure, prices are missing for Sulu and Batanes, provinces can drop in and out of bulletins, and the 14-day repeat-hit window is a chosen default. The results do not establish that warnings changed prices.

## Discrepancies and reconciliation notes

The project combines datasets with different coverage, units, and time structures. These differences are expected, but they must be visible in any final presentation:

1. **Warning coverage and price coverage are different universes.** The warning data report 63 provinces ever reaching a listed warning signal, while the price table has 81 province rows. The warning count should not be subtracted from the price count to infer the number of never-warned provinces. The notebook assigns zero severe-warning exposure to provinces in its analysis universe that were never listed at Signal 3 or higher.
2. **Two price provinces are excluded from the overlap calculations.** Sulu and Batanes have no regular-milled price readings. They may still appear in warning-focused material, but they cannot receive a price-spike score or an overlap-box assignment.
3. **One province has incomplete price coverage.** Misamis Occidental has two missing readings. Its upside swing is calculated from the available price sequence, so the missingness should be shown as a data-quality note rather than treated as a zero price change.
4. **The two warning counts are not the same measure.** A province can appear in warning bulletins at Signals 1–2 without contributing to `n_severe`. The 63-province warning count is “ever listed at any warning signal,” while `n_severe` counts storms where the province reached Signal 3 or higher.
5. **The robustness check is not a second result set or panel.** It uses a different set of 24 price readings and its own medians and box assignments. Stars and printed tables show the comparison; the main charts remain based on all 48 readings.
6. **The grid is not causal evidence.** A province above both medians is labeled Most vulnerable as a screening category. The label does not mean typhoons caused its price rises, nor that it experienced greater physical damage.

## Possible final dashboard

The final dashboard should be an interactive descriptive screening tool, not a causal model. It should use the notebook's already calculated values and clearly display the coverage differences above.

### 1. Header and KPI cards

Show:

- 81 province rows in the price table and 48 price readings;
- 63 provinces ever listed in warning data;
- 75 of 81 provinces ending lower in price;
- 12 Most vulnerable provinces using all readings;
- 3 Most vulnerable regions using all readings; and
- 67 of 81 provinces and 13 of 17 regions keeping the same box in the robustness check.

Each card should include a short definition or tooltip so that counts from different data universes are not confused.

### 2. Interactive map

Color provinces by the four all-reading boxes:

- Most vulnerable;
- Exposed but stable;
- High price swings, lower severe-warning exposure; and
- Low concern.

Use a separate visual state for missing price data, including Sulu and Batanes. On hover, show province, region, `n_severe`, upside swing, box, number of missing readings, and whether the province is also Most vulnerable under the monthly check.

### 3. Linked overlap grid

Recreate Chart 4 as an interactive scatter plot:

- X-axis: `n_severe`;
- Y-axis: upside swing;
- Fixed vertical reference at 1.5;
- Median lines visible;
- Same four box colors and symbols;
- Labels only for Most vulnerable provinces; and
- A toggle to show or hide robustness stars.

Add a region/province toggle or a separate regional view corresponding to Chart 3. Keep the display-only jitter rule and explain it in the chart caption.

### 4. Price and warning time views

Include:

- A national price timeline with the regional price-level view from Chart 2;
- A province selector for the 48-reading price sequence;
- A warning timeline showing storm months and Signal 3+ exposure; and
- A repeat-hit summary using the existing 14-day rule.

These views should support exploration without implying that a warning event caused a price movement.

### 5. Tables and robustness panel

Include searchable tables for:

- The regional scorecard;
- Most vulnerable provinces by region as `k/n` among provinces with price data;
- All 81 province rows sorted by box, exposure, and name; and
- The one-reading-per-month robustness summary.

The robustness panel should show the two box counts, the same-box totals, and the units that are Most vulnerable under both versions.

### 6. Method and data-quality panel

Keep the following visible in the dashboard:

- Upside swing is based on rises only; falls count as zero;
- The main version uses 48 readings and the robustness version uses 24 first-of-month readings;
- Region values are medians of province values;
- Exact median ties count as low;
- Sulu and Batanes have no price readings;
- Misamis Occidental has two missing readings; and
- The analysis is descriptive and does not establish causation.

### Dashboard implementation path

A practical next step is to export one tidy analysis table for provinces, one for regions, one monthly price table, and one warning summary from the notebook. A lightweight web app can then read those prepared tables and render the map, linked grids, time views, and searchable tables. The dashboard should not recompute the definitions independently; it should reuse the notebook's tested outputs so that displayed numbers and classifications stay aligned.

The repository also contains `dashboard/index.html` as a presentation scaffold. It is not counted as a completed interactive dashboard until its placeholders are replaced with the prepared analysis tables, charts, and data-quality notes described above.

## Milestone 4 readiness

The repository now contains the core Milestone 4 analytical deliverables: the executable notebook, five generated charts, written chart interpretations, a cautious non-causal inference, methodology documentation, and a README narrative connecting the results to the research question. A formal submission record or rubric-specific upload is not stored in this repository, so the final submission step must still be completed through the course or project submission process.
