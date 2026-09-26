import importlib.util
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import threading
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
import cx_runtime


def load_app():
    spec = importlib.util.spec_from_file_location("tested_app", ROOT / "app.py")
    module = importlib.util.module_from_spec(spec)
    with patch.dict(os.environ, {"RINON_MODE": "standard"}):
        spec.loader.exec_module(module)
    return module


class RuntimeModes(unittest.TestCase):
    def test_palette_read_does_not_import_gradio_or_execute_source(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            (root / "irodori_tts").mkdir()
            palette = root / "irodori_tts/gradio_emoji_palette.py"
            palette.write_text('raise RuntimeError("must not execute")\nEMOJI_PALETTE_ITEMS: tuple = (EmojiPaletteItem("x", "label", "desc"),)\n', encoding="utf-8")
            self.assertEqual(cx_runtime.load_emoji_palette(root)[0]["emoji"], "x")

    def test_standard_explicit_cpu_and_cuda_unchanged(self):
        app = load_app()
        self.assertIsNone(app.CX_runtime)
        for device, precision in [("cpu", "fp32"), ("cuda", "bf16")]:
            app.IRODORI_MODEL_DEVICE = app.IRODORI_CODEC_DEVICE = device
            app.IRODORI_MODEL_PRECISION = app.IRODORI_CODEC_PRECISION = precision
            self.assertEqual(app.irodori_runtime_settings(), dict(
                modelDevice=device, modelPrecision=precision,
                codecDevice=device, codecPrecision=precision))

    def test_standard_auto_respects_runtime(self):
        app = load_app()
        app.IRODORI_MODEL_DEVICE = app.IRODORI_CODEC_DEVICE = "auto"
        app.IRODORI_MODEL_PRECISION = app.IRODORI_CODEC_PRECISION = "auto"
        with patch.object(app, "default_irodori_runtime_device", return_value="mps"), \
             patch.object(app, "irodori_precision_for_device", return_value="fp32"):
            self.assertEqual(app.irodori_runtime_settings()["modelDevice"], "mps")

    def test_unknown_mode_and_missing_runtime_fail(self):
        for env in [{"RINON_MODE": "typo"}, {"RINON_MODE": "cx", "RINON_CX_RUNTIME": ""}]:
            result = subprocess.run([sys.executable, "-B", str(ROOT / "app.py"), "--check-runtime"],
                                    env={**os.environ, **env}, capture_output=True, timeout=15)
            self.assertNotEqual(result.returncode, 0)

    def test_cx_does_not_fallback_to_legacy_and_serializes(self):
        app = load_app()
        fake = Mock(info={"mode": "cx"})
        app.Emoji_items_cache = []
        active = 0
        max_active = 0
        def generate(**kwargs):
            nonlocal active, max_active
            active += 1
            max_active = max(active, max_active)
            time.sleep(.02)
            active -= 1
            return {**cx_runtime.CX_SETTINGS, "runtimeMode": "cx", "watermarkEnabled": False}
        fake.synthesize.side_effect = generate
        app.CX_runtime = fake
        app.ensure_irodori_module = Mock(side_effect=AssertionError("legacy must not load"))
        results = []
        def speak():
            results.append(app.synthesize_sentence("テスト", 1, 40, emoji_style="", duration_scale=.9))
        threads = [threading.Thread(target=speak) for _ in range(3)]
        for thread in threads: thread.start()
        for thread in threads: thread.join()
        self.assertEqual(len(results), 3)
        self.assertEqual(max_active, 1)
        self.assertEqual(len({r["url"] for r in results}), 3)
        self.assertFalse(results[0]["watermarkEnabled"])
        self.assertEqual(fake.synthesize.call_args.kwargs["duration_scale"], .9)

    def test_missing_runtime_does_not_change_environment(self):
        with tempfile.TemporaryDirectory() as directory, patch.dict(os.environ):
            before = dict(os.environ)
            with self.assertRaises(RuntimeError):
                cx_runtime.configure_environment(Path(directory))
            self.assertEqual(dict(os.environ), before)


if __name__ == "__main__":
    unittest.main()
