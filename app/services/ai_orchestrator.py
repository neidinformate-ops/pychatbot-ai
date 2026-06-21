from app.services.openai_service import (

    get_client

)

client = get_client()

from app.config import OPENAI_API_KEY

from app.services.prompt_service import (
    build_system_prompt
)

from app.services.memory_service import (
    get_memory,
    save_message,
    get_conversation_summary,
    get_user_profile
)

from app.services.search_service import (
    semantic_search
)

from app.services.intent_service import (
    detect_intent
)

from app.services.extraction_service import (
    extract_customer_data
)

from app.services.lead_service import (
    save_lead
)

from app.services.booking_service import (
    save_booking
)

from app.services.analytics_service import (
    increment_messages,
    increment_leads,
    increment_bookings
)

from app.services.conversation_summary_service import (

generate_summary

)

summary = generate_summary(

messages

)

save_summary(

assistant_id,

session_id,

summary

)

profile = extract_profile(

    messages

)

save_user_profile(

    assistant_id,

    session_id,

    profile

)

async def handle_message(

    assistant_id: str,

    session_id: str,

    question: str

):

    try:


        # SAVE USER MESSAGE

        save_message(

            assistant_id,

            session_id,

            "user",

            question

        )


        # MEMORY

        memory = get_memory(

            assistant_id,

            session_id

        )


        # SUMMARY

        summary = get_conversation_summary(

            assistant_id,

            session_id

        )


        # USER PROFILE

        user_profile = get_user_profile(

            assistant_id,

            session_id

        )


        # KNOWLEDGE

        knowledge = semantic_search(

            assistant_id,

            question

        )


        # PROMPT

        system_prompt = build_system_prompt(

            assistant_id,

            knowledge

        )


        messages = [

            {

                "role":"system",

                "content":

                f"""

{system_prompt}


SUMMARY:

{summary}



USER PROFILE:

{user_profile}


"""

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


        # GPT STREAM

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


        # SAVE AI

        save_message(

            assistant_id,

            session_id,

            "assistant",

            full_answer

        )

        messages = get_memory(

            assistant_id,

            session_id,

            limit=20

        )

        increment_messages(

            assistant_id

        )


        # INTENT

        intent = detect_intent(

            question

        )


        customer = extract_customer_data(

            question

        )


        # LEAD

        if intent == "lead":


            save_lead(

                assistant_id,

                customer

            )


            increment_leads(

                assistant_id

            )


        # BOOKING

        if intent == "booking":


            save_booking(

                assistant_id,

                customer

            )


            increment_bookings(

                assistant_id

            )


    except Exception as e:


        print(

            "AI ORCHESTRATOR ERROR:",

            e

        )


        yield (

            "Przepraszam, "

            "wystąpił błąd "

            "podczas generowania odpowiedzi."

        )