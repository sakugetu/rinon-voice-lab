const messagesEl = document.querySelector("#messages");
const composer = document.querySelector("#composer");
const messageInput = document.querySelector("#message");
const sendButton = document.querySelector("#send");
const autoStartButton = document.querySelector("#autoStart");
const player = document.querySelector("#player");
const saveAudioButton = document.querySelector("#saveAudio");
const audioSaveStatus = document.querySelector("#audioSaveStatus");
const portraitWrap = document.querySelector("#mainPortraitWrap");
const secondPortraitWrap = document.querySelector("#secondPortraitWrap");
const portrait = document.querySelector("#portrait");
const secondPortrait = document.querySelector("#secondPortrait");
const mainCharacterNameLabel = document.querySelector("#mainCharacterNameLabel");
const secondCharacterNameLabel = document.querySelector("#secondCharacterNameLabel");
const modelSelect = document.querySelector("#model");
const stepsInput = document.querySelector("#steps");
const speechRate = document.querySelector("#speechRate");
const speechRateButtons = Array.from(document.querySelectorAll("[data-rate]"));
const replyLength = document.querySelector("#replyLength");
const systemPrompt = document.querySelector("#systemPrompt");
const userAddress = document.querySelector("#userAddress");
const ttsCaption = document.querySelector("#ttsCaption");
const secondSystemPrompt = document.querySelector("#secondSystemPrompt");
const secondTtsCaption = document.querySelector("#secondTtsCaption");
const contextLimit = document.querySelector("#contextLimit");
const contextUsage = document.querySelector("#contextUsage");
const autoEmoji = document.querySelector("#autoEmoji");
const webSearch = document.querySelector("#webSearch");
const twoPlayerMode = document.querySelector("#twoPlayerMode");
const twoOnlyMode = document.querySelector("#twoOnlyMode");
const mainCharacterSelect = document.querySelector("#mainCharacterSelect");
const secondCharacterSelect = document.querySelector("#secondCharacterSelect");
const openOptionsButton = document.querySelector("#openOptions");
const closeOptionsButton = document.querySelector("#closeOptions");
const shutdownAppButton = document.querySelector("#shutdownApp");
const optionsModal = document.querySelector("#optionsModal");
const editCharacterSelect = document.querySelector("#editCharacterSelect");
const newCharacterButton = document.querySelector("#newCharacter");
const loadCharactersButton = document.querySelector("#loadCharacters");
const saveCharactersButton = document.querySelector("#saveCharacters");
const editCharacterName = document.querySelector("#editCharacterName");
const editSystemPrompt = document.querySelector("#editSystemPrompt");
const editTtsCaption = document.querySelector("#editTtsCaption");
const editReferenceFile = document.querySelector("#editReferenceFile");
const editReferenceChoose = document.querySelector("#editReferenceChoose");
const editReferenceDrop = document.querySelector("#editReferenceDrop");
const editReferenceStatus = document.querySelector("#editReferenceStatus");
const editExpressionSelect = document.querySelector("#editExpressionSelect");
const expressionSlotDescription = document.querySelector("#expressionSlotDescription");
const newExpressionName = document.querySelector("#newExpressionName");
const addExpressionSlot = document.querySelector("#addExpressionSlot");
const expressionImageFile = document.querySelector("#expressionImageFile");
const expressionImageChoose = document.querySelector("#expressionImageChoose");
const expressionImageDrop = document.querySelector("#expressionImageDrop");
const expressionImageStatus = document.querySelector("#expressionImageStatus");
const expressionThumbs = document.querySelector("#expressionThumbs");
const emojiStyleSelect = document.querySelector("#emojiStyle");
const emojiCustom = document.querySelector("#emojiCustom");
const saveSessionButton = document.querySelector("#saveSession");
const loadSessionButton = document.querySelector("#loadSession");
const clearContextButton = document.querySelector("#clearContext");
const sessionStatus = document.querySelector("#sessionStatus");
const lmStatus = document.querySelector("#lmStatus");
const irodoriStatus = document.querySelector("#irodoriStatus");
const speaking = document.querySelector("#speaking");
const secondSpeaking = document.querySelector("#secondSpeaking");
const DEFAULT_MAIN_CHARACTER_NAME = "リノン";
const DEFAULT_SECOND_CHARACTER_NAME = "ルヴィア";
let mainCharacterName = DEFAULT_MAIN_CHARACTER_NAME;
let secondCharacterName = DEFAULT_SECOND_CHARACTER_NAME;
let mainReferencePath = "";
let secondReferencePath = "";
let characters = {};
let activeMainCharacterId = "rinon";
let activeSecondCharacterId = "luvia";
let editingCharacterId = "rinon";

const history = [];
let queue = [];
let interactionLocked = false;
let autoMode = false;
let autoPending = false;
let autoNextSpeaker = mainCharacterName;
let playbackSpeaker = mainCharacterName;
let lastAssistantSpeaker = "";
let lastAssistantText = "";
let autoTopic = "";
let autoTopicQueue = [];
let autoWebContext = "";
let autoWebQuery = "";
let autoWebResults = [];
let autoTurnCount = 0;
let autoNoDialogue = false;
let externalSpeakLastId = 0;
let externalSpeakPolling = false;
let lastContextStats = null;
let audioContext = null;
let audioSource = null;
let stereoPanner = null;
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
const expressionSlotInfo = {
  neutral: { emoji: "・", label: "通常", description: "基準になる表情" },
  happy: { emoji: "😊", label: "楽しげ", description: "嬉しそう、明るい反応" },
  surprised: { emoji: "😲", label: "驚き", description: "驚く、息をのむ" },
  soft: { emoji: "👂", label: "囁き", description: "近い距離のやわらかい声" },
  angry: { emoji: "😠", label: "怒り", description: "不満げ、拗ねる" },
  worried: { emoji: "😟", label: "心配", description: "不安そう、弱い声" },
  sad: { emoji: "😭", label: "泣き声", description: "悲しみ、嗚咽" },
  shy: { emoji: "🫣", label: "照れ", description: "恥ずかしそう" },
  narration: { emoji: "📖", label: "朗読", description: "ナレーション調" },
  fast: { emoji: "⏩", label: "早口", description: "急いで一気に話す" },
  sleepy: { emoji: "😪", label: "眠そう", description: "気だるげ、眠い声" },
  phone: { emoji: "📞", label: "電話越し", description: "スピーカー越しの質感" },
  echo: { emoji: "📢", label: "エコー", description: "響き、リバーブ" },
  broadcast: { emoji: "📢", label: "エコー", description: "放送・響きのある声" },
  muffled: { emoji: "🤐", label: "口を塞ぐ", description: "こもった声、口元の音" },
  throat: { emoji: "😖", label: "苦しげ", description: "喉に力が入る、詰まる感じ" },
  strong: { emoji: "💪", label: "力強く", description: "勢い、強い声" },
  teasing: { emoji: "😏", label: "からかう", description: "甘えるように、挑発的に" },
  pleading: { emoji: "🙏", label: "懇願", description: "お願いするように" },
  exasperated: { emoji: "🙄", label: "呆れ", description: "呆れた、困った反応" },
  smug: { emoji: "😎", label: "得意げ", description: "自信ありげ、余裕" },
  sigh: { emoji: "😮‍💨", label: "吐息", description: "溜息、息を漏らす" },
  gasp: { emoji: "😮", label: "息をのむ", description: "驚きの短い吸気" },
  breathless: { emoji: "🌬️", label: "息切れ", description: "荒い息遣い、呼吸音" },
  yawn: { emoji: "🥱", label: "あくび", description: "眠そうなあくび" },
  humming: { emoji: "🎵", label: "鼻歌", description: "ハミング、軽い歌声" },
  swallow: { emoji: "🥤", label: "飲み込む", description: "唾を飲む音" },
  cough: { emoji: "🤧", label: "咳・鼻", description: "咳き込み、鼻すすり" },
  sniff: { emoji: "👃", label: "嗅ぐ音", description: "匂いを嗅ぐ、鼻の音" },
  pause: { emoji: "⏸️", label: "間", description: "沈黙、間を置く" },
  question: { emoji: "🤔", label: "疑問", description: "考え込む、疑問形" },
  tender: { emoji: "🫶", label: "優しく", description: "Tenderly、包むように" },
};

