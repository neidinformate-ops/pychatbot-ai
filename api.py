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
# 🤖 GŁÓWNA LOGIKA
# =========================
def handle(q: Question):

    # 🔴 BLOKADA
    if "blokada" in q.question:
        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "imie": "ADMIN",
            "telefon": ""
        })
        save_db(reservations)
        return "🔴 Zablokowano"

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

    return "Napisz rezerwacja lub wybierz daty"

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