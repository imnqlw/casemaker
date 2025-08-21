from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse
import shutil
from pathlib import Path

load_dotenv()
app = FastAPI()

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
    return {"answer": text.split("</think>")[1]}


import uvicorn


@app.get("/")
async def root():
    return {"message": "Secure Local Server"}


@app.get("/ping")
async def ping():
    return {"status": "ok", "message": "pong"}


@app.options("/ask", include_in_schema=False)
async def options_ask():
    return JSONResponse(content={}, status_code=200)


UPLOAD_DIR = Path("uploads")
UPLOAD_DIR.mkdir(exist_ok=True)

# Подключите статические файлы для доступа к загруженным файлам
app.mount("/uploads", StaticFiles(directory="uploads"), name="uploads")


@app.post("/upload/file")
async def upload_file(file: UploadFile = File(...)):
    try:
        # Проверяем расширение файла
        validate_file_extension(file.filename)

        # Сохраняем файл
        file_path = UPLOAD_DIR / file.filename

        with open(file_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)

        return {
            "message": "Файл успешно загружен",
            "filename": file.filename,
            "file_url": f"/uploads/{file.filename}"
        }
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при загрузке файла: {str(e)}")



@app.get("/uploaded/files")
async def list_uploaded_files():
    try:
        files = []
        for file_path in UPLOAD_DIR.iterdir():
            if file_path.is_file():
                files.append({
                    "name": file_path.name,
                    "size": file_path.stat().st_size,
                    "url": f"/uploads/{file_path.name}"
                })
        return {"files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Ошибка при получении списка файлов: {str(e)}")


def validate_file_extension(filename: str):
    allowed_extensions = {'.txt', '.pdf', '.doc', '.docx', '.jpg', '.jpeg', '.png', '.gif'}
    file_extension = Path(filename).suffix.lower()

    if file_extension not in allowed_extensions:
        raise HTTPException(status_code=400, detail="Недопустимый тип файла")


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
