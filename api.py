print("🔥 NOWA WERSJA API PRO DZIAŁA 🔥")

import os
import requests
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 🔥 CORS (NAPRAWA BŁĘDU)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 FAKE BAZA
reservations = []

# 🔗 WEBHOOK MAKE
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


# 🔒 SPRAWDZANIE TERMINÓW
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


# 🔥 FAQ (bez dat!)
def get_smart_answer(text: str, domek: Optional[str], sniadanie: Optional[bool]):
    text = text.lower()

    if any(word in text for word in ["cena", "koszt", "ile"]):
        if domek == "1":
            base = "Domek 1: 300 zł / noc"
        elif domek == "2":
            base = "Domek 2: 350 zł / noc"
        elif domek == "3":
            base = "Domek 3: 400 zł / noc"
        else:
            base = "Ceny: 1=300zł, 2=350zł, 3=400zł"

        return base + (" + śniadania 🥐" if sniadanie else " (bez śniadań)")

    if any(word in text for word in ["godzin", "meldunek", "wymeldowanie"]):
        return "Zameldowanie od 15:00 🕒, wymeldowanie do 11:00."

    if any(word in text for word in ["śniad", "sniad"]):
        return "Śniadania w koszu 🧺 do domku."

    if any(word in text for word in ["termin", "dostęp"]):
        return "Sprawdź kalendarz 👉 https://twojastrona.pl"

    return f"[TEST MODE] {text}"


# ✅ TEST
@app.get("/")
def home():
    return {"message": "API działa 🚀"}


# 🤖 GŁÓWNY ENDPOINT
@app.post("/ask")
async def ask_ai(q: Question):

    print("\n📩 NOWE ZAPYTANIE")
    print(q)

    # 🔥 BLOKOWANIE TERMINÓW (TU MA BYĆ!)
    if q.data_od and q.data_do and q.numer_domku:

        if is_date_conflict(q.data_od, q.data_do, q.numer_domku):
            answer = "❌ Termin zajęty — wybierz inną datę"
            print("⛔ ZAJĘTE")

        else:
            reservations.append({
                "numer_domku": q.numer_domku,
                "data_od": q.data_od,
                "data_do": q.data_do
            })

            answer = "✅ Rezerwacja przyjęta!"
            print("✅ ZAPISANO:", reservations)

    else:
        # 🔥 FAQ
        answer = get_smart_answer(q.question, q.numer_domku, q.sniadanie)

    print("🧠 ODPOWIEDŹ:", answer)

    # 📦 MAKE
    data = {
        "question": q.question,
        "answer": answer,
        "imie": q.imie,
        "nazwisko": q.nazwisko,
        "email": q.email,
        "telefon": q.telefon,
        "numer_domku": q.numer_domku,
        "sniadanie": q.sniadanie,
        "data_od": q.data_od,
        "data_do": q.data_do,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
    }

    try:
        res = requests.post(MAKE_WEBHOOK_URL, json=data, timeout=10)
        print("✅ MAKE:", res.status_code)
    except Exception as e:
        print("❌ MAKE ERROR:", e)

    return {"answer": answer}


# 🚀 RAILWAY
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)