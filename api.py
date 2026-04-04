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
        "ś": "s","ą": "a","ę": "e","ć": "c",
        "ł": "l","ó": "o","ż": "z","ź": "z"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

# =========================
# 🚀 ULTRA FAST (90% odpowiedzi)
# =========================
def ultra_fast_answer(q):
    q = normalize(q)

    if "magnolia" in q:
        return "Pokój Magnolia: 160 zł / noc (max 3 osoby)"
    if "konwalia" in q:
        return "Pokój Konwalia: 130 zł / noc (2 osoby)"
    if "lawenda" in q:
        return "Pokój Lawenda: 240 zł / noc (3 osoby)"
    if "roza" in q:
        return "Pokój Róża: 110 zł / noc (2 osoby)"
    if "piwonia" in q:
        return "Pokój Piwonia: 130 zł / noc (2 osoby)"

    if "kajak" in q:
        return "Kajaki: 90 zł (1 os), 120 zł (2 os)"

    if "basen" in q:
        return "Tak, basen jest dostępny dla gości"

    if "grill" in q or "ognisko" in q:
        return "Tak, dostępny grill i ognisko"

    if "pies" in q or "kot" in q or "zwierze" in q:
        return "Tak 🙂 Psy i koty są dozwolone (20 zł, max 2)"

    if "rzeka" in q or "warta" in q:
        return "Rzeka Warta znajduje się bardzo blisko obiektu"

    if "gdzie" in q or "adres" in q:
        return "Załęcze Małe 30, Pątnów"

    if "atrakcje" in q or "co mozna" in q:
        return "Kajaki, basen, grill, ognisko, rowery i natura"

    return None

# =========================
# 🧠 INTENT
# =========================
def detect_intent(q):
    q = normalize(q)

    if "rezerw" in q:
        return "rezerwacja"
    if "cena" in q or "ile" in q:
        return "cena"
    if "sniadanie" in q:
        return "sniadanie"
    if "zwierze" in q or "pies" in q or "kot" in q:
        return "zwierzeta"

    return None

def handle_intent(intent):
    answers = {
        "cena": "Domek 1: 300 zł, Domek 2: 350 zł, Domek 3: 400 zł",
        "sniadanie": "Śniadanie: 30 zł / osoba",
        "zwierzeta": "Tak 🙂 Zwierzęta dozwolone (20 zł)"
    }
    return answers.get(intent)

# =========================
# 🧠 MEMORY UPDATE
# =========================
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

# =========================
# 🤖 AI (fallback tylko)
# =========================
def ai_answer(question, mem=None):
    try:
        if not os.getenv("OPENAI_API_KEY"):
            return None

        context = f"Kontekst: {mem}" if mem else ""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Odpowiadaj krótko i konkretnie."},
                {"role": "user", "content": context + " " + question}
            ],
            max_tokens=60
        )

        return response.choices[0].message.content.strip()

    except:
        return None

# =========================
# 🤖 LOGIKA GŁÓWNA
# =========================
def handle(q: Question):

    text = q.question
    mem = update_memory(q)

    # ⚡ szybkie odpowiedzi
    fast = ultra_fast_answer(text)
    if fast:
        return fast

    # 📅 rezerwacja
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

    # 🧠 intent
    intent = detect_intent(text)
    if intent:
        ans = handle_intent(intent)
        if ans:
            return ans

    # 🧠 flow rezerwacji
    if mem.get("intent") == "rezerwacja":

        domek = mem.get("domek")
        osoby = mem.get("osoby")
        sniadanie = mem.get("sniadanie")

        if domek and osoby:
            return f"Domek {domek} dla {osoby} osób{' ze śniadaniem' if sniadanie else ''}. Wybierz daty 📅"

        if domek:
            return f"Domek {domek} — dla ilu osób?"

        return "Który domek chcesz zarezerwować?"

    # 🤖 AI fallback
    ai = ai_answer(text, mem)
    if ai:
        return ai

    return "Mogę pomóc w rezerwacji lub odpowiedzieć na pytania 🙂"

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