from fastapi import (

    APIRouter,

    HTTPException,

    Request

)

from fastapi.responses import StreamingResponse

from app.models import PublicQuestion

from app.services.ai_service import ask_public

from app.services.rate_limit_service import (

    allow_request

)

from app.services.public_validation_service import (

    assistant_exists,

    widget_enabled

)

cache_key = (

f"search:{assistant_id}:{query}"

)

cached = get_cache(

cache_key

)

client_ip = request.client.host

if not assistant_exists(

    q.assistant_id

):

    raise HTTPException(

        status_code=404,

        detail="Assistant not found"

    )

if not widget_enabled(

    q.assistant_id

):

    raise HTTPException(

        status_code=403,

        detail="Widget disabled"

    )

if not allow_request(

    client_ip

):

    raise HTTPException(

        status_code=429,

        detail="Too many requests"

    )

router = APIRouter(

    tags=["Public Chat"]

)



@router.post("/ask-public")

async def public_chat(

    request: Request,

    q: PublicQuestion

):

    async def generate():



        async for token in ask_public(

            assistant_id=q.assistant_id,

            session_id=q.session_id,

            question=q.question

        ):



            yield (

                '{"token":"'

                + token

                + '"}\n'

            )



    return StreamingResponse(

        generate(),

        media_type="text/plain"

    )