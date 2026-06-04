from __future__ import annotations

import base64
import json
import mimetypes
import os
import re
import shutil
import subprocess
import sys
import threading
import time
import uuid
import urllib.error
import urllib.request
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from html import unescape as html_unescape
from pathlib import Path
from urllib.parse import parse_qs, quote_plus, unquote, urlparse


APP_ROOT = Path(__file__).resolve().parent
STATIC_ROOT = APP_ROOT / "static"
LOG_ROOT = APP_ROOT / "logs"
CHAT_LOG_PATH = LOG_ROOT / "chat.jsonl"
PROFILE_ROOT = APP_ROOT / "profiles"
SESSION_PROFILE_PATH = PROFILE_ROOT / "latest_session.json"
CHARACTER_PROFILE_PATH = PROFILE_ROOT / "characters.json"
SAVED_AUDIO_ROOT = APP_ROOT / "saved_audio"
USER_REFERENCE_ROOT = STATIC_ROOT / "reference" / "user_refs"
LEGACY_CHARACTER_ROOT = APP_ROOT / "characters"
CHARACTER_ROOT = APP_ROOT / "Character"
IRODORI_ROOT = Path(os.environ.get("IRODORI_ROOT", r"H:\AI\Irodori-TTS"))
LM_STUDIO_URL = os.environ.get("LM_STUDIO_URL", "http://127.0.0.1:1234/v1").rstrip("/")
DEFAULT_MODEL = os.environ.get("LM_STUDIO_MODEL", "gemma-4-31b-it")
DEFAULT_CONTEXT_LIMIT = int(os.environ.get("LM_STUDIO_CONTEXT_LIMIT", "8200"))
LM_COMPACT_CONTEXT_LIMIT = int(os.environ.get("LM_COMPACT_CONTEXT_LIMIT", "4200"))
LM_RECENT_MESSAGE_COUNT = int(os.environ.get("LM_RECENT_MESSAGE_COUNT", "12"))
LM_SUMMARY_CHAR_LIMIT = int(os.environ.get("LM_SUMMARY_CHAR_LIMIT", "1400"))
WEB_SEARCH_TIMEOUT = int(os.environ.get("WEB_SEARCH_TIMEOUT", "12"))

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
LUVIA_REF_WAV = Path(
    os.environ.get(
        "LUVIA_REF_WAV",
        str(APP_ROOT / "static" / "reference" / "luvia_smoky_radio_pitchdown3_ref.wav"),
    )
)
LUVIA_REMOTE_TTS_HOST = os.environ.get("LUVIA_REMOTE_TTS_HOST", "shin@KSHIN-RYZEN4090")
LUVIA_REMOTE_IRODORI_ROOT = os.environ.get("LUVIA_REMOTE_IRODORI_ROOT", r"E:\AI\Irodori-TTS")
LUVIA_REMOTE_REF_WAV = os.environ.get(
    "LUVIA_REMOTE_REF_WAV",
    r"E:\AI\Irodori-TTS\remote_refs\luvia_smoky_radio_pitchdown3_ref.wav",
)
LUVIA_REMOTE_TTS_URL = os.environ.get(
    "LUVIA_REMOTE_TTS_URL",
    "http://192.168.68.59:7874",
).rstrip("/")
ALLOWED_REFERENCE_EXTENSIONS = {".wav", ".mp3", ".flac", ".m4a", ".ogg", ".aac"}
ALLOWED_IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".webp"}

Irodori_lock = threading.Lock()
Irodori_module = None
Emoji_items_cache = None
Luvia_remote_ref_cache: dict[str, str] = {}


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


def expression_asset_lists(root: Path, url_prefix: str) -> dict[str, list[str]]:
    assets: dict[str, list[str]] = {}
    if not root.exists():
        return assets
    for path in sorted(root.glob("*.png")):
        if path.name.endswith("_sheet.png") or path.name.endswith("_contact.png"):
            continue
        key = re.sub(r"_\d+$", "", path.stem)
        if key.startswith("luvia_"):
            key = key.removeprefix("luvia_")
        assets.setdefault(key, []).append(f"{url_prefix}/{path.name}")
    return assets


def default_character_profiles() -> dict:
    rinon_expressions = expression_asset_lists(STATIC_ROOT / "expressions", "/expressions")
    luvia_expressions = expression_asset_lists(
        STATIC_ROOT / "second_player" / "expressions",
        "/second_player/expressions",
    )
    return {
        "version": 1,
        "activeMainId": "rinon",
        "activeSecondId": "luvia",
        "characters": [
            {
                "id": "rinon",
                "name": "リノン",
                "systemPrompt": (
                    "リノンは20歳以上の、アニメ的で少し色っぽい日本語の女の子AI。"
                    "人なつっこく、気が利き、相手の反応を見ながら甘くからかったり照れたりする。"
                    "会話は自然で短めに返し、距離感は近いが、露骨すぎる性的描写や未成年っぽい振る舞いは避ける。"
                    "声は明るくやわらかく、少し小悪魔っぽい余裕と、ふとした照れを混ぜる。"
                ),
                "ttsCaption": IRODORI_CAPTION,
                "referencePath": str(IRODORI_REF_WAV),
                "portrait": "/expressions/neutral.png",
                "expressions": rinon_expressions,
            },
            {
                "id": "luvia",
                "name": "ルヴィア",
                "systemPrompt": (
                    "ルヴィアは20歳以上の、赤髪で勝ち気なアニメ的美少女AI。"
                    "リノンより少しストレートで、挑発的だが根は面倒見がよい。"
                    "会話では相手をからかいながらも、要点ははっきり伝える。"
                    "露骨すぎる性的描写や未成年っぽい振る舞いは避ける。"
                    "声は少し低めで明るく、元気で自信があり、いたずらっぽい笑みを含む。"
                ),
                "ttsCaption": (
                    "Native Japanese adult woman, smoky radio presenter voice, low feminine resonance, "
                    "confident lively tone, polished adult speaking style, restrained teasing confidence, "
                    "clean studio sound."
                ),
                "referencePath": str(LUVIA_REF_WAV),
                "portrait": "/second_player/expressions/luvia_neutral.png",
                "expressions": luvia_expressions,
            },
        ],
    }


def sanitize_character_id(value: object, fallback: str = "") -> str:
    raw = str(value or "").strip().lower()
    safe = re.sub(r"[^0-9a-z_-]+", "_", raw).strip("_")
    return safe[:48] or fallback or f"character_{uuid.uuid4().hex[:8]}"


def sanitize_expression_key(value: object, fallback: str = "neutral") -> str:
    return re.sub(r"[^0-9A-Za-z_-]+", "_", str(value or fallback)).strip("_") or fallback


def character_url(character_id: str, *parts: str) -> str:
    return "/".join(["/Character", character_id, *[part.strip("/\\") for part in parts if part]])


