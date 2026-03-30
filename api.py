import os
from fastapi import FastAPI
from pydantic import BaseModel

from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

app = FastAPI()

class Question(BaseModel):
    question: str

# 🔐 API KEY
api_key = os.getenv("OPENAI_API_KEY")

# 📂 dane
try:
    with open("Dane.txt", "r", encoding="utf-8") as f:
        text = f.read()
except:
    text = "Brak danych"

text_splitter = CharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20
)
texts = text_splitter.split_text(text)

# 🧠 embeddings tylko jeśli masz API
if api_key:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
else:
    embeddings = None

# ❗ KLUCZOWE: NIE TWORZYMY FAISS NA RAILWAY
if embeddings and os.path.exists("faiss_index"):
    db = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
else:
    db = None

# 🤖 model
if api_key:
    llm = ChatOpenAI(model="gpt-4o-mini")
else:
    llm = None

@app.get("/")
def home():
    return {"message": "API działa 🚀"}

@app.post("/ask")
async def ask_ai(q: Question):

    # 🔹 brak AI → test
    if not llm:
        return {"answer": f"Test dziala: {q.question}"}

    # 🔹 brak RAG → zwykły AI
    if not db:
        response = llm.invoke(q.question)
        return {"answer": response.content}

    # 🔹 RAG
    docs = db.similarity_search(q.question, k=3)
    context = "\n".join([doc.page_content for doc in docs])

    prompt = f"""
Odpowiadaj tylko na podstawie poniższych danych.
Jeśli nie ma odpowiedzi w danych, napisz: "Nie wiem".

DANE:
{context}

PYTANIE:
{q.question}
"""

    response = llm.invoke(prompt)

    return {"answer": response.content}