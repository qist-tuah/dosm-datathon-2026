import pandas as pd
pd.set_option('display.max_colwidth', None)
pd.set_option('display.max_rows', None)

df = pd.read_csv('sample_data/clean_reviews_land_translated.csv', encoding='utf-8')
leftovers = df[df['translation_status'] == 'untranslated_no_method_available']

for idx, text in leftovers['text'].items():
    print(f"--- idx {idx} ---")
    print(repr(text))
    print()
