# =========================
# IMPORTS
# =========================
import os
import logging
import requests
import stripe
import uuid
import bcrypt

from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from openai import OpenAI

from auth import (
    create_user,
    create_token,
    get_user,
    get_current_user,
    update_user_by_email,
    get_user_by_verify_token,
    update_user_by_token
)

# =========================
# CONFIG
# =========================
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

client = OpenAI(api_key=OPENAI_API_KEY)
stripe.api_key = STRIPE_SECRET_KEY

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
# MODELS
# =========================
class LoginData(BaseModel):
    email: str
    password: str

class VerifyData(BaseModel):
    token: str

class Question(BaseModel):
    question: str
    session_id: Optional[str] = "default"

# =========================
# RATE LIMIT
# =========================
RATE_LIMIT = {}

def check_rate_limit(client_id):
    now = datetime.now()
    RATE_LIMIT.setdefault(client_id, [])

    RATE_LIMIT[client_id] = [
        t for t in RATE_LIMIT[client_id]
        if now - t < timedelta(minutes=1)
    ]

    if len(RATE_LIMIT[client_id]) > 20:
        raise HTTPException(429, "Too many requests")

    RATE_LIMIT[client_id].append(now)

# =========================
# PLAN + USAGE
# =========================
def get_plan(client_id):
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/subscriptions",
            headers=HEADERS,
            params={"client_id": f"eq.{client_id}"}
        )

        data = res.json()
        if not data:
            return "free"

        return data[0].get("plan", "free")
    except:
        return "free"

def get_limit(plan):
    return {
        "free": 10,
        "pro": 200,
        "business": 999999
    }.get(plan, 10)

def get_usage(client_id):
    try:
        today = str(datetime.now().date())

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/usage",
            headers=HEADERS,
            params={
                "client_id": f"eq.{client_id}",
                "date": f"eq.{today}"
            }
        )

        data = res.json()
        if not data:
            return 0

        return data[0].get("requests", 0)
    except:
        return 0

# =========================
# KNOWLEDGE
# =========================
def get_knowledge(client_id):
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/knowledge",
            headers=HEADERS,
            params={"client_id": f"eq.{client_id}"}
        )

        return [k["content"] for k in res.json()]
    except:
        return []

# =========================
# AUTH
# =========================
@app.post("/register")
def register(data: LoginData):
    email = data.email.strip().lower()

    if get_user(email):
        raise HTTPException(400, "User exists")

    user = create_user(email, data.password)

    verify_token = str(uuid.uuid4())

    update_user_by_email(email, {
        "verify_token": verify_token
    })

    return {
        "ok": True,
        "verify_url": f"http://localhost:5173/verify?token={verify_token}"
    }

@app.post("/verify-email")
def verify_email(data: VerifyData):
    user = get_user_by_verify_token(data.token)

    if not user:
        raise HTTPException(400, "Invalid token")

    update_user_by_token(data.token, {
        "email_verified": True,
        "verify_token": None
    })

    return {"status": "verified"}

@app.post("/login")
def login(data: LoginData):
    email = data.email.strip().lower()

    user = get_user(email)

    if not user:
        raise HTTPException(401)

    if not bcrypt.checkpw(data.password.encode(), user["password"].encode()):
        raise HTTPException(401)

    if not user.get("email_verified"):
        raise HTTPException(403, "Email not verified")

    return {"token": create_token(user["id"])}

# =========================
# CLIENT DATA
# =========================
@app.get("/client-data")
def client_data(user=Depends(get_current_user)):
    client_id = user["id"]

    return {
        "plan": get_plan(client_id),
        "usage": get_usage(client_id),
        "limit": get_limit(get_plan(client_id))
    }

# =========================
# CHAT
# =========================
@app.post("/ask")
def ask(q: Question, user=Depends(get_current_user)):
    client_id = user["id"]

    check_rate_limit(client_id)

    if get_usage(client_id) >= get_limit(get_plan(client_id)):
        return {"error": "LIMIT"}

    context = "\n".join(get_knowledge(client_id)[:5])

    if not context:
        return {"answer": "❌ Brak danych"}

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": "Odpowiadaj krótko i konkretnie"},
            {"role": "user", "content": f"{context}\n\n{q.question}"}
        ]
    )

    return {"answer": response.choices[0].message.content}

# =========================
# STRIPE
# =========================
@app.post("/create-checkout")
def create_checkout(user=Depends(get_current_user)):
    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        success_url="http://localhost:5173/dashboard",
        cancel_url="http://localhost:5173/dashboard",
        metadata={"client_id": user["id"]}
    )

    return {"url": session.url}

@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig, STRIPE_WEBHOOK_SECRET
        )
    except:
        return {"error": "invalid"}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        client_id = session.get("metadata", {}).get("client_id")

        requests.patch(
            f"{SUPABASE_URL}/rest/v1/subscriptions",
            headers=HEADERS,
            json={
                "client_id": client_id,
                "plan": "pro"
            }
        )

    return {"ok": True}