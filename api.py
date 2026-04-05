import os
import json
from datetime import datetime
from fastapi import FastAPI, Header
from pydantic import BaseModel, EmailStr
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from openai import OpenAI
import faiss
import numpy as np
import logging
from auth import create_user, verify_password, create_token, get_user, get_current_user
from fastapi import Depends, HTTPException

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook")

# =========================
# 🧠 RAG (FAISS)
# =========================
RAG_DATA = []
RAG_INDEX = None

def load_rag():
    global RAG_DATA, RAG_INDEX

    try:
        with open("Dane.txt", "r", encoding="utf-8") as f:
            chunks = [c.strip() for c in f.read().split("\n") if c.strip()]

        embeddings = []
        for c in chunks:
            emb = client.embeddings.create(
                model="text-embedding-3-small",
                input=c
            )
            embeddings.append(emb.data[0].embedding)

        if not embeddings:
            return

        dim = len(embeddings[0])
        index = faiss.IndexFlatL2(dim)

        index.add(np.array(embeddings).astype("float32"))

        RAG_DATA = chunks
        RAG_INDEX = index


    except Exception as e:

        print("Embedding error:", e)

        return []

def search_rag(query, k=3, threshold=0.8):
    if not RAG_INDEX:
        return []

    try:
        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
    except Exception as e:
        print("Embedding error:", e)
        return []
    )

    q_vec = np.array([emb.data[0].embedding]).astype("float32")
    D, I = RAG_INDEX.search(q_vec, k)

    results = []
    for dist, idx in zip(D[0], I[0]):
        if idx < len(RAG_DATA) and dist < threshold:
            results.append(RAG_DATA[idx])

    return results

load_rag()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
class MemoryStore:
    def get(self, key: str):
        return user_memory.get(key)

    def set(self, key: str, value: dict):
        user_memory[key] = value

    def clear(self, key: str):
        if key in user_memory:
            del user_memory[key]


class MemoryService:
    def __init__(self, store: MemoryStore):
        self.store = store

    def get_memory(self, key: str):
        return self.store.get(key) or {}

    def update_memory(self, key: str, patch: dict):
        current = self.get_memory(key)
        current.update(patch)
        self.store.set(key, current)
        return current

    def clear(self, key: str):
        def set(self, key: str, value: dict):
            self.store.set(key, value)
        self.store.clear(key)


memory_service = MemoryService(MemoryStore())
# =========================
# 🔐 AUTH (JWT - auth.py)
# =========================


class LoginData(BaseModel):
    email: str
    password: str


class RegisterData(BaseModel):
    email: str
    password: str

@app.post("/login")
def login(data: LoginData):
    user = get_user(data.email)

    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401, detail="invalid_credentials")

    token = create_token(user["id"])
    return {"token": token}

@app.post("/register")
def register(data: RegisterData):
    try:
        user = create_user(data.email, data.password)
        return {"ok": True, "user": user["email"]}
    except ValueError:
        raise HTTPException(status_code=400, detail="user_exists")

# =========================
# 📦 MODEL
# =========================
class Question(BaseModel):
    question: str
    imie: Optional[str] = None
    nazwisko: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[EmailStr] = None
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
    key = sid

    mem = memory_service.get_memory(sid) = {}

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
        memory_service.clear(sid)
        return {}

    memory_service.set(sid, mem)
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
import requests

def handle(q: Question):

    text = q.question
    mem = update_memory(q)

    # ⚡ szybkie odpowiedzi
    fast = ultra_fast_answer(text)
    if fast:
        return fast

    # 📅 rezerwacja

    import requests
    import time
    import logging

    WEBHOOK_URL = "https://hook.eu1.make.com/228u53xafjidh3etv4d1u3tzbpozjeaq"  # np discord / make / zapier

    def send_webhook(data, retries=3, timeout=5):
        payload = {
            "event": "reservation_created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }

        for attempt in range(retries):
            try:
                response = requests.post(
                    WEBHOOK_URL,
                    json=payload,
                    timeout=timeout
                )

                if response.status_code < 300:
                    return True

                logger.warning(f"Webhook failed (status {response.status_code}) attempt {attempt + 1}")

            except requests.exceptions.Timeout:
                logger.warning(f"Webhook timeout attempt {attempt + 1}")

            except Exception as e:
                logger.error(f"Webhook error: {str(e)} attempt {attempt + 1}")

            time.sleep(1)

        logger.error("Webhook failed after retries")
        return False

    if q.data_od and q.data_do and q.numer_domku:
        if is_conflict(q.data_od, q.data_do, q.numer_domku):
            return "❌ Termin zajęty"

        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "imie": q.imie,
            "telefon": q.telefon,
            "email": q.email
        })

        save_db(reservations)

        send_webhook({
            "type": "reservation",
            "reservation": {
                "house_id": q.numer_domku,
                "date_from": q.data_od,
                "date_to": q.data_do
            },
            "customer": {
                "name": q.imie,
                "phone": q.telefon,
                "email": q.email
            }
        })

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

    # 🧠 RAG
    rag_results = search_rag(text)

    if rag_results:
        context = " ".join(rag_results)

        rag_prompt = f"""
        Odpowiedz WYŁĄCZNIE na podstawie poniższych danych.
        Jeśli nie ma odpowiedzi w danych → napisz: "brak informacji".

        DANE:
        {context}

        PYTANIE:
        {text}
        """

        rag_response = ai_answer(rag_prompt, mem)
        if rag_response and "brak informacji" not in rag_response.lower():
            return rag_response

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
def delete(data: dict, user=Depends(get_current_user)):
    global reservations
    reservations = [r for r in reservations if r.get("telefon") != data.get("telefon")]
    save_db(reservations)
    return {"ok":True}

@app.delete("/unblock")
def unblock(data: dict, user=Depends(get_current_user)):
    global reservations
    reservations = [
        r for r in reservations
        if not (
                r.get("numer_domku") == data.get("numer_domku") and
                r.get("data_od") == data.get("data_od")
        )
    ]
    save_db(reservations)
    return {"ok":True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000)