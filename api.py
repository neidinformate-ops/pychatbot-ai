import os
import json
from datetime import datetime
import logging
import requests
import time

from fastapi import FastAPI, Header, Depends, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr, validator
from typing import Optional

from openai import OpenAI
import faiss
import numpy as np

from auth import create_user, verify_password, create_token, get_user, get_current_user

client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
app = FastAPI()

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("webhook")

# =========================
# 🧠 RAG (FAISS)
# =========================
RAG_STORE = {}
def load_rag_for_client(client_id):
    global RAG_STORE

    if client_id in RAG_STORE:
        return  # ✅ cache w RAM

    try:
        index_file = f"rag_{client_id}.index"
        data_file = f"rag_{client_id}.json"
        txt_file = f"Dane_{client_id}.txt"

        # 🔁 load z dysku (FAST)
        if os.path.exists(index_file) and os.path.exists(data_file):
            index = faiss.read_index(index_file)

            with open(data_file, "r", encoding="utf-8") as f:
                data = json.load(f)

            RAG_STORE[client_id] = {
                "index": index,
                "data": data
            }
            logger.info(f"RAG loaded from disk: {client_id}")
            return

        # 📄 fallback → build (TYLKO RAZ)
        if not os.path.exists(txt_file):
            txt_file = "Dane.txt"

        with open(txt_file, "r", encoding="utf-8") as f:
            chunks = [c.strip() for c in f.read().split("\n") if c.strip()]

        embeddings = []
        for c in chunks:
            emb = client.embeddings.create(
                model="text-embedding-3-small",
                input=c
            )
            embeddings.append(emb.data[0].embedding)

        if not embeddings:
            return

        dim = len(embeddings[0])
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(embeddings).astype("float32"))

        RAG_STORE[client_id] = {
            "index": index,
            "data": chunks
        }

        # 💾 zapis
        faiss.write_index(index, index_file)

        with open(data_file, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        logger.info(f"RAG built: {client_id}")

    except Exception as e:
        logger.error(f"RAG error ({client_id}): {e}")
RAG_INDEX_FILE = "rag.index"
RAG_DATA_FILE = "rag_data.json"



            # 📄 fallback
            if not os.path.exists(txt_file):
                txt_file = "Dane.txt"

            with open(txt_file, "r", encoding="utf-8") as f:
                chunks = [c.strip() for c in f.read().split("\n") if c.strip()]

            embeddings = []
            for c in chunks:
                emb = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=c
                )
                embeddings.append(emb.data[0].embedding)

            if not embeddings:
                return

            dim = len(embeddings[0])
            index = faiss.IndexFlatL2(dim)
            index.add(np.array(embeddings).astype("float32"))

            RAG_STORE[client_id] = {
                "index": index,
                "data": chunks
            }

            # 💾 zapis
            faiss.write_index(index, index_file)

            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"RAG client load error: {e}")
    try:
        # 🔁 próbuj wczytać cache
        if os.path.exists(RAG_INDEX_FILE) and os.path.exists(RAG_DATA_FILE):
            RAG_INDEX = faiss.read_index(RAG_INDEX_FILE)

            with open(RAG_DATA_FILE, "r", encoding="utf-8") as f:
                RAG_DATA = json.load(f)

            print("RAG loaded from cache:", len(RAG_DATA))
            return

        # 📄 fallback → buduj index
        file_name = "Dane.txt"

        with open(file_name, "r", encoding="utf-8") as f:
            chunks = [c.strip() for c in f.read().split("\n") if c.strip()]

        embeddings = []
        for c in chunks:
            emb = client.embeddings.create(
                model="text-embedding-3-small",
                input=c
            )
            embeddings.append(emb.data[0].embedding)

        if not embeddings:
            return

        dim = len(embeddings[0])
        index = faiss.IndexFlatL2(dim)
        index.add(np.array(embeddings).astype("float32"))

        RAG_DATA = chunks
        RAG_INDEX = index

        # 💾 zapis cache
        faiss.write_index(index, RAG_INDEX_FILE)

        with open(RAG_DATA_FILE, "w", encoding="utf-8") as f:
            json.dump(chunks, f, ensure_ascii=False, indent=2)

        print("RAG built and saved:", len(RAG_DATA))

    except Exception as e:
        print("RAG load error:", e)

