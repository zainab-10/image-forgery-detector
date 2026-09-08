# import os
# import numpy as np
# import torch
# import torch.nn as nn
# import cv2
# import streamlit as st
# import plotly.graph_objects as go
# from torchvision import models, transforms
# from PIL import Image, ImageChops, ImageEnhance
# from PIL.ExifTags import TAGS

# st.set_page_config(page_title="Forgery Detector", layout="wide")
# device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# # ---------- load model once, cached ----------
# @st.cache_resource
# def load_model():
#     m = models.resnet18(weights=None)
#     m.fc = nn.Linear(m.fc.in_features, 2)
#     m.load_state_dict(torch.load("best_model.pth", map_location=device, weights_only=True))
#     return m.to(device).eval()

# model = load_model()
# norm = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
# tfm = transforms.Compose([transforms.ToTensor(), norm])

# # ---------- detectors ----------
# def compute_ela(pil_img, quality=90):
#     tmp = "_app_tmp.jpg"
#     pil_img.convert("RGB").save(tmp, "JPEG", quality=quality)
#     resaved = Image.open(tmp)
#     ela = ImageChops.difference(pil_img.convert("RGB"), resaved)
#     max_diff = max(e[1] for e in ela.getextrema()) or 1
#     ela = ImageEnhance.Brightness(ela).enhance(255.0 / max_diff)
#     os.remove(tmp)
#     return ela

# feats, grads = {}, {}
# model.layer4[-1].register_forward_hook(lambda m, i, o: feats.__setitem__("v", o.detach()))
# model.layer4[-1].register_full_backward_hook(lambda m, gi, go: grads.__setitem__("v", go[0].detach()))

# def cnn_and_gradcam(pil_img):
#     ela = compute_ela(pil_img).resize((224, 224)).convert("RGB")
#     x = tfm(ela).unsqueeze(0).to(device)
#     logits = model(x)
#     prob = torch.softmax(logits, 1)[0, 1].item()
#     model.zero_grad()
#     logits[0, 1].backward()
#     g, f = grads["v"][0], feats["v"][0]
#     w = g.mean(dim=(1, 2))
#     cam = torch.relu((w[:, None, None] * f).sum(0))
#     cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
#     cam = cam.cpu().numpy()
#     orig = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
#     h, wd = orig.shape[:2]
#     cam = cv2.resize(cam, (wd, h))
#     heat = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
#     overlay = cv2.addWeighted(orig, 0.6, heat, 0.4, 0)
#     return prob, cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)

# def copy_move(pil_img, min_dist=40):
#     img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
#     gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
#     orb = cv2.ORB_create(nfeatures=2000)
#     kp, des = orb.detectAndCompute(gray, None)
#     if des is None or len(kp) < 2:
#         return img[:, :, ::-1], 0
#     bf = cv2.BFMatcher(cv2.NORM_HAMMING)
#     matches = bf.knnMatch(des, des, k=3)
#     good = []
#     for ms in matches:
#         for m in ms:
#             if m.queryIdx == m.trainIdx:
#                 continue
#             p1, p2 = np.array(kp[m.queryIdx].pt), np.array(kp[m.trainIdx].pt)
#             if m.distance < 40 and np.linalg.norm(p1 - p2) > min_dist:
#                 good.append((kp[m.queryIdx], kp[m.trainIdx]))
#     out = img.copy()
#     for k1, k2 in good[:200]:
#         cv2.line(out, tuple(map(int, k1.pt)), tuple(map(int, k2.pt)), (0, 0, 255), 1)
#     return out[:, :, ::-1], len(good)

# def check_exif(pil_img):
#     flags = []
#     exif = pil_img._getexif() if hasattr(pil_img, "_getexif") else None
#     if not exif:
#         return ["No EXIF metadata (stripped or never present)"]
#     r = {TAGS.get(k, k): v for k, v in exif.items()}
#     sw = str(r.get("Software", "")).lower()
#     for h in ["photoshop", "gimp", "lightroom", "affinity"]:
#         if h in sw:
#             flags.append(f"Edited with: {r.get('Software')}")
#     if not r.get("Make") and not r.get("Model"):
#         flags.append("No camera make/model")
#     return flags or ["No obvious metadata anomalies"]

# def gauge(prob):
#     fig = go.Figure(go.Indicator(
#         mode="gauge+number", value=prob * 100,
#         title={"text": "Tamper probability (%)"},
#         gauge={"axis": {"range": [0, 100]},
#                "bar": {"color": "darkred" if prob > 0.5 else "green"},
#                "steps": [{"range": [0, 50], "color": "#d9f0d9"},
#                          {"range": [50, 100], "color": "#f0d9d9"}]}))
#     fig.update_layout(height=300)
#     return fig

