import os
import json
from datetime import datetime
import logging
import requests
import time

from fastapi import FastAPI, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from typing import Optional

from openai import OpenAI
import faiss
import numpy as np

from auth import create_user, verify_password, create_token, get_user, get_current_user

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()
allow_origins=["*"],
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("app")

# =========================
# 🧠 RAG
# =========================
RAG_STORE = {}

def load_rag_for_client(client_id):
    if client_id in RAG_STORE:
        return

    try:
        index_file = f"rag_{client_id}.index"
        data_file = f"rag_{client_id}.json"
        txt_file = f"Dane_{client_id}.txt"
        print("SZUKAM PLIKU:", txt_file)

        if not os.path.exists(txt_file):
            print("❌ NIE MA PLIKU")

        if os.path.exists(index_file) and os.path.exists(data_file):
            index = faiss.read_index(index_file)
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            RAG_STORE[client_id] = {"index": index, "data": data}
            return

        if not os.path.exists(txt_file):
            txt_file = "Dane.txt"

        with open(txt_file, "r", encoding="utf-8") as f:
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

        RAG_STORE[client_id] = {"index": index, "data": chunks}

        faiss.write_index(index, index_file)
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"RAG error ({client_id}): {e}")


def search_rag(query, client_id, k=3, threshold=0.5):
    if client_id not in RAG_STORE:
        return []

    index = RAG_STORE[client_id]["index"]
    data = RAG_STORE[client_id]["data"]

    try:
        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return []

    q_vec = np.array([emb.data[0].embedding]).astype("float32")
    D, I = index.search(q_vec, k)

    results = []
    for dist, idx in zip(D[0], I[0]):
        if idx < len(data) and dist < threshold:
            results.append(data[idx])

    return results


# =========================
# 💾 DB
# =========================
def load_db():
    try:
        with open("db.json", "r") as f:
            data = json.load(f)
            return data if isinstance(data, dict) else {}
    except:
        return {}

def save_db(data):
    with open("db.json", "w") as f:
        json.dump(data, f, indent=2)
def is_conflict(data_od, data_do, numer_domku, client_id):
    db = load_db()
    reservations = db.get(client_id, [])

    for r in reservations:
        if r.get("numer_domku") != numer_domku:
            continue

        try:
            r_od = datetime.fromisoformat(r.get("data_od"))
            r_do = datetime.fromisoformat(r.get("data_do"))
            new_od = datetime.fromisoformat(data_od)
            new_do = datetime.fromisoformat(data_do)
        except:
            continue

        if new_od < r_do and new_do > r_od:
            return True

    return False

def get_user_reservations(client_id):
    return load_db().get(client_id, [])


# =========================
# 🧠 MEMORY
# =========================
class MemoryStore:
    def __init__(self):
        self.store = {}

    def get(self, key):
        return self.store.get(key)

    def set(self, key, value):
        self.store[key] = value

    def clear(self, key):
        self.store.pop(key, None)


class MemoryService:
    def __init__(self, store):
        self.store = store

    def get_memory(self, key):
        return self.store.get(key) or {}

    def set(self, key, value):
        self.store.set(key, value)

    def clear(self, key):
        self.store.clear(key)


memory_service = MemoryService(MemoryStore())


# =========================
# 🚦 RATE LIMIT
# =========================
rate_limit_store = {}
RATE_LIMIT = 10
RATE_WINDOW = 10


def check_rate_limit(session_id):
    now = time.time()

    rate_limit_store.setdefault(session_id, [])
    rate_limit_store[session_id] = [
        t for t in rate_limit_store[session_id] if now - t < RATE_WINDOW
    ]

    if len(rate_limit_store[session_id]) >= RATE_LIMIT:
        return False

    rate_limit_store[session_id].append(now)
    return True


# =========================
# 🔐 AUTH
# =========================
class LoginData(BaseModel):
    email: str
    password: str


class RegisterData(BaseModel):
    email: str
    password: str


class ClientSetupData(BaseModel):
    text: str


def get_client_id(user):
    return user["id"]


@app.post("/login")
def login(data: LoginData):
    user = get_user(data.email)
    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(status_code=401)
    return {"token": create_token(user["id"])}


@app.post("/register")
def register(data: RegisterData):
    return {"ok": True, "user": create_user(data.email, data.password)["email"]}


@app.post("/client/setup")
def client_setup(data: ClientSetupData, user=Depends(get_current_user)):
    client_id = get_client_id(user)
    print("CLIENT_ID:", client_id)

    with open(f"Dane_{client_id}.txt", "w", encoding="utf-8") as f:
        f.write(data.text.strip())

    RAG_STORE.pop(client_id, None)

    for fpath in [f"rag_{client_id}.index", f"rag_{client_id}.json"]:
        if os.path.exists(fpath):
            os.remove(fpath)

    return {"ok": True}


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

    @validator("telefon")
    def validate_phone(cls, v):
        if v and len(v) < 7:
            raise ValueError("telefon za krótki")
        return v


