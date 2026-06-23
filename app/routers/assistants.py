from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from auth import get_current_user

import requests
import os

SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {
    "apikey": SUPABASE_KEY,
    "Authorization": f"Bearer {SUPABASE_KEY}",
    "Content-Type": "application/json"
}

router = APIRouter(
    prefix="/assistants",
    tags=["Assistants"]
)


class AssistantCreate(BaseModel):

    name: str

    assistant_type: str

    industry_template: str | None = None

    description: str | None = None

    system_prompt: str | None = None


class AssistantUpdate(BaseModel):
    name: str | None = None
    assistant_type: str | None = None
    industry_template: str | None = None
    status: str | None = None


@router.post("")
def create_assistant(
    data: AssistantCreate,
    user=Depends(get_current_user)
):

    print("========== CREATE ASSISTANT ==========")
    print("USER:")
    print(user)

    payload = {

        "client_id": user["id"],

        "name": data.name,

        "assistant_type": data.assistant_type,

        "industry_template": data.industry_template,

        "status": "active"

    }

    print("PAYLOAD:")
    print(payload)

    response = requests.post(

        f"{SUPABASE_URL}/rest/v1/assistants",

        headers={
            **HEADERS,
            "Prefer": "return=representation"
        },

        json=payload

    )

    print("STATUS:")
    print(response.status_code)

    print("TEXT:")
    print(response.text)

    return response.json()


@router.get("")
def get_assistants(
    user=Depends(get_current_user)
):

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/assistants",
        headers=HEADERS,
        params={
            "client_id": f"eq.{user['id']}",
            "order": "created_at.desc"
        }
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=response.text
        )

    return response.json()


@router.get("/{assistant_id}")
def get_assistant(
    assistant_id: str,
    user=Depends(get_current_user)
):

    response = requests.get(
        f"{SUPABASE_URL}/rest/v1/assistants",
        headers=HEADERS,
        params={
            "id": f"eq.{assistant_id}",
            "client_id": f"eq.{user['id']}"
        }
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=response.text
        )

    data = response.json()

    if not data:
        raise HTTPException(
            status_code=404,
            detail="Assistant not found"
        )

    return data[0]


@router.patch("/{assistant_id}")
def update_assistant(
    assistant_id: str,
    data: AssistantUpdate,
    user=Depends(get_current_user)
):

    payload = data.model_dump(
        exclude_none=True
    )

    response = requests.patch(
        f"{SUPABASE_URL}/rest/v1/assistants",
        headers=HEADERS,
        params={
            "id": f"eq.{assistant_id}",
            "client_id": f"eq.{user['id']}"
        },
        json=payload
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=response.text
        )

    return {
        "success": True
    }


@router.delete("/{assistant_id}")
def delete_assistant(
    assistant_id: str,
    user=Depends(get_current_user)
):

    response = requests.delete(
        f"{SUPABASE_URL}/rest/v1/assistants",
        headers=HEADERS,
        params={
            "id": f"eq.{assistant_id}",
            "client_id": f"eq.{user['id']}"
        }
    )

    if response.status_code >= 400:
        raise HTTPException(
            status_code=500,
            detail=response.text
        )

    return {
        "success": True
    }