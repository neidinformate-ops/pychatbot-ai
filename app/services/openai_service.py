from openai import OpenAI

from app.config import OPENAI_API_KEY


_client = None


def get_client():

    global _client


    if _client is None:

        _client = OpenAI(

            api_key=OPENAI_API_KEY

        )


    return _client