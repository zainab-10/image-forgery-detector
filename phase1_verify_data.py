import os
from PIL import Image

# EDIT these to match where your Au and Tp folders actually landed
AU = r"D:\\zainab\\forgery-detector\\data\\CASIA2\\Au"
TP = r"D:\zainab\\forgery-detector\\data\\CASIA2\\Tp"

for name, path in [("Authentic", AU), ("Tampered", TP)]:
    if not os.path.isdir(path):
        print(f"[MISSING] {name} folder not found at: {path}")
        continue
    files = [f for f in os.listdir(path)
             if f.lower().endswith((".jpg", ".jpeg", ".png", ".tif", ".bmp"))]
    print(f"{name}: {len(files)} images")
    # try opening the first one to confirm it's readable
    if files:
        img = Image.open(os.path.join(path, files[0]))
        print(f"   sample: {files[0]}  size={img.size}  mode={img.mode}")