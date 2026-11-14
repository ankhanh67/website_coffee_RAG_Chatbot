"""Modern Single-Page Web Chat UI served at GET /."""

from fastapi import APIRouter
from fastapi.responses import HTMLResponse

router = APIRouter(tags=["ui"])

CHAT_UI_HTML = """<!DOCTYPE html>
<html lang="vi">
<head>
  <meta charset="UTF-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1.0" />
  <title>Highlands Coffee — AI Assistant</title>
  <style>
    :root {
      --brand: #8b1e24;
      --brand-dark: #661419;
      --bg: #f6f3ee;
      --card: #ffffff;
      --text: #221f1d;
      --muted: #6e6761;
      --border: #e5ded5;
      --user-bubble: #8b1e24;
      --bot-bubble: #f1ebe3;
    }
    * { box-sizing: border-box; margin: 0; padding: 0; }
    body {
      font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, sans-serif;
      background: var(--bg);
      color: var(--text);
      height: 100vh;
      display: flex;
      flex-direction: column;
    }
    header {
      background: var(--brand);
      color: #fff;
      padding: 14px 20px;
      display: flex;
      align-items: center;
      justify-content: space-between;
      box-shadow: 0 2px 8px rgba(0, 0, 0, 0.12);
    }
    .brand-title {
      display: flex;
      align-items: center;
      gap: 10px;
      font-weight: 700;
      font-size: 1.05rem;
    }
    .session-controls {
      display: flex;
      align-items: center;
      gap: 8px;
      font-size: 0.82rem;
    }
    .session-badge {
      background: rgba(255, 255, 255, 0.16);
      padding: 4px 10px;
      border-radius: 999px;
      font-family: monospace;
    }
    .btn-reset {
      background: #fff;
      color: var(--brand);
      border: none;
      padding: 5px 11px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      font-size: 0.8rem;
    }
    .btn-reset:hover { opacity: 0.92; }
    main {
      flex: 1;
      max-width: 820px;
      width: 100%;
      margin: 0 auto;
      display: flex;
      flex-direction: column;
      padding: 16px;
      overflow: hidden;
    }
    #chat-box {
      flex: 1;
      background: var(--card);
      border: 1px solid var(--border);
      border-radius: 14px;
      padding: 18px;
      overflow-y: auto;
      display: flex;
      flex-direction: column;
      gap: 14px;
      box-shadow: 0 4px 16px rgba(0, 0, 0, 0.04);
    }
    .msg {
      max-width: 80%;
      padding: 11px 15px;
      border-radius: 14px;
      line-height: 1.5;
      font-size: 0.94rem;
      white-space: pre-wrap;
      word-wrap: break-word;
    }
    .msg.user {
      align-self: flex-end;
      background: var(--user-bubble);
      color: #fff;
      border-bottom-right-radius: 4px;
    }
    .msg.bot {
      align-self: flex-start;
      background: var(--bot-bubble);
      color: var(--text);
      border-bottom-left-radius: 4px;
    }
    .msg-meta {
      display: flex;
      align-items: center;
      gap: 6px;
      margin-bottom: 5px;
      font-size: 0.72rem;
      font-weight: 700;
      text-transform: uppercase;
      color: var(--brand);
    }
    .badge-action {
      background: rgba(139, 30, 36, 0.12);
      color: var(--brand);
      padding: 2px 7px;
      border-radius: 4px;
    }
    .suggestions {
      display: flex;
      flex-wrap: wrap;
      gap: 8px;
      margin-top: 10px;
    }
    .chip {
      background: #fff;
      border: 1px solid var(--border);
      color: var(--text);
      padding: 6px 11px;
      border-radius: 999px;
      font-size: 0.8rem;
      cursor: pointer;
      transition: all 0.15s;
    }
    .chip:hover {
      border-color: var(--brand);
      color: var(--brand);
    }
    .composer {
      display: flex;
      gap: 10px;
      margin-top: 12px;
    }
    .composer input {
      flex: 1;
      padding: 13px 16px;
      border: 1px solid var(--border);
      border-radius: 10px;
      font-size: 0.95rem;
      outline: none;
    }
    .composer input:focus {
      border-color: var(--brand);
    }
    .composer button {
      background: var(--brand);
      color: #fff;
      border: none;
      padding: 0 22px;
      border-radius: 10px;
      font-weight: 600;
      font-size: 0.95rem;
      cursor: pointer;
    }
    .composer button:disabled {
      opacity: 0.55;
      cursor: not-allowed;
    }
  </style>
</head>
<body>
  <header>
    <div class="brand-title">
      <span>☕ Highlands Coffee — Trợ lý AI Đa Tác Tử</span>
    </div>
    <div class="session-controls">
      <span id="session-label" class="session-badge"></span>
      <button class="btn-reset" onclick="resetSession()">Phiên mới</button>
    </div>
  </header>

  <main>
    <div id="chat-box"></div>

    <div class="suggestions">
      <button class="chip" onclick="sendQuick('Quán có đồ uống nào không có caffeine và thuần chay?')">🌱 Đồ uống không caffeine & thuần chay</button>
      <button class="chip" onclick="sendQuick('Ở Hà Nội chi nhánh nào có chỗ đỗ ô tô và mấy giờ mở cửa?')">🚗 Chi nhánh Hà Nội đỗ ô tô</button>
      <button class="chip" onclick="sendQuick('Cho mình 2 ly Trà Đào Cam Sả size L và 1 bánh Tiramisu')">🛒 Đặt 2 Trà Đào Cam Sả L + 1 Tiramisu</button>
      <button class="chip" onclick="sendQuick('Đúng rồi, chốt đơn nhé')">✅ Xác nhận chốt đơn</button>
    </div>

    <form class="composer" onsubmit="handleSubmit(event)">
      <input id="msg-input" type="text" placeholder="Nhập câu hỏi tư vấn, chính sách quán hoặc đặt món..." autocomplete="off" />
      <button id="send-btn" type="submit">Gửi</button>
    </form>
  </main>

  <script>
    let sessionId = localStorage.getItem("coffee_session_id") || makeSessionId();
    const chatBox = document.getElementById("chat-box");
    const msgInput = document.getElementById("msg-input");
    const sendBtn = document.getElementById("send-btn");
    const sessionLabel = document.getElementById("session-label");

    function makeSessionId() {
      const id = "sess-" + Math.random().toString(36).substring(2, 8);
      localStorage.setItem("coffee_session_id", id);
      return id;
    }

    function updateSessionBadge() {
      sessionLabel.textContent = "Session: " + sessionId;
    }

    function appendMessage(role, text, action) {
      const div = document.createElement("div");
      div.className = "msg " + role;
      if (role === "bot" && action) {
        const meta = document.createElement("div");
        meta.className = "msg-meta";
        meta.innerHTML = `<span class="badge-action">${action}</span>`;
        div.appendChild(meta);
      }
      const body = document.createElement("div");
      body.textContent = text;
      div.appendChild(body);
      chatBox.appendChild(div);
      chatBox.scrollTop = chatBox.scrollHeight;
    }

    function resetSession() {
      sessionId = makeSessionId();
      updateSessionBadge();
      chatBox.innerHTML = "";
      appendMessage(
        "bot",
        "Xin chào! Mình là trợ lý ảo Highlands Coffee. Mình có thể tư vấn thực đơn, giải đáp thông tin chi nhánh/khuyến mãi hoặc nhận đặt món giúp bạn ạ!",
        "system"
      );
    }

    function sendQuick(text) {
      msgInput.value = text;
      msgInput.focus();
      sendMessage(text);
    }

    async function handleSubmit(e) {
      e.preventDefault();
      const text = msgInput.value.trim();
      if (!text) return;
      await sendMessage(text);
    }

    async function sendMessage(text) {
      msgInput.value = "";
      appendMessage("user", text);
      sendBtn.disabled = true;
      sendBtn.textContent = "Đang xử lý...";

      try {
        const res = await fetch("/api/v1/chat", {
          method: "POST",
          headers: { "Content-Type": "application/json" },
          body: JSON.stringify({ session_id: sessionId, message: text })
        });
        const data = await res.json();
        if (!res.ok) {
          appendMessage("bot", "Lỗi hệ thống: " + (data.detail || res.statusText), "error");
        } else {
          appendMessage("bot", data.reply, data.action);
        }
      } catch (err) {
        appendMessage("bot", "Không thể kết nối tới server: " + err.message, "error");
      } finally {
        sendBtn.disabled = false;
        sendBtn.textContent = "Gửi";
        msgInput.focus();
      }
    }

    updateSessionBadge();
    appendMessage(
      "bot",
      "Xin chào! Mình là trợ lý ảo Highlands Coffee. Mình có thể tư vấn thực đơn, giải đáp thông tin chi nhánh/khuyến mãi hoặc nhận đặt món giúp bạn ạ!",
      "system"
    );
  </script>
</body>
</html>
"""


@router.get("/", response_class=HTMLResponse)
async def chat_ui() -> HTMLResponse:
    return HTMLResponse(content=CHAT_UI_HTML)
