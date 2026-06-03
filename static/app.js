const messagesEl = document.querySelector("#messages");
const composer = document.querySelector("#composer");
const messageInput = document.querySelector("#message");
const sendButton = document.querySelector("#send");
const player = document.querySelector("#player");
const saveAudioButton = document.querySelector("#saveAudio");
const audioSaveStatus = document.querySelector("#audioSaveStatus");
const portraitWrap = document.querySelector(".portrait-wrap");
const portrait = document.querySelector("#portrait");
const modelSelect = document.querySelector("#model");
const stepsInput = document.querySelector("#steps");
const replyLength = document.querySelector("#replyLength");
const systemPrompt = document.querySelector("#systemPrompt");
const ttsCaption = document.querySelector("#ttsCaption");
const contextLimit = document.querySelector("#contextLimit");
const contextUsage = document.querySelector("#contextUsage");
const autoEmoji = document.querySelector("#autoEmoji");
const emojiStyleSelect = document.querySelector("#emojiStyle");
const emojiCustom = document.querySelector("#emojiCustom");
const saveSessionButton = document.querySelector("#saveSession");
const loadSessionButton = document.querySelector("#loadSession");
const clearContextButton = document.querySelector("#clearContext");
const sessionStatus = document.querySelector("#sessionStatus");
const lmStatus = document.querySelector("#lmStatus");
const irodoriStatus = document.querySelector("#irodoriStatus");
const speaking = document.querySelector("#speaking");

const history = [];
let queue = [];
let interactionLocked = false;
let expressionImages = {
  neutral: ["/expressions/neutral.png"],
  happy: ["/expressions/happy.png"],
  surprised: ["/expressions/surprised.png"],
  soft: ["/expressions/soft.png"],
  angry: ["/expressions/angry.png"],
  worried: ["/expressions/worried.png"],
  sad: ["/expressions/sad.png"],
  shy: ["/expressions/shy.png"],
  narration: ["/expressions/narration.png"],
  fast: ["/expressions/fast.png"],
  sleepy: ["/expressions/sleepy.png"],
  phone: ["/expressions/phone.png"],
  echo: ["/expressions/echo.png"],
  muffled: ["/expressions/muffled.png"],
  throat: ["/expressions/throat.png"],
  strong: ["/expressions/strong.png"],
  teasing: ["/expressions/teasing.png"],
  pleading: ["/expressions/pleading.png"],
  exasperated: ["/expressions/exasperated.png"],
  smug: ["/expressions/smug.png"],
  sigh: ["/expressions/sigh.png"],
  gasp: ["/expressions/gasp.png"],
  breathless: ["/expressions/breathless.png"],
  yawn: ["/expressions/yawn.png"],
  humming: ["/expressions/humming.png"],
  swallow: ["/expressions/swallow.png"],
  cough: ["/expressions/cough.png"],
  sniff: ["/expressions/sniff.png"],
  pause: ["/expressions/pause.png"],
  question: ["/expressions/question.png"],
  tender: ["/expressions/tender.png"],
  broadcast: ["/expressions/broadcast.png"],
};

function setExpression(name) {
  const key = expressionImages[name] ? name : "neutral";
  const values = Array.isArray(expressionImages[key]) ? expressionImages[key] : [expressionImages[key]];
  const usable = values.filter(Boolean);
  const src = usable[Math.floor(Math.random() * usable.length)] || "/expressions/neutral.png";
  portrait.src = src;
}

function addMessage(role, text, meta = "") {
  const node = document.createElement("div");
  node.className = `msg ${role}`;
  node.textContent = text;
  if (meta) {
    const metaNode = document.createElement("div");
    metaNode.className = "meta";
    metaNode.textContent = meta;
    node.appendChild(metaNode);
  }
  messagesEl.appendChild(node);
  messagesEl.scrollTop = messagesEl.scrollHeight;
}

function contextCost(items) {
  return items.reduce((total, item) => total + String(item.content || "").length + 32, 0);
}

function updateContextUsage(extraText = "") {
  const limit = Number(contextLimit.value || 8200);
  const pending = extraText ? [{ role: "user", content: extraText }] : [];
  const used = contextCost([...history, ...pending]);
  contextUsage.textContent = `${used} / ${limit}`;
  contextUsage.classList.toggle("is-near", used > limit * 0.8);
  contextUsage.classList.toggle("is-over", used > limit);
}

function setInteractionLocked(locked, label = "Send") {
  interactionLocked = locked;
  sendButton.disabled = locked;
  sendButton.textContent = label;
  messageInput.readOnly = locked;
}

