#!/usr/bin/env bash
# Pre-generate the emergency instructions as audio so they play with no network and no device
# voice. PLACEHOLDER: espeak's robotic voice. Replace with a recorded human voice (reviewed Hindi)
# before field use; keep file names. Text comes from src/i18n/<lang>.json (emergency.*).
set -euo pipefail
cd "$(dirname "$0")/.."
for lang in hi en; do
  text=$(node -e "const s=require('./src/i18n/$lang.json').emergency; console.log([s.lead, s.call_108, s.call_112, s.no_wait].join(' '))")
  espeak -v "$lang" -s 140 -w /dev/stdout "$text" | ffmpeg -loglevel error -y -i pipe:0 -ac 1 -ar 22050 -b:a 32k "public/audio/emergency_$lang.mp3"
done
ls -l public/audio
