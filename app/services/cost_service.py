import requests

from app.config import (
    SUPABASE_URL,
    HEADERS
)


USD_TO_PLN = 4.0


PRICE_INPUT = 0.00000015

PRICE_OUTPUT = 0.00000060



def calculate_cost(

    prompt_tokens,

    completion_tokens

):


    input_cost = (

        prompt_tokens

        * PRICE_INPUT

    )


    output_cost = (

        completion_tokens

        * PRICE_OUTPUT

    )


    total = (

        input_cost

        + output_cost

    )


    return {

        "usd":

        round(total,6),

        "pln":

        round(

            total

            * USD_TO_PLN,

            4

        )

    }
def save_usage(

    assistant_id,

    session_id,

    prompt_tokens,

    completion_tokens

):


    total = (

        prompt_tokens

        + completion_tokens

    )



    cost = calculate_cost(

        prompt_tokens,

        completion_tokens

    )



    payload = {

        "assistant_id":

        assistant_id,



        "session_id":

        session_id,



        "prompt_tokens":

        prompt_tokens,



        "completion_tokens":

        completion_tokens,



        "total_tokens":

        total,



        "cost_usd":

        cost["usd"],



        "cost_pln":

        cost["pln"]

    }



    requests.post(

        f"{SUPABASE_URL}/rest/v1/ai_usage",

        headers={

            **HEADERS,

            "Prefer":

            "return=minimal"

        },

        json=payload

    )