import pandas as pd

df = pd.read_csv("sample_data/clean_reviews_marine_translated.csv", encoding="utf-8")

print("=== untranslated_no_method_available ===")
print(df[df["translation_status"] == "untranslated_no_method_available"][["text", "failure_reason"]].to_string())

print("\n=== translated_mymemory (all 16) ===")
print(df[df["translation_status"] == "translated_mymemory"][["text"]].to_string())

print("\n=== translated_argos (random sample of 15) ===")
print(df[df["translation_status"] == "translated_argos"].sample(15, random_state=42)[["text"]].to_string())

print("\n=== no_translatable_content (all 3) ===")
print(df[df["translation_status"] == "no_translatable_content"][["text"]].to_string())

print("\n=== already_english (all 13) ===")
print(df[df["translation_status"] == "already_english"][["text"]].to_string())
