import os
import time
import warnings
import queue
from pathlib import Path

import streamlit as st
import torch
import torch.nn as nn
import torchvision.transforms as transforms
import torchvision.models as models
from PIL import Image

import cv2
import av
from streamlit_webrtc import webrtc_streamer, WebRtcMode, VideoTransformerBase
import gdown

warnings.filterwarnings("ignore")

# ---------------- UI basics ----------------
st.set_page_config(page_title="Face Scanner (Anti-Spoof)", page_icon=":shield:", layout="centered")

HIDE_STYLE = """
<style>
#MainMenu {visibility: hidden;}
footer {visibility: hidden;}
.block-container {padding-top: 1.5rem; padding-bottom: 1rem;}
</style>
"""
st.markdown(HIDE_STYLE, unsafe_allow_html=True)

st.title("🔒 Face Scanner — Anti-Spoof Classification (Streamlit)")

# --------------- Model loading (same head & weights contract as your code) ---------------
@st.cache_resource
def load_model(model_path: str):
    m = models.resnet50(weights=None)              # ไม่ต้องโหลด pretrained ตอนนี้ (เราจะโหลด state_dict)
    m.fc = nn.Sequential(
        nn.Linear(m.fc.in_features, 512),
        nn.BatchNorm1d(512),
        nn.ReLU(inplace=True),
        nn.Dropout(p=0.4),
        nn.Linear(512, 2)
    )
    ckpt = torch.load(model_path, map_location=torch.device("cpu"))
    # รองรับทั้งรูปแบบ {'model_state_dict': ...} หรือ state_dict ตรง ๆ
    state = ckpt.get("model_state_dict", ckpt.get("model_state", ckpt))
    m.load_state_dict(state)
    m.eval()
    return m

def download_model_from_drive(file_id: str, output_path: str):
    if not os.path.exists(output_path):
        with st.spinner("Downloading model from Google Drive..."):
            url = f"https://drive.google.com/uc?id={file_id}"
            gdown.download(url, output_path, quiet=False)

GDRIVE_FILE_ID = "1O-xajP2gfAmMLGkxrjmb_hfUMcAnbUZA"
MODEL_PATH = "Stage1_fix_ResNet50_CE_3Data_checkpoint_best_epoch_8"
download_model_from_drive(GDRIVE_FILE_ID, MODEL_PATH)
model = load_model(MODEL_PATH)

# Preprocess เหมือนเดิม
preprocess = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
    transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225]),
])

CLASS_NAMES = ["Deepfake", "Real"]

def predict_pil(pil_img: Image.Image):
    x = preprocess(pil_img).unsqueeze(0)
    with torch.no_grad():
        logits = model(x)
        probs = torch.softmax(logits, dim=1)
        conf, pred_idx = torch.max(probs, 1)
    return int(pred_idx.item()), float(conf.item())

