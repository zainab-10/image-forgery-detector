import os
from PIL import Image, ImageChops, ImageEnhance

def compute_ela(image_path, quality=90, scale=15):
    """Return an ELA image where tampered regions appear brighter."""
    original = Image.open(image_path).convert("RGB")

    # resave at a known JPEG quality into a temp file
    tmp = "_ela_tmp.jpg"
    original.save(tmp, "JPEG", quality=quality)
    resaved = Image.open(tmp)

    # pixel-wise difference between original and recompressed
    ela = ImageChops.difference(original, resaved)

    # the raw diff is very dark; scale it so edits are visible
    extrema = ela.getextrema()
    max_diff = max(e[1] for e in extrema) or 1
    scale_factor = 255.0 / max_diff
    ela = ImageEnhance.Brightness(ela).enhance(scale_factor * (scale / 15))

    os.remove(tmp)
    return ela

if __name__ == "__main__":
    import pandas as pd
    df = pd.read_csv("manifest.csv")

    # grab one authentic and one tampered to compare
    auth = df[df.label == 0].iloc[0]["path"]
    tamp = df[df.label == 1].iloc[0]["path"]

    compute_ela(auth).save("ela_authentic.png")
    compute_ela(tamp).save("ela_tampered.png")
    print("Saved ela_authentic.png and ela_tampered.png — open and compare")