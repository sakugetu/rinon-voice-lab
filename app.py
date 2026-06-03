from __future__ import annotations

import json
import mimetypes
import os
import re
import shutil
import sys
import threading
import time
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from urllib.parse import unquote, urlparse


APP_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = APP_ROOT / "static"
LOG_ROOT = APP_ROOT / "logs"
CHAT_LOG_PATH = LOG_ROOT / "chat.jsonl"
PROFILE_ROOT = APP_ROOT / "profiles"
SESSION_PROFILE_PATH = PROFILE_ROOT / "latest_session.json"
SAVED_AUDIO_ROOT = APP_ROOT / "saved_audio"
IRODORI_ROOT = Path(os.environ.get("IRODORI_ROOT", r"H:\AI\Irodori-TTS"))
LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1").rstrip("/")
DEFAULT_MODEL = os.environ.get("LM_STUDIO_MODEL", "gemma-4-31b-it")
DEFAULT_CONTEXT_LIMIT = int(os.environ.get("LM_STUDIO_CONTEXT_LIMIT", "8200"))

IRODORI_CHECKPOINT = os.environ.get(
    "IRODORI_CHECKPOINT", "Aratako/Irodori-TTS-600M-v3-VoiceDesign"
)
IRODORI_CAPTION = os.environ.get(
    "IRODORI_CAPTION",
    (
        "Native Japanese young adult woman, cute anime assistant voice, "
        "warm and intimate conversational acting, slightly teasing little-devil smile, "
        "soft breath, gentle emotional nuance, clear pronunciation, clean studio sound."
    ),
)
IRODORI_REF_WAV = Path(
    os.environ.get(
        "IRODORI_REF_WAV",
        str(APP_ROOT / "static" / "reference" / "tokyo_ref.wav"),
    )
)

Irodori_lock = threading.Lock()
Irodori_module = None
Emoji_items_cache = None


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    if not raw:
        return {}
    return json.loads(raw.decode("utf-8"))


def split_sentences(text: str, limit: int = 8) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    parts = re.split(r"(?<=[。！？!?])\s*", text)
    chunks = [part.strip() for part in parts if part.strip()]
    if len(chunks) <= limit:
        return chunks
    return chunks[: limit - 1] + ["".join(chunks[limit - 1 :])]


def load_emoji_items() -> list[dict[str, str]]:
    global Emoji_items_cache
    if Emoji_items_cache is not None:
        return Emoji_items_cache
    sys.path.insert(0, str(IRODORI_ROOT))
    from irodori_tts.gradio_emoji_palette import EMOJI_PALETTE_ITEMS

    Emoji_items_cache = [
        {
            "emoji": item.emoji,
            "label": item.label,
            "description": item.description,
        }
        for item in EMOJI_PALETTE_ITEMS
    ]
    return Emoji_items_cache


def apply_emoji_style(text: str, emoji_style: str) -> str:
    text = strip_irodori_style_marks(text)
    emoji_style = str(emoji_style or "").strip()
    if not emoji_style:
        return text
    return f"{emoji_style}{text}"


def expression_for_emoji(emoji_style: str) -> str:
    emoji = str(emoji_style or "").strip()
    if not emoji:
        return "neutral"
    mapping = {
        "👂": "soft",
        "😮‍💨": "sigh",
        "⏸️": "pause",
        "🤭": "teasing",
        "🥵": "breathless",
        "📢": "broadcast",
        "😏": "teasing",
        "🥺": "worried",
        "🌬️": "breathless",
        "😮": "gasp",
        "👅": "muffled",
        "💋": "muffled",
        "🫶": "tender",
        "😭": "sad",
        "😱": "surprised",
        "😪": "sleepy",
        "😴": "sleepy",
        "⏩": "fast",
        "📞": "phone",
        "🐢": "sleepy",
        "🥤": "swallow",
        "🤧": "cough",
        "😒": "exasperated",
        "😰": "worried",
        "😆": "happy",
        "💥": "strong",
        "😠": "angry",
        "😲": "gasp",
        "🥱": "yawn",
        "😖": "worried",
        "😟": "worried",
        "🫣": "shy",
        "🙄": "exasperated",
        "😊": "happy",
        "😎": "smug",
        "👌": "neutral",
        "🙏": "pleading",
        "🥴": "muffled",
        "🎵": "humming",
        "🤐": "pause",
        "😌": "tender",
        "🤔": "question",
        "💪": "strong",
        "👃": "sniff",
        "📖": "narration",
    }
    return mapping.get(emoji, "neutral")


