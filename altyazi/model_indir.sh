#!/usr/bin/env bash
# Altyazı araçlarının kullandığı modelleri npm'den indirir.
#  - Whisper-small (~250 MB): konuşmayı yazıya dökmek için
#    ("sts-whisper-small" paketi: Xenova/whisper-small, ONNX, Apache-2.0)
#  - BlazeFace (~0.6 MB): tam ekran videolarda yüzün yerini bulmak için
#    ("jp.keijiro.mediapipe.blazeface" paketi: MediaPipe BlazeFace, ONNX, Apache-2.0)
set -e
cd "$(dirname "$0")" && mkdir -p models
tarball() { curl -sf "https://registry.npmjs.org/$1/latest" | python3 -c "import sys,json;print(json.load(sys.stdin)['dist']['tarball'])"; }

curl -sfL "$(tarball sts-whisper-small)" | tar xz -C models
rm -rf models/whisper-small && mv models/package/models/Xenova/whisper-small models/whisper-small && rm -rf models/package
echo "Model indirildi: altyazi/models/whisper-small"

curl -sfL "$(tarball jp.keijiro.mediapipe.blazeface)" | tar xz -C models
rm -rf models/blazeface && mkdir -p models/blazeface
mv models/package/ONNX/face_detection_back_256x256_barracuda.onnx models/package/LICENSE models/blazeface/ && rm -rf models/package
echo "Model indirildi: altyazi/models/blazeface"
