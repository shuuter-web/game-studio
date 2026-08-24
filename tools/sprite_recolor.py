"""スプライトの色みをゲーム内パレットへ寄せる。

生成AIは指定した色から外れることがある（蛙竜は「明るいライム」と書いてもオリーブ色で出た）。
作り直すより、**主線を残したまま中間色だけ目標の色相へ寄せる**方が速くて確実。

  python tools/sprite_recolor.py <in.png> <out.png> --hue 97.6 --sat 0.60 --val 1.45

  --hue  目標の色相（度）。ゲーム内パレット（DRAGON_ELEMENT_COLORS）の色から取る
  --sat  彩度の下限（0-1）
  --val  明度の倍率（主線＝暗い画素は対象外なので黒つぶれしない）
"""
import sys, colorsys
from PIL import Image
import numpy as np

def recolor(src, dst, hue_deg, sat_min, val_mul, line_v=0.30):
    im = Image.open(src).convert("RGBA")
    arr = np.array(im).astype(np.float32)
    rgb, a = arr[:, :, :3] / 255.0, arr[:, :, 3]
    out = rgb.copy()
    h, w, _ = rgb.shape
    tgt_h = (hue_deg % 360) / 360.0
    changed = 0
    for y in range(h):
        for x in range(w):
            if a[y, x] < 40:
                continue
            r, g, b = rgb[y, x]
            hh, ss, vv = colorsys.rgb_to_hsv(r, g, b)
            if vv <= line_v:      # 主線・影は触らない（触ると輪郭が溶ける）
                continue
            nr, ng, nb = colorsys.hsv_to_rgb(tgt_h, max(ss, sat_min), min(1.0, vv * val_mul))
            out[y, x] = (nr, ng, nb)
            changed += 1
    arr[:, :, :3] = np.clip(out * 255.0, 0, 255)
    Image.fromarray(arr.astype(np.uint8)).save(dst, optimize=True)
    print(f"{dst}: recolored {changed} px (hue={hue_deg} satMin={sat_min} valMul={val_mul})")

if __name__ == "__main__":
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    o = {}
    for i, a in enumerate(sys.argv):
        if a == "--hue": o["hue"] = float(sys.argv[i+1])
        if a == "--sat": o["sat"] = float(sys.argv[i+1])
        if a == "--val": o["val"] = float(sys.argv[i+1])
    if len(args) < 2: raise SystemExit(__doc__)
    recolor(args[0], args[1], o.get("hue", 97.6), o.get("sat", 0.55), o.get("val", 1.4))
