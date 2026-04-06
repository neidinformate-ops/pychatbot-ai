import os
from langchain_text_splitters import CharacterTextSplitter
from langchain_openai import OpenAIEmbeddings, ChatOpenAI
from langchain_community.vectorstores import FAISS

# 🔐 API KEY z ENV (BEZPIECZNIE)
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise Exception("❌ Brak OPENAI_API_KEY w środowisku")

# 📂 Wczytaj dane
with open("Dane.txt", "r", encoding="utf-8") as f:
    raw = f.read()

# 🔥 NOWY CHUNKING (NAPRAWA RAG)
chunks = []
current = ""

for line in raw.split("\n"):
    line = line.strip()
    if not line:
        continue

    if line.startswith("Pytanie:"):
        if current:
            chunks.append(current.strip())
        current = line
    else:
        current += " " + line

if current:
    chunks.append(current.strip())

print("CHUNKS:", chunks[:3])  # debug

# ✂️ Podział tekstu (zostawiamy jak było)
text_splitter = CharacterTextSplitter(
    chunk_size=200,
    chunk_overlap=20
)

texts = []
for chunk in chunks:
    texts.extend(text_splitter.split_text(chunk))

# 🧠 Embeddings
embeddings = OpenAIEmbeddings(model="text-embedding-3-small")

# 💾 FAISS cache
if os.path.exists("faiss_index"):
    print("📂 Wczytuję istniejący index FAISS...")
    db = FAISS.load_local(
        "faiss_index",
        embeddings,
        allow_dangerous_deserialization=True
    )
else:
    print("⚡ Tworzę nowy index (zużywa API)...")
    db = FAISS.from_texts(texts, embeddings)
    db.save_local("faiss_index")
    print("✅ Index zapisany!")

# 🤖 Model AI
llm = ChatOpenAI(model="gpt-4o-mini")

# 🔁 Chat loop
while True:
    query = input("\nTy: ")

    if query.lower() in ["exit", "quit"]:
        break

    # 🔍 Szukanie kontekstu
    docs = db.similarity_search(query, k=3)
    context = "\n".join([doc.page_content for doc in docs])

    print("RAG:", context)  # debug

    # 🧾 Prompt
    prompt = f"""
Odpowiadaj tylko na podstawie poniższych danych.
Jeśli nie ma odpowiedzi w danych, napisz: "Nie wiem".

DANE:
{context}

PYTANIE:
{query}
"""

    # 💬 Odpowiedź
    response = llm.invoke(prompt)

    print("AI:", response.content)