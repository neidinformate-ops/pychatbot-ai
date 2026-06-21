import requests

from app.config import (

    SUPABASE_URL,

    HEADERS

)



def check_booking_conflict(

    assistant_id,

    booking_date,

    booking_time

):


    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_bookings",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}",


            "booking_date":

            f"eq.{booking_date}",


            "booking_time":

            f"eq.{booking_time}",


            "status":

            "eq.booked"

        }

    )



    bookings = response.json()



    return len(bookings) > 0

def save_booking(

    assistant_id,

    data

):


    conflict = (

        check_booking_conflict(

            assistant_id,

            data.get("booking_date"),

            data.get("booking_time")

        )

    )



    if conflict:

        return {

            "success":False,

            "message":

            "Termin zajęty"

        }



    payload = {

        "assistant_id":

        assistant_id,



        "customer_name":

        data.get("name"),



        "email":

        data.get("email"),



        "phone":

        data.get("phone"),



        "service":

        data.get("service"),



        "booking_date":

        data.get("booking_date"),



        "booking_time":

        data.get("booking_time"),



        "people":

        data.get("people",1),



        "status":

        "booked",



        "confirmed":

        False,



        "source":

        "chat"

    }



    requests.post(

        f"{SUPABASE_URL}/rest/v1/assistant_bookings",

        headers={

            **HEADERS,

            "Prefer":

            "return=minimal"

        },

        json=payload

    )



    return {

        "success":True

    }