function expressionSlotLabel(key) {
  const info = expressionSlotInfo[key];
  return info ? `${info.emoji} ${info.label} / ${key}` : `・ カスタム / ${key}`;
}

function expressionSlotDetail(key) {
  const info = expressionSlotInfo[key];
  return info ? `${info.emoji} ${info.label}: ${info.description}` : `・ カスタム: ${key}`;
}

const secondExpressionImages = {
  neutral: ["/second_player/expressions/luvia_neutral.png"],
  happy: ["/second_player/expressions/luvia_happy.png", "/second_player/expressions/luvia_laughing.png"],
  surprised: ["/second_player/expressions/luvia_surprised.png"],
  soft: ["/second_player/expressions/luvia_soft.png"],
  angry: ["/second_player/expressions/luvia_angry.png"],
  worried: ["/second_player/expressions/luvia_worried.png"],
  sad: ["/second_player/expressions/luvia_sad.png"],
  shy: [
    "/second_player/expressions/luvia_shy.png",
    "/second_player/expressions/luvia_shy_02.png",
    "/second_player/expressions/luvia_shy_03.png",
    "/second_player/expressions/luvia_shy_04.png",
    "/second_player/expressions/luvia_shy_05.png",
  ],
  strong: ["/second_player/expressions/luvia_determined.png"],
  teasing: [
    "/second_player/expressions/luvia_teasing.png",
    "/second_player/expressions/luvia_teasing_02.png",
    "/second_player/expressions/luvia_teasing_03.png",
    "/second_player/expressions/luvia_teasing_04.png",
    "/second_player/expressions/luvia_teasing_05.png",
  ],
  pleading: ["/second_player/expressions/luvia_worried.png"],
  exasperated: ["/second_player/expressions/luvia_exasperated.png"],
  smug: ["/second_player/expressions/luvia_smug.png"],
  sigh: ["/second_player/expressions/luvia_exasperated.png"],
  question: ["/second_player/expressions/luvia_question.png"],
  tender: [
    "/second_player/expressions/luvia_tender.png",
    "/second_player/expressions/luvia_tender_02.png",
    "/second_player/expressions/luvia_tender_03.png",
    "/second_player/expressions/luvia_tender_04.png",
    "/second_player/expressions/luvia_tender_05.png",
  ],
  narration: ["/second_player/expressions/luvia_serious.png"],
  broadcast: ["/second_player/expressions/luvia_serious.png"],
  fast: ["/second_player/expressions/luvia_determined.png"],
  sleepy: ["/second_player/expressions/luvia_exasperated.png"],
  phone: ["/second_player/expressions/luvia_thoughtful.png"],
  echo: ["/second_player/expressions/luvia_serious.png"],
  muffled: [
    "/second_player/expressions/luvia_muffled.png",
    "/second_player/expressions/luvia_muffled_02.png",
    "/second_player/expressions/luvia_muffled_03.png",
    "/second_player/expressions/luvia_muffled_04.png",
    "/second_player/expressions/luvia_muffled_05.png",
  ],
  throat: ["/second_player/expressions/luvia_exasperated.png"],
  gasp: ["/second_player/expressions/luvia_surprised.png"],
  breathless: ["/second_player/expressions/luvia_exasperated.png"],
  yawn: ["/second_player/expressions/luvia_exasperated.png"],
  humming: ["/second_player/expressions/luvia_happy.png"],
  swallow: ["/second_player/expressions/luvia_thoughtful.png"],
  cough: ["/second_player/expressions/luvia_worried.png"],
  sniff: ["/second_player/expressions/luvia_worried.png"],
  pause: ["/second_player/expressions/luvia_thoughtful.png"],
  thoughtful: ["/second_player/expressions/luvia_thoughtful.png"],
  laughing: ["/second_player/expressions/luvia_laughing.png"],
  serious: ["/second_player/expressions/luvia_serious.png"],
  determined: ["/second_player/expressions/luvia_determined.png"],
};

function characterById(id) {
  return characters[id] || null;
}

function expressionValuesForCharacter(character, expression) {
  const expressions = character?.expressions || {};
  const values = expressions[expression] || expressions.neutral || [];
  return Array.isArray(values) ? values.filter(Boolean) : [values].filter(Boolean);
}

function randomExpressionImage(character, expression, fallback) {
  const values = expressionValuesForCharacter(character, expression);
  const src = values[Math.floor(Math.random() * values.length)] || character?.portrait || fallback;
  return src || fallback;
}

function setExpression(name) {
  portrait.src = randomExpressionImage(characterById(activeMainCharacterId), name, "/expressions/neutral.png");
}

function setSecondExpression(name) {
  secondPortrait.src = randomExpressionImage(
    characterById(activeSecondCharacterId),
    name,
    "/Character/luvia/expressions/neutral/luvia_neutral.png"
  );
}

