#!/usr/bin/env bash
# Konuşmayı yazıya dökmek için Whisper-small modelini indirir (~250 MB).
# Model, npm'deki "sts-whisper-small" paketinden alınır (Xenova/whisper-small, ONNX, Apache-2.0).
set -e
cd "$(dirname "$0")" && mkdir -p models
url=$(curl -sf https://registry.npmjs.org/sts-whisper-small/latest | python3 -c "import sys,json;print(json.load(sys.stdin)['dist']['tarball'])")
curl -sfL "$url" | tar xz -C models
rm -rf models/whisper-small && mv models/package/models/Xenova/whisper-small models/whisper-small && rm -rf models/package
echo "Model indirildi: altyazi/models/whisper-small"
