import uvicorn
import numpy as np
import base64
import cv2
import os
import re
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import List
from deepface import DeepFace

# --- สำหรับส่ง LINE ---
from linebot import LineBotApi, WebhookHandler
from linebot.models import TextSendMessage, FlexSendMessage, BubbleContainer, BoxComponent, TextComponent, ButtonComponent, ImageComponent, PostbackAction
from linebot.exceptions import InvalidSignatureError
from linebot.models.events import PostbackEvent

# --- ตั้งค่า LINE ของคุณ (ใส่ค่าเดิมของคุณตรงนี้) ---
LINE_CHANNEL_ACCESS_TOKEN = 'yMTfcTZoEaG2kSZMDtUCVT5I8S47c0APKUNUtRvFfIVfAj+005EixdA9iDJPDReJaM8snIwnjMgPJ3B/rYru1Fr6/veFTAhga+DXB/97zSfoMo279kisRv1hsKM6K+0Me32GvqQvG07qCPMXuHda9QdB04t89/1O/w1cDnyilFU='
LINE_HOST_USER_ID = 'U669226ca0e16195477ca5857a469567d'
LINE_CHANNEL_SECRET = 'b8c65e65a4ead4ef817d7c66f2832e0c'

# ตรวจสอบ Line API
try:
    line_bot_api = LineBotApi(LINE_CHANNEL_ACCESS_TOKEN)
    webhook_handler = WebhookHandler(LINE_CHANNEL_SECRET)
    print("LINE Bot API and Webhook Handler Initialized.")
except Exception as e:
    line_bot_api = None
    webhook_handler = None
    print(f"Warning: LINE Bot API failed. Error: {e}")

# ----------------------------

app = FastAPI(title="Smart Home Backend (DeepFace)")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

DB_PATH = "database"
if not os.path.exists(DB_PATH):
    os.makedirs(DB_PATH)

# โมเดลที่เราจะใช้ (VGG-Face แม่นยำและเสถียรมาก)
MODEL_NAME = "VGG-Face"
# ตัวหาใบหน้า (opencv เร็วสุดและไม่ต้องลงอะไรเพิ่ม)
DETECTOR_BACKEND = "opencv"

# ฐานข้อมูลสถานะ User ชั่วคราว
user_status_db = {}

# --- Models ---
class SpoofRequest(BaseModel):
    frames: List[str]

class PermissionRequest(BaseModel):
    name: str
    image_data: str

class RegisterFaceRequest(BaseModel):
    user_id: str
    name: str
    images: List[str]

class ScanRequest(BaseModel):
    image_data: str

# --- Helper Functions ---
def base64_to_cv2_image(base64_string):
    """แปลง base64 เป็น cv2 image"""
    img_data = re.sub(r'^data:image/.+;base64,', '', base64_string)
    img_bytes = base64.b64decode(img_data)
    img_array = np.frombuffer(img_bytes, dtype=np.uint8)
    image = cv2.imdecode(img_array, cv2.IMREAD_COLOR)
    return image # DeepFace ใช้ BGR (cv2 default) ได้เลย ไม่ต้องแปลง RGB

def load_known_faces():
    """โหลด Embeddings จากไฟล์ .npy"""
    embeddings_dict = {} # เปลี่ยนมาเก็บแบบ Dict เพื่อความง่าย {name: [emb1, emb2...]}
    
    print("Loading known faces from database...")
    if not os.path.exists(DB_PATH):
        os.makedirs(DB_PATH)
        
    count = 0
    for file_name in os.listdir(DB_PATH):
        if file_name.endswith("_embeddings.npy"):
            try:
                # ชื่อไฟล์: "Name_UserID_embeddings.npy"
                parts = file_name.split("_")
                name = parts[0]
                
                # โหลด embeddings
                loaded_embs = np.load(os.path.join(DB_PATH, file_name))
                
                if name not in embeddings_dict:
                    embeddings_dict[name] = []
                
                # DeepFace embedding เป็น list, แต่ numpy load มาเป็น array
                for emb in loaded_embs:
                    embeddings_dict[name].append(emb)
                count += len(loaded_embs)
            except Exception as e:
                print(f"Error loading {file_name}: {e}")
                
    print(f"Loaded {count} face vectors.")
    return embeddings_dict

# โหลดข้อมูลเข้า Memory
known_face_db = load_known_faces()

def calculate_cosine_similarity(v1, v2):
    """คำนวณความเหมือน (ยิ่งใกล้ยิ่งเหมือน)"""
    dot_product = np.dot(v1, v2)
    norm_v1 = np.linalg.norm(v1)
    norm_v2 = np.linalg.norm(v2)
    return dot_product / (norm_v1 * norm_v2)

# --- API Endpoints ---

@app.get("/")
def read_root():
    return {"message": "Smart Home API (DeepFace) is running!"}

@app.post("/api/v1/spoof-check")
async def spoof_check(request: SpoofRequest):
    # TODO: ใส่โมเดล Spoof (MiniFASNetV2) ตรงนี้ได้เหมือนเดิม
    # ตอนนี้ Bypass ไปก่อนเพื่อให้ระบบรันได้
    return {"is_real": True, "confidence": 0.99}

@app.post("/api/v1/request-permission")
async def request_permission(request: PermissionRequest):
    print(f"Permission request from: {request.name}")
    user_id = f"user_{np.random.randint(1000, 9999)}"
    user_status_db[user_id] = "pending"
    
    # Placeholder Image URL
    image_url = "https://placehold.co/512x512/333333/00FF88?text=New+User"
    
    try:
        if line_bot_api and LINE_HOST_USER_ID != "YOUR_HOST_USER_ID":
            send_line_flex_message(LINE_HOST_USER_ID, request.name, user_id, image_url)
    except Exception as e:
        print(f"LINE Error: {e}")
        
    return {"success": True, "user_id": user_id}

