import os
import pandas as pd

AU = r"D:\\zainab\\forgery-detector\\data\\CASIA2\\Au"
TP = r"D:\\zainab\\forgery-detector\\data\\CASIA2\\Tp"

EXTS = (".jpg", ".jpeg", ".png", ".tif", ".bmp")

rows = []
for f in os.listdir(AU):
    if f.lower().endswith(EXTS):
        rows.append({"path": os.path.join(AU, f), "label": 0})
for f in os.listdir(TP):
    if f.lower().endswith(EXTS):
        rows.append({"path": os.path.join(TP, f), "label": 1})

df = pd.DataFrame(rows)
df = df.sample(frac=1, random_state=42).reset_index(drop=True)  # shuffle
df.to_csv("manifest.csv", index=False)

print("Total images:", len(df))
print(df["label"].value_counts())
print(df.head())