import re
import pandas as pd

IN_PATH = "sample_data/clean_reviews_marine_translated.csv"

df = pd.read_csv(IN_PATH, encoding="utf-8")
df["text"] = df["text"].fillna("").astype(str)

# 1. Leftover non-Latin script (translation should have removed this)
NON_LATIN_PATTERN = re.compile(
    r'[\u4E00-\u9FFF\u3040-\u30FF\uAC00-\uD7A3\u0E00-\u0E7F'
    r'\u0600-\u06FF\u0400-\u04FF\u0900-\u097F\u0980-\u09FF]'
)
has_non_latin = df["text"].apply(lambda t: bool(NON_LATIN_PATTERN.search(t)))

# 2. Repetition-loop garbage that may have slipped through
REPETITION_CHAR = re.compile(r'(.)\1{4,}')
REPETITION_WORD = re.compile(r'(\S+)(\s+\1){3,}', re.UNICODE)
has_repetition = df["text"].apply(
    lambda t: bool(REPETITION_CHAR.search(t)) or bool(REPETITION_WORD.search(t))
)

# 3. Common Malay words/markers that suggest code-mixing even in "English" text
MALAY_MARKERS = [
    r'\bakan\b', r'\bdtg\b', r'\bdatang\b', r'\byang\b', r'\bdan\b', r'\btempat\b',
    r'\bcantik\b', r'\bcntik\w*\b', r'\bbagus\b', r'\bsangat\b', r'\bbaik\b',
    r'\bpergi\b', r'\blagi\b', r'\bsuka\b', r'\bboleh\b', r'\btak\b', r'\byg\b',
]
MALAY_PATTERN = re.compile('|'.join(MALAY_MARKERS), re.IGNORECASE)
has_malay_marker = df["text"].apply(lambda t: bool(MALAY_PATTERN.search(t)))

flagged = df[has_non_latin | has_repetition | has_malay_marker].copy()
flagged["issue"] = ""
flagged.loc[has_non_latin[flagged.index], "issue"] += "non_latin_script;"
flagged.loc[has_repetition[flagged.index], "issue"] += "repetition;"
flagged.loc[has_malay_marker[flagged.index], "issue"] += "possible_malay_mix;"

print(f"Total rows: {len(df)}")
print(f"Flagged for manual review: {len(flagged)}")
print(f"  - non-Latin script leftover: {has_non_latin.sum()}")
print(f"  - repetition-loop garbage: {has_repetition.sum()}")
print(f"  - possible Malay code-mixing: {has_malay_marker.sum()}")
print()
print(flagged[["text", "translation_status", "issue"]].to_string())

flagged.to_csv("sample_data/needs_manual_review.csv", index=False, encoding="utf-8")
print("\nSaved full flagged list -> sample_data/needs_manual_review.csv")
