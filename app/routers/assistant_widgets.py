from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import requests

from app.config import (
    SUPABASE_URL,
    HEADERS
)


router = APIRouter(

    prefix="/assistant-widgets",

    tags=["Assistant Widgets"]

)


# ==========================================
# MODELS
# ==========================================

class WidgetUpdate(BaseModel):

    primary_color: str | None = None

    glow_color: str | None = None

    position: str | None = None

    radius: int | None = None

    font: str | None = None

    avatar_url: str | None = None

    logo_url: str | None = None

    welcome_message: str | None = None

    starter_message: str | None = None

    online_text: str | None = None

    suggested_questions: list | None = None

    enabled: bool | None = None



# ==========================================
# CREATE DEFAULT
# ==========================================

@router.post("/create-default/{assistant_id}")

def create_default_widget(

    assistant_id: str

):

    payload = {

        "assistant_id":

        assistant_id,



        "primary_color":

        "#7C3AED",



        "glow_color":

        "#8B5CF6",



        "position":

        "right",



        "radius":

        28,



        "font":

        "Inter",



        "welcome_message":

        "Witaj 👋",



        "starter_message":

        "Jak mogę Ci pomóc?",



        "online_text":

        "Zwykle odpowiadamy w kilka sekund",



        "suggested_questions":[

            "Poznaj ofertę",

            "Zapytaj o ceny",

            "Porozmawiaj z AI"

        ],



        "enabled":

        True

    }



    response = requests.post(

        f"{SUPABASE_URL}/rest/v1/assistant_widgets",

        headers={

            **HEADERS,

            "Prefer":

            "return=representation"

        },

        json=payload

    )



    return response.json()[0]



# ==========================================
# GET
# ==========================================

@router.get("/{assistant_id}")

def get_widget(

    assistant_id: str

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_widgets",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}",

            "limit":"1"

        }

    )



    data = response.json()



    if not data:

        raise HTTPException(

            404,

            "Widget not found"

        )



    return data[0]



# ==========================================
# UPDATE
# ==========================================

@router.patch("/{assistant_id}")

def update_widget(

    assistant_id: str,

    data: WidgetUpdate

):

    payload = data.model_dump(

        exclude_none=True

    )



    response = requests.patch(

        f"{SUPABASE_URL}/rest/v1/assistant_widgets",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}"

        },

        json=payload

    )



    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )



    return {

        "success":True

    }



# ==========================================
# PUBLIC APPEARANCE
# ==========================================

@router.get("/public/{assistant_id}")

def widget_appearance(

    assistant_id: str

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_widgets",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}",

            "limit":"1"

        }

    )



    data = response.json()



    if not data:

        raise HTTPException(

            404,

            "Widget not found"

        )



    widget = data[0]



    return {

        "color":

        widget["primary_color"],



        "glow_color":

        widget["glow_color"],



        "position":

        widget["position"],



        "radius":

        widget["radius"],



        "font":

        widget["font"],



        "avatar":

        widget["avatar_url"],



        "logo":

        widget["logo_url"],



        "starter_message":

        widget["starter_message"],



        "online_text":

        widget["online_text"],



        "suggested_questions":

        widget["suggested_questions"]

    }