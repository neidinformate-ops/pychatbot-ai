import os
import json
from datetime import datetime
import logging
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
    TTL = 600  # 10 minut

    # 🔥 TTL check
    if client_id in RAG_STORE:
        created = RAG_STORE[client_id].get("created_at")

        if created and time.time() - created < TTL:
            return
        else:
            RAG_STORE.pop(client_id, None)

    # 🔥 kontrola cache
    if len(RAG_STORE) > 100:
        oldest_client = min(
            RAG_STORE.items(),
            key=lambda x: x[1].get("created_at", time.time())
        )[0]

        RAG_STORE.pop(oldest_client, None)
    try:
        index_file = f"rag_{client_id}.index"
        data_file = f"rag_{client_id}.json"
        txt_file = f"Dane_{client_id}.txt"
        logger.info(f"SZUKAM PLIKU: {txt_file}")

        if os.path.exists(index_file) and os.path.exists(data_file):
            index = faiss.read_index(index_file)
            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            RAG_STORE[client_id] = {
                "index": index,
                "data": data,
                "created_at": time.time()
            }
            return

        if not os.path.exists(txt_file):
            return

        with open(txt_file, "r", encoding="utf-8") as f:
            raw = f.read()

        chunks = []
        current = ""


        for line in raw.split("\n"):
            line = line.strip()
            if not line:
                continue

            # nowy chunk gdy zaczyna się pytanie
            if line.lower().startswith("pytanie"):
                if current:
                    chunks.append(current.strip())
                current = line
            else:
                current += " " + line

        # ostatni chunk
        if current:
            chunks.append(current.strip())

        # 🔥 NOWE — usuwamy za krótkie i za długie
        chunks = [
            c for c in chunks
            if 50 < len(c) < 500
        ]

        # limit
        chunks = chunks[:100]

        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=chunks
        )

        embeddings = [e.embedding for e in emb.data]

        if not embeddings:
            logger.error(f"Brak embeddings dla {client_id}")
            return

        dim = len(embeddings[0])
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(embeddings).astype("float32"))

        RAG_STORE[client_id] = {
            "index": index,
            "data": chunks,
            "created_at": time.time()
        }
        faiss.write_index(index, index_file)
        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

    except Exception as e:
        logger.error(f"RAG error ({client_id}): {e}")


def search_rag(query, client_id, k=3):
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

    for i, idx in enumerate(I[0]):
        if idx < len(data) and D[0][i] < 2.0:
            results.append(data[idx])

    if not results:
        return sorted(data, key=lambda x: len(x), reverse=True)[:2]

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
        # 🔥 LIMIT pamięci (ochrona przed memory leak)
        if len(self.store) > 1000:
            # usuń tylko najstarszy wpis
            first_key = next(iter(self.store))
            self.store.pop(first_key)

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

    # usuń stare requesty
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
    session_key = f"{client_id}:{q.session_id}"

    mem = memory_service.get_memory(session_key)

    history = mem.get("history", [])
    history.append({"role": "user", "content": q.question})

    history = history[-6:]

    mem["history"] = history

    memory_service.set(session_key, mem)

    return mem

def ai_answer(question, context=None, mem=None, force_context=False):
    try:
        if not os.getenv("OPENAI_API_KEY"):
            return None
        response = None
        system_prompt = """
        Jesteś chatbotem firmy.

        Masz dostęp do danych firmy (sekcja DANE).

        Zasady:
        1. Odpowiadaj TYLKO na podstawie sekcji DANE
        2. Jeśli brak informacji → powiedz to jasno
        3. NIE zgaduj
        4. NIE dodawaj nic spoza danych

        Jak odpowiadać:
        - konkretnie
        - krótko (2–4 zdania)
        - używaj informacji z DANE

        Priorytet:
        DANE > HISTORIA > własna wiedza
        """

        content = ""

        # 🧠 historia
        if mem and mem.get("history"):
            history_text = "\n".join(
                [f"{h['role']}: {h['content']}" for h in mem["history"]]
            )
            content += f"HISTORIA:\n{history_text}\n\n"

        # 📚 RAG
        if context:
            content += f"DANE:\n{context}\n\n"

        # ❓ pytanie
        content += f"AKTUALNE PYTANIE:\n{question}"

        for _ in range(2):  # 🔁 2 próby
            try:
                response = client.chat.completions.create(
                    model="gpt-4o-mini",
                    messages=[
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": content}
                    ],
                    max_tokens=100,
                    timeout=10
                )
                break
            except Exception as e:
                logger.error(f"OpenAI retry error: {e}")
                time.sleep(1)

        if not response:
            return None
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
    client_id = get_client_id(user) if user else "default"
    logger.info(f"CLIENT: {client_id}")
    session_key = f"{client_id}:{q.session_id}"

    # 🚦 rate limit
    if not check_rate_limit(session_key):
        return "⛔ Za dużo zapytań"

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

    # 🧠 RAG
    load_rag_for_client(client_id)

    rag = search_rag(q.question, client_id)
    logger.info(f"RAG: {rag}")

    rag = [r for r in rag if len(r) > 20]

    if not rag:
        logger.warning(f"Empty RAG for {client_id}")
        return "Nie mam informacji w bazie na ten temat."

    # 🔥 wybierz najlepsze chunki (dłuższe = więcej info)
    rag = sorted(rag, key=lambda x: len(x), reverse=True)

    context = " ".join(rag[:2])[:1000]
    logger.info(f"FINAL CONTEXT: {context}")

    # 🧠 MEMORY
    # 🧠 MEMORY (user)
    mem = update_memory(q, client_id)

    # 🤖 AI
    ai = ai_answer(q.question, context=context, mem=mem)

    if ai:
        # 🧠 pobierz świeżą pamięć
        mem = memory_service.get_memory(session_key)

        history = mem.get("history", [])
        history.append({"role": "assistant", "content": ai})
        mem["history"] = history[-6:]

        memory_service.set(session_key, mem)

        return ai


    return "Nie mam wystarczających danych, żeby odpowiedzieć."


# =========================
# 🚀 API
# =========================
@app.post("/ask")
def ask(q: Question, user=Depends(get_current_user)):
    logger.info(f"USER: {user}")
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