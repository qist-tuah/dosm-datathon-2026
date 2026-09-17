import pandas as pd

IN_PATH = "sample_data/land_destination_reviews.csv"
OUT_PATH = "sample_data/raw_reviews_land.csv"

df = pd.read_csv(IN_PATH)
print("Original shape:", df.shape)

df = df.rename(columns={
	"place_name": "destination",
	"review_text": "text",
	"published_date": "time",
})
df = df[["destination", "rating", "text", "time"]]
df.to_csv(OUT_PATH, index=False)
print(f"Saved {len(df)} rows -> {OUT_PATH}")
print(df["destination"].value_counts())