def local_path_for_asset_url(url: str) -> Path | None:
    text = str(url or "").strip()
    if not text.startswith("/"):
        return None
    if text.startswith("/Character/"):
        rel = Path(unquote(text.removeprefix("/Character/")))
        return (CHARACTER_ROOT / rel).resolve()
    if text.startswith("/characters/"):
        rel = Path(unquote(text.removeprefix("/characters/")))
        return (LEGACY_CHARACTER_ROOT / rel).resolve()
    rel = Path(unquote(text.lstrip("/")))
    return (STATIC_ROOT / rel).resolve()


def copy_character_asset(character_id: str, expression: str, url: str) -> str:
    text = str(url or "").strip()
    if text.startswith(f"/Character/{character_id}/"):
        return text
    src = local_path_for_asset_url(text)
    if not src or not src.exists() or src.suffix.lower() not in ALLOWED_IMAGE_EXTENSIONS:
        return text
    expression_key = sanitize_expression_key(expression)
    out_dir = CHARACTER_ROOT / character_id / "expressions" / expression_key
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / src.name
    if out_path.exists() and out_path.resolve() != src.resolve():
        if out_path.read_bytes() != src.read_bytes():
            out_path = out_dir / f"{src.stem}_{uuid.uuid4().hex[:6]}{src.suffix.lower()}"
    if not out_path.exists():
        shutil.copy2(src, out_path)
    return character_url(character_id, "expressions", expression_key, out_path.name)


def copy_character_reference(character_id: str, reference_path: str) -> str:
    raw = str(reference_path or "").strip()
    if not raw:
        return raw
    src = Path(raw)
    if not src.is_absolute():
        src = (APP_ROOT / src).resolve()
    if not src.exists() or src.suffix.lower() not in ALLOWED_REFERENCE_EXTENSIONS:
        return raw
    char_dir = (CHARACTER_ROOT / character_id).resolve()
    if str(src.resolve()).startswith(str(char_dir)):
        return str(src.resolve())
    out_dir = CHARACTER_ROOT / character_id / "reference"
    out_dir.mkdir(parents=True, exist_ok=True)
    out_path = out_dir / src.name
    if out_path.exists() and out_path.resolve() != src.resolve():
        if out_path.read_bytes() != src.read_bytes():
            out_path = out_dir / f"{src.stem}_{uuid.uuid4().hex[:6]}{src.suffix.lower()}"
    if not out_path.exists():
        shutil.copy2(src, out_path)
    return str(out_path.resolve())


def character_text_profile(character: dict) -> str:
    expressions = character.get("expressions") if isinstance(character.get("expressions"), dict) else {}
    lines = [
        "# Rinon Voice Lab character profile",
        "# Edit this file, then use Options > キャラ読込 to reload.",
        f"id: {character.get('id', '')}",
        f"name: {character.get('name', '')}",
        f"referencePath: {character.get('referencePath', '')}",
        f"portrait: {character.get('portrait', '')}",
        "",
        "[systemPrompt]",
        str(character.get("systemPrompt") or ""),
        "",
        "[ttsCaption]",
        str(character.get("ttsCaption") or ""),
        "",
        "[expressions]",
    ]
    for key in sorted(expressions):
        values = expressions.get(key) or []
        raw_values = values if isinstance(values, list) else [values]
        lines.append(f"{key}=" + "|".join(str(value) for value in raw_values if str(value or "").strip()))
    lines.append("")
    return "\n".join(lines)


def parse_character_text_profile(path: Path) -> dict:
    values: dict[str, str] = {}
    sections: dict[str, list[str]] = {"systemPrompt": [], "ttsCaption": [], "expressions": []}
    section = ""
    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.rstrip()
        stripped = line.strip()
        if not stripped or stripped.startswith("#"):
            continue
        if stripped.startswith("[") and stripped.endswith("]"):
            section = stripped[1:-1]
            sections.setdefault(section, [])
            continue
        if section in {"systemPrompt", "ttsCaption"}:
            sections[section].append(line)
            continue
        if section == "expressions":
            sections[section].append(line)
            continue
        if ":" in line:
            key, value = line.split(":", 1)
            values[key.strip()] = value.strip()
    expressions: dict[str, list[str]] = {}
    for line in sections.get("expressions", []):
        if "=" not in line:
            continue
        key, raw_values = line.split("=", 1)
        expr_key = sanitize_expression_key(key)
        expressions[expr_key] = [value.strip() for value in raw_values.split("|") if value.strip()]
    return {
        "id": values.get("id", path.parent.name),
        "name": values.get("name", path.parent.name),
        "referencePath": values.get("referencePath", ""),
        "portrait": values.get("portrait", ""),
        "systemPrompt": "\n".join(sections.get("systemPrompt", [])).strip(),
        "ttsCaption": "\n".join(sections.get("ttsCaption", [])).strip(),
        "expressions": expressions,
    }