def search_rag(query, client_id, k=3, threshold=0.8):
    if client_id not in RAG_STORE:
        return []

    index = RAG_STORE[client_id]["index"]
    data = RAG_STORE[client_id]["data"]

    try:
        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
    except Exception as e:
        logger.error(f"Embedding error: {e}")
        return []

    q_vec = np.array([emb.data[0].embedding]).astype("float32")

    D, I = index.search(q_vec, k)

    results = []
    for dist, idx in zip(D[0], I[0]):
        if idx < len(data) and dist < threshold:
            results.append(data[idx])

                            return results

            # 📄 fallback
            if not os.path.exists(txt_file):
                txt_file = "Dane.txt"

            with open(txt_file, "r", encoding="utf-8") as f:
                chunks = [c.strip() for c in f.read().split("\n") if c.strip()]

            embeddings = []
            for c in chunks:
                emb = client.embeddings.create(
                    model="text-embedding-3-small",
                    input=c
                )
                embeddings.append(emb.data[0].embedding)

            if not embeddings:
                return

            dim = len(embeddings[0])
            index = faiss.IndexFlatL2(dim)
            index.add(np.array(embeddings).astype("float32"))

            RAG_DATA = chunks
            RAG_INDEX = index

            # 💾 zapis
            faiss.write_index(index, index_file)

            with open(data_file, "w", encoding="utf-8") as f:
                json.dump(chunks, f, ensure_ascii=False, indent=2)

        except Exception as e:
            logger.error(f"RAG client load error: {e}")
    try:
        emb = client.embeddings.create(
            model="text-embedding-3-small",
            input=query
        )
    except Exception as e:
        print("Embedding error:", e)
        return []

    q_vec = np.array([emb.data[0].embedding]).astype("float32")
D, I = index.search(q_vec, k)

    results = []
    for dist, idx in zip(D[0], I[0]):
        if idx < len(data) and dist < threshold:
            results.append(data[idx])
              return results

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# =========================
# 💾 DB
# =========================
def load_db():
    try:
        with open("db.json", "r") as f:
            data = json.load(f)
            if isinstance(data, dict):
                return data
            return {}  # migracja ze starego formatu
    except:
        return {}

def save_db(data):
    with open("db.json", "w") as f:
        json.dump(data, f, indent=2)

def get_user_reservations(client_id):
    data = load_db()
    return data.get(client_id, [])

# =========================
# 🧠 MEMORY
# =========================
class MemoryStore:
    def __init__(self):
        self.store = {}

    def get(self, key: str):
        return self.store.get(key)

    def set(self, key: str, value: dict):
        self.store[key] = value

    def clear(self, key: str):
        if key in self.store:
            del self.store[key]


class MemoryService:
    def __init__(self, store: MemoryStore):
        self.store = store

    def get_memory(self, key: str):
        return self.store.get(key) or {}

    def update_memory(self, key: str, patch: dict):
        current = self.get_memory(key)
        current.update(patch)
        self.store.set(key, current)
        return current

    def set(self, key: str, value: dict):
        self.store.set(key, value)

    def clear(self, key: str):
        self.store.clear(key)


memory_service = MemoryService(MemoryStore())
# =========================
# 🚦 RATE LIMIT
# =========================
rate_limit_store = {}
RATE_LIMIT = 10  # requestów
RATE_WINDOW = 10  # sekund
# =========================
# 🔐 AUTH (JWT - auth.py)
# =========================


class LoginData(BaseModel):
    email: str
    password: str


class RegisterData(BaseModel):
    class ClientSetupData(BaseModel):
        text: str
    email: str
    password: str

@app.post("/login")
def login(data: LoginData):
    logger.info(f"Login attempt: {data.email}")
    user = get_user(data.email)

    if not user or not verify_password(data.password, user["password"]):
        logger.warning(f"Login failed: {data.email}")
        raise HTTPException(status_code=401, detail="invalid_credentials")

    logger.info(f"Login success: {data.email}")
    token = create_token(user["id"])
    return {"token": token}

@app.post("/register")
def register(data: RegisterData):
    try:
        user = create_user(data.email, data.password)
        return {"ok": True, "user": user["email"]}
    except ValueError:
        raise HTTPException(status_code=400, detail="user_exists")
