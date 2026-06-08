#!/usr/bin/env bash
set -euo pipefail

APP_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

export IRODORI_ROOT="${IRODORI_ROOT:-"$APP_ROOT/../Irodori-TTS"}"
export IRODORI_TORCH_EXTRA="${IRODORI_TORCH_EXTRA:-cpu}"
export IRODORI_PYTHON_VERSION="${IRODORI_PYTHON_VERSION:-3.10}"
export IRODORI_MODEL_DEVICE="${IRODORI_MODEL_DEVICE:-auto}"
export IRODORI_MODEL_PRECISION="${IRODORI_MODEL_PRECISION:-auto}"
export IRODORI_CODEC_DEVICE="${IRODORI_CODEC_DEVICE:-auto}"
export IRODORI_CODEC_PRECISION="${IRODORI_CODEC_PRECISION:-auto}"

IRODORI_PYTHON="$IRODORI_ROOT/.venv/bin/python"

if [ ! -x "$IRODORI_PYTHON" ]; then
  echo "Irodori-TTS was not found at $IRODORI_ROOT."
  echo "Installing Irodori-TTS. This may take a while."
  bash "$APP_ROOT/tools/install_irodori_tts.sh"
fi

exec "$IRODORI_PYTHON" "$APP_ROOT/app.py"
