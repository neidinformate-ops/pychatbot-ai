import requests

from app.config import (

    SUPABASE_URL,

    HEADERS

)



def get_analytics(

    assistant_id

):


    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_analytics",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}",

            "limit":"1"

        }

    )



    data = response.json()



    if not data:

        return None



    return data[0]

def update_field(

    assistant_id,

    field

):


    analytics = get_analytics(

        assistant_id

    )



    if not analytics:

        return



    current = (

        analytics

        .get(field,0)

    )



    requests.patch(

        f"{SUPABASE_URL}/rest/v1/assistant_analytics",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}"

        },

        json={

            field:

            current+1

        }

    )

    def increment_conversations(

            assistant_id

    ):
        update_field(

            assistant_id,

            "total_conversations"

        )

        def increment_messages(

                assistant_id

        ):
            update_field(

                assistant_id,

                "total_messages"

            )

            def increment_leads(

                    assistant_id

            ):
                update_field(

                    assistant_id,

                    "total_leads"

                )

                def increment_bookings(

                        assistant_id

                ):
                    update_field(

                        assistant_id,

                        "total_bookings"

                    )

                    def increment_hot_leads(

                            assistant_id

                    ):
                        update_field(

                            assistant_id,

                            "hot_leads"

                        )

                        def update_ai_score(

                                assistant_id,

                                score

                        ):
                            requests.patch(

                                f"{SUPABASE_URL}/rest/v1/assistant_analytics",

                                headers=HEADERS,

                                params={

                                    "assistant_id":

                                        f"eq.{assistant_id}"

                                },

                                json={

                                    "ai_score":

                                        score

                                }

                            )

                            def add_tokens(

                                    assistant_id,

                                    amount

                            ):
                                analytics = get_analytics(

                                    assistant_id

                                )

                                current = (

                                    analytics

                                    .get(

                                        "tokens_used",

                                        0

                                    )

                                )

                                requests.patch(

                                    f"{SUPABASE_URL}/rest/v1/assistant_analytics",

                                    headers=HEADERS,

                                    params={

                                        "assistant_id":

                                            f"eq.{assistant_id}"

                                    },

                                    json={

                                        "tokens_used":

                                            current + amount

                                    }

                                )