#!/bin/bash
# Uso: bash hacer_video.sh spec.json salida.mp4   -> vídeo con música de fondo suave
set -e
D=$(cd "$(dirname "$0")" && pwd); T=$(mktemp -d)
python3 "$D/plantilla.py" "$1" "$T/mudo.mp4"
dur=$(ffprobe -v error -show_entries format=duration -of csv=p=0 "$T/mudo.mp4")
python3 "$D/musica.py" "$T/m.wav" "$dur"
ffmpeg -y -loglevel error -i "$T/mudo.mp4" -i "$T/m.wav" -map 0:v -map 1:a -c:v copy -c:a aac -b:a 128k -af "volume=0.45" -shortest -movflags +faststart "$2"
echo "OK $2"
