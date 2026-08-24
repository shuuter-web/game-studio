#!/usr/bin/env bash
# Dragon Tide: 竜1種ぶんの body / wing を生成 → 透過 → 整形 まで一気に通す。
#   tools/gen_dragon_sprite.sh <species> "<体の描写>" "<翼の描写>"
# 画風・構図の指定は docs/tdd/dragon-tide-sprites.md §3 の通った型をそのまま使う。
set -u
SPECIES="$1"; BODY_DESC="$2"; WING_DESC="$3"
G=/c/forge/ClaudeCodeForge
PY=/c/Users/syuta/AppData/Local/Programs/Python/Python311/python.exe
OUT="$(pwd)/prototypes/dragon-tide/assets"
TMP="${SPRITE_TMP:-/tmp/dt-sprites}"; mkdir -p "$TMP"

COMMON="Top-down view seen from directly above. Flat cel-shaded illustration style, bold clean silhouette, thick dark ink outlines, high contrast, no painterly texture. Solid flat pure green background (#00FF00) for chroma key removal, no ground, no shadow, no other objects."

BODY_PROMPT="$COMMON Perfectly centered and symmetric, comfortable green margin on all sides. Dragon body and head only, seen from directly above, snout pointing toward the TOP of the image. NO WINGS. NO TAIL - the body ends just behind the hind legs with only a tiny tail stub. Bilaterally symmetric along the vertical axis. Compact reptilian silhouette, NOT humanoid and NOT bodybuilder muscular. $BODY_DESC"

WING_PROMPT="$COMMON ONE single dragon wing, isolated. IMPORTANT: the wing is drawn SMALL, occupying only the middle 60 percent of the image, with a WIDE EMPTY GREEN BORDER on all four sides. Nothing may touch or approach the image edges. Composition: the shoulder end of the wing is in the RIGHT THIRD, the wrist knuckle in the UPPER RIGHT, and the outer wing sweeps LEFTWARD with the wing tip ending well before the LEFT EDGE. Only ONE wing. Do NOT draw a second wing. Do NOT draw a mirrored copy. No body, no head, no neck, no tail, no legs. $WING_DESC"

gen () {  # $1=prompt $2=aspect $3=outname
  local before after
  before=$(ls -1 "$G/output/gemini-generated" | tail -1)
  (cd "$G" && $PY generate_gemini.py "$1" --aspect "$2" --size 1K >/dev/null 2>&1)
  after=$(ls -1 "$G/output/gemini-generated" | tail -1)
  if [ "$before" = "$after" ]; then echo "  !! $3 の生成に失敗"; return 1; fi
  $PY "$G/chroma_key.py" "$G/output/gemini-generated/$after" "$TMP/$3.raw.png" >/dev/null 2>&1
  $PY tools/sprite_clean.py "$TMP/$3.raw.png" "$OUT/$3.png"
}

export GEMINI_API_KEY=$(powershell -Command "[System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User')" | tr -d '\r')
export PYTHONIOENCODING=utf-8
echo "== $SPECIES =="
gen "$BODY_PROMPT" 1:1  "dragon_${SPECIES}_body"
gen "$WING_PROMPT" 16:9 "dragon_${SPECIES}_wing"
