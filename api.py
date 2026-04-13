import os
import json
import logging
import requests
import numpy as np
import faiss

from fastapi import FastAPI, Depends, HTTPException, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from openai import OpenAI
from auth import create_user, verify_password, create_token, get_user, get_current_user

# =========================
# 🔥 CONFIG
# =========================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SUPABASE_URL = "https://mhsysbmtdwqqptlltfdm.supabase.co"
SUPABASE_KEY = "sb_publishable_2BOeHJS5wkepQRZo5mMDtw_C4vd1WOq"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

# =========================
# 🔥 MULTI TENANT
# =========================
def resolve_client_id(user=None, x_client_id: str = None):
    if user:
        return user["id"]
    if x_client_id:
        return x_client_id
    return "public"

# =========================
# 🧠 RAG (STARY — ZOSTAJE)
# =========================
def load_rag(client_id):
    try:
        txt_file = f"Dane_{client_id}.txt"

        if not os.path.exists(txt_file):
            return None

        with open(txt_file, "r", encoding="utf-8") as f:
            text = f.read()

        chunks = text.split("\n\n")[:50]

        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=chunks
        )

        vectors = [e.embedding for e in emb.data]

        index = faiss.IndexFlatL2(len(vectors[0]))
        index.add(np.array(vectors).astype("float32"))

        return {"index": index, "data": chunks}

    except Exception as e:
        print("RAG ERROR:", e)
        return None


def search_rag(query, client_id):
    rag = load_rag(client_id)

    if not rag:
        return []

    emb = client.embeddings.create(
        model="text-embedding-3-small",
        input=query
    )

    q_vec = np.array([emb.data[0].embedding]).astype("float32")
    D, I = rag["index"].search(q_vec, 3)

    return [rag["data"][i] for i in I[0]]

# =========================
# 🧠 RAG 2.0 (NOWY)
# =========================
def get_knowledge(client_id):
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/knowledge",
        headers=HEADERS,
        params={"client_id": f"eq.{client_id}"}
    )
    return [k["content"] for k in res.json()]


def get_history(client_id, session_id):
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/messages",
        headers=HEADERS,
        params={
            "client_id": f"eq.{client_id}",
            "session_id": f"eq.{session_id}",
            "order": "created_at.desc",
            "limit": "6"
        }
    )
    return res.json()


def save_message(client_id, session_id, role, text):
    requests.post(
        f"{SUPABASE_URL}/rest/v1/messages",
        headers=HEADERS,
        json={
            "client_id": client_id,
            "session_id": session_id,
            "role": role,
            "text": text
        }
    )

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
def client_setup(data: ClientSetupData, user=Depends(get_current_user)):
    client_id = resolve_client_id(user)

    # 🔥 zapis do pliku (stary RAG)
    with open(f"Dane_{client_id}.txt", "w") as f:
        f.write(data.text)

    # 🔥 zapis do DB (nowy RAG)
    requests.post(
        f"{SUPABASE_URL}/rest/v1/knowledge",
        headers=HEADERS,
        json={
            "client_id": client_id,
            "content": data.text
        }
    )

    return {"ok": True}

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

# =========================
# 📅 RESERVATIONS
# =========================
def check_conflict(client_id, data_od, data_do, numer_domku):
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/reservations",
        headers=HEADERS,
        params={"client_id": f"eq.{client_id}"}
    ).json()

    for r in res:
        if r["numer_domku"] != numer_domku:
            continue

        if data_od < r["data_do"] and data_do > r["data_od"]:
            return True

    return False

@app.post("/reservation")
def create_reservation(data: dict, user=Depends(get_current_user), x_client_id: str = Header(None)):
    client_id = resolve_client_id(user, x_client_id)

    if check_conflict(client_id, data["data_od"], data["data_do"], data["numer_domku"]):
        raise HTTPException(status_code=400, detail="Termin zajęty")

    payload = {
        "client_id": client_id,
        "numer_domku": data["numer_domku"],
        "data_od": data["data_od"],
        "data_do": data["data_do"],
        "email": data["email"]
    }

    requests.post(f"{SUPABASE_URL}/rest/v1/reservations", headers=HEADERS, json=payload)

    return {"ok": True}

@app.get("/availability")
def availability(user=Depends(get_current_user), x_client_id: str = Header(None)):
    client_id = resolve_client_id(user, x_client_id)

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/reservations",
        headers=HEADERS,
        params={"client_id": f"eq.{client_id}"}
    )

    return res.json()

# =========================
# 🤖 CHAT (RAG 2.0 + MEMORY)
# =========================
@app.post("/ask")
def ask(q: Question, user=Depends(get_current_user), x_client_id: str = Header(None)):
    client_id = resolve_client_id(user, x_client_id)

    # 👉 rezerwacja przez chat
    if q.data_od and q.data_do:
        return create_reservation(q.dict(), user, x_client_id)

    # 💾 zapisz user
    save_message(client_id, q.session_id, "user", q.question)

    # 🧠 knowledge DB
    knowledge = get_knowledge(client_id)

    # 🧠 stary RAG fallback
    rag = search_rag(q.question, client_id)

    # 💬 history
    history = get_history(client_id, q.session_id)

    context_parts = []

    if knowledge:
        context_parts.append(" ".join(knowledge[:3]))

    if rag:
        context_parts.append(" ".join(rag))

    context = "\n".join(context_parts)

    messages = [
        {"role": "system", "content": "Jesteś asystentem klienta. Pomagasz w rezerwacjach."}
    ]

    for m in reversed(history):
        messages.append({
            "role": m["role"],
            "content": m["text"]
        })

    messages.append({
        "role": "user",
        "content": context + "\n\n" + q.question
    })

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages,
        max_tokens=150
    )

    answer = response.choices[0].message.content

    # 💾 zapisz AI
    save_message(client_id, q.session_id, "assistant", answer)

    return {"answer": answer}