import os
import json
from datetime import datetime
import logging
import time

from fastapi import FastAPI, Depends, HTTPException, Header
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
# 🔥 MULTI TENANT CORE
# =========================
def resolve_client_id(user=None, x_client_id: str = None):
    if user:
        return user["id"]

    if x_client_id:
        return x_client_id

    return "public"


# =========================
# 🧠 RAG
# =========================
RAG_STORE = {}

def load_rag_for_client(client_id):
    TTL = 600

    if client_id in RAG_STORE:
        created = RAG_STORE[client_id].get("created_at")
        if created and time.time() - created < TTL:
            return
        else:
            RAG_STORE.pop(client_id, None)

    try:
        index_file = f"rag_{client_id}.index"
        data_file = f"rag_{client_id}.json"
        txt_file = f"Dane_{client_id}.txt"

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

        chunks = raw.split("\n\n")[:100]

        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=chunks
        )

        embeddings = [e.embedding for e in emb.data]

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
            json.dump(chunks, f)

    except Exception as e:
        logger.error(f"RAG error: {e}")


def search_rag(query, client_id, k=3):
    if client_id not in RAG_STORE:
        return []

    index = RAG_STORE[client_id]["index"]
    data = RAG_STORE[client_id]["data"]

    emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )

    q_vec = np.array([emb.data[0].embedding]).astype("float32")
    D, I = index.search(q_vec, k)

    return [data[i] for i in I[0] if i < len(data)]


# =========================
# 💾 DB
# =========================
def load_db():
    try:
        with open("db.json", "r") as f:
            return json.load(f)
    except:
        return {}

def save_db(data):
    with open("db.json", "w") as f:
        json.dump(data, f, indent=2)


def is_conflict(data_od, data_do, numer_domku, client_id):
    reservations = load_db().get(client_id, [])

    for r in reservations:
        if r["numer_domku"] != numer_domku:
            continue

        r_od = datetime.fromisoformat(r["data_od"])
        r_do = datetime.fromisoformat(r["data_do"])
        new_od = datetime.fromisoformat(data_od)
        new_do = datetime.fromisoformat(data_do)

        if new_od < r_do and new_do > r_od:
            return True

    return False


def get_user_reservations(client_id):
    return load_db().get(client_id, [])


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
def client_setup(
    data: ClientSetupData,
    user=Depends(get_current_user)
):
    client_id = resolve_client_id(user)

    with open(f"Dane_{client_id}.txt", "w") as f:
        f.write(data.text)

    RAG_STORE.pop(client_id, None)


# =========================
# 📦 MODEL
# =========================
class Question(BaseModel):
    question: str
    session_id: Optional[str] = "default"
    numer_domku: Optional[str] = None
    data_od: Optional[str] = None
    data_do: Optional[str] = None
    email: Optional[EmailStr] = None

    @validator("telefon", check_fields=False)
    def validate_phone(cls, v):
        return v


# =========================
# 🤖 LOGIKA
# =========================
def handle(q: Question, client_id: str):

    if q.data_od and q.data_do:
        if is_conflict(q.data_od, q.data_do, q.numer_domku, client_id):
            return "❌ Termin zajęty"

        db = load_db()
        reservations = db.get(client_id, [])

        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "email": q.email
        })

        db[client_id] = reservations
        save_db(db)

        return "✅ Rezerwacja zapisana"

    load_rag_for_client(client_id)

    rag = search_rag(q.question, client_id)

    if not rag:
        return "Brak danych"

    context = " ".join(rag[:2])

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Odpowiadaj tylko na podstawie danych"},
            {"role": "user", "content": context + "\n\n" + q.question}
        ],
        max_tokens=100
    )

    return response.choices[0].message.content


# =========================
# 🚀 API
# =========================
@app.post("/ask")
def ask(
    q: Question,
    user=Depends(get_current_user),
    x_client_id: str = Header(None)
):
    client_id = resolve_client_id(user, x_client_id)
    result = handle(q, client_id)

    return {"answer": result}


@app.get("/availability")
def availability(
    user=Depends(get_current_user),
    x_client_id: str = Header(None)
):
    client_id = resolve_client_id(user, x_client_id)
    return get_user_reservations(client_id)


@app.delete("/reservation")
def delete(
    data: dict,
    user=Depends(get_current_user),
    x_client_id: str = Header(None)
):
    cid = resolve_client_id(user, x_client_id)

    db = load_db()
    db[cid] = [
        r for r in db.get(cid, [])
        if r.get("telefon") != data.get("telefon")
    ]

    save_db(db)

    return {"ok": True}