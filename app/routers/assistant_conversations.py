from fastapi import APIRouter
from fastapi import Depends

from auth import get_current_user

import requests
import os

SUPABASE_URL=os.getenv("SUPABASE_URL")
SUPABASE_KEY=os.getenv("SUPABASE_KEY")

HEADERS={

"apikey":SUPABASE_KEY,

"Authorization":

f"Bearer {SUPABASE_KEY}"

}

router=APIRouter(

prefix="/assistants",

tags=["Assistant Conversations"]

)


@router.get(

"/conversation/{conversation_id}"

)

def get_messages(

conversation_id:str,

user=Depends(get_current_user)

):

response=requests.get(

f"{SUPABASE_URL}/rest/v1/assistant_messages",

headers=HEADERS,

params={

"conversation_id":

f"eq.{conversation_id}",

"order":

"created_at.asc"

}

)

return response.json()
