"""
compute_marine_risk_score.py
--------------------------------
MODULE B, PART 2: adds review sentiment, computes the final Risk Score (0-100)
and tier, plus a "what-if" visitor cap simulator.

Formula: risk_score = 0.35*visitors + 0.35*sst_anomaly + 0.15*turbidity + 0.15*review_sentiment
"""

import pandas as pd

COMPONENTS_PATH = "sample_data/marine_risk_components.csv"
REVIEWS_PATH = "sample_data/scored_reviews_marine.csv"
OUT_PATH = "sample_data/marine_risk_tiers.csv"

# Maps each resort's specific name (from the Google Reviews scrape) back to
# its generic park name (used in the environmental/SST data), so the two
# datasets actually line up when merged.
RESORT_TO_PARK = {
    "The Taaras Beach & Spa Resort": "Pulau Redang",
    "Perhentian Island Resort": "Pulau Perhentian",
    "Berjaya Tioman Resort - Malaysia": "Pulau Tioman",
    "Sipadan Kapalai Dive Resort": "Pulau Sipadan",
    "Pulau Payar Marine Park": "Pulau Payar",
}


def normalize(series: pd.Series) -> pd.Series:
    lo, hi = series.min(), series.max()
    if hi == lo:
        return series * 0
    return (series - lo) / (hi - lo)


def normalize_with_range(series: pd.Series, lo: float, hi: float) -> pd.Series:
    if hi == lo:
        return series * 0
    return (series - lo) / (hi - lo)


def compute_final_score(df: pd.DataFrame) -> pd.DataFrame:
    df["risk_score"] = (
        0.35 * df["visitor_norm"]
        + 0.35 * df["sst_anomaly_norm"]
        + 0.15 * df["turbidity_norm"]
        + 0.15 * df["neg_review_norm"]
    ) * 100
    df["risk_score"] = df["risk_score"].clip(lower=0, upper=100)

    def tier(score):
        if score >= 66:
            return "High"
        elif score >= 33:
            return "Medium"
        return "Low"

    df["risk_tier"] = df["risk_score"].apply(tier)
    return df


def simulate_visitor_cap(df: pd.DataFrame, marine_park: str, reduction_pct: float) -> pd.DataFrame:
    visitor_min, visitor_max = df["visitors"].min(), df["visitors"].max()

    subset = df[df["marine_park"] == marine_park].copy()
    subset["visitors"] = subset["visitors"] * (1 - reduction_pct / 100)
    subset["visitor_norm"] = normalize_with_range(subset["visitors"], visitor_min, visitor_max).clip(lower=0, upper=1)
    subset = compute_final_score(subset)
    return subset


def main():
    components = pd.read_csv(COMPONENTS_PATH)
    reviews = pd.read_csv(REVIEWS_PATH)

    reviews["marine_park"] = reviews["destination"].map(RESORT_TO_PARK)
    unmapped = reviews[reviews["marine_park"].isna()]["destination"].unique()
    if len(unmapped) > 0:
        print(f"WARNING: unmapped destinations found (dropped): {list(unmapped)}")
    reviews = reviews.dropna(subset=["marine_park"])

    env_reviews = reviews[reviews["aspect"] == "environment"]
    env_monthly = (
        env_reviews.groupby(["marine_park", "month"])["sentiment_score"]
        .mean()
        .reset_index()
        .rename(columns={"sentiment_score": "env_review_sentiment"})
    )

    df = pd.merge(components, env_monthly, on=["marine_park", "month"], how="left")
    df["env_review_sentiment"] = df["env_review_sentiment"].fillna(0)
    df["neg_review_norm"] = normalize((-df["env_review_sentiment"]).clip(lower=0))

    df = compute_final_score(df)
    df.to_csv(OUT_PATH, index=False)
    print(f"Saved {len(df)} rows -> {OUT_PATH}")

    latest = df.sort_values("month").groupby("marine_park").tail(1)
    print("\nMost recent risk tier per marine park:")
    print(latest[["marine_park", "month", "risk_score", "risk_tier"]].sort_values("risk_score", ascending=False))

    example_park = df["marine_park"].iloc[0]
    example = simulate_visitor_cap(df, example_park, reduction_pct=20)
    print(f"\nExample what-if: {example_park} with 20% visitor cap reduction (most recent month):")
    print(example.sort_values("month").tail(1)[["marine_park", "month", "risk_score", "risk_tier"]])


if __name__ == "__main__":
    main()