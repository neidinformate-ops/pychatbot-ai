import os
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

# 🔐 API KEY
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise Exception("❌ Brak OPENAI_API_KEY w środowisku")

# 📂 LOAD DATA
with open("Dane.txt", "r", encoding="utf-8") as f:
    raw = f.read()

# =========================
# 🧠 SMART CHUNKING
# =========================
text_splitter = RecursiveCharacterTextSplitter(
    chunk_size=300,
    chunk_overlap=50
)

texts = text_splitter.split_text(raw)

# =========================
# 🔍 EMBEDDINGS
# =========================
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# =========================
# 💾 FAISS CACHE
# =========================
if os.path.exists("faiss_index"):
    db = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
else:
    db = FAISS.from_texts(texts, embeddings)
    db.save_local("faiss_index")

# =========================
# 🤖 MODEL
# =========================
llm = ChatOpenAI(model="gpt-4o-mini")

# =========================
# 🧠 BUSINESS DETECTION
# =========================
def detect_business(context):
    context = context.lower()

    if any(x in context for x in ["strzyż", "barber", "włosy"]):
        return "barber"
    if any(x in context for x in ["nocleg", "domek", "rezerwacj"]):
        return "hotel"
    if any(x in context for x in ["produkt", "cena", "kup"]):
        return "shop"

    return "general"

# =========================
# 🔁 CHAT LOOP
# =========================
while True:
    query = input("\nTy: ")

    if query.lower() in ["exit", "quit"]:
        break

    # 🔍 SEARCH (więcej kontekstu)
    docs = db.similarity_search(query, k=5)

    # 🧹 deduplikacja
    unique_docs = list(dict.fromkeys([d.page_content for d in docs]))
    context = "\n".join(unique_docs)

    print("RAG:", context[:300], "...")  # debug

    # 🔒 STRICT RAG
    if not context.strip():
        print("AI: ❌ Nie mam danych dla tego klienta.")
        continue

    # 🧠 BUSINESS MODE
    business_type = detect_business(context)

    if business_type == "barber":
        tone = "luźny, szybki, konkretny"
    elif business_type == "hotel":
        tone = "profesjonalny, informacyjny"
    elif business_type == "shop":
        tone = "sprzedażowy, zachęcający"
    else:
        tone = "neutralny"

    # =========================
    # 🧾 SUPER PROMPT
    # =========================
    prompt = f"""
Jesteś AI asystentem dla konkretnego biznesu.

STYL:
{tone}

ZASADY:
- odpowiadaj TYLKO na podstawie danych
- jeśli nie masz danych → napisz "Nie mam tej informacji"
- nie zgaduj
- odpowiadaj konkretnie
- jeśli możesz → kieruj do działania (rezerwacja / zakup / kontakt)

DANE:
{context}

PYTANIE:
{query}
"""

    # 🤖 RESPONSE
    response = llm.invoke(prompt)

    print("AI:", response.content)