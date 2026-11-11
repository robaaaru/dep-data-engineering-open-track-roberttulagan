"""Serialize notebook analysis outputs for the static dashboard."""

import json
from pathlib import Path

import numpy as np
import pandas as pd


def save_data(
    output_path,
    *,
    exposure,
    peak,
    boundaries,
    price_stats,
    region_main,
    prov_main,
    monthly_prices,
    storms_by_month,
    kpi_trends,
    repeat_counts,
):
    """Save the notebook's calculated KPIs and dashboard data contract."""
    output_path = Path(output_path)
    province_rows = prov_main.merge(
        boundaries[["province", "region", "lat", "lon"]],
        on="province",
        how="left",
        suffixes=("", "_boundary"),
    )
    province_rows["group"] = province_rows["box"].replace(
        {"High price swings, lower severe-warning exposure": "High price swings"}
    )
    province_rows = province_rows.replace({np.nan: None})

    regions = region_main.copy()
    regions["group"] = regions["box"].replace(
        {"High price swings, lower severe-warning exposure": "High price swings"}
    )
    region_rows = regions.replace({np.nan: None})

    def records(frame, columns, rename=None):
        result = frame[columns].rename(columns=rename or {}).to_dict("records")
        for row in result:
            for key, value in row.items():
                if isinstance(value, (np.integer, np.floating)):
                    row[key] = value.item()
                elif isinstance(value, pd.Timestamp):
                    row[key] = value.strftime("%Y-%m-%d")
        return result

    price_rows = []
    for month, row in monthly_prices.iterrows():
        price_rows.append(
            {
                "month": month.strftime("%Y-%m"),
                "median": round(float(row["median"]), 2),
                "p10": round(float(row["p10"]), 2),
                "p90": round(float(row["p90"]), 2),
            }
        )
    storm_rows = [
        {"month": month.strftime("%Y-%m"), "storms": int(row.sum())}
        for month, row in storms_by_month.iterrows()
    ]

    province_records = records(
        province_rows,
        [
            "province",
            "region",
            "lat",
            "lon",
            "n_severe",
            "upside_swing",
            "group",
        ],
        {"n_severe": "severeWarnings", "upside_swing": "upsideSwing"},
    )
    for row in province_records:
        row["upsideSwing"] = round(float(row["upsideSwing"]), 2)
        row["repeatHits"] = int(repeat_counts.get(row["province"], 0))

    region_records = records(
        region_rows,
        ["region_short", "n_severe", "upside_swing", "group"],
        {
            "region_short": "shortRegion",
            "n_severe": "severeWarnings",
            "upside_swing": "upsideSwing",
        },
    )
    region_sizes = region_main.groupby("region_short").n_provinces.first()
    flagged = prov_main[prov_main.box.eq("Most vulnerable")].groupby("region_short").size()
    for row in region_records:
        name = row["shortRegion"]
        row["upsideSwing"] = round(float(row["upsideSwing"]), 2)
        row["provinceCount"] = int(region_sizes[name])
        row["mostVulnerableProvinces"] = int(flagged.get(name, 0))

    kpi_trend_records = records(
        kpi_trends,
        ["kpi", "year", "geography", "value"],
    )
    for row in kpi_trend_records:
        row["value"] = round(float(row["value"]), 2)

    top_repeat_counts = (
        repeat_counts.rename("repeat_hits")
        .rename_axis("province")
        .reset_index()
        .sort_values(["repeat_hits", "province"], ascending=[False, True])
        .head(5)
    )
    repeat_hit_provinces = [
        {"rank": rank, "province": province, "repeatHits": int(count)}
        for rank, (province, count) in enumerate(
            top_repeat_counts.itertuples(index=False), start=1
        )
    ]
    median_swing = float(price_stats["upside_swing"].median())
    payload = {
        "meta": {
            "priceMedian": round(median_swing, 2),
            "exposureMedian": int(exposure["n_severe"].median()),
            "provinceCount": len(province_records),
            "regionCount": len(region_records),
            "everWarnedCount": int(peak["province"].nunique()),
            "mostVulnerableCount": int((prov_main["box"] == "Most vulnerable").sum()),
            "mostVulnerableRegionCount": int(
                (region_main["box"] == "Most vulnerable").sum()
            ),
            "top5RepeatHitProvinceCount": len(repeat_hit_provinces),
        },
        "provinces": province_records,
        "regions": region_records,
        "kpiTrends": kpi_trend_records,
        "top5RepeatHitProvinces": repeat_hit_provinces,
        "priceMonthly": price_rows,
        "stormMonthly": storm_rows,
    }
    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    print(f"Saved dashboard data to {output_path}")
