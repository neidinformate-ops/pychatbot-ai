import os
import json
import secrets
from datetime import datetime
from fastapi import FastAPI, Header
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

ADMIN_PASSWORD = os.getenv("ADMIN_PASSWORD", "admin123")

# =========================
# 💾 DB
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
# 🔐 AUTH
# =========================
tokens = set()

class LoginData(BaseModel):
    password: str

@app.post("/login")
def login(data: LoginData):
    if data.password == ADMIN_PASSWORD:
        token = secrets.token_hex(16)
        tokens.add(token)
        return {"token": token}
    return {"error": "unauthorized"}

def verify(token):
    return token in tokens

# =========================
# 📦 MODEL
# =========================
class Question(BaseModel):
    question: str
    imie: Optional[str] = None
    telefon: Optional[str] = None
    numer_domku: Optional[str] = None
    data_od: Optional[str] = None
    data_do: Optional[str] = None

# =========================
# 🔥 KONFLIKT
# =========================
def is_conflict(f, t, domek):
    for r in reservations:
        if r["numer_domku"] != domek:
            continue
        if f <= r["data_do"] and t >= r["data_od"]:
            return True
    return False

def normalize(text):
    text = text.lower()

    replacements = {
        "ś": "s", "ą": "a", "ę": "e", "ć": "c",
        "ł": "l", "ó": "o", "ż": "z", "ź": "z"
    }

    for k, v in replacements.items():
        text = text.replace(k, v)

    return text

# =========================
# 🧠 INTENT
# =========================
def detect_intent(q):

    q = normalize(q)

    intents = {

        "cena": ["cena","koszt","ile koszt","ile za noc"],
        "sniadanie": ["sniadanie","posilek","jedzenie"],
        "zwierzeta": ["pies","zwierze","psy"],
        "godziny": ["zameldowanie","wymeldowanie","check in","check out"],
        "lokalizacja": ["gdzie","lokalizacja","okolica"],
        "rzeka": ["rzeka","warta","nad rzeka"],
        "atrakcje": ["atrakcje","co robic","co mozna"],
        "rowery": ["rower","trasy rowerowe"],
        "kajaki": ["kajaki","splywy"],
        "parking": ["parking"],
        "osoby": ["ile osob","pojemnosc","dla ilu"],
        "domek1": ["domek 1"],
        "domek2": ["domek 2"],
        "domek3": ["domek 3"]
    }

    for intent, words in intents.items():
        if any(w in q for w in words):
            return intent

    return None


def handle_intent(intent):

    answers = {

        "cena": "Domek 1: 300 zł, Domek 2: 350 zł, Domek 3: 400 zł za noc",
        "sniadanie": "Śniadanie w koszu kosztuje 30 zł za osobę",
        "zwierzeta": "Tak, zwierzęta są dozwolone po wcześniejszym uzgodnieniu",
        "godziny": "Zameldowanie od 15:00, wymeldowanie do 11:00",
        "lokalizacja": "Domki są w spokojnej okolicy blisko rzeki Warty",
        "rzeka": "Tak, w pobliżu znajduje się rzeka Warta",
        "atrakcje": "Spacery, rowery, kajaki i relaks nad rzeką",
        "rowery": "W okolicy są trasy rowerowe",
        "kajaki": "Dostępne są spływy kajakowe",
        "parking": "Parking dla gości jest bezpłatny",
        "osoby": "Domki są dla 2 do 6 osób",
        "domek1": "Domek 1 kosztuje 300 zł za noc",
        "domek2": "Domek 2 kosztuje 350 zł za noc",
        "domek3": "Domek 3 kosztuje 400 zł za noc"
    }

    return answers.get(intent, None)

# =========================
# 🔍 RAG
# =========================
def rag_search(q):

    try:
        with open("dane.txt","r",encoding="utf-8") as f:
            lines = f.readlines()

        q = normalize(q)
        words = q.split()

        best = None
        best_score = 0

        for line in lines:
            l = normalize(line)
            score = 0

            for w in words:
                if w in l:
                    score += 1

            if q in l:
                score += 3

            if score > best_score:
                best_score = score
                best = line

        if best and best_score >= 2:
            return best.strip()

    except:
        pass

    def ai_answer(question):

        try:
            from openai import OpenAI
            client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": "Odpowiadaj krótko (1 zdanie)"},
                    {"role": "user", "content": question}
                ],
                max_tokens=60
            )

            return response.choices[0].message.content.strip()

        except Exception as e:
            print("AI ERROR:", e)
            return None



# =========================
# 🤖 GŁÓWNA LOGIKA
# =========================
def smart_fallback(q):

    q = normalize(q)

    if len(q) < 4:
        return "Napisz trochę więcej 🙂"

    if "hej" in q or "czesc" in q:
        return "Cześć 🙂 Mogę pomóc w rezerwacji lub odpowiedzieć na pytania"

    if "dzieki" in q:
        return "Nie ma sprawy 🙂"

    if "rezerw" in q:
        return "Kliknij 📅 Rezerwacja aby wybrać termin"

    return "Mogę pomóc w cenach, dostępności lub atrakcjach 🙂"


def handle(q: Question):

    text = q.question

    # 📅 REZERWACJA
    if q.data_od and q.data_do and q.numer_domku:

        if is_conflict(q.data_od, q.data_do, q.numer_domku):
            return "❌ Termin zajęty"

        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "imie": q.imie,
            "telefon": q.telefon
        })

        save_db(reservations)
        return "✅ Rezerwacja przyjęta"

    # 🔴 BLOKADA
    if "blokada" in normalize(text):
        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "imie": "ADMIN",
            "telefon": ""
        })
        save_db(reservations)
        return "🔴 Termin zablokowany"

    # 🧠 INTENT
    intent = detect_intent(text)
    if intent:
        return handle_intent(intent)

    # 🔍 RAG
    rag = rag_search(text)
    if rag:
        return rag

    # 🤖 AI fallback
    ai = ai_answer(text)
    if ai:
        return ai

    # 🧠 fallback
    return smart_fallback(text)

# =========================
# 🚀 API
# =========================
@app.post("/ask")
async def ask(q: Question):
    return {"answer": handle(q)}

@app.get("/availability")
def availability():
    return load_db()

# DELETE
@app.delete("/reservation")
def delete(data: dict, token: str = Header(None)):
    if not verify(token):
        return {"error":"unauthorized"}

    global reservations
    reservations = [r for r in reservations if r["telefon"] != data["telefon"]]
    save_db(reservations)
    return {"ok":True}

# UNBLOCK
@app.delete("/unblock")
def unblock(data: dict, token: str = Header(None)):
    if not verify(token):
        return {"error":"unauthorized"}

    global reservations
    reservations = [
        r for r in reservations
        if not (
            r["numer_domku"] == data["numer_domku"] and
            r["data_od"] == data["data_od"]
        )
    ]
    save_db(reservations)
    return {"ok":True}

# RUN
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000)