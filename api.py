import os
import logging
import requests
import numpy as np
import faiss
import stripe

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime, timedelta

from openai import OpenAI
from auth import create_user, verify_password, create_token, get_user, get_current_user

# =========================
# 🔥 CONFIG
# =========================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SUPABASE_URL = "https://mhsysbmtdwqqptlltfdm.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")  # 🔥 FIX

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# 🔐 STRIPE
stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

app = FastAPI()

# 🔥 CORS (FIX – tylko raz)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

logging.basicConfig(level=logging.INFO)

# =========================
# 🚦 RATE LIMIT
# =========================
RATE_LIMIT = {}

def check_rate_limit(client_id):
    now = datetime.now()

    if client_id not in RATE_LIMIT:
        RATE_LIMIT[client_id] = []

    RATE_LIMIT[client_id] = [
        t for t in RATE_LIMIT[client_id]
        if now - t < timedelta(minutes=1)
    ]

    if len(RATE_LIMIT[client_id]) > 20:
        raise HTTPException(status_code=429, detail="Too many requests")

    RATE_LIMIT[client_id].append(now)

# =========================
# 📊 PLAN
# =========================
def get_plan(client_id):
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/subscriptions",
        headers=HEADERS,
        params={"client_id": f"eq.{client_id}"}
    ).json()

    if res and res[0].get("plan") == "pro":
        return "pro"

    return "free"

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
# 🧠 RAG 2.0
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

    with open(f"Dane_{client_id}.txt", "w") as f:
        f.write(data.text)

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
# 🤖 CHAT
# =========================
@app.post("/ask")
def ask(q: Question, user=Depends(get_current_user), x_client_id: str = Header(None)):
    client_id = resolve_client_id(user, x_client_id)

    check_rate_limit(client_id)

    save_message(client_id, q.session_id, "user", q.question)

    knowledge = get_knowledge(client_id)
    rag = search_rag(q.question, client_id)
    history = get_history(client_id, q.session_id)

    context_parts = []

    if knowledge:
        context_parts.append(" ".join(knowledge[:3]))

    if rag:
        context_parts.append(" ".join(rag))

    context = "\n".join(context_parts)

    if not context.strip():
        return {"answer": "❌ Nie mam danych dla tego biznesu."}

    # 🧠 BUSINESS DETECTION
    def detect_business(context):
        context = context.lower()
        if "barber" in context:
            return "barber"
        if "nocleg" in context:
            return "hotel"
        if "produkt" in context:
            return "shop"
        return "general"

    business = detect_business(context)

    tone = {
        "barber": "luźny",
        "hotel": "profesjonalny",
        "shop": "sprzedażowy"
    }.get(business, "neutralny")

    messages = [
        {
            "role": "system",
            "content": f"""
Jesteś AI asystentem biznesowym.

STYL: {tone}

ZASADY:
- odpowiadaj tylko na podstawie danych
- nie zgaduj
- jeśli brak danych → napisz "Nie mam tej informacji"
"""
        }
    ]

    for m in reversed(history):
        messages.append({"role": m["role"], "content": m["text"]})

    messages.append({
        "role": "user",
        "content": context + "\n\n" + q.question
    })

    # 🔥 FIX (brakowało tego)
    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    answer = response.choices[0].message.content

    # 📊 SCORING
    score = 0
    if len(answer) > 20: score += 1
    if "Nie mam" not in answer: score += 1

    requests.post(
        f"{SUPABASE_URL}/rest/v1/ai_logs",
        headers=HEADERS,
        json={
            "client_id": client_id,
            "question": q.question,
            "answer": answer,
            "score": score
        }
    )

    save_message(client_id, q.session_id, "assistant", answer)

    return {"answer": answer}

# =========================
# 💳 STRIPE CHECKOUT
# =========================

@app.post("/create-checkout")
def create_checkout(user=Depends(get_current_user)):
    try:
        client_id = user["id"]

        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            mode="subscription",
            line_items=[{
                "price": os.getenv("STRIPE_PRICE_ID"),  # 🔥 z ENV
                "quantity": 1
            }],
            success_url="https://web-production-1de94.up.railway.app",
            cancel_url="https://web-production-1de94.up.railway.app",
            metadata={"client_id": client_id}
        )

        return {"url": session.url}

    except Exception as e:
        print("🔥 STRIPE ERROR:", str(e))
        return {"error": str(e)}

# =========================
# 🔔 STRIPE WEBHOOK
# =========================
@app.post("/webhook")
async def stripe_webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig_header,
            STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        print("❌ WEBHOOK ERROR:", e)
        return {"error": "invalid"}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        client_id = session["metadata"]["client_id"]

        requests.post(
            f"{SUPABASE_URL}/rest/v1/subscriptions",
            headers=HEADERS,
            json={
                "client_id": client_id,
                "plan": "pro"
            }
        )

        print("🔥 USER UPGRADED:", client_id)

    return {"ok": True}