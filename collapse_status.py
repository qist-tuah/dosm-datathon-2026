import pandas as pd

df = pd.read_csv('sample_data/clean_reviews_land_translated.csv', encoding='utf-8')
df['translation_status'] = df['translation_status'].replace({
    'already_english_missed': 'already_english',
    'no_translation_needed': 'already_english',
})
df.to_csv('sample_data/clean_reviews_land_translated.csv', index=False, encoding='utf-8')
print(df['translation_status'].value_counts())
