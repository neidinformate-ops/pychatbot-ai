from app.services.openai_service import (

    get_client

)


client = get_client()



def extract_profile(

    messages

):


    conversation = "\n".join([

        f"{m['role']}:{m['content']}"

        for m

        in messages

    ])



    prompt=f"""

Wyciągnij profil klienta.



Zwróć JSON:



{{

"name":"",

"email":"",

"phone":"",

"budget":"",

"interests":[]

}}



Rozmowa:



{conversation}

"""



    response = (

        client.chat.completions.create(

            model="gpt-4o-mini",

            response_format={

                "type":

                "json_object"

            },

            messages=[

                {

                    "role":"user",

                    "content":

                    prompt

                }

            ]

        )

    )



    return (

        response

        .choices[0]

        .message

        .content

    )