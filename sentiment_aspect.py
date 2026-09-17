"""
Runs sentiment analysis on each review and tags which "aspect" it's about
(crowding, price, cleanliness, environment).
"""

import pandas as pd
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer

IN_PATH = "sample_data/clean_reviews_marine_translated.csv"
OUT_PATH = "sample_data/scored_reviews_marine.csv"

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