# =========================
# IMPORTS
# =========================
from dotenv import load_dotenv

load_dotenv(override=True)
from fastapi import UploadFile, File
from supabase import create_client
import os
import uuid
import logging
import stripe
import uuid
import json
import asyncio
import bcrypt
import resend
import os
import requests
from bs4 import BeautifulSoup
import math
from datetime import datetime, timedelta
from app.routers.assistants import router as assistants_router

app.include_router(
    assistants_router
)
from app.routers.assistant_knowledge import router as assistant_knowledge_router

app.include_router(
    assistant_knowledge_router
)
from app.routers.assistant_uploads import router as assistant_upload_router

app.include_router(

assistant_upload_router

)
from app.routers.assistant_prompts import router as assistant_prompts_router

app.include_router(
    assistant_prompts_router
)
from app.routers.assistant_ai_generator import router as ai_generator_router

app.include_router(

ai_generator_router

)
from app.routers.assistant_widgets import router as assistant_widgets_router

app.include_router(
    assistant_widgets_router
)
from app.routers.assistant_conversations import router as conversations_router

app.include_router(

conversations_router

)
from app.routers.assistant_leads import router as assistant_leads_router

app.include_router(
    assistant_leads_router
)
from app.routers.assistant_analytics import router as assistant_analytics_router

app.include_router(
    assistant_analytics_router
)
from app.routers.assistant_bookings import router as assistant_bookings_router

app.include_router(

assistant_bookings_router

)
from app.routers.assistant_branding import router as assistant_branding_router

app.include_router(
    assistant_branding_router
)
from typing import Optional
from app.services.usage_service import check_limit, increment_usage
from fastapi import FastAPI, Depends, HTTPException, Request
app = FastAPI()
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from app.services.usage_service import check_limit, get_usage, get_limit
from openai import OpenAI
from fastapi.responses import StreamingResponse
from fastapi.responses import FileResponse
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
print("OPENAI KEY LOADED")
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

supabase = create_client(
    SUPABASE_URL,
    SUPABASE_KEY
)

STRIPE_SECRET_KEY = os.getenv("STRIPE_SECRET_KEY")
STRIPE_PRICE_ID = os.getenv("STRIPE_PRICE_ID")
STRIPE_WEBHOOK_SECRET = os.getenv("STRIPE_WEBHOOK_SECRET")

FRONTEND_URL = os.getenv("FRONTEND_URL", "http://localhost:5173")

if not OPENAI_API_KEY:
    raise Exception(
        "Missing OPENAI_API_KEY"
    )

client = OpenAI(
    api_key=OPENAI_API_KEY
)
stripe.api_key = STRIPE_SECRET_KEY

FROM_EMAIL = "onboarding@resend.dev"

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json",
    "x-upsert": "true"
}

# =========================
# ANALYTICS HELPERS
# =========================

def track_widget_event(
    client_id: str,
    event_type: str,
    session_id: str = None,
    metadata: dict = None
):
    try:

        requests.post(
            f"{SUPABASE_URL}/rest/v1/widget_events",

            headers=HEADERS,

            json={
                "client_id": client_id,
                "session_id": session_id,
                "event_type": event_type,
                "metadata": metadata or {}
            }
        )

    except Exception as e:

        print(
            "TRACK EVENT ERROR:",
            e
        )


def track_usage_event(
    client_id: str,
    event_type: str
):
    try:

        requests.post(
            f"{SUPABASE_URL}/rest/v1/usage_events",

            headers=HEADERS,

            json={
                "client_id": client_id,
                "event_type": event_type
            }
        )

    except Exception as e:

        print(
            "USAGE EVENT ERROR:",
            e
        )


def update_daily_analytics(
    client_id: str,
    field: str
):
    try:

        today = datetime.utcnow().date().isoformat()

        existing = requests.get(
            f"{SUPABASE_URL}/rest/v1/analytics_daily",

            headers=HEADERS,

            params={
                "client_id": f"eq.{client_id}",
                "day": f"eq.{today}"
            }
        ).json()

        if existing:

            row = existing[0]

            requests.patch(
                f"{SUPABASE_URL}/rest/v1/analytics_daily",

                headers=HEADERS,

                params={
                    "id": f"eq.{row['id']}"
                },

                json={
                    field:
                    row.get(field, 0) + 1
                }
            )

        else:

            payload = {
                "client_id": client_id,
                "day": today,

                "messages": 0,
                "conversations": 0,
                "leads": 0,
                "widget_opens": 0
            }

            payload[field] = 1

            requests.post(
                f"{SUPABASE_URL}/rest/v1/analytics_daily",

                headers=HEADERS,

                json=payload
            )

    except Exception as e:

        print(
            "ANALYTICS ERROR:",
            e
        )

# =========================
# APP
# =========================