function activeStage(speaker = "") {
  const mainCharacter = characterById(activeMainCharacterId);
  const secondCharacter = characterById(activeSecondCharacterId);
  const activeSpeaker = speaker || (twoPlayerMode.checked ? secondCharacterName : mainCharacterName);
  const isSecond = activeSpeaker === secondCharacterName;
  const character = isSecond ? secondCharacter : mainCharacter;
  return {
    speaker: character?.name || activeSpeaker,
    slot: isSecond ? "second" : "main",
    systemPrompt: character?.systemPrompt || (isSecond ? secondSystemPrompt.value : systemPrompt.value),
    ttsCaption: character?.ttsCaption || (isSecond ? secondTtsCaption.value : ttsCaption.value),
    referencePath: character?.referencePath || (isSecond ? secondReferencePath : mainReferencePath),
  };
}

function setActiveSpeaker(speaker, preserveTwoPlayer = false) {
  if (speaker === secondCharacterName) {
    twoPlayerMode.checked = true;
  } else if (!preserveTwoPlayer) {
    twoPlayerMode.checked = false;
  }
  updateTwoPlayerMode();
}

function setStageStatus(text, speaker = "") {
  const stage = activeStage(speaker);
  speaking.textContent = stage.slot === "main" ? text : "ready";
  secondSpeaking.textContent = stage.slot === "second" ? text : "standby";
}

function setSpeakingState(active, speaker = "") {
  const stage = activeStage(speaker);
  document.body.classList.toggle("speaking-main", active && stage.slot === "main");
  document.body.classList.toggle("speaking-second", active && stage.slot === "second");
  portraitWrap.classList.toggle("is-speaking", active && stage.slot === "main");
  secondPortraitWrap.classList.toggle("is-speaking", active && stage.slot === "second");
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
  const compactLabel = lastContextStats
    ? ` · LM ${lastContextStats.sent}/${lastContextStats.effectiveLimit}${lastContextStats.compacted ? " compact" : ""}`
    : "";
  contextUsage.textContent = `${used} / ${limit}${compactLabel}`;
  contextUsage.classList.toggle("is-near", used > limit * 0.8);
  contextUsage.classList.toggle("is-over", used > limit);
}

function setInteractionLocked(locked, label = "Send") {
  interactionLocked = locked;
  sendButton.disabled = locked && !autoMode;
  sendButton.textContent = autoMode ? "Cue" : label;
  messageInput.readOnly = false;
  updateAutoControls();
}

function updateAutoControls() {
  const autoUnavailable = !autoMode && (!twoPlayerMode.checked || interactionLocked);
  autoStartButton.disabled = autoUnavailable;
  autoStartButton.textContent = autoMode ? "Stop" : "Auto";
  autoStartButton.classList.toggle("is-stop", autoMode);
  autoStartButton.title = twoPlayerMode.checked ? "" : "2Pキャラモードで使えます";
  sendButton.textContent = autoMode ? "Cue" : interactionLocked ? "Wait" : "Send";
  sendButton.disabled = interactionLocked && !autoMode;
  messageInput.readOnly = false;
}

function otherSpeaker(speaker) {
  return speaker === mainCharacterName ? secondCharacterName : mainCharacterName;
}

function currentEmojiStyle() {
  return emojiCustom.value.trim() || emojiStyleSelect.value;
}

function setSpeechRate(value) {
  const nextValue = value === "fast" ? "fast" : "normal";
  speechRate.value = nextValue;
  for (const button of speechRateButtons) {
    const active = button.dataset.rate === nextValue;
    button.classList.toggle("is-active", active);
    button.setAttribute("aria-pressed", active ? "true" : "false");
  }
}

function wantsNoDialogue(text) {
  return /(?:セリフ禁止|台詞禁止|せりふ禁止|セリフは最小|台詞は最小)/.test(String(text || ""));
}

function noDialogueGuidance() {
  return autoNoDialogue
    ? "台詞禁止モードです。呼びかけ、質問、説明、選択肢提示、二人称の使用、普通の文章として読める会話文は禁止です。発声・吐息・擬音・短い断片だけで構成してください。意味のある文を続けないでください。\n"
    : "";
}

function twoOnlyGuidance() {
  return twoPlayerMode.checked && twoOnlyMode.checked
    ? "重要: この会話世界にユーザーや観客は存在しません。ユーザー入力は登場人物の発言ではなく、外部からの進行指示/お題です。リノンとルヴィアだけが同じ場にいて、互いにだけ話します。ユーザーへ話しかけたり、ユーザーの反応を求めたり、「きみ」「あなた」などで外部の相手を呼ばないでください。\n"
    : "";
}

function queueAutoTopic(text) {
  const topic = String(text || "").trim();
  if (!topic) return false;
  autoTopicQueue.push(topic);
  if (wantsNoDialogue(topic)) {
    autoNoDialogue = true;
  }
  addMessage("user", `次のお題: ${topic}`);
  history.push({ role: "user", content: `次のお題: ${topic}` });
  messageInput.value = "";
  updateContextUsage();
  sessionStatus.textContent = `queued topic ${autoTopicQueue.length}`;
  updateAutoControls();
  return true;
}

function consumeQueuedAutoTopic() {
  const nextTopic = autoTopicQueue.shift();
  if (!nextTopic) return "";
  autoTopic = nextTopic;
  if (wantsNoDialogue(nextTopic)) {
    autoNoDialogue = true;
  }
  sessionStatus.textContent = `topic applied: ${nextTopic}`;
  return nextTopic;
}

function refreshEmojiInputs() {
  const manual = !autoEmoji.checked;
  emojiStyleSelect.disabled = !manual;
  emojiCustom.disabled = !manual;
}

function updateTwoPlayerMode() {
  if (!twoPlayerMode.checked && autoMode) {
    stopAutoConversation();
  }
  if (!twoPlayerMode.checked) {
    twoOnlyMode.checked = false;
  }
  twoOnlyMode.disabled = !twoPlayerMode.checked;
  document.body.classList.toggle("two-player-mode", twoPlayerMode.checked);
  updateAudioPan(playbackSpeaker);
  if (!interactionLocked) {
    speaking.textContent = "ready";
    secondSpeaking.textContent = twoPlayerMode.checked ? "ready" : "standby";
    setSpeakingState(false);
  }
}

function ensureAudioPanner() {
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;
  if (!AudioContextClass || !AudioContextClass.prototype.createStereoPanner) {
    return false;
  }
  if (!audioContext) {
    audioContext = new AudioContextClass();
    audioSource = audioContext.createMediaElementSource(player);
    stereoPanner = audioContext.createStereoPanner();
    audioSource.connect(stereoPanner).connect(audioContext.destination);
  }
  if (audioContext.state === "suspended") {
    audioContext.resume().catch(() => {});
  }
  return Boolean(stereoPanner);
}

