import pandas as pd
import re

df = pd.read_csv('sample_data/clean_reviews_land_translated.csv', encoding='utf-8')
argos_rows = df[df['translation_status'] == 'translated_argos']

# crude check: any row with CJK, Thai, Arabic, Cyrillic, etc. characters left in it
def has_non_latin(text):
    return bool(re.search(r'[\u4e00-\u9fff\u3040-\u30ff\uac00-\ud7a3\u0e00-\u0e7f\u0600-\u06ff\u0400-\u04ff\u0900-\u097f\u0980-\u09ff]', str(text)))

suspect = argos_rows[argos_rows['text'].apply(has_non_latin)]
print(f"{len(suspect)} rows marked translated_argos but still contain non-Latin script:\n")
print(suspect[['text']].to_string())
