import os
import re
import time
import pandas as pd
from langdetect import detect_langs, LangDetectException, DetectorFactory
from deep_translator import MyMemoryTranslator

DetectorFactory.seed = 0

ORIGINAL_PATH = "sample_data/clean_reviews_marine.csv"
TRANSLATED_PATH = "sample_data/clean_reviews_marine_translated.csv"
BACKUP_PATH = "sample_data/clean_reviews_marine_translated_backup2.csv"
TMP_PATH = "sample_data/clean_reviews_marine_translated.tmp.csv"

MYMEMORY_EMAIL = None  # <-- add your email for a higher daily quota
MYMEMORY_CHAR_LIMIT = 480

# ---------------------------------------------------------------------------
# Row categories from the audit
# ---------------------------------------------------------------------------
TOO_LONG_ROWS = [83, 482, 1033, 1162]                 # manually translated
SHORT_UNTRANSLATED_ROWS = [429, 477, 547, 668]        # manually translated
NOISE_ROWS = [636, 964]                               # flagged only, untouched
GARBAGE_ARGOS_ROWS = [
    6, 8, 36, 57, 60, 65, 77, 90, 95, 134, 139, 145, 167, 233, 252, 354,
    377, 410, 449, 499, 550, 793, 829, 901, 938, 996, 997, 1001, 1034,
    1035, 1047, 1051, 1078, 1116,
]
MYMEMORY_ERROR_ROWS = [
    123, 140, 184, 253, 445, 580, 612, 693, 707, 770, 904, 912, 993,
    1140, 1160, 1188,
]

# ---------------------------------------------------------------------------
# Validity checks
# ---------------------------------------------------------------------------
REPETITION_PATTERN = re.compile(r'(.{1,40}?)\1{4,}', re.DOTALL)
ERROR_MARKERS = [
    "mymemory warning", "you used all available free translations",
    "query length limit exceeded", "invalid target language",
    "invalid source language", "is an invalid", "langpair=",
]


def is_bad_translation(text) -> bool:
    text = str(text)
    low = text.lower()
    if any(m in low for m in ERROR_MARKERS):
        return True
    if REPETITION_PATTERN.search(text):
        return True
    return False


# ---------------------------------------------------------------------------
# Proper source-language detection (this is the actual fix -- the previous
# attempt skipped this and just tried every installed language blindly)
# ---------------------------------------------------------------------------
LANGDETECT_TO_MYMEMORY = {"zh-cn": "zh-CN", "zh-tw": "zh-TW"}


def map_to_mymemory_code(code: str) -> str:
    return LANGDETECT_TO_MYMEMORY.get(code, code)


def detect_source_language(text: str):
    """Best-guess source language. Returns 'en' if the text is almost
    certainly already English, a language code if foreign, or None if
    undetectable (very rare)."""
    stripped = text.strip()
    has_non_ascii = any(ord(c) > 127 for c in stripped)

    # Short strings are where langdetect is least reliable. If it's short
    # AND pure ASCII, it's overwhelmingly likely to be plain English
    # (this is exactly what happened to "Good.", "Awesome", "Great view",
    # etc. in the previous run -- they got needlessly sent to translation).
    if len(stripped) < 20 and not has_non_ascii:
        return "en"

    try:
        candidates = detect_langs(text)
    except LangDetectException:
        return "en" if not has_non_ascii else None

    if candidates and candidates[0].lang == "en" and candidates[0].prob > 0.6:
        return "en"
    if candidates:
        return candidates[0].lang
    return None


def mymemory_translate(text: str, source_code: str) -> str:
    kwargs = {"source": source_code, "target": "en-GB"}
    if MYMEMORY_EMAIL:
        kwargs["email"] = MYMEMORY_EMAIL
    return MyMemoryTranslator(**kwargs).translate(text)


