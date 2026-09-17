import pandas as pd

df = pd.read_csv("sample_data/clean_reviews_marine.csv", encoding="utf-8")

GARBAGE_ARGOS_ROWS = [6, 8, 36, 57, 60, 65, 77, 90, 95, 134, 139, 145, 167, 233, 252, 354, 377, 410, 449, 499, 550, 793, 829, 901, 938, 996, 997, 1001, 1034, 1035, 1047, 1051, 1078, 1116]
MYMEMORY_ERROR_ROWS = [123, 140, 184, 253, 445, 580, 612, 693, 707, 770, 904, 912, 993, 1140, 1160, 1188]

rows_needed = sorted(GARBAGE_ARGOS_ROWS + MYMEMORY_ERROR_ROWS)
subset = df.loc[rows_needed, ["text"]].copy()
subset.insert(0, "row_index", rows_needed)
subset.to_csv("sample_data/rows_for_manual_translation.csv", index=False, encoding="utf-8")
print(f"Saved {len(subset)} full-text rows -> sample_data/rows_for_manual_translation.csv")
