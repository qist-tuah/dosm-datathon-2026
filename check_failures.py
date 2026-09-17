import pandas as pd

df = pd.read_csv("sample_data/clean_reviews_land_translated.csv", encoding="utf-8")
review = df[df["translation_status"] == "needs_manual_review"]
print(review["failure_reason"].value_counts())
print()
print(review[["failure_reason"]].head(10).to_string())