app.add_middleware(
    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=False,

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
    captcha_token: str | None = None

class VerifyData(BaseModel):
    token: str

class ResetData(BaseModel):
    token: str
    password: str

class Question(BaseModel):
    question: str
    session_id: Optional[str] = "default"

class WidgetAppearanceUpdate(BaseModel):
    client_id: str
    theme: str | None = None
    color: str
    name: str
    welcome_message: str

    position: str

    radius: int

    dark_mode: bool

    font: str

    logo_url: str | None = None

    launcher_icon: str | None = None

    theme: str | None = None
    launcher_image: str | None = None


class PublicQuestion(BaseModel):
    question: str
    assistant_id: str
    session_id: Optional[str] = "default"

class ScrapeRequest(BaseModel):
    url: str
# =========================
# RATE LIMIT
# =========================
RATE_LIMIT = {}

class DeleteFileRequest(BaseModel):
    file_url: str

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

def verify_captcha(token):
    return True
    # 🔥 DEV MODE — captcha disabled
    if not token:
        return True

    try:
        res = requests.post(
            "https://challenges.cloudflare.com/turnstile/v0/siteverify",
            data={
                "secret": os.getenv("TURNSTILE_SECRET"),
                "response": token
            },
            timeout=10
        )

        data = res.json()

        if not data.get("success"):
            raise HTTPException(
                status_code=400,
                detail="Captcha failed"
            )

        return True


    except Exception as e:

        import traceback

        traceback.print_exc()

        print("FULL AI ERROR:", str(e))
        logging.error(f"Captcha error: {e}")

        raise HTTPException(
            status_code=500,
            detail="Captcha service error"
        )

# =========================
# KNOWLEDGE
# =========================

def get_knowledge(assistant_id: str):

    try:

        response = requests.get(

            f"{SUPABASE_URL}/rest/v1/assistant_knowledge",

            headers=HEADERS,

            params={

                "assistant_id":
                f"eq.{assistant_id}",

                "select":
                "content"

            }

        )

        data = response.json()

        return [

            row["content"]

            for row in data

            if row.get("content")

        ]

    except Exception as e:

        print(

            "GET KNOWLEDGE ERROR:",

            e

        )

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
    verify_captcha(data.captcha_token)

    email = data.email.strip().lower()

    if get_user(email):
        raise HTTPException(400, "User exists")

    create_user(email, data.password)

    update_user_by_email(email, {
        "email_verified": True,
        "verify_token": None
    })

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
    verify_captcha(data.captcha_token)

    email = data.email.strip().lower()

    user = get_user(email)

    if not user:
        raise HTTPException(401)

    if not bcrypt.checkpw(data.password.encode(), user["password"].encode()):
        raise HTTPException(401)

    # if not user.get("email_verified"):
    #     raise HTTPException(403, "Email not verified")

    return {
        "access_token": create_token(user["id"]),
        "token_type": "bearer"
    }

class WidgetQuestion(BaseModel):
    client_id: str
    question: str


@app.post("/widget/ask")
def widget_ask(data: WidgetQuestion):

    try:

        client_id = data.client_id
        question = data.question

        #
        # 🔥 KNOWLEDGE
        #
        results = semantic_search(
            client_id,
            question
        )

        context = "\n".join([
            r["content"]
            for r in results
        ])

        if not context:
            return {
                "answer": "Brak danych knowledge base."
            }

        #
        # 🔥 AI RESPONSE
        #
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {
                    "role": "system",
                    "content": "Odpowiadaj krótko i konkretnie."
                },
                {
                    "role": "user",
                    "content": f"{context}\n\n{question}"
                }
            ]
        )

        answer = response.choices[0].message.content

        return {
            "answer": answer
        }

    except Exception as e:

        print("WIDGET ERROR:", e)

        raise HTTPException(
            status_code=500,
            detail="WIDGET_AI_ERROR"
        )

# =========================
# CLIENT DATA
# =========================
@app.get("/client-data")
def client_data(user=Depends(get_current_user)):

    print("CLIENT DATA HIT")

    client_id = user["id"]

    try:

        #
        # SAFE LIMIT CHECK
        #
        try:

            data = check_limit(client_id)

            plan = data.get(
                "plan",
                "free"
            )

            usage = data.get(
                "usage",
                0
            )

            limit = data.get(
                "limit",
                10
            )

        except:

            plan = "free"
            usage = 0
            limit = 10

        return {
            "id": client_id,
            "email": user.get(
                "email",
                ""
            ),
            "plan": plan,
            "usage": usage,
            "limit": limit,
            "status": "active"
        }

    except Exception as e:

        logging.error(
            f"CLIENT DATA ERROR: {e}"
        )

        raise HTTPException(
            status_code=500,
            detail="CLIENT_DATA_ERROR"
        )

# =========================
# COSINE SIMILARITY
# =========================
import math


def cosine_similarity(a,b):

    dot = sum(

        x*y

        for x,y

        in zip(a,b)

    )



    norm_a = math.sqrt(

        sum(

            x*x

            for x in a

        )

    )



    norm_b = math.sqrt(

        sum(

            x*x

            for x in b

        )

    )



    if norm_a == 0 or norm_b == 0:

        return 0



    return dot / (

        norm_a * norm_b

    )
# =========================
# SEMANTIC SEARCH
# =========================

