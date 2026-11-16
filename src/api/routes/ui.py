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
    .btn-voice-toggle {
      background: rgba(255, 255, 255, 0.16);
      color: #fff;
      border: 1px solid rgba(255, 255, 255, 0.28);
      padding: 5px 11px;
      border-radius: 6px;
      font-weight: 600;
      cursor: pointer;
      font-size: 0.8rem;
      transition: all 0.15s;
    }
    .btn-voice-toggle:hover {
      background: rgba(255, 255, 255, 0.28);
    }
    .btn-mic {
      background: #fff;
      color: var(--brand);
      border: 1px solid var(--border);
      padding: 0 16px;
      border-radius: 10px;
      font-size: 1.15rem;
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: all 0.2s;
    }
    .btn-mic:hover {
      border-color: var(--brand);
      background: #faf7f5;
    }
    .btn-mic.recording {
      background: #e74c3c;
      color: #fff;
      border-color: #c0392b;
      animation: mic-pulse 1.2s infinite;
    }
    @keyframes mic-pulse {
      0% { transform: scale(1); box-shadow: 0 0 0 0 rgba(231, 76, 60, 0.5); }
      70% { transform: scale(1.06); box-shadow: 0 0 0 9px rgba(231, 76, 60, 0); }
      100% { transform: scale(1); box-shadow: 0 0 0 0 rgba(231, 76, 60, 0); }
    }
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
      <button id="voice-toggle-btn" class="btn-voice-toggle" onclick="toggleVoiceOutput()" title="Bật/Tắt tự động đọc giọng nói">🔊 Đọc: Bật</button>
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
      <button id="mic-btn" type="button" class="btn-mic" onclick="toggleSpeechRecognition()" title="Bấm để nói bằng Micro">🎙️</button>
      <button id="send-btn" type="submit">Gửi</button>
    </form>
  </main>

  <script>
    function getStoredSession() {
      try {
        return localStorage.getItem("coffee_session_id");
      } catch (e) {
        return null;
      }
    }

    function setStoredSession(id) {
      try {
        localStorage.setItem("coffee_session_id", id);
      } catch (e) {}
    }

    function makeSessionId() {
      const id = "sess-" + Math.random().toString(36).substring(2, 8);
      setStoredSession(id);
      return id;
    }

    let sessionId = getStoredSession() || makeSessionId();
    const chatBox = document.getElementById("chat-box");
    const msgInput = document.getElementById("msg-input");
    const sendBtn = document.getElementById("send-btn");
    const sessionLabel = document.getElementById("session-label");
    const micBtn = document.getElementById("mic-btn");
    const voiceToggleBtn = document.getElementById("voice-toggle-btn");

    let autoSpeak = true;
    let vietnameseVoice = null;
    let recognition = null;
    let isListening = false;

    function initVoices() {
      if (!("speechSynthesis" in window)) return;
      const voices = window.speechSynthesis.getVoices();
      vietnameseVoice = voices.find(v => v.lang && (v.lang.toLowerCase().includes("vi") || v.lang.toLowerCase() === "vi-vn")) || null;
    }
    if ("speechSynthesis" in window) {
      initVoices();
      if (window.speechSynthesis.onvoiceschanged !== undefined) {
        window.speechSynthesis.onvoiceschanged = initVoices;
      }
    }

    function toggleVoiceOutput() {
      autoSpeak = !autoSpeak;
      if (voiceToggleBtn) {
        voiceToggleBtn.textContent = autoSpeak ? "🔊 Đọc: Bật" : "🔇 Đọc: Tắt";
        voiceToggleBtn.style.opacity = autoSpeak ? "1" : "0.65";
      }
      if (!autoSpeak && "speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
    }

    function speakText(text) {
      if (!autoSpeak || !("speechSynthesis" in window) || !text) return;
      try {
        window.speechSynthesis.cancel();
        const utterance = new SpeechSynthesisUtterance(text);
        utterance.lang = "vi-VN";
        utterance.rate = 1.0;
        utterance.pitch = 1.0;
        if (vietnameseVoice) {
          utterance.voice = vietnameseVoice;
        }
        window.speechSynthesis.speak(utterance);
      } catch (err) {
        console.warn("TTS error:", err);
      }
    }

    const SpeechRec = window.SpeechRecognition || window.webkitSpeechRecognition;

    function stopListening() {
      isListening = false;
      if (micBtn) micBtn.classList.remove("recording");
      if (msgInput) msgInput.placeholder = "Nhập câu hỏi tư vấn, chính sách quán hoặc đặt món...";
    }

    if (SpeechRec) {
      recognition = new SpeechRec();
      recognition.lang = "vi-VN";
      recognition.continuous = false;
      recognition.interimResults = false;

      recognition.onstart = () => {
        isListening = true;
        if (micBtn) micBtn.classList.add("recording");
        if (msgInput) msgInput.placeholder = "Đang lắng nghe tiếng Việt từ micro...";
      };

      recognition.onresult = (event) => {
        const transcript = event.results && event.results[0] && event.results[0][0] ? event.results[0][0].transcript : "";
        stopListening();
        if (transcript.trim()) {
          msgInput.value = transcript.trim();
          sendMessage(transcript.trim());
        }
      };

      recognition.onerror = (event) => {
        console.warn("STT error:", event.error);
        stopListening();
      };

      recognition.onend = () => {
        stopListening();
      };
    } else {
      if (micBtn) {
        micBtn.title = "Trình duyệt chưa hỗ trợ Web Speech API (khuyên dùng Chrome/Edge)";
        micBtn.style.opacity = "0.5";
      }
    }

    function toggleSpeechRecognition() {
      if (!recognition) {
        alert("Trình duyệt hiện tại chưa hỗ trợ nhận diện giọng nói qua Web Speech API. Bạn vui lòng sử dụng Google Chrome hoặc Microsoft Edge để nói qua Micro nhé!");
        return;
      }
      if (isListening) {
        recognition.stop();
        stopListening();
      } else {
        try {
          recognition.start();
        } catch (e) {
          console.warn("Recognition start failed:", e);
        }
      }
    }

    function updateSessionBadge() {
      if (sessionLabel) {
        sessionLabel.textContent = "Session: " + sessionId;
      }
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
      if ("speechSynthesis" in window) {
        window.speechSynthesis.cancel();
      }
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

      const botDiv = document.createElement("div");
      botDiv.className = "msg bot";
      const meta = document.createElement("div");
      meta.className = "msg-meta";
      meta.innerHTML = `<span class="badge-action">Đang suy nghĩ...</span>`;
      const body = document.createElement("div");
      body.textContent = "";
      botDiv.appendChild(meta);
      botDiv.appendChild(body);
      chatBox.appendChild(botDiv);
      chatBox.scrollTop = chatBox.scrollHeight;

      try {
        let streamOk = false;
        try {
          const res = await fetch("/api/v1/chat/stream", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, message: text })
          });
          if (res.ok && res.body && res.body.getReader) {
            const reader = res.body.getReader();
            const decoder = new TextDecoder("utf-8");
            let buffer = "";
            while (true) {
              const { done, value } = await reader.read();
              if (done) break;
              buffer += decoder.decode(value, { stream: true });
              const lines = buffer.split("\\n\\n");
              buffer = lines.pop();

              for (const block of lines) {
                const trimmed = block.trim();
                if (!trimmed.startsWith("data: ")) continue;
                try {
                  const payload = JSON.parse(trimmed.slice(6));
                  if (payload.event === "routed") {
                    meta.innerHTML = `<span class="badge-action">${payload.action}</span>`;
                  } else if (payload.event === "token") {
                    body.textContent += payload.token;
                    chatBox.scrollTop = chatBox.scrollHeight;
                  } else if (payload.event === "done") {
                    meta.innerHTML = `<span class="badge-action">${payload.action}</span>`;
                    body.textContent = payload.reply;
                    chatBox.scrollTop = chatBox.scrollHeight;
                    speakText(payload.tts_text || payload.reply);
                  }
                } catch (err) {
                  console.error("Parse SSE error:", err);
                }
              }
            }
            if (body.textContent.trim().length > 0) {
              streamOk = true;
            }
          }
        } catch (streamErr) {
          console.warn("SSE stream failed, falling back to standard POST:", streamErr);
        }

        if (!streamOk) {
          const res = await fetch("/api/v1/chat", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ session_id: sessionId, message: text })
          });
          if (!res.ok) {
            const err = await res.text();
            body.textContent = "Lỗi hệ thống: " + (err || res.statusText);
            meta.innerHTML = `<span class="badge-action">ERROR</span>`;
            return;
          }
          const data = await res.json();
          meta.innerHTML = `<span class="badge-action">${data.action}</span>`;
          body.textContent = data.reply;
          chatBox.scrollTop = chatBox.scrollHeight;
          speakText(data.reply);
        }
      } catch (err) {
        body.textContent = "Không thể kết nối tới server: " + err.message;
        meta.innerHTML = `<span class="badge-action">ERROR</span>`;
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
    return HTMLResponse(
        content=CHAT_UI_HTML,
        headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
    )
