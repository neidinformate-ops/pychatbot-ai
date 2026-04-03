import os
import requests
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

# 🔥 BAZA
reservations = []

MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/228u53xafjidh3etv4d1u3tzbpozjeaq"

# 📄 DANE TXT
def load_knowledge():
    try:
        with open("dane.txt", "r", encoding="utf-8") as f:
            return f.read().lower().split("\n")
    except:
        return []

KNOWLEDGE = load_knowledge()

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


# 🔥 KONFLIKT
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


# 🔍 PROSTY RAG (dopasowanie zdań)
def rag_search(question):

    q = question.lower().split()

    best_match = None
    best_score = 0

    for line in KNOWLEDGE:
        score = sum(1 for word in q if word in line)

        if score > best_score and len(line) > 5:
            best_score = score
            best_match = line

    if best_score >= 2:  # próg dopasowania
        return best_match.capitalize()

    return None


# 🤖 AI (minimalne użycie)
def ai_answer(question):

    if len(question) < 6:
        return None

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Odpowiadaj max 1 zdaniem, konkretnie."},
                {"role": "user", "content": question}
            ],
            max_tokens=50
        )

        return response.choices[0].message.content.strip()

    except:
        return None


# 🧠 LOGIKA
def get_smart_answer(q: Question):

    text = q.question.lower()

    # 🔴 BLOKADA
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
            return "🔴 Termin zablokowany"

    # 📅 REZERWACJA
    if q.data_od and q.data_do and q.numer_domku:
        if is_date_conflict(q.data_od, q.data_do, q.numer_domku):
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

        return "✅ Rezerwacja przyjęta!"

    # 🔍 RAG (NAJWAŻNIEJSZE)
    rag = rag_search(q.question)
    if rag:
        return rag

    # 🤖 AI fallback
    ai = ai_answer(q.question)
    if ai:
        return ai

    return "Mogę pomóc w rezerwacji lub odpowiedzieć na pytania 🙂"


# 🚀 API
@app.post("/ask")
async def ask(q: Question):

    answer = get_smart_answer(q)

    try:
        requests.post(MAKE_WEBHOOK_URL, json={
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
        }, timeout=5)
    except:
        pass

    return {"answer": answer}


@app.get("/availability")
def availability():
    return reservations


# 🚀 RUN
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)