def get_client_id(user):
    return user["id"]  # email jako client_id
@app.post("/client/setup")
def client_setup(data: ClientSetupData, user=Depends(get_current_user)):
    client_id = get_client_id(user)

    file_name = f"Dane_{client_id}.txt"

    try:
        # 💾 zapis danych klienta
        with open(file_name, "w", encoding="utf-8") as f:
            f.write(data.text.strip())

        logger.info(f"Client data saved: {client_id}")

        # 🔥 reset RAG cache (RAM)
        if client_id in RAG_STORE:
            del RAG_STORE[client_id]

        # 🧹 usuń stare pliki indexu (opcjonalnie, ale ważne)
        index_file = f"rag_{client_id}.index"
        data_file = f"rag_{client_id}.json"

        if os.path.exists(index_file):
            os.remove(index_file)

        if os.path.exists(data_file):
            os.remove(data_file)

        logger.info(f"RAG reset for client: {client_id}")

        return {"ok": True, "message": "Dane zapisane i RAG zresetowany"}

    except Exception as e:
        logger.error(f"Client setup error: {e}")
        raise HTTPException(status_code=500, detail="setup_failed")
# =========================
# 📦 MODEL
# =========================
class Question(BaseModel):
    question: str
    imie: Optional[str] = None
    nazwisko: Optional[str] = None
    telefon: Optional[str] = None
    email: Optional[EmailStr] = None
    numer_domku: Optional[str] = None
    data_od: Optional[str] = None
    data_do: Optional[str] = None
    session_id: Optional[str] = "default"

    @validator("text")
    def validate_length(cls, v):
        if len(v) > 50000:
            raise ValueError("tekst za długi")
        return v
    @validator("telefon")
    def validate_phone(cls, v):
        if v and len(v) < 7:
            raise ValueError("telefon za krótki")
        return v

    @validator("data_do")
    def validate_dates(cls, v, values):
        data_od = values.get("data_od")
        if v and data_od:
            try:
                d1 = datetime.fromisoformat(data_od)
                d2 = datetime.fromisoformat(v)
                if d1 >= d2:
                    raise ValueError("data_od musi być wcześniejsza niż data_do")
            except Exception:
                raise ValueError("niepoprawny format daty")
        return v
# =========================
# 🔥 KONFLIKT
# =========================
def is_conflict(f, t, domek, client_id=None):
    data = load_db()
    user_reservations = data.get(client_id, [])

    for r in user_reservations:
        # client_id już jest filtrowany na poziomie DB (data.get(client_id))
        if r["numer_domku"] != domek:
            continue
        if f <= r["data_do"] and t >= r["data_od"]:
            return True
    return False
def check_rate_limit(session_id: str):
    now = time.time()

    if session_id not in rate_limit_store:
        rate_limit_store[session_id] = []

    # usuń stare requesty
    rate_limit_store[session_id] = [
        t for t in rate_limit_store[session_id]
        if now - t < RATE_WINDOW
    ]

    if len(rate_limit_store[session_id]) >= RATE_LIMIT:
        return False

    rate_limit_store[session_id].append(now)
    return True
def normalize(text):
    text = text.lower()
    replacements = {
        "ś": "s","ą": "a","ę": "e","ć": "c",
        "ł": "l","ó": "o","ż": "z","ź": "z"
    }
    for k, v in replacements.items():
        text = text.replace(k, v)
    return text

# =========================
# 🚀 ULTRA FAST (90% odpowiedzi)
# =========================
def ultra_fast_answer(q):
    q = normalize(q)

    if "magnolia" in q:
        return "Pokój Magnolia: 160 zł / noc (max 3 osoby)"
    if "konwalia" in q:
        return "Pokój Konwalia: 130 zł / noc (2 osoby)"
    if "lawenda" in q:
        return "Pokój Lawenda: 240 zł / noc (3 osoby)"
    if "roza" in q:
        return "Pokój Róża: 110 zł / noc (2 osoby)"
    if "piwonia" in q:
        return "Pokój Piwonia: 130 zł / noc (2 osoby)"

    if "kajak" in q:
        return "Kajaki: 90 zł (1 os), 120 zł (2 os)"

    if "basen" in q:
        return "Tak, basen jest dostępny dla gości"

    if "grill" in q or "ognisko" in q:
        return "Tak, dostępny grill i ognisko"

    if "pies" in q or "kot" in q or "zwierze" in q:
        return "Tak 🙂 Psy i koty są dozwolone (20 zł, max 2)"

    if "rzeka" in q or "warta" in q:
        return "Rzeka Warta znajduje się bardzo blisko obiektu"

    if "gdzie" in q or "adres" in q:
        return "Załęcze Małe 30, Pątnów"

    if "atrakcje" in q or "co mozna" in q:
        return "Kajaki, basen, grill, ognisko, rowery i natura"

    return None