def expression_assets() -> dict[str, str | list[str]]:
    names = [
        "neutral",
        "happy",
        "surprised",
        "soft",
        "angry",
        "worried",
        "sad",
        "shy",
        "narration",
        "fast",
        "sleepy",
        "phone",
        "echo",
        "muffled",
        "throat",
        "strong",
        "teasing",
        "pleading",
        "exasperated",
        "smug",
        "sigh",
        "gasp",
        "breathless",
        "yawn",
        "humming",
        "swallow",
        "cough",
        "sniff",
        "pause",
        "question",
        "tender",
        "broadcast",
    ]
    assets: dict[str, str | list[str]] = {}
    expression_dir = STATIC_ROOT / "expressions"
    for name in names:
        variants = sorted(expression_dir.glob(f"{name}*.png"))
        urls = [f"/expressions/{path.name}" for path in variants if not path.name.endswith("_sheet.png")]
        assets[name] = urls if len(urls) > 1 else (urls[0] if urls else f"/expressions/{name}.png")
    return assets


def append_chat_log(record: dict) -> None:
    LOG_ROOT.mkdir(parents=True, exist_ok=True)
    with CHAT_LOG_PATH.open("a", encoding="utf-8") as f:
        f.write(json.dumps(record, ensure_ascii=False) + "\n")


def chat_log_summary(limit: int = 20) -> dict:
    expression_counts: dict[str, int] = {}
    emoji_counts: dict[str, int] = {}
    recent: list[dict] = []
    total = 0
    if not CHAT_LOG_PATH.exists():
        return {
            "path": str(CHAT_LOG_PATH),
            "total": 0,
            "expressions": [],
            "emojis": [],
            "recent": [],
        }
    for line in CHAT_LOG_PATH.read_text(encoding="utf-8").splitlines():
        if not line.strip():
            continue
        try:
            item = json.loads(line)
        except json.JSONDecodeError:
            continue
        total += 1
        expression = str(item.get("expression") or "neutral")
        emoji = str(item.get("emojiStyle") or "")
        expression_counts[expression] = expression_counts.get(expression, 0) + 1
        if emoji:
            emoji_counts[emoji] = emoji_counts.get(emoji, 0) + 1
        recent.append(
            {
                "time": item.get("time"),
                "user": item.get("user"),
                "reply": item.get("reply"),
                "emojiStyle": emoji,
                "expression": expression,
                "chunks": item.get("chunkCount"),
            }
        )
        if len(recent) > limit:
            recent = recent[-limit:]
    return {
        "path": str(CHAT_LOG_PATH),
        "total": total,
        "expressions": sorted(
            ({"name": key, "count": value} for key, value in expression_counts.items()),
            key=lambda item: item["count"],
            reverse=True,
        ),
        "emojis": sorted(
            ({"emoji": key, "count": value} for key, value in emoji_counts.items()),
            key=lambda item: item["count"],
            reverse=True,
        ),
        "recent": recent,
    }


def sanitize_history(value: object) -> list[dict[str, str]]:
    if not isinstance(value, list):
        return []
    history: list[dict[str, str]] = []
    for item in value:
        if not isinstance(item, dict):
            continue
        role = str(item.get("role") or "")
        content = str(item.get("content") or "").strip()
        if role in {"user", "assistant"} and content:
            history.append({"role": role, "content": content})
    return history


