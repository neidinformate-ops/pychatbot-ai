from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

import requests

from app.config import (
    SUPABASE_URL,
    HEADERS
)


router = APIRouter(

    prefix="/assistant-bookings",

    tags=["Assistant Bookings"]

)


# ======================================
# MODELS
# ======================================

class BookingCreate(BaseModel):

    assistant_id: str

    customer_name: str

    email: str | None = None

    phone: str | None = None

    service: str | None = None

    booking_date: str

    booking_time: str

    people: int = 1

    notes: str | None = None



class BookingUpdate(BaseModel):

    customer_name: str | None = None

    email: str | None = None

    phone: str | None = None

    service: str | None = None

    booking_date: str | None = None

    booking_time: str | None = None

    people: int | None = None

    status: str | None = None

    notes: str | None = None



# ======================================
# CREATE BOOKING
# ======================================

@router.post("")

def create_booking(

    booking: BookingCreate

):

    payload = booking.model_dump()



    response = requests.post(

        f"{SUPABASE_URL}/rest/v1/assistant_bookings",

        headers={

            **HEADERS,

            "Prefer":

            "return=representation"

        },

        json=payload

    )



    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )



    return response.json()[0]



# ======================================
# GET BOOKINGS
# ======================================

@router.get("/{assistant_id}")

def get_bookings(

    assistant_id: str

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_bookings",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}",

            "order":

            "booking_date.asc"

        }

    )



    return response.json()



# ======================================
# UPDATE BOOKING
# ======================================

@router.patch("/{booking_id}")

def update_booking(

    booking_id: str,

    data: BookingUpdate

):

    payload = data.model_dump(

        exclude_none=True

    )



    response = requests.patch(

        f"{SUPABASE_URL}/rest/v1/assistant_bookings",

        headers=HEADERS,

        params={

            "id":

            f"eq.{booking_id}"

        },

        json=payload

    )



    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )



    return {

        "success": True

    }



# ======================================
# DELETE BOOKING
# ======================================

@router.delete("/{booking_id}")

def delete_booking(

    booking_id: str

):

    response = requests.delete(

        f"{SUPABASE_URL}/rest/v1/assistant_bookings",

        headers=HEADERS,

        params={

            "id":

            f"eq.{booking_id}"

        }

    )



    if response.status_code >= 400:

        raise HTTPException(

            500,

            response.text

        )



    return {

        "success": True

    }



# ======================================
# CALENDAR VIEW
# ======================================

@router.get("/calendar/{assistant_id}")

def get_calendar(

    assistant_id: str

):

    response = requests.get(

        f"{SUPABASE_URL}/rest/v1/assistant_bookings",

        headers=HEADERS,

        params={

            "assistant_id":

            f"eq.{assistant_id}",

            "select":

            "customer_name,booking_date,booking_time,status,service"

        }

    )



    return response.json()