from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import requests

from app.config import (
    SUPABASE_URL,
    HEADERS
)


router = APIRouter(

    prefix="/assistant-leads",

    tags=["Assistant Leads"]

)


# =====================================
# MODELS
# =====================================

class LeadCreate(BaseModel):

    assistant_id: str

    name: str | None = None

    email: str | None = None

    phone: str | None = None

    status: str = "new"

    lead_value: float | None = None

    source: str = "chat"

    notes: str | None = None



class LeadUpdate(BaseModel):

    name: str | None = None

    email: str | None = None

    phone: str | None = None

    status: str | None = None

    lead_value: float | None = None

    source: str | None = None

    notes: str | None = None


# =====================================
# CREATE
# =====================================

@router.post("")

def create_lead(

    lead: LeadCreate

):

    response = requests.post(

        f"{SUPABASE_URL}/rest/v1/assistant_leads",

        headers={

            **HEADERS,

            "Prefer":

            "return=representation"

        },

        json=lead.model_dump()

    )



    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )



    return response.json()[0]



# =====================================
# GET ALL
# =====================================

@router.get("/{assistant_id}")

def get_leads(

    assistant_id: str

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_leads",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}",

            "order":

            "created_at.desc"

        }

    )



    return response.json()



# =====================================
# UPDATE
# =====================================

@router.patch("/{lead_id}")

def update_lead(

    lead_id: str,

    data: LeadUpdate

):

    payload = data.model_dump(

        exclude_none=True

    )



    response = requests.patch(

        f"{SUPABASE_URL}/rest/v1/assistant_leads",

        headers=HEADERS,

        params={

            "id":

            f"eq.{lead_id}"

        },

        json=payload

    )



    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )



    return {

        "success": True

    }



# =====================================
# DELETE
# =====================================

@router.delete("/{lead_id}")

def delete_lead(

    lead_id: str

):

    response = requests.delete(

        f"{SUPABASE_URL}/rest/v1/assistant_leads",

        headers=HEADERS,

        params={

            "id":

            f"eq.{lead_id}"

        }

    )



    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )



    return {

        "success": True

    }



# =====================================
# STATS
# =====================================

@router.get("/stats/{assistant_id}")

def lead_stats(

    assistant_id: str

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_leads",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}"

        }

    )



    leads = response.json()



    total = len(leads)



    total_value = sum(

        float(

            lead.get(

                "lead_value",

                0

            ) or 0

        )

        for lead in leads

    )



    return {

        "total": total,

        "value": total_value

    }