def save_session_profile(payload: dict) -> dict:
    PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
    settings = payload.get("settings") if isinstance(payload.get("settings"), dict) else {}
    profile = {
        "version": 1,
        "savedAt": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
            "settings": {
                "systemPrompt": str(settings.get("systemPrompt") or ""),
                "ttsCaption": str(settings.get("ttsCaption") or IRODORI_CAPTION),
                "contextLimit": int(settings.get("contextLimit") or DEFAULT_CONTEXT_LIMIT),
                "model": str(settings.get("model") or DEFAULT_MODEL),
            "steps": int(settings.get("steps") or 12),
            "replyLength": str(settings.get("replyLength") or "normal"),
            "autoEmoji": bool(settings.get("autoEmoji", True)),
            "emojiStyle": str(settings.get("emojiStyle") or ""),
            "emojiCustom": str(settings.get("emojiCustom") or ""),
        },
        "history": sanitize_history(payload.get("history")),
    }
    SESSION_PROFILE_PATH.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return profile


def load_session_profile() -> dict:
    if not SESSION_PROFILE_PATH.exists():
        return {
            "exists": False,
            "path": str(SESSION_PROFILE_PATH),
            "settings": {},
            "history": [],
        }
    profile = json.loads(SESSION_PROFILE_PATH.read_text(encoding="utf-8"))
    if not isinstance(profile, dict):
        raise ValueError("saved profile is invalid")
    profile["exists"] = True
    profile["path"] = str(SESSION_PROFILE_PATH)
    profile["history"] = sanitize_history(profile.get("history"))
    return profile


def save_current_audio(payload: dict) -> dict:
    url = str(payload.get("url") or "").strip()
    parsed = urlparse(url)
    rel_url = parsed.path if parsed.scheme or parsed.netloc else url
    if not rel_url.startswith("/generated/"):
        raise ValueError("only generated app audio can be saved")
    source_name = Path(unquote(rel_url)).name
    source_path = (STATIC_ROOT / "generated" / source_name).resolve()
    generated_root = (STATIC_ROOT / "generated").resolve()
    if not str(source_path).startswith(str(generated_root)) or not source_path.exists():
        raise FileNotFoundError("audio file was not found")

    SAVED_AUDIO_ROOT.mkdir(parents=True, exist_ok=True)
    label = re.sub(r"[^0-9A-Za-z_-]+", "_", str(payload.get("label") or "rinon").strip())
    label = label.strip("_")[:40] or "rinon"
    saved_name = f"{time.strftime('%Y%m%d_%H%M%S')}_{label}_{source_path.name}"
    saved_path = SAVED_AUDIO_ROOT / saved_name
    shutil.copy2(source_path, saved_path)
    return {
        "ok": True,
        "path": str(saved_path),
        "url": f"/saved_audio/{saved_name}",
        "name": saved_name,
        "size": saved_path.stat().st_size,
    }


def build_emoji_choice_prompt() -> str:
    items = load_emoji_items()
    lines = [f"{item['emoji']} = {item['label']} / {item['description']}" for item in items]
    return "\n".join(lines)


def parse_lmstudio_reply(raw: str, allowed_emojis: set[str]) -> tuple[str, str]:
    text = raw.strip()
    fenced = re.search(r"```(?:json)?\s*(.*?)```", text, re.DOTALL)
    if fenced:
        text = fenced.group(1).strip()
    try:
        data = json.loads(text)
        reply = str(data.get("text") or data.get("reply") or "").strip()
        emoji = str(data.get("emoji") or "").strip()
        if reply:
            return reply, emoji if emoji in allowed_emojis else ""
    except Exception:
        pass
    return raw.strip(), ""


def strip_irodori_style_marks(text: str) -> str:
    cleaned = str(text or "")
    emojis = sorted((item["emoji"] for item in load_emoji_items()), key=len, reverse=True)
    for emoji in emojis:
        cleaned = cleaned.replace(emoji, "")
    return re.sub(r"\s+", " ", cleaned).strip()