def semantic_search(

    assistant_id: str,

    question: str,

    top_k: int = 5

):

    try:

        embedding_response = client.embeddings.create(

            model="text-embedding-3-small",

            input=question

        )

        query_embedding = (

            embedding_response

            .data[0]

            .embedding

        )



        response = requests.get(

            f"{SUPABASE_URL}/rest/v1/assistant_knowledge",

            headers=HEADERS,

            params={

                "assistant_id":

                f"eq.{assistant_id}"

            }

        )



        chunks = response.json()



        scored = []



        for chunk in chunks:

            emb = chunk.get("embedding")



            if not emb:

                continue



            score = cosine_similarity(

                query_embedding,

                emb

            )



            scored.append({

                "content":

                chunk["content"],

                "score":

                score

            })



        scored.sort(

            key=lambda x:

            x["score"],

            reverse=True

        )



        return scored[:top_k]



    except Exception as e:

        print(

            "SEMANTIC SEARCH ERROR:",

            e

        )

        return []
# =========================
# SAVE MESSAGE
# =========================

def save_message(

    assistant_id: str,

    session_id: str,

    role: str,

    content: str

):

    try:

        payload = {

            "assistant_id":

            assistant_id,

            "session_id":

            session_id,

            "role":

            role,

            "content":

            content,

        }



        requests.post(

            f"{SUPABASE_URL}/rest/v1/assistant_messages",

            headers={

                **HEADERS,

                "Prefer":

                "return=minimal"

            },

            json=payload

        )



    except Exception as e:

        print(

            "SAVE MESSAGE ERROR:",

            e

        )

@app.get("/widgets")
def get_widgets(
    user=Depends(
        get_current_user
    )
):

    client_id = user["id"]

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/widgets",

        headers=HEADERS,

        params={
            "client_id":
                f"eq.{client_id}",

            "order":
                "created_at.desc"
        }
    )

    return response.json()

@app.post("/widgets")
def create_widget(
    data: dict,
    user=Depends(
        get_current_user
    )
):

    client_id = user["id"]

    payload = {

        "client_id":
            client_id,

        "name":
            data.get(
                "name",
                "Nowy Widget"
            )

    }

    response = requests.post(

        f"{SUPABASE_URL}/rest/v1/widgets",

        headers=HEADERS,

        json=payload
    )

    return response.json()

# =========================
# MEMORY
# =========================

def get_memory(

    assistant_id: str,

    session_id: str,

    limit: int = 10

):

    try:

        response = requests.get(

            f"{SUPABASE_URL}/rest/v1/assistant_messages",

            headers=HEADERS,

            params={

                "assistant_id":

                f"eq.{assistant_id}",

                "session_id":

                f"eq.{session_id}",

                "order":

                "created_at.asc",

                "limit":

                str(limit)

            }

        )



        rows = response.json()



        memory = []



        for row in rows:

            memory.append({

                "role":

                row["role"],

                "content":

                row["content"]

            })



        return memory



    except Exception as e:

        print(

            "GET MEMORY ERROR:",

            e

        )



        return []

# =========================
# CHAT
# =========================

def get_client_ai_settings(
    client_id: str
):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/ai_settings",

        headers=HEADERS,

        params={
            "client_id":
                f"eq.{client_id}",

            "select":
                "*"
        }
    )

    data = response.json()

    if len(data) == 0:

        return {

            "model":
                "gpt-4o-mini",

            "temperature":
                0.7,

            "language":
                "Polski",

            "response_length":
                "Średnia",

            "system_prompt":
                "",

            "lead_generation":
                True
        }

    return data[0]

# =========================
# ASSISTANT PROMPT
# =========================

def get_assistant_prompt(
    assistant_id: str
):

    try:

        response = requests.get(

            f"{SUPABASE_URL}/rest/v1/assistant_prompts",

            headers=HEADERS,

            params={

                "assistant_id":
                f"eq.{assistant_id}",

                "select":
                "*",

                "limit":
                "1"

            }

        )

        data = response.json()

        if not data:

            return {

                "system_prompt":"",

                "tone":"Profesjonalny",

                "personality":"Pomocny",

                "restrictions":""

            }

        return data[0]


    except Exception as e:

        print(

            "PROMPT ERROR:",

            e

        )

        return {

            "system_prompt":"",

            "tone":"Profesjonalny",

            "personality":"Pomocny",

            "restrictions":""

        }

@app.get(
    "/widget/status"
)
def get_widget_status(
    user=Depends(
        get_current_user
    )
):

    client_id = user["id"]

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/widget_installations",

        headers=HEADERS,

        params={
            "client_id":
                f"eq.{client_id}",

            "select":
                "*",

            "order":
                "last_seen.desc"
        }
    )

    data = response.json()

    installed = len(
        data
    ) > 0

    domains = len(
        data
    )

    latest = None

    if installed:
        latest = data[0]

    return {

        "installed":
            installed,

        "domains":
            domains,

        "latest":
            latest,

        "records":
            data
    }

