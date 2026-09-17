"""
translate_reviews.py
------------------------
Layered, fully-free translation pipeline (no API keys, no billing account):
  0. Detect which rows need translation using actual language detection
     (langdetect), not an ASCII-character-ratio heuristic. Latin-script
     European languages (French, German, Italian, Spanish, etc.) are
     mostly ASCII and were being silently skipped by ratio-based checks.
  1. Strip emoji-only / punctuation-only text (not translatable, not a failure)
  2. Detect language via langdetect (top-N candidates), falling back to
     Unicode-script heuristics for short text langdetect can't handle
  3. Translate offline via Argos Translate (no rate limits, no network calls)
     - Output is validated for repetition-loop decoder failures; if detected,
       the row is treated as untranslated and falls through to Layer 4
  4. Anything Argos can't handle (or produced garbage for) gets a final
     pass through MyMemory (free, unauthenticated, ~5,000 chars/day)
"""

import re
import time
import pandas as pd
import argostranslate.package
import argostranslate.translate
from langdetect import detect_langs, LangDetectException
from deep_translator import MyMemoryTranslator

IN_PATH = "sample_data/clean_reviews_land.csv"
OUT_PATH = "sample_data/clean_reviews_land_translated.csv"

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

# Unicode script ranges -> Argos code, used when langdetect fails outright
# (typical for very short strings).
SCRIPT_RANGES = [
    (0x4E00, 0x9FFF, "zh"),     # CJK Unified Ideographs
    (0x3040, 0x30FF, "ja"),     # Hiragana + Katakana
    (0xAC00, 0xD7A3, "ko"),     # Hangul
    (0x0E00, 0x0E7F, "th"),     # Thai
    (0x0600, 0x06FF, "ar"),     # Arabic
    (0x0400, 0x04FF, "ru"),     # Cyrillic
    (0x0900, 0x097F, "hi"),     # Devanagari
    (0x0980, 0x09FF, "bn"),     # Bengali
]

STATUS_NO_CONTENT = "no_translatable_content"
STATUS_ALREADY_ENGLISH = "already_english"
STATUS_TRANSLATED_ARGOS = "translated_argos"
STATUS_TRANSLATED_MYMEMORY = "translated_mymemory"
STATUS_UNTRANSLATED = "untranslated_no_method_available"

# Detects decoder repetition-loop failures in Argos output: the same
# character repeated 5+ times in a row, or the same word/token repeated
# 4+ times separated by spaces (e.g. "island island island island").
REPETITION_CHAR_PATTERN = re.compile(r'(.)\1{4,}')
REPETITION_WORD_PATTERN = re.compile(r'(\S+)(\s+\1){3,}', re.UNICODE)


def needs_translation(text: str) -> bool:
    """Uses actual language detection instead of an ASCII-ratio heuristic.
    Latin-script European languages (French, German, Italian, Spanish,
    Vietnamese with diacritics, Polish, Czech, etc.) are mostly ASCII
    characters and were being silently skipped by a ratio-based check."""
    text = str(text)
    if len(text.strip()) == 0:
        return False
    try:
        detected = detect_langs(text)
        if detected and detected[0].lang == "en" and detected[0].prob > 0.85:
            return False
        return True
    except LangDetectException:
        # Can't detect at all (often very short strings) -> let it through
        # so the script-guess fallback and content check downstream can decide.
        return True


def is_translatable_content(text: str) -> bool:
    """False for emoji-only / punctuation-only / whitespace-only strings."""
    letters = re.findall(r"[^\W\d_]", text, flags=re.UNICODE)
    return len(letters) > 0


def looks_like_repetition_failure(text: str) -> bool:
    """Detects Argos decoder repetition-loop failures in translated output."""
    if REPETITION_CHAR_PATTERN.search(text):
        return True
    if REPETITION_WORD_PATTERN.search(text):
        return True
    return False


def script_guess(text: str):
    counts = {}
    for ch in text:
        cp = ord(ch)
        for lo, hi, code in SCRIPT_RANGES:
            if lo <= cp <= hi:
                counts[code] = counts.get(code, 0) + 1
                break
    if not counts:
        return None
    return max(counts, key=counts.get)


def candidate_lang_codes(text: str):
    """Ranked list of Argos-code guesses for this text."""
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
    pkg = next(
        (p for p in available_packages if p.from_code == from_code and p.to_code == to_code),
        None,
    )
    if pkg is None:
        return False
    print(f"  Downloading Argos model: {from_code} -> en (one-time)...")
    argostranslate.package.install_from_path(pkg.download())
    return True


def try_argos_translate(text: str, unavailable_langs: set):
    """Returns (translated_text_or_None, status_or_None)."""
    candidates = candidate_lang_codes(text)

    if not candidates:
        return None, None  # couldn't even guess -> queue for MyMemory

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
                # Argos got stuck in a decoder loop; treat as a failure
                # and try the next candidate language, if any.
                continue
            return result, STATUS_TRANSLATED_ARGOS
        except Exception:
            continue

    return None, None  # every candidate failed -> queue for MyMemory


def translate_via_mymemory(text: str):
    try:
        return MyMemoryTranslator(source="auto", target="en").translate(text)
    except Exception as e:
        print(f"  MyMemory failed on this row ({e})")
        return None


def main():
    df = pd.read_csv(IN_PATH, encoding="utf-8")
    df["is_non_english"] = df["text"].apply(needs_translation)
    df["translation_status"] = "not_applicable"

    print("Updating Argos Translate package index...")
    argostranslate.package.update_package_index()

    unavailable_langs = set()
    to_translate = df[df["is_non_english"]].index
    pending_for_mymemory = []  # (idx, original_text)

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

        if (i + 1) % 20 == 0:
            print(f"  {i + 1}/{len(to_translate)} processed...")

    print(f"\nLayers 1-3 complete. {len(pending_for_mymemory)} rows still untranslated.")

    if pending_for_mymemory:
        print(f"Layer 4: sending {len(pending_for_mymemory)} residual rows to MyMemory...")
        for i, (idx, original) in enumerate(pending_for_mymemory):
            result = translate_via_mymemory(original)
            if result is not None and not looks_like_repetition_failure(result):
                df.at[idx, "text"] = result
                df.at[idx, "translation_status"] = STATUS_TRANSLATED_MYMEMORY
            else:
                df.at[idx, "translation_status"] = STATUS_UNTRANSLATED
            if (i + 1) % 10 == 0:
                print(f"  {i + 1}/{len(pending_for_mymemory)} sent to MyMemory...")
            time.sleep(1.0)  # stay well under MyMemory's daily quota pacing

    df = df.drop(columns=["is_non_english"])
    df.to_csv(OUT_PATH, index=False, encoding="utf-8")

    print(f"\nDone. Saved -> {OUT_PATH}")
    print("\nStatus breakdown:")
    print(df["translation_status"].value_counts())


if __name__ == "__main__":
    main()