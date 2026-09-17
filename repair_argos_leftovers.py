import re, time
import pandas as pd
from deep_translator import MyMemoryTranslator

ORIG_PATH = "sample_data/clean_reviews_land.csv"
CUR_PATH = "sample_data/clean_reviews_land_translated.csv"

NON_LATIN_RE = re.compile(r"[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7a3\u0e00-\u0e7f\u0600-\u06ff\u0400-\u04ff\u0900-\u097f\u0980-\u09ff]")
CHUNK_LIMIT = 480
TARGET = "en-GB"  # <-- the fix: MyMemory requires a full locale code, not bare "en"

def has_non_latin(text):
    return bool(NON_LATIN_RE.search(str(text)))

def chunk_text(text, limit=CHUNK_LIMIT):
    parts = re.split(r"(\n+)", text)
    chunks, current = [], ""
    for part in parts:
        if len(current) + len(part) <= limit:
            current += part
        else:
            if current:
                chunks.append(current)
            while len(part) > limit:
                chunks.append(part[:limit])
                part = part[limit:]
            current = part
    if current:
        chunks.append(current)
    return chunks

def translate_long_mymemory(text):
    chunks = chunk_text(text)
    out = []
    for c in chunks:
        if not c.strip():
            out.append(c)
            continue
        try:
            out.append(MyMemoryTranslator(source="auto", target=TARGET).translate(c))
        except Exception as e:
            return None, str(e)
        time.sleep(1.0)
    return "".join(out), None

def main():
    df_orig = pd.read_csv(ORIG_PATH, encoding="utf-8")
    df = pd.read_csv(CUR_PATH, encoding="utf-8")
    if "failure_reason" not in df.columns:
        df["failure_reason"] = ""

    problem_idx = df[
        df["translation_status"].isin(["translated_argos", "needs_manual_review"])
        & df["text"].apply(has_non_latin)
    ].index.tolist()
    print(f"Reprocessing {len(problem_idx)} rows...")

    still_bad = []
    for i, idx in enumerate(problem_idx):
        original = str(df_orig.at[idx, "text"])
        translated, err = translate_long_mymemory(original)
        if translated is not None and not has_non_latin(translated):
            df.at[idx, "text"] = translated
            df.at[idx, "translation_status"] = "translated_mymemory_repair"
            df.at[idx, "failure_reason"] = ""
        else:
            still_bad.append(idx)
            df.at[idx, "translation_status"] = "needs_manual_review"
            df.at[idx, "failure_reason"] = err or "still_non_latin_after_retry"
        print(f"  {i+1}/{len(problem_idx)} done (idx {idx})")

    df.to_csv(CUR_PATH, index=False, encoding="utf-8")
    print(f"\nAuto-fixed: {len(problem_idx) - len(still_bad)}")
    print(f"Still needs manual review ({len(still_bad)}): {still_bad}")

if __name__ == "__main__":
    main()