function currentEmojiStyle() {
  return emojiCustom.value.trim() || emojiStyleSelect.value;
}

function refreshEmojiInputs() {
  const manual = !autoEmoji.checked;
  emojiStyleSelect.disabled = !manual;
  emojiCustom.disabled = !manual;
}

function setSelectValue(select, value) {
  if (!value) return;
  const exists = [...select.options].some((option) => option.value === value);
  if (!exists) {
    const option = document.createElement("option");
    option.value = value;
    option.textContent = value;
    select.appendChild(option);
  }
  select.value = value;
}

function sessionPayload() {
  return {
    settings: {
      systemPrompt: systemPrompt.value,
      ttsCaption: ttsCaption.value,
      contextLimit: Number(contextLimit.value || 8200),
      model: modelSelect.value,
      steps: Number(stepsInput.value || 12),
      replyLength: replyLength.value,
      autoEmoji: autoEmoji.checked,
      emojiStyle: emojiStyleSelect.value,
      emojiCustom: emojiCustom.value,
    },
    history,
  };
}

function renderHistory(items) {
  history.length = 0;
  messagesEl.innerHTML = "";
  for (const item of items || []) {
    if (!item || !["user", "assistant"].includes(item.role) || !item.content) continue;
    history.push({ role: item.role, content: item.content });
    addMessage(item.role, item.content);
  }
  updateContextUsage();
}

function clearContext() {
  const ok = window.confirm("今の会話コンテキストを消して、ゼロからやり直します。消してもいいですか？");
  if (!ok) return;
  history.length = 0;
  messagesEl.innerHTML = "";
  queue = [];
  player.pause();
  player.removeAttribute("src");
  player.load();
  audioSaveStatus.textContent = "no audio";
  speaking.textContent = "ready";
  portraitWrap.classList.remove("is-speaking");
  setExpression("neutral");
  setInteractionLocked(false);
  sessionStatus.textContent = "context cleared";
  updateContextUsage();
}

function applySession(profile) {
  const settings = profile.settings || {};
  if (settings.systemPrompt) systemPrompt.value = settings.systemPrompt;
  if (settings.ttsCaption) ttsCaption.value = settings.ttsCaption;
  if (settings.contextLimit) {
    contextLimit.value = settings.contextLimit;
    contextLimit.dataset.touched = "1";
  }
  updateContextUsage();
  setSelectValue(modelSelect, settings.model);
  if (settings.steps) stepsInput.value = settings.steps;
  if (settings.replyLength) replyLength.value = settings.replyLength;
  autoEmoji.checked = Boolean(settings.autoEmoji ?? true);
  setSelectValue(emojiStyleSelect, settings.emojiStyle);
  emojiCustom.value = settings.emojiCustom || "";
  refreshEmojiInputs();
  renderHistory(profile.history || []);
  sessionStatus.textContent = profile.savedAt
    ? `loaded ${profile.history?.length || 0} turns`
    : "loaded";
}

async function saveSession() {
  const res = await fetch("/api/session", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(sessionPayload()),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  sessionStatus.textContent = `saved ${data.historyCount} turns`;
}

async function loadSession(silent = false) {
  const res = await fetch("/api/session");
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  if (!data.exists) {
    if (!silent) sessionStatus.textContent = "no save";
    return;
  }
  applySession(data);
}

function playQueue(items) {
  queue = [...items];
  if (queue.length === 0) {
    setInteractionLocked(false);
  }
  playNext();
}

function playNext() {
  const next = queue.shift();
  if (!next) {
    speaking.textContent = "ready";
    portraitWrap.classList.remove("is-speaking");
    setExpression("neutral");
    setInteractionLocked(false);
    return;
  }
  setExpression(next.expression || "neutral");
  speaking.textContent = "speaking";
  portraitWrap.classList.add("is-speaking");
  player.src = next.url;
  audioSaveStatus.textContent = "save ready";
  player.play().catch(() => {
    speaking.textContent = "tap play";
    portraitWrap.classList.remove("is-speaking");
  });
}

player.addEventListener("ended", playNext);

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    lmStatus.textContent = data.models.length ? `${data.models.length} models` : "not detected";
    if (data.contextLimit && !contextLimit.dataset.touched) {
      contextLimit.value = data.contextLimit;
    }
    updateContextUsage();
    if (data.ttsCaption && !ttsCaption.dataset.touched) {
      ttsCaption.value = data.ttsCaption;
    }
    irodoriStatus.textContent = data.referenceExists
      ? `Tokyo ref / ${data.irodoriRoot}`
      : data.irodoriRoot;
    expressionImages = Object.fromEntries(
      Object.entries(data.expressions || expressionImages).map(([key, value]) => [
        key,
        Array.isArray(value) ? value : [value],
      ])
    );
    setExpression("neutral");
    modelSelect.innerHTML = "";
    for (const model of data.models) {
      const option = document.createElement("option");
      option.value = model;
      option.textContent = model;
      modelSelect.appendChild(option);
    }
    const preferred =
      [...modelSelect.options].find((opt) => opt.value === "gemma-4-31b-it") ||
      [...modelSelect.options].find((opt) => opt.value.toLowerCase().includes("gemma"));
    if (preferred) modelSelect.value = preferred.value;

    emojiStyleSelect.innerHTML = '<option value="">plain</option>';
    for (const item of data.emojis || []) {
      const option = document.createElement("option");
      option.value = item.emoji;
      option.textContent = `${item.emoji} ${item.label}`;
      option.title = item.description;
      emojiStyleSelect.appendChild(option);
    }
  } catch (error) {
    lmStatus.textContent = "error";
    irodoriStatus.textContent = String(error);
  }
}

composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  if (interactionLocked) return;
  const text = messageInput.value.trim();
  if (!text) return;
  const historyBeforeSend = [...history];
  addMessage("user", text);
  history.push({ role: "user", content: text });
  updateContextUsage();
  messageInput.value = "";
  setInteractionLocked(true, "Wait");
  speaking.textContent = "thinking";
  setExpression("soft");

  try {
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: historyBeforeSend,
        model: modelSelect.value,
        steps: Number(stepsInput.value || 12),
        replyLength: replyLength.value,
        systemPrompt: systemPrompt.value,
        ttsCaption: ttsCaption.value,
        contextLimit: Number(contextLimit.value || 8200),
        emojiStyle: autoEmoji.checked ? "" : currentEmojiStyle(),
        autoEmoji: autoEmoji.checked,
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    const timing = data.audios.map((item) => `${item.elapsed}s`).join(", ");
    const style = data.emojiStyle
      ? ` / ${data.autoEmoji && data.llmEmojiStyle ? "auto style" : "style"} ${data.emojiStyle}`
      : "";
    addMessage("assistant", data.reply, `${data.model} / ${data.replyLength}${style} / pose ${data.expression} / tts ${timing}`);
    history.push({ role: "assistant", content: data.reply });
    updateContextUsage();
    playQueue(data.audios);
  } catch (error) {
    addMessage("assistant", `エラー: ${error.message}`);
    speaking.textContent = "error";
    setInteractionLocked(false);
  }
});

autoEmoji.addEventListener("change", refreshEmojiInputs);
contextLimit.addEventListener("input", () => {
  contextLimit.dataset.touched = "1";
  updateContextUsage();
});

ttsCaption.addEventListener("input", () => {
  ttsCaption.dataset.touched = "1";
});

saveSessionButton.addEventListener("click", async () => {
  try {
    sessionStatus.textContent = "saving...";
    await saveSession();
  } catch (error) {
    sessionStatus.textContent = `save error: ${error.message}`;
  }
});

loadSessionButton.addEventListener("click", async () => {
  try {
    sessionStatus.textContent = "loading...";
    await loadSession();
  } catch (error) {
    sessionStatus.textContent = `load error: ${error.message}`;
  }
});

clearContextButton.addEventListener("click", clearContext);

saveAudioButton.addEventListener("click", async () => {
  const currentUrl = player.getAttribute("src") || "";
  if (!currentUrl) {
    audioSaveStatus.textContent = "no audio";
    return;
  }
  try {
    audioSaveStatus.textContent = "saving...";
    const res = await fetch("/api/save-audio", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        url: currentUrl,
        label: "rinon",
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    audioSaveStatus.textContent = `saved: ${data.name}`;
  } catch (error) {
    audioSaveStatus.textContent = `save error: ${error.message}`;
  }
});

messageInput.addEventListener("keydown", (event) => {
  if (event.key === "Enter" && !event.shiftKey) {
    event.preventDefault();
    composer.requestSubmit();
  }
});

async function initialize() {
  refreshEmojiInputs();
  await refreshStatus();
  await loadSession(true);
}

initialize().catch((error) => {
  sessionStatus.textContent = `init error: ${error.message}`;
});
