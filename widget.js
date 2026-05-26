(function () {

  // =========================
  // CONFIG
  // =========================
  const API_URL =
    "https://web-production-1de94.up.railway.app";

  const config =
    window.CHATBOT_CONFIG || {};

  const clientId =
    config.clientId;

  const color =
    config.color || "#7c3aed";

  const name =
    config.name || "AI Assistant";

  const position =
    config.position || "right";

  if (!clientId) {
    console.error(
      "❌ Brak clientId w CHATBOT_CONFIG"
    );
    return;
  }

  // =========================
  // POSITION
  // =========================
  const side =
    position === "left"
      ? "left"
      : "right";

  // =========================
  // STYLES
  // =========================
  const style =
    document.createElement("style");

  style.innerHTML = `
    #chatbot-button {
      position: fixed;
      bottom: 20px;
      ${side}: 20px;
      width: 60px;
      height: 60px;
      background: ${color};
      color: white;
      border-radius: 50%;
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      z-index: 999999;
      font-size: 24px;
      box-shadow: 0 10px 30px rgba(0,0,0,0.3);
    }

    #chatbot-box {
      position: fixed;
      bottom: 90px;
      ${side}: 20px;
      width: 340px;
      height: 520px;
      background: #111827;
      border-radius: 16px;
      overflow: hidden;
      z-index: 999999;
      display: none;
      flex-direction: column;
      box-shadow: 0 10px 30px rgba(0,0,0,0.4);
      font-family: sans-serif;
    }

    #chatbot-header {
      background: ${color};
      color: white;
      padding: 16px;
      font-weight: bold;
    }

    #chatbot-messages {
      flex: 1;
      padding: 12px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 10px;
    }

    .chatbot-message {
      padding: 10px 14px;
      border-radius: 12px;
      max-width: 80%;
      font-size: 14px;
      color: white;
      line-height: 1.5;
    }

    .chatbot-user {
      align-self: flex-end;
      background: ${color};
    }

    .chatbot-ai {
      align-self: flex-start;
      background: #1f2937;
    }

    #chatbot-input-wrap {
      display: flex;
      gap: 10px;
      padding: 12px;
      border-top: 1px solid #222;
    }

    #chatbot-input {
      flex: 1;
      border: none;
      border-radius: 10px;
      padding: 12px;
      background: #1f2937;
      color: white;
      font-size: 14px;
      outline: none;
    }

    #chatbot-send {
      border: none;
      background: ${color};
      color: white;
      padding: 0 18px;
      border-radius: 10px;
      cursor: pointer;
      font-weight: bold;
    }
  `;

  document.head.appendChild(style);

  // =========================
  // UI
  // =========================
  const button =
    document.createElement("div");

  button.id = "chatbot-button";
  button.innerHTML = "💬";

  const box =
    document.createElement("div");

  box.id = "chatbot-box";

  const header =
    document.createElement("div");

  header.id = "chatbot-header";
  header.innerText = name;

  const messages =
    document.createElement("div");

  messages.id = "chatbot-messages";

  const inputWrap =
    document.createElement("div");

  inputWrap.id =
    "chatbot-input-wrap";

  const input =
    document.createElement("input");

  input.id = "chatbot-input";
  input.placeholder =
    "Napisz wiadomość...";

  const sendBtn =
    document.createElement("button");

  sendBtn.id = "chatbot-send";
  sendBtn.innerText = "Send";

  inputWrap.appendChild(input);
  inputWrap.appendChild(sendBtn);

  box.appendChild(header);
  box.appendChild(messages);
  box.appendChild(inputWrap);

  document.body.appendChild(button);
  document.body.appendChild(box);

  // =========================
  // TOGGLE
  // =========================
  let open = false;

  button.onclick = () => {
    open = !open;

    box.style.display =
      open ? "flex" : "none";
  };

  // =========================
  // MESSAGE
  // =========================
  function addMessage(
    text,
    type
  ) {
    const el =
      document.createElement("div");

    el.className =
      "chatbot-message " +
      (type === "user"
        ? "chatbot-user"
        : "chatbot-ai");

    el.innerText = text;

    messages.appendChild(el);

    messages.scrollTop =
      messages.scrollHeight;

    return el;
  }

  // =========================
  // SEND MESSAGE
  // =========================
  async function sendMessage() {

    const text =
      input.value.trim();

    if (!text) return;

    input.value = "";

    addMessage(text, "user");

    const aiMessage =
      addMessage("...", "ai");

    try {

      const res = await fetch(
        API_URL + "/ask-public",
        {
          method: "POST",
          headers: {
            "Content-Type":
              "application/json",
          },
          body: JSON.stringify({
            question: text,
            client_id: clientId,
          }),
        }
      );

      const data =
        await res.json();

      aiMessage.innerText =
        data.answer || "Brak odpowiedzi";

    } catch (err) {

      console.error(err);

      aiMessage.innerText =
        "❌ AI Error";
    }
  }

  // =========================
  // EVENTS
  // =========================
  sendBtn.onclick =
    sendMessage;

  input.addEventListener(
    "keydown",
    (e) => {
      if (e.key === "Enter") {
        sendMessage();
      }
    }
  );

})();