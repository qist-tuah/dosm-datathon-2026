import re
import time
import pandas as pd
import argostranslate.package
import argostranslate.translate
from deep_translator import MyMemoryTranslator

ORIGINAL_PATH = "sample_data/clean_reviews_marine.csv"          # untouched source
TRANSLATED_PATH = "sample_data/clean_reviews_marine_translated.csv"  # to be fixed in place
BACKUP_PATH = "sample_data/clean_reviews_marine_translated_backup2.csv"

MYMEMORY_EMAIL = None  # <-- put your email here for a higher daily quota
MYMEMORY_CHAR_LIMIT = 480

# ---------------------------------------------------------------------------
# Row categories found during the audit
# ---------------------------------------------------------------------------

# 1) Too long for MyMemory's char limit -- 3 Spanish + 1 Japanese review.
#    Manually translated below.
TOO_LONG_ROWS = [83, 482, 1033, 1162]

# 2) Short CJK strings Argos silently failed to translate (still non-English
#    despite being marked translated_argos). Manually translated below.
SHORT_UNTRANSLATED_ROWS = [429, 477, 547, 668]

# 3) Likely non-review scraped noise (byline/fragment, not a guest review).
#    Flagged only -- script does not silently rewrite or drop these; decide
#    for yourself whether to keep, translate literally, or remove.
NOISE_ROWS = [636, 964]

# 4) Argos repetition-loop garbage (e.g. "mainstremainstremainstre...").
#    Re-translated below from the ORIGINAL text using a fixed detector.
GARBAGE_ARGOS_ROWS = [
    6, 8, 36, 57, 60, 65, 77, 90, 95, 134, 139, 145, 167, 233, 252, 354,
    377, 410, 449, 499, 550, 793, 829, 901, 938, 996, 997, 1001, 1034,
    1035, 1047, 1051, 1078, 1116,
]

# 5) MyMemory API error text ("'AUTO' IS AN INVALID SOURCE LANGUAGE...")
#    that was wrongly accepted as a valid translation. Re-translated below
#    from the ORIGINAL text using fixed error detection.
MYMEMORY_ERROR_ROWS = [
    123, 140, 184, 253, 445, 580, 612, 693, 707, 770, 904, 912, 993,
    1140, 1160, 1188,
]

# ---------------------------------------------------------------------------
# Fixed detectors (root-cause fixes for the two bugs above)
# ---------------------------------------------------------------------------

# Catches ANY short substring (1-40 chars) repeated 4+ times back to back,
# with or without whitespace between repeats -- unlike the original filter,
# this catches "mainstremainstremainstre..." with no separator.
REPETITION_PATTERN = re.compile(r'(.{1,40}?)\1{4,}', re.DOTALL)


def looks_like_repetition_failure(text: str) -> bool:
    return bool(REPETITION_PATTERN.search(str(text)))


# Expanded to catch the specific MyMemory error text that slipped through,
# plus other likely API-error phrasing.
ERROR_MARKERS = [
    "mymemory warning",
    "you used all available free translations",
    "query length limit exceeded",
    "invalid target language",
    "invalid source language",
    "is an invalid",
    "langpair=",
    "almost all languages supported but some may have no content",
]


def looks_like_error_response(text: str) -> bool:
    low = str(text).lower()
    return any(marker in low for marker in ERROR_MARKERS)


def is_bad_translation(text: str) -> bool:
    return looks_like_repetition_failure(text) or looks_like_error_response(text)


# ---------------------------------------------------------------------------
# Translation helpers
# ---------------------------------------------------------------------------

def mymemory_translate_once(text: str):
    kwargs = {"source": "auto", "target": "en-GB"}
    if MYMEMORY_EMAIL:
        kwargs["email"] = MYMEMORY_EMAIL
    return MyMemoryTranslator(**kwargs).translate(text)


