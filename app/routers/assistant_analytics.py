from fastapi import APIRouter, HTTPException

import requests

from app.config import (
    SUPABASE_URL,
    HEADERS
)


router = APIRouter(

    prefix="/assistant-analytics",

    tags=["Assistant Analytics"]

)


# ======================================
# GET ANALYTICS
# ======================================

@router.get("/{assistant_id}")

def get_analytics(

    assistant_id: str

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_analytics",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}",

            "limit":

            "1"

        }

    )



    data = response.json()



    if not data:

        raise HTTPException(

            404,

            "Analytics not found"

        )



    return data[0]



# ======================================
# CREATE DEFAULT
# ======================================

@router.post("/create/{assistant_id}")

def create_analytics(

    assistant_id: str

):

    payload = {

        "assistant_id":

        assistant_id,



        "total_conversations":0,

        "total_messages":0,

        "total_leads":0,

        "hot_leads":0,



        "conversion_rate":0,



        "lead_value":0,



        "avg_response_time":0,



        "ai_score":100,



        "tokens_used":0

    }



    response = requests.post(

        f"{SUPABASE_URL}/rest/v1/assistant_analytics",

        headers={

            **HEADERS,

            "Prefer":

            "return=representation"

        },

        json=payload

    )



    return response.json()[0]



# ======================================
# INCREMENT CONVERSATIONS
# ======================================

@router.post("/conversation/{assistant_id}")

def increment_conversations(

    assistant_id: str

):

    analytics = get_analytics(

        assistant_id

    )



    new_count = (

        analytics["total_conversations"]

        + 1

    )



    requests.patch(

        f"{SUPABASE_URL}/rest/v1/assistant_analytics",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}"

        },

        json={

            "total_conversations":

            new_count

        }

    )



    return {

        "success":True

    }



# ======================================
# INCREMENT LEADS
# ======================================

@router.post("/lead/{assistant_id}")

def increment_leads(

    assistant_id: str

):

    analytics = get_analytics(

        assistant_id

    )



    requests.patch(

        f"{SUPABASE_URL}/rest/v1/assistant_analytics",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}"

        },

        json={

            "total_leads":

            analytics["total_leads"]

            + 1

        }

    )



    return {

        "success":True

    }



# ======================================
# UPDATE SCORE
# ======================================

@router.post("/score/{assistant_id}")

def update_score(

    assistant_id: str,

    score: float

):

    requests.patch(

        f"{SUPABASE_URL}/rest/v1/assistant_analytics",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}"

        },

        json={

            "ai_score":

            score

        }

    )



    return {

        "success":True

    }