"""Dragon Tide（DT-656〜664 11/28）: 竜の新デザインの見本の絵（design-preview.html）を作る。

  python3 tools/compose_design_preview.py ball mole ...
  → prototypes/dragon-tide/assets/design_candidates/preview_<竜種>_{now,new}.png

ゲームの drawPartSeparatedDragon・codexDragonCanvas と同じ組み方（胴の高さ bodyDrawH・翼の幅 wingDrawW・肩に翼の付け根・
翼を胴の上に重ねて付け根をぼかす・尻尾は胴の後ろから5節）で、
  now … いまの姿（DRAGON_PARTS_ALIAS で借りている絵＋spriteTint を 0.42 で重ねる。index.html の値を読む）
  new … 新しいデザイン（assets/design_candidates/dragon_<竜種>_{body,wing}.png。寸法は tools/sprite_meta.py で測る）
を描く。羽ばたきは開ききった形（flapFactor 1）。
"""
import math
import os
import re
import sys

import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from sprite_meta import body_meta, wing_meta  # noqa: E402

ROOT = os.path.normpath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
GAME = os.path.join(ROOT, "prototypes", "dragon-tide")
CAND = os.path.join(GAME, "assets", "design_candidates")
SRC = open(os.path.join(GAME, "index.html"), encoding="utf-8").read()

# index.html の定数（描き方を合わせるため。変わったら読み直す）
BODY_DRAW_H, WING_DRAW_W = 27, 25
TAIL_SEGS, TAIL_SEG_LEN, TAIL_WIDTH0, TAIL_START, TAIL_CURL = 5, 4.5, 2.2, 10, 0.14
EVO_TINT_ALPHA = 0.42
WING_ROOT_FADE = 0.03
SCALE = 320 / BODY_DRAW_H   # 胴の高さが 320px になる倍率（ほかの見本の絵と揃える）
SS = 2                      # 尻尾の線を滑らかにする描き込みの倍率


def species_def(species):
    m = re.search(r"\n  " + species + r": \{(.*?)\n  \},", SRC[SRC.index("const SPECIES_DEFS"):], re.S)
    block = m.group(1)
    tint = re.search(r'spriteTint: "(#[0-9a-f]{6})"', block)
    return {"tint": tint.group(1) if tint else None, "noTail": "noTail: true" in block}


def alias_parts(species):
    key = re.search(r"\b" + species + r': "([a-z_]+)"', SRC[SRC.index("const DRAGON_PARTS_ALIAS"):]).group(1)
    blk = SRC[SRC.index("const DRAGON_PART_SPRITES"):]
    m = re.search(r"\n  " + key + r": \{(.*?)\n  \},", blk, re.S).group(1)
    num = lambda pat: [float(v) for v in re.search(pat, m).groups()]
    cx, cy, w, h = num(r"bodyPivot:\s*\{ cx: ([\d.]+), cy: ([\d.]+), w: (\d+), h: (\d+)")
    lx, ly, rx, ry = num(r"left: \{ x: ([\d.]+), y: ([\d.]+) \}, right: \{ x: ([\d.]+), y: ([\d.]+) \}")
    ax, ay = num(r"wingAnchor: \{ x: ([\d.]+), y: ([\d.]+) \}")
    body = re.search(r'body: "assets/([^"]+)"', m).group(1)
    wing = re.search(r'wing: "assets/([^"]+)"', m).group(1)
    ww = float(re.search(r"wingDrawW: ([\d.]+)", m).group(1))
    bh = float(re.search(r"bodyDrawH: ([\d.]+)", m).group(1))
    return dict(body=os.path.join(GAME, "assets", body), wing=os.path.join(GAME, "assets", wing),
                cx=cx, cy=cy, sl=(lx, ly), sr=(rx, ry), ax=ax, ay=ay, wingDrawW=ww, bodyDrawH=bh, key=key)


# sprite_meta.py の肩は「上55%でいちばん幅の広い行」なので、前脚が胴より大きく張り出す竜種は前脚の所に付いてしまう。
# 手で測った肩（胴の絵の px。x は左右、y は共通）で置き換える（ゲームに入れるときも DRAGON_PART_SPRITES にこの値を書く）
SHOULDER_FIX = {
    "mole": (45, 157, 140),    # 掘る前足（y 70〜115 で幅 190）の後ろ、胴の横
    "whale": (40, 172, 125),   # 前脚の鰭（y 145〜200 で幅 210）の前、胴の横
}


def new_parts(species):
    bp, wp = (os.path.join(CAND, f"dragon_{species}_{p}.png") for p in ("body", "wing"))
    b, wg = body_meta(bp), wing_meta(wp)
    if species in SHOULDER_FIX:
        b["shoulder_l"], b["shoulder_r"], b["shoulder_y"] = SHOULDER_FIX[species]
    return dict(body=bp, wing=wp, cx=b["cx"], cy=b["cy"], sl=(b["shoulder_l"], b["shoulder_y"]),
                sr=(b["shoulder_r"], b["shoulder_y"]), ax=wg["anchor_x"], ay=wg["anchor_y"],
                wingDrawW=WING_DRAW_W, bodyDrawH=BODY_DRAW_H, meta=(b, wg))