@app.post(
    "/widget/heartbeat"
)
def widget_heartbeat(
    data: dict
):

    client_id = data.get(
        "client_id"
    )

    domain = data.get(
        "domain"
    )

    if not client_id:
        return {
            "success": False
        }

    existing = requests.get(

        f"{SUPABASE_URL}/rest/v1/widget_installations",

        headers=HEADERS,

        params={
            "client_id":
                f"eq.{client_id}",

            "domain":
                f"eq.{domain}"
        }

    ).json()

    payload = {

        "client_id":
            client_id,

        "domain":
            domain,

        "installed":
            True,

        "last_seen":
            datetime.utcnow()
            .isoformat()
    }

    if existing:

        record_id = (
            existing[0]["id"]
        )

        requests.patch(

            f"{SUPABASE_URL}/rest/v1/widget_installations",

            headers=HEADERS,

            params={
                "id":
                    f"eq.{record_id}"
            },

            json=payload
        )

    else:

        requests.post(

            f"{SUPABASE_URL}/rest/v1/widget_installations",

            headers=HEADERS,

            json=payload
        )

    return {
        "success": True
    }

@app.post("/ask")
def ask(q: Question, user=Depends(get_current_user)):

    print("ASK HIT")

    try:

        client_id = user["id"]
        settings = get_client_ai_settings(
            client_id
        )
        print("CLIENT:", client_id)

        #
        # ANALYTICS
        #
        track_usage_event(
            client_id,
            "chat_message"
        )

        update_daily_analytics(
            client_id,
            "messages"
        )

        #
        # RATE LIMIT
        #
        check_rate_limit(client_id)

        #
        # USAGE LIMIT
        #
        # check_limit(client_id)

        #
        # KNOWLEDGE
        #
        results = semantic_search(
            client_id,
            q.question
        )

        context = "\n".join([
            r["content"]
            for r in results
        ])

        print("SEMANTIC RESULTS:", results)

        print("CONTEXT:", context)

        if not context:
            #
            # SAVE USER MESSAGE
            #
            save_message(
                client_id,
                q.session_id,
                "user",
                q.question
            )

            #
            # SAVE AI MESSAGE
            #
            save_message(
                client_id,
                q.session_id,
                "assistant",
                "Brak danych treningowych"
            )

            return {
                "answer":
                    "❌ Brak danych treningowych"
            }

        #
        # MEMORY
        #
        memory = get_memory(
            client_id,
            q.session_id
        )

        #
        # NEW CONVERSATION
        #
        if len(memory) == 0:
            track_widget_event(
                client_id,
                "conversation_started",
                q.session_id
            )

            update_daily_analytics(
                client_id,
                "conversations"
            )

        response_style = ""

        if (
                settings["response_length"]
                == "Krótka"
        ):
            response_style = (
                "Odpowiadaj bardzo krótko."
            )

        elif (
                settings["response_length"]
                == "Długa"
        ):
            response_style = (
                "Odpowiadaj szczegółowo."
            )

        else:
            response_style = (
                "Odpowiadaj średniej długości."
            )

        system_message = f"""
        Język odpowiedzi:
        {settings["language"]}

        {response_style}

        {settings["system_prompt"]}
        """

        messages = [
            {
                "role": "system",
                "content":
                    system_message
            }
        ]

        #
        # MEMORY MESSAGES
        #
        for msg in memory:
            messages.append({
                "role": msg["role"],
                "content": msg["content"]
            })

        #
        # KNOWLEDGE + QUESTION
        #
        messages.append({
            "role": "user",
            "content":
                f"""
            KNOWLEDGE:
            {context}

            QUESTION:
            {q.question}
            """
        })

        #
        # OPENAI REQUEST
        #
        response = client.chat.completions.create(

            model=
            settings["model"],

            temperature=
            float(
                settings[
                    "temperature"
                ]
            ),

            messages=
            messages
        )

        answer = (
            response
            .choices[0]
            .message
            .content
        )

        #
        # SAVE USER MESSAGE
        #
        save_message(
            client_id,
            q.session_id,
            "user",
            q.question
        )

        #
        # SAVE AI MESSAGE
        #
        save_message(
            client_id,
            q.session_id,
            "assistant",
            answer
        )

        #
        # INCREMENT USAGE
        #
        increment_usage(client_id)

        return {
            "answer": answer
        }

    except Exception as e:

        logging.error(
            f"AI ERROR: {e}"
        )

        raise HTTPException(
            500,
            "AI_ERROR"
        )

# =========================
# PUBLIC CHAT (WIDGET)
# =========================
@app.post("/ask-public")
async def ask_public(q: PublicQuestion):

    assistant_id = q.assistant_id

    #
    # ANALYTICS
    #
    track_usage_event(
        client_id,
        "public_chat_message"
    )

    update_daily_analytics(
        client_id,
        "messages"
    )

    if not client_id:
        raise HTTPException(400, "Missing client_id")

    check_rate_limit(client_id)

    save_message(
        client_id,
        q.session_id,
        "user",
        q.question
    )

    results = semantic_search(

assistant_id,

q.question

)

    context = "\n".join(

        item["content"]

        for item in results

    )

    if not context:
        async def no_data():
            yield json.dumps({
                "token": "❌ Brak danych"
            }) + "\n"

        return StreamingResponse(
            no_data(),
            media_type="text/plain"
        )

    async def generate():

        full_answer = ""

        stream = client.chat.completions.create(
            model="gpt-4o-mini",

            stream=True,

            messages=[
                {
                    "role": "system",
                    "content":
                        settings = get_client_ai_settings(
client_id
)

system_message = f"""

Język:

{settings["language"]}

{settings["system_prompt"]}

Nigdy nie wymyślaj informacji.

Odpowiadaj wyłącznie na podstawie KNOWLEDGE.

"""
                },
                {
                    "role": "user",
                    "content":
                        f"{context}\n\n{q.question}"
                }
            ]
        )

        for chunk in stream:

            token = (
                chunk
                .choices[0]
                .delta
                .content
            )

            if token:

                full_answer += token

                yield json.dumps({
                    "token": token
                }) + "\n"

                await asyncio.sleep(0.01)

        save_message(
            client_id,
            q.session_id,
            "assistant",
            full_answer
        )

        increment_usage(client_id)

    return StreamingResponse(
        generate(),
        media_type="text/plain"
    )

