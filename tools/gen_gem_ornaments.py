"""Dragon Tide（DT-609）: 2回目の進化の飾りを、全身カットの宝石の絵（*_sparkle）に描き足して *_jewel を作る。

  python3 tools/gen_gem_ornaments.py            # 火竜・氷竜の *_jewel_body.png / *_jewel_wing.png を書き出し、DRAGON_PART_SPRITES に貼る値を出す

前の版（v3.191.0）は画像生成で「全身の金の縁取り＋細かい飾り」を描いたので、全体を縁取っただけに見えた。
こちらは手で形を決めて飾る部位だけを太く描き、**元の輪郭からはみ出させる**（画像の余白を足して広げる）。
  火竜（ルビー）… 金の炎の冠（頭）と金の尾の刃。翼・胴・足は飾らない
  氷竜（アクアマリン）… 白金（プラチナ）の氷柱のティアラ（頭）と、翼の縁の霜の飾り。尾・胴・足は飾らない
乱数は使わない（毎回同じ絵になる）。絵の作り置き（向き×羽ばたき）は今までどおりゲーム側で1回だけ。
"""
import math
import os
import sys

import numpy as np
from PIL import Image, ImageChops, ImageDraw, ImageFilter

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "prototypes", "dragon-tide", "assets"))
SS = 4                      # 描くときの拡大（縮めてなめらかにする）
THRESH = 90                 # sprite_meta.py と同じ（アルファがこれ以上を「ある」とみなす）

GOLD = dict(light=(255, 238, 140), base=(247, 188, 28), dark=(176, 98, 8), line=(70, 30, 4))
PLATINUM = dict(light=(255, 255, 255), base=(226, 236, 248), dark=(120, 140, 176), line=(22, 40, 74))
GEM_BLUE = dict(light=(220, 250, 255), base=(120, 214, 246), dark=(40, 120, 190), line=(22, 40, 74))
OUTLINE_PX = 5.0            # 飾りの縁の太さ（元の絵の画素。小さく表示しても縁が残る太さ）


class Canvas:
    """拡大して描き、最後に縮めて元の絵の上に重ねる"""

    def __init__(self, width, height):
        self.w, self.h = width, height
        self.layer = Image.new("RGBA", (width * SS, height * SS), (0, 0, 0, 0))

    def _mask(self, polygons):
        m = Image.new("L", self.layer.size, 0)
        d = ImageDraw.Draw(m)
        for poly in polygons:
            d.polygon([(x * SS, y * SS) for x, y in poly], fill=255)
        return m

    def shape(self, polygons, pal, axis=(0.0, 1.0), outline=OUTLINE_PX, ridge=None, facet=None):
        """多角形（複数可）を、縁取り＋明→暗の傾きで塗る。axis は明るい側から暗い側への向き。
        ridge: [(x0,y0),(x1,y1),...] の折れ線。明るい筋を引く（刃や氷柱の芯）"""
        fill = self._mask(polygons)
        grow = max(1, int(round(outline * SS)) | 1)
        edge = fill.filter(ImageFilter.MaxFilter(grow))
        # 縁
        solid = Image.new("RGBA", self.layer.size, pal["line"] + (255,))
        self.layer.paste(solid, (0, 0), edge)
        # 塗り（傾き）
        bbox = fill.getbbox()
        if bbox is None:
            return
        x0, y0, x1, y1 = bbox
        ys, xs = np.mgrid[y0:y1, x0:x1].astype(np.float32)
        ax, ay = axis
        proj = xs * ax + ys * ay
        t = (proj - proj.min()) / max(1e-6, proj.max() - proj.min())
        t = t[..., None]
        light = np.array(pal["light"], np.float32)
        base = np.array(pal["base"], np.float32)
        dark = np.array(pal["dark"], np.float32)
        col = np.where(t < 0.45, light + (base - light) * (t / 0.45), base + (dark - base) * ((t - 0.45) / 0.55))
        patch = np.dstack([col, np.full(t.shape, 255, np.float32)]).astype(np.uint8)
        patch_img = Image.fromarray(patch, "RGBA")
        self.layer.paste(patch_img, (x0, y0), fill.crop(bbox))
        if facet:   # 片側の面を暗くして、結晶・刃の立体感を出す
            fm = ImageChops.multiply(self._mask([facet]), fill)
            sh = Image.new("RGBA", self.layer.size, pal["dark"] + (255,))
            self.layer.paste(sh, (0, 0), fm.point(lambda v: int(v * 0.55)))
        if ridge:
            rm = Image.new("L", self.layer.size, 0)
            ImageDraw.Draw(rm).line([(x * SS, y * SS) for x, y in ridge], fill=255, width=int(2.2 * SS), joint="curve")
            rm = ImageChops.multiply(rm, fill)
            hi = Image.new("RGBA", self.layer.size, pal["light"] + (255,))
            self.layer.paste(hi, (0, 0), rm)

    def finish(self):
        return self.layer.resize((self.w, self.h), Image.LANCZOS)


