print("🔥 AI + RAG + BOOKING PRO 🔥")

import os
import requests
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

# 🔐 ENV
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

# 🤖 AI (opcjonalnie)
USE_AI = True

# 📚 RAG dane lokalne
with open("Dane.txt", "r", encoding="utf-8") as f:
    DATA = f.read().lower()

# 📦 APP
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 💾 FAKE DB
reservations = []

# 🔗 MAKE
MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/228u53xafjidh3etv4d1u3tzbpozjeaq"

# 📦 MODEL
class Question(BaseModel):
    question: str
    imie: Optional[str] = None
    nazwisko: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    numer_domku: Optional[str] = None
    sniadanie: Optional[bool] = None
    data_od: Optional[str] = None
    data_do: Optional[str] = None

# 🔒 SPRAWDZENIE DAT
def is_conflict(new_from, new_to, domek):
    for r in reservations:
        if r["numer_domku"] != domek:
            continue

        a = datetime.strptime(r["data_od"], "%Y-%m-%d")
        b = datetime.strptime(r["data_do"], "%Y-%m-%d")
        nf = datetime.strptime(new_from, "%Y-%m-%d")
        nt = datetime.strptime(new_to, "%Y-%m-%d")

        if nf <= b and nt >= a:
            return True
    return False

# 🧠 SMART (FAQ + RAG + AI fallback)
def smart_answer(q: Question):
    text = q.question.lower()

    # 🔥 FAQ (0 kosztów)
    if "cena" in text:
        return "Ceny: domek1 300zł, domek2 350zł, domek3 400zł"

    if "godzin" in text:
        return "Zameldowanie 15:00, wymeldowanie 11:00"

    if "śniad" in text:
        return "Śniadania w koszu 🧺 (lokalne produkty)"

    # 📚 RAG (szukanie w pliku)
    if text in DATA:
        return "📚 Odpowiedź z bazy danych: " + q.question

    # 🤖 AI tylko jeśli trzeba
    if USE_AI and OPENAI_API_KEY:
        try:
            from openai import OpenAI
            client = OpenAI(api_key=OPENAI_API_KEY)

            res = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Odpowiadaj krótko i konkretnie."},
                    {"role": "user", "content": q.question}
                ],
                max_tokens=100  # 💸 LIMIT
            )

            return res.choices[0].message.content

        except Exception as e:
            return f"Błąd AI: {str(e)}"

    return "Nie mam odpowiedzi."

# 🏠 TEST
@app.get("/")
def home():
    return {"status": "OK"}

# 📅 LISTA
@app.get("/reservations")
def get_res():
    return reservations

# ❌ DELETE
@app.delete("/reservation")
def delete(index: int):
    if 0 <= index < len(reservations):
        reservations.pop(index)
        return {"status": "deleted"}
    return {"error": "bad index"}

# 🤖 GŁÓWNY ENDPOINT
@app.post("/ask")
async def ask(q: Question):

    print("📩", q)

    # 📅 REZERWACJA
    if q.data_od and q.data_do and q.numer_domku:

        if is_conflict(q.data_od, q.data_do, q.numer_domku):
            return {"answer": "❌ Termin zajęty"}

        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do
        })

        answer = "✅ Rezerwacja przyjęta"

    else:
        answer = smart_answer(q)

    # 📤 MAKE
    data = q.dict()
    data["answer"] = answer
    data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        requests.post(MAKE_WEBHOOK_URL, json=data, timeout=5)
    except:
        pass

    return {"answer": answer}


# 🚀 START
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))