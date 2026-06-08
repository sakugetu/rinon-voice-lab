#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
APP_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"

IRODORI_ROOT="${IRODORI_ROOT:-"$APP_ROOT/../Irodori-TTS"}"
IRODORI_REPOSITORY_URL="${IRODORI_REPOSITORY_URL:-https://github.com/Aratako/Irodori-TTS.git}"
IRODORI_TORCH_EXTRA="${IRODORI_TORCH_EXTRA:-cpu}"
IRODORI_PYTHON_VERSION="${IRODORI_PYTHON_VERSION:-3.10}"

require_command() {
  local name="$1"
  local hint="$2"
  if ! command -v "$name" >/dev/null 2>&1; then
    echo "$name was not found. $hint" >&2
    exit 1
  fi
}

require_command git "Install Git and rerun this script."
require_command uv "Install uv from https://docs.astral.sh/uv/ and rerun this script."

mkdir -p "$(dirname "$IRODORI_ROOT")"

if [ ! -d "$IRODORI_ROOT" ]; then
  echo "Cloning Irodori-TTS into $IRODORI_ROOT"
  git clone "$IRODORI_REPOSITORY_URL" "$IRODORI_ROOT"
elif [ ! -f "$IRODORI_ROOT/pyproject.toml" ]; then
  echo "IRODORI_ROOT exists but does not look like Irodori-TTS: $IRODORI_ROOT" >&2
  exit 1
fi

cd "$IRODORI_ROOT"
echo "Installing Irodori-TTS dependencies with uv extra '$IRODORI_TORCH_EXTRA' and Python $IRODORI_PYTHON_VERSION"
uv sync --python "$IRODORI_PYTHON_VERSION" --extra "$IRODORI_TORCH_EXTRA"

PYTHON="$IRODORI_ROOT/.venv/bin/python"
if [ ! -x "$PYTHON" ]; then
  echo "Expected virtual environment was not created: $PYTHON" >&2
  exit 1
fi

"$PYTHON" - <<'PY'
import importlib.util

missing = [
    name for name in ("gradio", "torch", "soundfile")
    if importlib.util.find_spec(name) is None
]
if missing:
    raise SystemExit("Missing modules after install: " + ", ".join(missing))

import torch

print("Irodori-TTS environment looks ready.")
print("torch:", torch.__version__)
print("cuda:", torch.cuda.is_available())
print("mps:", bool(getattr(torch.backends, "mps", None) and torch.backends.mps.is_available()))
PY

echo "Irodori-TTS install complete: $IRODORI_ROOT"