def translate_long_text_chunked(text: str):
    """Split on sentence boundaries to stay under MyMemory's char limit,
    translate each chunk, then rejoin. Used for text too long to send
    in one call."""
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
            result = mymemory_translate_once(chunk)
            if is_bad_translation(result):
                out.append(f"[UNTRANSLATED: {chunk[:60]}...]")
            else:
                out.append(result)
        except Exception:
            out.append(f"[ERROR: {chunk[:60]}...]")
        time.sleep(1.0)
    return " ".join(out)


def try_argos_then_mymemory(text: str):
    """Re-attempt translation with the FIXED repetition/error detectors."""
    installed = {lang.code: lang for lang in argostranslate.translate.get_installed_languages()}
    en = installed.get("en")
    for code, lang in installed.items():
        if code == "en":
            continue
        translation = lang.get_translation(en) if en else None
        if translation is None:
            continue
        try:
            result = translation.translate(text)
            if result and not is_bad_translation(result) and result.strip() != text.strip():
                return result, "translated_manual_fix_argos"
        except Exception:
            continue

    if len(text) <= MYMEMORY_CHAR_LIMIT:
        try:
            result = mymemory_translate_once(text)
            if not is_bad_translation(result):
                return result, "translated_manual_fix_mymemory"
        except Exception:
            pass

    return translate_long_text_chunked(text), "translated_manual_fix_mymemory_chunked"


# ---------------------------------------------------------------------------
# Manual translations for the too-long and short-untranslated rows
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


def main():
    orig_df = pd.read_csv(ORIGINAL_PATH, encoding="utf-8")
    trans_df = pd.read_csv(TRANSLATED_PATH, encoding="utf-8")

    trans_df.to_csv(BACKUP_PATH, index=False, encoding="utf-8")
    print(f"Backup saved -> {BACKUP_PATH}\n")

    # --- Sanity check: confirm row alignment between the two files ---
    # Spot-check a row that should be untouched/identical in both files.
    sample_idx = 0
    print("Alignment check (row 0 should match between original and translated "
          "if it was English and untouched by translation):")
    print(f"  original : {str(orig_df.at[sample_idx, 'text'])[:80]}")
    print(f"  translated: {str(trans_df.at[sample_idx, 'text'])[:80]}\n")

    # --- 1 & 2: apply manual translations ---
    manual_rows = TOO_LONG_ROWS + SHORT_UNTRANSLATED_ROWS
    for idx in manual_rows:
        trans_df.at[idx, "text"] = MANUAL_TRANSLATIONS[idx]
        trans_df.at[idx, "translation_status"] = "translated_manual"
        trans_df.at[idx, "failure_reason"] = ""
        print(f"Row {idx}: applied manual translation.")

    # --- 4 & 5: re-translate from ORIGINAL text using fixed detectors ---
    rows_to_fix = GARBAGE_ARGOS_ROWS + MYMEMORY_ERROR_ROWS
    print(f"\nRe-translating {len(rows_to_fix)} rows from original source text "
          f"using fixed repetition/error detection...")
    for i, idx in enumerate(rows_to_fix):
        original_text = str(orig_df.at[idx, "text"])
        result, status = try_argos_then_mymemory(original_text)
        trans_df.at[idx, "text"] = result
        trans_df.at[idx, "translation_status"] = status
        trans_df.at[idx, "failure_reason"] = ""
        print(f"  [{i + 1}/{len(rows_to_fix)}] row {idx} -> {status}")
        print(f"    ORIGINAL: {original_text[:100]}")
        print(f"    NEW     : {str(result)[:100]}\n")

    trans_df.to_csv(TRANSLATED_PATH, index=False, encoding="utf-8")
    print(f"Saved -> {TRANSLATED_PATH}")

    # --- 3: flag noise rows, no automatic changes ---
    print("\n=== Rows flagged as likely non-review noise (unchanged -- your call) ===")
    for idx in NOISE_ROWS:
        print(f"Row {idx}: {trans_df.at[idx, 'text']!r}")
    print(
        "These look like scraped fragments (a place-name snippet and what "
        "appears to be an art-exhibit/travel-guide byline) rather than genuine "
        "guest reviews. Consider dropping them from the dataset rather than "
        "translating them as if they were reviews."
    )

    print("\nDone.")


if __name__ == "__main__":
    main()