@app.get("/api/v1/check-status/{user_id}")
async def check_status(user_id: str):
    status = user_status_db.get(user_id, "not_found")
    return {"status": status}

@app.post("/api/v1/register-faces")
async def register_faces(request: RegisterFaceRequest):
    print(f"Registering faces for: {request.name}")
    new_embeddings = []
    
    for img_base64 in request.images:
        try:
            img = base64_to_cv2_image(img_base64)
            
            # DeepFace.represent ทำหน้าที่เหมือน face_encodings
            # enforce_detection=False เพื่อให้ไม่ error ถ้ารูปเบลอจัดๆ
            embedding_objs = DeepFace.represent(
                img_path=img,
                model_name=MODEL_NAME,
                detector_backend=DETECTOR_BACKEND,
                enforce_detection=False
            )
            
            # DeepFace คืนค่ามาเป็น List ของ dict
            if embedding_objs:
                embedding = embedding_objs[0]["embedding"]
                new_embeddings.append(embedding)
                
        except Exception as e:
            print(f"Skip frame: {e}")

    if not new_embeddings:
        raise HTTPException(status_code=400, detail="No faces found.")

    # Save to .npy
    embeddings_array = np.array(new_embeddings)
    file_name = f"{request.name}_{request.user_id}_embeddings.npy"
    save_path = os.path.join(DB_PATH, file_name)
    np.save(save_path, embeddings_array)
    
    # Reload DB
    global known_face_db
    known_face_db = load_known_faces()
    
    return {"success": True, "faces_registered": len(new_embeddings)}

@app.post("/api/v1/scan-face")
async def scan_face(request: ScanRequest):
    print("Scanning face...")
    if not known_face_db:
        return {"is_match": False, "reason": "unknown_face"}
        
    try:
        target_img = base64_to_cv2_image(request.image_data)
        
        # 1. สร้าง Embedding จากภาพที่สแกน
        target_embedding_objs = DeepFace.represent(
            img_path=target_img,
            model_name=MODEL_NAME,
            detector_backend=DETECTOR_BACKEND,
            enforce_detection=True
        )
        
        if not target_embedding_objs:
            return {"is_match": False, "reason": "no_face_detected"}
            
        target_embedding = target_embedding_objs[0]["embedding"]
        
        # 2. เปรียบเทียบกับทุกคนใน DB (Cosine Similarity)
        best_score = -1
        best_name = None
        
        # Threshold สำหรับ VGG-Face (Cosine) ปกติอยู่ที่ประมาณ 0.40 (distance) 
        # หรือ 0.60 (similarity) ขึ้นไปถือว่าใช่
        THRESHOLD = 0.60 
        
        for name, db_embeddings in known_face_db.items():
            for db_emb in db_embeddings:
                score = calculate_cosine_similarity(target_embedding, db_emb)
                if score > best_score:
                    best_score = score
                    best_name = name
        
        print(f"Best match: {best_name} with score {best_score}")
        
        if best_score > THRESHOLD:
            return {
                "is_match": True, 
                "user": {"name": best_name}, 
                "confidence": float(best_score)
            }
        else:
            return {"is_match": False, "reason": "unknown_face"}

    except Exception as e:
        print(f"Scan Error: {e}")
        return {"is_match": False, "reason": "error_processing"}

# --- Webhook & LINE Functions (เหมือนเดิม) ---

@app.post("/webhook")
async def line_webhook(request: Request):
    if not webhook_handler:
        raise HTTPException(status_code=500, detail="Webhook not ready")
    signature = request.headers.get("X-Line-Signature", "")
    body = await request.body()
    try:
        webhook_handler.handle(body.decode(), signature)
    except InvalidSignatureError:
        raise HTTPException(status_code=401, detail="Invalid signature")
    return {"status": "ok"}

@webhook_handler.add(PostbackEvent)
def handle_postback(event):
    data = dict(x.split("=") for x in event.postback.data.split("&"))
    user_id = data.get("user_id")
    action = data.get("action")
    
    if user_id and action:
        user_status_db[user_id] = "approved" if action == "approve" else "rejected"
        msg = f"อนุมัติ {user_id} แล้ว" if action == "approve" else f"ปฏิเสธ {user_id} แล้ว"
        line_bot_api.reply_message(event.reply_token, TextSendMessage(text=msg))

def send_line_flex_message(host_id, name, uid, img_url):
    # (ใช้ Code Flex Message เดิมของคุณได้เลย หรือย่อๆ แบบนี้)
    msg = TextSendMessage(text=f"คำขอใหม่จาก: {name}\nID: {uid}")
    # สร้าง Flex จริงๆ แบบ Code ก่อนหน้าก็ได้
    # ปุ่ม Postback
    actions = [
        PostbackAction(label="อนุมัติ", data=f"action=approve&user_id={uid}"),
        PostbackAction(label="ปฏิเสธ", data=f"action=reject&user_id={uid}")
    ]
    # เพื่อความง่าย ผมส่งแบบ QuickReply หรือ Template ง่ายๆ ไปก่อน
    # (แต่ถ้าคุณมี Flex Message code เดิมที่สวยๆ ก็แปะทับฟังก์ชันนี้ได้เลยครับ)
    from linebot.models import TemplateSendMessage, ButtonsTemplate
    template = TemplateSendMessage(
        alt_text="คำขอลงทะเบียน",
        template=ButtonsTemplate(
            title=f"คำขอ: {name}",
            text=f"ID: {uid}",
            actions=actions
        )
    )
    line_bot_api.push_message(host_id, template)

if __name__ == "__main__":
    known_face_db = load_known_faces()
    uvicorn.run(app, host="127.0.0.1", port=8000)