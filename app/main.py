from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routers.assistants import router as assistants_router
from app.routers.assistant_prompts import router as prompts_router
from app.routers.assistant_knowledge import router as knowledge_router
from app.routers.assistant_uploads import router as uploads_router
from app.routers.assistant_widgets import router as widgets_router
from app.routers.assistant_conversations import router as conversations_router
from app.routers.assistant_leads import router as leads_router
from app.routers.assistant_bookings import router as bookings_router
from app.routers.assistant_analytics import router as analytics_router
from app.routers.assistant_branding import router as branding_router


app = FastAPI(
    title="AI SaaS Platform",
    version="1.0"
)


app.add_middleware(

    CORSMiddleware,

    allow_origins=["*"],

    allow_credentials=True,

    allow_methods=["*"],

    allow_headers=["*"]

)


app.include_router(assistants_router)

app.include_router(prompts_router)

app.include_router(knowledge_router)

app.include_router(uploads_router)

app.include_router(widgets_router)

app.include_router(conversations_router)

app.include_router(leads_router)

app.include_router(bookings_router)

app.include_router(analytics_router)

app.include_router(branding_router)


@app.get("/")

def root():

    return {

        "status":"ok",

        "project":"AI SaaS",

        "version":"1.0"

    }