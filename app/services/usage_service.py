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

    try:

        url = (
            f"{SUPABASE_URL}"
            "/rest/v1/subscriptions"
        )

        res = requests.get(

            url,

            headers=HEADERS,

            params={
                "client_id":
                    f"eq.{client_id}",

                "select":
                    "plan",

                "limit":
                    1
            }
        )

        data = res.json()

        if not data:

            return "free"

        return (
            data[0]
            .get("plan", "free")
            .lower()
        )

    except Exception:

        return "free"

    #
    # TEMP FIX
    # zawsze free
    #

    return "free"


def get_limit(plan: str) -> int:
    return PLAN_LIMITS.get(plan, 10)


def get_usage(client_id: str) -> int:

    try:

        today = get_today()

        url = (
            f"{SUPABASE_URL}"
            "/rest/v1/usage"
        )

        res = requests.get(

            url,

            headers=HEADERS,

            params={

                "client_id":
                    f"eq.{client_id}",

                "date":
                    f"eq.{today}",

                "select":
                    "requests"
            }
        )

        data = res.json()

        if not data:

            return 0

        return (
            data[0]
            .get("requests", 0)
        )

    except Exception:

        return 0

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

    today = get_today()

    try:

        url = (
            f"{SUPABASE_URL}"
            "/rest/v1/usage"
        )

        res = requests.get(

            url,

            headers=HEADERS,

            params={

                "client_id":
                    f"eq.{client_id}",

                "date":
                    f"eq.{today}"
            }
        )

        rows = res.json()

        #
        # istnieje rekord
        #
        if rows:

            row = rows[0]

            requests.patch(

                url,

                headers=HEADERS,

                params={
                    "id":
                        f"eq.{row['id']}"
                },

                json={
                    "requests":
                        row["requests"] + 1
                }
            )

        #
        # pierwszy request dnia
        #
        else:

            requests.post(

                url,

                headers=HEADERS,

                json={

                    "client_id":
                        client_id,

                    "date":
                        today,

                    "requests":
                        1
                }
            )

    except Exception as e:

        print(
            "USAGE ERROR:",
            e
        )

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