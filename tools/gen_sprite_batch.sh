#!/usr/bin/env bash
# Dragon Tide: 敵スプライトをまとめて生成し、ENEMY_SPRITE_META 用の行を吐く。
#   tools/gen_sprite_batch.sh <batchfile>
# batchfile は 1行 = "name|aspect|forward|description"（# 始まりはコメント）。
#
# forward は本編の描き方:
#   up   … 進行方向へ回す（絵の上が前）
#   none … 回さない（飛行・静止塔・浮遊物）
#
# drawScale は既存の敵に合わせた規則で自動算出する:
#   縦長 → 描画高さ = 半径 × 3.6（= drawScale 3.6 * w/h）
#   横長 → 描画幅   = 半径 × 2.8
# ※ pack（複数体で1隊）の敵は**1体だけ**を描かせること。本編は個体ごとに1枚描く。
set -u
BATCH="$1"
OUT_META="${2:-/dev/stdout}"
: > "$OUT_META.tmp"

while IFS='|' read -r NAME ASPECT FORWARD DESC; do
  [ -z "${NAME:-}" ] && continue
  case "$NAME" in \#*) continue;; esac
  echo "--- $NAME"
  LINE=$(bash tools/gen_enemy_sprite.sh "$NAME" "$DESC" "$ASPECT" 2>&1 | tail -1)
  echo "    $LINE"
  # sprite_clean.py の出力: <path>: WxH  pivot=(..)  pivot_frac=(px,py)  ...
  SIZE=$(echo "$LINE" | sed -n 's/.*: \([0-9]*\)x\([0-9]*\) .*/\1 \2/p')
  FRAC=$(echo "$LINE" | sed -n 's/.*pivot_frac=(\([0-9.]*\),\([0-9.]*\)).*/\1 \2/p')
  if [ -z "$SIZE" ] || [ -z "$FRAC" ]; then echo "    !! メタを読めなかった"; continue; fi
  W=$(echo "$SIZE" | cut -d' ' -f1); H=$(echo "$SIZE" | cut -d' ' -f2)
  PX=$(echo "$FRAC" | cut -d' ' -f1); PY=$(echo "$FRAC" | cut -d' ' -f2)
  SCALE=$(awk -v w="$W" -v h="$H" 'BEGIN{ if (h>=w) printf "%.2f", 3.6*w/h; else printf "%.2f", 2.8 }')
  printf '  %-16s{ px: %s, py: %s, forward: "%s", drawScale: %s },\n' \
    "$NAME:" "$PX" "$PY" "$FORWARD" "$SCALE" >> "$OUT_META.tmp"
done < "$BATCH"

echo "=== ENEMY_SPRITE_META に貼る行 ==="
cat "$OUT_META.tmp"
