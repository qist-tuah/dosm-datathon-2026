import re
import time
import pandas as pd
import argostranslate.package
import argostranslate.translate
from langdetect import detect_langs, LangDetectException
from deep_translator import MyMemoryTranslator

IN_PATH = "sample_data/clean_reviews_marine.csv"
OUT_PATH = "sample_data/clean_reviews_marine_translated.csv"

MYMEMORY_EMAIL = "q.ist150302@gmail.com"
MYMEMORY_CHAR_LIMIT = 480
DAILY_CHAR_BUDGET_WARNING = 4500

QUOTA_WARNING_MARKERS = [
    "mymemory warning",
    "you used all available free translations",
    "query length limit exceeded",
    "invalid target language",
]

LANGDETECT_TO_ARGOS = {
    "zh-cn": "zh", "zh-tw": "zh", "ja": "ja", "ko": "ko", "th": "th",
    "ar": "ar", "ru": "ru", "vi": "vi", "id": "id", "ms": "ms",
    "fr": "fr", "de": "de", "es": "es", "pt": "pt", "it": "it",
    "nl": "nl", "tr": "tr", "pl": "pl", "uk": "uk", "hi": "hi",
    "bn": "bn", "fa": "fa", "he": "he", "el": "el", "cs": "cs",
    "sv": "sv", "fi": "fi", "da": "da", "no": "no", "ro": "ro",
    "hu": "hu", "bg": "bg", "sk": "sk", "hr": "hr", "sr": "sr",
    "en": "en",
}

SCRIPT_RANGES = [
    (0x4E00, 0x9FFF, "zh"), (0x3040, 0x30FF, "ja"), (0xAC00, 0xD7A3, "ko"),
    (0x0E00, 0x0E7F, "th"), (0x0600, 0x06FF, "ar"), (0x0400, 0x04FF, "ru"),
    (0x0900, 0x097F, "hi"), (0x0980, 0x09FF, "bn"),
]

STATUS_NO_CONTENT = "no_translatable_content"
STATUS_ALREADY_ENGLISH = "already_english"
STATUS_TRANSLATED_ARGOS = "translated_argos"
STATUS_TRANSLATED_MYMEMORY = "translated_mymemory"
STATUS_UNTRANSLATED = "untranslated_no_method_available"
STATUS_QUOTA_EXCEEDED = "untranslated_quota_exceeded"

REPETITION_CHAR_PATTERN = re.compile(r'(.)\1{4,}')
REPETITION_WORD_PATTERN = re.compile(r'(\S+)(\s+\1){3,}', re.UNICODE)

chars_sent_to_mymemory = 0


def needs_translation(text: str) -> bool:
    text = str(text)
    if len(text.strip()) == 0:
        return False
    try:
        detected = detect_langs(text)
        if detected and detected[0].lang == "en" and detected[0].prob > 0.85:
            return False
        return True
    except LangDetectException:
        return True


def is_translatable_content(text: str) -> bool:
    letters = re.findall(r"[^\W\d_]", text, flags=re.UNICODE)
    return len(letters) > 0


def looks_like_repetition_failure(text: str) -> bool:
    return bool(REPETITION_CHAR_PATTERN.search(text)) or bool(REPETITION_WORD_PATTERN.search(text))


def looks_like_quota_warning(text: str) -> bool:
    low = str(text).lower()
    return any(marker in low for marker in QUOTA_WARNING_MARKERS)


def script_guess(text: str):
    counts = {}
    for ch in text:
        cp = ord(ch)
        for lo, hi, code in SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[code] = counts.get(code, 0) + 1
                break
    return max(counts, key=counts.get) if counts else None


def candidate_lang_codes(text: str):
    candidates = []
    try:
        for guess in detect_langs(text):
            code = LANGDETECT_TO_ARGOS.get(guess.lang, guess.lang)
            if code not in candidates:
                candidates.append(code)
    except LangDetectException:
        pass
    script_code = script_guess(text)
    if script_code and script_code not in candidates:
        candidates.append(script_code)
    return candidates


def get_installed_languages():
    return {lang.code: lang for lang in argostranslate.translate.get_installed_languages()}


def ensure_package_installed(from_code: str, to_code: str = "en") -> bool:
    if from_code in get_installed_languages():
        return True
    available_packages = argostranslate.package.get_available_packages()
    pkg = next((p for p in available_packages if p.from_code == from_code and p.to_code == to_code), None)
    if pkg is None:
        return False
    print(f"  Downloading Argos model: {from_code} -> en (one-time)...")
    argostranslate.package.install_from_path(pkg.download())
    return True


def try_argos_translate(text: str, unavailable_langs: set):
    candidates = candidate_lang_codes(text)
    if not candidates:
        return None, None
    if candidates[0] == "en":
        return text, STATUS_ALREADY_ENGLISH
    for code in candidates:
        if code == "en" or code in unavailable_langs:
            continue
        if not ensure_package_installed(code, "en"):
            unavailable_langs.add(code)
            continue
        installed = get_installed_languages()
        from_lang, to_lang = installed.get(code), installed.get("en")
        if not from_lang or not to_lang:
            continue
        translation = from_lang.get_translation(to_lang)
        if translation is None:
            continue
        try:
            result = translation.translate(text)
            if looks_like_repetition_failure(result):
                continue
            return result, STATUS_TRANSLATED_ARGOS
        except Exception:
            continue
    return None, None


