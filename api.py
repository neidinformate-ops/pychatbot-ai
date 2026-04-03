import os
import json
import secrets
from datetime import datetime
from fastapi import FastAPI, Header
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# =========================
# 💾 DB
# =========================
def load_db():
    try:
        with open("db.json", "r") as f:
            return json.load(f)
    except:
        return []

def save_db(data):
    with open("db.json", "w") as f:
        json.dump(data, f, indent=2)

reservations = load_db()

# =========================
# 🔐 AUTH
# =========================
tokens = set()

class LoginData(BaseModel):
    password: str

@app.post("/login")
def login(data: LoginData):
    if data.password == ADMIN_PASSWORD:
        token = secrets.token_hex(16)
        tokens.add(token)
        return {"token": token}
    return {"error": "unauthorized"}

def verify(token):
    return token in tokens

# =========================
# 📦 MODEL
# =========================
class Question(BaseModel):
    question: str
    imie: Optional[str] = None
    telefon: Optional[str] = None
    numer_domku: Optional[str] = None
    data_od: Optional[str] = None
    data_do: Optional[str] = None

# =========================
# 🔥 KONFLIKT
# =========================
def is_conflict(f, t, domek):
    for r in reservations:
        if r["numer_domku"] != domek:
            continue
        if f <= r["data_do"] and t >= r["data_od"]:
            return True
    return False

# =========================
# 🧠 INTENT
# =========================
def detect_intent(q):

    q = q.lower()

    if "cena" in q or "koszt" in q or "ile" in q:
        return "cena"

    if "pies" in q or "zwierze" in q:
        return "zwierzeta"

    if "sniadanie" in q:
        return "sniadanie"

    if "ile osob" in q:
        return "osoby"

    return None


def handle_intent(intent):

    if intent == "cena":
        return "Domek 1: 300 zł, Domek 2: 350 zł, Domek 3: 400 zł"

    if intent == "zwierzeta":
        return "Tak, zwierzęta są dozwolone po uzgodnieniu"

    if intent == "sniadanie":
        return "Śniadanie kosztuje 30 zł za osobę"

    if intent == "osoby":
        return "Domki są dla 2 do 6 osób"

    return None

# =========================
# 🔍 RAG
# =========================
def rag_search(q):
    try:
        with open("dane.txt","r",encoding="utf-8") as f:
            data = f.readlines()

        q = q.lower()

        for line in data:
            if any(word in line.lower() for word in q.split()):
                return line.strip()

    except:
        pass

    return None

# =========================
# 🤖 GŁÓWNA LOGIKA
# =========================
def handle(q: Question):

    text = q.question.lower()

    # 🔴 BLOKADA
    if "blokada" in text:
        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "imie": "ADMIN",
            "telefon": ""
        })
        save_db(reservations)
        return "🔴 Termin zablokowany"

    # 📅 REZERWACJA
    if q.data_od and q.data_do and q.numer_domku:

        if is_conflict(q.data_od, q.data_do, q.numer_domku):
            return "❌ Termin zajęty"

        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "imie": q.imie,
            "telefon": q.telefon
        })

        save_db(reservations)
        return "✅ Rezerwacja przyjęta"

    # 🧠 INTENT
    intent = detect_intent(q.question)
    if intent:
        return handle_intent(intent)

    # 🔍 RAG
    rag = rag_search(q.question)
    if rag:
        return rag

    # 🤖 fallback
    return "Mogę pomóc w rezerwacji lub odpowiedzieć na pytania 🙂"

# =========================
# 🚀 API
# =========================
@app.post("/ask")
async def ask(q: Question):
    return {"answer": handle(q)}

@app.get("/availability")
def availability():
    return load_db()

# DELETE
@app.delete("/reservation")
def delete(data: dict, token: str = Header(None)):
    if not verify(token):
        return {"error":"unauthorized"}

    global reservations
    reservations = [r for r in reservations if r["telefon"] != data["telefon"]]
    save_db(reservations)
    return {"ok":True}

# UNBLOCK
@app.delete("/unblock")
def unblock(data: dict, token: str = Header(None)):
    if not verify(token):
        return {"error":"unauthorized"}

    global reservations
    reservations = [
        r for r in reservations
        if not (
            r["numer_domku"] == data["numer_domku"] and
            r["data_od"] == data["data_od"]
        )
    ]
    save_db(reservations)
    return {"ok":True}

# RUN
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000)