def translate_chunked(text: str, source_code: str) -> str:
    sentences = re.split(r'(?<=[.!?\n])\s+', text)
    chunks, current = [], ""
    for s in sentences:
        if len(current) + len(s) + 1 <= MYMEMORY_CHAR_LIMIT:
            current = (current + " " + s).strip()
        else:
            if current:
                chunks.append(current)
            current = s
    if current:
        chunks.append(current)

    out = []
    for chunk in chunks:
        chunk = chunk[:MYMEMORY_CHAR_LIMIT]
        try:
            result = mymemory_translate(chunk, source_code)
            out.append(f"[UNTRANSLATED: {chunk[:60]}...]" if is_bad_translation(result) else result)
        except Exception:
            out.append(f"[ERROR: {chunk[:60]}...]")
        time.sleep(1.0)
    return " ".join(out)


def translate_row(original_text: str):
    source_code = detect_source_language(original_text)

    if source_code == "en":
        return original_text, "already_english"

    if source_code is None:
        return original_text, "untranslated_no_language_detected"

    mm_code = map_to_mymemory_code(source_code)

    if len(original_text) <= MYMEMORY_CHAR_LIMIT:
        try:
            result = mymemory_translate(original_text, mm_code)
            if not is_bad_translation(result):
                return result, f"translated_fix_{source_code}"
        except Exception:
            pass
        time.sleep(1.0)

    result = translate_chunked(original_text, mm_code)
    return result, f"translated_fix_chunked_{source_code}"


# ---------------------------------------------------------------------------
# Manual translations for the too-long / short-untranslated rows
# ---------------------------------------------------------------------------
MANUAL_TRANSLATIONS = {
    83: (
        "The hotel is very poorly maintained -- broken doors, dirty and badly kept "
        "shower and bathroom. Beds set 70cm apart, and don't try to push the "
        "nightstand to join them because there's dirt all around. The cabin would "
        "be perfect if it were clean and tidied up. They don't clean, they just "
        "make the bed. The hot water doesn't work. Don't get full board at the "
        "restaurant -- terrible and expensive food, full of flies, the breakfast "
        "is pitiful, no protein (well, if you count the flies and ants wandering "
        "the buffet). Service: nonexistent, they don't explain anything even if "
        "you speak Malay -- you find things out by talking to other guests. A "
        "shame because the place is paradise, the best location in the "
        "Perhentians. Lucky I got a deal of EUR350 for 4 nights without board. If "
        "I'd taken full board I would have been disgusted. The price on platforms "
        "like Booking, Agoda is EUR800. Not worth it."
    ),
    1033: (
        "Very expensive for what it offers. The beach it's on is probably the "
        "best, but that means every day you get a massive influx of groups coming "
        "to snorkel and/or dive, which takes away from the paradise-beach image "
        "you expect. Even so, the beach and snorkeling are worth it. As for the "
        "'Resort', it's shabby, aged, and poorly kept. Lack of cleanliness "
        "everywhere, even the sheets seemed unchanged from previous guests, with "
        "sand left inside the bed. The cabins have air conditioning and a fan but "
        "the power goes out easily. There is no hot water. Breakfast is "
        "acceptable but lacks variety over several days, and the food isn't good "
        "quality -- nearby hotel restaurants offer better meals. Staff are okay "
        "but show zero warmth (a couple are the exception), a big difference from "
        "the rest of the country. Honestly you pay a price that doesn't match the "
        "facilities -- you pay for the location. We only had 2 nights booked and "
        "stayed longer on the island but switched hotels. If I had to come back "
        "to this island this isn't a hotel I'd choose, it has a lot of room for "
        "improvement."
    ),
    1162: (
        "The beach it's on is beautiful, quiet, with a family atmosphere. But I "
        "find it expensive for the services offered, and laundry, spa, etc. also "
        "have high prices. The included breakfast is fine but has little variety "
        "day to day, and the food quality isn't anything special either. Staff "
        "are fine, nothing more, but not particularly friendly. It's "
        "accommodation under Muslim management, so there's no alcohol. You can "
        "pay by card for all services. I wouldn't come back for the price I paid."
    ),
    482: (
        "The Taaras Beach & Spa Resort (Redang Island) review. I stayed at The "
        "Taaras Beach & Spa Resort on Redang Island, Malaysia. In short: the "
        "water clarity is next-level, the resort feel is strong, and it's "
        "perfect for anyone who wants a relaxing stay -- a real reward-yourself "
        "resort. The beach was genuinely beautiful, with a perfect contrast "
        "between the emerald-blue sea and white sand. Mornings were quiet and "
        "great for photos (a very reel-worthy location). The room was spacious "
        "and felt clean, and the balcony view gave a real resort feeling -- my "
        "mood lifted the moment we arrived. Staff were kind too, and everything "
        "from the airport boat transfer to check-in went smoothly. Best of all "
        "was the not-too-crowded, hidden-getaway feeling. Good fit for couples' "
        "trips, girls' trips, and slow relaxing getaways. Redang itself still has "
        "relatively few Japanese visitors, so it's especially recommended if you "
        "want an overseas resort that doesn't feel crowded with people like you. "
        "Staff I particularly liked: Hamdan Rajab was very kind and helped a lot "
        "during our stay, and Sarah taught us about so many fish while "
        "snorkeling -- it was a lot of fun! It's enjoyable even in the "
        "off-season, so please go try it. A resort I'd love to return to and "
        "take it slow again."
    ),
    429: "Environment is superb",
    477: "The room balcony has a view of sea turtles, a beautiful once-in-a-lifetime sight",
    547: "more good",
    668: "Great",
}


