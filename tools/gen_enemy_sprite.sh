#!/usr/bin/env bash
# Dragon Tide: 敵1体ぶんのスプライトを生成 → 透過 → 整形。
#   tools/gen_enemy_sprite.sh <name> "<描写>" [aspect]
# 敵は sprites.md のカテゴリG（1枚絵・回転のみ）。頭/正面が画像の上を向くこと。
set -u
NAME="$1"; DESC="$2"; ASPECT="${3:-1:1}"
G=/c/forge/ClaudeCodeForge
PY=/c/Users/syuta/AppData/Local/Programs/Python/Python311/python.exe
OUT="$(pwd)/prototypes/dragon-tide/assets"
TMP="${SPRITE_TMP:-/c/tmp/dt-sprites}"; mkdir -p "$TMP"

PROMPT="Top-down view seen from directly above, orthographic. Flat cel-shaded illustration style, bold clean silhouette, thick dark ink outlines, high contrast, no painterly texture. Solid flat pure green background (#00FF00) for chroma key removal, no ground, no shadow, no other objects. IMPORTANT: the subject is drawn occupying only the middle 65 percent of the image, with a WIDE EMPTY GREEN BORDER on all four sides. Nothing may touch the image edges. The subject faces toward the TOP of the image. $DESC"

export GEMINI_API_KEY=$(powershell -Command "[System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User')" | tr -d '\r')
export PYTHONIOENCODING=utf-8
before=$(ls -1 "$G/output/gemini-generated" | tail -1)
(cd "$G" && $PY generate_gemini.py "$PROMPT" --aspect "$ASPECT" --size 1K >/dev/null 2>&1)
after=$(ls -1 "$G/output/gemini-generated" | tail -1)
if [ "$before" = "$after" ]; then echo "  !! $NAME の生成に失敗"; exit 1; fi
$PY "$G/chroma_key.py" "$G/output/gemini-generated/$after" "$TMP/$NAME.raw.png" >/dev/null 2>&1
$PY tools/sprite_clean.py "$TMP/$NAME.raw.png" "$OUT/mover_$NAME.png"
