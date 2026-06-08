from __future__ import annotations

import base64
import contextlib
import json
import os
import re
import sys
import threading
import time
import warnings
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path


ROOT = Path(os.environ.get("IRODORI_ROOT", str(Path(__file__).resolve().parents[2] / "Irodori-TTS"))).resolve()
CHECKPOINT = os.environ.get("IRODORI_CHECKPOINT", "Aratako/Irodori-TTS-600M-v3-VoiceDesign")
DEFAULT_IRODORI_RUNTIME = "auto"
MODEL_DEVICE = os.environ.get(
    "IRODORI_MODEL_DEVICE",
    os.environ.get("IRODORI_DEVICE", DEFAULT_IRODORI_RUNTIME),
).strip() or DEFAULT_IRODORI_RUNTIME
MODEL_PRECISION = os.environ.get(
    "IRODORI_MODEL_PRECISION",
    os.environ.get("IRODORI_PRECISION", DEFAULT_IRODORI_RUNTIME),
).strip() or DEFAULT_IRODORI_RUNTIME
CODEC_DEVICE = os.environ.get(
    "IRODORI_CODEC_DEVICE",
    os.environ.get("IRODORI_DEVICE", DEFAULT_IRODORI_RUNTIME),
).strip() or DEFAULT_IRODORI_RUNTIME
CODEC_PRECISION = os.environ.get(
    "IRODORI_CODEC_PRECISION",
    os.environ.get("IRODORI_PRECISION", DEFAULT_IRODORI_RUNTIME),
).strip() or DEFAULT_IRODORI_RUNTIME
REF_WAV = os.environ.get(
    "LUVIA_REMOTE_REF_WAV",
    str(ROOT / "remote_refs" / "luvia_smoky_radio_pitchdown3_ref.wav"),
)
HOST = os.environ.get("LUVIA_SERVER_HOST", "0.0.0.0")
PORT = int(os.environ.get("LUVIA_SERVER_PORT", "7874"))

generation_lock = threading.Lock()
irodori_module = None

warnings.filterwarnings(
    "ignore",
    message=r"`torch\.nn\.utils\.weight_norm` is deprecated in favor of `torch\.nn\.utils\.parametrizations\.weight_norm`.*",
    category=FutureWarning,
)


def suppress_irodori_log_line(line: str) -> bool:
    return line.startswith(
        (
            "Using the default SDR of ",
            "WARNING! Reducing the sampling rate of the original audio from ",
        )
    )


class FilteredIrodoriStdout:
    def __init__(self, target) -> None:
        self.target = target
        self.buffer = ""

    def write(self, text: str) -> int:
        self.buffer += text
        while "\n" in self.buffer:
            line, self.buffer = self.buffer.split("\n", 1)
            if not suppress_irodori_log_line(line):
                self.target.write(f"{line}\n")
        return len(text)

    def flush(self) -> None:
        if self.buffer:
            if not suppress_irodori_log_line(self.buffer):
                self.target.write(self.buffer)
            self.buffer = ""
        self.target.flush()


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

        quiet_irodori_watermark_warnings()
        irodori_module = app_vd
        return irodori_module
    finally:
        os.chdir(old_cwd)


def quiet_irodori_watermark_warnings() -> None:
    import irodori_tts.inference_runtime as inference_runtime

    base_watermarker = inference_runtime.SilentCipherWatermarker
    if getattr(base_watermarker, "__rinon_quiet__", False):
        return

    class QuietSilentCipherWatermarker(base_watermarker):
        __rinon_quiet__ = True

        def __init__(self, *args, **kwargs) -> None:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"`torch\.nn\.utils\.weight_norm` is deprecated in favor of `torch\.nn\.utils\.parametrizations\.weight_norm`.*",
                    category=FutureWarning,
                )
                super().__init__(*args, **kwargs)

        def encode_batch(self, audios: list, *, sample_rate: int) -> list:
            with warnings.catch_warnings():
                warnings.filterwarnings(
                    "ignore",
                    message=r"An output with one or more elements was resized since it had shape \[\].*",
                    category=UserWarning,
                )
                with contextlib.redirect_stdout(FilteredIrodoriStdout(sys.stdout)):
                    return super().encode_batch(audios, sample_rate=sample_rate)

    inference_runtime.SilentCipherWatermarker = QuietSilentCipherWatermarker


def is_auto_runtime_value(value: str) -> bool:
    return str(value or "").strip().lower() in {"", "auto", "default"}


def default_irodori_runtime_device() -> str:
    from irodori_tts.inference_runtime import default_runtime_device

    return default_runtime_device()


def irodori_precision_for_device(device: str, requested: str) -> str:
    if not is_auto_runtime_value(requested):
        return str(requested).strip().lower()
    from irodori_tts.inference_runtime import list_available_runtime_precisions

    choices = list_available_runtime_precisions(device)
    device_type = str(device).split(":", 1)[0].lower()
    if device_type in {"cuda", "xpu"} and "bf16" in choices:
        return "bf16"
    return choices[0] if choices else "fp32"


def irodori_runtime_settings(payload: dict | None = None) -> dict[str, str]:
    payload = payload or {}
    model_device = str(payload.get("modelDevice") or MODEL_DEVICE)
    model_precision = str(payload.get("modelPrecision") or MODEL_PRECISION)
    codec_device = str(payload.get("codecDevice") or CODEC_DEVICE)
    codec_precision = str(payload.get("codecPrecision") or CODEC_PRECISION)
    if is_auto_runtime_value(model_device) or is_auto_runtime_value(codec_device):
        default_device = default_irodori_runtime_device()
        if is_auto_runtime_value(model_device):
            model_device = default_device
        if is_auto_runtime_value(codec_device):
            codec_device = default_device
    return {
        "modelDevice": model_device.strip().lower(),
        "modelPrecision": irodori_precision_for_device(model_device, model_precision),
        "codecDevice": codec_device.strip().lower(),
        "codecPrecision": irodori_precision_for_device(codec_device, codec_precision),
    }


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
            runtime = irodori_runtime_settings(payload)
            start = time.perf_counter()
            result = module._run_generation(
                CHECKPOINT,
                runtime["modelDevice"],
                runtime["modelPrecision"],
                runtime["codecDevice"],
                runtime["codecPrecision"],
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
        "modelDevice": runtime["modelDevice"],
        "modelPrecision": runtime["modelPrecision"],
        "codecDevice": runtime["codecDevice"],
        "codecPrecision": runtime["codecPrecision"],
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
                    "modelDevice": MODEL_DEVICE,
                    "modelPrecision": MODEL_PRECISION,
                    "codecDevice": CODEC_DEVICE,
                    "codecPrecision": CODEC_PRECISION,
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