def flame(cx, cy, length, width, angle, lean=0.35):
    """炎の舌。根元 (cx,cy) から angle（0=真上、+は右へ）の向きへ length のび、先がS字に曲がる"""
    pts_l, pts_r = [], []
    steps = 14
    for i in range(steps + 1):
        t = i / steps
        # 中心線：先へ行くほど lean ぶん横へ曲がる
        along = length * t
        side = lean * length * (t ** 2) * 0.6 * math.sin(t * math.pi * 0.9 + 0.3)
        half = width * 0.5 * (1 - t) ** 0.8 * (1 + 0.35 * math.sin(t * math.pi))
        dx, dy = math.sin(angle), -math.cos(angle)
        nx, ny = -dy, dx
        px, py = cx + dx * along + nx * side, cy + dy * along + ny * side
        pts_l.append((px + nx * half, py + ny * half))
        pts_r.append((px - nx * half, py - ny * half))
    return pts_l + pts_r[::-1]


def spike(cx, cy, length, width, angle, base_w=None):
    """まっすぐな棘（氷柱・刃の先）。根元 (cx,cy) から angle の向きへ"""
    dx, dy = math.sin(angle), -math.cos(angle)
    nx, ny = -dy, dx
    bw = (base_w if base_w is not None else width) * 0.5
    tip = (cx + dx * length, cy + dy * length)
    return [(cx + nx * bw, cy + ny * bw), (cx + nx * width * 0.5 + dx * length * 0.12, cy + ny * width * 0.5 + dy * length * 0.12),
            tip,
            (cx - nx * width * 0.5 + dx * length * 0.12, cy - ny * width * 0.5 + dy * length * 0.12), (cx - nx * bw, cy - ny * bw)]


def band(cx, y, half_w, thick, curve=10):
    """頭にかかる帯（上へ反った弓なり）"""
    top, bot = [], []
    for i in range(21):
        u = i / 20 * 2 - 1
        x = cx + u * half_w
        yy = y - curve * (1 - u * u) * -1  # 中央が下へ垂れる弓
        top.append((x, yy - thick / 2))
        bot.append((x, yy + thick / 2))
    return top + bot[::-1]


def body_alpha(img):
    return np.array(img)[:, :, 3] > THRESH


def mass_center(img):
    ys, xs = np.nonzero(body_alpha(img))
    return float(xs.mean()), float(ys.mean())


def wing_inner_edge(img):
    a = body_alpha(img)
    ys, xs = np.nonzero(a)
    xmax = xs.max()
    band_ = xs >= xmax - max(4, int(a.shape[1] * 0.03))
    return int(xmax), float(ys[band_].mean())


def padded(img, left, top, right, bottom):
    out = Image.new("RGBA", (img.width + left + right, img.height + top + bottom), (0, 0, 0, 0))
    out.alpha_composite(img, (left, top))
    return out


# ---------------------------------------------------------------- 火竜（ルビー・金）
FIRE_PAD = dict(left=34, top=62, right=34, bottom=70)


