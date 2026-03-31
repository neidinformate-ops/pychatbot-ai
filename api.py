print("🔥 NOWA WERSJA API DZIAŁA 🔥")

import os
import requests
from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()

# 🔗 WEBHOOK MAKE
MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/o8yg1shovrn0rmlcobmo2t941bqrgn8l"

# 📦 MODEL
class Question(BaseModel):
    question: str

# ✅ NOWY ENDPOINT TESTOWY (SPRAWDZENIE DEPLOY)
@app.get("/")
def home():
    return {"message": "NOWA WERSJA 123 🚀"}

# 🤖 GŁÓWNY ENDPOINT
@app.post("/ask")
async def ask_ai(q: Question):

    answer = f"[TEST MODE] {q.question}"

    print("📩 Otrzymano pytanie:", q.question)

    try:
        res = requests.post(
            MAKE_WEBHOOK_URL,
            json={
                "question": q.question,
                "answer": answer
            }
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