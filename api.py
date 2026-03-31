print("🔥 NOWA WERSJA API DZIAŁA 🔥")

import os
import requests
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# 🔗 WEBHOOK MAKE
MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/228u53xafjidh3etv4d1u3tzbpozjeaq"

# 📦 MODEL (NOWY - REZERWACJA)
class Question(BaseModel):
    question: str
    imie: str
    nazwisko: str
    email: str
    telefon: str
    numer_domku: str
    sniadanie: bool

# ✅ TEST DEPLOY
@app.get("/")
def home():
    return {"message": "NOWA WERSJA 123 🚀"}

# 🤖 GŁÓWNY ENDPOINT
@app.post("/ask")
async def ask_ai(q: Question):

    # 🔹 odpowiedź testowa
    answer = f"[TEST MODE] {q.question}"

    print("📩 Otrzymano dane:")
    print("👤", q.imie, q.nazwisko)
    print("📧", q.email)
    print("📞", q.telefon)
    print("🏠 Domek:", q.numer_domku)
    print("🥐 Śniadanie:", q.sniadanie)
    print("❓ Pytanie:", q.question)

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
        "source": "rezerwacja_api"
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