# =========================
# 🧠 INTENT
# =========================
def detect_intent(q):
    q = normalize(q)

    if "rezerw" in q:
        return "rezerwacja"
    if "cena" in q or "ile" in q:
        return "cena"
    if "sniadanie" in q:
        return "sniadanie"
    if "zwierze" in q or "pies" in q or "kot" in q:
        return "zwierzeta"

    return None

def handle_intent(intent):
    answers = {
        "cena": "Domek 1: 300 zł, Domek 2: 350 zł, Domek 3: 400 zł",
        "sniadanie": "Śniadanie: 30 zł / osoba",
        "zwierzeta": "Tak 🙂 Zwierzęta dozwolone (20 zł)"
    }
    return answers.get(intent)

# =========================
# 🧠 MEMORY UPDATE
# =========================
def update_memory(q: Question, client_id: str):
    sid = q.session_id or "default"
    key = f"{client_id}:{sid}"

    mem = memory_service.get_memory(key)
    text = normalize(q.question)

    if "domek 1" in text:
        mem["domek"] = "1"
    if "domek 2" in text:
        mem["domek"] = "2"
    if "domek 3" in text:
        mem["domek"] = "3"

    if "2 osob" in text:
        mem["osoby"] = 2
    if "3 osob" in text:
        mem["osoby"] = 3

    if "sniadanie" in text:
        mem["sniadanie"] = True

    if "rezerw" in text:
        mem["intent"] = "rezerwacja"

    if "zmien temat" in text:
        memory_service.clear(key)
        return {}

    memory_service.set(key, mem)
    return mem

# =========================
# 🤖 AI (fallback tylko)
# =========================
def ai_answer(question, mem=None):
    try:
        if not os.getenv("OPENAI_API_KEY"):
            return None

        context = f"Kontekst: {mem}" if mem else ""

        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                {"role": "system", "content": "Odpowiadaj krótko i konkretnie."},
                {"role": "user", "content": context + " " + question}
            ],
            max_tokens=60
        )

        return response.choices[0].message.content.strip()

    except:
        return None

# =========================
# 🤖 LOGIKA GŁÓWNA
# =========================

