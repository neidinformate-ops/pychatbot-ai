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

    tags=["Assistant Prompts"]

)


class PromptData(BaseModel):

    system_prompt: str = ""

    personality: str = ""

    tone: str = ""

    goal: str = ""

    greeting: str = ""

    restrictions: str = ""


@router.get("/{assistant_id}/prompt")

def get_prompt(

    assistant_id: str,

    user=Depends(get_current_user)

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_prompts",

        headers=HEADERS,

        params={

            "assistant_id":

                f"eq.{assistant_id}"

        }

    )

    data = response.json()

    if len(data) == 0:

        return {

            "system_prompt":"",

            "personality":"",

            "tone":"",

            "goal":"",

            "greeting":"",

            "restrictions":""

        }

    return data[0]



@router.post("/{assistant_id}/prompt")

def save_prompt(

    assistant_id:str,

    data:PromptData,

    user=Depends(get_current_user)

):

    existing=requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_prompts",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}"

        }

    )


    exists=existing.json()


    payload={

        "assistant_id":

            assistant_id,

        "system_prompt":

            data.system_prompt,

        "personality":

            data.personality,

        "tone":

            data.tone,

        "goal":

            data.goal,

        "greeting":

            data.greeting,

        "restrictions":

            data.restrictions,

    }


    if len(exists)==0:

        response=requests.post(

            f"{SUPABASE_URL}/rest/v1/assistant_prompts",

            headers={

                **HEADERS,

                "Prefer":

                "return=representation"

            },

            json=payload

        )

    else:

        response=requests.patch(

            f"{SUPABASE_URL}/rest/v1/assistant_prompts",

            headers=HEADERS,

            params={

                "assistant_id":

                f"eq.{assistant_id}"

            },

            json=payload

        )


    return {

        "success":True

    }