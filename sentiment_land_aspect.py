"""
sentiment_aspect.py
-----------------------
Runs sentiment analysis on each review and tags which "aspect" it's about.
Reads from the translated file so ALL reviews are included.
"""

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

IN_PATH = "sample_data/clean_reviews_land_translated.csv"
OUT_PATH = "sample_data/scored_reviews_land.csv"

analyzer = SentimentIntensityAnalyzer()

ASPECT_KEYWORDS = {
    "crowding": ["crowd", "crowded", "queue", "packed", "busy", "too many tourists", "overcrowded"],
    "price": ["price", "expensive", "overpriced", "cost", "value for money", "cheap"],
    "cleanliness": ["dirty", "clean", "trash", "rubbish", "litter", "maintained"],
    "environment": ["coral", "damaged", "reef", "polluted", "pollution", "bleached"],
}


def detect_aspects(text: str) -> list:
    text_lower = text.lower()
    found = []
    for aspect, keywords in ASPECT_KEYWORDS.items():
        if any(kw in text_lower for kw in keywords):
            found.append(aspect)
    return found if found else ["general"]


def score_sentiment(text: str) -> float:
    """Returns compound sentiment score from -1 (very negative) to +1 (very positive)."""
    return analyzer.polarity_scores(text)["compound"]


def main():
    df = pd.read_csv(IN_PATH)
    before = len(df)

    # Safety check: drop any row where text is missing/blank (e.g. a failed
    # translation that returned nothing) — VADER crashes on non-string input.
    df = df.dropna(subset=["text"])
    df["text"] = df["text"].astype(str)
    df = df[df["text"].str.strip() != ""]

    after = len(df)
    if before != after:
        print(f"Dropped {before - after} rows with missing/blank text before scoring")

    df["sentiment_score"] = df["text"].apply(score_sentiment)
    df["aspects"] = df["text"].apply(detect_aspects)

    df_exploded = df.explode("aspects").rename(columns={"aspects": "aspect"})
    df_exploded.to_csv(OUT_PATH, index=False)
    print(f"Scored {len(df)} reviews across {len(df_exploded)} aspect-tagged rows -> {OUT_PATH}")

    summary = df_exploded.groupby(["destination", "aspect"])["sentiment_score"].mean().round(2)
    print("\nSentiment summary (mean score per destination/aspect):")
    print(summary.to_string())


if __name__ == "__main__":
    main()