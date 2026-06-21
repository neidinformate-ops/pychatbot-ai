from app.services.openai_service import (

    get_client

)


client = get_client()


def create_embedding(text: str):

    response = client.embeddings.create(

        model="text-embedding-3-small",

        input=text

    )

    return response.data[0].embedding