def translate_via_mymemory(text: str):
    global chars_sent_to_mymemory
    if len(text) > MYMEMORY_CHAR_LIMIT:
        return None, f"too_long_{len(text)}_chars", False
    try:
        kwargs = {"source": "auto", "target": "en-GB"}
        if MYMEMORY_EMAIL:
            kwargs["email"] = MYMEMORY_EMAIL
        result = MyMemoryTranslator(**kwargs).translate(text)
        chars_sent_to_mymemory += len(text)
        if looks_like_quota_warning(result):
            return None, "quota_warning_in_response", True
        return result, None, False
    except Exception as e:
        msg = str(e)
        if looks_like_quota_warning(msg):
            return None, msg, True
        return None, msg, False


def main():
    df = pd.read_csv(IN_PATH, encoding="utf-8")

    try:
        prior = pd.read_csv(OUT_PATH, encoding="utf-8")
        if len(prior) == len(df) and "translation_status" in prior.columns:
            df["text"] = prior["text"]
            df["translation_status"] = prior["translation_status"]
            df["failure_reason"] = prior.get("failure_reason", "")
            print("Resuming from previous partial run.")
        else:
            df["translation_status"] = "not_applicable"
            df["failure_reason"] = ""
    except FileNotFoundError:
        df["translation_status"] = "not_applicable"
        df["failure_reason"] = ""

    df["is_non_english"] = df["text"].apply(needs_translation)

    print("Updating Argos Translate package index...")
    argostranslate.package.update_package_index()

    unavailable_langs = set()
    to_translate = df[
        df["is_non_english"] & (df["translation_status"] == "not_applicable")
    ].index
    pending_for_mymemory = []

    print(f"Layers 1-3: processing {len(to_translate)} non-English reviews offline...")
    for i, idx in enumerate(to_translate):
        original = str(df.at[idx, "text"])
        if not is_translatable_content(original):
            df.at[idx, "translation_status"] = STATUS_NO_CONTENT
            continue
        translated, status = try_argos_translate(original, unavailable_langs)
        if translated is not None:
            df.at[idx, "text"] = translated
            df.at[idx, "translation_status"] = status
        else:
            pending_for_mymemory.append((idx, original))
        if (i + 1) % 50 == 0:
            print(f"  {i + 1}/{len(to_translate)} processed...")

    print(f"\nLayers 1-3 complete. {len(pending_for_mymemory)} rows need MyMemory.")

    quota_hit = False
    if pending_for_mymemory:
        print(f"Layer 4: sending up to {len(pending_for_mymemory)} rows to MyMemory...")
        for i, (idx, original) in enumerate(pending_for_mymemory):
            if quota_hit:
                df.at[idx, "translation_status"] = STATUS_QUOTA_EXCEEDED
                df.at[idx, "failure_reason"] = "skipped_after_quota_hit"
                continue

            result, err, hit_quota = translate_via_mymemory(original)
            if hit_quota:
                quota_hit = True
                df.at[idx, "translation_status"] = STATUS_QUOTA_EXCEEDED
                df.at[idx, "failure_reason"] = err
                print(f"  Quota appears exhausted at row {idx} "
                      f"(~{chars_sent_to_mymemory} chars sent this run). "
                      f"Saving progress -- rerun tomorrow to resume.")
                continue

            if result is not None and not looks_like_repetition_failure(result):
                df.at[idx, "text"] = result
                df.at[idx, "translation_status"] = STATUS_TRANSLATED_MYMEMORY
            else:
                df.at[idx, "translation_status"] = STATUS_UNTRANSLATED
                df.at[idx, "failure_reason"] = err or "repetition_failure"

            if chars_sent_to_mymemory > DAILY_CHAR_BUDGET_WARNING and not MYMEMORY_EMAIL:
                print(f"  WARNING: ~{chars_sent_to_mymemory} chars sent -- "
                      f"approaching the anonymous ~5000/day cap.")

            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(pending_for_mymemory)} sent "
                      f"({chars_sent_to_mymemory} chars used this run)...")
            time.sleep(1.0)

    df = df.drop(columns=["is_non_english"])
    df.to_csv(OUT_PATH, index=False, encoding="utf-8")

    print(f"\nDone. Saved -> {OUT_PATH}")
    print(f"Characters sent to MyMemory this run: {chars_sent_to_mymemory}")
    print("\nStatus breakdown:")
    print(df["translation_status"].value_counts())

    if quota_hit:
        print("\nQuota was hit partway through. Rerun this script tomorrow "
              "(or after adding MYMEMORY_EMAIL for a higher quota) -- "
              "it will resume from where it left off.")


if __name__ == "__main__":
    main()