# ---------------- Video processor (face detect + 3-2-1 countdown) ----------------
class FaceScanner(VideoTransformerBase):
    def __init__(self):
        self.face_cascade = cv2.CascadeClassifier(
            cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
        )
        self.detected_since = None
        self.countdown_secs = 3.0
        self.capture_ready = False
        self.captured_frame_bgr = None
        self.last_draw = 0

    def transform(self, frame: av.VideoFrame) -> av.VideoFrame:
        img = frame.to_ndarray(format="bgr24")
        gray = cv2.cvtColor(img, cv2.COLOR_BGR2GRAY)

        faces = self.face_cascade.detectMultiScale(
            gray, scaleFactor=1.1, minNeighbors=5, minSize=(120, 120)
        )

        now = time.time()
        color_box = (0, 255, 0) if len(faces) > 0 else (60, 60, 60)

        # วาดกรอบ (เลือกกล่องใหญ่สุด)
        if len(faces) > 0:
            areas = [w*h for (x, y, w, h) in faces]
            idx = int(max(range(len(areas)), key=lambda i: areas[i]))
            (x, y, w, h) = faces[idx]
            cv2.rectangle(img, (x, y), (x+w, y+h), color_box, 3)

            # เริ่ม/เดิน countdown
            if self.detected_since is None:
                self.detected_since = now

            elapsed = now - self.detected_since
            remaining = self.countdown_secs - elapsed

            if remaining <= 0 and not self.capture_ready:
                # จับภาพ
                self.captured_frame_bgr = img.copy()
                self.capture_ready = True
                self.detected_since = None
                cv2.putText(img, "Captured!", (x, max(30, y-10)),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.0, (0, 255, 255), 3, cv2.LINE_AA)
            else:
                # วาดตัวเลขถอยหลัง 3-2-1
                cnum = max(1, int(remaining + 0.999))  # 2.1->3, 1.1->2, 0.1->1
                cv2.putText(img, str(cnum), (x + w//2 - 20, y - 15),
                            cv2.FONT_HERSHEY_SIMPLEX, 1.4, (0, 255, 0), 3, cv2.LINE_AA)
        else:
            self.detected_since = None
            cv2.putText(img, "Align your face in the frame", (20, 30),
                        cv2.FONT_HERSHEY_SIMPLEX, 0.8, (200, 200, 200), 2, cv2.LINE_AA)

        return av.VideoFrame.from_ndarray(img, format="bgr24")

# ---------------- Layout ----------------
st.write("จัดหน้าให้กล้องอยู่ตรงกลาง ด้านล่างแสดงผลลัพธ์/สถานะ")

col = st.columns([1, 2, 1])
video_slot = col[1].container()

with st.sidebar:
    st.subheader("Options")
    score_thr = st.slider("Score threshold (show box/text only)", 0.1, 1.0, 0.5, 0.05)
    st.caption("หมายเหตุ: Haar cascade ไม่มี score ต่อกล่องแบบโมเดลลึก ค่านี้ใช้กำหนดความมั่นใจขั้นต่ำถ้าไปต่อยอดภายหลัง")

status_box = st.empty()
result_box = st.empty()
preview_box = st.empty()

# WebRTC streamer (กล้องสด)
ctx = webrtc_streamer(
    key="face-scanner",
    mode=WebRtcMode.SENDRECV,
    video_transformer_factory=FaceScanner,
    media_stream_constraints={"video": True, "audio": False},
    rtc_configuration={
        # ใช้ STUN ของ Google เพื่อให้ทำงานบนโฮสต์ระยะไกล/คลาวด์
        "iceServers": [{"urls": ["stun:stun.l.google.com:19302"]}]
    },
)

# ปุ่ม reset เพื่อถ่ายใหม่
reset = st.button("🔁 Retake")

if reset and ctx.video_transformer:
    ctx.video_transformer.capture_ready = False
    ctx.video_transformer.captured_frame_bgr = None
    result_box.empty()
    preview_box.empty()
    status_box.info("Ready. Center your face…")

# Loop เช็คว่ามีภาพที่ถูกจับแล้วหรือยัง
if ctx.video_transformer:
    if ctx.video_transformer.capture_ready and ctx.video_transformer.captured_frame_bgr is not None:
        # แปลง BGR -> RGB -> PIL
        bgr = ctx.video_transformer.captured_frame_bgr
        rgb = cv2.cvtColor(bgr, cv2.COLOR_BGR2RGB)
        pil = Image.fromarray(rgb)

        # แสดงพรีวิวภาพที่ใช้ตัดสิน
        preview_box.image(pil, caption="Captured frame", use_container_width=True)

        # ทำนาย
        pred_idx, conf = predict_pil(pil)
        label = CLASS_NAMES[pred_idx]

        # แสดงผล
        if label == "Real":
            result_box.success(f"✅ Prediction: {label}  |  Confidence: {conf:.2%}")
            st.balloons()
        else:
            result_box.error(f"⚠️ Prediction: {label}  |  Confidence: {conf:.2%}")

        # รีเซ็ตสถานะเพื่อรอครั้งถัดไป (ให้ผู้ใช้กด Retake หรือขยับหน้าออก-เข้าใหม่)
        ctx.video_transformer.capture_ready = False
        status_box.info("Captured. Press Retake to scan again.")
    else:
        status_box.info("Center your face. Capturing in 3…2…1 when detected.")