# =========================
# CHUNKING
# =========================
def chunk_text(
            text: str,
            chunk_size: int = 1000,
            overlap: int = 200
    ):

        chunks = []

        start = 0

        while start < len(text):
            end = start + chunk_size

            chunk = text[start:end]

            chunks.append(chunk)

            start += chunk_size - overlap

        return chunks

# =========================
# EMBEDDINGS
# =========================
def create_embedding(text: str):

    response = client.embeddings.create(
        model="text-embedding-3-small",
        input=text
    )

    return response.data[0].embedding

@app.get("/widget.js")
def get_widget_script():
    return FileResponse(
        "widget.js",
        media_type="application/javascript"
    )

#
# 🔥 SAVE LEAD
#
@app.post("/lead")
async def save_lead(
    data: dict
):
    client_id = data.get("client_id")

    track_widget_event(
        client_id,
        "lead_created"
    )

    update_daily_analytics(
        client_id,
        "leads"
    )

    try:

        response = requests.post(
            f"{SUPABASE_URL}/rest/v1/leads",

            headers=HEADERS,

            json={

                "client_id":
                    data.get(
                        "client_id"
                    ),

                "session_id":
                    data.get(
                        "session_id"
                    ),

                "email":
                    data.get(
                        "email"
                    ),

                "name":
                    data.get(
                        "name"
                    ),

                "phone":
                    data.get(
                        "phone"
                    ),
            }
        )

        print(
            "LEAD STATUS:",
            response.status_code
        )

        print(
            "LEAD RESPONSE:",
            response.text
        )

        return {
            "success": True
        }

    except Exception as e:

        print(
            "LEAD ERROR:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )
#
# 🔥 UPLOAD FILE
#
print("🔥 NEW API FILE LOADED")
@app.post("/upload")
async def upload_file(
    file: UploadFile = File(...)
):

    try:

        import uuid
        import requests

        ext = (
            file.filename
            .split(".")[-1]
        )

        filename = (
            f"{uuid.uuid4()}.{ext}"
        )

        contents = await file.read()

        upload_url = (
            f"{SUPABASE_URL}"
            f"/storage/v1/object/"
            f"widget-assets/"
            f"{filename}"
        )

        headers = {
            "apikey":
                SUPABASE_KEY,

            "Authorization":
                f"Bearer {SUPABASE_KEY}",

            "Content-Type":
                file.content_type,
        }

        response = requests.put(
            upload_url,
            headers=headers,
            data=contents
        )

        print(
            "UPLOAD STATUS:",
            response.status_code
        )

        print(
            "UPLOAD RESPONSE:",
            response.text
        )

        if response.status_code >= 400:

            raise HTTPException(
                status_code=500,
                detail=response.text
            )

        public_url = (
            f"{SUPABASE_URL}"
            f"/storage/v1/object/public/"
            f"widget-assets/"
            f"{filename}"
        )

        return {
            "url":
                public_url
        }

    except Exception as e:

        print(
            "UPLOAD ERROR:"
        )

        print(e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/delete-file")
async def delete_file(
    data: DeleteFileRequest
):

    try:

        file_url = data.file_url

        filename = (
            file_url
            .split("/")[-1]
        )

        result = (
            supabase
            .storage
            .from_("widget-assets")
            .remove([
                filename
            ])
        )

        return {
            "success": True
        }

    except Exception as e:

        print(
            "DELETE FILE ERROR:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

@app.post("/widget/appearance")
async def save_widget_appearance(
    request: Request
):
    data = await request.json()

    print("🔥 SAVE APPEARANCE:", data)

    client_id = data.get("client_id")

    if not client_id:
        return {
            "success": False,
            "error": "Missing client_id"
        }

    supabase.table(
        "widget_settings"
    ).upsert(
        {
            "client_id": client_id,
            "name": data.get("name"),
            "subtitle": data.get("subtitle"),
            "color": data.get("color"),

            # 🔥 avatar z launcher image
            "avatar": data.get("avatar"),

            "launcher_image": data.get("launcher_image"),
            "radius": data.get("radius"),
            "dark_mode": data.get("dark_mode"),
            "font": data.get("font"),
            "position": data.get("position"),

            "welcome_message":
                data.get(
                    "welcome_message"
                ),

            "avatar_position_x":
    data.get(
        "avatar_position_x",
        data.get(
            "avatarPositionX",
            50
        )
    ),

            "avatar_position_y":
    data.get(
        "avatar_position_y",
        data.get(
            "avatarPositionY",
            50
        )
    ),

"avatar_zoom":
    data.get(
        "avatar_zoom",
        data.get(
            "avatarZoom",
            1
        )
    ),
            "launcher_position_x":
    data.get(
        "launcher_position_x",
        data.get(
            "launcherPositionX",
            50
        )
    ),

            "launcher_position_y":
    data.get(
        "launcher_position_y",
        data.get(
            "launcherPositionY",
            50
        )
    ),

"launcher_zoom":
    data.get(
        "launcher_zoom",
        data.get(
            "launcherZoom",
            1
        )
    ),
        },

        on_conflict="client_id"

    ).execute()

    return {
        "success": True
    }


@app.get("/widget/appearance/{client_id}")
async def get_widget_appearance(
    client_id: str
):

    try:

        response = (
            supabase
            .table("widget_settings")
            .select("*")
            .eq("client_id", client_id)
            .limit(1)
            .execute()
        )

        #
        # ❌ NO DATA
        #
        if (
            not response.data
            or len(response.data) == 0
        ):

            print(
                f"⚠️ No appearance for: {client_id}"
            )

            return {}

        #
        # ✅ SUCCESS
        #
        appearance = response.data[0]

        print(
            "🎨 Appearance loaded:",
            appearance
        )

        return {

            **appearance,

            "avatarPositionX":
                appearance.get(
                    "avatar_position_x",
                    50
                ),

            "avatarPositionY":
                appearance.get(
                    "avatar_position_y",
                    50
                ),

            "avatarZoom":
                appearance.get(
                    "avatar_zoom",
                    1
                ),
            "launcherPositionX":
                appearance.get(
                    "launcher_position_x",
                    50
                ),

            "launcherPositionY":
                appearance.get(
                    "launcher_position_y",
                    50
                ),

            "launcherZoom":
                appearance.get(
                    "launcher_zoom",
                    1
                ),
        }
    except Exception as error:

        print(
            "❌ Appearance fetch failed:",
            error
        )

        return {}

@app.post("/widget/history")
async def save_widget_history(
    request: Request
):
    data = await request.json()

    client_id = data.get("client_id")
    name = data.get("name")
    settings = data.get("settings")

    if not client_id:
        raise HTTPException(
            400,
            "Missing client_id"
        )

    if not name:
        raise HTTPException(
            400,
            "Missing name"
        )

    supabase.table(
        "widget_theme_history"
    ).insert(
        {
            "client_id": client_id,
            "name": name,
            "settings": settings,
        }
    ).execute()

    return {
        "success": True
    }

@app.get("/widget/history/{client_id}")
async def get_widget_history(
    client_id: str
):

    response = (
        supabase
        .table(
            "widget_theme_history"
        )
        .select("*")
        .eq(

            "assistant_id",

            assistant_id

        )
        .order(
            "created_at",
            desc=True
        )
        .execute()
    )

    return response.data

@app.delete("/widget/history/{snapshot_id}")
async def delete_widget_history(
    snapshot_id: str
):

    (
        supabase
        .table(
            "widget_theme_history"
        )
        .delete()
        .eq(
            "id",
            snapshot_id
        )
        .execute()
    )

    return {
        "success": True
    }


# =========================
# WEBSITE SCRAPING
# =========================
@app.post("/scrape-website")
def scrape_website(

    data: ScrapeRequest,

    assistant_id: str

):

    try:

        response = requests.get(

            data.url,

            timeout=20,

            headers={

                "User-Agent":

                "Mozilla/5.0"

            }

        )



        soup = BeautifulSoup(

            response.text,

            "lxml"

        )



        for tag in soup([

            "script",

            "style",

            "iframe",

            "noscript"

        ]):

            tag.decompose()



        text = soup.get_text(

            separator=" ",

            strip=True

        )



        text = text[:30000]



        chunks = chunk_text(

            text

        )



        saved = 0



        for chunk in chunks:



            embedding = create_embedding(

                chunk

            )



            requests.post(

                f"{SUPABASE_URL}/rest/v1/assistant_knowledge",

                headers=HEADERS,

                json={

                    "assistant_id":

                    assistant_id,



                    "content":

                    chunk,



                    "embedding":

                    embedding

                }

            )



            saved += 1



        return {

            "success": True,

            "chunks": saved,

            "characters": len(text)

        }



    except Exception as e:



        print(

            "SCRAPE ERROR:",

            e

        )



        raise HTTPException(

            500,

            "SCRAPE_FAILED"

        )

#
# 🔥 GET LEADS
#
@app.get("/leads/{client_id}")
async def get_leads(
    client_id: str
):

    try:

        response = requests.get(

            f"{SUPABASE_URL}/rest/v1/leads",

            headers=HEADERS,

            params={
                "client_id":
                    f"eq.{client_id}",

                "select":
                    "*",

                "order":
                    "created_at.desc"
            }
        )

        return response.json()

    except Exception as e:

        print(
            "GET LEADS ERROR:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )

# =========================
# AI BRAIN
# =========================

@app.post("/client/setup")
def client_setup(
    data: dict,
    user=Depends(get_current_user)
):
    client_id = user["id"]

    text = data.get("text")

    if not text:
        raise HTTPException(
            400,
            "Missing text"
        )

    chunks = chunk_text(text)

    saved = 0

    for chunk in chunks:

        embedding = create_embedding(
            chunk
        )

        requests.post(
            f"{SUPABASE_URL}/rest/v1/knowledge",
            headers=HEADERS,
            json={
                "client_id": client_id,
                "content": chunk,
                "embedding": embedding
            }
        )

        saved += 1

    return {
        "success": True,
        "chunks": saved
    }


@app.get("/knowledge")
def get_knowledge_records(
    user=Depends(get_current_user)
):
    client_id = user["id"]

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/knowledge",
        headers=HEADERS,
        params={
            "client_id": f"eq.{client_id}",
            "select": "*"
        }
    )

    return response.json()


@app.get("/knowledge/stats")
def get_knowledge_stats(
    user=Depends(get_current_user)
):
    client_id = user["id"]

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/knowledge",
        headers=HEADERS,
        params={
            "client_id": f"eq.{client_id}",
            "select": "id,content"
        }
    )

    knowledge = response.json()

    total_knowledge = len(
        knowledge
    )

    total_chars = sum(
        len(
            item.get(
                "content",
                ""
            )
        )
        for item in knowledge
    )

    average_length = 0

    if total_knowledge > 0:
        average_length = round(
            total_chars /
            total_knowledge
        )

    return {
        "totalKnowledge": total_knowledge,
        "totalChars": total_chars,
        "averageLength": average_length
    }


@app.delete("/knowledge/{knowledge_id}")
def delete_knowledge(
    knowledge_id: str,
    user=Depends(get_current_user)
):

    requests.delete(
        f"{SUPABASE_URL}/rest/v1/knowledge",
        headers=HEADERS,
        params={
            "id": f"eq.{knowledge_id}"
        }
    )

    return {
        "success": True
    }

# =========================
# AI DOCUMENTS
# =========================

@app.post("/upload-ai-document")
async def upload_ai_document(

    assistant_id: str,

    file: UploadFile = File(...)

):

    try:

        content = await file.read()


        text = ""


        # TXT
        if file.filename.endswith(".txt"):

            text = content.decode("utf-8")


        # PDF
        elif file.filename.endswith(".pdf"):

            pdf = PdfReader(

                BytesIO(content)

            )



            for page in pdf.pages:

                extracted = page.extract_text()

                if extracted:

                    text += extracted + "\n"


        else:

            raise HTTPException(

                400,

                "Unsupported file"

            )



        chunks = chunk_text(text)



        saved = 0



        for chunk in chunks:



            embedding = create_embedding(

                chunk

            )



            requests.post(

                f"{SUPABASE_URL}/rest/v1/assistant_knowledge",

                headers=HEADERS,

                json={

                    "assistant_id":

                    assistant_id,



                    "content":

                    chunk,



                    "embedding":

                    embedding

                }

            )



            saved += 1



        return {

            "success": True,

            "chunks": saved,

            "characters": len(text)

        }



    except Exception as e:



        print(

            "UPLOAD ERROR:",

            e

        )



        raise HTTPException(

            500,

            "UPLOAD_FAILED"

        )

@app.delete("/ai-document/{document_id}")
def delete_ai_document(
    document_id: str,
    user=Depends(get_current_user)
):

    #
    # DELETE KNOWLEDGE
    #
    requests.delete(

        f"{SUPABASE_URL}/rest/v1/knowledge",

        headers=HEADERS,

        params={
            "document_id":
                f"eq.{document_id}"
        }
    )

    #
    # DELETE DOCUMENT
    #
    requests.delete(

        f"{SUPABASE_URL}/rest/v1/ai_documents",

        headers=HEADERS,

        params={
            "id":
                f"eq.{document_id}"
        }
    )

    return {
        "success": True
    }

@app.get("/ai-documents")
def get_ai_documents(
    user=Depends(get_current_user)
):

    client_id = user["id"]

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/ai_documents",

        headers=HEADERS,

        params={

            "client_id":
                f"eq.{client_id}",

            "order":
                "created_at.desc"
        }
    )

    return response.json()

# =========================
# AI SETTINGS
# =========================

@app.get("/ai-settings")
def get_ai_settings(
    user=Depends(get_current_user)
):

    client_id = user["id"]

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/ai_settings",
        headers=HEADERS,
        params={
            "client_id": f"eq.{client_id}",
            "select": "*"
        }
    )

    data = response.json()

    if len(data) == 0:

        return {
            "model": "gpt-5.5",
            "temperature": 0.7,
            "language": "Polski",
            "response_length": "Średnia",
            "system_prompt": "",
            "lead_generation": True
        }

    return data[0]


