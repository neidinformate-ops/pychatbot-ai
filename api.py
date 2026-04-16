# =========================
# IMPORTS
# =========================
import os
import logging
import requests
import stripe
import uuid

from datetime import datetime, timedelta
from typing import Optional

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

from openai import OpenAI

from auth import (
    create_user,
    verify_password,
    create_token,
    get_user,
    get_current_user
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

class Question(BaseModel):
    question: str
    session_id: Optional[str] = "default"

# =========================
# SECURITY (LIGHT VERSION)
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
# PLAN
# =========================
def get_plan(client_id):
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/subscriptions",
            headers=HEADERS,
            params={"client_id": f"eq.{client_id}"}
        )

        if res.status_code != 200:
            return "free"

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

# =========================
# USAGE
# =========================
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

        if res.status_code != 200:
            return 0

        data = res.json()

        if not isinstance(data, list) or len(data) == 0:
            return 0

        return data[0].get("requests", 0)

    except:
        return 0

def increment_usage(client_id):
    res = supabase.table("usage").select("*").eq("client_id", client_id).execute()

    if not res.data:
        supabase.table("usage").insert({
            "client_id": client_id,
            "requests": 1
        }).execute()
    else:
        current = res.data[0]["requests"]

        supabase.table("usage").update({
            "requests": current + 1
        }).eq("client_id", client_id).execute()

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

        if res.status_code != 200:
            return []

        return [k["content"] for k in res.json()]

    except:
        return []

# =========================
# AUTH
# =========================
@app.post("/login")
def login(data: LoginData):
    user = get_user(data.email)

    if not user or not verify_password(data.password, user["password"]):
        raise HTTPException(401)

    return {"token": create_token(user["id"])}

@app.post("/register")
def register(data: LoginData):
    if get_user(data.email):
        raise HTTPException(400, "User exists")

    user = create_user(data.email, data.password)
    return {"ok": True}

# =========================
# CLIENT DATA
# =========================
@app.get("/client-data")
def client_data(user=Depends(get_current_user)):
    client_id = user["id"]

    plan = get_plan(client_id)
    usage = get_usage(client_id)
    limit = get_limit(plan)

    return {
        "plan": plan,
        "usage": usage,
        "limit": limit
    }

# =========================
# CHAT (ULEPSZONY AI)
# =========================
@app.post("/ask")
def ask(q: Question, user=Depends(get_current_user)):
    client_id = user["id"]

    check_rate_limit(client_id)

    plan = get_plan(client_id)
    limit = get_limit(plan)
    usage = get_usage(client_id)

    if usage >= limit:
        return {"error": "LIMIT"}

    knowledge = get_knowledge(client_id)

    context = "\n".join(knowledge[:5])

    if not context.strip():
        return {"answer": "❌ Brak danych"}

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {
                "role": "system",
                "content": (
                    "Jesteś asystentem sprzedażowym. "
                    "Odpowiadaj konkretnie, krótko i na temat. "
                    "Nie wymyślaj danych."
                )
            },
            {
                "role": "user",
                "content": f"{context}\n\nPytanie: {q.question}"
            }
        ]
    )

    answer = response.choices[0].message.content

    increment_usage(client_id)

    return {"answer": answer}

# =========================
# KNOWLEDGE UPLOAD
# =========================
@app.post("/client/setup")
def setup_client(data: dict, user=Depends(get_current_user)):
    try:
        client_id = user["id"]
        text = data.get("text", "")

        if not text:
            return {"status": "empty"}

        requests.post(
            f"{SUPABASE_URL}/rest/v1/knowledge",
            headers=HEADERS,
            json={
                "client_id": client_id,
                "content": text
            }
        )

        return {"status": "ok"}

    except Exception as e:
        logging.error(f"SETUP ERROR: {str(e)}")
        return {"status": "error"}

# =========================
# STRIPE CHECKOUT
# =========================
@app.post("/cancel-subscription")
def cancel_subscription(client_id: str = Depends(get_current_user)):
    client = supabase.table("clients").select("*").eq("id", client_id).execute()

    if not client.data:
        return {"error": "Client not found"}

    subscription_id = client.data[0].get("stripe_subscription_id")

    if not subscription_id:
        return {"error": "No subscription"}

    try:
        stripe.Subscription.delete(subscription_id)

        return {"status": "cancel_requested"}

    except Exception as e:
        return {"error": str(e)}
@app.post("/create-checkout")
def create_checkout(client_id: str = Depends(get_current_user)):
    try:
        session = stripe.checkout.Session.create(
            mode="subscription",
            payment_method_types=["card"],
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }],
            success_url="http://localhost:5173/dashboard",
            cancel_url="http://localhost:5173/dashboard",
            metadata={
                "client_id": client_id
            }
        )

        return {"url": session.url}

    except Exception as e:
        print("🔥 STRIPE ERROR:", e)
        return {"error": str(e)}

    except Exception as e:
        logging.error(f"STRIPE ERROR: {str(e)}")
        raise HTTPException(500, "Stripe error")

# =========================
# BILLING PORTAL
# =========================
@app.post("/billing-portal")
def billing_portal(user=Depends(get_current_user)):
    try:
        session = stripe.billing_portal.Session.create(
            customer=user["id"],  # działa jako placeholder
            return_url="http://localhost:5173/dashboard"
        )

        return {"url": session.url}

    except Exception as e:
        logging.error(f"BILLING ERROR: {str(e)}")
        raise HTTPException(500)

# =========================
# WEBHOOK (SAFE + STABLE)
# =========================
@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    sig_header = request.headers.get("stripe-signature")

    try:
        event = stripe.Webhook.construct_event(
            payload, sig_header, STRIPE_WEBHOOK_SECRET
        )
    except Exception as e:
        print("❌ Webhook verify error:", e)
        return {"status": "error"}

    # 🔥 CHECKOUT SUCCESS
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        client_id = session.get("metadata", {}).get("client_id")

        if not client_id:
            print("❌ Missing client_id")
            return {"status": "no client_id"}

        customer_id = session.get("customer")
        subscription_id = session.get("subscription")

        supabase.table("clients").update({
            "plan": "pro",
            "stripe_customer_id": customer_id,
            "stripe_subscription_id": subscription_id,
            "subscription_status": "active"
        }).eq("id", client_id).execute()

        print("✅ SUBSCRIPTION ACTIVATED")

    # 🔥 SUBSCRIPTION CANCEL / EXPIRE
    elif event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]
        subscription_id = sub["id"]

        supabase.table("clients").update({
            "plan": "free",
            "subscription_status": "canceled"
        }).eq("stripe_subscription_id", subscription_id).execute()

        print("⚠️ SUBSCRIPTION CANCELED")

    # 🔥 PAYMENT FAILED
    elif event["type"] == "invoice.payment_failed":
        sub = event["data"]["object"]

        subscription_id = sub.get("subscription")

        supabase.table("clients").update({
            "subscription_status": "past_due"
        }).eq("stripe_subscription_id", subscription_id).execute()

        print("⚠️ PAYMENT FAILED")

    return {"status": "success"}

