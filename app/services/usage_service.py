import requests
from datetime import date
from fastapi import HTTPException
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_SERVICE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}


PLAN_LIMITS = {
    "free": 10,
    "pro": 200,
    "business": 10000
}


def get_today():
    return str(date.today())


def get_user_plan(client_id: str) -> str:
    url = f"{SUPABASE_URL}/rest/v1/users?id=eq.{client_id}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="User fetch failed")

    data = res.json()

    if not data:
        raise HTTPException(status_code=404, detail="User not found")

    return data[0].get("plan", "free")


def get_limit(plan: str) -> int:
    return PLAN_LIMITS.get(plan, 10)


def get_usage(client_id: str) -> int:
    today = get_today()

    url = f"{SUPABASE_URL}/rest/v1/usage?client_id=eq.{client_id}&date=eq.{today}"
    res = requests.get(url, headers=HEADERS)

    if res.status_code != 200:
        raise HTTPException(status_code=500, detail="Usage fetch failed")

    data = res.json()

    if not data:
        return 0

    return data[0]["requests"]


def check_limit(client_id: str):
    plan = get_user_plan(client_id)
    usage = get_usage(client_id)
    limit = get_limit(plan)

    if usage >= limit:
        raise HTTPException(status_code=403, detail="LIMIT_REACHED")

    return {
        "plan": plan,
        "usage": usage,
        "limit": limit
    }


def increment_usage(client_id: str):
    today = get_today()

    # UPSERT → atomic increment
    url = f"{SUPABASE_URL}/rest/v1/rpc/increment_usage"

    payload = {
        "p_client_id": client_id,
        "p_date": today
    }

    res = requests.post(url, headers=HEADERS, json=payload)

    if res.status_code not in [200, 204]:
        raise HTTPException(status_code=500, detail="Usage increment failed")