def tail_color(species):
    blk = SRC[SRC.index("const DRAGON_ELEMENT_COLORS"):]
    r, g, b = re.search(r"\n  " + species + r':\s*\{ body: "rgba\((\d+), (\d+), (\d+)', blk).groups()
    return (int(r), int(g), int(b), 255)


def faded_wing(img, anchor_x):
    a = np.array(img).astype(np.float32)
    fade = img.width * WING_ROOT_FADE
    xs = np.arange(img.width)
    k = np.clip((anchor_x - xs) / fade, 0, 1)
    a[..., 3] *= k[None, :]
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def compose(parts, species, tint, no_tail):
    body = Image.open(parts["body"]).convert("RGBA")
    wing = Image.open(parts["wing"]).convert("RGBA")
    s = SCALE * SS
    bh = parts["bodyDrawH"] * s
    kb = bh / body.height
    bw = body.width * kb
    ww = parts["wingDrawW"] * s
    kw = ww / wing.width
    wh = wing.height * kw
    # 原点＝胴のピボット。大きめの画布に描いてから余白を詰める
    size = int(160 * s)
    o = size // 2
    tail = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    canvas = Image.new("RGBA", (size, size), (0, 0, 0, 0))
    if not no_tail:   # 尻尾（codexDragonCanvas と同じ：胴の後ろ10から5節・少ししならせる・根元2.2で先へ細く）
        d = ImageDraw.Draw(tail)
        x, y, a = 0.0, TAIL_START, math.pi / 2
        col = tail_color(species)
        for i in range(TAIL_SEGS):
            a += TAIL_CURL
            nx, ny = x + math.cos(a) * TAIL_SEG_LEN, y + math.sin(a) * TAIL_SEG_LEN
            width = max(0.4, TAIL_WIDTH0 * (1 - (i + 1) / (TAIL_SEGS + 1))) * s
            p0, p1 = (o + x * s, o + y * s), (o + nx * s, o + ny * s)
            d.line([p0, p1], fill=col, width=round(width))
            for px, py in (p0, p1):
                d.ellipse([px - width / 2, py - width / 2, px + width / 2, py + width / 2], fill=col)
            x, y = nx, ny
    bimg = body.resize((round(bw), round(bh)), Image.LANCZOS)
    canvas.alpha_composite(bimg, (round(o - parts["cx"] * kb), round(o - parts["cy"] * kb)))
    fw = faded_wing(wing, parts["ax"]).resize((round(ww), round(wh)), Image.LANCZOS)
    for (sx, sy), mirror in ((parts["sl"], False), (parts["sr"], True)):
        px, py = o + (sx - parts["cx"]) * kb, o + (sy - parts["cy"]) * kb
        rx, ry = parts["ax"] * kw, parts["ay"] * kw
        img = fw
        if mirror:
            img = fw.transpose(Image.FLIP_LEFT_RIGHT)
            canvas.alpha_composite(img, (round(px - (ww - rx)), round(py - ry)))
        else:
            canvas.alpha_composite(img, (round(px - rx), round(py - ry)))
    if tint:   # 仮の絵の色寄せ（tintedSprites：source-atop で EVO_TINT_ALPHA）。尻尾には重ねない（ゲームも胴・翼の絵とは別に描く）
        rgb = tuple(int(tint[i:i + 2], 16) for i in (1, 3, 5))
        a = np.array(canvas).astype(np.float32)
        a[..., :3] = a[..., :3] * (1 - EVO_TINT_ALPHA) + np.array(rgb) * EVO_TINT_ALPHA
        canvas = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    tail.alpha_composite(canvas)   # 尻尾は胴の下（codexDragonCanvas も尻尾を先に描く）
    canvas = tail
    canvas = canvas.crop(canvas.getbbox())
    return canvas.resize((round(canvas.width / SS), round(canvas.height / SS)), Image.LANCZOS)


def main():
    for species in sys.argv[1:]:
        d = species_def(species)
        now = alias_parts(species)
        compose(now, species, d["tint"], d["noTail"]).save(os.path.join(CAND, f"preview_{species}_now.png"), optimize=True)
        new = new_parts(species)
        compose(new, species, None, d["noTail"]).save(os.path.join(CAND, f"preview_{species}_new.png"), optimize=True)
        b, wg = new["meta"]
        print(f"{species}: borrowed={now['key']} tint={d['tint']} noTail={d['noTail']} | "
              f"bodyPivot cx {b['cx']} cy {b['cy']} w {b['w']} h {b['h']} / shoulder L {b['shoulder_l']} R {b['shoulder_r']} y {b['shoulder_y']} "
              f"/ wingAnchor {wg['anchor_x']},{wg['anchor_y']} (wing {wg['w']}x{wg['h']})")


if __name__ == "__main__":
    main()
