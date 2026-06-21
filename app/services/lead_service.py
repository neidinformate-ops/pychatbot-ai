import requests

from app.config import (

    SUPABASE_URL,

    HEADERS

)


def calculate_lead_score(data):

    score = 0


    if data.get("email"):

        score += 30


    if data.get("phone"):

        score += 30


    if data.get("name"):

        score += 10


    if data.get("service"):

        score += 20


    if data.get("booking_date"):

        score += 10


    return min(score,100)
def get_temperature(score):


    if score >= 80:

        return "hot"


    if score >= 50:

        return "warm"


    return "cold"
def save_lead(

    assistant_id,

    data

):


    score = calculate_lead_score(

        data

    )


    temperature = (

        get_temperature(

            score

        )

    )



    payload = {

        "assistant_id":

        assistant_id,



        "name":

        data.get("name"),



        "email":

        data.get("email"),



        "phone":

        data.get("phone"),



        "status":

        "new",



        "lead_score":

        score,



        "lead_temperature":

        temperature,



        "source":

        "chat"

    }



    requests.post(

        f"{SUPABASE_URL}/rest/v1/assistant_leads",

        headers={

            **HEADERS,

            "Prefer":

            "return=minimal"

        },

        json=payload

    )