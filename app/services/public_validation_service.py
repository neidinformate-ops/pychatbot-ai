import requests

from app.config import (

    SUPABASE_URL,

    HEADERS

)



def assistant_exists(

    assistant_id: str

):


    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistants",

        headers=HEADERS,

        params={

            "id":

            f"eq.{assistant_id}",

            "limit":"1"

        }

    )


    data = response.json()


    return len(data) > 0

def widget_enabled(

    assistant_id: str

):


    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_widgets",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}",


            "enabled":

            "eq.true",


            "limit":"1"

        }

    )


    data=response.json()


    return len(data)>0