function updateAudioPan(speaker = "") {
  if (!ensureAudioPanner()) return;
  if (!twoPlayerMode.checked) {
    stereoPanner.pan.value = 0;
    return;
  }
  stereoPanner.pan.value = speaker === secondCharacterName ? 0.22 : -0.22;
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

function shortPathLabel(path) {
  const text = String(path || "").trim();
  if (!text) return "default reference";
  const normalized = text.replaceAll("\\", "/");
  return normalized.split("/").pop() || text;
}

function characterList() {
  return Object.values(characters).sort((a, b) => String(a.name || "").localeCompare(String(b.name || ""), "ja"));
}

function expressionKeys(character) {
  const keys = Object.keys(character?.expressions || {});
  if (!keys.includes("neutral")) keys.unshift("neutral");
  return [...new Set(keys)].sort((a, b) => (a === "neutral" ? -1 : b === "neutral" ? 1 : a.localeCompare(b)));
}

function syncActiveCharacterState() {
  const mainCharacter = characterById(activeMainCharacterId) || characterList()[0];
  const secondCharacter = characterById(activeSecondCharacterId) || characterList()[1] || mainCharacter;
  if (mainCharacter) activeMainCharacterId = mainCharacter.id;
  if (secondCharacter) activeSecondCharacterId = secondCharacter.id;
  mainCharacterName = mainCharacter?.name || DEFAULT_MAIN_CHARACTER_NAME;
  secondCharacterName = secondCharacter?.name || DEFAULT_SECOND_CHARACTER_NAME;
  mainReferencePath = mainCharacter?.referencePath || mainReferencePath;
  secondReferencePath = secondCharacter?.referencePath || secondReferencePath;
  mainCharacterNameLabel.textContent = mainCharacterName;
  secondCharacterNameLabel.textContent = secondCharacterName;
  systemPrompt.value = mainCharacter?.systemPrompt || systemPrompt.value;
  ttsCaption.value = mainCharacter?.ttsCaption || ttsCaption.value;
  secondSystemPrompt.value = secondCharacter?.systemPrompt || secondSystemPrompt.value;
  secondTtsCaption.value = secondCharacter?.ttsCaption || secondTtsCaption.value;
  setExpression("neutral");
  setSecondExpression("neutral");
  updateTwoPlayerMode();
}

function populateCharacterSelect(select, value) {
  select.innerHTML = "";
  for (const character of characterList()) {
    const option = document.createElement("option");
    option.value = character.id;
    option.textContent = character.name || character.id;
    select.appendChild(option);
  }
  if (value && characters[value]) select.value = value;
}

function refreshCharacterSelectors() {
  populateCharacterSelect(mainCharacterSelect, activeMainCharacterId);
  populateCharacterSelect(secondCharacterSelect, activeSecondCharacterId);
  populateCharacterSelect(editCharacterSelect, editingCharacterId);
}

function renderExpressionEditor() {
  const character = characterById(editingCharacterId);
  editExpressionSelect.innerHTML = "";
  for (const key of expressionKeys(character)) {
    const option = document.createElement("option");
    option.value = key;
    option.textContent = expressionSlotLabel(key);
    option.title = expressionSlotDetail(key);
    editExpressionSelect.appendChild(option);
  }
  if (!editExpressionSelect.value && editExpressionSelect.options.length) {
    editExpressionSelect.value = editExpressionSelect.options[0].value;
  }
  renderExpressionThumbs();
}

function renderExpressionThumbs() {
  const character = characterById(editingCharacterId);
  const key = editExpressionSelect.value || "neutral";
  const values = expressionValuesForCharacter(character, key);
  expressionThumbs.innerHTML = "";
  expressionSlotDescription.textContent = expressionSlotDetail(key);
  for (const url of values) {
    const img = document.createElement("img");
    img.src = url;
    img.alt = key;
    expressionThumbs.appendChild(img);
  }
  expressionImageStatus.textContent = values.length ? `${values.length} images` : "no image selected";
}

function renderCharacterEditor() {
  const character = characterById(editingCharacterId);
  if (!character) return;
  editCharacterName.value = character.name || "";
  editSystemPrompt.value = character.systemPrompt || "";
  editTtsCaption.value = character.ttsCaption || "";
  editReferenceStatus.textContent = shortPathLabel(character.referencePath);
  renderExpressionEditor();
}

function openOptions() {
  refreshCharacterSelectors();
  renderCharacterEditor();
  optionsModal.hidden = false;
  editCharacterName.focus();
}

function closeOptions() {
  syncActiveCharacterState();
  optionsModal.hidden = true;
}

function fileToDataUrl(file) {
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(String(reader.result || ""));
    reader.onerror = () => reject(reader.error || new Error("file read failed"));
    reader.readAsDataURL(file);
  });
}

