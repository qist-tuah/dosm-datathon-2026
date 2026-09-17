"""
prepare_marine_risk_components.py
-------------------------------------
MODULE B, PART 1: merges marine visitor proxy with environmental data,
calculates SST anomaly, and normalizes each component to 0-1.
"""

import pandas as pd

VISITORS_PATH = "sample_data/clean_marine_visitor_arrivals.csv"
SST_PATH = "sample_data/clean_marine_environmental_data.csv"
OUT_PATH = "sample_data/marine_risk_components.csv"


def normalize(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return series * 0
    return (series - lo) / (hi - lo)


def main():
    visitors = pd.read_csv(VISITORS_PATH)
    sst = pd.read_csv(SST_PATH)

    # Calculate SST anomaly: each month's temperature minus that park's own
    # average temperature across the full period.
    sst["sst_anomaly"] = sst["sst_celsius"] - sst.groupby("marine_park")["sst_celsius"].transform("mean")

    df = pd.merge(visitors, sst, on=["marine_park", "month"], how="inner")

    df["visitor_norm"] = normalize(df["visitors"])
    df["sst_anomaly_norm"] = normalize(df["sst_anomaly"].clip(lower=0))  # only warming matters
    df["turbidity_norm"] = normalize(df["turbidity_index"])

    df.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(df)} rows -> {OUT_PATH}")
    print("\nColumns produced:", list(df.columns))
    print(df.head(3).to_string())


if __name__ == "__main__":
    main()