def handle(q: Question, user=None):
    logger.info(f"/ask request: session={q.session_id} question={q.question}")

    # 🚦 rate limit
    if not check_rate_limit(q.session_id):
        logger.warning(f"Rate limit exceeded: session={q.session_id}")
        return "⛔ Za dużo zapytań, spróbuj za chwilę"

    text = q.question
    client_id = get_client_id(user) if user else "default"
    mem = update_memory(q, client_id)

    # ⚡ szybkie odpowiedzi
    fast = ultra_fast_answer(text)
    if fast:
        return fast

    # 📅 rezerwacja


    WEBHOOK_URL = "https://hook.eu1.make.com/228u53xafjidh3etv4d1u3tzbpozjeaq"  # np discord / make / zapier

    def send_webhook(data, retries=3, timeout=5):
        payload = {
            "event": "reservation_created",
            "timestamp": datetime.utcnow().isoformat(),
            "data": data
        }

        for attempt in range(retries):
            try:
                response = requests.post(
                    WEBHOOK_URL,
                    json=payload,
                    timeout=timeout
                )

                if response.status_code < 300:
                    logger.info("Webhook success")
                    return True

                logger.warning(f"Webhook failed (status {response.status_code}) attempt {attempt + 1}")

            except requests.exceptions.Timeout:
                logger.warning(f"Webhook timeout attempt {attempt + 1}")

            except Exception as e:
                logger.error(f"Webhook error: {str(e)} attempt {attempt + 1}")

            time.sleep(1)

        logger.error("Webhook failed after retries")
        return False

    if q.data_od and q.data_do:
        logger.info(f"Reservation attempt: domek={q.numer_domku}, od={q.data_od}, do={q.data_do}")
        if not q.numer_domku:
            return "❌ Wybierz numer domku"
        client_id = get_client_id(user) if user else "default"

        if is_conflict(q.data_od, q.data_do, q.numer_domku, client_id):
            logger.warning(f"Reservation conflict: domek={q.numer_domku}, od={q.data_od}, do={q.data_do}")
            return "❌ Termin zajęty"

        client_id = get_client_id(user) if user else "default"

        data = load_db()
        user_reservations = data.get(client_id, [])

        user_reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "imie": q.imie,
            "telefon": q.telefon,
            "email": q.email
        })

        data[client_id] = user_reservations
        save_db(data)
        logger.info(f"Reservation saved: domek={q.numer_domku}, telefon={q.telefon}")

        send_webhook({
            "type": "reservation",
            "reservation": {
                "house_id": q.numer_domku,
                "date_from": q.data_od,
                "date_to": q.data_do
            },
            "customer": {
                "name": q.imie,
                "phone": q.telefon,
                "email": q.email
            }
        })

        return "✅ Rezerwacja przyjęta"

    # 🧠 intent
    intent = detect_intent(text)
    if intent:
        ans = handle_intent(intent)
        if ans:
            return ans

    # 🧠 flow rezerwacji
    if mem.get("intent") == "rezerwacja":

        domek = mem.get("domek")
        osoby = mem.get("osoby")
        sniadanie = mem.get("sniadanie")

        if domek and osoby:
            return f"Domek {domek} dla {osoby} osób{' ze śniadaniem' if sniadanie else ''}. Wybierz daty 📅"

        if domek:
            return f"Domek {domek} — dla ilu osób?"

        return "Który domek chcesz zarezerwować?"

    # 🧠 RAG
    client_id = get_client_id(user) if user else "default"
    load_rag_for_client(client_id)

    rag_results = search_rag(text, client_id)

    if rag_results:
        context = " ".join(rag_results)

        rag_prompt = f"""
        Jesteś pomocnym asystentem obsługi obiektu noclegowego.

        Odpowiadaj naturalnie, krótko i konkretnie.

        Wykorzystaj poniższe dane jako główne źródło informacji, ale:
        - jeśli dane są niepełne, spróbuj odpowiedzieć częściowo
        - nie używaj sformułowania "brak informacji"
        - jeśli czegoś nie ma w danych, możesz delikatnie zasugerować kontakt lub doprecyzowanie

        KONTEKST UŻYTKOWNIKA:
        {mem}

        DANE:
        {context}

        PYTANIE:
        {text}
        """

        rag_response = ai_answer(rag_prompt, mem)
        if rag_response and "brak informacji" not in rag_response.lower():
            return rag_response

    # 🤖 AI fallback
    ai = ai_answer(text, mem)
    if ai:
        logger.info("AI fallback used")
        return ai

    return "Mogę pomóc w rezerwacji lub odpowiedzieć na pytania 🙂"

# =========================
# 🚀 API
# =========================
@app.post("/ask")
async def ask(q: Question, user=Depends(get_current_user)):
    return {"answer": handle(q, user)}

@app.get("/availability")
def availability(user=Depends(get_current_user)):
    client_id = get_client_id(user) if user else "default"
    return get_user_reservations(client_id)

@app.delete("/reservation")
def delete(data: dict, user=Depends(get_current_user)):
    client_id = get_client_id(user) if user else "default"

    db = load_db()
    user_reservations = db.get(client_id, [])

    user_reservations = [
        r for r in user_reservations
        if r.get("telefon") != data.get("telefon")
    ]

    db[client_id] = user_reservations
    save_db(db)

    return {"ok": True}
@app.delete("/unblock")
def unblock(data: dict, user=Depends(get_current_user)):
    client_id = get_client_id(user) if user else "default"

    db = load_db()
    user_reservations = db.get(client_id, [])

    user_reservations = [
        r for r in user_reservations
        if not (
            r.get("numer_domku") == data.get("numer_domku") and
            r.get("data_od") == data.get("data_od")
        )
    ]

    db[client_id] = user_reservations
    save_db(db)

    return {"ok": True}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api:app", host="0.0.0.0", port=8000)