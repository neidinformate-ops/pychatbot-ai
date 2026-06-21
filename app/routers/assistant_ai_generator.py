from fastapi import APIRouter
from pydantic import BaseModel
from openai import OpenAI

import requests

from app.config import (
    OPENAI_API_KEY,
    SUPABASE_URL,
    HEADERS
)


router = APIRouter(

    prefix="/assistant-ai",

    tags=["Assistant AI Generator"]

)


client = OpenAI(

    api_key=OPENAI_API_KEY

)



class GenerateAgent(BaseModel):

    assistant_id:str

    name:str

    industry:str

    description:str



@router.post("/generate")

def generate_agent_ai(

    data: GenerateAgent

):


    prompt = f"""

Stwórz konfigurację Agenta AI.

Nazwa firmy:

{data.name}


Branża:

{data.industry}


Opis:

{data.description}



Zwróć JSON:



{{

"system_prompt":"",

"tone":"",

"personality":"",

"restrictions":"",

"starter_message":"",

"faq":[],

"suggested_questions":[],

"lead_strategy":"",

"booking_strategy":""

}}

"""


    response = client.chat.completions.create(

        model="gpt-4o-mini",

        response_format={

            "type":"json_object"

        },

        messages=[

            {

                "role":"user",

                "content":prompt

            }

        ]

    )



    content = (

        response

        .choices[0]

        .message

        .content

    )



    import json



    generated = json.loads(

        content

    )



    generated["assistant_id"] = (

        data.assistant_id

    )



    requests.post(

        f"{SUPABASE_URL}/rest/v1/assistant_prompts",

        headers={

            **HEADERS,

            "Prefer":

            "return=representation"

        },

        json=generated

    )



    return {

        "success":True,

        "data":generated

    }