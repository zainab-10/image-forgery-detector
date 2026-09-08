import numpy as np
import torch
import torch.nn as nn
import cv2
from torchvision import models, transforms
from PIL import Image, ImageChops, ImageEnhance

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ---- rebuild the model and load trained weights ----
model = models.resnet18(weights=None)
model.fc = nn.Linear(model.fc.in_features, 2)
model.load_state_dict(torch.load("best_model.pth", map_location=device))
model = model.to(device).eval()

# ---- same ELA + normalization used in training ----
norm = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
tfm = transforms.Compose([transforms.ToTensor(), norm])

def compute_ela(path, quality=90):
    original = Image.open(path).convert("RGB")
    tmp = "_gc_tmp.jpg"
    original.save(tmp, "JPEG", quality=quality)
    resaved = Image.open(tmp)
    ela = ImageChops.difference(original, resaved)
    max_diff = max(e[1] for e in ela.getextrema()) or 1
    ela = ImageEnhance.Brightness(ela).enhance(255.0 / max_diff)
    import os; os.remove(tmp)
    return ela.resize((224, 224))

# ---- hook the last conv block to capture activations + gradients ----
feats, grads = {}, {}
def fwd_hook(m, i, o): feats["v"] = o.detach()
def bwd_hook(m, gi, go): grads["v"] = go[0].detach()

target_layer = model.layer4[-1]           # last residual block
target_layer.register_forward_hook(fwd_hook)
target_layer.register_full_backward_hook(bwd_hook)

def gradcam(image_path, out_path="gradcam_result.png"):
    ela = compute_ela(image_path)
    x = tfm(ela.convert("RGB")).unsqueeze(0).to(device)

    logits = model(x)
    prob_tampered = torch.softmax(logits, 1)[0, 1].item()

    model.zero_grad()
    logits[0, 1].backward()               # backprop the "tampered" score

    # weight each feature map by its averaged gradient, then combine
    g = grads["v"][0]                      # [C,H,W]
    f = feats["v"][0]                      # [C,H,W]
    weights = g.mean(dim=(1, 2))           # importance per channel
    cam = torch.relu((weights[:, None, None] * f).sum(0))
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    cam = cam.cpu().numpy()

    # overlay heatmap on the ORIGINAL image
    orig = cv2.cvtColor(np.array(Image.open(image_path).convert("RGB")), cv2.COLOR_RGB2BGR)
    h, w = orig.shape[:2]
    cam = cv2.resize(cam, (w, h))
    heat = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(orig, 0.6, heat, 0.4, 0)

    cv2.imwrite(out_path, overlay)
    print(f"tamper probability: {prob_tampered:.3f}  -> saved {out_path}")
    return prob_tampered

if __name__ == "__main__":
    import pandas as pd
    df = pd.read_csv("manifest.csv")
    tamp = df[df.label == 1].iloc[0]["path"]
    auth = df[df.label == 0].iloc[0]["path"]
    gradcam(tamp, "gradcam_tampered.png")
    gradcam(auth, "gradcam_authentic.png")