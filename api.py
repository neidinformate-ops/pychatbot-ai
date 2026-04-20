# =========================
# IMPORTS
# =========================
import logging
import requests
import stripe
import uuid
import bcrypt
import resend
import os

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
    update_user_by_token,
    get_user_by_reset_token
)

# =========================
# CONFIG
# =========================
RESEND_API_KEY = os.getenv("RESEND_API_KEY")
resend.api_key = RESEND_API_KEY

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

client = OpenAI(api_key=OPENAI_API_KEY)
stripe.api_key = STRIPE_SECRET_KEY

FROM_EMAIL = "onboarding@resend.dev"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

# =========================
# APP
# =========================
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

class ResetData(BaseModel):
    token: str
    password: str

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
# EMAILS
# =========================
def send_verification_email(email: str, token: str):
    link = f"{FRONTEND_URL}/verify?token={token}"

    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": email,
        "subject": "Verify your email",
        "html": f"""
        <h2>Weryfikacja email</h2>
        <a href="{link}">Kliknij aby zweryfikować</a>
        """
    })

def send_reset_email(email: str, token: str):
    link = f"{FRONTEND_URL}/reset-password?token={token}"

    resend.Emails.send({
        "from": FROM_EMAIL,
        "to": email,
        "subject": "Reset hasła",
        "html": f"""
        <h2>Reset hasła</h2>
        <a href="{link}">Resetuj hasło</a>
        """
    })

# =========================
# AUTH
# =========================
@app.post("/register")
def register(data: LoginData):
    email = data.email.strip().to_lowercase() if hasattr(data.email, 'to_lowercase') else data.email.strip().lower()

    if get_user(email):
        raise HTTPException(400, "User exists")

    create_user(email, data.password)

    verify_token = str(uuid.uuid4())

    update_user_by_email(email, {
        "verify_token": verify_token
    })

    send_verification_email(email, verify_token)

    return {"ok": True}


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


@app.post("/resend-verification")
def resend_verification(data: LoginData):
    email = data.email.strip().lower()

    user = get_user(email)

    if not user:
        raise HTTPException(404, "User not found")

    if user.get("email_verified"):
        return {"ok": True}

    verify_token = str(uuid.uuid4())

    update_user_by_email(email, {
        "verify_token": verify_token
    })

    send_verification_email(email, verify_token)

    return {"ok": True}


@app.post("/forgot-password")
def forgot_password(data: LoginData):
    email = data.email.strip().lower()

    user = get_user(email)

    if not user:
        return {"ok": True}

    reset_token = str(uuid.uuid4())

    update_user_by_email(email, {
        "reset_token": reset_token
    })

    send_reset_email(email, reset_token)

    return {"ok": True}


@app.post("/reset-password")
def reset_password(data: ResetData):
    token = data.token

    user = get_user_by_reset_token(token)

    if not user:
        raise HTTPException(400, "Invalid token")

    hashed = bcrypt.hashpw(data.password.encode(), bcrypt.gensalt()).decode()

    update_user_by_token(token, {
        "password": hashed,
        "reset_token": None
    })

    return {"ok": True}


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

    plan = get_plan(client_id)

    return {
        "plan": plan,
        "usage": get_usage(client_id),
        "limit": get_limit(plan)
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
        success_url=f"{FRONTEND_URL}/dashboard",
        cancel_url=f"{FRONTEND_URL}/dashboard",
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