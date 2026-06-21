from app.services.openai_service import (

    get_client

)


client = get_client()



def detect_intent(

    message: str

):

    prompt = f"""

Określ intencję użytkownika.

Możliwe wartości:

booking

lead

sales

support

general



Zwróć TYLKO jedno słowo.



Wiadomość:

{message}

"""



    response = client.chat.completions.create(

        model="gpt-4o-mini",

        temperature=0,

        messages=[

            {

                "role":"user",

                "content":

                prompt

            }

        ]

    )



    intent = (

        response

        .choices[0]

        .message

        .content

        .strip()

        .lower()

    )



    allowed = [

        "booking",

        "lead",

        "sales",

        "support",

        "general"

    ]



    if intent not in allowed:

        return "general"



    return intent