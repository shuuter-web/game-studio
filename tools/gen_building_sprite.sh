#!/usr/bin/env bash
# Dragon Tide: 建物1つぶんのスプライトを生成 → 透過 → 整形。
#   tools/gen_building_sprite.sh <name> "<描写>" [aspect]
# 出力: prototypes/dragon-tide/assets/building_<name>.png
#
# 建物は**無彩色で作る**こと。本編は getTintedBuildingSprite で
# 街ごとの色を multiply して乗せるので、色付きで作ると濁る。
# 時代の違いは「色」ではなく**建築の形**で出す。
set -u
NAME="$1"; DESC="$2"; ASPECT="${3:-1:1}"
G=/c/forge/ClaudeCodeForge
PY=/c/Users/syuta/AppData/Local/Programs/Python/Python311/python.exe
OUT="$(pwd)/prototypes/dragon-tide/assets"
TMP="${SPRITE_TMP:-/c/tmp/dt-sprites}"; mkdir -p "$TMP"

PROMPT="Top-down view seen from directly above, orthographic, architectural roof plan. A SINGLE isolated building. Flat cel-shaded illustration, bold clean silhouette, thick dark ink outlines, high contrast, no painterly texture. STRICTLY GREYSCALE: only neutral greys, white and black, absolutely no color of any kind. Solid flat pure green background (#00FF00) for chroma key removal, no ground, no terrain, no shadow, no other objects, no people. IMPORTANT: the building is drawn occupying only the middle 70 percent of the image, with a WIDE EMPTY GREEN BORDER on all four sides. Nothing may touch the image edges. $DESC"

export GEMINI_API_KEY=$(powershell -Command "[System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User')" | tr -d '\r')
export PYTHONIOENCODING=utf-8
before=$(ls -1 "$G/output/gemini-generated" | tail -1)
(cd "$G" && $PY generate_gemini.py "$PROMPT" --aspect "$ASPECT" --size 1K >/dev/null 2>&1)
after=$(ls -1 "$G/output/gemini-generated" | tail -1)
if [ "$before" = "$after" ]; then echo "  !! $NAME の生成に失敗"; exit 1; fi
$PY "$G/chroma_key.py" "$G/output/gemini-generated/$after" "$TMP/b_$NAME.raw.png" >/dev/null 2>&1
$PY tools/sprite_clean.py "$TMP/b_$NAME.raw.png" "$OUT/building_$NAME.png"
