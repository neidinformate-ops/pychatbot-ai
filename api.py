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

MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/228u53xafjidh3etv4d1u3tzbpozjeaq"

# =========================
# 📄 NORMALIZACJA
# =========================
def normalize(text):
    text = text.lower()

    replacements = {
        "śniadanie": "sniadanie",
        "śniadania": "sniadanie",
        "kosztu": "koszt",
        "ceny": "cena",
        "domków": "domek"
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    text = text\
        .replace("ą","a").replace("ę","e").replace("ś","s")\
        .replace("ć","c").replace("ł","l").replace("ó","o")\
        .replace("ż","z").replace("ź","z")

    return text

# =========================
# 📄 DANE TXT
# =========================
def load_knowledge():
    try:
        with open("dane.txt", "r", encoding="utf-8") as f:
            return [normalize(x.strip()) for x in f.readlines() if len(x.strip()) > 3]
    except:
        return []

KNOWLEDGE = load_knowledge()

# =========================
# 📦 MODEL
# =========================
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

# =========================
# 🔥 KONFLIKT DAT
# =========================
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

# =========================
# 🧠 INTENT
# =========================
def detect_intent(question):
    q = normalize(question)

    intents = {
        "cena": ["cena", "koszt", "ile"],
        "sniadanie": ["sniadanie"],
        "termin": ["termin", "dostep", "wolne"],
        "zwierzeta": ["pies", "zwierze"],
        "parking": ["parking"],
        "wyposazenie": ["wifi", "tv", "klimatyzacja", "jacuzzi", "kuchnia"],
        "atrakcje": ["atrakcje", "co robic", "okolica"]
    }

    detected = []

    for intent, words in intents.items():
        for w in words:
            if w in q:
                detected.append(intent)
                break

    return detected

def handle_intent(intents):

    if "cena" in intents:
        return "Domek 1: 300 zł, Domek 2: 350 zł, Domek 3: 400 zł"

    if "sniadanie" in intents:
        return "Śniadanie kosztuje 30 zł za osobę"

    if "zwierzeta" in intents:
        return "Tak, zwierzęta są dozwolone po uzgodnieniu"

    if "parking" in intents:
        return "Parking jest darmowy dla gości"

    if "wyposazenie" in intents:
        return "Domki mają wifi, tv, kuchnię, a domek 3 dodatkowo jacuzzi"

    if "atrakcje" in intents:
        return "Rowery, kajaki, spacery i natura w okolicy"

    if "termin" in intents:
        return "Kliknij 📅 Rezerwacja aby sprawdzić dostępność"

    return None

# =========================
# 🔍 RAG
# =========================
def rag_search(question):

    q = normalize(question)
    words = q.split()

    best = None
    best_score = 0

    for line in KNOWLEDGE:
        score = 0

        for w in words:
            if w in line:
                score += 2

        if q in line:
            score += 5

        if score > best_score:
            best_score = score
            best = line

    if best and best_score >= 2:
        return best.capitalize()

    return None

# =========================
# 🤖 AI
# =========================
def ai_answer(question):

    if len(question) < 6:
        return None

    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Odpowiadaj krótko (1 zdanie), tylko jeśli nie ma odpowiedzi w danych."},
                {"role": "user", "content": question}
            ],
            max_tokens=60
        )

        return response.choices[0].message.content.strip()

    except:
        return None

# =========================
# 🧠 LOGIKA
# =========================
def get_smart_answer(q: Question):

    text = q.question.lower()

    intents = detect_intent(q.question)
    intent_answer = handle_intent(intents)
    if intent_answer:
        return intent_answer

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
            save_db(reservations)
            return "🔴 Termin zablokowany"

    # 📅 REZERWACJA
    if q.data_od and q.data_do and q.numer_domku:

        if q.data_od > q.data_do:
            return "❌ Błędny zakres dat"

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

        save_db(reservations)

        return "✅ Rezerwacja przyjęta!"

    rag = rag_search(q.question)
    if rag:
        return rag

    ai = ai_answer(q.question)
    if ai:
        return ai

    return "Mogę pomóc w rezerwacji lub odpowiedzieć na pytania 🙂"

# =========================
# 🚀 API
# =========================
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
    return load_db()

# 🚀 RUN
if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run("api:app", host="0.0.0.0", port=port)