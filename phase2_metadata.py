from PIL import Image
from PIL.ExifTags import TAGS

EDITOR_HINTS = ["photoshop", "gimp", "lightroom", "affinity", "paint.net", "pixelmator"]

def check_metadata(image_path):
    """Return a list of human-readable metadata flags."""
    flags = []
    try:
        img = Image.open(image_path)
    except Exception as e:
        return [f"Could not open image: {e}"]

    exif = None
    if hasattr(img, "_getexif"):
        exif = img._getexif()

    if not exif:
        flags.append("No EXIF metadata present (stripped or never had any)")
        return flags

    readable = {TAGS.get(k, k): v for k, v in exif.items()}

    sw = str(readable.get("Software", "")).lower()
    for hint in EDITOR_HINTS:
        if hint in sw:
            flags.append(f"Edited with software: {readable.get('Software')}")
            break

    dt_orig = readable.get("DateTimeOriginal")
    dt_mod = readable.get("DateTime")
    if dt_orig and dt_mod and dt_orig != dt_mod:
        flags.append(f"Timestamp mismatch: original {dt_orig} vs modified {dt_mod}")

    if not readable.get("Make") and not readable.get("Model"):
        flags.append("No camera make/model (unusual for an original photo)")

    if not flags:
        flags.append("No obvious metadata anomalies")
    return flags

if __name__ == "__main__":
    import pandas as pd
    df = pd.read_csv("manifest.csv")
    for label, name in [(0, "AUTHENTIC"), (1, "TAMPERED")]:
        p = df[df.label == label].iloc[0]["path"]
        print(f"\n{name}: {p}")
        for f in check_metadata(p):
            print("  -", f)