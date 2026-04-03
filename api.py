print("🔥 API BOOKING PRO DZIAŁA 🔥")

import os
import requests
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

# 🔥 CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔥 "BAZA"
reservations = []

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

        f1 = datetime.strptime(r["data_od"], "%Y-%m-%d")
        t1 = datetime.strptime(r["data_do"], "%Y-%m-%d")

        f2 = datetime.strptime(new_from, "%Y-%m-%d")
        t2 = datetime.strptime(new_to, "%Y-%m-%d")

        if f2 <= t1 and t2 >= f1:
            return True
    return False


# 🧠 FAQ
def get_smart_answer(text, domek, sniadanie):
    t = text.lower()

    if "cena" in t or "ile" in t:
        return "Domek 1:300zł | 2:350zł | 3:400zł"

    if "godzin" in t:
        return "Check-in 15:00 | Check-out 11:00"

    if "śniad" in t:
        return "Śniadania w koszu 🧺"

    return f"[INFO] {text}"


# ✅ TEST
@app.get("/")
def home():
    return {"status": "ok"}


# 📊 PANEL DATA
@app.get("/reservations")
def get_res():
    return reservations


# ❌ DELETE
@app.delete("/reservation")
def delete(index: int):
    if index < len(reservations):
        reservations.pop(index)
        return {"ok": True}
    return {"error": "not found"}


# 🤖 GŁÓWNY ENDPOINT
@app.post("/ask")
async def ask(q: Question):

    print("\n📩 NOWE:", q)

    # 🔒 REZERWACJA
    if q.data_od and q.data_do and q.numer_domku:

        if is_date_conflict(q.data_od, q.data_do, q.numer_domku):
            answer = "❌ Termin zajęty"
        else:
            reservations.append({
                "numer_domku": q.numer_domku,
                "data_od": q.data_od,
                "data_do": q.data_do
            })
            answer = "✅ Rezerwacja przyjęta"

    else:
        answer = get_smart_answer(q.question, q.numer_domku, q.sniadanie)

    # 📦 MAKE
    try:
        requests.post(MAKE_WEBHOOK_URL, json={
            "question": q.question,
            "answer": answer,
            "data_od": q.data_od,
            "data_do": q.data_do
        }, timeout=5)
    except:
        pass

    return {"answer": answer}


# 🚀 RUN
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)