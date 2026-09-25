#!/usr/bin/env bash
# Altyazıda kullanılan ücretsiz (OFL lisanslı) Google fontlarını indirir.
set -e
cd "$(dirname "$0")" && mkdir -p fonts && cd fonts
B=https://raw.githubusercontent.com/google/fonts/main/ofl
curl -sfL -o Montserrat.ttf "$B/montserrat/Montserrat%5Bwght%5D.ttf"
curl -sfL -o Inter.ttf "$B/inter/Inter%5Bopsz,wght%5D.ttf"
curl -sfL -o InstrumentSerif-Italic.ttf "$B/instrumentserif/InstrumentSerif-Italic.ttf"
echo "Fontlar indirildi."
