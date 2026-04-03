# =========================
# 🧠 INTENT (ULEPSZONY)
# =========================
def detect_intent(question):
    q = normalize(question)

    intents = {
        "cena": ["cena", "koszt"],
        "sniadanie": ["sniadanie"],
        "termin": ["termin", "dostep", "wolne"],
        "zwierzeta": ["pies", "zwierze"],
        "parking": ["parking"],
        "wyposazenie": ["wifi", "tv", "klimatyzacja", "jacuzzi", "kuchnia"],
        "atrakcje": ["atrakcje", "co robic", "okolica"],
        "ilosc_osob": ["ile osob", "ile osób", "ilosc osob"]
    }

    detected = []

    for intent, words in intents.items():
        for w in words:
            if w in q:
                detected.append(intent)
                break

    return detected


# =========================
# 🧠 KONKRETNE ODPOWIEDZI (NOWE 🔥)
# =========================
def handle_specific(question):

    q = normalize(question)

    # 🔥 ILE OSÓB + NUMER DOMKU
    if "ile osob" in q or "ile osob" in q:

        if "1" in q:
            return "Domek 1 jest dla 2–4 osób"

        if "2" in q:
            return "Domek 2 jest dla 4–6 osób"

        if "3" in q:
            return "Domek 3 jest dla 2–6 osób"

        return "Domki są dla 2 do 6 osób w zależności od wybranego"

    # 🔥 KONKRET: CENA DOMKU
    if "domek" in q and ("cena" in q or "koszt" in q):
        if "1" in q:
            return "Domek 1 kosztuje 300 zł za noc"
        if "2" in q:
            return "Domek 2 kosztuje 350 zł za noc"
        if "3" in q:
            return "Domek 3 kosztuje 400 zł za noc"

    return None


# =========================
# 🧠 INTENT HANDLER
# =========================
def handle_intent(intents):

    if "cena" in intents:
        return "Domek 1: 300 zł, Domek 2: 350 zł, Domek 3: 400 zł"

    if "sniadanie" in intents:
        return "Śniadanie kosztuje 30 zł za osobę"

    if "zwierzeta" in intents:
        return "Tak, zwierzęta są dozwolone po uzgodnieniu"

    if "parking" in intents:
        return "Parking jest darmowy dla gości"

    if "wyposazenie" in intents:
        return "Domki mają wifi, tv i kuchnię, a domek 3 dodatkowo jacuzzi"

    if "atrakcje" in intents:
        return "W okolicy są rowery, kajaki, spacery i natura"

    if "termin" in intents:
        return "Kliknij 📅 Rezerwacja aby sprawdzić dostępność"

    if "ilosc_osob" in intents:
        return "Domki są dla 2–6 osób w zależności od wybranego"

    return None


# =========================
# 🧠 LOGIKA (POPRAWIONA KOLEJNOŚĆ 🔥)
# =========================
def get_smart_answer(q: Question):

    text = q.question.lower()

    # 🔥 1. KONKRET
    specific = handle_specific(q.question)
    if specific:
        return specific

    # 🧠 2. INTENT
    intents = detect_intent(q.question)
    intent_answer = handle_intent(intents)
    if intent_answer:
        return intent_answer

    # 🔴 BLOKADA
    if "blokada" in text:
        if q.data_od and q.data_do and q.numer_domku:
            reservations.append({
                "numer_domku": q.numer_domku,
                "data_od": q.data_od,
                "data_do": q.data_do,
                "imie": "ADMIN",
                "nazwisko": "",
                "telefon": "",
                "email": ""
            })
            save_db(reservations)
            return "🔴 Termin zablokowany"

    # 📅 REZERWACJA
    if q.data_od and q.data_do and q.numer_domku:

        if q.data_od > q.data_do:
            return "❌ Błędny zakres dat"

        if is_date_conflict(q.data_od, q.data_do, q.numer_domku):
            return "❌ Niestety, ale termin zajęty."

        reservations.append({
            "numer_domku": q.numer_domku,
            "data_od": q.data_od,
            "data_do": q.data_do,
            "imie": q.imie,
            "nazwisko": q.nazwisko,
            "telefon": q.telefon,
            "email": q.email
        })

        save_db(reservations)

        return "✅ Rezerwacja przyjęta!"

    # 🔍 RAG
    rag = rag_search(q.question)
    if rag:
        return rag

    # 🤖 AI
    ai = ai_answer(q.question)
    if ai:
        return ai

    return "Mogę pomóc w rezerwacji lub odpowiedzieć na pytania 🙂"