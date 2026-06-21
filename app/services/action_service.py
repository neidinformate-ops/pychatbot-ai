from app.services.intent_service import (

    detect_intent

)


from app.services.extraction_service import (

    extract_customer_data

)


def process_ai_actions(

    question:str

):


    intent = detect_intent(

        question

    )



    result = {

        "intent":

        intent,



        "save_lead":

        False,



        "save_booking":

        False

    }

    def process_ai_actions(question):

        intent = detect_intent(

            question

        )

        extracted = extract_customer_data(

            question

        )

        return {

            "intent": intent,

            "data": extracted

        }


    if intent == "lead":

        result["save_lead"] = True



    if intent == "booking":

        result["save_booking"] = True



    return result