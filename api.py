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
# 🧠 MEMORY
# =========================
user_memory = {}

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
    session_id: Optional[str] = "default"

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
# 🚀 ULTRA RAG BOOST (NOWE)
# =========================
def ultra_fast_answer(q):
    q = normalize(q)

    # ceny pokoi
    if "magnolia" in q:
        return "Pokój Magnolia kosztuje 160 zł za noc (do 3 osób)"
    if "konwalia" in q:
        return "Pokój Konwalia kosztuje 130 zł za noc (2 osoby)"
    if "lawenda" in q:
        return "Pokój Lawenda kosztuje 240 zł za noc (3 osoby)"
    if "roza" in q:
        return "Pokój Róża kosztuje 110 zł za noc (2 osoby)"
    if "piwonia" in q:
        return "Pokój Piwonia kosztuje 130 zł za noc (2 osoby)"

    # kajaki
    if "kajak" in q:
        return "Kajak: 90 zł jednoosobowy, 120 zł dwuosobowy"

    # basen
    if "basen" in q:
        return "Tak, basen jest dostępny dla gości"

    # grill / ognisko
    if "grill" in q or "ognisko" in q:
        return "Tak, dostępny grill i ognisko"

    # psy
    if "pies" in q or "zwierze" in q or "zwierzeta" in q or "kot":
        return  "Tak 🙂 Psy i koty są dozwolone (20 zł, max 2 zwierzęta)",

    # rzeka
    if "rzeka" in q or "warta" in q:
        return "Rzeka Warta znajduje się bardzo blisko obiektu"

    # lokalizacja
    if "gdzie" in q or "adres" in q:
        return "Załęcze Małe 30, Pątnów"

    # atrakcje
    if "atrakcje" in q or "co mozna" in q:
        return "Kajaki, basen, grill, ognisko, rowery i natura"

    return None

# =========================
# 🧠 INTENT
# =========================
def detect_intent(q):
    q = normalize(q)

    intents = {
        "cena": ["cena","koszt","ile koszt","ile za noc"],
        "sniadanie": ["sniadanie","posilek","jedzenie"],
        "zwierzeta": ["pies","zwierze","psy","kot","koty","zwierzeta"],
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

def update_memory(q: Question):
    sid = q.session_id or "default"

    if sid not in user_memory:
        user_memory[sid] = {}

    mem = user_memory[sid]
    text = normalize(q.question)

    if "domek 1" in text:
        mem["domek"] = "1"
    if "domek 2" in text:
        mem["domek"] = "2"
    if "domek 3" in text:
        mem["domek"] = "3"

    if "2 osob" in text:
        mem["osoby"] = 2
    if "3 osob" in text:
        mem["osoby"] = 3

    if "sniadanie" in text:
        mem["sniadanie"] = True

    if "rezerw" in text:
        mem["intent"] = "rezerwacja"

    if "zmien temat" in text:
        mem.clear()

    return mem


    return answers.get(intent)

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
            score = sum(1 for w in words if w in l)

            if q in l:
                score += 3

            if score > best_score:
                best_score = score
                best = line

        if best and best_score >= 1:
            return best.strip()

    except:
        pass

    return None

# =========================
# 🤖 AI
# =========================
def ai_answer(question, mem=None):
    try:
        if not os.getenv("OPENAI_API_KEY"):
            return None

        context = f"Kontekst: {mem}" if mem else ""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Odpowiadaj krótko i logicznie (1 zdanie)."},
                {"role": "user", "content": context + " " + question}
            ],
            max_tokens=60
        )

        return response.choices[0].message.content.strip()

    except:
        return None

# =========================
# 🤖 LOGIKA
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
    mem = update_memory(q)

    # 🚀 NOWE (ULTRA FAST)
    fast = ultra_fast_answer(text)
    if fast:
        return fast

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

    # 🧠 FLOW REZERWACJI
    # 🧠 FLOW REZERWACJI (NAPRAWIONE)
    if mem.get("intent") == "rezerwacja":

        intent_now = detect_intent(text)

        # 🔥 jeśli user zadaje inne pytanie → NIE blokuj rozmowy
        if intent_now and intent_now not in ["domek1", "domek2", "domek3", "osoby"]:
            pass
        else:
            domek = mem.get("domek")
            osoby = mem.get("osoby")
            sniadanie = mem.get("sniadanie")

            if domek and osoby:
                return f"Świetnie 🙂 Domek {domek} dla {osoby} osób{' ze śniadaniem' if sniadanie else ''}. Wybierz daty 📅"

            if domek:
                return f"Domek {domek} — dla ilu osób ma być?"

            return "Który domek chcesz zarezerwować?"
        if domek and osoby:
            return f"Świetnie 🙂 Domek {domek} dla {osoby} osób{' ze śniadaniem' if sniadanie else ''}. Wybierz daty 📅"

        if domek:
            return f"Domek {domek} — dla ilu osób ma być?"

        return "Który domek chcesz zarezerwować?"

    # 🔍 RAG
    rag = rag_search(text)
    if rag:
        return rag

    # 🤖 AI
    ai = ai_answer(text, mem)
    if ai:
        return ai

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

@app.delete("/reservation")
def delete(data: dict, token: str = Header(None)):
    if not verify(token):
        return {"error":"unauthorized"}

    global reservations
    reservations = [r for r in reservations if r["telefon"] != data["telefon"]]
    save_db(reservations)
    return {"ok":True}

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

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000)