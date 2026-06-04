from __future__ import annotations

import base64
import json
import os
import re
import sys
import threading
import time
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(os.environ.get("IRODORI_ROOT", str(Path(__file__).resolve().parents[2] / "Irodori-TTS"))).resolve()
CHECKPOINT = os.environ.get("IRODORI_CHECKPOINT", "Aratako/Irodori-TTS-600M-v3-VoiceDesign")
REF_WAV = os.environ.get(
    "LUVIA_REMOTE_REF_WAV",
    str(ROOT / "remote_refs" / "luvia_smoky_radio_pitchdown3_ref.wav"),
)
HOST = os.environ.get("LUVIA_SERVER_HOST", "0.0.0.0")
PORT = int(os.environ.get("LUVIA_SERVER_PORT", "7874"))

generation_lock = threading.Lock()
irodori_module = None


def json_bytes(payload: object) -> bytes:
    return json.dumps(payload, ensure_ascii=False).encode("utf-8")


def ensure_module():
    global irodori_module
    if irodori_module is not None:
        return irodori_module
    sys.path.insert(0, str(ROOT))
    old_cwd = Path.cwd()
    os.chdir(ROOT)
    try:
        import gradio_app_voicedesign as app_vd

        irodori_module = app_vd
        return irodori_module
    finally:
        os.chdir(old_cwd)


def read_json_body(handler: BaseHTTPRequestHandler) -> dict:
    length = int(handler.headers.get("Content-Length", "0"))
    raw = handler.rfile.read(length) if length else b"{}"
    return json.loads(raw.decode("utf-8")) if raw else {}


def synthesize(payload: dict) -> dict:
    module = ensure_module()
    text = str(payload.get("text") or "").strip()
    caption = str(payload.get("caption") or "").strip()
    if not text:
        raise ValueError("text is required")
    steps = max(1, min(120, int(payload.get("steps") or 12)))
    duration_scale = float(payload.get("durationScale") or 1.0)
    ref_wav = str(payload.get("refWav") or REF_WAV)
    old_cwd = Path.cwd()
    os.chdir(ROOT)
    try:
        with generation_lock:
            start = time.perf_counter()
            result = module._run_generation(
                CHECKPOINT,
                "cuda",
                "bf16",
                "cuda",
                "bf16",
                text,
                caption,
                ref_wav if Path(ref_wav).exists() else None,
                steps,
                1,
                "",
                "",
                duration_scale,
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
    wav_path = (ROOT / match.group(1).strip()).resolve()
    return {
        "ok": True,
        "audioBase64": base64.b64encode(wav_path.read_bytes()).decode("ascii"),
        "elapsed": round(elapsed, 3),
        "source": str(wav_path),
        "reference": ref_wav if Path(ref_wav).exists() else "",
        "durationScale": duration_scale,
    }


class Handler(BaseHTTPRequestHandler):
    server_version = "LuviaIrodoriServer/0.1"

    def send_json(self, status: int, payload: object) -> None:
        body = json_bytes(payload)
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format: str, *args) -> None:
        return

    def do_GET(self) -> None:
        if self.path.split("?", 1)[0] == "/health":
            self.send_json(
                200,
                {
                    "ok": True,
                    "root": str(ROOT),
                    "checkpoint": CHECKPOINT,
                    "referenceExists": Path(REF_WAV).exists(),
                    "modelLoaded": irodori_module is not None,
                },
            )
            return
        self.send_json(404, {"error": "not found"})

    def do_POST(self) -> None:
        if self.path.split("?", 1)[0] != "/synthesize":
            self.send_json(404, {"error": "not found"})
            return
        try:
            self.send_json(200, synthesize(read_json_body(self)))
        except Exception as exc:
            self.send_json(500, {"ok": False, "error": str(exc)})


def main() -> None:
    ROOT.mkdir(parents=True, exist_ok=True)
    (ROOT / "outputs").mkdir(exist_ok=True)
    server = ThreadingHTTPServer((HOST, PORT), Handler)
    print(f"Luvia Irodori server listening on {HOST}:{PORT}", flush=True)
    server.serve_forever()


if __name__ == "__main__":
    main()