async function uploadReferenceFile(slot, file) {
  if (!file) return;
  const status = editReferenceStatus;
  status.textContent = "uploading...";
  const dataBase64 = await fileToDataUrl(file);
  const res = await fetch("/api/reference", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      slot,
      characterId: editingCharacterId,
      name: file.name,
      type: file.type,
      dataBase64,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  const character = characterById(editingCharacterId);
  if (character) {
    character.referencePath = data.path;
  }
  renderCharacterEditor();
  syncActiveCharacterState();
  sessionStatus.textContent = `${character?.name || "character"} reference loaded`;
}

function installReferenceDrop(drop, input, chooseButton, slot) {
  chooseButton.addEventListener("click", () => input.click());
  input.addEventListener("change", async () => {
    try {
      await uploadReferenceFile(slot, input.files?.[0]);
    } catch (error) {
      sessionStatus.textContent = `reference error: ${error.message}`;
    } finally {
      input.value = "";
    }
  });
  for (const eventName of ["dragenter", "dragover"]) {
    drop.addEventListener(eventName, (event) => {
      event.preventDefault();
      drop.classList.add("is-dragging");
    });
  }
  for (const eventName of ["dragleave", "drop"]) {
    drop.addEventListener(eventName, (event) => {
      event.preventDefault();
      drop.classList.remove("is-dragging");
    });
  }
  drop.addEventListener("drop", async (event) => {
    try {
      await uploadReferenceFile(slot, event.dataTransfer?.files?.[0]);
    } catch (error) {
      sessionStatus.textContent = `reference error: ${error.message}`;
    }
  });
}

function makeNewCharacter() {
  const id = `character_${Date.now().toString(36)}`;
  characters[id] = {
    id,
    name: "New Character",
    systemPrompt: "",
    ttsCaption: ttsCaption.value || "",
    referencePath: mainReferencePath || "",
    portrait: "/expressions/neutral.png",
    expressions: {
      neutral: ["/expressions/neutral.png"],
    },
  };
  editingCharacterId = id;
  refreshCharacterSelectors();
  renderCharacterEditor();
}

function updateEditingCharacter() {
  const character = characterById(editingCharacterId);
  if (!character) return;
  character.name = editCharacterName.value.trim() || character.id;
  character.systemPrompt = editSystemPrompt.value;
  character.ttsCaption = editTtsCaption.value;
  refreshCharacterSelectors();
  syncActiveCharacterState();
}

function addExpressionSlotForEditingCharacter() {
  const character = characterById(editingCharacterId);
  if (!character) return;
  const key = newExpressionName.value.trim().replace(/[^0-9A-Za-z_-]+/g, "_") || "neutral";
  character.expressions = character.expressions || {};
  character.expressions[key] = character.expressions[key] || [];
  newExpressionName.value = "";
  renderExpressionEditor();
  editExpressionSelect.value = key;
  renderExpressionThumbs();
}

async function uploadExpressionImage(file) {
  const character = characterById(editingCharacterId);
  if (!character || !file) return;
  const expression = editExpressionSelect.value || "neutral";
  expressionImageStatus.textContent = "uploading...";
  const dataBase64 = await fileToDataUrl(file);
  const res = await fetch("/api/character-image", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({
      characterId: character.id,
      expression,
      name: file.name,
      type: file.type,
      dataBase64,
    }),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  character.expressions = character.expressions || {};
  character.expressions[expression] = character.expressions[expression] || [];
  character.expressions[expression].push(data.url);
  if (expression === "neutral" || !character.portrait) {
    character.portrait = data.url;
  }
  renderExpressionEditor();
  syncActiveCharacterState();
}

async function uploadExpressionImages(files) {
  const list = [...(files || [])];
  if (!list.length) return;
  for (const file of list) {
    await uploadExpressionImage(file);
  }
  sessionStatus.textContent = `added ${list.length} expression image${list.length > 1 ? "s" : ""}`;
}

function installImageDrop(drop, input, chooseButton) {
  chooseButton.addEventListener("click", () => input.click());
  input.addEventListener("change", async () => {
    try {
      await uploadExpressionImages(input.files);
    } catch (error) {
      sessionStatus.textContent = `image error: ${error.message}`;
    } finally {
      input.value = "";
    }
  });
  for (const eventName of ["dragenter", "dragover"]) {
    drop.addEventListener(eventName, (event) => {
      event.preventDefault();
      drop.classList.add("is-dragging");
    });
  }
  for (const eventName of ["dragleave", "drop"]) {
    drop.addEventListener(eventName, (event) => {
      event.preventDefault();
      drop.classList.remove("is-dragging");
    });
  }
  drop.addEventListener("drop", async (event) => {
    try {
      await uploadExpressionImages(event.dataTransfer?.files);
    } catch (error) {
      sessionStatus.textContent = `image error: ${error.message}`;
    }
  });
}

function characterPayload() {
  return {
    version: 1,
    activeMainId: activeMainCharacterId,
    activeSecondId: activeSecondCharacterId,
    characters: characterList(),
  };
}

function applyCharacterProfile(profile) {
  characters = {};
  for (const character of profile.characters || []) {
    if (character?.id) {
      characters[character.id] = character;
    }
  }
  activeMainCharacterId = profile.activeMainId || Object.keys(characters)[0] || "rinon";
  activeSecondCharacterId = profile.activeSecondId || Object.keys(characters)[1] || activeMainCharacterId;
  editingCharacterId = editingCharacterId && characters[editingCharacterId] ? editingCharacterId : activeMainCharacterId;
  refreshCharacterSelectors();
  syncActiveCharacterState();
  renderCharacterEditor();
}

async function loadCharacters() {
  const res = await fetch("/api/characters");
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  applyCharacterProfile(data);
}

async function saveCharacters() {
  updateEditingCharacter();
  const res = await fetch("/api/characters", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify(characterPayload()),
  });
  const data = await res.json();
  if (!res.ok) throw new Error(data.error || res.statusText);
  applyCharacterProfile(data);
  sessionStatus.textContent = `saved ${data.characters?.length || 0} characters`;
}

function sessionPayload() {
  return {
    settings: {
      systemPrompt: systemPrompt.value,
      mainCharacterName,
      secondCharacterName,
      activeMainCharacterId,
      activeSecondCharacterId,
      userAddress: userAddress.value,
      ttsCaption: ttsCaption.value,
      secondSystemPrompt: secondSystemPrompt.value,
      secondTtsCaption: secondTtsCaption.value,
      referencePath: mainReferencePath,
      secondReferencePath,
      contextLimit: Number(contextLimit.value || 8200),
      model: modelSelect.value,
      steps: Number(stepsInput.value || 12),
      speechRate: speechRate.value,
      replyLength: replyLength.value,
      autoEmoji: autoEmoji.checked,
      webSearch: webSearch.checked,
      twoPlayerMode: twoPlayerMode.checked,
      twoOnlyMode: twoOnlyMode.checked,
      emojiStyle: emojiStyleSelect.value,
      emojiCustom: emojiCustom.value,
    },
    history,
  };
}

function renderHistory(items) {
  history.length = 0;
  messagesEl.innerHTML = "";
  lastContextStats = null;
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
  autoMode = false;
  autoPending = false;
  lastContextStats = null;
  autoWebContext = "";
  autoWebQuery = "";
  autoWebResults = [];
  history.length = 0;
  messagesEl.innerHTML = "";
  queue = [];
  player.pause();
  player.removeAttribute("src");
  player.load();
  audioSaveStatus.textContent = "no audio";
  speaking.textContent = "ready";
  secondSpeaking.textContent = "standby";
  setSpeakingState(false);
  setExpression("neutral");
  setInteractionLocked(false);
  updateAutoControls();
  sessionStatus.textContent = "context cleared";
  updateContextUsage();
}

function applySession(profile) {
  const settings = profile.settings || {};
  if (settings.activeMainCharacterId && characters[settings.activeMainCharacterId]) {
    activeMainCharacterId = settings.activeMainCharacterId;
  }
  if (settings.activeSecondCharacterId && characters[settings.activeSecondCharacterId]) {
    activeSecondCharacterId = settings.activeSecondCharacterId;
  }
  mainCharacterName = settings.mainCharacterName || mainCharacterName || DEFAULT_MAIN_CHARACTER_NAME;
  secondCharacterName = settings.secondCharacterName || secondCharacterName || DEFAULT_SECOND_CHARACTER_NAME;
  mainReferencePath = settings.referencePath || mainReferencePath;
  secondReferencePath = settings.secondReferencePath || secondReferencePath;
  if (settings.systemPrompt) systemPrompt.value = settings.systemPrompt;
  userAddress.value = settings.userAddress || userAddress.value || "あなた";
  if (settings.ttsCaption) ttsCaption.value = settings.ttsCaption;
  if (settings.secondSystemPrompt) secondSystemPrompt.value = settings.secondSystemPrompt;
  if (settings.secondTtsCaption) secondTtsCaption.value = settings.secondTtsCaption;
  if (secondSystemPrompt.value.startsWith("2Pは")) {
    secondSystemPrompt.value = secondSystemPrompt.value.replace(/^2Pは/, `${secondCharacterName}は`);
  }
  if (settings.contextLimit) {
    contextLimit.value = settings.contextLimit;
    contextLimit.dataset.touched = "1";
  }
  updateContextUsage();
  setSelectValue(modelSelect, settings.model);
  if (settings.steps) stepsInput.value = settings.steps;
  setSpeechRate(settings.speechRate);
  if (settings.replyLength) replyLength.value = settings.replyLength;
  autoEmoji.checked = Boolean(settings.autoEmoji ?? true);
  webSearch.checked = Boolean(settings.webSearch ?? false);
  twoPlayerMode.checked = Boolean(settings.twoPlayerMode ?? false);
  twoOnlyMode.checked = Boolean(settings.twoOnlyMode ?? false);
  refreshCharacterSelectors();
  syncActiveCharacterState();
  updateTwoPlayerMode();
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

function playQueue(items, speaker = activeStage().speaker, options = {}) {
  const nextItems = [...items].map((item) => ({ ...item, speaker }));
  const isAudioActive = Boolean(player.currentSrc) && !player.paused && !player.ended;
  if (options.append && isAudioActive) {
    queue.push(...nextItems);
    return;
  }
  queue = options.append ? [...queue, ...nextItems] : nextItems;
  playbackSpeaker = speaker;
  if (queue.length === 0) {
    setInteractionLocked(false);
    return;
  }
  playNext();
}

function hasBufferedOtherSpeaker(speaker) {
  return queue.some((item) => (item.speaker || speaker) !== speaker);
}

function playNext() {
  const next = queue.shift();
  if (!next) {
    speaking.textContent = "ready";
    secondSpeaking.textContent = "standby";
    setSpeakingState(false);
    setExpression("neutral");
    setSecondExpression("neutral");
    setInteractionLocked(false);
    if (autoMode && !autoPending) {
      continueAutoConversation();
    }
    return;
  }
  playbackSpeaker = next.speaker || playbackSpeaker;
  updateAudioPan(playbackSpeaker);
  if (next.deferredMessage) {
    addMessage("assistant", next.deferredMessage.reply, next.deferredMessage.meta);
  }
  if (playbackSpeaker === mainCharacterName) {
    setExpression(next.expression || "neutral");
  } else if (playbackSpeaker === secondCharacterName) {
    setSecondExpression(next.expression || "neutral");
  }
  setStageStatus("speaking", playbackSpeaker);
  setSpeakingState(true, playbackSpeaker);
  player.src = next.url;
  audioSaveStatus.textContent = "save ready";
  player.play().catch(() => {
    setStageStatus("tap play", playbackSpeaker);
    setSpeakingState(false);
  });
  if (autoMode && !autoPending && !hasBufferedOtherSpeaker(playbackSpeaker)) {
    window.setTimeout(() => continueAutoConversation(), 0);
  }
}

player.addEventListener("ended", playNext);

function speakerForExternalEvent(event) {
  if (event.speakerSlot === "second") {
    if (!twoPlayerMode.checked) {
      twoPlayerMode.checked = true;
      updateTwoPlayerMode();
    }
    return secondCharacterName;
  }
  return mainCharacterName;
}

function handleExternalSpeakEvent(event) {
  const audios = Array.isArray(event.audios) ? event.audios : [];
  if (!audios.length) return;
  const speaker = speakerForExternalEvent(event);
  const timing = audios.map((item) => `${item.elapsed}s`).join(", ");
  const style = event.emojiStyle ? ` / style ${event.emojiStyle}` : "";
  const sourceSpeaker = event.speaker ? ` from ${event.speaker}` : "";
  const meta = `external speak${sourceSpeaker}${style} / pose ${event.expression || "neutral"} / tts ${timing}`;
  addMessage("assistant", event.text || audios.map((item) => item.text).join(""), meta);
  playQueue(audios, speaker, { append: true });
}

async function primeExternalSpeakEvents() {
  try {
    const res = await fetch("/api/speak-events?after=latest");
    const data = await res.json();
    if (res.ok) {
      externalSpeakLastId = Number(data.latestId || 0);
    }
  } catch {
    externalSpeakLastId = 0;
  }
}

async function pollExternalSpeakEvents() {
  if (externalSpeakPolling) return;
  externalSpeakPolling = true;
  try {
    const res = await fetch(`/api/speak-events?after=${externalSpeakLastId}`);
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    const events = Array.isArray(data.events) ? data.events : [];
    for (const event of events) {
      externalSpeakLastId = Math.max(externalSpeakLastId, Number(event.id || 0));
      handleExternalSpeakEvent(event);
    }
    externalSpeakLastId = Math.max(externalSpeakLastId, Number(data.latestId || 0));
  } catch {
    // Keep this quiet; normal chat should not be interrupted by a polling miss.
  } finally {
    externalSpeakPolling = false;
  }
}

async function refreshStatus() {
  try {
    const res = await fetch("/api/status");
    const data = await res.json();
    const diagnostics = data.diagnostics || {};
    lmStatus.textContent = data.models.length
      ? `${data.models.length} models`
      : `not detected: ${data.lmStudioUrl}`;
    if (data.contextLimit && !contextLimit.dataset.touched) {
      contextLimit.value = data.contextLimit;
    }
    updateContextUsage();
    if (data.ttsCaption && !ttsCaption.dataset.touched) {
      ttsCaption.value = data.ttsCaption;
    }
    mainReferencePath = mainReferencePath || data.reference || "";
    secondReferencePath = secondReferencePath || data.luviaReference || "";
    renderCharacterEditor();
    if (data.irodoriReady) {
      const remoteLabel = diagnostics.remoteLuviaEnabled ? " / 2P remote on" : " / 2P local";
      irodoriStatus.textContent = `${data.referenceExists ? "refs ready" : "ref missing"} / ${data.irodoriRoot}${remoteLabel}`;
    } else {
      const missing = [];
      if (!diagnostics.gitExists) missing.push("git");
      if (!diagnostics.uvExists) missing.push("uv");
      if (!diagnostics.irodoriRootExists) missing.push("Irodori");
      if (diagnostics.irodoriRootExists && !diagnostics.irodoriPythonExists) missing.push("Irodori venv");
      irodoriStatus.textContent = `setup needed: ${missing.join(", ") || data.irodoriRoot}`;
    }
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

async function sendChatTurn({
  message,
  visibleUserText = message,
  speaker = activeStage().speaker,
  isAuto = false,
  allowWhileLocked = false,
  backgroundAuto = false,
  webSearchNow = false,
  webContext = "",
  webTopic = "",
}) {
  if (interactionLocked && !allowWhileLocked) return false;
  const text = String(message || "").trim();
  if (!text) return false;
  const historyBeforeSend = [...history];
  if (visibleUserText) {
    addMessage("user", visibleUserText);
    history.push({ role: "user", content: visibleUserText });
  }
  updateContextUsage();
  if (!backgroundAuto) {
    messageInput.value = "";
  }
  setActiveSpeaker(speaker, isAuto || autoMode);
  if (!backgroundAuto) {
    setInteractionLocked(true, "Wait");
    setStageStatus("thinking", speaker);
    setSpeakingState(false, speaker);
    if (speaker === mainCharacterName) setExpression("soft");
  } else {
    sessionStatus.textContent = `auto thinking: ${speaker}`;
  }

  try {
    const stage = activeStage(speaker);
    const res = await fetch("/api/chat", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        message: text,
        history: historyBeforeSend,
        model: modelSelect.value,
        steps: Number(stepsInput.value || 12),
        speechRate: speechRate.value,
        replyLength: replyLength.value,
        speaker: stage.speaker,
        speakerSlot: stage.slot,
        systemPrompt: stage.systemPrompt,
        userAddress: userAddress.value,
        ttsCaption: stage.ttsCaption,
        secondSystemPrompt: secondSystemPrompt.value,
        secondTtsCaption: secondTtsCaption.value,
        referencePath: stage.slot === "main" ? stage.referencePath : mainReferencePath,
        secondReferencePath: stage.slot === "second" ? stage.referencePath : secondReferencePath,
        twoPlayerMode: twoPlayerMode.checked,
        twoOnlyMode: twoPlayerMode.checked && twoOnlyMode.checked,
        contextLimit: Number(contextLimit.value || 8200),
        emojiStyle: autoEmoji.checked ? "" : currentEmojiStyle(),
        autoEmoji: autoEmoji.checked,
        webSearch: webSearchNow || (webSearch.checked && speaker === mainCharacterName && !isAuto),
        webContext,
        webTopic,
        noDialogue: autoNoDialogue || wantsNoDialogue(text),
      }),
    });
    const data = await res.json();
    if (!res.ok) throw new Error(data.error || res.statusText);
    lastContextStats = data.contextStats || lastContextStats;
    if (autoMode && data.webContext) {
      autoWebContext = data.webContext;
      autoWebQuery = data.webQuery || "";
      autoWebResults = data.webResults || [];
    }
    const timing = data.audios.map((item) => `${item.elapsed}s`).join(", ");
    const style = data.emojiStyle
      ? ` / ${data.autoEmoji && data.llmEmojiStyle ? "auto style" : "style"} ${data.emojiStyle}`
      : "";
    const webQuery = String(data.webQuery || "");
    const webQueryLabel = webQuery.length > 32 ? `${webQuery.slice(0, 31)}…` : webQuery;
    const webMeta = data.webSearch || data.webContext
      ? ` / web ${data.webSearch ? (data.webResults || []).length : "memo"}${webQueryLabel ? ` q:${webQueryLabel}` : ""}`
      : "";
    const paceMeta = data.speechRate === "fast" ? " / pace fast" : "";
    const assistantMeta = `${data.speaker || mainCharacterName} / ${data.model} / ${data.replyLength}${style}${webMeta}${paceMeta} / pose ${data.expression} / tts ${timing}`;
    if (!backgroundAuto) {
      addMessage("assistant", data.reply, assistantMeta);
    } else if (data.audios.length) {
      data.audios[0] = {
        ...data.audios[0],
        deferredMessage: {
          reply: data.reply,
          meta: assistantMeta,
        },
      };
    }
    history.push({ role: "assistant", content: `${data.speaker || speaker}: ${data.reply}` });
    lastAssistantSpeaker = data.speaker || speaker;
    lastAssistantText = data.reply;
    updateContextUsage();
    playQueue(data.audios, data.speaker || speaker, { append: backgroundAuto });
    return true;
  } catch (error) {
    autoMode = false;
    autoPending = false;
    addMessage("assistant", `エラー: ${error.message}`);
    setStageStatus("error", speaker);
    if (!backgroundAuto) {
      setInteractionLocked(false);
    }
    updateAutoControls();
    return false;
  }
}

composer.addEventListener("submit", async (event) => {
  event.preventDefault();
  const text = messageInput.value.trim();
  if (!text) return;
  if (autoMode) {
    queueAutoTopic(text);
    return;
  }
  if (interactionLocked) return;
  await sendChatTurn({
    message: text,
    visibleUserText: text,
    speaker: activeStage().speaker,
    isAuto: false,
  });
});

async function startAutoConversation() {
  if (interactionLocked || autoMode || !twoPlayerMode.checked) return;
  const topic = messageInput.value.trim();
  if (!topic) {
    sessionStatus.textContent = "enter a topic first";
    return;
  }
  autoMode = true;
  autoPending = false;
  updateTwoPlayerMode();
  autoNextSpeaker = mainCharacterName;
  lastAssistantSpeaker = "";
  lastAssistantText = "";
  autoTopic = topic;
  autoTopicQueue = [];
  autoWebContext = "";
  autoWebQuery = "";
  autoWebResults = [];
  autoTurnCount = 0;
  autoNoDialogue = wantsNoDialogue(topic);
  updateAutoControls();
  sessionStatus.textContent = "auto running";
  const firstSpeaker = autoNextSpeaker;
  autoNextSpeaker = otherSpeaker(firstSpeaker);
  autoTurnCount += 1;
  const firstAutoMessage = autoNoDialogue
    ? `${twoOnlyGuidance()}${noDialogueGuidance()}お題: ${autoTopic}\nこれは2人の自動進行の第${autoTurnCount}ターンです。通常の会話として返さず、発声・吐息・擬音の強弱、間、苦しさ、気持ちよさの変化だけで少し展開してください。`
    : `${twoOnlyGuidance()}お題: ${autoTopic}\nこれは2人の自動会話の第${autoTurnCount}ターンです。お題を会話の中心に置き、結論へ急がず、相手が次に返しやすい問い・感想・小さなズレを残して始めてください。`;
  await sendChatTurn({
    message: firstAutoMessage,
    visibleUserText: `お題: ${topic}`,
    speaker: firstSpeaker,
    isAuto: true,
    webSearchNow: webSearch.checked,
    webTopic: topic,
  });
}

async function continueAutoConversation() {
  if (!autoMode || autoPending) return;
  autoPending = true;
  const speaker = autoNextSpeaker;
  autoNextSpeaker = otherSpeaker(speaker);
  autoTurnCount += 1;
  const queuedTopic = consumeQueuedAutoTopic();
  const shouldRefreshWeb = Boolean(queuedTopic && webSearch.checked);
  sessionStatus.textContent = queuedTopic ? `auto: ${speaker} / new topic` : `auto: ${speaker}`;
  const partner = otherSpeaker(speaker);
  const previousLine = lastAssistantText
    ? `直前に${partner}がこう言いました。\n「${lastAssistantText}」\n`
    : "";
  const topicLine = queuedTopic
    ? `ここから新しいお題に切り替えます。新しいお題は「${autoTopic}」です。第${autoTurnCount}ターンとして、直前の発言を受けつつ、この新しいお題へ自然に寄せてください。\n`
    : autoTopic
      ? `会話のお題は「${autoTopic}」です。第${autoTurnCount}ターンとして、このお題から離れすぎず、直前の発言を受けて少しだけ展開を進めてください。\n`
      : "";
  const nextAutoMessage = autoNoDialogue
    ? `${twoOnlyGuidance()}${noDialogueGuidance()}${queuedTopic ? "ここから新しいお題に切り替えます。" : ""}会話のお題は「${autoTopic}」です。第${autoTurnCount}ターンです。直前の発声を受けて、普通のセリフではなく、発声・吐息・擬音の流れだけを少し変化させて続けてください。呼びかけ、質問、説明、選択肢提示は禁止です。`
    : `${twoOnlyGuidance()}${topicLine}${previousLine}あなたは${speaker}です。${partner}の発言を受けて、${partner}に返す一言として自然に会話を続けてください。単純な相槌で終わらせず、前の発言から一歩だけ発展させてください。新しい情報、疑問、軽い反論、感情の変化のどれかを少し入れて、次の発言につながる余韻を残してください。`;
  try {
    await sendChatTurn({
      message: nextAutoMessage,
      visibleUserText: "",
      speaker,
      isAuto: true,
      allowWhileLocked: true,
      backgroundAuto: true,
      webSearchNow: shouldRefreshWeb,
      webContext: shouldRefreshWeb ? "" : autoWebContext,
      webTopic: shouldRefreshWeb ? queuedTopic : "",
    });
  } finally {
    autoPending = false;
    updateAutoControls();
  }
}

function stopAutoConversation() {
  autoMode = false;
  autoPending = false;
  autoTopic = "";
  autoTopicQueue = [];
  autoWebContext = "";
  autoWebQuery = "";
  autoWebResults = [];
  autoTurnCount = 0;
  autoNoDialogue = false;
  updateAutoControls();
  sessionStatus.textContent = interactionLocked ? "auto stopping" : "auto stopped";
}

autoEmoji.addEventListener("change", refreshEmojiInputs);
twoPlayerMode.addEventListener("change", updateTwoPlayerMode);
openOptionsButton.addEventListener("click", openOptions);
closeOptionsButton.addEventListener("click", closeOptions);
optionsModal.addEventListener("click", (event) => {
  if (event.target === optionsModal) {
    closeOptions();
  }
});
document.addEventListener("keydown", (event) => {
  if (event.key === "Escape" && !optionsModal.hidden) {
    closeOptions();
  }
});
mainCharacterSelect.addEventListener("change", () => {
  activeMainCharacterId = mainCharacterSelect.value;
  syncActiveCharacterState();
});
secondCharacterSelect.addEventListener("change", () => {
  activeSecondCharacterId = secondCharacterSelect.value;
  syncActiveCharacterState();
});
editCharacterSelect.addEventListener("change", () => {
  editingCharacterId = editCharacterSelect.value;
  renderCharacterEditor();
});
newCharacterButton.addEventListener("click", makeNewCharacter);
loadCharactersButton.addEventListener("click", async () => {
  try {
    await loadCharacters();
    sessionStatus.textContent = `loaded ${characterList().length} characters`;
  } catch (error) {
    sessionStatus.textContent = `character load error: ${error.message}`;
  }
});
saveCharactersButton.addEventListener("click", async () => {
  try {
    await saveCharacters();
  } catch (error) {
    sessionStatus.textContent = `character save error: ${error.message}`;
  }
});
for (const input of [editCharacterName, editSystemPrompt, editTtsCaption]) {
  input.addEventListener("input", updateEditingCharacter);
}
for (const button of speechRateButtons) {
  button.addEventListener("click", () => setSpeechRate(button.dataset.rate));
}
editExpressionSelect.addEventListener("change", renderExpressionThumbs);
addExpressionSlot.addEventListener("click", addExpressionSlotForEditingCharacter);
installReferenceDrop(editReferenceDrop, editReferenceFile, editReferenceChoose, "edit");
installImageDrop(expressionImageDrop, expressionImageFile, expressionImageChoose);
shutdownAppButton.addEventListener("click", async () => {
  const ok = window.confirm("IrodoriTTS UI とこのチャットアプリを終了します。よろしいですか？");
  if (!ok) return;
  shutdownAppButton.disabled = true;
  shutdownAppButton.textContent = "Stopping...";
  sessionStatus.textContent = "shutting down";
  try {
    await fetch("/api/shutdown", { method: "POST" });
    document.body.classList.add("is-shutdown");
    sessionStatus.textContent = "stopped";
  } catch (error) {
    shutdownAppButton.disabled = false;
    shutdownAppButton.textContent = "終了";
    sessionStatus.textContent = `shutdown error: ${error.message}`;
  }
});
autoStartButton.addEventListener("click", () => {
  if (autoMode) {
    stopAutoConversation();
  } else {
    startAutoConversation();
  }
});
contextLimit.addEventListener("input", () => {
  contextLimit.dataset.touched = "1";
  updateContextUsage();
});

ttsCaption.addEventListener("input", () => {
  ttsCaption.dataset.touched = "1";
});

secondTtsCaption.addEventListener("input", () => {
  secondTtsCaption.dataset.touched = "1";
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
        label: twoPlayerMode.checked ? "2p" : "rinon",
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
  await loadCharacters();
  updateTwoPlayerMode();
  await refreshStatus();
  await loadSession(true);
  await primeExternalSpeakEvents();
  window.setInterval(pollExternalSpeakEvents, 1500);
}

initialize().catch((error) => {
  sessionStatus.textContent = `init error: ${error.message}`;
});
