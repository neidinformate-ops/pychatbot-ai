import requests

from app.config import (
    SUPABASE_URL,
    HEADERS
)

cache_key = (

f"prompt:{assistant_id}"

)

def get_prompt_settings(

    assistant_id: str

):

    try:

        response = requests.get(

            f"{SUPABASE_URL}/rest/v1/assistant_prompts",

            headers=HEADERS,

            params={

                "assistant_id":

                f"eq.{assistant_id}",

                "limit":"1"

            }

        )



        data = response.json()



        if not data:

            return {

                "system_prompt":"",

                "tone":"Profesjonalny",

                "personality":"Pomocny",

                "restrictions":""

            }



        return data[0]



    except:

        return {

            "system_prompt":"",

            "tone":"Profesjonalny",

            "personality":"Pomocny",

            "restrictions":""

        }



def build_system_prompt(

    assistant_id: str,

    knowledge: str

):

    settings = get_prompt_settings(

        assistant_id

    )



    prompt = f"""

Jesteś profesjonalnym Agentem AI.



TON:

{settings["tone"]}



OSOBOWOŚĆ:

{settings["personality"]}



INSTRUKCJE:

{settings["system_prompt"]}



OGRANICZENIA:

{settings["restrictions"]}



WIEDZA:

{knowledge}



WAŻNE:

- odpowiadaj tylko na podstawie wiedzy

- nie wymyślaj informacji

- odpowiadaj naturalnie

- odpowiadaj zwięźle

"""



    return prompt