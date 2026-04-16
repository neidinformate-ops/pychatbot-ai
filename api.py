import os
import logging
import requests
import stripe
import uuid
import os

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")

from fastapi import FastAPI, Depends, HTTPException, Header, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Optional
from datetime import datetime, timedelta

from openai import OpenAI
from auth import create_user, verify_password, create_token, get_user, get_current_user

# =========================
# CONFIG
# =========================
client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

SUPABASE_URL = "https://mhsysbmtdwqqptlltfdm.supabase.co"
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

stripe.api_key = os.getenv("STRIPE_SECRET_KEY")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

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
# SECURITY
# =========================
LOGIN_ATTEMPTS = {}
IP_RATE = {}
RATE_LIMIT = {}

def check_login_attempts(email):
    now = datetime.now()
    LOGIN_ATTEMPTS.setdefault(email, [])
    LOGIN_ATTEMPTS[email] = [t for t in LOGIN_ATTEMPTS[email] if now - t < timedelta(minutes=10)]
    if len(LOGIN_ATTEMPTS[email]) > 5:
        raise HTTPException(429, "Too many login attempts")

def record_failed_login(email):
    LOGIN_ATTEMPTS.setdefault(email, []).append(datetime.now())

def check_ip_rate(ip):
    now = datetime.now()
    IP_RATE.setdefault(ip, [])
    IP_RATE[ip] = [t for t in IP_RATE[ip] if now - t < timedelta(minutes=1)]
    if len(IP_RATE[ip]) > 50:
        raise HTTPException(429, "Too many requests")
    IP_RATE[ip].append(now)

def check_rate_limit(client_id):
    now = datetime.now()
    RATE_LIMIT.setdefault(client_id, [])
    RATE_LIMIT[client_id] = [t for t in RATE_LIMIT[client_id] if now - t < timedelta(minutes=1)]
    if len(RATE_LIMIT[client_id]) > 20:
        raise HTTPException(429)
    RATE_LIMIT[client_id].append(now)

def is_safe_input(text):
    blocked = ["ignore previous", "system prompt", "override"]
    return not any(b in text.lower() for b in blocked)

# =========================
# PLAN
# =========================
def get_plan(client_id):
    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/subscriptions",
        headers=HEADERS,
        params={"client_id": f"eq.{client_id}"}
    ).json()

    if not res:
        return "free"
    return res[0].get("plan", "free")

def get_limit(plan):
    return {"free": 10, "pro": 200, "business": 999999}.get(plan, 10)

# =========================
# USAGE
# =========================
def get_usage(client_id):
    try:
        today = str(datetime.now().date())

        response = requests.get(
            f"{SUPABASE_URL}/rest/v1/usage",
            headers=HEADERS,
            params={
                "client_id": f"eq.{client_id}",
                "date": f"eq.{today}"
            }
        )

        if response.status_code != 200:
            print("🔥 SUPABASE ERROR:", response.text)
            return 0

        data = response.json()

        # 🔥 KLUCZOWE — musi być lista
        if not isinstance(data, list) or len(data) == 0:
            return 0

        value = data[0].get("requests", 0)

        return value if isinstance(value, int) else 0

    except Exception as e:
        print("🔥 USAGE CRASH:", str(e))
        return 0

def increment_usage(client_id):
    today = str(datetime.now().date())
    current = get_usage(client_id)

    if current == 0:
        requests.post(
            f"{SUPABASE_URL}/rest/v1/usage",
            headers=HEADERS,
            json={"client_id": client_id, "date": today, "requests": 1}
        )
    else:
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/usage",
            headers=HEADERS,
            params={"client_id": f"eq.{client_id}", "date": f"eq.{today}"},
            json={"requests": current + 1}
        )

# =========================
# API KEYS
# =========================
def create_api_key(client_id):
    key = str(uuid.uuid4())
    requests.post(
        f"{SUPABASE_URL}/rest/v1/api_keys",
        headers=HEADERS,
        json={"client_id": client_id, "key": key}
    )
    return key

def get_client_by_api_key(api_key):
    if not api_key or len(api_key) < 10:
        return None

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/api_keys",
        headers=HEADERS,
        params={"key": f"eq.{api_key}"}
    ).json()

    return res[0]["client_id"] if res else None

# =========================
# CLIENT RESOLVE
# =========================
def resolve_client_id(user=None, api_key=None):
    if user:
        return user["id"]

    if api_key:
        cid = get_client_by_api_key(api_key)
        if cid:
            return cid

    raise HTTPException(status_code=401, detail="Unauthorized")

# =========================
# DB RAG
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
# MODELS
# =========================
class LoginData(BaseModel):
    email: str
    password: str

class Question(BaseModel):
    question: str
    session_id: Optional[str] = "default"

# =========================
# AUTH
# =========================
@app.post("/login")
def login(data: LoginData):
    check_login_attempts(data.email)

    user = get_user(data.email)

    if not user or not verify_password(data.password, user["password"]):
        record_failed_login(data.email)
        raise HTTPException(401)

    return {"token": create_token(user["id"])}

@app.post("/register")
def register(data: LoginData):
    existing = get_user(data.email)

    if existing:
        raise HTTPException(status_code=400, detail="User exists")

    user = create_user(data.email, data.password)

    return {"ok": True, "user": user["email"]}

