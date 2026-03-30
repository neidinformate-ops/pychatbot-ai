import os
from openai import OpenAI

# 🔐 API KEY z ENV (bezpiecznie)
api_key = os.getenv("OPENAI_API_KEY")

if not api_key:
    raise Exception("❌ Brak OPENAI_API_KEY w środowisku")

client = OpenAI()

def chat():
    print("Chatbot AI (napisz 'exit' żeby wyjść)\n")

    messages = [
        {"role": "system", "content": "Jesteś pomocnym asystentem."}
    ]

    while True:
        user_input = input("Ty: ")

        if user_input.lower() == "exit":
            break

        messages.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model="gpt-4o-mini",
                messages=messages
            )

            reply = response.choices[0].message.content

        except Exception as e:
            print("❌ Błąd:", e)
            continue

        print("AI:", reply)

        messages.append({"role": "assistant", "content": reply})

if __name__ == "__main__":
    chat()


