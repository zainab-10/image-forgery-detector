import os
import pandas as pd
from PIL import Image, ImageChops, ImageEnhance
from tqdm import tqdm

CACHE = r"D:\\zainab\\forgery-detector\\data\\ela_cache"
os.makedirs(CACHE, exist_ok=True)

def compute_ela(path, quality=90):
    original = Image.open(path).convert("RGB")
    tmp = "_pp_tmp.jpg"
    original.save(tmp, "JPEG", quality=quality)
    resaved = Image.open(tmp)
    ela = ImageChops.difference(original, resaved)
    extrema = ela.getextrema()
    max_diff = max(e[1] for e in extrema) or 1
    ela = ImageEnhance.Brightness(ela).enhance(255.0 / max_diff)
    os.remove(tmp)
    return ela

df = pd.read_csv("manifest.csv")
rows = []
for i, r in tqdm(df.iterrows(), total=len(df)):
    out_name = f"{i}_{r.label}.png"
    out_path = os.path.join(CACHE, out_name)
    if not os.path.exists(out_path):
        try:
            compute_ela(r["path"]).resize((224, 224)).save(out_path)
        except Exception as e:
            print(f"skip {r['path']}: {e}")
            continue
    rows.append({"path": out_path, "label": r.label})

pd.DataFrame(rows).to_csv("manifest_ela.csv", index=False)
print(f"Done. {len(rows)} ELA images cached -> manifest_ela.csv")