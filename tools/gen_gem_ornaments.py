"""Dragon Tide（DT-609）: 2回目の進化の飾りを、全身カットの宝石の絵（*_sparkle）に描き足して *_jewel を作る。

  python3 tools/gen_gem_ornaments.py            # 火竜・氷竜の *_jewel_body.png / *_jewel_wing.png を書き出し、DRAGON_PART_SPRITES に貼る値を出す

前の版（v3.191.0）は画像生成で「全身の金の縁取り＋細かい飾り」を描いたので、全体を縁取っただけに見えた。
こちらは手で形を決めて飾る部位だけを太く描き、**元の輪郭からはみ出させる**（画像の余白を足して広げる）。
竜種ごとの突き出る飾り（v3.203.0・DT-609 11/25 Shooter「縁取りはイマイチなのでやめる」「首輪やハチマキのような飾りはペットみたいなのでやめる」
「顔の前の飾りは変だったが、後頭部に付いていればたぶん問題ない」）:
  火竜（ルビー）… 後頭部から後ろ・外へなびく金の炎のたてがみ・翼の先の後ろへ反る金の炎の刃3枚・金の尾の刃と返し
  氷竜（アクアマリン）… 後頭部から後ろ・外へ広がる白金の氷柱の冠・翼の白金の氷の結晶・氷柱・槍（v3.196.0 のまま）・尾の先の氷の結晶の房
  細い縁取り（rim）・額飾り・首輪と雫・尾の根元の輪は付けない（rim() は使わないが、縁取りの作り方の記録として残す）
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


def curved_blade(cx, cy, length, width, angle, bend):
    """曲がった刃（炎の舌を細く鋭くしたもの）。根元 (cx,cy) から angle の向きへ、先へ行くほど bend（ラジアン）だけ向きが回る。
    返り値は（刃の形, 芯の折れ線）"""
    pts_l, pts_r, spine = [], [], []
    x, y = cx, cy
    steps = 16
    for i in range(steps + 1):
        t = i / steps
        a = angle + bend * t * t
        dx, dy = math.sin(a), -math.cos(a)
        nx, ny = -dy, dx
        half = width * 0.5 * (1 - t) ** 1.15
        pts_l.append((x + nx * half, y + ny * half))
        pts_r.append((x - nx * half, y - ny * half))
        spine.append((x, y))
        x, y = x + dx * length / steps, y + dy * length / steps
    return pts_l + pts_r[::-1], spine[1:-3]


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


def rim(canvas, sprite_alpha, pal, keep, width=5.0, axis=(0.0, 1.0)):
    """輪郭の外側の細い縁取り（v3.191.0 の全身の金の縁取りを、keep で選んだ部位だけに戻す）。
    sprite_alpha: 絵の「ある」所（bool）。keep(xs, ys) -> bool の配列：縁取りを残す所（元の絵の画素の座標）。
    胴・翼の下（back）に敷くので、見えるのは輪郭の外へはみ出た分だけ"""
    h, w = sprite_alpha.shape
    m = Image.fromarray((sprite_alpha * 255).astype(np.uint8), "L").resize((w * SS, h * SS), Image.BILINEAR)
    m = m.point(lambda v: 255 if v >= 128 else 0)
    grown = m
    for _ in range(int(round(width * SS / 2))):     # 3×3 の膨らませを重ねて width 画素ぶん外へ
        grown = grown.filter(ImageFilter.MaxFilter(3))
    ys, xs = np.mgrid[0:h * SS, 0:w * SS].astype(np.float32) / SS
    sel = Image.fromarray((keep(xs, ys) * 255).astype(np.uint8), "L")
    canvas.paint(ImageChops.multiply(grown, sel), pal, axis, outline=2.0)


# ---------------------------------------------------------------- 火竜（ルビー・金）
# v3.199.0（DT-609 手直し・Shooter「地味になりすぎ」「突出した二つくらいのパーツに加えて、無くした縁取りを一部戻して」）:
#   突き出る飾り＝尾の金の刃（と返し）・翼の先の金の炎の刃（外へ）。頭は目の後ろの細い額飾り（顔の前へは出さない）。
#   縁取り（v3.191.0 の細い金の縁）を戻すのは、翼の外まわり（付け根を除く）と、腰から尾の先まで。頭・首・胴・足には付けない。
#   v3.198.0 の「翼の前の縁の外側半分の太い金の帯と鋲」は、細い縁取りに置き換えた。
RIM = 8                         # 上の余白（v3.199.0 の縁取りの名残。値を変えると胴の重心の値も変わるのでそのまま）
FIRE_PAD = dict(left=24, top=RIM, right=24, bottom=70)   # 左右は炎のたてがみがはみ出す分
FIRE_WING_PAD = dict(left=110, top=RIM, right=0, bottom=40)


def stack(back, sprite, front):
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.alpha_composite(back.finish())
    out.alpha_composite(sprite)
    out.alpha_composite(front.finish())
    return out


def fire_body(src):
    p = FIRE_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    ox, oy = p["left"], p["top"]
    cx = ox + 63.0
    # 尾の刃（先は元の尾の先 y≈318 の外へ）。胴の下に敷いて、はみ出た所だけが見える
    ty = oy + 290
    blade = [(cx, ty + 100), (cx + 12, ty + 76), (cx + 22, ty + 44), (cx + 18, ty + 18), (cx + 8, ty + 8),
             (cx - 8, ty + 8), (cx - 18, ty + 18), (cx - 22, ty + 44), (cx - 12, ty + 76)]
    back.shape([blade], GOLD, axis=(1.0, 0.25), ridge=[(cx, ty + 12), (cx, ty + 88)],
               facet=[(cx, ty + 8), (cx + 22, ty + 44), (cx + 12, ty + 76), (cx, ty + 100)])
    # 刃の両わきの返し（尾の左右へはみ出す。後ろ向きなので顔の前には出ない）
    for s in (-1, 1):
        barb = [(cx + s * 6, ty + 28), (cx + s * 26, ty + 14), (cx + s * 44, ty + 40), (cx + s * 20, ty + 64)]
        back.shape([barb], GOLD, axis=(0.3, 1.0))
    # 炎のたてがみ（v3.196.0 の炎の冠を後頭部へ移した）：頭のいちばん幅のある所（y≈56）の左右から、後ろ・外へなびく炎の舌を3枚ずつ。
    # 角度は 0＝顔の向き（上）なので、90°より大きい＝後ろ向き。胴の下に敷くので、根元は頭に隠れ、はみ出た先だけが見える
    hy = oy + 56
    for ang, length, width, root in ((104, 52, 22, 20), (128, 66, 24, 17), (150, 80, 24, 13)):
        for side in (-1, 1):
            back.shape([flame(cx + side * root, hy, length, width, math.radians(side * ang), lean=0.45 * side)], GOLD, axis=(0.0, -1.0))
    return stack(back, sprite, Canvas(*sprite.size))


def fire_wing(src):
    p = FIRE_WING_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    a = body_alpha(sprite)
    back = Canvas(*sprite.size)
    left_x = int(np.nonzero(a.any(axis=0))[0].min())
    # 翼の先の金の炎の刃：先から外（左）へ3枚、炎のように後ろへ反って扇に突き出る。翼の下に敷く
    ty = float(np.nonzero(a[:, left_x + 2])[0].mean())
    for ang, length, width, bend in ((-62, 66, 20, -0.5), (-86, 108, 26, -0.55), (-110, 74, 20, -0.5)):
        poly, spine = curved_blade(left_x + 26, ty, length, width, math.radians(ang), math.radians(bend * 70))
        back.shape([poly], GOLD, axis=(0.3, 1.0), ridge=spine)
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.alpha_composite(back.finish())
    out.alpha_composite(sprite)
    return out


# ---------------------------------------------------------------- 氷竜（アクアマリン・白金）
# v3.199.0（DT-609 手直し・Shooter「氷竜の翼の飾りは全然ダメじゃなかった」「無くした縁取りを一部戻して」）:
#   翼は v3.196.0 の飾り（前の縁の氷の結晶3本・後ろの縁の指の先から垂れる氷柱・先の氷の槍）に戻した。
#   v3.198.0 で前の縁の結晶もやめたのは「顔の前に出るトゲトゲ」を「前へ突き出るもの全部」と広く読み違えたため（ダメと言われたのは頭のティアラだけ）。
#   突き出る飾りの2つ目は、頭の代わりに尾の先の氷の結晶の房（後ろへ3本）。頭は飾らず、首の付け根の白金の首輪とアクアマリンの雫は残す。
#   縁取り（白金）を戻すのは、頭から腰まで（胴の外まわり）。翼・尾には付けない（翼は結晶、尾は房で飾るので）。
ICE_PAD = dict(left=24, top=RIM, right=24, bottom=56)    # 左右は氷柱の冠がはみ出す分
ICE_WING_PAD = dict(left=48, top=46, right=0, bottom=50)


def ice_body(src):
    p = ICE_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    ox, oy = p["left"], p["top"]
    cx = ox + 82.0
    a = body_alpha(sprite)

    def crystal(x, y, length, width, ang_deg):
        r = math.radians(ang_deg)
        poly = spike(x, y, length, width, r, base_w=width)
        dx, dy = math.sin(r), -math.cos(r)
        nx, ny = -dy, dx
        half = [(x, y), (x + dx * length, y + dy * length), (x + nx * width * 0.5 + dx * length * 0.12, y + ny * width * 0.5 + dy * length * 0.12)]
        back.shape([poly], PLATINUM, axis=(0.6, 1.0), facet=half)

    # 尾の先の氷の結晶の房（後ろへ、真ん中が長い3本）。尾の下に敷く
    tail_y = float(np.nonzero(a.any(axis=1))[0].max())
    tail_x = float(np.nonzero(a[int(tail_y) - 6])[0].mean())
    for ang, length, width in ((180, 64, 20), (152, 44, 15), (208, 44, 15)):
        crystal(tail_x, tail_y - 16, length, width, ang)
    # 氷柱の冠（v3.196.0 の氷柱のティアラを後頭部へ移した）：頭のいちばん幅のある所（y≈66）の左右から、後ろ・外へ広がる氷柱を3本ずつ。
    # 火竜の炎のたてがみと違って、まっすぐ鋭い。胴の下に敷くので、根元は頭に隠れ、はみ出た先だけが見える
    hy = oy + 66
    for ang, length, width, root in ((100, 50, 17, 24), (124, 66, 19, 20), (148, 82, 20, 15)):
        for side in (-1, 1):
            crystal(cx + side * root, hy, length, width, side * ang)
    return stack(back, sprite, Canvas(*sprite.size))


def ice_wing(src):
    """v3.196.0 の翼の飾りのまま（DT-609 11/25 Shooter「全然ダメじゃなかった」）"""
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


SPARKLE_SPEC = {   # index.html の fire_sparkle / ice_sparkle の値（*_jewel はここに余白を足して作る）
    "fire": dict(cx=62.4, cy=169.4, sl=(14.2, 152), sr=(110.8, 152), wa=(319, 64.1)),
    "ice": dict(cx=81.5, cy=175.6, sl=(21.4, 152), sr=(141.6, 152), wa=(319, 69.0)),
}


def report(element, body, wing, pad_b, pad_w):
    """DRAGON_PART_SPRITES に貼る値。元の胴の重心・肩・翼の付け根を、余白ぶんずらして写す（胴の高さ 27・翼の幅 25 は絵の大きさに比例）"""
    s = SPARKLE_SPEC[element]
    L, T = pad_b["left"], pad_b["top"]
    print(f"  {element}_jewel: bodyPivot {{ cx: {s['cx'] + L:.1f}, cy: {s['cy'] + T:.1f}, w: {body.width}, h: {body.height} }}"
          f" shoulder L({s['sl'][0] + L:.1f},{s['sl'][1] + T}) R({s['sr'][0] + L:.1f},{s['sr'][1] + T})"
          f" wingAnchor {{ x: {s['wa'][0] + pad_w['left']}, y: {s['wa'][1] + pad_w['top']:.1f} }}"
          f" bodyDrawH: {27 * body.height / 320:.2f} wingDrawW: {25 * wing.width / 320:.2f}")


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
        print(element, "body", sb.size, "->", jb.size, "wing", sw.size, "->", jw.size)
        report(element, jb, jw, pad_b, pad_w)


if __name__ == "__main__":
    main()
