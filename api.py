
from fastapi.middleware.cors import CORSMiddleware
print("🔥 NOWA WERSJA API PRO DZIAŁA 🔥")
import os
import requests
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional

app = FastAPI()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 🔥 na start (potem można ograniczyć)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 🔗 WEBHOOK MAKE
MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/228u53xafjidh3etv4d1u3tzbpozjeaq"

# 📦 MODEL (wszystko opcjonalne oprócz question)
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

# 🔥 SMART FAQ PRO (bez AI)
def get_smart_answer(q: str, domek: Optional[str], sniadanie: Optional[bool]):
    text = q.lower()

    # 🟣 CENA
    if any(word in text for word in ["cena", "koszt", "ile", "platnosc"]):
        if domek == "1":
            base = "Domek 1: 300 zł / noc"
        elif domek == "2":
            base = "Domek 2: 350 zł / noc"
        elif domek == "3":
            base = "Domek 3: 400 zł / noc"
        else:
            base = "Cena zależy od wybranego domku (1:300zł, 2:350zł, 3:400zł)"

        if sniadanie:
            return base + " + śniadania 🥐 (+30 zł/os)"
        else:
            return base + " (bez śniadań)"

    # 🟣 GODZINY
    if any(word in text for word in ["godzin", "meldunek", "wymeldowanie", "check", "kiedy"]):
        return "Zameldowanie od 15:00 🕒, wymeldowanie do 11:00."

    # 🟣 ŚNIADANIA
    if any(word in text for word in ["śniad", "sniad", "jedzenie", "posiłek"]):
        return "Śniadania dostarczamy w formie kosza 🧺 (świeże pieczywo, kawa, lokalne produkty)."

    # 🟣 TERMINY
    if any(word in text for word in ["termin", "dostęp", "wolne", "kalendarz"]):
        return "Sprawdź dostępność tutaj 👉 https://twojastrona.pl/kalendarz"

    # 🟣 REZERWACJA INTENT
    if any(word in text for word in ["rezerw", "zarezerwuj", "booking"]):
        return "Kliknij przycisk 📋 Rezerwacja i wypełnij formularz."

    # 🔥 fallback (najważniejsze)
    return f"[TEST MODE] Otrzymałem: {q}"


# ✅ TEST
@app.get("/")
def home():
    return {"message": "API PRO działa 🚀"}


# 🤖 GŁÓWNY ENDPOINT
@app.post("/ask")
async def ask_ai(q: Question):

    print("\n📩 NOWE ZAPYTANIE ----------------------")
    print("❓ Pytanie:", q.question)
    print("👤 Imię:", q.imie or "brak")
    print("📧 Email:", q.email or "brak")
    print("🏠 Domek:", q.numer_domku or "brak")
    print("🥐 Śniadanie:", q.sniadanie)

    # 🔥 SMART odpowiedź
    answer = get_smart_answer(q.question, q.numer_domku, q.sniadanie)

    print("🧠 ODPOWIEDŹ:", answer)

    # 📦 dane do Make
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
        "status": "nowa"
    }
    print("🚀 WYSYŁAM DO MAKE:", data)

    try:
        res = requests.post(
            MAKE_WEBHOOK_URL,
            json=data,
            timeout=10
        )

        print("✅ WEBHOOK STATUS:", res.status_code)
        print("📦 WEBHOOK RESPONSE:", res.text)

    except Exception as e:
        print("❌ WEBHOOK ERROR:", str(e))

    return {"answer": answer}


# 🚀 RAILWAY FIX
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)