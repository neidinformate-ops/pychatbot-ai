from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_user

import requests
import os


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")


HEADERS = {

    "apikey": SUPABASE_KEY,

    "Authorization":
        f"Bearer {SUPABASE_KEY}",

    "Content-Type":
        "application/json"

}


router = APIRouter(

    prefix="/assistants",

    tags=["Assistants"]

)


# -------------------------
# MODELS
# -------------------------


class AssistantCreate(BaseModel):

    name: str

    industry: str | None = None

    description: str | None = None

    website: str | None = None

    phone: str | None = None

    email: str | None = None

    language: str = "pl"



class AssistantUpdate(BaseModel):

    name: str | None = None

    industry: str | None = None

    description: str | None = None

    website: str | None = None

    phone: str | None = None

    email: str | None = None

    language: str | None = None

    status: str | None = None


# -------------------------
# CREATE
# -------------------------


@router.post("")

def create_assistant(

    data: AssistantCreate,

    user=Depends(get_current_user)

):

    payload = {

        "owner_id": user["id"],

        "name": data.name,

        "industry": data.industry,

        "description": data.description,

        "website": data.website,

        "phone": data.phone,

        "email": data.email,

        "language": data.language,

        "status": "active"

    }

    response = requests.post(

        f"{SUPABASE_URL}/rest/v1/assistants",

        headers={

            **HEADERS,

            "Prefer": "return=representation"

        },

        json=payload

    )

    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )

    return response.json()[0]


# -------------------------
# GET ALL
# -------------------------


@router.get("")

def get_assistants(

    user=Depends(get_current_user)

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistants",

        headers=HEADERS,

        params={

            "user_id":
                f"eq.{user['id']}",

            "order":
                "created_at.desc"

        }

    )

    return response.json()


# -------------------------
# GET ONE
# -------------------------


@router.get("/{assistant_id}")

def get_assistant(

    assistant_id: str,

    user=Depends(get_current_user)

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistants",

        headers=HEADERS,

        params={

            "id":
                f"eq.{assistant_id}",

            "user_id":
                f"eq.{user['id']}"

        }

    )

    data = response.json()

    if len(data) == 0:

        raise HTTPException(

            404,

            "Assistant not found"

        )

    return data[0]


# -------------------------
# UPDATE
# -------------------------


@router.patch("/{assistant_id}")

def update_assistant(

    assistant_id: str,

    data: AssistantUpdate,

    user=Depends(get_current_user)

):

    response = requests.patch(

        f"{SUPABASE_URL}/rest/v1/assistants",

        headers=HEADERS,

        params={

            "id":
                f"eq.{assistant_id}",

            "user_id":
                f"eq.{user['id']}"

        },

        json=data.model_dump(

            exclude_none=True

        )

    )

    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )

    return {

        "success": True

    }


# -------------------------
# DELETE
# -------------------------


@router.delete("/{assistant_id}")

def delete_assistant(

    assistant_id: str,

    user=Depends(get_current_user)

):

    response = requests.delete(

        f"{SUPABASE_URL}/rest/v1/assistants",

        headers=HEADERS,

        params={

            "id":
                f"eq.{assistant_id}",

            "user_id":
                f"eq.{user['id']}"

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