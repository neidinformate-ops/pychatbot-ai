import os
import requests
import json
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# =========================
# 💾 BAZA
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
# 🧠 SESSION
# =========================
sessions = {}

def get_session(user_id="default"):
    if user_id not in sessions:
        sessions[user_id] = {"step": None, "data": {}}
    return sessions[user_id]

# =========================
# 📦 MODEL
# =========================
class Question(BaseModel):
    question: str
    user_id: Optional[str] = "default"
    imie: Optional[str] = None
    nazwisko: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    numer_domku: Optional[str] = None
    data_od: Optional[str] = None
    data_do: Optional[str] = None
    sniadanie: Optional[bool] = None

# =========================
# 💰 CENY
# =========================
PRICES = {
    "1": 300,
    "2": 350,
    "3": 400
}

# =========================
# 🔥 KONFLIKT
# =========================
def is_date_conflict(new_from, new_to, domek):
    for r in reservations:
        if r["numer_domku"] != domek:
            continue

        f = datetime.strptime(r["data_od"], "%Y-%m-%d")
        t = datetime.strptime(r["data_do"], "%Y-%m-%d")

        nf = datetime.strptime(new_from, "%Y-%m-%d")
        nt = datetime.strptime(new_to, "%Y-%m-%d")

        if nf <= t and nt >= f:
            return True
    return False

# =========================
# 💰 LICZENIE CENY (NOWE)
# =========================
def calculate_price(data):

    start = datetime.strptime(data["data_od"], "%Y-%m-%d")
    end = datetime.strptime(data["data_do"], "%Y-%m-%d")

    nights = (end - start).days
    base = PRICES.get(data["numer_domku"], 0)

    total = nights * base

    if data.get("sniadanie"):
        total += nights * 30

    return total

# =========================
# 🤖 FLOW
# =========================
def booking_flow(q: Question):

    session = get_session(q.user_id)
    step = session["step"]
    data = session["data"]
    text = q.question.lower()

    if "rezerw" in text and not step:
        session["step"] = "date_from"
        return "Podaj datę przyjazdu (YYYY-MM-DD)"

    if step == "date_from":
        data["data_od"] = q.question
        session["step"] = "date_to"
        return "Podaj datę wyjazdu"

    if step == "date_to":
        data["data_do"] = q.question
        session["step"] = "domek"
        return "Który domek (1-3)?"

    if step == "domek":
        data["numer_domku"] = q.question
        session["step"] = "sniadanie"
        return "Czy śniadanie? (tak/nie)"

    if step == "sniadanie":
        data["sniadanie"] = "tak" in text
        session["step"] = "name"
        return "Podaj imię"

    if step == "name":
        data["imie"] = q.question
        session["step"] = "phone"
        return "Podaj telefon"

    if step == "phone":
        data["telefon"] = q.question

        if is_date_conflict(data["data_od"], data["data_do"], data["numer_domku"]):
            session["step"] = None
            session["data"] = {}
            return "❌ Termin zajęty"

        price = calculate_price(data)

        reservations.append({
            **data,
            "nazwisko": "",
            "email": "",
            "price": price
        })

        save_db(reservations)

        session["step"] = None
        session["data"] = {}

        return f"✅ Rezerwacja przyjęta. Cena: {price} zł"

    return None

# =========================
# 🧠 ODPOWIEDŹ
# =========================
def get_smart_answer(q: Question):

    flow = booking_flow(q)
    if flow:
        return flow

    return "Napisz 'rezerwacja' aby rozpocząć 🙂"

# =========================
# 🚀 API
# =========================
@app.post("/ask")
async def ask(q: Question):

    answer = get_smart_answer(q)

    return {"answer": answer}

@app.get("/availability")
def availability():
    return load_db()


@app.delete("/reservation")
def delete_reservation(data: dict):
    global reservations

    new_list = []
    for r in reservations:
        if not (
            r["data_od"] == data["data_od"] and
            r["data_do"] == data["data_do"] and
            r["telefon"] == data["telefon"]
        ):
            new_list.append(r)

    reservations = new_list
    save_db(reservations)

    return {"status": "deleted"}

# RUN
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)