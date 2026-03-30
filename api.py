import os
from fastapi import FastAPI
from pydantic import BaseModel

from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

app = FastAPI()

# 📩 Model danych
class Question(BaseModel):
    question: str

# 🔐 API KEY (z Railway / ENV)
api_key = os.getenv("OPENAI_API_KEY")

# 👉 NIE crashujemy aplikacji!
if not api_key:
    print("❌ Brak OPENAI_API_KEY - API działa w trybie testowym")

# 📂 Wczytaj dane
try:
    with open("Dane.txt", "r", encoding="utf-8") as f:
        text = f.read()
except:
    text = "Brak danych"

# ✂️ Podział tekstu
text_splitter = CharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20
)
texts = text_splitter.split_text(text)

# 🧠 Embeddings (tylko jeśli mamy API)
if api_key:
    embeddings = OpenAIEmbeddings(model="text-embedding-3-small")
else:
    embeddings = None

# 💾 FAISS (bez crashowania)
if embeddings and os.path.exists("faiss_index"):
    print("📂 Wczytuję FAISS...")
    db = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
elif embeddings:
    print("⚡ Tworzę FAISS (może zużyć API)...")
    db = FAISS.from_texts(texts, embeddings)
    db.save_local("faiss_index")
else:
    db = None

# 🤖 Model AI
if api_key:
    llm = ChatOpenAI(model="gpt-4o-mini")
else:
    llm = None

# 🏠 TEST endpoint
@app.get("/")
def home():
    return {"message": "API działa 🚀"}

# 🔥 GŁÓWNY endpoint
@app.post("/ask")
async def ask_ai(q: Question):

    # 👉 TRYB TESTOWY (bez AI)
    if not llm:
        return {"answer": f"Test dziala: {q.question}"}

    # 👉 TRYB BEZ RAG
    if not db:
        response = llm.invoke(q.question)
        return {"answer": response.content}

    # 👉 TRYB RAG
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