"""Opt-in CX adapter. Never imports Torch in the normal desktop mode."""
from __future__ import annotations

import ast
import os
import sys
import time
from pathlib import Path

CX_SETTINGS = dict(modelDevice="cuda", modelPrecision="bf16",
                   codecDevice="cpu", codecPrecision="fp32")


def load_emoji_palette(source: Path) -> list[dict[str, str]]:
    """Read literal palette data without importing the upstream Gradio UI."""
    tree = ast.parse((source / "irodori_tts/gradio_emoji_palette.py").read_text(encoding="utf-8"))
    for node in tree.body:
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name) and node.target.id == "EMOJI_PALETTE_ITEMS":
            if not isinstance(node.value, (ast.Tuple, ast.List)):
                break
            items = []
            for call in node.value.elts:
                if not (isinstance(call, ast.Call) and isinstance(call.func, ast.Name)
                        and call.func.id == "EmojiPaletteItem" and len(call.args) == 3 and not call.keywords):
                    raise RuntimeError("Unsupported Irodori emoji palette format")
                values = [ast.literal_eval(arg) for arg in call.args]
                if not all(isinstance(value, str) for value in values):
                    raise RuntimeError("Invalid Irodori emoji palette data")
                items.append(dict(zip(("emoji", "label", "description"), values)))
            return items
    raise RuntimeError("Irodori emoji palette changed; revalidate the CX runtime")


def runtime_paths(root: Path) -> dict[str, Path]:
    root = root.resolve()
    return {
        "python": root / "venv/Scripts/python.exe",
        "source": root / "source",
        "checkpoint": root / "models/phasefield-audio--Irodori-TTS-v4.1-Anime/model.safetensors",
        "codec": root / "models/Aratako--Semantic-DACVAE-Japanese-32dim/weights.pth",
    }


def configure_environment(root: Path) -> dict[str, Path]:
    paths = runtime_paths(root)
    for name, path in paths.items():
        if not path.exists():
            raise RuntimeError(f"CX {name} missing: {path}. See docs/CX_SETUP.md")
    os.environ.update(
        IRODORI_ROOT=str(paths["source"]), IRODORI_PYTHON=str(paths["python"]),
        IRODORI_CHECKPOINT=str(paths["checkpoint"]),
        IRODORI_MODEL_DEVICE="cuda", IRODORI_MODEL_PRECISION="bf16",
        IRODORI_CODEC_DEVICE="cpu", IRODORI_CODEC_PRECISION="fp32",
        HF_HOME=str(root / "hf-cache"), HF_HUB_CACHE=str(root / "hf-cache/hub"),
        HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1",
        NUMBA_CACHE_DIR=str(root / "numba-cache"), TORCH_HOME=str(root / "torch-cache"),
        MIOPEN_USER_DB_PATH=str(root / "miopen-cache"),
    )
    return paths


class CXRuntime:
    """One resident runtime; caller holds Irodori_lock for load and synthesis."""

    def __init__(self, root: Path):
        self.root = root.resolve()
        self.paths = configure_environment(self.root)
        self.runtime = None
        self.info = {}

    def preflight(self) -> dict:
        if Path(sys.executable).resolve() != self.paths["python"].resolve():
            raise RuntimeError("CX requires its isolated Python. Use start_chat_cx.bat.")
        sys.path.insert(0, str(self.paths["source"]))
        import torch
        from irodori_tts.inference_runtime import RuntimeKey

        if not Path(torch.__file__).resolve().is_relative_to(self.root / "venv"):
            raise RuntimeError("CX Torch must come from the isolated runtime, not a shared environment.")
        if not torch.version.hip or not torch.cuda.is_available():
            raise RuntimeError("CX mode requires working ROCm GPU support; CPU fallback is disabled.")
        if "watermark_enabled" not in RuntimeKey.__dataclass_fields__:
            raise RuntimeError("CX runtime needs the optional-watermark patch. See docs/CX_SETUP.md")
        torch.set_num_threads(8)
        if not self.info:
            torch.set_num_interop_threads(2)
        self.info = dict(mode="cx", label="CX / GPU生成・CPU復元 / 透かしOFF",
                         gpu=torch.cuda.get_device_name(0), torch=torch.__version__,
                         hip=torch.version.hip, watermarkEnabled=False, **CX_SETTINGS)
        return self.info

    def synthesize(self, *, text: str, caption: str, reference: Path,
                   steps: int, duration_scale: float, output: Path) -> dict:
        import numpy as np
        import soundfile as sf
        import torch
        from irodori_tts.inference_runtime import InferenceRuntime, RuntimeKey, SamplingRequest

        if not reference.is_file():
            raise RuntimeError(f"CX reference audio missing: {reference}")
        started = time.perf_counter()
        if self.runtime is None:
            self.runtime = InferenceRuntime.from_key(RuntimeKey(
                checkpoint=str(self.paths["checkpoint"]), model_device="cuda",
                model_precision="bf16", codec_device="cpu", codec_precision="fp32",
                codec_repo=str(self.paths["codec"]), compile_model=False,
                watermark_enabled=False,
            ))
        if self.runtime.watermarker.ready:
            raise RuntimeError("CX watermark must remain disabled")
        result = self.runtime.synthesize(SamplingRequest(
            text=text, caption=caption, ref_wav=str(reference), num_steps=int(steps),
            duration_scale=float(duration_scale), cfg_scale_caption=4.0,
        ), log_fn=lambda line: print(line, flush=True))
        torch.cuda.synchronize()
        audio = result.audio.detach().float().cpu().numpy().squeeze()
        if audio.ndim != 1 or not audio.size or not np.isfinite(audio).all():
            raise RuntimeError("Invalid CX waveform")
        if float(np.sqrt(np.mean(audio ** 2))) < 1e-5:
            raise RuntimeError("CX generated silence")
        output.parent.mkdir(parents=True, exist_ok=True)
        sf.write(str(output), audio, result.sample_rate, subtype="PCM_16")
        import psutil
        memory = psutil.Process().memory_info()
        return dict(elapsed=round(time.perf_counter() - started, 3),
                    audioSeconds=len(audio) / result.sample_rate,
                    rssBytes=memory.rss, peakWorkingSetBytes=getattr(memory, "peak_wset", None),
                    availableMemoryBytes=psutil.virtual_memory().available,
                    gpuPeakAllocatedBytes=torch.cuda.max_memory_allocated(),
                    watermarkEnabled=False, runtimeMode="cx", **CX_SETTINGS)
