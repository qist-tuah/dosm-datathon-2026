"""
Renames Apify's "All fields" export columns to match what clean_reviews.py expects.
"""

import pandas as pd

IN_PATH = "sample_data/raw_reviews_marine_export.csv"
OUT_PATH = "sample_data/raw_reviews_marine.csv"

df = pd.read_csv(IN_PATH)
print("Original shape:", df.shape)

df = df.rename(columns={
	"title": "destination",
	"stars": "rating",
	"text": "text",
	"publishedAtDate": "time",
})

df = df[["destination", "rating", "text", "time"]]
df.to_csv(OUT_PATH, index=False)
print(f"Saved {len(df)} rows -> {OUT_PATH}")
print("\nDestinations found:")
print(df["destination"].value_counts())
