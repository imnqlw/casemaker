from fastapi import FastAPI, Request
from pydantic import BaseModel
import requests
from dotenv import load_dotenv
import os
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import JSONResponse

load_dotenv()
app = FastAPI()

origins = [
    "https://www.qahelper.ru",  # Ваш фронтенд
    "http://localhost:3000",
    "https://qahelper.ru"
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
        "Authorization": f"Bearer io-v2-eyJhbGciOiJSUzI1NiIsInR5cCI6IkpXVCJ9.eyJvd25lciI6ImFmNTU5YzA5LWQwYmUtNDQyZi1iNDBjLTg2YmNhYzg4ZmM5YiIsImV4cCI6NDkwODgwNzY5N30.pbm1x9iYRaDijFH2Ehj4dvACqb1gciWVq4jNjm1DzNIVrBohHUNDOqEnu5o-vlO8ortuIoOqCeSL2IHMPgMAxw"
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




@app.options("/ask", include_in_schema=False)
async def options_ask():
    return JSONResponse(content={}, status_code=200)

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("main:app", host="0.0.0.0", port=port)
