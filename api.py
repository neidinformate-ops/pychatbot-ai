print("🔥 FINAL SYSTEM V3 🔥")

import os
import requests
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

reservations = []

MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/228u53xafjidh3etv4d1u3tzbpozjeaq"

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

# 🧠 LOGIKA
def smart_answer(text):

    t = text.lower()

    if t in ["tak","ok","jasne"]:
        return "Super 👍 kliknij przycisk rezerwacji poniżej 📅"

    if t in ["nie"]:
        return "OK 😊 jeśli zmienisz zdanie, daj znać!"

    if "cena" in t:
        return "Domek 1: 300zł, Domek 2: 350zł, Domek 3: 400zł 💰"

    if "okolica" in t:
        return "Jesteśmy przy Załęczańskim Parku Krajobrazowym 🌿"

    return "Mogę pomóc w rezerwacji lub odpowiedzieć na pytania 😊"

def add_cta(answer, question):
    if "cena" in question.lower():
        return answer + " 👉 Sprawdzić dostępne terminy?"
    return answer

@app.get("/availability")
def availability():
    return reservations

@app.post("/ask")
async def ask(q: Question):

    if q.data_od and q.data_do and q.numer_domku:

        if is_conflict(q.data_od, q.data_do, q.numer_domku):
            return {"answer": "❌ Termin zajęty"}

        reservations.append({
            "imie": q.imie,
            "nazwisko": q.nazwisko,
            "email": q.email,
            "telefon": q.telefon,
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "sniadanie": q.sniadanie,
            "time": datetime.now().strftime("%Y-%m-%d %H:%M")
        })

        return {"answer": "✅ Rezerwacja przyjęta 🎉"}

    answer = smart_answer(q.question)
    answer = add_cta(answer, q.question)

    return {"answer": answer}