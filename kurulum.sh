#!/usr/bin/env bash
# Para Ne Diyor? — film/kurgu ve altyazı araçlarının çalışma ortamını kurar.
# Her yeni oturumda (bulut makinesi her seferinde sıfırdan açılır) bir kez çalıştır:
#     bash kurulum.sh
# Tekrar çalıştırmak güvenlidir, kurulu olanları atlar. İlk kurulum ~3-5 dk (Blender modülü ~375 MB).
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/5] Python paketleri"
if python3 -c "import bpy, cv2, numpy, OpenEXR, scipy, pyloudnorm, PIL, onnxruntime, tokenizers, transformers" 2>/dev/null; then
  echo "      zaten kurulu"
else
  # Blender'ın Python modülü (bpy 5.0.1) numpy<2 ister. Hepsini tek komutta kurmak, pip'in uyumlu
  # sürümleri birlikte seçmesini sağlar (ör. numpy 1.26 + opencv 4.11). Ayrı ayrı kurmak sürüm çakıştırır.
  pip install -q "bpy==5.0.1" "numpy<2" opencv-python-headless pillow onnxruntime tokenizers transformers \
      scipy pyloudnorm OpenEXR
fi

echo "[2/5] Fontlar (Montserrat, Inter, Instrument Serif)"
if [ -s altyazi/fonts/Montserrat.ttf ]; then echo "      zaten var"; else bash altyazi/fontlari_indir.sh; fi

echo "[3/5] Konuşmayı yazıya dökme (Whisper) ve yüz bulma (BlazeFace) modelleri"
if [ -d altyazi/models/whisper-small ]; then echo "      zaten var"; else bash altyazi/model_indir.sh; fi

echo "[4/5] Harita verisi (Natural Earth 1:10m sınırlar, göller, nehirler)"
mkdir -p tekstil/veri
for f in ne_10m_admin_0_countries ne_10m_lakes ne_10m_rivers_lake_centerlines; do
  [ -s "tekstil/veri/$f.geojson" ] || curl -sSfL -o "tekstil/veri/$f.geojson" \
    "https://raw.githubusercontent.com/nvkelso/natural-earth-vector/master/geojson/$f.geojson"
done

echo "[5/5] Kontrol"
command -v ffmpeg >/dev/null || { echo "HATA: ffmpeg bulunamadı"; exit 1; }
python3 - <<'EOF'
import bpy, cv2, numpy, OpenEXR, scipy, pyloudnorm
print(f"      Blender {bpy.app.version_string} | numpy {numpy.__version__} | OpenCV {cv2.__version__}")
EOF
echo "Hazır. Rehber: .claude/skills/film-kurgu/SKILL.md"