def stack(back, sprite, front):
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.alpha_composite(back.finish())
    out.alpha_composite(sprite)
    out.alpha_composite(front.finish())
    return out


def fire_body(src):
    p = FIRE_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back, front = Canvas(*sprite.size), Canvas(*sprite.size)
    ox, oy = p["left"], p["top"]
    cx = ox + 63.0
    # 尾の刃（先は元の尾の先 y≈318 の外へ）。胴の下に敷いて、はみ出た所だけが見える。根元に金の輪
    ty = oy + 290
    blade = [(cx, ty + 100), (cx + 12, ty + 76), (cx + 22, ty + 44), (cx + 18, ty + 18), (cx + 8, ty + 8),
             (cx - 8, ty + 8), (cx - 18, ty + 18), (cx - 22, ty + 44), (cx - 12, ty + 76)]
    back.shape([blade], GOLD, axis=(1.0, 0.25), ridge=[(cx, ty + 12), (cx, ty + 88)],
               facet=[(cx, ty + 8), (cx + 22, ty + 44), (cx + 12, ty + 76), (cx, ty + 100)])
    # 刃の両わきの返し（尾の左右へ大きくはみ出す）
    for s in (-1, 1):
        barb = [(cx + s * 6, ty + 28), (cx + s * 26, ty + 14), (cx + s * 44, ty + 40), (cx + s * 20, ty + 64)]
        back.shape([barb], GOLD, axis=(0.3, 1.0))
    front.shape([band(cx, ty + 10, 14, 13, curve=0)], GOLD, axis=(0.0, 1.0))
    # 炎の冠：頭の後ろの炎の舌を前と横へ広げる（頭の幅 ±22 を大きくはみ出す）。炎は胴の下、帯と石は上
    hy = oy + 44
    spikes = [(-80, 64, 24), (-54, 82, 28), (-26, 98, 30), (0, 112, 32), (26, 98, 30), (54, 82, 28), (80, 64, 24)]
    for ang, length, width in spikes:
        lean = 0.5 * (1 if ang >= 0 else -1) if ang else 0.0
        back.shape([flame(cx, hy, length, width, math.radians(ang), lean=lean)], GOLD, axis=(0.0, -1.0))
    front.shape([band(cx, hy + 10, 27, 11, curve=7)], GOLD, axis=(0.0, 1.0))
    gem = [(cx, hy + 1), (cx + 8, hy + 10), (cx, hy + 19), (cx - 8, hy + 10)]
    front.shape([gem], dict(light=(255, 190, 190), base=(214, 22, 44), dark=(110, 4, 20), line=GOLD["line"]), outline=3.0)
    return stack(back, sprite, front)


def fire_wing(src):
    # 翼は飾らない。胴と同じ寸法の規則（余白）だけそろえる必要はなく、元の絵のまま
    return src.copy()


# ---------------------------------------------------------------- 氷竜（アクアマリン・白金）
ICE_PAD = dict(left=34, top=70, right=34, bottom=22)
ICE_WING_PAD = dict(left=48, top=46, right=0, bottom=50)


def ice_body(src):
    p = ICE_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back, front = Canvas(*sprite.size), Canvas(*sprite.size)
    ox, oy = p["left"], p["top"]
    cx = ox + 82.0
    hy = oy + 48
    # 氷柱のティアラ：頭の後ろから氷柱を扇状に（まっすぐ・鋭い。火竜の炎の冠とは線の質が違う）。胴の下に敷く
    shards = [(-68, 52, 17), (-46, 76, 19), (-23, 98, 20), (0, 118, 22), (23, 98, 20), (46, 76, 19), (68, 52, 17)]
    for ang, length, width in shards:
        a = math.radians(ang)
        poly = spike(cx, hy, length, width, a, base_w=width)
        dx, dy = math.sin(a), -math.cos(a)
        nx, ny = -dy, dx
        half = [(cx, hy), (cx + dx * length, cy_ := hy + dy * length), (cx + nx * width * 0.5 + dx * length * 0.12, hy + ny * width * 0.5 + dy * length * 0.12)]
        back.shape([poly], PLATINUM, axis=(0.6, 1.0), facet=half)
    front.shape([band(cx, hy + 12, 30, 11, curve=7)], PLATINUM, axis=(0.0, 1.0))
    gem = [(cx, hy + 3), (cx + 9, hy + 12), (cx, hy + 23), (cx - 9, hy + 12)]
    front.shape([gem], GEM_BLUE, outline=3.0)
    return stack(back, sprite, front)


