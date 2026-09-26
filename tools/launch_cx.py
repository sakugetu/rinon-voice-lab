"""Launch using a local, explicit runtime registration; no installs or LM operations."""
import argparse
import json
import os
from pathlib import Path
import subprocess
import sys

APP = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(APP))
from cx_runtime import runtime_paths


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--runtime-root", type=Path)
    parser.add_argument("--register", action="store_true")
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    config = APP / "cx.local.json"
    if args.runtime_root:
        root = args.runtime_root.resolve()
    elif config.exists():
        root = Path(json.loads(config.read_text(encoding="utf-8-sig"))["runtimeRoot"])
    else:
        parser.error("Register the tested runtime first: --runtime-root PATH --register --check")
    paths = runtime_paths(root)
    for path in paths.values():
        if not path.exists():
            parser.error(f"Missing CX runtime file: {path}")
    env = os.environ.copy()
    env.update(RINON_MODE="cx", RINON_CX_RUNTIME=str(root), PYTHONUTF8="1",
               PYTHONDONTWRITEBYTECODE="1")
    command = [str(paths["python"]), "-X", "utf8", "-B", str(APP / "app.py")]
    if args.check or args.register:
        subprocess.run(command + ["--check-runtime"], env=env, cwd=APP, check=True, timeout=120)
    if args.register:
        if config.exists():
            parser.error("cx.local.json already exists. Back it up and edit runtimeRoot explicitly.")
        config.write_text(json.dumps({"runtimeRoot": str(root)}, indent=2) + "\n", encoding="utf-8")
        print(f"Registered: {config}")
    if not args.check:
        return subprocess.call(command, env=env, cwd=APP)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