# =========================
# API KEYS ENDPOINTS
# =========================
@app.post("/create-api-key")
def create_key(user=Depends(get_current_user)):
    return {"api_key": create_api_key(user["id"])}

@app.get("/api-keys")
def list_api_keys(user=Depends(get_current_user)):
    client_id = user["id"]

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/api_keys",
        headers=HEADERS,
        params={"client_id": f"eq.{client_id}"}
    )

    return res.json()

@app.delete("/api-key/{kid}")
def delete_api_key(kid: str, user=Depends(get_current_user)):
    client_id = user["id"]

    requests.delete(
        f"{SUPABASE_URL}/rest/v1/api_keys",
        headers=HEADERS,
        params={
            "id": f"eq.{kid}",
            "client_id": f"eq.{client_id}"
        }
    )

    return {"ok": True}

# =========================
# KNOWLEDGE ENDPOINTS
# =========================
@app.get("/knowledge")
def list_knowledge(user=Depends(get_current_user)):
    client_id = user["id"]

    res = requests.get(
        f"{SUPABASE_URL}/rest/v1/knowledge",
        headers=HEADERS,
        params={"client_id": f"eq.{client_id}"}
    )

    return res.json()

@app.delete("/knowledge/{kid}")
def delete_knowledge(kid: str, user=Depends(get_current_user)):
    client_id = user["id"]

    requests.delete(
        f"{SUPABASE_URL}/rest/v1/knowledge",
        headers=HEADERS,
        params={
            "id": f"eq.{kid}",
            "client_id": f"eq.{client_id}"
        }
    )

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
# CHAT
# =========================
@app.post("/ask")
def ask(q: Question, request: Request, user=Depends(get_current_user), x_api_key: str = Header(None)):
    ip = request.client.host
    check_ip_rate(ip)

    if not is_safe_input(q.question):
        return {"answer": "❌ Niepoprawne zapytanie"}

    client_id = resolve_client_id(user, x_api_key)

    check_rate_limit(client_id)

    plan = get_plan(client_id)
    limit = get_limit(plan)
    usage = get_usage(client_id)

    if usage >= limit:
        return {"answer": f"🔒 Limit planu ({plan}) osiągnięty"}

    save_message(client_id, q.session_id, "user", q.question)

    knowledge = get_knowledge(client_id)
    history = get_history(client_id, q.session_id)

    context = "\n".join(knowledge[:5])

    if not context.strip():
        return {"answer": "❌ Brak danych"}

    messages = [{"role": "system", "content": "STRICT MODE"}]

    for m in reversed(history):
        messages.append({"role": m["role"], "content": m["text"]})

    messages.append({"role": "user", "content": context + "\n\n" + q.question})

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=messages
    )

    answer = response.choices[0].message.content

    requests.post(
        f"{SUPABASE_URL}/rest/v1/ai_logs",
        headers=HEADERS,
        json={
            "client_id": client_id,
            "question": q.question,
            "answer": answer,
            "score": 1
        }
    )

    increment_usage(client_id)
    save_message(client_id, q.session_id, "assistant", answer)

    return {"answer": answer}
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
        print("🔥 SETUP ERROR:", str(e))
        return {"status": "error"}
# =========================
# STRIPE
# =========================
@app.post("/create-checkout")
def create_checkout(user=Depends(get_current_user)):
    try:
        session = stripe.checkout.Session.create(
            payment_method_types=["card"],
            line_items=[{
                "price": STRIPE_PRICE_ID,
                "quantity": 1,
            }],
            mode="subscription",

            # 🔥 KLUCZOWE
            metadata={
                "client_id": user["id"]  # lub user["email"] jeśli tak masz
            },

            success_url="http://localhost:5173/dashboard?success=true",
            cancel_url="http://localhost:5173/dashboard?canceled=true",
        )

        return {"url": session.url}

    except Exception as e:
        print("🔥 STRIPE ERROR:", str(e))
        raise HTTPException(status_code=500, detail="Stripe error")

# =========================
# WEBHOOK
# =========================
@app.post("/webhook")
async def webhook(request: Request):
    payload = await request.body()
    sig = request.headers.get("stripe-signature")

    if not STRIPE_WEBHOOK_SECRET:
        return {"error": "no webhook secret"}

    try:
        event = stripe.Webhook.construct_event(
            payload,
            sig,
            STRIPE_WEBHOOK_SECRET
        )
    except Exception:
        return {"error": "invalid webhook"}

    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]
        client_id = session["metadata"]["client_id"]

        requests.post(
            f"{SUPABASE_URL}/rest/v1/subscriptions",
            headers=HEADERS,
            json={"client_id": client_id, "plan": "pro"}
        )

    if event["type"] in ["customer.subscription.deleted", "invoice.payment_failed"]:
        sub = event["data"]["object"]
        client_id = sub.get("metadata", {}).get("client_id")

        if client_id:
            requests.post(
                f"{SUPABASE_URL}/rest/v1/subscriptions",
                headers=HEADERS,
                json={"client_id": client_id, "plan": "free"}
            )

    return {"ok": True}