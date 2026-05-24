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

    #
    # TEMP FIX
    # zawsze free
    #

    return "free"


def get_limit(plan: str) -> int:
    return PLAN_LIMITS.get(plan, 10)


def get_usage(client_id: str) -> int:

    #
    # TEMP FIX
    #

    return 0


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

    #
    # TEMP FIX
    #

    return
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