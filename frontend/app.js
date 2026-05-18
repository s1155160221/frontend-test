const BASE_URL = "http://localhost:8000/chat";

const chatHistoryEl = document.getElementById("chat-history");
const chatInputEl = document.getElementById("chat-input");
const sendBtnEl = document.getElementById("send-btn");
const clearHistoryBtnEl = document.getElementById("clear-history-btn");

let isSending = false;
let loadingRowEl = null;

function scrollToBottom() {
  if (!chatHistoryEl) return;
  chatHistoryEl.scrollTop = chatHistoryEl.scrollHeight;
}

function addMessageBubble(role, text) {
  if (!chatHistoryEl) return;

  const row = document.createElement("div");
  row.classList.add("message-row");

  const normalizedRole = (role || "").toLowerCase();
  if (normalizedRole === "user") {
    row.classList.add("user");
  } else if (normalizedRole === "assistant" || normalizedRole === "bot") {
    row.classList.add("bot");
  } else {
    row.classList.add("system");
  }

  const bubble = document.createElement("div");
  bubble.classList.add("message-bubble");
  bubble.textContent = text;

  row.appendChild(bubble);
  chatHistoryEl.appendChild(row);
  scrollToBottom();

  return row;
}

// --- Helper for parsing references from assistant answers ---

function splitAnswerAndReferences(text) {
  if (!text) {
    return { mainText: "", references: [] };
  }

  const marker = "reference:";
  const lower = text.toLowerCase();
  const idx = lower.lastIndexOf(marker);

  if (idx === -1) {
    return { mainText: text, references: [] };
  }

  const mainText = text.slice(0, idx);
  const refBlock = text.slice(idx + marker.length);

  const lines = refBlock.split(/\r?\n/).map((l) => l.trim());
  const references = [];

  for (const line of lines) {
    if (!line.startsWith("-")) continue;

    // Last <...> as URL
    const urlMatch = line.match(/<([^>]+)>[^<]*$/);
    if (!urlMatch) continue;
    const url = urlMatch[1];

    // [1] style id
    const idMatch = line.match(/\[(\d+)\]/);
    const id = idMatch ? idMatch[1] : "?";

    // All <...> parts; last one is URL, others are titles
    const titleMatches = [...line.matchAll(/<([^>]+)>/g)].map((m) => m[1]);
    const titleParts = titleMatches.slice(0, -1);
    const title = titleParts.join(" / ") || url;

    const label = `[${id}] ${title}`;
    references.push({ label, url });
  }

  return { mainText, references };
}

// --- Specialized renderer for assistant messages with reference bubbles ---

function addAssistantMessageWithReferences(text) {
  if (!chatHistoryEl) return;

  const row = document.createElement("div");
  row.classList.add("message-row", "bot");

  const bubble = document.createElement("div");
  bubble.classList.add("message-bubble", "message-bubble-assistant");

  const { mainText, references } = splitAnswerAndReferences(text);

  const mainDiv = document.createElement("div");
  mainDiv.classList.add("message-main");

  const raw = (mainText || "").trim();
  if (window.marked && raw) {
    // Render markdown (including tables, headings, blockquotes)
    mainDiv.innerHTML = window.marked.parse(raw);
  } else {
    // Fallback if marked is not available
    mainDiv.textContent = raw;
  }

  bubble.appendChild(mainDiv);

  if (references.length > 0) {
    const refsContainer = document.createElement("div");
    refsContainer.classList.add("message-references");

    references.forEach((ref) => {
      const pill = document.createElement("button");
      pill.type = "button";
      pill.classList.add("reference-pill");
      pill.textContent = ref.label;
      pill.addEventListener("click", () => {
        window.open(ref.url, "_blank");
      });
      refsContainer.appendChild(pill);
    });

    bubble.appendChild(refsContainer);
  }

  row.appendChild(bubble);
  chatHistoryEl.appendChild(row);
  scrollToBottom();

  return row;
}

function setLoading(isLoading) {
  if (isLoading) {
    if (loadingRowEl) return;
    loadingRowEl = addMessageBubble("system", "Thinking…");
    if (loadingRowEl) {
      loadingRowEl.classList.add("loading-indicator");
    }
  } else {
    if (loadingRowEl && loadingRowEl.parentNode) {
      loadingRowEl.parentNode.removeChild(loadingRowEl);
    }
    loadingRowEl = null;
  }
}

async function loadHistory() {
  if (!chatHistoryEl) return;
  chatHistoryEl.innerHTML = "";
  try {
    const res = await fetch(`${BASE_URL}/history`);
    if (!res.ok) {
      addMessageBubble(
        "system",
        `Failed to load history (status ${res.status}).`
      );
      return;
    }
    const data = await res.json();
    if (Array.isArray(data)) {
      for (const item of data) {
        const role = item.role || item.sender || "assistant";
        const content =
          item.content ||
          item.message ||
          item.text ||
          String(item);

        const normalizedRole = (role || "").toLowerCase();
        if (normalizedRole === "assistant" || normalizedRole === "bot") {
          addAssistantMessageWithReferences(content);
        } else {
          addMessageBubble(role, content);
        }
      }
    } else {
      addMessageBubble(
        "system",
        "Unexpected history format from server."
      );
    }
  } catch (err) {
    console.error("Error loading history:", err);
    addMessageBubble(
      "system",
      "Error loading history. Please check the backend."
    );
  }
}

async function sendMessage() {
  if (isSending) return;
  if (!chatInputEl) return;

  const text = chatInputEl.value.trim();
  if (!text) return;

  addMessageBubble("user", text);

  chatInputEl.value = "";
  chatInputEl.focus();
  isSending = true;
  sendBtnEl.disabled = true;
  setLoading(true);

  try {
    const res = await fetch(`${BASE_URL}/answer`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ question: text }),
    });

    if (!res.ok) {
      addMessageBubble(
        "system",
        `Server error while getting answer (status ${res.status}).`
      );
      return;
    }

    const data = await res.json();
    const botText =
      data.answer ||
      data.content ||
      data.text ||
      (typeof data === "string" ? data : JSON.stringify(data));
    addAssistantMessageWithReferences(botText);
  } catch (err) {
    console.error("Error sending message:", err);
    addMessageBubble(
      "system",
      "Network error while sending message. Please check the backend."
    );
  } finally {
    setLoading(false);
    isSending = false;
    sendBtnEl.disabled = false;
    scrollToBottom();
  }
}

async function clearHistory() {
  if (!confirm("Clear chat history?")) {
    return;
  }

  try {
    const res = await fetch(`${BASE_URL}/history`, {
      method: "DELETE",
    });
    if (!res.ok) {
      addMessageBubble(
        "system",
        `Failed to clear history (status ${res.status}).`
      );
      return;
    }
    if (chatHistoryEl) {
      chatHistoryEl.innerHTML = "";
    }
    addMessageBubble("system", "History cleared.");
  } catch (err) {
    console.error("Error clearing history:", err);
    addMessageBubble(
      "system",
      "Error clearing history. Please check the backend."
    );
  }
}

document.addEventListener("DOMContentLoaded", () => {
  if (sendBtnEl) {
    sendBtnEl.addEventListener("click", () => {
      sendMessage();
    });
  }

  if (chatInputEl) {
    chatInputEl.addEventListener("keydown", (event) => {
      if (event.key === "Enter" && !event.shiftKey) {
        event.preventDefault();
        sendMessage();
      }
    });
  }

  if (clearHistoryBtnEl) {
    clearHistoryBtnEl.addEventListener("click", () => {
      clearHistory();
    });
  }

  loadHistory();
});