def reply_style_for_length(reply_length: str) -> tuple[str, int, int]:
    mode = str(reply_length or "normal").strip().lower()
    if mode == "long":
        return "返答は6から10文くらいまで使って、自然な会話調で少し詳しく答えてください。", 1200, 10
    if mode == "short":
        return "返答は1から2文を基本にしてください。", 360, 3
    return "返答は3から5文くらいまで使って、自然な会話調で答えてください。", 720, 6


def trim_messages_for_context(messages: list[dict[str, str]], limit: int) -> list[dict[str, str]]:
    limit = max(1000, int(limit or DEFAULT_CONTEXT_LIMIT))
    kept: list[dict[str, str]] = []
    used = 0
    for item in reversed(messages):
        content = str(item.get("content") or "")
        cost = len(content) + 32
        if kept and used + cost > limit:
            break
        kept.append(item)
        used += cost
    return list(reversed(kept))


def request_lmstudio(
    messages: list[dict[str, str]],
    model: str | None,
    auto_emoji: bool,
    reply_length: str,
    character_prompt: str,
) -> tuple[str, str, str, int]:
    length_instruction, max_tokens, chunk_limit = reply_style_for_length(reply_length)
    emoji_instruction = ""
    if auto_emoji:
        emoji_instruction = (
            "\nIrodori-TTSの感情/発声スタイル絵文字を1つだけ選んでください。"
            "自然な通常発話ならemojiは空文字にしてください。"
            "選べる絵文字:\n"
            f"{build_emoji_choice_prompt()}\n"
            '必ずJSONだけで返してください: {"text":"返答本文","emoji":"絵文字または空文字"}'
        )
    payload = {
        "model": model or DEFAULT_MODEL,
        "messages": [
            {
                "role": "system",
                "content": (
                    "あなたは日本語で短く自然に返す会話相手です。"
                    "あなたは画面左のキャラクター、リノンとして話します。"
                    f"{character_prompt.strip()}\n"
                    f"{length_instruction}"
                    "思考過程は出さず、最終回答だけを出してください。 /no_think"
                    f"{emoji_instruction}"
                ),
            },
            *messages,
        ],
        "temperature": 0.7,
        "max_tokens": max_tokens,
        "stream": False,
    }
    req = urllib.request.Request(
        f"{LM_STUDIO_URL}/chat/completions",
        data=json_bytes(payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    with urllib.request.urlopen(req, timeout=90) as res:
        data = json.loads(res.read().decode("utf-8"))
    choice_message = data["choices"][0]["message"]
    content = str(choice_message.get("content") or "").strip()
    if not content:
        # Some local reasoning models can spend the whole budget in reasoning_content.
        # Return a visible explanation instead of silently handing an empty string to TTS.
        raise RuntimeError(
            "LM Studio returned empty assistant content. Try a non-reasoning model, "
            "or add /no_think to the prompt/model preset."
        )
    allowed_emojis = {item["emoji"] for item in load_emoji_items()}
    message, emoji = parse_lmstudio_reply(content, allowed_emojis) if auto_emoji else (content, "")
    message = strip_irodori_style_marks(message)
    if not message:
        raise RuntimeError("LM Studio returned only style marks and no speakable text.")
    model_used = data.get("model") or payload["model"]
    return message, model_used, emoji, chunk_limit


def ensure_irodori_module():
    global Irodori_module
    if Irodori_module is not None:
        return Irodori_module
    if not IRODORI_ROOT.exists():
        raise RuntimeError(f"Irodori root not found: {IRODORI_ROOT}")
    sys.path.insert(0, str(IRODORI_ROOT))
    old_cwd = Path.cwd()
    os.chdir(IRODORI_ROOT)
    try:
        import gradio_app_voicedesign as app_vd

        Irodori_module = app_vd
        return Irodori_module
    finally:
        os.chdir(old_cwd)


def synthesize_sentence(
    text: str,
    index: int,
    steps: int,
    emoji_style: str = "",
    caption: str = "",
) -> dict:
    module = ensure_irodori_module()
    styled_text = apply_emoji_style(text, emoji_style)
    voice_caption = str(caption or "").strip() or IRODORI_CAPTION
    old_cwd = Path.cwd()
    os.chdir(IRODORI_ROOT)
    try:
        with Irodori_lock:
            start = time.perf_counter()
            result = module._run_generation(
                IRODORI_CHECKPOINT,
                "cuda",
                "bf16",
                "cuda",
                "bf16",
                styled_text,
                voice_caption,
                str(IRODORI_REF_WAV) if IRODORI_REF_WAV.exists() else None,
                int(steps),
                1,
                "",
                "",
                1.0,
                "linear",
                -1.0,
                "independent",
                3.0,
                4.0,
                5.0,
                "",
                0.0,
                1.0,
                True,
                "",
                "",
                "",
                "",
                "",
                "",
                "",
            )
            elapsed = time.perf_counter() - start
    finally:
        os.chdir(old_cwd)

    detail = str(result[-2])
    match = re.search(r"saved\[1\]:\s*(.+)", detail)
    if not match:
        raise RuntimeError(f"Could not find generated wav path in Irodori result: {detail}")
    wav_path = (IRODORI_ROOT / match.group(1).strip()).resolve()
    out_dir = STATIC_ROOT / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"reply_{int(time.time() * 1000)}_{index:02d}.wav"
    public_path = out_dir / safe_name
    shutil.copy2(wav_path, public_path)
    return {
        "text": text,
        "ttsText": styled_text,
        "caption": voice_caption,
        "emojiStyle": emoji_style,
        "expression": expression_for_emoji(emoji_style),
        "url": f"/generated/{safe_name}",
        "elapsed": round(elapsed, 3),
        "source": str(wav_path),
    }


def get_models() -> list[str]:
    try:
        with urllib.request.urlopen(f"{LM_STUDIO_URL}/models", timeout=5) as res:
            data = json.loads(res.read().decode("utf-8"))
        return [item["id"] for item in data.get("data", []) if item.get("id")]
    except Exception:
        return []


class Handler(BaseHTTPRequestHandler):
    server_version = "IrodoriLMStudioChat/0.1"

    def send_json(self, status: int, payload: object) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/status":
            self.send_json(
                200,
                {
                    "lmStudioUrl": LM_STUDIO_URL,
                    "models": get_models(),
                    "contextLimit": DEFAULT_CONTEXT_LIMIT,
                    "irodoriRoot": str(IRODORI_ROOT),
                    "checkpoint": IRODORI_CHECKPOINT,
                    "ttsCaption": IRODORI_CAPTION,
                    "reference": str(IRODORI_REF_WAV),
                    "referenceExists": IRODORI_REF_WAV.exists(),
                    "emojis": load_emoji_items(),
                    "expressions": expression_assets(),
                },
            )
            return

        if parsed.path == "/api/log-summary":
            self.send_json(200, chat_log_summary())
            return

        if parsed.path == "/api/session":
            try:
                self.send_json(200, load_session_profile())
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return

        path = "/index.html" if parsed.path == "/" else parsed.path
        rel = Path(unquote(path.lstrip("/")))
        static_root = STATIC_ROOT.resolve()
        file_path = (STATIC_ROOT / rel).resolve()
        if parsed.path.startswith("/saved_audio/"):
            static_root = SAVED_AUDIO_ROOT.resolve()
            file_path = (SAVED_AUDIO_ROOT / Path(unquote(parsed.path)).name).resolve()
        if not str(file_path).startswith(str(static_root)) or not file_path.exists():
            self.send_error(404)
            return
        mime, _ = mimetypes.guess_type(str(file_path))
        data = file_path.read_bytes()
        self.send_response(200)
        self.send_header("Content-Type", mime or "application/octet-stream")
        self.send_header("Content-Length", str(len(data)))
        self.end_headers()
        self.wfile.write(data)

    def do_POST(self) -> None:
        parsed = urlparse(self.path)
        if parsed.path == "/api/session":
            try:
                profile = save_session_profile(read_json_body(self))
                self.send_json(
                    200,
                    {
                        "ok": True,
                        "path": str(SESSION_PROFILE_PATH),
                        "savedAt": profile["savedAt"],
                        "historyCount": len(profile["history"]),
                    },
                )
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return

        if parsed.path == "/api/save-audio":
            try:
                self.send_json(200, save_current_audio(read_json_body(self)))
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return

        if parsed.path != "/api/chat":
            self.send_error(404)
            return
        try:
            body = read_json_body(self)
            user_text = str(body.get("message", "")).strip()
            if not user_text:
                self.send_json(400, {"error": "message is required"})
                return
            history = body.get("history") if isinstance(body.get("history"), list) else []
            model = str(body.get("model") or "").strip() or None
            steps = int(body.get("steps") or 12)
            emoji_style = str(body.get("emojiStyle") or "").strip()
            auto_emoji = bool(body.get("autoEmoji", True))
            reply_length = str(body.get("replyLength") or "normal").strip()
            character_prompt = str(body.get("systemPrompt") or "").strip()
            tts_caption = str(body.get("ttsCaption") or IRODORI_CAPTION).strip()
            context_limit = int(body.get("contextLimit") or DEFAULT_CONTEXT_LIMIT)
            raw_messages = [
                item
                for item in history
                if isinstance(item, dict) and item.get("role") in {"user", "assistant"}
            ]
            raw_messages.append({"role": "user", "content": user_text})
            messages = trim_messages_for_context(raw_messages, context_limit)
            reply, model_used, llm_emoji, chunk_limit = request_lmstudio(
                messages,
                model,
                auto_emoji=auto_emoji,
                reply_length=reply_length,
                character_prompt=character_prompt,
            )
            effective_emoji = emoji_style or llm_emoji
            chunks = split_sentences(reply, limit=chunk_limit)
            audios = [
                synthesize_sentence(
                    chunk,
                    i,
                    steps=max(1, min(120, steps)),
                    emoji_style=effective_emoji,
                    caption=tts_caption,
                )
                for i, chunk in enumerate(chunks, start=1)
            ]
            append_chat_log(
                {
                    "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "user": user_text,
                    "reply": reply,
                    "model": model_used,
                    "replyLength": reply_length,
                    "emojiStyle": effective_emoji,
                    "llmEmojiStyle": llm_emoji,
                    "autoEmoji": auto_emoji,
                    "ttsCaption": tts_caption,
                    "expression": expression_for_emoji(effective_emoji),
                    "chunkCount": len(chunks),
                    "chunks": chunks,
                    "audios": [
                        {
                            "text": item.get("text"),
                            "ttsText": item.get("ttsText"),
                            "emojiStyle": item.get("emojiStyle"),
                            "expression": item.get("expression"),
                            "elapsed": item.get("elapsed"),
                            "url": item.get("url"),
                        }
                        for item in audios
                    ],
                }
            )
            self.send_json(
                200,
                {
                    "reply": reply,
                    "model": model_used,
                    "chunks": chunks,
                    "emojiStyle": effective_emoji,
                    "expression": expression_for_emoji(effective_emoji),
                    "llmEmojiStyle": llm_emoji,
                    "autoEmoji": auto_emoji,
                    "replyLength": reply_length,
                    "audios": audios,
                },
            )
        except urllib.error.URLError as exc:
            self.send_json(502, {"error": f"LM Studio request failed: {exc}"})
        except Exception as exc:
            self.send_json(500, {"error": str(exc)})

    def log_message(self, fmt: str, *args: object) -> None:
        print(f"[server] {self.address_string()} {fmt % args}", flush=True)


def main() -> None:
    host = os.environ.get("CHAT_HOST", "127.0.0.1")
    port = int(os.environ.get("CHAT_PORT", "7862"))
    STATIC_ROOT.mkdir(parents=True, exist_ok=True)
    (STATIC_ROOT / "generated").mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Irodori LM Studio chat: http://{host}:{port}/", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
