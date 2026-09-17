"""
Cleans raw review text: removes duplicates, empty text, standardizes dates.
"""

import pandas as pd

IN_PATH = "sample_data/raw_reviews_marine.csv"
OUT_PATH = "sample_data/clean_reviews_marine.csv"


def clean(df: pd.DataFrame) -> pd.DataFrame:
    before = len(df)

    df = df.dropna(subset=["text"])
    df = df[df["text"].str.strip() != ""]
    df = df.drop_duplicates(subset=["destination", "text"])
    df["text"] = df["text"].str.strip()
    df["destination"] = df["destination"].str.strip()

    def to_month(val):
        try:
            return pd.to_datetime(val).strftime("%Y-%m")
        except Exception:
            return val

    df["month"] = df["time"].apply(to_month)
    df = df.drop(columns=["time"])

    after = len(df)
    print(f"Cleaned reviews: {before} -> {after} rows ({before - after} removed)")
    return df.reset_index(drop=True)


def main():
    df = pd.read_csv(IN_PATH)
    df = clean(df)
    df.to_csv(OUT_PATH, index=False)
    print(f"Saved -> {OUT_PATH}")


if __name__ == "__main__":
    main()