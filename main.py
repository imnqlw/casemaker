from urllib.request import Request

from fastapi import FastAPI
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

load_dotenv()
app = FastAPI()

origins = [
    "https://localhost:3000",  # Ваш фронтенд
    "http://localhost:3000",  # На случай HTTP
    "https://127.0.0.1:3000",
    "http://127.0.0.1:3000",
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],  # Разрешить все методы
    allow_headers=["*"],  # Разрешить все заголовки
    expose_headers=["*"]  # Важно для кастомных заголовков
)


class RequestData(BaseModel):
    message: str


promp = """
На основе ТЗ создай тест-кейсы в STRICT MARKDOWN FORMAT.

Шаблон для тест-кейсов:
### Тест-кейс 1: {название}
**ID:** TC-001  
**Приоритет:** Высокий  
**Шаги:**  
1. {шаг 1}  
2. {шаг 2}  
**Ожидаемый результат:**  
{результат}  

Правила:
1. Сохрани ВСЕ данные из ТЗ
2. Строго следуй шаблону
3. Не добавляй дополнительные тексты
Представь данные в виде списка с фиксированным выравниванием:
- Используй символ • для пунктов
- После двоеточия 20 пробелов для выравнивания
- Переноси строки с отступом 25 пробелов
- Максимальная ширина блока: 70 символов
"""


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
            {"role": "system", "content": promp},
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


@app.middleware("http")
async def add_cors_headers(request: Request, call_next):
    response = await call_next(request)
    response.headers["Access-Control-Allow-Origin"] = "https://localhost:3000"
    response.headers["Access-Control-Allow-Methods"] = "GET, POST, PUT, DELETE, OPTIONS"
    response.headers["Access-Control-Allow-Headers"] = "Content-Type, Authorization"
    response.headers["Access-Control-Allow-Credentials"] = "true"
    return response

@app.options("/ask", include_in_schema=False)
async def options_ask():
    return JSONResponse(content={}, status_code=200)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host="127.0.0.1",
        port=5000,
        ssl_keyfile="E:/proect/tcasemaker/ssl/localhost+2-key.pem",
        ssl_certfile="E:/proect/tcasemaker/ssl/localhost+2.pem"
    )
