from fastapi import APIRouter, Depends
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

    tags=["Assistant Branding"]

)


class BrandingData(BaseModel):

    company_name:str=""

    logo_url:str=""

    primary_color:str="#7C3AED"

    secondary_color:str="#111827"

    custom_domain:str=""

    custom_css:str=""


@router.get("/{assistant_id}/branding")

def get_branding(

    assistant_id:str,

    user=Depends(get_current_user)

):

    response=requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_branding",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}"

        }

    )

    data=response.json()

    if len(data)==0:

        return BrandingData()

    return data[0]



@router.post("/{assistant_id}/branding")

def save_branding(

    assistant_id:str,

    data:BrandingData,

    user=Depends(get_current_user)

):

    payload={

        "assistant_id":

            assistant_id,

        **data.dict()

    }


    existing=requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_branding",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}"

        }

    )


    if len(existing.json())==0:

        requests.post(

            f"{SUPABASE_URL}/rest/v1/assistant_branding",

            headers={

                **HEADERS,

                "Prefer":

                "return=representation"

            },

            json=payload

        )

    else:

        requests.patch(

            f"{SUPABASE_URL}/rest/v1/assistant_branding",

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