# # ---------- UI ----------
# st.title("Document Forgery / Tampering Detector")
# st.caption("ELA + copy-move + EXIF + CNN (ResNet18 on ELA)")

# up = st.file_uploader("Upload an image", type=["jpg", "jpeg", "png", "tif", "bmp"])
# if up:
#     pil = Image.open(up)
#     prob, cam = cnn_and_gradcam(pil)
#     cm_img, cm_n = copy_move(pil)
#     exif_flags = check_exif(pil)

#     st.plotly_chart(gauge(prob), use_container_width=True)
#     verdict = "LIKELY TAMPERED" if prob > 0.5 else "LIKELY AUTHENTIC"
#     st.subheader(f"Verdict: {verdict}  ({prob*100:.1f}%)")

#     c1, c2 = st.columns(2)
#     with c1:
#         st.image(pil, caption="Original", use_container_width=True)
#         st.image(compute_ela(pil), caption="Error Level Analysis", use_container_width=True)
#     with c2:
#         st.image(cam, caption="Grad-CAM heatmap (where the model looked)", use_container_width=True)
#         st.image(cm_img, caption=f"Copy-move matches: {cm_n}", use_container_width=True)

#     st.write("**EXIF flags:**")
#     for f in exif_flags:
#         st.write("- " + f)
#     st.info("Signals are complementary. CNN probability is primary; "
#             "ELA, copy-move and EXIF are supporting evidence and can be weak on some images.")
import os
import numpy as np
import torch
import torch.nn as nn
import cv2
import streamlit as st
import plotly.graph_objects as go
from torchvision import models, transforms
from PIL import Image, ImageChops, ImageEnhance
from PIL.ExifTags import TAGS

# ----------------------------------------------------------------------
# Page config
# ----------------------------------------------------------------------
st.set_page_config(
    page_title="Forgery Detector",
    page_icon="🔍",
    layout="wide",
    initial_sidebar_state="collapsed",
)

device = torch.device("cuda" if torch.cuda.is_available() else "cpu")

# ----------------------------------------------------------------------
# Styling — dark forensic instrument panel
# ----------------------------------------------------------------------
st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@500;600&display=swap');

:root{
  --bg:#0d1117;
  --panel:#161b22;
  --panel-edge:#243040;
  --ink:#e6edf3;
  --muted:#8b98a5;
  --amber:#f0a202;
  --teal:#3fb6a8;
  --danger:#e5484d;
}