def safe_to_csv(df, path, tmp_path):
    df.to_csv(tmp_path, index=False, encoding="utf-8")
    try:
        os.replace(tmp_path, path)
    except PermissionError:
        print(
            f"\nERROR: could not overwrite {path} -- it looks like it's open in "
            f"another program (Excel, Notepad, another terminal, a Jupyter "
            f"kernel). Close it and re-run. Nothing was lost: your finished "
            f"changes are safely sitting in {tmp_path} -- once the target file "
            f"is closed, just rename {tmp_path} to {path} manually, or re-run "
            f"this script."
        )
        raise


def main():
    orig_df = pd.read_csv(ORIGINAL_PATH, encoding="utf-8")
    trans_df = pd.read_csv(TRANSLATED_PATH, encoding="utf-8")

    trans_df.to_csv(BACKUP_PATH, index=False, encoding="utf-8")
    print(f"Backup saved -> {BACKUP_PATH}\n")

    print("Alignment check (row 0 should match between original and translated):")
    print(f"  original  : {str(orig_df.at[0, 'text'])[:80]}")
    print(f"  translated: {str(trans_df.at[0, 'text'])[:80]}\n")

    for idx in TOO_LONG_ROWS + SHORT_UNTRANSLATED_ROWS:
        trans_df.at[idx, "text"] = MANUAL_TRANSLATIONS[idx]
        trans_df.at[idx, "translation_status"] = "translated_manual"
        trans_df.at[idx, "failure_reason"] = ""
        print(f"Row {idx}: applied manual translation.")

    rows_to_fix = GARBAGE_ARGOS_ROWS + MYMEMORY_ERROR_ROWS
    print(f"\nRe-translating {len(rows_to_fix)} rows with proper source-language "
          f"detection (this replaces the old blind Argos-loop approach)...")
    for i, idx in enumerate(rows_to_fix):
        original_text = str(orig_df.at[idx, "text"])
        result, status = translate_row(original_text)
        trans_df.at[idx, "text"] = result
        trans_df.at[idx, "translation_status"] = status
        trans_df.at[idx, "failure_reason"] = ""
        print(f"  [{i + 1}/{len(rows_to_fix)}] row {idx} -> {status}")
        print(f"    ORIGINAL: {original_text[:100]}")
        print(f"    NEW     : {str(result)[:100]}\n")

    safe_to_csv(trans_df, TRANSLATED_PATH, TMP_PATH)
    print(f"Saved -> {TRANSLATED_PATH}")

    print("\n=== Flagged as likely non-review noise (unchanged -- your call) ===")
    for idx in NOISE_ROWS:
        print(f"Row {idx}: {trans_df.at[idx, 'text']!r}")
    print(
        "These look like scraped fragments rather than genuine guest reviews. "
        "Consider dropping them from the dataset."
    )

    print("\nDone.")


if __name__ == "__main__":
    main()