import pandas as pd
import re

df = pd.read_csv("sample_data/clean_reviews_land_translated.csv", encoding="utf-8")

NON_LATIN_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7a3\u0e00-\u0e7f\u0600-\u06ff\u0400-\u04ff\u0900-\u097f\u0980-\u09ff]")

def has_non_latin(text):
    return bool(NON_LATIN_RE.search(str(text)))

leftover = df[df["text"].apply(has_non_latin)]
print(f"{len(leftover)} rows anywhere in the file still contain non-Latin script:\n")
print(leftover[["text", "translation_status"]].to_string())

print("\nFinal status breakdown:")
print(df["translation_status"].value_counts())