.stApp{
  background:
    radial-gradient(1100px 600px at 15% -10%, #16233a 0%, rgba(22,35,58,0) 55%),
    radial-gradient(900px 500px at 100% 0%, #1a2030 0%, rgba(26,32,48,0) 50%),
    linear-gradient(180deg, #0d1117 0%, #0a0e14 100%);
  background-attachment: fixed;
  color:var(--ink);
  font-family:'IBM Plex Sans',sans-serif;
}

/* hide default streamlit chrome */
#MainMenu, footer, header {visibility:hidden;}
.block-container{padding-top:2.2rem; padding-bottom:3rem; max-width:1180px;}

/* ---- hero ---- */
.hero-eyebrow{
  font-family:'IBM Plex Mono',monospace;
  font-size:.72rem; letter-spacing:.28em; color:var(--muted);
  text-transform:uppercase; margin-bottom:.4rem;
}
.hero-title{
  font-size:2.6rem; font-weight:700; line-height:1.05;
  margin:0 0 .5rem 0; color:var(--ink);
}
.hero-sub{ color:var(--muted); font-size:1rem; max-width:60ch; }
.rule{ height:1px; background:linear-gradient(90deg,var(--panel-edge),transparent);
  margin:1.6rem 0 2rem 0; }

/* ---- verdict banner ---- */
.verdict{
  border-radius:16px; padding:1.4rem 1.6rem; margin:.4rem 0 1.2rem 0;
  border:1px solid var(--panel-edge); background:var(--panel);
  display:flex; align-items:center; gap:1.2rem;
}
.verdict.tampered{ border-left:5px solid var(--amber);
  box-shadow:inset 0 0 60px rgba(240,162,2,.06); }
.verdict.authentic{ border-left:5px solid var(--teal);
  box-shadow:inset 0 0 60px rgba(63,182,168,.06); }
.verdict-dot{ width:14px; height:14px; border-radius:50%; }
.verdict.tampered .verdict-dot{ background:var(--amber); box-shadow:0 0 14px var(--amber);}
.verdict.authentic .verdict-dot{ background:var(--teal); box-shadow:0 0 14px var(--teal);}
.verdict-label{ font-size:1.5rem; font-weight:700; }
.verdict-score{ font-family:'IBM Plex Mono',monospace; color:var(--muted);
  font-size:.95rem; margin-top:.15rem; }

/* ---- panels ---- */
.panel-cap{
  font-family:'IBM Plex Mono',monospace; font-size:.74rem;
  letter-spacing:.14em; color:var(--muted); text-transform:uppercase;
  margin:.2rem 0 .5rem 0;
}
.stImage img{ border-radius:12px; border:1px solid var(--panel-edge); }

/* ---- evidence chips ---- */
.chip{
  display:inline-block; font-family:'IBM Plex Mono',monospace;
  font-size:.8rem; padding:.35rem .7rem; border-radius:999px;
  border:1px solid var(--panel-edge); background:var(--panel);
  color:var(--ink); margin:.2rem .35rem .2rem 0;
}
.chip .k{ color:var(--muted); }

/* uploader */
[data-testid="stFileUploader"]{
  background:var(--panel); border:1px dashed var(--panel-edge);
  border-radius:14px; padding:.6rem;
}
.note{ color:var(--muted); font-size:.85rem; border-left:2px solid var(--panel-edge);
  padding-left:.8rem; margin-top:1.4rem; }
</style>
""", unsafe_allow_html=True)

# ----------------------------------------------------------------------
# Model
# ----------------------------------------------------------------------
@st.cache_resource
def load_model():
    m = models.resnet18(weights=None)
    m.fc = nn.Linear(m.fc.in_features, 2)
    m.load_state_dict(torch.load("best_model.pth", map_location=device, weights_only=True))
    return m.to(device).eval()

model = load_model()
norm = transforms.Normalize([0.485, 0.456, 0.406], [0.229, 0.224, 0.225])
tfm = transforms.Compose([transforms.ToTensor(), norm])

# hooks for grad-cam
feats, grads = {}, {}
model.layer4[-1].register_forward_hook(lambda m, i, o: feats.__setitem__("v", o.detach()))
model.layer4[-1].register_full_backward_hook(lambda m, gi, go: grads.__setitem__("v", go[0].detach()))

# ----------------------------------------------------------------------
# Detectors
# ----------------------------------------------------------------------
def compute_ela(pil_img, quality=90):
    tmp = "_app_tmp.jpg"
    pil_img.convert("RGB").save(tmp, "JPEG", quality=quality)
    resaved = Image.open(tmp)
    ela = ImageChops.difference(pil_img.convert("RGB"), resaved)
    max_diff = max(e[1] for e in ela.getextrema()) or 1
    ela = ImageEnhance.Brightness(ela).enhance(255.0 / max_diff)
    os.remove(tmp)
    return ela

def cnn_and_gradcam(pil_img):
    ela = compute_ela(pil_img).resize((224, 224)).convert("RGB")
    x = tfm(ela).unsqueeze(0).to(device)
    logits = model(x)
    prob = torch.softmax(logits, 1)[0, 1].item()
    model.zero_grad()
    logits[0, 1].backward()
    g, f = grads["v"][0], feats["v"][0]
    w = g.mean(dim=(1, 2))
    cam = torch.relu((w[:, None, None] * f).sum(0))
    cam = (cam - cam.min()) / (cam.max() - cam.min() + 1e-8)
    cam = cam.cpu().numpy()
    orig = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
    h, wd = orig.shape[:2]
    cam = cv2.resize(cam, (wd, h))
    heat = cv2.applyColorMap((cam * 255).astype(np.uint8), cv2.COLORMAP_JET)
    overlay = cv2.addWeighted(orig, 0.6, heat, 0.4, 0)
    return prob, cv2.cvtColor(overlay, cv2.COLOR_BGR2RGB)

def copy_move(pil_img, min_dist=40):
    img = cv2.cvtColor(np.array(pil_img.convert("RGB")), cv2.COLOR_RGB2BGR)
    gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)
    orb = cv2.ORB_create(nfeatures=2000)
    kp, des = orb.detectAndCompute(gray, None)
    if des is None or len(kp) < 2:
        return img[:, :, ::-1], 0
    bf = cv2.BFMatcher(cv2.NORM_HAMMING)
    matches = bf.knnMatch(des, des, k=3)
    good = []
    for ms in matches:
        for m in ms:
            if m.queryIdx == m.trainIdx:
                continue
            p1, p2 = np.array(kp[m.queryIdx].pt), np.array(kp[m.trainIdx].pt)
            if m.distance < 40 and np.linalg.norm(p1 - p2) > min_dist:
                good.append((kp[m.queryIdx], kp[m.trainIdx]))
    out = img.copy()
    for k1, k2 in good[:200]:
        cv2.line(out, tuple(map(int, k1.pt)), tuple(map(int, k2.pt)), (0, 0, 255), 1)
    return out[:, :, ::-1], len(good)

def check_exif(pil_img):
    flags = []
    exif = pil_img._getexif() if hasattr(pil_img, "_getexif") else None
    if not exif:
        return ["No EXIF metadata (stripped or never present)"]
    r = {TAGS.get(k, k): v for k, v in exif.items()}
    sw = str(r.get("Software", "")).lower()
    for h in ["photoshop", "gimp", "lightroom", "affinity"]:
        if h in sw:
            flags.append(f"Edited with: {r.get('Software')}")
    if not r.get("Make") and not r.get("Model"):
        flags.append("No camera make/model")
    return flags or ["No obvious metadata anomalies"]

def gauge(prob):
    tampered = prob > 0.5
    color = "#f0a202" if tampered else "#3fb6a8"
    fig = go.Figure(go.Indicator(
        mode="gauge+number",
        value=prob * 100,
        number={"suffix": "%", "font": {"size": 40,
                "color": "#e6edf3", "family": "IBM Plex Mono"}},
        gauge={
            "axis": {"range": [0, 100], "tickcolor": "#8b98a5",
                     "tickfont": {"color": "#8b98a5", "size": 11}},
            "bar": {"color": color, "thickness": 0.28},
            "bgcolor": "rgba(0,0,0,0)",
            "borderwidth": 0,
            "steps": [
                {"range": [0, 50], "color": "rgba(63,182,168,.12)"},
                {"range": [50, 100], "color": "rgba(240,162,2,.12)"},
            ],
            "threshold": {"line": {"color": "#e5484d", "width": 2},
                          "thickness": 0.75, "value": 50},
        },
    ))
    fig.update_layout(height=260, margin=dict(l=20, r=20, t=10, b=10),
                      paper_bgcolor="rgba(0,0,0,0)", font={"color": "#e6edf3"})
    return fig

# ----------------------------------------------------------------------
# Hero
# ----------------------------------------------------------------------
st.markdown("""
<div class="hero-eyebrow">Image forensics · ELA · copy-move · CNN</div>
<div class="hero-title">Document Forgery &amp; Tampering Detector</div>
<div class="hero-sub">Upload an image to check whether it has been spliced, cloned, or
digitally edited. A ResNet18 model trained on error-level-analysis drives the verdict,
backed by classical forensic signals.</div>
<div class="rule"></div>
""", unsafe_allow_html=True)

up = st.file_uploader("Upload an image to analyze",
                      type=["jpg", "jpeg", "png", "tif", "bmp"])

if not up:
    st.markdown("""
    <div class="note">
    Tip: upload an original photo, not a screenshot or a re-saved copy —
    re-compression changes the error-level signature and can skew the score.
    </div>""", unsafe_allow_html=True)
    st.stop()

pil = Image.open(up)
with st.spinner("Analyzing…"):
    prob, cam = cnn_and_gradcam(pil)
    ela_img = compute_ela(pil)
    cm_img, cm_n = copy_move(pil)
    exif_flags = check_exif(pil)

tampered = prob > 0.5
cls = "tampered" if tampered else "authentic"
label = "Likely tampered" if tampered else "Likely authentic"

# ---- verdict + gauge ----
left, right = st.columns([1.15, 1])
with left:
    st.markdown(f"""
    <div class="verdict {cls}">
      <div class="verdict-dot"></div>
      <div>
        <div class="verdict-label">{label}</div>
        <div class="verdict-score">tamper probability &nbsp;{prob*100:.1f}%
        &nbsp;·&nbsp; confidence {abs(prob-0.5)*2*100:.0f}%</div>
      </div>
    </div>
    """, unsafe_allow_html=True)
    st.markdown(f"""
    <span class="chip"><span class="k">copy-move matches</span> &nbsp;{cm_n}</span>
    <span class="chip"><span class="k">exif</span> &nbsp;{exif_flags[0]}</span>
    """, unsafe_allow_html=True)
with right:
    st.plotly_chart(gauge(prob), use_container_width=True,
                    config={"displayModeBar": False})

st.markdown('<div class="rule"></div>', unsafe_allow_html=True)

# ---- evidence grid ----
c1, c2 = st.columns(2)
with c1:
    st.markdown('<div class="panel-cap">Original</div>', unsafe_allow_html=True)
    st.image(pil, use_container_width=True)
    st.markdown('<div class="panel-cap">Error level analysis</div>', unsafe_allow_html=True)
    st.image(ela_img, use_container_width=True)
with c2:
    st.markdown('<div class="panel-cap">Grad-CAM · where the model looked</div>',
                unsafe_allow_html=True)
    st.image(cam, use_container_width=True)
    st.markdown('<div class="panel-cap">Copy-move keypoint matches</div>',
                unsafe_allow_html=True)
    st.image(cm_img, use_container_width=True)

st.markdown("""
<div class="note">
The CNN probability is the primary signal. Error-level analysis, copy-move detection,
and EXIF checks are supporting evidence — each can be quiet on images that were stripped
of metadata or saved without a clear edit trail. Read the signals together, not in isolation.
</div>
""", unsafe_allow_html=True)