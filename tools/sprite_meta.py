"""Dragon Tide: 竜パーツの DRAGON_PART_SPRITES メタデータを実測する。

  python tools/sprite_meta.py <species> <body.png> <wing.png>

出す値（docs/tdd/dragon-tide-sprites.md §2-2 の定義）:
  bodyPivot  … 胴体のアルファ質量重心（画像中心ではない。中心にすると回転で脚が前に来る）
  shoulder   … 翼の付け根。胴体シルエットが**上半分で最も横に張り出す行**を採り、
               そこから内側へ寄せる。寄せ幅と行のオフセットは、手で詰めた火竜の値
               （±125 / y=425）に合わせて校正した（実測の縁は ±149 / y=415 だった）。
               最後はプレビューで微調整する前提の自動推定。
  wingAnchor … 翼画像の**内側端**（＝肩に付く側）。構図上いちばん右にある内容の位置。
               手首ではない（§2-0。手首にすると翼が胴から離れて浮く）
"""
import sys
from PIL import Image
import numpy as np

THRESH = 90

def load_alpha(path):
    a = np.array(Image.open(path).convert("RGBA"))[:, :, 3]
    return a

def body_meta(path):
    a = load_alpha(path)
    h, w = a.shape
    ys, xs = np.nonzero(a > THRESH)
    cx, cy = xs.mean(), ys.mean()
    # 肩: 内容の上55%の範囲で最も横幅の広い行
    y0, y1 = ys.min(), ys.max()
    upper_end = int(y0 + (y1 - y0) * 0.55)
    best_row, best_span, best_lr = None, -1, None
    for y in range(int(y0), upper_end + 1):
        row = np.nonzero(a[y] > THRESH)[0]
        if len(row) == 0:
            continue
        span = row.max() - row.min()
        if span > best_span:
            best_span, best_row, best_lr = span, y, (int(row.min()), int(row.max()))
    # 校正: 縁そのままだと翼が外へ付きすぎる。火竜の手詰め値に合わせて 0.84 倍・10px 下へ。
    SHOULDER_INSET, SHOULDER_DROP = 0.84, 10
    mid = (best_lr[0] + best_lr[1]) / 2
    half = (best_lr[1] - best_lr[0]) / 2 * SHOULDER_INSET
    return dict(w=w, h=h, cx=round(float(cx), 1), cy=round(float(cy), 1),
                shoulder_y=best_row + SHOULDER_DROP,
                shoulder_l=round(mid - half, 1), shoulder_r=round(mid + half, 1),
                half=round(half, 1))

def wing_meta(path):
    a = load_alpha(path)
    h, w = a.shape
    ys, xs = np.nonzero(a > THRESH)
    xmax = xs.max()
    # 右端から3%の帯にある内容の縦方向重心＝内側端（肩に付く位置）
    band = xs >= xmax - max(4, int(w * 0.03))
    ay = ys[band].mean()
    return dict(w=w, h=h, anchor_x=int(xmax), anchor_y=round(float(ay), 1))

if __name__ == "__main__":
    if len(sys.argv) < 4:
        raise SystemExit(__doc__)
    species, bpath, wpath = sys.argv[1], sys.argv[2], sys.argv[3]
    b, wg = body_meta(bpath), wing_meta(wpath)
    print(f"  {species}: {{")
    print(f'    body: "assets/dragon_{species}_body.png",')
    print(f'    wing: "assets/dragon_{species}_wing.png",')
    print(f"    bodyPivot:  {{ cx: {b['cx']}, cy: {b['cy']}, w: {b['w']}, h: {b['h']} }},")
    print(f"    shoulder:   {{ left: {{ x: {b['shoulder_l']}, y: {b['shoulder_y']} }}, "
          f"right: {{ x: {b['shoulder_r']}, y: {b['shoulder_y']} }} }},   // 幅最大の行で実測")
    print(f"    wingAnchor: {{ x: {wg['anchor_x']}, y: {wg['anchor_y']} }},")
    print(f"    bodyDrawH: 27,")
    print(f"    wingDrawW: 30,")
    print(f"  }},")
