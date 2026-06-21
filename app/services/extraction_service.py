from app.services.openai_service import (

    get_client

)


client = get_client()

def extract_customer_data(message: str):

    prompt = f"""

Wyciągnij dane klienta.

Zwróć WYŁĄCZNIE JSON:

{{
"name":"",
"email":"",
"phone":"",
"service":"",
"booking_date":"",
"booking_time":"",
"people":1
}}


Wiadomość:

{message}

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


    return json.loads(content)