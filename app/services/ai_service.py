from openai import OpenAI

from app.config import OPENAI_API_KEY

from app.services.memory_service import (
    get_memory,
    save_message
)

from app.services.search_service import (
    semantic_search
)

from app.services.prompt_service import (
    build_system_prompt
)


client = OpenAI(
    api_key=OPENAI_API_KEY
)



async def ask_public(

    assistant_id: str,

    session_id: str,

    question: str

):

    # -----------------------
    # MEMORY
    # -----------------------

    memory = get_memory(

        assistant_id,

        session_id

    )



    # -----------------------
    # KNOWLEDGE
    # -----------------------

    results = semantic_search(

        assistant_id,

        question

    )



    knowledge = "\n\n".join(

        [

            r["content"]

            for r

            in results

        ]

    )



    # -----------------------
    # SYSTEM PROMPT
    # -----------------------

    system_prompt = build_system_prompt(

        assistant_id,

        knowledge

    )



    messages = [

        {

            "role":"system",

            "content":

            system_prompt

        }

    ]



    messages.extend(

        memory

    )



    messages.append(

        {

            "role":"user",

            "content":

            question

        }

    )



    # save user

    save_message(

        assistant_id,

        session_id,

        "user",

        question

    )



    # -----------------------
    # GPT STREAM
    # -----------------------

    stream = client.chat.completions.create(

        model="gpt-4o-mini",

        messages=messages,

        stream=True,

        temperature=0.4

    )



    full_answer = ""



    for chunk in stream:



        delta = (

            chunk

            .choices[0]

            .delta

            .content

        )



        if not delta:

            continue



        full_answer += delta



        yield delta



    # save assistant

    save_message(

        assistant_id,

        session_id,

        "assistant",

        full_answer

    )