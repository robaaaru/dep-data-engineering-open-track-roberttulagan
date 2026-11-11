# Rice Price Spikes and Typhoon Warnings: A Province-Level Overlap Analysis

## The question

Which Philippine regions and provinces had both more severe typhoon warnings and larger rice-price increases during **2024–2025**?

## Why this matters

Typhoon warnings and rice prices are both useful signals for food-security planning. This project places them side by side to identify places that deserve closer monitoring and further investigation.

This is a descriptive comparison. It does **not** claim that typhoons caused rice-price changes, and warning exposure is not the same as physical damage.

## The short answer

- **Bicol, CAR, and Cagayan Valley** stood out in the regional comparison.
- **12 provinces** were in the high-exposure/high-price-swing group.
- **67 of 81 provinces** and **13 of 17 regions** kept the same group when the price data were checked using one reading per month.

These results identify areas for follow-up. They do not prove cause and effect.

## What the project measures

- **Severe-warning exposure:** the number of storms where a province reached Wind Signal 3 or higher.
- **Rice-price upside swing:** the root-mean-square size of upward percentage movements in regular-milled rice prices. Price decreases do not increase this score.
- **Top five repeatedly hit provinces:** a ranked list of the five provinces with the most repeat severe-warning hits.
- **Overlap:** places above the typical value for their comparison group on both severe-warning exposure and price swing. Places equal to the typical value are placed in the lower group.

Repeat hits are tracked separately from the four groups, which use only the first two measures. The top-five repeat-hit KPI gives stakeholders a clear list of provinces to monitor.

The analysis places provinces and regions into four descriptive groups:

| Group                                            | Meaning                                     |
| ------------------------------------------------ | ------------------------------------------- |
| Most vulnerable                                  | High warning exposure and high price swing  |
| Exposed but stable                               | High warning exposure and lower price swing |
| High price swings, lower severe-warning exposure | Lower warning exposure and high price swing |
| Low concern                                      | Lower values on both measures               |

These are screening labels, not claims about damage or vulnerability in the everyday sense.

## Data

The project uses:

- PSA rice-price data;
- PAGASA typhoon bulletins; and
- PSA provincial boundary data.

The analysis covers 81 provinces with usable price data, 48 rice-price readings per province, 41 storms, and 2024–2025 warning records. Sulu and Batanes have no usable regular-milled price readings, so they are left out of the price comparisons.
The analysis uses the warning bulletins themselves; it does not use the separate forecast-track data.

Rice prices were recorded twice a month, using a first and second phase. Warning records were combined so that each province and storm was counted once, using the highest warning level recorded for that storm.

Regional results use the typical province value within each region. The project also checks the results using one price reading per month instead of two. This is a stability check, not a test of cause and effect.

For the warning charts and repeat-hit KPI, a repeat hit means that the same province had another severe warning within 14 days. This is a timing measure, not a measure of damage or recovery.

## Run the project

Install the dependencies:

```powershell
python -m venv venv
.\venv\Scripts\python.exe -m pip install -r requirements.txt
```

Run the complete pipeline, including PAGASA bulletin download:

```powershell
.\venv\Scripts\python.exe scripts\run_pipeline.py
```

If the PAGASA files are already available locally:

```powershell
.\venv\Scripts\python.exe scripts\run_pipeline.py --skip-ingest
```

The pipeline always uses the repository's `venv\Scripts\python.exe` for ingestion, transformation, SQLite loading, and notebook execution, even if another Python installation is active in the shell.

The pipeline:

```text
ingests data -> transforms data -> loads SQLite -> runs the notebook -> regenerates figures, tables, and dashboard/data.json
```

The final notebook cell calls [`scripts/dashboard_data.py`](scripts/dashboard_data.py) to serialize the calculated province, region, price, warning, and KPI trend outputs consumed by the dashboard. It also writes KPI definitions, KPI trends, and province and region group tables to `output/`. Running the pipeline again after adding source data therefore refreshes the dashboard data and tables reproducibly.

The pipeline does not create the stakeholder PDF. That brief is a separate, manually prepared summary of the analysis.

## Main outputs

- **Analysis notebook:** [`notebooks/kpi_and_segmentation_analysis.ipynb`](notebooks/kpi_and_segmentation_analysis.ipynb)
- **Interactive dashboard:** [`dashboard/index.html`](dashboard/index.html) (published through GitHub Pages)
- **Charts:** [`output/figures/`](output/figures/)
- **Stakeholder policy brief:** [`output/stakeholder_policy_brief.pdf`](output/stakeholder_policy_brief.pdf)
- **KPI definitions:** [`output/kpi_definitions.csv`](output/kpi_definitions.csv)
- **KPI trends:** [`output/kpi_trends.csv`](output/kpi_trends.csv)
- **Top-five repeatedly hit provinces:** [`output/repeat_hit_provinces.csv`](output/repeat_hit_provinces.csv)
- **Province groups:** [`output/province_groups.csv`](output/province_groups.csv)
- **Region groups:** [`output/region_groups.csv`](output/region_groups.csv)
- **Processed datasets:** [`data/processed/`](data/processed/)

The notebook contains the data checks, KPI calculations, descriptive charts, regional and provincial groupings, robustness check, findings, and limitations.

## Important limitations

This project covers two years and describes patterns in the available data. It does not measure:

- whether typhoons caused rice-price increases;
- physical damage or household impact;
- transport, supply, demand, or policy effects; or
- whether one flagged place was harmed more than another.

The findings should be used to guide monitoring and better questions, not to make causal claims.
