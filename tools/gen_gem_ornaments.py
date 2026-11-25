"""Dragon Tide（DT-609）: 2回目の進化の飾りを、全身カットの宝石の絵（*_sparkle）に描き足して *_jewel を作る。

  python3 tools/gen_gem_ornaments.py            # 火竜・氷竜の *_jewel_body.png / *_jewel_wing.png を書き出し、DRAGON_PART_SPRITES に貼る値を出す

前の版（v3.191.0）は画像生成で「全身の金の縁取り＋細かい飾り」を描いたので、全体を縁取っただけに見えた。
こちらは手で形を決めて飾る部位だけを太く描き、**元の輪郭からはみ出させる**（画像の余白を足して広げる）。
  火竜（ルビー）… 金の額飾り（頭。顔の前へは出さない）・翼の前の縁の外側半分の金の縁取りと先の爪の覆い・金の尾の刃。胴・足・翼の後ろの縁は飾らない
  氷竜（アクアマリン）… 白金（プラチナ）の首輪とアクアマリンの雫・翼の後ろの縁の外側だけ白金の縁取りと垂れる氷柱・先の氷の槍。頭・胴・足・尾は飾らない
  （v3.196.0 の炎の冠・氷柱のティアラは顔の前へ突き出て異様に見えたのでやめた。DT-609 11/25 Shooter）
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
        self.paint(self._mask(polygons), pal, axis, outline, ridge, facet)

    def stroke(self, points, width, pal, axis=(0.0, 1.0), outline=OUTLINE_PX, ridge=True):
        """折れ線に沿った帯（縁の飾り）。points は元の絵の画素。帯の芯に明るい筋を通して金属の照りを出す"""
        m = Image.new("L", self.layer.size, 0)
        pts = [(x * SS, y * SS) for x, y in points]
        d = ImageDraw.Draw(m)
        d.line(pts, fill=255, width=int(width * SS), joint="curve")
        r = width * SS / 2
        for x, y in (pts[0], pts[-1]):     # 端を丸める
            d.ellipse((x - r, y - r, x + r, y + r), fill=255)
        self.paint(m, pal, axis, outline, points if ridge else None, None, ridge_w=max(1.4, width * 0.22))

    def paint(self, fill, pal, axis=(0.0, 1.0), outline=OUTLINE_PX, ridge=None, facet=None, ridge_w=2.2):
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
            ImageDraw.Draw(rm).line([(x * SS, y * SS) for x, y in ridge], fill=255, width=int(ridge_w * SS), joint="curve")
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


def edge_line(a, x0, x1, side, offset, step=3, smooth=2):
    """翼の縁（side="upper"＝前の縁・"lower"＝後ろの縁）を x0→x1 でなぞる折れ線。offset だけ外へずらす（飾りが輪郭をはみ出す）"""
    pts = []
    for x in range(int(x0), int(x1) + 1, step):
        lo, hi = max(0, x - smooth), min(a.shape[1], x + smooth + 1)
        cols = [np.nonzero(a[:, c])[0] for c in range(lo, hi)]
        cols = [c for c in cols if len(c)]
        if not cols:
            continue
        y = (min(c.min() for c in cols) - offset) if side == "upper" else (max(c.max() for c in cols) + offset)
        pts.append((float(x), float(y)))
    return pts


def studs(canvas, points, pal, every, size):
    """縁の飾りの上に、菱形の鋲を間をあけて打つ"""
    for i in range(every // 2, len(points), every):
        x, y = points[i]
        canvas.shape([[(x, y - size), (x + size * 0.8, y), (x, y + size), (x - size * 0.8, y)]], pal, axis=(0.5, 1.0), outline=2.5)


# ---------------------------------------------------------------- 火竜（ルビー・金）
# v3.198.0（DT-609 手直し・Shooter「顔の前に出るトゲトゲは変。火竜も氷竜も」「縁の飾りも、全部を覆わず一部の部位に」）:
# 炎の冠をやめ、頭は顔の前へ出ない細い金の額飾り（ルビー付き）だけ。縁の飾りは翼の前の縁の外側半分（手首→翼の先）だけ。尾の刃はそのまま。
FIRE_PAD = dict(left=0, top=0, right=0, bottom=70)
FIRE_WING_PAD = dict(left=10, top=10, right=0, bottom=0)


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
    # 刃の両わきの返し（尾の左右へはみ出す。後ろ向きなので顔の前には出ない）
    for s in (-1, 1):
        barb = [(cx + s * 6, ty + 28), (cx + s * 26, ty + 14), (cx + s * 44, ty + 40), (cx + s * 20, ty + 64)]
        back.shape([barb], GOLD, axis=(0.3, 1.0))
    front.shape([band(cx, ty + 10, 14, 13, curve=0)], GOLD, axis=(0.0, 1.0))
    # 額飾り：目の後ろに金の細い帯とルビー。頭の輪郭から左右へ少しだけはみ出し、前（顔の先）へは何も出さない
    hy = oy + 44
    front.shape([band(cx, hy + 10, 31, 10, curve=6)], GOLD, axis=(0.0, 1.0))
    gem = [(cx, hy + 1), (cx + 8, hy + 10), (cx, hy + 19), (cx - 8, hy + 10)]
    front.shape([gem], dict(light=(255, 190, 190), base=(214, 22, 44), dark=(110, 4, 20), line=GOLD["line"]), outline=3.0)
    return stack(back, sprite, front)


def fire_wing(src):
    p = FIRE_WING_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    a = body_alpha(sprite)
    front = Canvas(*sprite.size)
    left_x = int(np.nonzero(a.any(axis=0))[0].min())
    top_x = int(np.argmin([np.nonzero(a[:, x])[0].min() if a[:, x].any() else 1e9 for x in range(a.shape[1])]))
    # 前の縁のうち、翼の先から手首（いちばん上の爪の手前）までだけを金で縁取る。根元側・後ろの縁は飾らない
    line = edge_line(a, left_x + 3, top_x - 14, "upper", offset=-1.5)
    front.stroke(line, 13, GOLD, axis=(0.0, 1.0), outline=4.0)
    studs(front, line, GOLD, every=16, size=7)
    # 翼の先に金の爪の覆い（先の向きのまま少し伸ばす）
    ty = float(np.nonzero(a[:, left_x + 1])[0].mean())
    front.shape([[(left_x + 22, ty - 12), (left_x - 10, ty + 2), (left_x + 20, ty + 10)]], GOLD, axis=(0.0, 1.0), outline=4.0)
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.alpha_composite(sprite)
    out.alpha_composite(front.finish())
    return out


# ---------------------------------------------------------------- 氷竜（アクアマリン・白金）
# v3.198.0（DT-609 手直し）: 氷柱のティアラ・翼の前の縁の結晶（どちらも前へ突き出る）をやめた。
# 頭は飾らず、首の付け根に白金の首輪（アクアマリンの雫）。翼は後ろの縁のうち先から2本目の指までの膜だけ白金で縁取り、指の先から短い氷柱を後ろへ垂らす。先の氷の槍は外向きなので残す。
ICE_PAD = dict(left=0, top=0, right=0, bottom=0)
ICE_WING_PAD = dict(left=48, top=0, right=0, bottom=40)


def ice_body(src):
    p = ICE_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    front = Canvas(*sprite.size)
    ox, oy = p["left"], p["top"]
    cx = ox + 82.0
    ny = oy + 124
    # 首輪：いちばん細い首（幅 ±34）より少し広い帯。胴の上に重ねる
    front.shape([band(cx, ny, 40, 13, curve=10)], PLATINUM, axis=(0.0, 1.0))
    # 前の雫（首輪から胸へ垂れる。後ろ向き）
    drop = [(cx, ny + 6), (cx + 10, ny + 18), (cx, ny + 36), (cx - 10, ny + 18)]
    front.shape([drop], GEM_BLUE, outline=3.0)
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.alpha_composite(sprite)
    out.alpha_composite(front.finish())
    return out


def ice_wing(src):
    p = ICE_WING_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    a = body_alpha(sprite)
    back, front = Canvas(*sprite.size), Canvas(*sprite.size)
    w, h = sprite.size

    def crystal(canvas, x, y, length, width, ang):
        poly = spike(x, y, length, width, ang, base_w=width)
        dx, dy = math.sin(ang), -math.cos(ang)
        nx, ny = -dy, dx
        half = [(x, y), (x + dx * length, y + dy * length), (x + nx * width * 0.5 + dx * length * 0.12, y + ny * width * 0.5 + dy * length * 0.12)]
        canvas.shape([poly], PLATINUM, axis=(0.6, 1.0), facet=half)

    left_x = int(np.nonzero(a.any(axis=0))[0].min())
    lower = np.array([np.nonzero(a[:, x])[0].max() if a[:, x].any() else -1 for x in range(w)], np.float32)
    # 後ろの縁の山（指の先）を拾う。飾るのは翼の先から2本目の指の先までの膜だけ（根元側の膜は飾らない）
    peaks = []
    for x in range(left_x + 20, w - 40):
        win = lower[x - 10:x + 11]
        if lower[x] == win.max() and (not peaks or x - peaks[-1] > 30) and lower[x] > np.median(lower[lower >= 0]) + 8:
            peaks.append(x)
    peaks = peaks[:2]
    # 膜の弧ごとに白金の縁を付け、指の先の前後は切る（指の先からは氷柱を垂らす）
    # 2つ目の弧は指の先に近い急な所を外し、真ん中のゆるい所だけ（花綱のように見える）
    spans = [(left_x + 20, peaks[0] - 7)] + [(x0 + 18, x1 - 26) for x0, x1 in zip(peaks[:-1], peaks[1:])]
    for x0, x1 in spans:
        line = edge_line(a, x0, x1, "lower", offset=1.0, smooth=0)
        front.stroke(line, 11, PLATINUM, axis=(0.0, 1.0), outline=4.0)
    for i, x in enumerate(peaks):
        crystal(back, x, lower[x] - 6, 46 - i * 8, 16, math.radians(176 + i * 6))
    # 翼の先に長い氷の槍を外へ
    ty = float(np.nonzero(a[:, left_x + 2])[0].mean())
    crystal(back, left_x + 14, ty, 70, 26, math.radians(-98))
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.alpha_composite(back.finish())
    out.alpha_composite(sprite)
    out.alpha_composite(front.finish())
    return out


def report(name, body, wing, src_body, src_wing, pad_body, pad_wing):
    """DRAGON_PART_SPRITES に貼る値。元の胴の重心・肩・翼の付け根を、余白ぶんずらして写す"""
    return None


def main():
    out = {}
    for element, body_fn, wing_fn, pad_b, pad_w in (
        ("fire", fire_body, fire_wing, FIRE_PAD, FIRE_WING_PAD),
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
