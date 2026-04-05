import json
import os
import bcrypt
import jwt
from datetime import datetime, timedelta
from fastapi import Header, HTTPException

SECRET = os.getenv("JWT_SECRET", "supersecret")
ALGO = "HS256"
USERS_DB = "users.json"


# =========================
# 💾 USERS DB
# =========================
def load_users():
    try:
        with open(USERS_DB, "r") as f:
            return json.load(f)
    except:
        return []

def save_users(data):
    with open(USERS_DB, "w") as f:
        json.dump(data, f, indent=2)


# =========================
# 🔐 HASH
# =========================
def hash_password(password: str):
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()

def verify_password(password: str, hashed: str):
    return bcrypt.checkpw(password.encode(), hashed.encode())


# =========================
# 🎫 JWT
# =========================
def create_token(user_id: str):
    payload = {
        "sub": user_id,
        "exp": datetime.utcnow() + timedelta(hours=12)
    }
    return jwt.encode(payload, SECRET, algorithm=ALGO)

def decode_token(token: str):
    try:
        return jwt.decode(token, SECRET, algorithms=[ALGO])
    except:
        return None


# =========================
# 👤 USER LOGIC
# =========================
def get_user(email: str):
    users = load_users()
    for u in users:
        if u["email"] == email:
            return u
    return None

def create_user(email: str, password: str):
    users = load_users()

    if get_user(email):
        raise ValueError("user_exists")

    user = {
        "id": email,
        "email": email,
        "password": hash_password(password)
    }

    users.append(user)
    save_users(users)

    return user


# =========================
# 🛡️ MIDDLEWARE (POPRAWIONE)
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

    user = get_user(data["sub"])
    if not user:
        raise HTTPException(status_code=401, detail="user_not_found")

    return user