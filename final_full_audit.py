"""
final_full_audit.py
--------------------
One comprehensive pass checking every failure mode we've hit in this
pipeline so far, plus a few we haven't explicitly checked yet. Run this
before treating the translated CSV as final.
"""

import re
import pandas as pd

ORIG_PATH = "sample_data/clean_reviews_land.csv"
CUR_PATH = "sample_data/clean_reviews_land_translated.csv"

NON_LATIN_RE = re.compile(
    r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7a3\u0e00-\u0e7f"
    r"\u0600-\u06ff\u0400-\u04ff\u0900-\u097f\u0980-\u09ff]"
)
REPETITION_CHAR_PATTERN = re.compile(r"(.)\1{4,}")
REPETITION_WORD_PATTERN = re.compile(r"(\S+)(\s+\1){3,}", re.UNICODE)
REPLACEMENT_CHAR = "\ufffd"

ERROR_LEAK_PATTERNS = [
    "no support for the provided language",
    "mymemory",
    "quota",
    "traceback",
    "httperror",
    "connectionerror",
    "429",
    "403 client error",
]

EXPECTED_STATUSES = {
    "not_applicable",
    "translated_argos",
    "already_english",
    "translated_mymemory_repair",
    "translated_manual",
    "translated_manual_low_confidence",
    "no_translatable_content",
    "translated_mymemory",
    "needs_manual_review",
}


def has_non_latin(text):
    return bool(NON_LATIN_RE.search(str(text)))


def has_repetition_failure(text):
    text = str(text)
    return bool(REPETITION_CHAR_PATTERN.search(text)) or bool(
        REPETITION_WORD_PATTERN.search(text)
    )


def has_error_leak(text):
    low = str(text).lower()
    return any(p in low for p in ERROR_LEAK_PATTERNS)


def has_replacement_char(text):
    return REPLACEMENT_CHAR in str(text)


def is_mostly_ascii_letters(text, threshold=0.6):
    letters = re.findall(r"[^\W\d_]", str(text), flags=re.UNICODE)
    if not letters:
        return False
    ascii_letters = [c for c in letters if ord(c) < 0x2000]
    return (len(ascii_letters) / len(letters)) >= threshold


def main():
    df_orig = pd.read_csv(ORIG_PATH, encoding="utf-8")
    df = pd.read_csv(CUR_PATH, encoding="utf-8")

    print("=" * 70)
    print("1. ROW COUNT CHECK")
    print("=" * 70)
    if len(df_orig) == len(df):
        print(f"OK -- {len(df)} rows in both files.")
    else:
        print(f"MISMATCH -- original has {len(df_orig)} rows, "
              f"translated has {len(df)} rows.")

    print("\n" + "=" * 70)
    print("2. NULL / EMPTY TEXT CHECK")
    print("=" * 70)
    orig_had_content = df_orig["text"].apply(
        lambda t: len(str(t).strip()) > 0
    )
    now_empty = df["text"].apply(lambda t: len(str(t).strip()) == 0)
    problem = df[orig_had_content & now_empty]
    if problem.empty:
        print("OK -- no row that had content originally is now empty.")
    else:
        print(f"PROBLEM -- {len(problem)} rows lost their content:")
        print(problem[["text", "translation_status"]].to_string())

    print("\n" + "=" * 70)
    print("3. STATUS VALUE CHECK")
    print("=" * 70)
    actual_statuses = set(df["translation_status"].unique())
    unexpected = actual_statuses - EXPECTED_STATUSES
    if not unexpected:
        print("OK -- all translation_status values are recognized.")
        print(df["translation_status"].value_counts())
    else:
        print(f"PROBLEM -- unexpected status values found: {unexpected}")

    print("\n" + "=" * 70)
    print("4. ERROR-STRING LEAK CHECK (API errors saved as translations)")
    print("=" * 70)
    leaked = df[df["text"].apply(has_error_leak)]
    if leaked.empty:
        print("OK -- no row's text column contains an API/error fragment.")
    else:
        print(f"PROBLEM -- {len(leaked)} rows may have an error string "
              f"saved as translated text:")
        print(leaked[["text", "translation_status"]].to_string())

    print("\n" + "=" * 70)
    print("5. REPETITION-FAILURE CHECK (full file, not just flagged rows)")
    print("=" * 70)
    repetition_hits = df[df["text"].apply(has_repetition_failure)]
    if repetition_hits.empty:
        print("OK -- no row shows decoder repetition-loop garbage.")
    else:
        print(f"NOTE -- {len(repetition_hits)} rows match the repetition "
              f"pattern (verify manually -- some may be legitimate, e.g. "
              f"'sooo good' or 'bestrttttt'):")
        print(repetition_hits[["text", "translation_status"]].to_string())

    print("\n" + "=" * 70)
    print("6. NON-LATIN SCRIPT SCAN (full file, auto-classified)")
    print("=" * 70)
    non_latin_rows = df[df["text"].apply(has_non_latin)]
    needs_review = pd.DataFrame()
    if non_latin_rows.empty:
        print("OK -- zero rows contain non-Latin script.")
    else:
        bilingual_safe = non_latin_rows[
            non_latin_rows["text"].apply(is_mostly_ascii_letters)
        ]
        needs_review = non_latin_rows[
            ~non_latin_rows["text"].apply(is_mostly_ascii_letters)
        ]
        print(f"{len(non_latin_rows)} rows contain non-Latin script total:")
        print(f"  - {len(bilingual_safe)} look like bilingual reviews "
              f"(majority-English text with native-language duplicate) "
              f"-- likely SAFE, but listed for your own confirmation:")
        if not bilingual_safe.empty:
            print(bilingual_safe[["text", "translation_status"]].to_string())
        print(f"  - {len(needs_review)} do NOT look majority-English -- "
              f"NEEDS REVIEW:")
        if not needs_review.empty:
            print(needs_review[["text", "translation_status"]].to_string())

    print("\n" + "=" * 70)
    print("7. ENCODING SANITY CHECK (replacement character U+FFFD)")
    print("=" * 70)
    bad_encoding = df[df["text"].apply(has_replacement_char)]
    if bad_encoding.empty:
        print("OK -- no row contains the U+FFFD replacement character.")
    else:
        print(f"PROBLEM -- {len(bad_encoding)} rows show signs of lossy "
              f"encoding conversion:")
        print(bad_encoding[["text", "translation_status"]].to_string())

    print("\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)
    total_problems = (
        (0 if len(df_orig) == len(df) else 1)
        + len(problem)
        + len(unexpected)
        + len(leaked)
        + len(needs_review)
        + len(bad_encoding)
    )
    if total_problems == 0:
        print("All checks passed. Dataset looks clean and ready to proceed.")
    else:
        print(f"{total_problems} issue(s) flagged above -- review before "
              f"proceeding.")


if __name__ == "__main__":
    main()
