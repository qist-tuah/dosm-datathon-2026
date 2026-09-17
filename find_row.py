import pandas as pd

df = pd.read_csv('sample_data/clean_reviews_land_translated.csv', encoding='utf-8')
match = df[df['text'].str.contains('鳥類拍照', na=False)]
print(match[['text', 'translation_status']])
