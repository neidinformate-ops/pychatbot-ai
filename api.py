# 🔥 API PRO V2

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
    allow_credentials=True,
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

# 🔒 konflikt
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

# 📅 dostępność
@app.get("/availability")
def availability():
    return reservations

# 🧠 FAQ bez AI
def smart_answer(q):
    text = q.lower()

    if "cena" in text:
        return "Domek 1: 300zł, Domek 2: 350zł, Domek 3: 400zł 💰"

    if "godzin" in text:
        return "Zameldowanie 15:00, wymeldowanie 11:00 🕒"

    if "śniad" in text:
        return "Śniadania dostarczamy w koszu do domku 🧺"

    if "okolica" in text:
        return "Domki są przy Załęczańskim Parku Krajobrazowym 🌿 — idealne na spacer i odpoczynek"

    if "rower" in text:
        return "W okolicy są trasy rowerowe 🚴"

    return "Chcesz sprawdzić dostępne terminy? 📅"

@app.post("/ask")
async def ask(q: Question):

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
        answer = smart_answer(q.question)

    data = q.dict()
    data["answer"] = answer
    data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        requests.post(MAKE_WEBHOOK_URL, json=data)
    except:
        pass

    return {"answer": answer}