@app.post("/ai-settings")
def save_ai_settings(
    data: dict,
    user=Depends(get_current_user)
):

    client_id = user["id"]

    existing = requests.get(
        f"{SUPABASE_URL}/rest/v1/ai_settings",
        headers=HEADERS,
        params={
            "client_id": f"eq.{client_id}",
            "select": "id"
        }
    ).json()

    payload = {

        "client_id": client_id,

        "model":
            data.get(
                "model",
                "gpt-5.5"
            ),

        "temperature":
            data.get(
                "temperature",
                0.7
            ),

        "language":
            data.get(
                "language",
                "Polski"
            ),

        "response_length":
            data.get(
                "response_length",
                "Średnia"
            ),

        "system_prompt":
            data.get(
                "system_prompt",
                ""
            ),

        "lead_generation":
            data.get(
                "lead_generation",
                True
            )
    }

    if len(existing) > 0:

        requests.patch(

            f"{SUPABASE_URL}/rest/v1/ai_settings",

            headers=HEADERS,

            params={
                "client_id":
                    f"eq.{client_id}"
            },

            json=payload
        )

    else:

        requests.post(

            f"{SUPABASE_URL}/rest/v1/ai_settings",

            headers=HEADERS,

            json=payload
        )

    return {
        "success": True
    }