# =========================
# 🤖 LOGIKA
# =========================
def update_memory(q, client_id):
    key = f"{client_id}:{q.session_id or 'default'}"
    mem = memory_service.get_memory(key)

    # 🧠 historia rozmowy (ostatnie 3 wiadomości)
    history = mem.get("history", [])
    history.append({"role": "user", "content": q.question})

    # trzymaj tylko ostatnie 3
    history = history[-6:]

    mem["history"] = history

    memory_service.set(key, mem)
    return mem

def ai_answer(question, context=None, mem=None, force_context=False):
    try:
        if not os.getenv("OPENAI_API_KEY"):
            return None

        system_prompt = """
        Jesteś profesjonalnym chatbotem firmy.

        ODPOWIADAJ WYŁĄCZNIE na podstawie dostarczonych danych.

        Zasady:
        - jeśli dane istnieją → MUSISZ ich użyć
        - NIE twórz ogólnych odpowiedzi
        - NIE zgaduj
        - NIE dodawaj informacji spoza danych

        Jeśli nie ma danych:
        - powiedz jasno że nie masz informacji

        Styl:
        - krótko (2-4 zdania)
        - naturalnie
        - konkretnie
        """

        content = ""

        # 🧠 historia rozmowy
        if mem and mem.get("history"):
            history_text = "\n".join(
                [f"{h['role']}: {h['content']}" for h in mem["history"]]
            )
            content += f"POPREDNIE WIADOMOŚCI:\n{history_text}\n\n"
        if context:
            content += f"DANE:\n{context}\n\n"

        if mem:
            content += f"KONTEKST:\n{mem}\n\n"

        content += f"PYTANIE:\n{question}"

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": content}
            ],
            max_tokens=100
        )

        answer = response.choices[0].message.content.strip()

        # ✂️ skracanie jeśli AI się rozpędzi
        sentences = answer.split(". ")
        if len(sentences) > 4:
            answer = ". ".join(sentences[:4])

        return answer

    except Exception as e:
        logger.error(f"AI error: {e}")
        return None

def handle(q: Question, user=None):
    print("HANDLE USER:", user)

    client_id = user["id"] if user else "default"
    print("CLIENT_ID:", client_id)

    RAG_STORE.clear()
    if not check_rate_limit(q.session_id):
        return "⛔ Za dużo zapytań"

    client_id = get_client_id(user) if user else "default"
    mem = update_memory(q, client_id)
    # 📅 REZERWACJA
    if q.data_od and q.data_do:
        if not q.numer_domku:
            return "❌ Podaj numer domku"

        if is_conflict(q.data_od, q.data_do, q.numer_domku, client_id):
            return "❌ Ten termin jest już zajęty"

        db = load_db()
        user_reservations = db.get(client_id, [])

        reservation = {
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "imie": q.imie,
            "nazwisko": q.nazwisko,
            "telefon": q.telefon,
            "email": q.email
        }

        user_reservations.append(reservation)
        db[client_id] = user_reservations
        save_db(db)

        return f"✅ Rezerwacja zapisana: domek {q.numer_domku} od {q.data_od} do {q.data_do}"
    load_rag_for_client(client_id)
    rag = search_rag(q.question, client_id)
    print("CLIENT:", client_id)
    print("RAG:", rag)

    # 🐛 DEBUG RAG
    logger.info(f"RAG results: {rag}")

    if rag:
        logger.info(f"RAG context: {' '.join(rag)}")
    else:
        logger.warning("RAG EMPTY")

    if rag:
        context = " ".join(rag)

        # 🔒 wymuszenie użycia danych
        ai = ai_answer(q.question, context=context, mem=mem, force_context=True)
        if ai:
            history = mem.get("history", [])
            history.append({"role": "assistant", "content": ai})
            mem["history"] = history[-6:]
            memory_service.set(f"{client_id}:{q.session_id or 'default'}", mem)

            return ai

        # fallback jeśli AI nie zadziałało
        return context

    ai = ai_answer(q.question, mem=mem)
    if ai:
        history = mem.get("history", [])
        history.append({"role": "assistant", "content": ai})
        mem["history"] = history[-6:]
        memory_service.set(f"{client_id}:{q.session_id or 'default'}", mem)

        return ai

    return "Chętnie pomogę 🙂 Możesz zapytać o dostępność, ceny albo szczegóły rezerwacji."


# =========================
# 🚀 API
# =========================
@app.post("/ask")
def ask(q: Question, user=Depends(get_current_user)):
    print("USER:", user)
    return handle(q, user)

@app.get("/availability")
def availability(user=Depends(get_current_user)):
    return get_user_reservations(get_client_id(user))


@app.delete("/reservation")
def delete(data: dict, user=Depends(get_current_user)):
    cid = get_client_id(user)
    db = load_db()
    db[cid] = [r for r in db.get(cid, []) if r.get("telefon") != data.get("telefon")]
    save_db(db)
    return {"ok": True}


@app.delete("/unblock")
def unblock(data: dict, user=Depends(get_current_user)):
    cid = get_client_id(user)
    db = load_db()
    db[cid] = [
        r for r in db.get(cid, [])
        if not (r.get("numer_domku") == data.get("numer_domku") and r.get("data_od") == data.get("data_od"))
    ]
    save_db(db)
    return {"ok": True}