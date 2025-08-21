from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
import uvicorn
import io
import PyPDF2  # для обработки PDF
import docx2txt  # для обработки DOCX
from PIL import Image  # для обработки изображений
import pytesseract  # для OCR

load_dotenv()
app = FastAPI()

# Настройки CORS
origins = [
    "https://www.qahelper.ru",
    "http://localhost:3000",
    "https://qahelper.ru"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
    expose_headers=["*"]
)


class RequestData(BaseModel):
    message: str


# Функция для извлечения текста из файла
async def extract_text_from_file(file: UploadFile):
    content = await file.read()
    file_extension = file.filename.split('.')[-1].lower()

    if file_extension == 'txt':
        return content.decode('utf-8')
    elif file_extension == 'pdf':
        # Обработка PDF
        pdf_reader = PyPDF2.PdfReader(io.BytesIO(content))
        text = ""
        for page in pdf_reader.pages:
            text += page.extract_text()
        return text
    elif file_extension in ['docx', 'doc']:
        # Обработка DOCX/DOC
        return docx2txt.process(io.BytesIO(content))
    elif file_extension in ['jpg', 'jpeg', 'png']:
        # OCR для изображений
        image = Image.open(io.BytesIO(content))
        text = pytesseract.image_to_string(image)
        return text
    else:
        raise HTTPException(status_code=400, detail="Неподдерживаемый формат файла")


@app.post("/process-file")
async def process_file(file: UploadFile = File(...)):
    try:
        # Извлекаем текст из файла
        text_content = await extract_text_from_file(file)

        # Отправляем текст в API для генерации тест-кейсов
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

        return {"answer": text.split("</think>")[1] if "</think>" in text else text}

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при обработке файла: {str(e)}")


@app.post("/ask")
async def ask_ai(data: RequestData):
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


@app.get("/")
async def root():
    return {"message": "Secure Local Server"}


@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "pong"}


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)