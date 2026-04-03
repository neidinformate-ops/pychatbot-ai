print("🔥 FINAL PRO AI + RAG + SALES SYSTEM 🔥")

import os
import requests
from datetime import datetime
from fastapi import FastAPI
from pydantic import BaseModel
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

# 🔥 RAG
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 💾 FAKE DB
reservations = []

MAKE_WEBHOOK_URL = "https://hook.eu1.make.com/228u53xafjidh3etv4d1u3tzbpozjeaq"

# 📦 MODEL
class Question(BaseModel):
    question: str
    imie: Optional[str] = None
    nazwisko: Optional[str] = None
    email: Optional[str] = None
    telefon: Optional[str] = None
    numer_domku: Optional[str] = None
    sniadanie: Optional[bool] = None
    data_od: Optional[str] = None
    data_do: Optional[str] = None

# 📚 RAG SETUP
with open("Dane.txt", "r", encoding="utf-8") as f:
    text = f.read()

splitter = CharacterTextSplitter(chunk_size=300, chunk_overlap=50)
texts = splitter.split_text(text)

embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

if os.path.exists("faiss_index"):
    db = FAISS.load_local("faiss_index", embeddings, allow_dangerous_deserialization=True)
else:
    db = FAISS.from_texts(texts, embeddings)
    db.save_local("faiss_index")

# 🤖 MODEL
llm = ChatOpenAI(
    model="gpt-4o-mini",
    temperature=0.3,
    max_tokens=80
)

# 🔒 KONFLIKT
def is_conflict(new_from, new_to, domek):
    for r in reservations:
        if r["numer_domku"] != domek:
            continue

        a = datetime.strptime(r["data_od"], "%Y-%m-%d")
        b = datetime.strptime(r["data_do"], "%Y-%m-%d")
        nf = datetime.strptime(new_from, "%Y-%m-%d")
        nt = datetime.strptime(new_to, "%Y-%m-%d")

        if nf <= b and nt >= a:
            return True
    return False


# 🎯 CTA (SPRZEDAŻ)
def add_cta(answer, question):
    q = question.lower()

    if any(word in q for word in ["cena", "koszt", "oferta"]):
        return answer + " 💰 Chcesz sprawdzić dostępne terminy?"

    if any(word in q for word in ["okolica", "atrakcje", "co robić"]):
        return answer + " 🌿 To świetne miejsce na odpoczynek — chcesz zarezerwować pobyt?"

    if any(word in q for word in ["domek", "nocleg"]):
        return answer + " 🏡 Mogę pomóc w rezerwacji — podać dostępne terminy?"

    return answer


# 🧠 RAG + AI
def rag_answer(question):

    docs = db.similarity_search(question, k=3)
    context = "\n".join([d.page_content for d in docs])

    # 🟢 RAG
    if len(context.strip()) > 20:

        prompt = f"""
Odpowiedz maksymalnie w 1 krótkim zdaniu na podstawie danych.

DANE:
{context}

PYTANIE:
{question}
"""
        res = llm.invoke(prompt)
        answer = res.content.strip()[:150]

    # 🟡 fallback AI
    else:
        prompt = f"""
Odpowiedz logicznie na pytanie w jednym krótkim zdaniu.
Nie wymyślaj szczegółów jeśli nie masz pewności.

PYTANIE:
{question}
"""
        res = llm.invoke(prompt)
        answer = res.content.strip()[:150]

    # 🔥 DODAJ CTA
    return add_cta(answer, question)


@app.get("/")
def home():
    return {"status": "FINAL PRO działa 🚀"}


@app.get("/reservations")
def get_res():
    return reservations


@app.post("/ask")
async def ask(q: Question):

    print("📩", q)

    # 📅 REZERWACJA
    if q.data_od and q.data_do and q.numer_domku:

        if is_conflict(q.data_od, q.data_do, q.numer_domku):
            return {"answer": "❌ Termin zajęty"}

        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do
        })

        answer = "✅ Rezerwacja przyjęta 🎉"

    else:
        answer = rag_answer(q.question)

    # 📤 MAKE
    data = q.dict()
    data["answer"] = answer
    data["time"] = datetime.now().strftime("%Y-%m-%d %H:%M")

    try:
        requests.post(MAKE_WEBHOOK_URL, json=data, timeout=5)
    except:
        pass

    return {"answer": answer}


# 🚀 RUN
if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=int(os.environ.get("PORT", 8000)))