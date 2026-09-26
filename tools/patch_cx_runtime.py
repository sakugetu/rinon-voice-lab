"""Apply only the two validated compatibility patches to an isolated runtime."""
import argparse
import hashlib
import json
from pathlib import Path

CHANGES = {
    "source/irodori_tts/watermark.py": [(
        'def __init__(self, *, device: str, model_type: str = "44.1k") -> None:\n        self.model = self._load_backend(device=device, model_type=model_type)',
        'def __init__(self, *, device: str, model_type: str = "44.1k", enabled: bool = True) -> None:\n        self.model = self._load_backend(device=device, model_type=model_type) if enabled else None')],
    "source/irodori_tts/inference_runtime.py": [
        ('    compile_dynamic: bool = False\n', '    compile_dynamic: bool = False\n    watermark_enabled: bool = True\n'),
        ('self.watermarker = SilentCipherWatermarker(device=str(self.codec_device))',
         'self.watermarker = SilentCipherWatermarker(device=str(self.codec_device), enabled=key.watermark_enabled)'),
        ('                    "watermarked."\n                )',
         '                    "watermarked."\n                ) if self.key.watermark_enabled else "info: SilentCipher watermark disabled by RuntimeKey.watermark_enabled=False."')],
    "venv/Lib/site-packages/audiotools/ml/decorators.py": [(
        '        op: dist.ReduceOp = dist.ReduceOp.AVG,',
        '        op: "dist.ReduceOp" = dist.ReduceOp.AVG if dist.is_available() else None,')],
}


def patch_runtime(root: Path):
    root = root.resolve(strict=True)
    if not (root / "venv/Scripts/python.exe").is_file():
        raise RuntimeError("Expected an isolated Windows runtime with venv/Scripts/python.exe")
    pending = []
    for relative, changes in CHANGES.items():
        path = (root / relative).resolve(strict=True)
        if not path.is_relative_to(root):
            raise RuntimeError(f"Refusing a source outside runtime: {path}")
        before = path.read_bytes()
        after = before.decode("utf-8").replace("\r\n", "\n")
        changed = False
        for old, new in changes:
            if after.count(new) == 1:
                continue
            if after.count(old) != 1:
                raise RuntimeError(f"Unknown source version: {relative}; no files changed")
            after = after.replace(old, new)
            changed = True
        compile(after, str(path), "exec")
        if changed:
            pending.append((relative, path, before, after.encode("utf-8")))
    # Validate every target before writing any source file. Preserve originals once.
    backups = root / "patches/rinon-cx-originals"
    if not backups.resolve().is_relative_to(root):
        raise RuntimeError("Backup directory escapes runtime")
    for relative, path, before, after in pending:
        backup = backups / relative
        if not backup.resolve().is_relative_to(root):
            raise RuntimeError("Backup path escapes runtime")
        if backup.exists() and backup.read_bytes() != before:
            raise RuntimeError(f"Conflicting backup: {backup}; no files changed")
    manifest = []
    for relative, path, before, after in pending:
        backup = backups / relative
        backup.parent.mkdir(parents=True, exist_ok=True)
        if not backup.exists():
            backup.write_bytes(before)
        path.write_bytes(after)
        manifest.append(dict(path=relative, before=hashlib.sha256(before).hexdigest(),
                             after=hashlib.sha256(after).hexdigest()))
    if manifest:
        (backups / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    return manifest


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--runtime-root", type=Path, required=True)
    args = parser.parse_args()
    print(json.dumps(patch_runtime(args.runtime_root), indent=2))
