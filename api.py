# 🔥 NOWA WERSJA API PRO DZIAŁA 🔥

import os
import requests
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 🔓 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 FAKE BAZA
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

# 🔥 SPRAWDZENIE KONFLIKTU
def is_date_conflict(new_from, new_to, domek):
    for r in reservations:
        if r["numer_domku"] != domek:
            continue

        existing_from = datetime.strptime(r["data_od"], "%Y-%m-%d")
        existing_to = datetime.strptime(r["data_do"], "%Y-%m-%d")

        new_from_dt = datetime.strptime(new_from, "%Y-%m-%d")
        new_to_dt = datetime.strptime(new_to, "%Y-%m-%d")

        if new_from_dt <= existing_to and new_to_dt >= existing_from:
            return True

    return False

# 🔥 SMART FAQ + BLOKADY
def get_smart_answer(q: Question):

    text = q.question.lower()

    # 🔴 BLOKADA ADMINA
    if "blokada" in text:
        if q.data_od and q.data_do and q.numer_domku:

            reservations.append({
                "numer_domku": q.numer_domku,
                "data_od": q.data_od,
                "data_do": q.data_do,
                "imie": "ADMIN",
                "nazwisko": "",
                "telefon": "",
                "email": ""
            })

            print("🔴 BLOKADA:", reservations)
            return "🔴 Termin zablokowany"

    # 📅 REZERWACJA
    if q.data_od and q.data_do and q.numer_domku:

        conflict = is_date_conflict(q.data_od, q.data_do, q.numer_domku)

        if conflict:
            return "❌ Niestety, ale termin zajęty."

        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "imie": q.imie,
            "nazwisko": q.nazwisko,
            "telefon": q.telefon,
            "email": q.email
        })

        print("✅ REZERWACJA:", reservations)

        return "✅ Rezerwacja przyjęta!"

    # 💰 CENY
    if "cena" in text:
        return "Domek 1: 300zł | Domek 2: 350zł | Domek 3: 400zł"

    # 🕒 GODZINY
    if "godzin" in text:
        return "Zameldowanie 15:00, wymeldowanie 11:00"

    return "Napisz 'rezerwacja' aby rozpocząć booking."

# 🧠 API
@app.post("/ask")
async def ask(q: Question):

    answer = get_smart_answer(q)

    data = {
        "question": q.question,
        "answer": answer,
        "imie": q.imie,
        "nazwisko": q.nazwisko,
        "email": q.email,
        "telefon": q.telefon,
        "numer_domku": q.numer_domku,
        "data_od": q.data_od,
        "data_do": q.data_do,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    }

    try:
        requests.post(MAKE_WEBHOOK_URL, json=data, timeout=5)
    except:
        print("❌ Make error")

    return {"answer": answer}

# 📅 AVAILABILITY (KLUCZOWE!)
@app.get("/availability")
def availability():
    return reservations

# 🚀 RUN
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)