@app.get("/analytics")
def get_analytics(
    user=Depends(get_current_user)
):

    client_id = user["id"]

    try:

        #
        # DAILY STATS
        #
        daily = requests.get(

            f"{SUPABASE_URL}/rest/v1/analytics_daily",

            headers=HEADERS,

            params={
                "client_id":
                    f"eq.{client_id}",

                "order":
                    "day.asc"
            }
        ).json()

        #
        # TOTALS
        #
        total_messages = sum(
            row.get("messages", 0)
            for row in daily
        )

        total_conversations = sum(
            row.get("conversations", 0)
            for row in daily
        )

        total_leads = sum(
            row.get("leads", 0)
            for row in daily
        )

        conversion_rate = 0

        if total_messages > 0:

            conversion_rate = round(
                (
                    total_leads /
                    total_messages
                ) * 100,
                1
            )

        #
        # CHART
        #
        chart_data = []

        for row in daily[-30:]:

            chart_data.append({
                "label":
                    row["day"][-5:],

                "messages":
                    row.get(
                        "messages",
                        0
                    ),

                "leads":
                    row.get(
                        "leads",
                        0
                    )
            })

        #
        # RESPONSE
        #
        return {

            "kpis": {

                "messages":
                    total_messages,

                "conversations":
                    total_conversations,

                "leads":
                    total_leads,

                "responseRate":
                    100
            },

            "summary": {

                "messages":
                    total_messages,

                "leads":
                    total_leads,

                "conversionRate":
                    conversion_rate
            },

            "topQuestions": [],

            "analyticsData": {

                "24h":
                    chart_data,

                "7d":
                    chart_data,

                "30d":
                    chart_data,

                "90d":
                    chart_data
            },

            "widgetPerformance": {

                "openRate": 0,

                "engagement": 0,

                "avgResponse": "1.2s"
            },

            "aiStatus": {

                "systemOnline": True,

                "currentModel": "GPT-4o-mini",

                "retrievalSystem":
                    "Semantic Search V1"
            }
        }

    except Exception as e:

        print(
            "ANALYTICS ERROR:",
            e
        )

        raise HTTPException(
            status_code=500,
            detail="ANALYTICS_ERROR"
        )

