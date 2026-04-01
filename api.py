print("🔥 NOWA WERSJA API PRO DZIAŁA 🔥")

import os
import requests
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
# 🔗 WEBHOOK MAKE
MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/228u53xafjidh3etv4d1u3tzbpozjeaq"

# 📦 MODEL
class Question(BaseModel):
    question: str
    imie: str
    nazwisko: str
    email: str
    telefon: str
    numer_domku: str
    sniadanie: bool

# 🔥 FAQ PRO (multi-odpowiedzi + separator)
def get_smart_answer(q: str, domek: str, sniadanie: bool):
    text = q.lower()
    answers = []

    # 🟣 CENA
    if any(word in text for word in ["cena", "koszt", "ile"]):
        if domek == "1":
            base = "Domek 1: 300 zł / noc"
        elif domek == "2":
            base = "Domek 2: 350 zł / noc"
        elif domek == "3":
            base = "Domek 3: 400 zł / noc"
        else:
            base = "Cena zależy od wybranego domku"

        if sniadanie:
            answers.append(f"{base} + śniadania 🥐 (+30 zł/os)")
        else:
            answers.append(f"{base} (bez śniadań)")

    # 🟣 GODZINY
    if any(word in text for word in ["godzin", "meldunek", "wymeldowanie"]):
        answers.append("Zameldowanie od 15:00 🕒, wymeldowanie do 11:00.")

    # 🟣 ŚNIADANIA
    if "śniad" in text:
        answers.append("Śniadania dostarczamy w formie kosza do domku 🧺 (świeże pieczywo, kawa, lokalne produkty).")

    # 🟣 TERMINY
    if any(word in text for word in ["termin", "dostępność", "kiedy wolne"]):
        answers.append("Dostępne terminy sprawdzisz tutaj 👉 https://twojastrona.pl/kalendarz")

    # 🔹 fallback
    if not answers:
        return f"[TEST MODE] {q}"

    # 🔥 SEPARATOR (czytelny)
    return "\n\n".join(answers)


# ✅ TEST
@app.get("/")
def home():
    return {"message": "API PRO działa 🚀"}


# 🤖 GŁÓWNY ENDPOINT
@app.post("/ask")
async def ask_ai(q: Question):

    print("📩 Otrzymano dane:")
    print("👤", q.imie, q.nazwisko)
    print("📧", q.email)
    print("📞", q.telefon)
    print("🏠 Domek:", q.numer_domku)
    print("🥐 Śniadanie:", q.sniadanie)
    print("❓ Pytanie:", q.question)

    # 🔥 SMART ODPOWIEDŹ
    answer = get_smart_answer(q.question, q.numer_domku, q.sniadanie)

    # 📦 dane do Make
    data = {
        "imie": q.imie,
        "nazwisko": q.nazwisko,
        "email": q.email,
        "telefon": q.telefon,
        "numer_domku": q.numer_domku,
        "sniadanie": q.sniadanie,
        "question": q.question,
        "answer": answer,
        "time": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "source": "api_pro"
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