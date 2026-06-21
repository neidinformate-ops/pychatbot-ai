from app.services.openai_service import get_client

client = get_client()


def generate_summary(

    messages

):


    try:


        text = "\n".join([

            f"{m['role']}: {m['content']}"

            for m

            in messages

        ])



        prompt = f"""

Stwórz krótkie podsumowanie rozmowy.

Uwzględnij:

- imię użytkownika

- zainteresowania

- ważne informacje

- produkty lub usługi

- preferencje



Rozmowa:



{text}

"""



        response = client.chat.completions.create(

            model="gpt-4o-mini",

            temperature=0.2,

            messages=[

                {

                    "role":"user",

                    "content":

                    prompt

                }

            ]

        )



        return (

            response

            .choices[0]

            .message

            .content

        )



    except Exception as e:


        print(

            "SUMMARY ERROR:",

            e

        )



        return ""