# =========================
# STRIPE
# =========================
@app.post("/create-checkout")
def create_checkout(user=Depends(get_current_user)):
    session = stripe.checkout.Session.create(
        mode="subscription",
        payment_method_types=["card"],
        line_items=[{"price": STRIPE_PRICE_ID, "quantity": 1}],
        success_url=f"{FRONTEND_URL}/success?session_id={{CHECKOUT_SESSION_ID}}",
        cancel_url=f"{FRONTEND_URL}/cancel",
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
    except Exception as e:
        logging.error(f"Webhook error: {e}")
        return {"error": "invalid"}

    # =========================
    # CHECKOUT COMPLETED
    # =========================
    if event["type"] == "checkout.session.completed":
        session = event["data"]["object"]

        client_id = session.get("metadata", {}).get("client_id")
        subscription_id = session.get("subscription")

        if not client_id:
            return {"error": "no client_id"}

        # pobierz dane subskrypcji ze Stripe
        sub = stripe.Subscription.retrieve(subscription_id)

        current_period_end = datetime.fromtimestamp(sub.current_period_end)

        # UPSERT DO SUPABASE
        requests.post(
            f"{SUPABASE_URL}/rest/v1/subscriptions",
            headers={
                **HEADERS,
                "Prefer": "resolution=merge-duplicates"
            },
            json={
                "client_id": client_id,
                "plan": "pro",
                "status": "active",
                "current_period_end": current_period_end.isoformat(),
                "stripe_subscription_id": subscription_id
            }
        )

        # =========================
        # AI BRAIN
        # ========================

    # =========================
    # SUBSCRIPTION CANCELED
    # =========================
    if event["type"] == "customer.subscription.deleted":
        sub = event["data"]["object"]

        subscription_id = sub.get("id")

        # ustaw status = canceled
        requests.patch(
            f"{SUPABASE_URL}/rest/v1/subscriptions",
            headers=HEADERS,
            params={
                "stripe_subscription_id": f"eq.{subscription_id}"
            },
            json={
                "status": "canceled"
            }
        )

    return {"ok": True}