import os
import jwt
from datetime import datetime, timedelta
from fastapi import Header, HTTPException
import requests

SECRET = os.getenv("JWT_SECRET", "supersecret")
ALGO = "HS256"

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


# =========================
# JWT
# =========================
def create_token(user_id: str):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(hours=12),
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)


def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGO])
    except:
        return None


# =========================
# USER HELPERS
# =========================
def get_user(email: str):
    try:
        email = email.strip().lower()

        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=HEADERS,
            params={
                "email": f"eq.{email}",
                "select": "*"
            }
        )

        if res.status_code != 200:
            return None

        data = res.json()
        if not data:
            return None

        return data[0]
    except:
        return None


def create_user(email: str, password: str):
    from bcrypt import hashpw, gensalt
    import uuid

    email = email.strip().lower()

    if get_user(email):
        raise ValueError("user_exists")

    hashed_password = hashpw(password.encode(), gensalt()).decode()

    user = {
        "id": str(uuid.uuid4()),  # 🔥 KLUCZOWE
        "email": email,
        "password": hashed_password,
        "email_verified": False,
        "verify_token": None,
    }

    res = requests.post(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=HEADERS,
        json=user
    )

    if res.status_code not in (200, 201):
        print("SUPABASE ERROR:", res.text)  # 🔥 DEBUG
        raise ValueError(f"user_create_failed: {res.text}")

    created = get_user(email)
    if not created:
        raise ValueError("user_not_created")

    return created


def update_user_by_email(email: str, data: dict):
    email = email.strip().lower()

    res = requests.patch(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=HEADERS,
        params={"email": f"eq.{email}"},
        json=data
    )

    return res.status_code in (200, 204)


def update_user_by_token(token: str, data: dict):
    res = requests.patch(
        f"{SUPABASE_URL}/rest/v1/users",
        headers=HEADERS,
        params={"verify_token": f"eq.{token}"},
        json=data
    )

    return res.status_code in (200, 204)


def get_user_by_verify_token(token: str):
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=HEADERS,
            params={
                "verify_token": f"eq.{token}",
                "select": "*"
            }
        )

        if res.status_code != 200:
            return None

        data = res.json()
        if not data:
            return None

        return data[0]
    except:
        return None


# =========================
# MIDDLEWARE
# =========================
def get_current_user(authorization: str = Header(None)):
    if not authorization:
        raise HTTPException(status_code=401, detail="missing_token")

    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="invalid_scheme")
    except:
        raise HTTPException(status_code=401, detail="invalid_header")

    data = decode_token(token)
    if not data:
        raise HTTPException(status_code=401, detail="invalid_token")

    user = get_user_by_id(data["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")

    return user


def get_user_by_id(user_id: str):
    try:
        res = requests.get(
            f"{SUPABASE_URL}/rest/v1/users",
            headers=HEADERS,
            params={
                "id": f"eq.{user_id}",
                "select": "*"
            }
        )

        if res.status_code != 200:
            return None

        data = res.json()
        if not data:
            return None

        return data[0]
    except:
        return None

def get_user_by_reset_token(token: str):
        try:
            res = requests.get(
                f"{SUPABASE_URL}/rest/v1/users",
                headers=HEADERS,
                params={
                    "reset_token": f"eq.{token}",
                    "select": "*"
                }
            )

            if res.status_code != 200:
                return None

            data = res.json()
            if not data:
                return None

            return data[0]
        except:
            return None