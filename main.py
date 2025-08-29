from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
import uvicorn
import io
import PyPDF2
import docx
from PIL import Image
import pytesseract
from fastapi import Depends
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from models import User, Chat
from auth import get_db, get_password_hash, verify_password, create_access_token, get_current_user

@app.post("/register")
def register(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.username == form_data.username).first()
    if existing:
        raise HTTPException(status_code=400, detail="Пользователь уже существует")

    user = User(
        username=form_data.username,
        password_hash=get_password_hash(form_data.password)
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return {"msg": "Пользователь создан"}

@app.post("/login")
def login(form_data: OAuth2PasswordRequestForm = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.username == form_data.username).first()
    if not user or not verify_password(form_data.password, user.password_hash):
        raise HTTPException(status_code=400, detail="Неверный логин или пароль")

    token = create_access_token({"sub": user.username})
    return {"access_token": token, "token_type": "bearer"}


# Попробуем подключить pdf2image (если установлен)
try:
    from pdf2image import convert_from_bytes
    PDF2IMAGE_AVAILABLE = True
except ImportError:
    PDF2IMAGE_AVAILABLE = False

load_dotenv()
app = FastAPI()

# Настройки CORS (для отладки можно оставить * , потом сузить)
origins = [
    "https://www.qahelper.ru",
    "http://localhost:3000",
    "https://qahelper.ru",
    "*"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


@app.middleware("http")
async def add_cors_headers(request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "https://www.qahelper.ru"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response


class RequestData(BaseModel):
    message: str


# Функция для извлечения текста из файла
async def extract_text_from_file(file: UploadFile):
    content = await file.read()
    file_extension = file.filename.split('.')[-1].lower()

    if file_extension == "txt":
        return content.decode("utf-8", errors="ignore")

    elif file_extension == "pdf":
        text = ""
        try:
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
            for page in pdf_reader.pages:
                extracted = page.extract_text()
                if extracted:
                    text += extracted
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка чтения PDF: {str(e)}")

        if text.strip():
            return text

        # fallback через OCR, если текст не извлекся
        if PDF2IMAGE_AVAILABLE:
            try:
                images = convert_from_bytes(content)
                ocr_text = ""
                for img in images:
                    ocr_text += pytesseract.image_to_string(img)
                return ocr_text
            except Exception as e:
                raise HTTPException(status_code=500, detail=f"OCR ошибка PDF: {str(e)}")
        return "Не удалось извлечь текст из PDF"

    elif file_extension in ["docx"]:
        try:
            doc = docx.Document(io.BytesIO(content))
            return "\n".join([p.text for p in doc.paragraphs if p.text.strip()])
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка чтения DOCX: {str(e)}")

    elif file_extension in ["jpg", "jpeg", "png"]:
        try:
            image = Image.open(io.BytesIO(content))
            return pytesseract.image_to_string(image)
        except Exception as e:
            raise HTTPException(status_code=500, detail=f"Ошибка OCR изображения: {str(e)}")

    else:
        raise HTTPException(status_code=400, detail="Неподдерживаемый формат файла")


@app.post("/process-file")
async def process_file(file: UploadFile = File(...),
                       current_user: User = Depends(get_current_user),
                       db: Session = Depends(get_db)):
    text_content = await extract_text_from_file(file)
    try:
        text_content = await extract_text_from_file(file)
        url = "https://api.intelligence.io.solutions/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('api')}"
        }
        payload = {
            "model": "deepseek-ai/DeepSeek-R1-0528",
            "messages": [
                {"role": "system", "content": os.getenv('promt')},
                {"role": "user", "content": text_content}
            ]
        }

        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        chat = Chat(user_id=current_user.id, message=text_content, response=text)
        db.add(chat)
        db.commit()

        return {"answer": text.split("</think>")[1] if "</think>" in text else text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке файла: {str(e)}")


@app.post("/ask")
async def ask_ai(data: RequestData):
    try:
        url = "https://api.intelligence.io.solutions/api/v1/chat/completions"
        headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {os.getenv('api')}"
        }
        payload = {
            "model": "deepseek-ai/DeepSeek-R1-0528",
            "messages": [
                {"role": "system", "content": os.getenv('promt')},
                {"role": "user", "content": data.message}
            ]
        }
        response = requests.post(url, headers=headers, json=payload)
        data = response.json()
        text = data["choices"][0]["message"]["content"]
        return {"answer": text.split("</think>")[1] if "</think>" in text else text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке файла: {str(e)}")

@app.get("/history")
def get_history(current_user: User = Depends(get_current_user), db: Session = Depends(get_db)):
    chats = db.query(Chat).filter(Chat.user_id == current_user.id).order_by(Chat.timestamp.desc()).all()
    return [{"id": c.id, "message": c.message, "response": c.response, "timestamp": c.timestamp} for c in chats]



@app.get("/")
async def root():
    return {"message": "Secure Local Server"}


@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "pong"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
