import requests

from app.config import (
    SUPABASE_URL,
    HEADERS
)


# =====================================
# SAVE MESSAGE
# =====================================

def save_summary(

    assistant_id,

    session_id,

    summary

):
    requests.patch(

        f"{SUPABASE_URL}/rest/v1/assistant_conversations",

        headers=HEADERS,

        params={

            "assistant_id":

                f"eq.{assistant_id}",

            "session_id":

                f"eq.{session_id}"

        },

        json={

            "summary":

                summary

        }

    )

def save_user_profile(

    assistant_id,

    session_id,

    profile

):
    requests.patch(

        f"{SUPABASE_URL}/rest/v1/assistant_conversations",

        headers=HEADERS,

        params={

            "assistant_id":

                f"eq.{assistant_id}",

            "session_id":

                f"eq.{session_id}"

        },

        json={

            "user_profile":

                profile

        }

    )

def save_message(

    assistant_id: str,

    session_id: str,

    role: str,

    content: str

):

    payload = {

        "assistant_id":

        assistant_id,



        "session_id":

        session_id,



        "role":

        role,



        "content":

        content

    }


    try:

        requests.post(

            f"{SUPABASE_URL}/rest/v1/assistant_messages",

            headers={

                **HEADERS,

                "Prefer":

                "return=minimal"

            },

            json=payload

        )

    except Exception as e:

        print(

            "SAVE MESSAGE ERROR:",

            e

        )


# =====================================
# GET MEMORY
# =====================================

def get_memory(

    assistant_id,

    session_id,

    limit=12

):


    try:

        response = requests.get(

            f"{SUPABASE_URL}/rest/v1/assistant_messages",

            headers=HEADERS,

            params={

                "assistant_id":

                f"eq.{assistant_id}",



                "session_id":

                f"eq.{session_id}",



                "order":

                "created_at.asc",



                "limit":

                limit

            }

        )


        data = response.json()


        return [

            {

                "role":

                msg["role"],



                "content":

                msg["content"]

            }

            for msg in data

        ]


    except:

        return []


def get_conversation_summary(

            assistant_id,

            session_id

    ):

        response = requests.get(

            f"{SUPABASE_URL}/rest/v1/assistant_conversations",

            headers=HEADERS,

            params={

                "assistant_id":

                    f"eq.{assistant_id}",

                "session_id":

                    f"eq.{session_id}",

                "limit": "1"

            }

        )

        data = response.json()

        if not data:
            return ""

        return data[0].get(

            "summary",

            ""

        )

    def get_user_profile(

            assistant_id,

            session_id

    ):

        response = requests.get(

            f"{SUPABASE_URL}/rest/v1/assistant_conversations",

            headers=HEADERS,

            params={

                "assistant_id":

                    f"eq.{assistant_id}",

                "session_id":

                    f"eq.{session_id}",

                "limit": "1"

            }

        )

        data = response.json()

        if not data:
            return {}

        return data[0].get(

            "user_profile",

            {}

        )