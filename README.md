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
- **Rice-price upside swing:** the typical size of upward movements in regular-milled rice prices. Price decreases do not increase this score.
- **Overlap:** places above the overall median on both measures.

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

The processed data cover 81 provinces, 48 rice-price readings per province, 41 storms, and 2024–2025 warning records.

## Run the project

Install the dependencies:

```text
pip install -r requirements.txt
```

Run the complete pipeline, including PAGASA bulletin download:

```text
python scripts/run_pipeline.py
```

If the PAGASA files are already available locally:

```text
python scripts/run_pipeline.py --skip-ingest
```

The pipeline:

```text
ingests data -> transforms data -> loads SQLite -> runs the notebook -> regenerates figures
```

## Main outputs

- **Analysis notebook:** [`notebooks/kpi_and_segmentation_analysis.ipynb`](notebooks/kpi_and_segmentation_analysis.ipynb)
- **Charts:** [`output/figures/`](output/figures/)
- **Stakeholder policy brief:** [`output/stakeholder_policy_brief.pdf`](output/stakeholder_policy_brief.pdf)
- **Processed datasets:** [`data/processed/`](data/processed/)

The notebook contains the data checks, KPI calculations, descriptive charts, regional and provincial groupings, robustness check, findings, and limitations.

## Important limitations

This project covers two years and describes patterns in the available data. It does not measure:

- whether typhoons caused rice-price increases;
- physical damage or household impact;
- transport, supply, demand, or policy effects; or
- whether one flagged place was harmed more than another.

The findings should be used to guide monitoring and better questions, not to make causal claims.