def save_character_folder_profile(character: dict) -> None:
    character_id = sanitize_character_id(character.get("id"))
    char_dir = CHARACTER_ROOT / character_id
    char_dir.mkdir(parents=True, exist_ok=True)
    (char_dir / "profile.json").write_text(
        json.dumps(character, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    (char_dir / "profile.txt").write_text(character_text_profile(character), encoding="utf-8")


def load_character_folder_profiles() -> list[dict]:
    profiles: list[dict] = []
    if not CHARACTER_ROOT.exists():
        return profiles
    for char_dir in sorted(path for path in CHARACTER_ROOT.iterdir() if path.is_dir()):
        text_path = char_dir / "profile.txt"
        json_path = char_dir / "profile.json"
        try:
            if text_path.exists() and (not json_path.exists() or text_path.stat().st_mtime >= json_path.stat().st_mtime):
                profiles.append(parse_character_text_profile(text_path))
            elif json_path.exists():
                data = json.loads(json_path.read_text(encoding="utf-8"))
                if isinstance(data, dict):
                    profiles.append(data)
        except Exception:
            continue
    return profiles


def materialize_character_profile(profile: dict) -> dict:
    clean = sanitize_character_profiles(profile, materialize=False)
    CHARACTER_ROOT.mkdir(parents=True, exist_ok=True)
    for character in clean["characters"]:
        character_id = character["id"]
        clean_expressions: dict[str, list[str]] = {}
        for key, values in (character.get("expressions") or {}).items():
            expr_key = sanitize_expression_key(key)
            clean_expressions[expr_key] = [copy_character_asset(character_id, expr_key, value) for value in values]
        character["expressions"] = clean_expressions
        portrait = str(character.get("portrait") or "").strip()
        if portrait:
            for values in clean_expressions.values():
                if portrait in values:
                    break
            else:
                portrait = copy_character_asset(character_id, "neutral", portrait)
        if not portrait:
            portrait = (clean_expressions.get("neutral") or ["/expressions/neutral.png"])[0]
        character["portrait"] = portrait
        character["referencePath"] = copy_character_reference(character_id, character.get("referencePath", ""))
        save_character_folder_profile(character)
    return clean


def sanitize_character_profiles(payload: dict, materialize: bool = True) -> dict:
    defaults = default_character_profiles()
    raw_characters = payload.get("characters") if isinstance(payload.get("characters"), list) else []
    characters: list[dict] = []
    used_ids: set[str] = set()
    for index, item in enumerate(raw_characters):
        if not isinstance(item, dict):
            continue
        char_id = sanitize_character_id(item.get("id"), f"character_{index + 1}")
        original_id = char_id
        suffix = 2
        while char_id in used_ids:
            char_id = f"{original_id}_{suffix}"
            suffix += 1
        used_ids.add(char_id)
        expressions = item.get("expressions") if isinstance(item.get("expressions"), dict) else {}
        clean_expressions: dict[str, list[str]] = {}
        for key, values in expressions.items():
            expr_key = sanitize_expression_key(key)
            raw_values = values if isinstance(values, list) else [values]
            urls = [str(url).strip() for url in raw_values if str(url or "").strip()]
            clean_expressions[expr_key] = urls[:80]
        portrait = str(item.get("portrait") or "").strip()
        if not portrait:
            neutral = clean_expressions.get("neutral") or []
            portrait = neutral[0] if neutral else "/expressions/neutral.png"
        characters.append(
            {
                "id": char_id,
                "name": str(item.get("name") or char_id).strip()[:80],
                "systemPrompt": str(item.get("systemPrompt") or "").strip(),
                "ttsCaption": str(item.get("ttsCaption") or IRODORI_CAPTION).strip(),
                "referencePath": str(item.get("referencePath") or IRODORI_REF_WAV).strip(),
                "portrait": portrait,
                "expressions": clean_expressions,
            }
        )
    if not characters:
        return defaults
    character_ids = {item["id"] for item in characters}
    active_main = sanitize_character_id(payload.get("activeMainId"), characters[0]["id"])
    active_second = sanitize_character_id(payload.get("activeSecondId"), characters[min(1, len(characters) - 1)]["id"])
    if active_main not in character_ids:
        active_main = characters[0]["id"]
    if active_second not in character_ids:
        active_second = characters[min(1, len(characters) - 1)]["id"]
    clean = {
        "version": 1,
        "activeMainId": active_main,
        "activeSecondId": active_second,
        "characters": characters,
    }
    return materialize_character_profile(clean) if materialize else clean


def load_character_profiles() -> dict:
    if CHARACTER_PROFILE_PATH.exists():
        data = json.loads(CHARACTER_PROFILE_PATH.read_text(encoding="utf-8"))
        if not isinstance(data, dict):
            data = default_character_profiles()
    else:
        data = default_character_profiles()
    profile = sanitize_character_profiles(data, materialize=False)
    folder_profiles = load_character_folder_profiles()
    if folder_profiles:
        by_id = {character["id"]: character for character in profile["characters"]}
        order = [character["id"] for character in profile["characters"]]
        for raw_character in folder_profiles:
            sanitized = sanitize_character_profiles({"characters": [raw_character]}, materialize=False)["characters"][0]
            by_id[sanitized["id"]] = sanitized
            if sanitized["id"] not in order:
                order.append(sanitized["id"])
        profile["characters"] = [by_id[character_id] for character_id in order if character_id in by_id]
    profile = materialize_character_profile(profile)
    PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
    CHARACTER_PROFILE_PATH.write_text(json.dumps(profile, ensure_ascii=False, indent=2), encoding="utf-8")
    return profile


def save_character_profiles(payload: dict) -> dict:
    PROFILE_ROOT.mkdir(parents=True, exist_ok=True)
    profile = sanitize_character_profiles(payload)
    CHARACTER_PROFILE_PATH.write_text(
        json.dumps(profile, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    return profile


def save_character_image(payload: dict) -> dict:
    character_id = sanitize_character_id(payload.get("characterId"))
    expression = sanitize_expression_key(payload.get("expression"))
    original_name = Path(str(payload.get("name") or "expression.png")).name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_IMAGE_EXTENSIONS:
        raise ValueError("expression image must be png, jpg, jpeg, or webp")
    encoded = str(payload.get("dataBase64") or "")
    if "," in encoded:
        encoded = encoded.split(",", 1)[1]
    image_bytes = base64.b64decode(encoded, validate=True)
    if not image_bytes:
        raise ValueError("expression image is empty")
    if len(image_bytes) > 32 * 1024 * 1024:
        raise ValueError("expression image is too large")
    out_dir = CHARACTER_ROOT / character_id / "expressions" / expression
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^0-9A-Za-z_-]+", "_", Path(original_name).stem).strip("_")[:48] or "image"
    file_name = f"{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{safe_stem}{suffix}"
    out_path = out_dir / file_name
    out_path.write_bytes(image_bytes)
    return {
        "ok": True,
        "characterId": character_id,
        "expression": expression,
        "path": str(out_path),
        "url": character_url(character_id, "expressions", expression, file_name),
        "name": file_name,
        "size": out_path.stat().st_size,
    }


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
                "mainCharacterName": str(settings.get("mainCharacterName") or "リノン"),
                "secondCharacterName": str(settings.get("secondCharacterName") or "ルヴィア"),
                "activeMainCharacterId": str(settings.get("activeMainCharacterId") or "rinon"),
                "activeSecondCharacterId": str(settings.get("activeSecondCharacterId") or "luvia"),
                "userAddress": str(settings.get("userAddress") or "あなた"),
                "ttsCaption": str(settings.get("ttsCaption") or IRODORI_CAPTION),
                "secondSystemPrompt": str(settings.get("secondSystemPrompt") or ""),
                "secondTtsCaption": str(settings.get("secondTtsCaption") or IRODORI_CAPTION),
                "referencePath": str(settings.get("referencePath") or IRODORI_REF_WAV),
                "secondReferencePath": str(settings.get("secondReferencePath") or LUVIA_REF_WAV),
                "contextLimit": int(settings.get("contextLimit") or DEFAULT_CONTEXT_LIMIT),
                "model": str(settings.get("model") or DEFAULT_MODEL),
                "steps": int(settings.get("steps") or 12),
                "speechRate": str(settings.get("speechRate") or "normal"),
                "replyLength": str(settings.get("replyLength") or "normal"),
            "autoEmoji": bool(settings.get("autoEmoji", True)),
            "webSearch": bool(settings.get("webSearch", False)),
            "twoPlayerMode": bool(settings.get("twoPlayerMode", False)),
            "twoOnlyMode": bool(settings.get("twoOnlyMode", False)),
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


def sanitize_reference_path(value: object, fallback: Path) -> Path:
    raw = str(value or "").strip()
    if not raw:
        return fallback
    candidate = Path(raw)
    if not candidate.is_absolute():
        candidate = (APP_ROOT / candidate).resolve()
    else:
        candidate = candidate.resolve()
    if candidate.suffix.lower() not in ALLOWED_REFERENCE_EXTENSIONS:
        return fallback
    if not candidate.exists():
        return fallback
    return candidate


def save_reference_audio(payload: dict) -> dict:
    slot = "second" if str(payload.get("slot") or "") == "second" else "main"
    character_id = sanitize_character_id(payload.get("characterId"), "rinon")
    original_name = Path(str(payload.get("name") or "reference.wav")).name
    suffix = Path(original_name).suffix.lower()
    if suffix not in ALLOWED_REFERENCE_EXTENSIONS:
        raise ValueError("reference audio must be wav, mp3, flac, m4a, ogg, or aac")
    encoded = str(payload.get("dataBase64") or "")
    if "," in encoded:
        encoded = encoded.split(",", 1)[1]
    audio_bytes = base64.b64decode(encoded, validate=True)
    if not audio_bytes:
        raise ValueError("reference audio is empty")
    if len(audio_bytes) > 80 * 1024 * 1024:
        raise ValueError("reference audio is too large")

    out_dir = CHARACTER_ROOT / character_id / "reference"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_stem = re.sub(r"[^0-9A-Za-z_-]+", "_", Path(original_name).stem).strip("_")[:48]
    safe_stem = safe_stem or "reference"
    file_name = f"{slot}_{time.strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:8]}_{safe_stem}{suffix}"
    out_path = out_dir / file_name
    out_path.write_bytes(audio_bytes)
    return {
        "ok": True,
        "characterId": character_id,
        "slot": slot,
        "path": str(out_path),
        "url": character_url(character_id, "reference", file_name),
        "name": file_name,
        "size": out_path.stat().st_size,
    }


def remote_ref_for_luvia(reference_wav: Path) -> str:
    if reference_wav.resolve() == LUVIA_REF_WAV.resolve():
        return LUVIA_REMOTE_REF_WAV
    cache_key = str(reference_wav.resolve())
    if cache_key in Luvia_remote_ref_cache:
        return Luvia_remote_ref_cache[cache_key]
    request_id = f"ref_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}{reference_wav.suffix.lower()}"
    remote_refs = rf"{LUVIA_REMOTE_IRODORI_ROOT}\remote_refs"
    remote_path = rf"{remote_refs}\{request_id}"

    def run_command(args: list[str], timeout: int = 60) -> None:
        completed = subprocess.run(
            args,
            cwd=str(APP_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(detail or f"command failed: {' '.join(args)}")

    run_command(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            LUVIA_REMOTE_TTS_HOST,
            f'cmd /c if not exist "{remote_refs}" mkdir "{remote_refs}"',
        ],
        timeout=30,
    )
    remote_scp = remote_path.replace("\\", "/").replace("E:/", "E:/")
    run_command(["scp", "-q", str(reference_wav), f"{LUVIA_REMOTE_TTS_HOST}:{remote_scp}"], timeout=90)
    Luvia_remote_ref_cache[cache_key] = remote_path
    return remote_path


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


def stop_irodori_ui_processes() -> list[dict[str, str | int]]:
    current_pid = os.getpid()
    irodori_root_text = str(IRODORI_ROOT).lower()
    script = r"""
$ports = @(7861)
$portPids = @()
foreach ($port in $ports) {
  Get-NetTCPConnection -LocalPort $port -State Listen -ErrorAction SilentlyContinue |
    Select-Object -ExpandProperty OwningProcess -Unique |
    ForEach-Object { $portPids += [int]$_ }
}
Get-CimInstance Win32_Process |
  Where-Object {
    $_.CommandLine -and (
      ($_.CommandLine -like '*Irodori-TTS*' -and $_.CommandLine -match '(gradio|voicedesign|base_ui|infer\.py|uv run|python)') -or
      ($portPids -contains [int]$_.ProcessId)
    )
  } |
  Select-Object ProcessId, Name, CommandLine |
  ConvertTo-Json -Compress
"""
    try:
        completed = subprocess.run(
            ["powershell", "-NoProfile", "-ExecutionPolicy", "Bypass", "-Command", script],
            cwd=str(APP_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=20,
        )
    except Exception as exc:
        return [{"pid": 0, "name": "scan failed", "detail": str(exc)}]
    if completed.returncode != 0:
        return [{"pid": 0, "name": "scan failed", "detail": (completed.stderr or completed.stdout).strip()}]
    raw = (completed.stdout or "").strip()
    if not raw:
        return []
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return [{"pid": 0, "name": "scan parse failed", "detail": raw[:500]}]
    items = data if isinstance(data, list) else [data]
    stopped: list[dict[str, str | int]] = []
    for item in items:
        if not isinstance(item, dict):
            continue
        pid = int(item.get("ProcessId") or 0)
        command_line = str(item.get("CommandLine") or "")
        if not pid or pid == current_pid:
            continue
        if irodori_root_text not in command_line.lower() and "7861" not in command_line:
            continue
        try:
            subprocess.run(
                ["taskkill", "/PID", str(pid), "/T", "/F"],
                cwd=str(APP_ROOT),
                capture_output=True,
                text=True,
                timeout=15,
            )
            stopped.append({"pid": pid, "name": str(item.get("Name") or ""), "detail": "stopped"})
        except Exception as exc:
            stopped.append({"pid": pid, "name": str(item.get("Name") or ""), "detail": str(exc)})
    return stopped


def shutdown_app_server(server: ThreadingHTTPServer) -> None:
    def worker() -> None:
        time.sleep(0.35)
        try:
            server.shutdown()
            server.server_close()
        finally:
            time.sleep(0.35)
            os._exit(0)

    threading.Thread(target=worker, daemon=True).start()


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


def sanitize_no_dialogue_reply(text: str) -> str:
    allowed_fragments = (
        "好き",
        "大好き",
        "感じる",
        "感じちゃう",
        "だめ",
        "だめえ",
        "だめぇ",
        "だめっ",
        "もうだめ",
        "我慢できない",
        "おかしくなっちゃう",
        "いかせて",
        "いかせてぇ",
        "無理",
    )
    hard_banned_fragments = (
        "きみ",
        "君",
        "あなた",
        "あんた",
        "こっち",
        "そこ",
        "ここ",
        "反応",
        "可愛い",
        "かわいい",
        "止め",
        "してほしい",
        "ほしい",
        "して",
        "ほら",
        "ねぇ",
        "ねえ",
        "混ぜて",
        "来て",
        "見て",
        "？",
        "?",
    )
    parts = re.split(r"(?<=[。！？!?])\s*|\n+", str(text or ""))
    kept: list[str] = []
    for part in parts:
        candidate = strip_irodori_style_marks(part).strip()
        if not candidate:
            continue
        allowed_hit = any(fragment in candidate for fragment in allowed_fragments)
        if any(fragment in candidate for fragment in hard_banned_fragments):
            continue
        if re.search(r"[一-龯々〆ヵヶ]", candidate) and not allowed_hit:
            continue
        if len(candidate) > (64 if allowed_hit else 48):
            continue
        kept.append(candidate)
    cleaned = " ".join(kept)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    if len(cleaned) < 6:
        return "……っ、はぁ……。ん……っ。……ふぅ……。"
    return cleaned


def reply_style_for_length(reply_length: str) -> tuple[str, int, int]:
    mode = str(reply_length or "normal").strip().lower()
    if mode == "long":
        return "返答は6から10文くらいまで使って、自然な会話調で少し詳しく答えてください。", 1200, 10
    if mode == "short":
        return "返答は1から2文を基本にしてください。", 360, 3
    return "返答は3から5文くらいまで使って、自然な会話調で答えてください。", 720, 6


def tts_duration_scale_for_rate(value: object) -> float:
    mode = str(value or "normal").strip().lower()
    if mode == "fast":
        return 0.86
    return 1.0


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


def message_context_cost(messages: list[dict[str, str]]) -> int:
    return sum(len(str(item.get("content") or "")) + 32 for item in messages)


def compact_text(value: str, limit: int = 110) -> str:
    text = re.sub(r"\s+", " ", str(value or "")).strip()
    if len(text) <= limit:
        return text
    return text[: max(0, limit - 1)].rstrip() + "…"


def summarize_old_messages(messages: list[dict[str, str]], limit: int = LM_SUMMARY_CHAR_LIMIT) -> str:
    if not messages:
        return ""
    topic_lines: list[str] = []
    turn_lines: list[str] = []
    for item in messages:
        content = str(item.get("content") or "").strip()
        if not content:
            continue
        if content.startswith(("お題:", "次のお題:")):
            topic_lines.append(compact_text(content, 90))
        role = "ユーザー" if item.get("role") == "user" else "相手"
        if content.startswith(("リノン:", "ルヴィア:")) and ":" in content:
            role, content = content.split(":", 1)
            role = role.strip() or "相手"
            content = content.strip()
        turn_lines.append(f"{role}: {compact_text(content, 95)}")

    selected: list[str] = []
    if topic_lines:
        selected.append("過去のお題: " + " / ".join(topic_lines[-5:]))
    if turn_lines:
        selected.append("古い会話の圧縮ログ:")
        selected.extend(turn_lines[-14:])
    summary = "\n".join(selected)
    if len(summary) > limit:
        summary = "… " + summary[-limit:].lstrip()
    return summary


def compact_messages_for_context(
    messages: list[dict[str, str]],
    limit: int,
) -> tuple[list[dict[str, str]], dict[str, int | bool]]:
    requested_limit = max(1000, int(limit or DEFAULT_CONTEXT_LIMIT))
    effective_limit = min(requested_limit, max(1000, LM_COMPACT_CONTEXT_LIMIT))
    recent_count = max(4, LM_RECENT_MESSAGE_COUNT)
    full_cost = message_context_cost(messages)
    if full_cost <= effective_limit and len(messages) <= recent_count:
        trimmed = trim_messages_for_context(messages, effective_limit)
        return trimmed, {
            "full": full_cost,
            "sent": message_context_cost(trimmed),
            "limit": requested_limit,
            "effectiveLimit": effective_limit,
            "compacted": False,
            "recentMessages": len(trimmed),
        }

    recent = messages[-recent_count:]
    older = messages[:-recent_count]
    summary = summarize_old_messages(older)
    compacted: list[dict[str, str]] = []
    if summary:
        compacted.append(
            {
                "role": "user",
                "content": (
                    "以下は古い会話の要約です。細部よりも、現在の関係性、進行中のお題、"
                    "直前までの流れを保つための参考として扱ってください。\n"
                    f"{summary}"
                ),
            }
        )
    compacted.extend(recent)
    trimmed = trim_messages_for_context(compacted, effective_limit)
    if summary and compacted and (not trimmed or trimmed[0] != compacted[0]):
        compacted[0]["content"] = compacted[0]["content"][-max(400, effective_limit // 3) :]
        trimmed = trim_messages_for_context(compacted, effective_limit)
    return trimmed, {
        "full": full_cost,
        "sent": message_context_cost(trimmed),
        "limit": requested_limit,
        "effectiveLimit": effective_limit,
        "compacted": bool(summary),
        "recentMessages": min(len(recent), len(trimmed)),
    }


def strip_html(value: str) -> str:
    text = re.sub(r"<[^>]+>", " ", str(value or ""))
    text = html_unescape(text)
    return re.sub(r"\s+", " ", text).strip()


def normalize_search_url(value: str) -> str:
    url = html_unescape(str(value or ""))
    if url.startswith("//"):
        url = "https:" + url
    parsed = urlparse(url)
    if parsed.netloc.endswith("duckduckgo.com") and parsed.path.startswith("/l/"):
        target = parse_qs(parsed.query).get("uddg", [""])[0]
        if target:
            return unquote(target)
    return url


def web_search(query: str, limit: int = 3) -> list[dict[str, str]]:
    search_query = re.sub(r"\s+", " ", str(query or "")).strip()
    if not search_query:
        return []
    url = f"https://lite.duckduckgo.com/lite/?q={quote_plus(search_query[:220])}"
    request = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0",
            "Accept-Language": "ja,en-US;q=0.8,en;q=0.6",
        },
    )
    with urllib.request.urlopen(request, timeout=WEB_SEARCH_TIMEOUT) as res:
        html = res.read().decode("utf-8", errors="replace")
    results: list[dict[str, str]] = []
    anchor_pattern = re.compile(r"<a(?P<attrs>[^>]*)>(?P<title>.*?)</a>", re.IGNORECASE | re.DOTALL)
    anchors = [match for match in anchor_pattern.finditer(html) if "result-link" in match.group("attrs")]
    for index, match in enumerate(anchors):
        attrs = match.group("attrs")
        href_match = re.search(r"href=['\"](?P<href>[^'\"]+)['\"]", attrs, re.IGNORECASE)
        if not href_match:
            continue
        title = strip_html(match.group("title"))
        href = normalize_search_url(href_match.group("href"))
        tail_end = anchors[index + 1].start() if index + 1 < len(anchors) else len(html)
        tail = html[match.end() : tail_end]
        snippet_match = re.search(
            r"<td[^>]*result-snippet[^>]*>(?P<snippet>.*?)</td>",
            tail,
            re.IGNORECASE | re.DOTALL,
        )
        snippet = strip_html(snippet_match.group("snippet")) if snippet_match else ""
        if title and href:
            results.append({"title": title, "url": href, "snippet": snippet})
        if len(results) >= limit:
            break
    return results


WEB_INTENT_TERMS = (
    "評判",
    "口コミ",
    "レビュー",
    "感想",
    "映画",
    "新作",
    "公開",
    "公開日",
    "監督",
    "声優",
    "キャスト",
    "制作",
    "予告",
    "配信",
    "あらすじ",
    "ネタバレ",
)
WEB_QUERY_STOP_TERMS = {"リノン", "ルヴィア", "ユーザー", "お題", "会話", "自動会話"}


def extract_web_query_terms(text: str, include_intents: bool = True) -> list[str]:
    source = str(text or "")
    terms: list[str] = []
    for quoted in re.findall(r"[「『\"]([^」』\"]{2,40})[」』\"]", source):
        terms.append(quoted)
    terms.extend(re.findall(r"[A-Za-z][A-Za-z0-9._+-]{1,}", source))
    terms.extend(re.findall(r"[ァ-ヶー]{2,}", source))
    if include_intents:
        for term in WEB_INTENT_TERMS:
            if term in source:
                terms.append(term)
    cleaned: list[str] = []
    seen: set[str] = set()
    for term in terms:
        value = re.sub(r"\s+", " ", term).strip("。、，,.!?！？:：;；()（）[]【】")
        if len(value) < 2 or value in WEB_QUERY_STOP_TERMS or value in seen:
            continue
        seen.add(value)
        cleaned.append(value)
    return cleaned


def build_continuous_web_query(user_text: str, history: list[dict[str, str]]) -> str:
    current_terms = extract_web_query_terms(user_text, include_intents=True)
    inherited: list[str] = []
    for item in reversed(history[-8:]):
        content = str(item.get("content") or "")
        if ":" in content and content.split(":", 1)[0] in {"リノン", "ルヴィア"}:
            content = content.split(":", 1)[1]
        for term in extract_web_query_terms(content, include_intents=False):
            if term not in inherited:
                inherited.append(term)
        if len(inherited) >= 6:
            break
    combined: list[str] = []
    for term in [*inherited, *current_terms]:
        if term not in combined:
            combined.append(term)
    if combined:
        return " ".join(combined[:8])
    return re.sub(r"\s+", " ", str(user_text or "")).strip()


def format_web_results(query: str, results: list[dict[str, str]]) -> str:
    if not results:
        return ""
    lines = [
        f'Web検索結果です。検索語: "{compact_text(query, 120)}"',
        "現在までの会話コンテキスト、キャラ設定、直前の発言を優先してください。",
        "検索結果は補助情報として必要な場合だけ使い、検索結果にない事実は断定しないでください。",
    ]
    for index, item in enumerate(results, start=1):
        lines.append(
            f"{index}. {compact_text(item.get('title', ''), 100)}\n"
            f"URL: {item.get('url', '')}\n"
            f"概要: {compact_text(item.get('snippet', ''), 180)}"
        )
    return "\n".join(lines)


def request_lmstudio(
    messages: list[dict[str, str]],
    model: str | None,
    auto_emoji: bool,
    reply_length: str,
    character_prompt: str,
    user_address: str,
    no_dialogue: bool = False,
    speaker: str = "リノン",
    two_only_mode: bool = False,
) -> tuple[str, str, str, int]:
    length_instruction, max_tokens, chunk_limit = reply_style_for_length(reply_length)
    address = str(user_address or "").strip() or "あなた"
    address_instruction = (
        f"\nユーザーへの呼びかけは「{address}」を使ってください。"
        "名前が明示されていない相手を「〇〇君」「君」「きみ」と呼ばないでください。"
    )
    no_dialogue_instruction = (
        "\n台詞禁止モードです。呼びかけ、質問、説明、選択肢提示、二人称の使用、"
        "普通の文章として読める会話文は禁止です。発声・吐息・擬音・短い断片だけで構成し、"
        "意味のある文を続けないでください。"
        if no_dialogue
        else ""
    )
    two_only_instruction = (
        "\n2人だけモードです。この会話世界にユーザーや観客は存在しません。"
        "ユーザー入力は登場人物の発言ではなく、外部からの進行指示/お題として扱ってください。"
        "リノンとルヴィアだけが同じ場にいて、互いにだけ話します。"
        "ユーザーへ話しかけたり、ユーザーの反応を求めたり、外部の相手を「きみ」「君」「あなた」などで呼ばないでください。"
        "返答は必ず相手キャラクターへの発言として書いてください。"
        if two_only_mode
        else ""
    )
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
    payload["messages"][0]["content"] = (
        "あなたは日本語で自然に返す会話相手です。\n"
        f"いま話すキャラクターは「{speaker}」です。\n"
        f"{character_prompt.strip()}\n"
        f"{address_instruction}\n"
        f"{no_dialogue_instruction}\n"
        f"{two_only_instruction}\n"
        f"{length_instruction}"
        "思考過程は出さず、最終回答だけを出してください。/no_think"
        f"{emoji_instruction}"
    )
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
    if no_dialogue:
        message = sanitize_no_dialogue_reply(message)
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
    ref_wav: Path | None = None,
    duration_scale: float = 1.0,
) -> dict:
    module = ensure_irodori_module()
    styled_text = apply_emoji_style(text, emoji_style)
    voice_caption = str(caption or "").strip() or IRODORI_CAPTION
    reference_wav = ref_wav or IRODORI_REF_WAV
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
                str(reference_wav) if reference_wav.exists() else None,
                int(steps),
                1,
                "",
                "",
                float(duration_scale),
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
        "reference": str(reference_wav) if reference_wav.exists() else "",
        "emojiStyle": emoji_style,
        "speechRate": "fast" if float(duration_scale) < 0.99 else "normal",
        "durationScale": float(duration_scale),
        "expression": expression_for_emoji(emoji_style),
        "url": f"/generated/{safe_name}",
        "elapsed": round(elapsed, 3),
        "source": str(wav_path),
    }


def synthesize_sentence_remote_luvia(
    text: str,
    index: int,
    steps: int,
    emoji_style: str = "",
    caption: str = "",
    remote_ref_wav: str = "",
    duration_scale: float = 1.0,
) -> dict:
    styled_text = apply_emoji_style(text, emoji_style)
    voice_caption = str(caption or "").strip() or IRODORI_CAPTION
    payload = {
        "text": styled_text,
        "caption": voice_caption,
        "steps": max(1, min(120, int(steps))),
        "emojiStyle": emoji_style,
        "refWav": remote_ref_wav or LUVIA_REMOTE_REF_WAV,
        "durationScale": float(duration_scale),
    }
    request = urllib.request.Request(
        f"{LUVIA_REMOTE_TTS_URL}/synthesize",
        data=json_bytes(payload),
        headers={"Content-Type": "application/json"},
        method="POST",
    )
    try:
        start = time.perf_counter()
        with urllib.request.urlopen(request, timeout=240) as res:
            data = json.loads(res.read().decode("utf-8"))
        audio_bytes = base64.b64decode(str(data["audioBase64"]))
        elapsed = float(data.get("elapsed") or (time.perf_counter() - start))
    except Exception as exc:
        fallback = synthesize_sentence_remote_luvia_cli(text, index, steps, emoji_style, caption, remote_ref_wav, duration_scale)
        fallback["remoteServerError"] = str(exc)
        fallback["engine"] = "4090-cli-fallback"
        return fallback

    out_dir = STATIC_ROOT / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"reply_{int(time.time() * 1000)}_{index:02d}_luvia4090.wav"
    public_path = out_dir / safe_name
    public_path.write_bytes(audio_bytes)
    return {
        "text": text,
        "ttsText": styled_text,
        "caption": voice_caption,
        "reference": str(data.get("reference") or LUVIA_REMOTE_REF_WAV),
        "emojiStyle": emoji_style,
        "speechRate": "fast" if float(duration_scale) < 0.99 else "normal",
        "durationScale": float(duration_scale),
        "expression": expression_for_emoji(emoji_style),
        "url": f"/generated/{safe_name}",
        "elapsed": round(elapsed, 3),
        "source": str(data.get("source") or LUVIA_REMOTE_TTS_URL),
        "engine": "4090-server",
    }


def synthesize_sentence_remote_luvia_cli(
    text: str,
    index: int,
    steps: int,
    emoji_style: str = "",
    caption: str = "",
    remote_ref_wav: str = "",
    duration_scale: float = 1.0,
) -> dict:
    styled_text = apply_emoji_style(text, emoji_style)
    voice_caption = str(caption or "").strip() or IRODORI_CAPTION
    request_id = f"luvia_{int(time.time() * 1000)}_{uuid.uuid4().hex[:8]}_{index:02d}"
    remote_root = LUVIA_REMOTE_IRODORI_ROOT
    remote_requests = rf"{remote_root}\remote_requests"
    remote_outputs = rf"{remote_root}\outputs\remote_luvia"
    remote_request_path = rf"{remote_requests}\{request_id}.json"
    remote_output_wav = rf"{remote_outputs}\{request_id}.wav"
    request_dir = LOG_ROOT / "remote_tts_requests"
    request_dir.mkdir(parents=True, exist_ok=True)
    request_path = request_dir / f"{request_id}.json"
    request_payload = {
        "text": styled_text,
        "caption": voice_caption,
        "steps": max(1, min(120, int(steps))),
        "ref_wav": remote_ref_wav or LUVIA_REMOTE_REF_WAV,
        "output_wav": remote_output_wav,
        "duration_scale": float(duration_scale),
    }
    request_path.write_text(json.dumps(request_payload, ensure_ascii=False), encoding="utf-8")

    def run_command(args: list[str], timeout: int = 180) -> None:
        completed = subprocess.run(
            args,
            cwd=str(APP_ROOT),
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=timeout,
        )
        if completed.returncode != 0:
            detail = (completed.stderr or completed.stdout or "").strip()
            raise RuntimeError(detail or f"command failed: {' '.join(args)}")

    remote_request_scp = remote_request_path.replace("\\", "/").replace("E:/", "E:/")
    remote_output_scp = remote_output_wav.replace("\\", "/").replace("E:/", "E:/")
    run_command(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            LUVIA_REMOTE_TTS_HOST,
            (
                f'cmd /c if not exist "{remote_requests}" mkdir "{remote_requests}" '
                f'& if not exist "{remote_outputs}" mkdir "{remote_outputs}"'
            ),
        ],
        timeout=30,
    )
    run_command(
        [
            "scp",
            "-q",
            str(request_path),
            f"{LUVIA_REMOTE_TTS_HOST}:{remote_request_scp}",
        ],
        timeout=60,
    )

    remote_script = (
        "$ErrorActionPreference='Stop';"
        f"$root='{remote_root}';"
        f"$req='{remote_request_path}';"
        "$r=Get-Content -Raw -Encoding UTF8 $req | ConvertFrom-Json;"
        f"Set-Location '{remote_root}';"
        "& '.\\.venv\\Scripts\\python.exe' 'infer.py' "
        "--hf-checkpoint 'Aratako/Irodori-TTS-600M-v3-VoiceDesign' "
        "--text $r.text "
        "--caption $r.caption "
        "--ref-wav $r.ref_wav "
        "--num-steps $r.steps "
        "--duration-scale $r.duration_scale "
        "--t-schedule-mode linear "
        "--sway-coeff -1 "
        "--cfg-guidance-mode independent "
        "--cfg-scale-text 3 "
        "--cfg-scale-caption 4 "
        "--cfg-scale-speaker 5 "
        "--model-precision bf16 "
        "--codec-precision bf16 "
        "--output-wav $r.output_wav"
    )
    encoded_remote_script = base64.b64encode(remote_script.encode("utf-16le")).decode("ascii")
    start = time.perf_counter()
    run_command(
        [
            "ssh",
            "-o",
            "BatchMode=yes",
            LUVIA_REMOTE_TTS_HOST,
            "powershell",
            "-NoProfile",
            "-ExecutionPolicy",
            "Bypass",
            "-EncodedCommand",
            encoded_remote_script,
        ],
        timeout=240,
    )
    elapsed = time.perf_counter() - start

    out_dir = STATIC_ROOT / "generated"
    out_dir.mkdir(parents=True, exist_ok=True)
    safe_name = f"reply_{int(time.time() * 1000)}_{index:02d}_luvia4090.wav"
    public_path = out_dir / safe_name
    run_command(
        [
            "scp",
            "-q",
            f"{LUVIA_REMOTE_TTS_HOST}:{remote_output_scp}",
            str(public_path),
        ],
        timeout=60,
    )
    return {
        "text": text,
        "ttsText": styled_text,
        "caption": voice_caption,
        "reference": remote_ref_wav or LUVIA_REMOTE_REF_WAV,
        "emojiStyle": emoji_style,
        "speechRate": "fast" if float(duration_scale) < 0.99 else "normal",
        "durationScale": float(duration_scale),
        "expression": expression_for_emoji(emoji_style),
        "url": f"/generated/{safe_name}",
        "elapsed": round(elapsed, 3),
        "source": f"{LUVIA_REMOTE_TTS_HOST}:{remote_output_wav}",
        "engine": "4090",
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
                    "luviaReference": str(LUVIA_REF_WAV),
                    "luviaReferenceExists": LUVIA_REF_WAV.exists(),
                    "userReferenceRoot": str(USER_REFERENCE_ROOT),
                    "luviaRemoteTtsHost": LUVIA_REMOTE_TTS_HOST,
                    "luviaRemoteTtsUrl": LUVIA_REMOTE_TTS_URL,
                    "luviaRemoteReference": LUVIA_REMOTE_REF_WAV,
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

        if parsed.path == "/api/characters":
            try:
                self.send_json(200, load_character_profiles())
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
        if parsed.path.startswith("/Character/"):
            static_root = CHARACTER_ROOT.resolve()
            rel_character = Path(unquote(parsed.path.removeprefix("/Character/")))
            file_path = (CHARACTER_ROOT / rel_character).resolve()
        if parsed.path.startswith("/characters/"):
            static_root = LEGACY_CHARACTER_ROOT.resolve()
            rel_character = Path(unquote(parsed.path.removeprefix("/characters/")))
            file_path = (LEGACY_CHARACTER_ROOT / rel_character).resolve()
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

        if parsed.path == "/api/characters":
            try:
                self.send_json(200, save_character_profiles(read_json_body(self)))
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return

        if parsed.path == "/api/save-audio":
            try:
                self.send_json(200, save_current_audio(read_json_body(self)))
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return

        if parsed.path == "/api/reference":
            try:
                self.send_json(200, save_reference_audio(read_json_body(self)))
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return

        if parsed.path == "/api/character-image":
            try:
                self.send_json(200, save_character_image(read_json_body(self)))
            except Exception as exc:
                self.send_json(500, {"error": str(exc)})
            return

        if parsed.path == "/api/shutdown":
            try:
                stopped = stop_irodori_ui_processes()
                self.send_json(200, {"ok": True, "stopped": stopped, "self": os.getpid()})
                shutdown_app_server(self.server)
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
            speech_rate = str(body.get("speechRate") or "normal").strip().lower()
            duration_scale = tts_duration_scale_for_rate(speech_rate)
            emoji_style = str(body.get("emojiStyle") or "").strip()
            auto_emoji = bool(body.get("autoEmoji", True))
            no_dialogue = bool(body.get("noDialogue", False))
            reply_length = str(body.get("replyLength") or "normal").strip()
            speaker_slot = "second" if str(body.get("speakerSlot") or "") == "second" else "main"
            speaker = str(body.get("speaker") or ("ルヴィア" if body.get("twoPlayerMode") else "リノン")).strip()
            two_player_mode = bool(body.get("twoPlayerMode", False))
            two_only_mode = bool(body.get("twoOnlyMode", False)) and two_player_mode
            use_second_speaker = speaker_slot == "second"
            use_web_search = bool(body.get("webSearch", False)) and (not use_second_speaker or two_player_mode)
            character_prompt = str(body.get("systemPrompt") or "").strip()
            user_address = str(body.get("userAddress") or "あなた").strip() or "あなた"
            tts_caption = str(body.get("ttsCaption") or IRODORI_CAPTION).strip()
            reference_path = sanitize_reference_path(body.get("referencePath"), IRODORI_REF_WAV)
            second_reference_path = sanitize_reference_path(body.get("secondReferencePath"), LUVIA_REF_WAV)
            context_limit = int(body.get("contextLimit") or DEFAULT_CONTEXT_LIMIT)
            existing_web_context = str(body.get("webContext") or "").strip()
            web_topic = str(body.get("webTopic") or "").strip()
            raw_messages = [
                item
                for item in history
                if isinstance(item, dict) and item.get("role") in {"user", "assistant"}
            ]
            search_results: list[dict[str, str]] = []
            web_query = ""
            web_context = existing_web_context
            if use_web_search:
                web_query_source = web_topic or user_text
                web_query = build_continuous_web_query(web_query_source, raw_messages)
                try:
                    search_results = web_search(web_query, limit=3)
                except Exception as exc:
                    search_results = [{"title": "検索エラー", "url": "", "snippet": str(exc)}]
                web_context = format_web_results(web_query, search_results)
            if web_context:
                raw_messages.append(
                    {
                        "role": "user",
                            "content": (
                                f"今回の進行指示/質問: {compact_text(web_topic or user_text, 180)}\n"
                                f"共有Webメモとして保持中の検索語: {web_query or '前回のお題'}\n"
                                f"{web_context}"
                            ),
                    }
                )
            raw_messages.append({"role": "user", "content": user_text})
            messages, context_stats = compact_messages_for_context(raw_messages, context_limit)
            reply, model_used, llm_emoji, chunk_limit = request_lmstudio(
                messages,
                model,
                auto_emoji=auto_emoji,
                reply_length=reply_length,
                character_prompt=character_prompt,
                user_address=user_address,
                no_dialogue=no_dialogue,
                speaker=speaker,
                two_only_mode=two_only_mode,
            )
            effective_emoji = emoji_style or llm_emoji
            chunks = split_sentences(reply, limit=chunk_limit)
            reference_wav = second_reference_path if use_second_speaker else reference_path
            remote_reference_wav = remote_ref_for_luvia(reference_wav) if use_second_speaker else ""
            synthesize = (
                synthesize_sentence_remote_luvia
                if use_second_speaker
                else synthesize_sentence
            )
            audios = [
                synthesize(
                    chunk,
                    i,
                    steps=max(1, min(120, steps)),
                    emoji_style=effective_emoji,
                    caption=tts_caption,
                    duration_scale=duration_scale,
                    **(
                        {"remote_ref_wav": remote_reference_wav}
                        if use_second_speaker
                        else {"ref_wav": reference_wav}
                    ),
                )
                for i, chunk in enumerate(chunks, start=1)
            ]
            append_chat_log(
                {
                    "time": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
                    "user": user_text,
                    "reply": reply,
                    "speaker": speaker,
                    "model": model_used,
                    "replyLength": reply_length,
                    "speechRate": speech_rate,
                    "durationScale": duration_scale,
                    "emojiStyle": effective_emoji,
                    "llmEmojiStyle": llm_emoji,
                    "autoEmoji": auto_emoji,
                    "noDialogue": no_dialogue,
                    "webSearch": use_web_search,
                    "twoOnlyMode": two_only_mode,
                    "webQuery": web_query,
                    "webContext": web_context,
                    "webResults": search_results,
                    "ttsCaption": tts_caption,
                    "userAddress": user_address,
                    "reference": str(reference_wav),
                    "characterPrompt": character_prompt,
                    "expression": expression_for_emoji(effective_emoji),
                    "chunkCount": len(chunks),
                    "chunks": chunks,
                    "audios": [
                        {
                            "text": item.get("text"),
                            "ttsText": item.get("ttsText"),
                            "emojiStyle": item.get("emojiStyle"),
                            "speechRate": item.get("speechRate"),
                            "durationScale": item.get("durationScale"),
                            "expression": item.get("expression"),
                            "elapsed": item.get("elapsed"),
                            "url": item.get("url"),
                        }
                        for item in audios
                    ],
                    "contextStats": context_stats,
                }
            )
            self.send_json(
                200,
                {
                    "reply": reply,
                    "speaker": speaker,
                    "model": model_used,
                    "chunks": chunks,
                    "emojiStyle": effective_emoji,
                    "expression": expression_for_emoji(effective_emoji),
                    "llmEmojiStyle": llm_emoji,
                    "autoEmoji": auto_emoji,
                    "replyLength": reply_length,
                    "speechRate": speech_rate,
                    "durationScale": duration_scale,
                    "audios": audios,
                    "contextStats": context_stats,
                    "webSearch": use_web_search,
                    "twoOnlyMode": two_only_mode,
                    "webQuery": web_query,
                    "webContext": web_context,
                    "webResults": search_results,
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
    CHARACTER_ROOT.mkdir(parents=True, exist_ok=True)
    httpd = ThreadingHTTPServer((host, port), Handler)
    print(f"Irodori LM Studio chat: http://{host}:{port}/", flush=True)
    httpd.serve_forever()


if __name__ == "__main__":
    main()
