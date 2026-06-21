from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import requests

from app.config import (
    SUPABASE_URL,
    HEADERS
)

from app.services.embedding_service import (
    create_embedding
)


router = APIRouter(

    prefix="/assistant-knowledge",

    tags=["Assistant Knowledge"]

)


class KnowledgeCreate(BaseModel):

    assistant_id: str

    content: str

    source: str = "manual"



@router.post("")

def create_knowledge(

    data: KnowledgeCreate

):

    embedding = create_embedding(

        data.content

    )


    payload = {

        "assistant_id":

        data.assistant_id,


        "content":

        data.content,


        "embedding":

        embedding,


        "source":

        data.source,


        "chunk_index":

        0

    }


    response = requests.post(

        f"{SUPABASE_URL}/rest/v1/assistant_knowledge",

        headers={

            **HEADERS,

            "Prefer":

            "return=representation"

        },

        json=payload

    )


    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )


    return response.json()[0]

@router.get("/{assistant_id}")

def get_knowledge(

    assistant_id: str

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_knowledge",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}",


            "order":

            "chunk_index.asc"

        }

    )


    return response.json()

@router.delete("/{knowledge_id}")

def delete_knowledge(

    knowledge_id: str

):

    response = requests.delete(

        f"{SUPABASE_URL}/rest/v1/assistant_knowledge",

        headers=HEADERS,

        params={

            "id":

            f"eq.{knowledge_id}"

        }

    )


    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )


    return {

        "success":True

    }