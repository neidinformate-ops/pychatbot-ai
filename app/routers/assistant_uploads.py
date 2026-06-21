from fastapi import APIRouter
from fastapi import UploadFile
from fastapi import File
from fastapi import Depends
from fastapi import HTTPException

from auth import get_current_user

import requests
import os

from pypdf import PdfReader
from docx import Document
import tempfile


SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

HEADERS = {

    "apikey": SUPABASE_KEY,

    "Authorization":
        f"Bearer {SUPABASE_KEY}",

    "Content-Type":
        "application/json"

}

router = APIRouter(

    prefix="/assistants",

    tags=["Assistant Uploads"]

)


def read_pdf(path):

    reader = PdfReader(path)

    text = ""

    for page in reader.pages:

        text += page.extract_text() + "\n"

    return text


def read_docx(path):

    doc = Document(path)

    text = "\n".join(

        p.text

        for p in doc.paragraphs

    )

    return text


@router.post("/{assistant_id}/upload")

async def upload_file(

    assistant_id:str,

    file:UploadFile=File(...),

    user=Depends(get_current_user)

):

    suffix = file.filename.split(".")[-1]

    with tempfile.NamedTemporaryFile(

        delete=False,

        suffix=f".{suffix}"

    ) as tmp:

        content = await file.read()

        tmp.write(content)

        path = tmp.name


    if suffix == "pdf":

        text = read_pdf(path)


    elif suffix == "docx":

        text = read_docx(path)


    elif suffix == "txt":

        with open(

            path,

            "r",

            encoding="utf-8"

        ) as f:

            text = f.read()

    else:

        raise HTTPException(

            400,

            "Unsupported file"

        )


    payload = {

        "assistant_id":

            assistant_id,

        "source_type":

            suffix,

        "title":

            file.filename,

        "content":

            text

    }


    response = requests.post(

        f"{SUPABASE_URL}/rest/v1/assistant_knowledge",

        headers={

            **HEADERS,

            "Prefer":

                "return=representation"

        },

        json=payload

    )


    return response.json()[0]