#!/bin/sh
# Installs Kokoro TTS and downloads its model files (from GitHub releases) into voice/.
set -e
cd "$(dirname "$0")"
pip install --break-system-packages -q kokoro-onnx soundfile
mkdir -p voice
B=https://github.com/thewh1teagle/kokoro-onnx/releases/download/model-files-v1.0
[ -s voice/kokoro-v1.0.onnx ] || curl -sSL -o voice/kokoro-v1.0.onnx $B/kokoro-v1.0.onnx
[ -s voice/voices-v1.0.bin ] || curl -sSL -o voice/voices-v1.0.bin $B/voices-v1.0.bin
python3 -c "import kokoro_onnx" && ls -la voice/kokoro-v1.0.onnx voice/voices-v1.0.bin