def ice_wing(src):
    p = ICE_WING_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    a = body_alpha(sprite)
    back = Canvas(*sprite.size)
    w, h = sprite.size

    def crystal(x, y, length, width, ang):
        poly = spike(x, y, length, width, ang, base_w=width)
        dx, dy = math.sin(ang), -math.cos(ang)
        nx, ny = -dy, dx
        half = [(x, y), (x + dx * length, y + dy * length), (x + nx * width * 0.5 + dx * length * 0.12, y + ny * width * 0.5 + dy * length * 0.12)]
        back.shape([poly], PLATINUM, axis=(0.6, 1.0), facet=half)

    lower = np.array([np.nonzero(a[:, x])[0].max() if a[:, x].any() else -1 for x in range(w)], np.float32)
    upper = np.array([np.nonzero(a[:, x])[0].min() if a[:, x].any() else -1 for x in range(w)], np.float32)
    # 下の縁（羽根の先）の山を拾って、そこから氷柱を下へ・外へのばす
    peaks = []
    med = np.median(lower[lower >= 0])
    for x in range(14, w - 40):
        win = lower[x - 14:x + 15]
        if lower[x] >= 0 and lower[x] == win.max() and (not peaks or x - peaks[-1] > 26) and lower[x] > med + 4:
            peaks.append(x)
    for x in peaks:
        crystal(x, lower[x] - 6, 52 + 10 * (1 - x / w), 22, math.radians(160 + (x / w) * 16))
    # 前の縁（上）に、前へ向く氷の結晶を3本（翼の骨に沿って並べる）
    for f, length in ((0.34, 58), (0.52, 66), (0.70, 54)):
        x = int(w * f)
        crystal(x, upper[x] + 8, length, 22, math.radians(-8 + 30 * f))
    # 翼の先（左端）に長い氷の槍を外へ
    left_x = int(np.nonzero(a.any(axis=0))[0].min())
    ty = float(np.nonzero(a[:, left_x + 2])[0].mean())
    crystal(left_x + 14, ty, 70, 26, math.radians(-98))
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.alpha_composite(back.finish())
    out.alpha_composite(sprite)
    return out


def report(name, body, wing, src_body, src_wing, pad_body, pad_wing):
    """DRAGON_PART_SPRITES に貼る値。元の胴の重心・肩・翼の付け根を、余白ぶんずらして写す"""
    return None


def main():
    out = {}
    for element, body_fn, wing_fn, pad_b, pad_w in (
        ("fire", fire_body, fire_wing, FIRE_PAD, dict(left=0, top=0, right=0, bottom=0)),
        ("ice", ice_body, ice_wing, ICE_PAD, ICE_WING_PAD),
    ):
        sb = Image.open(os.path.join(ASSETS, f"dragon_{element}_sparkle_body.png")).convert("RGBA")
        sw = Image.open(os.path.join(ASSETS, f"dragon_{element}_sparkle_wing.png")).convert("RGBA")
        jb, jw = body_fn(sb), wing_fn(sw)
        jb.save(os.path.join(ASSETS, f"dragon_{element}_jewel_body.png"), optimize=True)
        jw.save(os.path.join(ASSETS, f"dragon_{element}_jewel_wing.png"), optimize=True)
        out[element] = dict(body=jb.size, wing=jw.size, pad_b=pad_b, pad_w=pad_w, sb=sb.size, sw=sw.size)
        print(element, "body", sb.size, "->", jb.size, "wing", sw.size, "->", jw.size)


if __name__ == "__main__":
    main()
