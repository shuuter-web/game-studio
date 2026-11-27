"""Dragon Tide（DT-609）: 2回目の進化の飾りを、全身カットの宝石の絵（*_sparkle）に描き足して *_jewel を作る。

  python3 tools/gen_gem_ornaments.py [竜種...]   # 火竜・氷竜・影竜・緋竜・飛竜・隼竜・燕竜・蜂竜・鮫竜・雷雲竜・亀竜・蛙竜（名指しでその竜種だけ）の *_jewel_body.png / *_jewel_wing.png を書き出し、DRAGON_PART_SPRITES に貼る値を出す

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


def ice_crystal(canvas, x, y, length, width, ang_deg):
    """氷竜の白金の氷の結晶1本（片側の面を明るく）"""
    r = math.radians(ang_deg)
    poly = spike(x, y, length, width, r, base_w=width)
    dx, dy = math.sin(r), -math.cos(r)
    nx, ny = -dy, dx
    half = [(x, y), (x + dx * length, y + dy * length), (x + nx * width * 0.5 + dx * length * 0.12, y + ny * width * 0.5 + dy * length * 0.12)]
    canvas.shape([poly], PLATINUM, axis=(0.6, 1.0), facet=half)


ICE_TAIL_CRYSTALS = ((180, 64, 20), (152, 44, 15), (208, 44, 15))   # 尾の先の氷の結晶の房（向き・長さ・幅。後ろへ、真ん中が長い3本）


def ice_tailtip():
    """v3.234.0（DT-609 手直し・11/26 Shooter「氷竜も先端がいい」）: 尾の先の氷の結晶の房を、動く尻尾の先に付ける絵（根元が上）"""
    c = Canvas(110, 80)
    for ang, length, width in ICE_TAIL_CRYSTALS:
        ice_crystal(c, 55, 6, length, width, ang)
    c.shape([ellipse_poly(55, 6, 8, 6, 16)], PLATINUM, axis=(0.4, 1.0), outline=2.5)
    return c.finish(), (55, 6)


def ice_body(src, tail="root"):
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
    # tail="tip"（v3.234.0）は胴の絵に描かず、ice_tailtip の絵を動く尻尾の先に重ねる（余白は "root" と同じにして寸法の値をそろえる）
    if tail == "root":
        tail_y = float(np.nonzero(a.any(axis=1))[0].max())
        tail_x = float(np.nonzero(a[int(tail_y) - 6])[0].mean())
        for ang, length, width in ICE_TAIL_CRYSTALS:
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


# ---------------------------------------------------------------- 影竜・緋竜・飛竜（v3.205.0・DT-609）
# 11/25 Shooter「他の竜では、外側に広がるだけでなく上に乗ってる飾りとか、色々バリエーションを出して」「色も金属に限らなくていい」
# 「首輪は良くないが、襷掛けとか斜め掛けなら行ける」。火竜・氷竜はどちらも「外へ突き出る金属の飾り」なので、
# 3竜種は飾る部位・形・素材をばらばらにした（同じ形の飾りが群れごとに並ばないように）:
#   影竜（アメジスト）… 背に乗る黒曜石の背びれ（首の付け根から尾まで）と尾の先から突き出る黒曜石の刃・翼の先の月長石の三日月と雫
#   緋竜（ガーネット）… 左肩から右の腰へ斜めに掛けた白絹の襷（藍の縁）と、腰の結び目から後ろ・外へなびく2本の垂れ。翼は飾らない
#   飛竜（エメラルド）… 背に乗る象牙の鞍板（真ん中に琥珀、左右の角が胴から少しはみ出す）・尾の先の緋色の羽根飾り3枚。翼は飾らない
# 「上に乗る」飾り（背びれ・襷・鞍板）は胴の上（front）に描く。輪郭の外へ出る分だけが輪郭を変える。
OBSIDIAN = dict(light=(176, 150, 222), base=(46, 34, 70), dark=(14, 10, 24), line=(0, 0, 0))
MOONSTONE = dict(light=(255, 255, 255), base=(214, 228, 248), dark=(132, 150, 204), line=(28, 28, 70))
SILK = dict(light=(255, 255, 255), base=(246, 242, 232), dark=(196, 186, 176), line=(36, 20, 40))
INDIGO = dict(light=(110, 140, 220), base=(40, 56, 130), dark=(18, 24, 70), line=(10, 10, 30))
IVORY = dict(light=(255, 252, 238), base=(238, 224, 190), dark=(168, 142, 100), line=(66, 40, 16))
AMBER = dict(light=(255, 236, 160), base=(244, 156, 36), dark=(166, 76, 8), line=(66, 30, 4))
SCARLET = dict(light=(255, 214, 120), base=(232, 64, 40), dark=(132, 18, 30), line=(48, 8, 10))
GARNET_KNOT = dict(light=(255, 150, 160), base=(150, 20, 40), dark=(70, 6, 20), line=(30, 4, 8))


def ellipse_poly(cx, cy, rx, ry, steps=28):
    return [(cx + rx * math.cos(i / steps * math.tau), cy + ry * math.sin(i / steps * math.tau)) for i in range(steps)]


def clip_to(canvas, sprite_alpha, grow_px):
    """front に描いた飾りを、胴の輪郭を grow_px だけ広げた形で切る（襷が胴に巻き付いて見えるように、外へは少しだけ出す）"""
    h, w = sprite_alpha.shape
    m = Image.fromarray((sprite_alpha * 255).astype(np.uint8), "L").resize((w * SS, h * SS), Image.BILINEAR)
    m = m.point(lambda v: 255 if v >= 128 else 0)
    for _ in range(int(round(grow_px * SS / 2))):
        m = m.filter(ImageFilter.MaxFilter(3))
    r, g, b, a = canvas.layer.split()
    canvas.layer = Image.merge("RGBA", (r, g, b, ImageChops.multiply(a, m)))


SHADOW_PAD = dict(left=0, top=0, right=0, bottom=40)        # 尾の先から突き出る黒曜石の刃の分
SHADOW_WING_PAD = dict(left=70, top=0, right=0, bottom=40)  # 翼の先の三日月と、垂れる雫の分


def shadow_body(src):
    p = SHADOW_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    front = Canvas(*sprite.size)
    back = Canvas(*sprite.size)
    cx = p["left"] + 74.5
    # 黒曜石の背びれ：背骨に沿って、後ろ向きの菱形の板を少しずつ重ねて並べる（前の板が上）。
    # 頭・首には付けない（顔の前に出さない・首輪に見せない）。胴より細い尾のあたりは小さく
    fins = ((118, 13, 30), (146, 16, 34), (176, 16, 34), (206, 14, 30), (234, 13, 28), (262, 11, 24), (288, 9, 22))
    for y, half, length in reversed(fins):
        poly = [(cx, y - length * 0.35), (cx + half, y), (cx + half * 0.35, y + length * 0.55), (cx, y + length * 0.75),
                (cx - half * 0.35, y + length * 0.55), (cx - half, y)]
        front.shape([poly], OBSIDIAN, axis=(0.4, 1.0), outline=3.5, ridge=[(cx, y - length * 0.3), (cx, y + length * 0.6)],
                    facet=[(cx, y - length * 0.35), (cx + half, y), (cx + half * 0.35, y + length * 0.55), (cx, y + length * 0.75)])
    # 尾の先から後ろへ突き出る黒曜石の刃（尾の下に敷く）
    ty = 300
    back.shape([[(cx, ty + 52), (cx + 12, ty + 20), (cx + 7, ty - 6), (cx - 7, ty - 6), (cx - 12, ty + 20)]], OBSIDIAN,
               axis=(1.0, 0.3), ridge=[(cx, ty), (cx, ty + 44)], facet=[(cx, ty - 6), (cx + 12, ty + 20), (cx, ty + 52)])
    return stack(back, sprite, front)


def shadow_wing(src):
    p = SHADOW_WING_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    a = body_alpha(sprite)
    back = Canvas(*sprite.size)
    w, h = sprite.size
    left_x = int(np.nonzero(a.any(axis=0))[0].min())
    ty = float(np.nonzero(a[:, left_x + 2])[0].mean())
    # 月長石の三日月：翼の先を外側から抱くように。丸の外側の弧と、右へずらした丸の内側の弧で切り出す
    mx, my, r_out = left_x + 26, ty + 4, 50
    outer, inner = [], []
    for i in range(25):
        t = math.radians(100 + i * 160 / 24)            # 上（100°）→ 左 → 下（260°）
        outer.append((mx + r_out * math.cos(t), my - r_out * math.sin(t)))
    for i in range(25):
        t = math.radians(260 - i * 160 / 24)
        ri = r_out * 0.84
        inner.append((mx + 18 + ri * math.cos(t), my - ri * math.sin(t) * 0.92))
    back.shape([outer + inner], MOONSTONE, axis=(-0.3, 1.0), outline=4.0, ridge=outer[4:-4])
    # 後ろの縁の外側2つの山から、月長石の雫を垂らす（翼の下に敷く）
    lower = np.array([np.nonzero(a[:, x])[0].max() if a[:, x].any() else -1 for x in range(w)], np.float32)
    med = np.median(lower[lower >= 0])
    peaks = []
    for x in range(left_x + 30, w - 40):
        win = lower[max(0, x - 14):x + 15]
        if lower[x] >= 0 and lower[x] == win.max() and (not peaks or x - peaks[-1] > 26) and lower[x] > med + 4:
            peaks.append(x)
    for x in peaks[:2]:
        y0 = lower[x] - 4
        back.shape([[(x - 3, y0), (x + 3, y0), (x + 2, y0 + 14)]], MOONSTONE, outline=2.5)
        back.shape([ellipse_poly(x, y0 + 24, 9, 12)], MOONSTONE, axis=(-0.4, 1.0), outline=3.0)
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.alpha_composite(back.finish())
    out.alpha_composite(sprite)
    return out


def ribbon(x, y, length, width, angle, wave):
    """なびく布の垂れ：幅を保ったまま横へ波打ち（wave＝振れ幅）、先を燕尾（V字の切れ込み）にする。返り値は（形, 芯）"""
    dx, dy = math.sin(angle), -math.cos(angle)
    nx, ny = -dy, dx
    left, right, spine = [], [], []
    steps = 20
    for i in range(steps + 1):
        t = i / steps
        side = wave * math.sin(t * math.pi * 1.6) * t
        half = width * 0.5 * (1 + 0.25 * t)
        px, py = x + dx * length * t + nx * side, y + dy * length * t + ny * side
        left.append((px + nx * half, py + ny * half))
        right.append((px - nx * half, py - ny * half))
        spine.append((px, py))
    notch = (spine[-1][0] - dx * width * 0.8, spine[-1][1] - dy * width * 0.8)
    return left + [notch] + right[::-1], spine


CRIMSON_PAD = dict(left=0, top=0, right=60, bottom=70)   # 腰の結び目から右・後ろへなびく垂れの分


def crimson_body(src):
    p = CRIMSON_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    a = body_alpha(sprite)
    front = Canvas(*sprite.size)
    # 襷：左肩（頭が上の絵で左）から右の腰へ斜めに。藍の太い帯の上に白絹の帯を重ねて、藍を縁に見せる
    path = [(46, 116), (80, 150), (112, 188), (140, 222), (152, 240)]   # 肩の付け根から（腕・手の上は通さない）
    front.stroke(path, 32, INDIGO, axis=(1.0, 1.0), outline=3.0, ridge=False)
    front.stroke(path, 21, SILK, axis=(1.0, 1.0), outline=0.1, ridge=True)
    clip_to(front, a, 4.0)          # 胴の外へは帯の厚みの分だけ（巻き付いて見える）
    # 結び目から後ろ・外（右下）へなびく2本の垂れ。胴の外へ突き出る（切らない）。
    # 刃に見えないよう、幅を保ったまま波打たせ、先を燕尾に切る
    tails = Canvas(*sprite.size)
    kx, ky = 152, 240
    for ang, length, width, wave in ((158, 104, 17, 9.0), (132, 84, 15, -8.0)):
        poly, spine = ribbon(kx, ky, length, width, math.radians(ang), wave)
        tails.shape([poly], INDIGO, axis=(1.0, 1.0), outline=3.0)
        inner_poly, _ = ribbon(kx, ky, length - 6, width * 0.55, math.radians(ang), wave)
        tails.shape([inner_poly], SILK, axis=(1.0, 1.0), outline=0.1)
    # 結び目（ガーネットの留め玉。濃い赤なので白絹の上で目立つ）
    tails.shape([ellipse_poly(kx, ky, 14, 12)], SILK, axis=(0.5, 1.0), outline=3.0)
    tails.shape([ellipse_poly(kx, ky, 7, 7, 16)], GARNET_KNOT, axis=(0.5, 1.0), outline=2.0)
    out = stack(Canvas(*sprite.size), sprite, front)
    out.alpha_composite(tails.finish())
    return out


def crimson_wing(src):
    """緋竜の翼は飾らない（襷が胴を斜めに横切るので、翼まで飾ると重い）。None＝*_sparkle の翼の絵をそのまま使う"""
    return None


WYVERN_PAD = dict(left=8, top=0, right=8, bottom=64)    # 鞍板の角と、尾の先の羽根飾りの分


def feather(x, y, length, width, ang_deg, bend):
    """羽根：曲がった刃より幅の広い葉の形（根元が細く、中ほどが太い）。返り値は（形, 軸の折れ線）"""
    pts_l, pts_r, spine = [], [], []
    px, py = x, y
    steps = 18
    for i in range(steps + 1):
        t = i / steps
        a = math.radians(ang_deg) + bend * t * t
        dx, dy = math.sin(a), -math.cos(a)
        nx, ny = -dy, dx
        half = width * 0.5 * math.sin(math.pi * min(1.0, 0.12 + t * 0.95)) ** 0.7
        pts_l.append((px + nx * half, py + ny * half))
        pts_r.append((px - nx * half, py - ny * half))
        spine.append((px, py))
        px, py = px + dx * length / steps, py + dy * length / steps
    return pts_l + pts_r[::-1], spine[1:-2]


def wyvern_body(src):
    p = WYVERN_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx = p["left"] + 64.5
    # 象牙の鞍板：肩から腰の手前まで背に乗る盾の形。左右の角は胴の幅から少しはみ出す
    plate = [(cx, 126), (cx + 30, 134), (cx + 54, 148), (cx + 34, 160), (cx + 30, 186), (cx + 14, 206), (cx, 214),
             (cx - 14, 206), (cx - 30, 186), (cx - 34, 160), (cx - 54, 148), (cx - 30, 134)]
    front.shape([plate], IVORY, axis=(0.3, 1.0), outline=4.0, ridge=[(cx, 132), (cx, 208)],
                facet=[(cx, 126), (cx + 30, 134), (cx + 54, 148), (cx + 34, 160), (cx + 30, 186), (cx + 14, 206), (cx, 214)])
    front.shape([[(cx, 152), (cx + 14, 170), (cx, 190), (cx - 14, 170)]], AMBER, axis=(0.5, 1.0), outline=3.0)   # 琥珀（菱形のカット）
    for sy in (140, 200):     # 鞍板の前後に小さな琥珀の粒
        front.shape([ellipse_poly(cx, sy, 4.5, 4.5, 12)], AMBER, outline=2.0)
    # 尾の先の緋色の羽根飾り（後ろへ扇に3枚。尾の下に敷く）
    tx, ty = cx, 306
    for ang, length, width, bend in ((180, 74, 22, 0.0), (156, 58, 18, -0.25), (204, 58, 18, 0.25)):
        poly, spine = feather(tx, ty, length, width, ang, bend)
        back.shape([poly], SCARLET, axis=(0.0, 1.0), outline=3.5, ridge=spine)
    return stack(back, sprite, front)


def wyvern_wing(src):
    """飛竜の翼は飾らない（鞍板と羽根飾りで足りる。翼まで飾ると火竜・氷竜と同じ「翼に飾り」になる）。None＝*_sparkle の翼の絵をそのまま使う"""
    return None


# ---------------------------------------------------------------- 隼竜・燕竜・蜂竜（v3.216.0・DT-609「引き続きお願いします」）
SAPPHIRE = dict(light=(170, 210, 255), base=(40, 84, 200), dark=(14, 30, 110), line=(6, 12, 50))
SILVER = dict(light=(255, 255, 255), base=(214, 220, 230), dark=(128, 138, 156), line=(30, 34, 48))
LACQUER = dict(light=(150, 150, 170), base=(28, 26, 34), dark=(6, 6, 10), line=(0, 0, 0))
PEARL = dict(light=(255, 255, 255), base=(244, 236, 236), dark=(190, 176, 196), line=(60, 44, 70))
HONEY = dict(light=(255, 238, 150), base=(236, 146, 20), dark=(150, 66, 6), line=(60, 26, 2))
ONYX = dict(light=(150, 150, 160), base=(30, 30, 36), dark=(4, 4, 8), line=(0, 0, 0))

# v3.233.0（DT-609 手直し・11/26 Shooter「三体とも、2進化の追加パーツがやや地味なのでもう一要素くらい追加できますか」
# 「蜂は、追加パーツが黄色くて目立たないので違う色に」「尻尾にパーツを追加する場合、ゲームで描画される動く尻尾の先端も選択肢にできますか」）:
#   尾の飾りは2通り作る。tail="root"＝今までどおり胴の絵の尾の付け根に描く（*_jewel）。tail="tip"＝胴の絵には描かず（*_jewelt）、
#   別の絵（*_tailtip。根元が上・飾りは下へ伸びる）にして、ゲームが動く尻尾の先に向きを合わせて重ねる。
AMETHYST = dict(light=(236, 200, 255), base=(150, 70, 210), dark=(64, 18, 110), line=(26, 4, 50))

FALCON_PAD_ROOT = dict(left=58, top=0, right=58, bottom=78)   # 後頭部の飾り羽根（3枚ずつ）と、尾の先の羽根の扇の分
FALCON_PAD_TIP = dict(left=58, top=0, right=58, bottom=0)
FALCON_TAIL_Y = 300          # 尾の先（元の絵の画素）


def falcon_tail_fan(canvas, tx, ty):
    """隼竜の尾の飾り：サファイアの羽根3枚の扇（下へ）と、根元の銀の留め具"""
    for ang, length, width, bend in ((180, 78, 22, 0.0), (154, 62, 17, -0.25), (206, 62, 17, 0.25)):
        poly, spine = feather(tx, ty, length, width, ang, bend)
        canvas.shape([poly], SAPPHIRE, axis=(0.3, 1.0), outline=3.5, ridge=spine)
    canvas.shape([ellipse_poly(tx, ty + 2, 8, 6, 16)], SILVER, axis=(0.4, 1.0), outline=2.5)


def falcon_body(src, tail="root"):
    """隼竜（水晶）：後頭部から後ろ・外へ流れるサファイアの飾り羽根を左右3枚ずつ（v3.233.0 で2→3枚・長く）。根元に銀の留め具とサファイアの粒。
    尾の先にサファイアの羽根の扇（v3.233.0 で足した）。頭の前・首には巻かない。翼は飾らない（羽根の翼なので羽根だらけになる）"""
    p = FALCON_PAD_ROOT if tail == "root" else FALCON_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx = p["left"] + 63.0
    for sd in (-1, 1):
        rx, ry = cx + sd * 26, 84          # 後頭部の左右の角
        for ang, length, width, bend in ((180 + sd * -30, 104, 22, sd * -0.35), (180 + sd * -52, 86, 19, sd * -0.3), (180 + sd * -76, 64, 15, sd * -0.25)):
            poly, spine = feather(rx, ry, length, width, ang, bend)
            back.shape([poly], SAPPHIRE, axis=(0.3, 1.0), outline=3.5, ridge=spine)
        front.shape([ellipse_poly(rx, ry, 8, 7, 16)], SILVER, axis=(0.4, 1.0), outline=2.5)
        front.shape([ellipse_poly(rx, ry, 3.5, 3.5, 12)], SAPPHIRE, axis=(0.4, 1.0), outline=1.5)
    if tail == "root":
        falcon_tail_fan(back, cx, FALCON_TAIL_Y)
    return stack(back, sprite, front)


def falcon_tailtip():
    c = Canvas(92, 92)
    falcon_tail_fan(c, 46, 6)
    return c.finish(), (46, 6)


def falcon_wing(src):
    return None


SWALLOW_PAD_ROOT = dict(left=40, top=0, right=40, bottom=150)   # 尾の先から後ろへ伸びる燕尾の飾り紐（2対）の分
SWALLOW_PAD_TIP = dict(left=40, top=0, right=40, bottom=0)
SWALLOW_TAIL_Y = 306


def swallow_streamers(canvas, tx, ty):
    """燕竜の尾の飾り：黒漆の飾り紐（燕の尾羽）を外側の長い1対・内側の短い1対、その先の真珠。付け根に金の留め具"""
    for sd in (-1, 1):
        for length, width, spread, bend, pearl in ((150, 16, 18, 0.34, 8), (92, 11, 8, 0.2, 6)):
            poly, spine = curved_blade(tx, ty, length, width, math.radians(180 - sd * spread), sd * bend)
            canvas.shape([poly], LACQUER, axis=(1.0, 0.4), outline=3.0, ridge=spine)
            ex, ey = spine[-1]
            canvas.shape([ellipse_poly(ex, ey + 4, pearl, pearl + 1, 16)], PEARL, axis=(-0.4, 1.0), outline=2.5)
    canvas.shape([ellipse_poly(tx, ty + 2, 10, 9, 16)], GOLD, axis=(0.4, 1.0), outline=2.5)


def swallow_body(src, tail="root"):
    """燕竜（パライバ）：尾の先から二又に伸びる黒漆の飾り紐（v3.233.0 で長く・内側にもう1対）と先の真珠。
    背骨の真珠3つに加えて、左の肩から右の腰へ斜めに掛かる真珠の連（襷掛け。v3.233.0 で足した）"""
    p = SWALLOW_PAD_ROOT if tail == "root" else SWALLOW_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx = p["left"] + 53.0
    if tail == "root":
        swallow_streamers(back, cx, SWALLOW_TAIL_Y)
    for y in (120, 140, 158):          # 背骨に乗る真珠（首の付け根から肩の間）
        front.shape([ellipse_poly(cx, y, 6.5, 6.5, 16)], PEARL, axis=(-0.4, 1.0), outline=2.5)
    # 真珠の連の襷：左の肩から右の腰へ。少し弓なりに。粒と粒の間に金の小さな留め
    x0, y0, x1, y1 = cx - 38, 168, cx + 36, 262
    for k in range(10):
        t = k / 9
        x = x0 + (x1 - x0) * t
        y = y0 + (y1 - y0) * t + 10 * math.sin(math.pi * t)
        front.shape([ellipse_poly(x, y, 5.2, 5.2, 14)], PEARL, axis=(-0.4, 1.0), outline=2.2)
    return stack(back, sprite, front)


def swallow_tailtip():
    c = Canvas(130, 168)
    swallow_streamers(c, 65, 8)
    return c.finish(), (65, 8)


def swallow_wing(src):
    return None


HORNET_PAD_ROOT = dict(left=40, top=0, right=40, bottom=76)    # 後頭部の触角の飾りと、尾の先から後ろへ伸びる針の分
HORNET_PAD_TIP = dict(left=40, top=0, right=40, bottom=0)
HORNET_TAIL_Y = 312


def hexagon(cx, cy, r):
    return [(cx + r * math.cos(math.radians(30 + 60 * i)), cy + r * math.sin(math.radians(30 + 60 * i))) for i in range(6)]


def hornet_stinger(canvas, tx, ty):
    """蜂竜の尾の飾り：紫水晶の大きな針（芯に黒瑪瑙）と、根元の金の留め具"""
    canvas.shape([[(tx - 12, ty - 4), (tx + 12, ty - 4), (tx + 4, ty + 48), (tx, ty + 70), (tx - 4, ty + 48)]], AMETHYST, axis=(1.0, 0.3),
                 outline=3.0, ridge=[(tx, ty), (tx, ty + 60)], facet=[(tx, ty - 4), (tx + 12, ty - 4), (tx + 4, ty + 48), (tx, ty + 70)])
    canvas.shape([ellipse_poly(tx, ty - 2, 13, 8, 18)], GOLD, axis=(0.4, 1.0), outline=2.5)


def hornet_body(src, tail="root"):
    """蜂竜（シトリン＋オニキス）：背に乗る紫水晶の巣板（v3.233.0 で蜜蝋の黄色→紫水晶、房を6→10に）。
    後頭部から後ろ・外へ反る黒瑪瑙の触角の飾り（先に紫水晶の粒。v3.233.0 で足した）。尾の先に紫水晶の針"""
    p = HORNET_PAD_ROOT if tail == "root" else HORNET_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx = p["left"] + 82.3
    # 触角の飾り：後頭部の左右から後ろ・外へ大きく反る
    for sd in (-1, 1):
        rx, ry = cx + sd * 20, 62
        poly, spine = curved_blade(rx, ry, 100, 12, math.radians(180 + sd * -42), sd * -0.3)
        back.shape([poly], ONYX, axis=(1.0, 0.4), outline=3.0, ridge=spine)
        ex, ey = spine[-1]
        back.shape([ellipse_poly(ex, ey, 8, 8, 16)], AMETHYST, axis=(-0.4, 1.0), outline=2.5)
        front.shape([ellipse_poly(rx, ry, 6, 5, 14)], GOLD, axis=(0.4, 1.0), outline=2.0)
    # 巣板：腰の上に10房（3・4・3）
    r = 14
    dx, dy = r * math.sqrt(3), r * 1.5
    cells = [(cx + (k - 1) * dx, 176) for k in range(3)] + [(cx + (k - 1.5) * dx, 176 + dy) for k in range(4)] + [(cx + (k - 1) * dx, 176 + 2 * dy) for k in range(3)]
    for hx, hy in cells:
        front.shape([hexagon(hx, hy, r - 1)], AMETHYST, axis=(0.4, 1.0), outline=3.0,
                    facet=[(hx, hy), *hexagon(hx, hy, r - 1)[:3]])
    if tail == "root":
        hornet_stinger(back, cx, HORNET_TAIL_Y)
    return stack(back, sprite, front)


def hornet_tailtip():
    c = Canvas(40, 86)
    hornet_stinger(c, 20, 8)
    return c.finish(), (20, 8)


def hornet_wing(src):
    return None


# ---------------------------------------------------------------- 鮫竜・蛙竜・亀竜・雷雲竜（v3.235.0・DT-609「続けて他の竜もお願いします」）
# v3.244.0（DT-609 11/27）: 鮫竜・亀竜・雷雲竜は専用の絵（tools/gen_dragon_design.py）ができたので、飾りの位置をその輪郭に合わせ直した
# （それまでは燕竜・ガーゴイル・影竜の絵を借りていた）。尾の飾りは4竜種とも動く尻尾の先（"tip"）を既定にする
NACRE = dict(light=(255, 255, 255), base=(230, 234, 246), dark=(146, 158, 198), line=(20, 32, 78))
CORAL = dict(light=(255, 196, 186), base=(228, 72, 72), dark=(140, 20, 36), line=(60, 6, 14))
VERMILION = dict(light=(255, 176, 146), base=(212, 44, 30), dark=(118, 10, 10), line=(40, 0, 0))
DRUMHEAD = dict(light=(255, 252, 236), base=(242, 228, 192), dark=(192, 162, 112), line=(40, 10, 10))
ELECTRIC = dict(light=(240, 255, 255), base=(96, 204, 255), dark=(30, 92, 206), line=(8, 18, 70))
TORTOISESHELL = dict(light=(255, 216, 146), base=(200, 116, 38), dark=(96, 42, 8), line=(40, 16, 2))
WHITE_JADE = dict(light=(255, 255, 250), base=(236, 240, 226), dark=(168, 184, 158), line=(36, 50, 36))
LOTUS = dict(light=(255, 238, 248), base=(246, 150, 192), dark=(196, 70, 130), line=(90, 20, 60))
LILYPAD = dict(light=(170, 236, 200), base=(36, 146, 110), dark=(12, 78, 60), line=(4, 38, 28))

# v3.253.0（DT-650 11/28 Shooter「鮫竜の2進化の飾りが地味なので、もう少し目立つものに。輪郭が変わるパーツが欲しい」）:
# 前の飾り（真珠層の鰭・背びれ）は胴の輪郭の内側に収まって目立たなかった。後頭部の鰭を、えらの後ろから横・後ろへ大きく枝を張る
# 赤珊瑚の枝（石の青と反対の色）に替え、胸びれの翼の後ろの縁に真珠層の鮫の歯の列を並べ、尾びれを大きくして、輪郭そのものを変える
SHARK_PAD_ROOT = dict(left=120, top=0, right=120, bottom=84)    # 赤珊瑚の枝が左右へ、尾びれが尾の先から後ろへはみ出す分
SHARK_PAD_TIP = dict(left=120, top=0, right=120, bottom=0)
SHARK_WING_PAD = dict(left=0, top=0, right=0, bottom=70)       # 翼の後ろの縁から後ろへ突き出る鮫の歯の分
SHARK_TAIL_Y = 312
# v3.252.0（DT-650）: 新しいデザイン（ホホジロザメの胴・幅 147）に合わせた位置
SHARK_CX = 73.5          # 胴の真ん中（dragon_shark_body.png・幅 147）
SHARK_HEAD_BACK_Y = 100  # 後頭部（えらの後ろ）
SHARK_HEAD_BACK_DX = 30  # 赤珊瑚の枝の根元の左右のずれ（胴の縁の近く）
SHARK_FIN_Y = 122        # 背びれの付け根の先（胴の絵の背びれに重ねる）
# 赤珊瑚の枝：（根元からの割合, 向きのずれ°, 長さ, 太さ）。幹は横・後ろへ、枝は前と後ろへ分かれる
SHARK_CORAL_TRUNK = (108, 136, 26)            # 幹の向き（0＝顔の向き・90＝真横）・長さ・太さ
SHARK_CORAL_BRANCHES = ((0.3, 50, 66, 17), (0.5, -42, 56, 15), (0.75, 44, 46, 13))
SHARK_TEETH = 4          # 翼の後ろの縁に並べる鮫の歯の数


def shark_caudal(canvas, tx, ty):
    """鮫竜の尾の飾り：真珠層（螺鈿の白）の大きな三日月の尾びれと、根元の赤珊瑚の玉"""
    for sd in (-1, 1):
        poly, spine = curved_blade(tx, ty, 78, 26, math.radians(180 - sd * 46), sd * 0.8)
        canvas.shape([poly], NACRE, axis=(0.4, 1.0), outline=3.5, ridge=spine)
    canvas.shape([ellipse_poly(tx, ty + 3, 9, 9, 16)], CORAL, axis=(-0.4, 1.0), outline=2.5)


def coral_branch(canvas, rx, ry, sd):
    """赤珊瑚の枝（sd＝-1 左・1 右）。幹から3本の枝が分かれ、先に丸い珊瑚の粒"""
    ang, length, width = SHARK_CORAL_TRUNK
    trunk, spine = curved_blade(rx, ry, length, width, math.radians(sd * ang), sd * 0.35)
    shapes = [(trunk, spine)]
    pts = spine + [spine[-1]]
    for at, dang, blen, bw in SHARK_CORAL_BRANCHES:
        bx, by = pts[min(len(pts) - 1, int(at * len(pts)))]
        shapes.append(curved_blade(bx, by, blen, bw, math.radians(sd * (ang + dang)), sd * 0.3))
    for poly, sp in shapes:
        canvas.shape([poly], CORAL, axis=(0.4, 1.0), outline=4.0, ridge=sp)
    for poly, sp in shapes:   # 枝の先の粒（先の少し手前に置いて、細い先を丸くする）
        ex, ey = sp[-1]
        canvas.shape([ellipse_poly(ex, ey, 9, 9, 14)], CORAL, axis=(-0.4, 1.0), outline=2.0)
    canvas.shape([ellipse_poly(rx, ry, 12, 12, 16)], NACRE, axis=(-0.4, 1.0), outline=2.5)   # 根元の真珠


def shark_body(src, tail="root"):
    """鮫竜（サファイア）：えらの後ろから横・後ろへ大きく枝を張る赤珊瑚（根元に真珠）・背骨に乗って後ろへ反る真珠層の背びれ。
    尾の先に大きな三日月の尾びれ。翼の後ろの縁に真珠層の鮫の歯"""
    p = SHARK_PAD_ROOT if tail == "root" else SHARK_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx = p["left"] + SHARK_CX
    # 胴の上（front）に描く（v3.252.0: 後ろに描くと太い胴と胸びれの翼に隠れた）
    for sd in (-1, 1):
        coral_branch(front, cx + sd * SHARK_HEAD_BACK_DX, SHARK_HEAD_BACK_Y, sd)
    f = SHARK_FIN_Y - 148   # 背びれを胴の絵の背びれの位置へずらす分
    fin = [(cx - 6, 150 + f), (cx + 6, 148 + f), (cx + 20, 196 + f), (cx + 34, 250 + f), (cx + 6, 226 + f), (cx - 6, 212 + f)]
    front.shape([fin], NACRE, axis=(1.0, 0.5), outline=4.0, ridge=[(cx, 154 + f), (cx + 10, 200 + f), (cx + 32, 246 + f)],
                facet=[(cx + 6, 148 + f), (cx + 20, 196 + f), (cx + 34, 250 + f), (cx + 10, 200 + f)])
    if tail == "root":
        shark_caudal(back, cx, SHARK_TAIL_Y)
    return stack(back, sprite, front)


def shark_tailtip():
    c = Canvas(150, 96)
    shark_caudal(c, 75, 8)
    return c.finish(), (75, 8)


def shark_wing(src):
    """胸びれの翼の後ろの縁に、真珠層の鮫の歯（三角）を並べて後ろへ突き出す。翼の下に敷いて、はみ出た所だけを見せる"""
    p = SHARK_WING_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    a = body_alpha(sprite)
    xs = np.nonzero(a.any(axis=0))[0]
    x0, x1 = xs.min(), xs.max()
    edge = edge_line(a, x0 + (x1 - x0) * 0.12, x0 + (x1 - x0) * 0.78, "lower", -10)
    back = Canvas(*sprite.size)
    for k in range(SHARK_TEETH):
        x, y = edge[int((k + 0.5) / SHARK_TEETH * len(edge))]
        size = 66 - abs(k - (SHARK_TEETH - 1) / 2) * 8   # 真ん中が大きい
        back.shape([spike(x, y, size, 32, math.radians(168), base_w=38)], NACRE, axis=(0.4, 1.0), outline=4.0,
                   ridge=[(x, y), (x + math.sin(math.radians(168)) * size * 0.8, y - math.cos(math.radians(168)) * size * 0.8)])
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.alpha_composite(back.finish())
    out.alpha_composite(sprite)
    return out


THUNDER_PAD_ROOT = dict(left=54, top=0, right=54, bottom=84)   # 後頭部の雷太鼓の輪が左右へ、稲妻が尾の先から後ろへはみ出す分
THUNDER_PAD_TIP = dict(left=54, top=0, right=54, bottom=0)
THUNDER_TAIL_Y = 306
THUNDER_TAIL_DX = 0      # v3.252.0（DT-650）: 胴の絵の尻尾を除いたので、尾の付け根は真ん中の下
THUNDER_CX = 76.5
THUNDER_RING_Y = 84      # 輪の両端の高さ（稲妻の角の後ろ）
THUNDER_BOLT = [(-8, 0), (8, 0), (4, 24), (14, 24), (-1, 52), (8, 52), (-10, 84), (-5, 58), (-14, 58), (-3, 30), (-13, 30)]


def thunder_bolt(canvas, tx, ty):
    """雷雲竜の尾の飾り：青白い水晶の稲妻と、根元の朱漆の玉"""
    canvas.shape([[(tx + x, ty + y) for x, y in THUNDER_BOLT]], ELECTRIC, axis=(0.6, 1.0), outline=3.5,
                 ridge=[(tx, ty + 4), (tx + 6, ty + 25), (tx - 2, ty + 54), (tx - 9, ty + 80)])
    canvas.shape([ellipse_poly(tx, ty + 1, 8, 6, 16)], VERMILION, axis=(0.4, 1.0), outline=2.5)


def drum(canvas, x, y, r):
    """雷太鼓：朱漆の胴の縁＋生成りの皮＋三つ巴（巴は3つの小さな玉で描く）"""
    canvas.shape([ellipse_poly(x, y, r, r, 24)], VERMILION, axis=(0.4, 1.0), outline=3.0)
    canvas.shape([ellipse_poly(x, y, r * 0.7, r * 0.7, 24)], DRUMHEAD, axis=(-0.3, 1.0), outline=1.8)
    for k in range(3):
        a = math.radians(90 + k * 120)
        canvas.shape([ellipse_poly(x + math.cos(a) * r * 0.32, y + math.sin(a) * r * 0.32, r * 0.2, r * 0.2, 12)], VERMILION, outline=1.2)


def thunder_body(src, tail="root"):
    """雷雲竜（ヘリオドール）：雷神の太鼓の輪。後頭部の後ろで弓なりに張った黒漆の輪が首の下を通って左右へ広がり、
    輪の左右に朱漆の雷太鼓を2つずつ（顔の前へは出さず、頭の横より後ろ）。尾の先に青白い水晶の稲妻。翼は飾らない"""
    p = THUNDER_PAD_ROOT if tail == "root" else THUNDER_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx = p["left"] + THUNDER_CX

    def ring(t):   # 輪の上の点（t＝-1 左端〜1 右端）。真ん中が後ろ（首の下）へ垂れる弓
        return cx + t * 110, THUNDER_RING_Y + 42 * (1 - t * t)
    back.stroke([ring(i / 20 * 2 - 1) for i in range(21)], 7, LACQUER, axis=(0.3, 1.0), outline=3.0)
    for t in (-1, -0.74, 0.74, 1):
        drum(front, *ring(t), 15)
    if tail == "root":
        thunder_bolt(back, cx + THUNDER_TAIL_DX, THUNDER_TAIL_Y)
    return stack(back, sprite, front)


def thunder_tailtip():
    c = Canvas(40, 96)
    thunder_bolt(c, 20, 6)
    return c.finish(), (20, 6)


def thunder_wing(src):
    return None


TORTOISE_PAD_ROOT = dict(left=0, top=0, right=0, bottom=80)   # 尾の先の白玉の璧と朱の房の分
TORTOISE_PAD_TIP = dict(left=0, top=0, right=0, bottom=0)
# v3.252.0（DT-650）: 鎧竜（アンキロサウルス）の新しいデザイン（幅 181）に合わせた位置。背の装甲の縁にべっ甲の縁甲板を並べる
TORTOISE_TAIL_Y = 308
TORTOISE_TAIL_DX = 0     # 尾の付け根は真ん中の下
TORTOISE_SHELL = (90.5, 172, 1.0)     # 胴の絵の背の装甲の真ん中と大きさ
TORTOISE_RIM = (64, 86)                # べっ甲の縁甲板を並べる楕円（背の装甲の縁）
TORTOISE_RIM_PLATES = 18
TORTOISE_SPINE_PLATES = 5   # v3.252.0: 背骨の上の大きな甲板の数
TORTOISE_SPINE_STEP = 34    # 甲板の間隔（px）
TORTOISE_SIDE_DX = 36       # 左右の小さな甲板の列の、背骨からの距離


def tortoise_pendant(canvas, tx, ty):
    """亀竜の尾の飾り：白玉（白い翡翠）の璧（真ん中に穴のある円盤）と、その下に垂れる朱の絹の房"""
    canvas.stroke([(tx, ty), (tx, ty + 14)], 3.0, VERMILION, outline=1.5, ridge=False)
    canvas.shape([ellipse_poly(tx, ty + 24, 14, 14, 28)], WHITE_JADE, axis=(-0.4, 1.0), outline=3.0)
    canvas.shape([ellipse_poly(tx, ty + 24, 4.5, 4.5, 16)], LILYPAD, outline=1.5)
    canvas.shape([ellipse_poly(tx, ty + 43, 4.5, 4.5, 14)], VERMILION, outline=2.0)   # 房の結び目
    canvas.shape([[(tx - 4, ty + 46), (tx + 4, ty + 46), (tx + 12, ty + 76), (tx - 12, ty + 76)]], VERMILION, axis=(1.0, 0.2), outline=2.5,
                 ridge=[(tx, ty + 48), (tx, ty + 74)])


def tortoise_body(src, tail="root"):
    """亀竜（翡翠）：背に乗るべっ甲（鼈甲）の甲羅。腰の細い所では胴の輪郭からはみ出す。甲羅は六角の甲板（背の3枚・左右の2枚ずつ）と縁で描く。
    尾の先に白玉の璧と朱の房。翼は飾らない"""
    p = TORTOISE_PAD_ROOT if tail == "root" else TORTOISE_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    # v3.244.0（DT-609 11/27）: 専用の絵は胴そのものが翡翠の甲羅になったので、甲羅を丸ごと覆わず、
    # 翡翠の甲羅の縁にべっ甲の縁甲板（TORTOISE_RIM_PLATES 枚）を並べ、背の真ん中の筋にだけ小さな甲板を3枚乗せる（翡翠が見えるように）
    scx, cy, k = TORTOISE_SHELL
    cx = p["left"] + scx
    # v3.252.0（DT-650）: 鎧竜の新しい胴では、縁に並べた甲板が数珠の輪に見えたので、背の装甲の上に乗るべっ甲の装甲板にした
    # （背骨の上に大きな甲板 TORTOISE_SPINE_PLATES 枚、その左右に小さな甲板を1列ずつ。輪にはしない）
    for k in range(TORTOISE_SPINE_PLATES):
        dy = (k - (TORTOISE_SPINE_PLATES - 1) / 2) * TORTOISE_SPINE_STEP
        hx, hy, r = cx, cy + dy, 14
        front.shape([hexagon(hx, hy, r)], TORTOISESHELL, axis=(-0.5, 1.0), outline=2.6, facet=[(hx, hy), *hexagon(hx, hy, r)[:3]])
    for sd in (-1, 1):
        for k in range(TORTOISE_SPINE_PLATES - 1):
            dy = (k - (TORTOISE_SPINE_PLATES - 2) / 2) * TORTOISE_SPINE_STEP
            hx, hy, r = cx + sd * TORTOISE_SIDE_DX, cy + dy, 9.5
            front.shape([hexagon(hx, hy, r)], TORTOISESHELL, axis=(-0.5, 1.0), outline=2.2, facet=[(hx, hy), *hexagon(hx, hy, r)[:3]])
    if tail == "root":
        tortoise_pendant(back, cx + TORTOISE_TAIL_DX, TORTOISE_TAIL_Y)
    return stack(back, sprite, front)


def tortoise_tailtip():
    c = Canvas(40, 86)
    tortoise_pendant(c, 20, 4)
    return c.finish(), (20, 4)


def tortoise_wing(src):
    return None


FROG_LOTUS_BODY = (129, 180, 1.2)      # 蓮を乗せる所（胴の絵）と大きさ
FROG_LOTUS_AIR = (160, 120, 1.0)       # 跳んでいるときの胴の絵（dragon_frog_*_body_air）


def lotus(canvas, x, y, s):
    """背に乗る蓮：深い青緑の蓮の葉（切れ込み）の上に、桃色の蓮の花（外の8枚・内の5枚）と金の花托"""
    pad = []
    for i in range(41):   # 葉：後ろ（+y）に切れ込み
        a = math.radians(90 + 14 + i / 40 * (360 - 28))
        pad.append((x + math.cos(a) * 46 * s, y + math.sin(a) * 43 * s))
    pad.append((x, y + 6 * s))
    canvas.shape([pad], LILYPAD, axis=(0.3, 1.0), outline=3.5)
    for k in range(8):
        poly, spine = feather(x, y, 42 * s, 24 * s, k * 45 + 22.5, 0.0)
        canvas.shape([poly], LOTUS, axis=(0.0, 1.0), outline=2.5, ridge=spine)
    for k in range(5):
        poly, spine = feather(x, y, 27 * s, 17 * s, k * 72, 0.0)
        canvas.shape([poly], LOTUS, axis=(0.5, 1.0), outline=2.2, ridge=spine)
    canvas.shape([ellipse_poly(x, y, 7.5 * s, 7.5 * s, 16)], HONEY, axis=(0.4, 1.0), outline=2.0)


def frog_body(src, tail="tip", air=False):
    """蛙竜（ペリドット）：背に乗る蓮の葉と桃色の蓮の花。尾の先に蓮の蕾（動く尻尾の先だけ。胴の絵の寸法を跳んでいるときの絵と
    共有しているので、胴の絵に余白を足して尾の付け根に描く形は作らない）。翼は飾らない"""
    sprite = padded(src, 0, 0, 0, 0)
    front = Canvas(*sprite.size)
    lotus(front, *(FROG_LOTUS_AIR if air else FROG_LOTUS_BODY))
    return stack(Canvas(*sprite.size), sprite, front)


def frog_tailtip():
    c = Canvas(44, 60)
    x, y = 22, 4
    poly, spine = feather(x, y + 6, 46, 26, 180, 0.0)
    c.shape([poly], LOTUS, axis=(1.0, 0.3), outline=3.0, ridge=spine)
    for sd in (-1, 1):
        poly, spine = feather(x, y + 4, 22, 11, 180 - sd * 34, 0.0)
        c.shape([poly], LILYPAD, axis=(0.4, 1.0), outline=2.2)
    c.shape([ellipse_poly(x, y + 3, 5, 4, 12)], LILYPAD, outline=1.8)
    return c.finish(), (x, y)


def frog_wing(src):
    return None


SPARKLE_SPEC = {   # index.html の fire_sparkle / ice_sparkle の値（*_jewel はここに余白を足して作る）
    "fire": dict(cx=62.4, cy=169.4, sl=(14.2, 152), sr=(110.8, 152), wa=(319, 64.1)),
    "ice": dict(cx=81.5, cy=175.6, sl=(21.4, 152), sr=(141.6, 152), wa=(319, 69.0)),
    # 影竜・緋竜・飛竜の *_sparkle は元の絵と同じ輪郭（下絵のアルファで切った）なので、元の竜種の値のまま
    "shadow": dict(cx=74.5, cy=174.7, sl=(22.8, 177), sr=(126.2, 177), wa=(317, 63.4)),
    "crimson": dict(cx=97.5, cy=176.6, sl=(18.1, 161), sr=(176.9, 161), wa=(316, 66.7)),
    "wyvern": dict(cx=64.4, cy=169.1, sl=(17.0, 152), sr=(112.0, 152), wa=(317, 64.7)),
    # v3.216.0: 隼竜・燕竜・蜂竜も tools/gen_gem_restyle.py で元の輪郭のまま描き直したので、元の竜種の値
    "falcon": dict(cx=63.0, cy=179.6, sl=(32.8, 183), sr=(93.2, 183), wa=(316, 55.0)),
    "swallow": dict(cx=53.0, cy=179.7, sl=(12.7, 182), sr=(93.3, 182), wa=(317, 60.2)),
    "hornet": dict(cx=82.3, cy=173.0, sl=(22.4, 139), sr=(142.6, 139), wa=(316, 18.1)),
    # v3.244.0: 鮫竜・亀竜・雷雲竜は専用の絵（tools/gen_dragon_design.py）の値（tools/sprite_meta.py の実測）。蛙竜は元の値
    # v3.252.0（DT-650）: 鮫竜・亀竜（鎧竜）・雷雲竜（尻尾なし）の新しいデザインの値
    "shark": dict(cx=73.1, cy=163.5, sl=(30, 128), sr=(117, 128), wa=(319, 10.4)),
    "tortoise": dict(cx=90.0, cy=167.6, sl=(12, 100), sr=(169, 100), wa=(319, 90.9)),
    "thunder": dict(cx=75.8, cy=178.4, sl=(19, 162), sr=(133, 162), wa=(319, 64.8)),
    "frog": dict(cx=139.9, cy=185.3, sl=(71.0, 182), sr=(208.0, 182), wa=(317, 66.1)),
}


def report(element, body, wing, pad_b, pad_w, spec_of=None):
    """DRAGON_PART_SPRITES に貼る値。元の胴の重心・肩・翼の付け根を、余白ぶんずらして写す（胴の高さ 27・翼の幅 25 は絵の大きさに比例）"""
    s = SPARKLE_SPEC[spec_of or element]
    L, T = pad_b["left"], pad_b["top"]
    print(f"  {element}_jewel: bodyPivot {{ cx: {s['cx'] + L:.1f}, cy: {s['cy'] + T:.1f}, w: {body.width}, h: {body.height} }}"
          f" shoulder L({s['sl'][0] + L:.1f},{s['sl'][1] + T}) R({s['sr'][0] + L:.1f},{s['sr'][1] + T})"
          f" wingAnchor {{ x: {s['wa'][0] + pad_w['left']}, y: {s['wa'][1] + pad_w['top']:.1f} }}"
          f" bodyDrawH: {27 * body.height / 320:.2f} wingDrawW: {25 * wing.width / 320:.2f}")


TAIL_TIP = {   # v3.233.0: 尾の飾りを動く尻尾の先にも付けられる竜種（胴の余白, 尻尾の先の絵を作る関数）
    "ice": (ICE_PAD, ice_tailtip),   # v3.234.0
    "falcon": (FALCON_PAD_TIP, falcon_tailtip),
    "swallow": (SWALLOW_PAD_TIP, swallow_tailtip),
    "hornet": (HORNET_PAD_TIP, hornet_tailtip),
    "shark": (SHARK_PAD_TIP, shark_tailtip),        # v3.235.0
    "thunder": (THUNDER_PAD_TIP, thunder_tailtip),
    "tortoise": (TORTOISE_PAD_TIP, tortoise_tailtip),
}


def main():
    only = set(sys.argv[1:])     # 竜種を名指しすると、その竜種だけ作り直す（ほかの竜種の絵を書き換えない）
    for element, body_fn, wing_fn, pad_b, pad_w in (
        ("fire", fire_body, fire_wing, FIRE_PAD, FIRE_WING_PAD),
        ("ice", ice_body, ice_wing, ICE_PAD, ICE_WING_PAD),
        ("shadow", shadow_body, shadow_wing, SHADOW_PAD, SHADOW_WING_PAD),
        ("crimson", crimson_body, crimson_wing, CRIMSON_PAD, dict(left=0, top=0, right=0, bottom=0)),
        ("wyvern", wyvern_body, wyvern_wing, WYVERN_PAD, dict(left=0, top=0, right=0, bottom=0)),
        ("falcon", falcon_body, falcon_wing, FALCON_PAD_ROOT, dict(left=0, top=0, right=0, bottom=0)),
        ("swallow", swallow_body, swallow_wing, SWALLOW_PAD_ROOT, dict(left=0, top=0, right=0, bottom=0)),
        ("hornet", hornet_body, hornet_wing, HORNET_PAD_ROOT, dict(left=0, top=0, right=0, bottom=0)),
        ("shark", shark_body, shark_wing, SHARK_PAD_ROOT, SHARK_WING_PAD),   # v3.235.0
        ("thunder", thunder_body, thunder_wing, THUNDER_PAD_ROOT, dict(left=0, top=0, right=0, bottom=0)),
        ("tortoise", tortoise_body, tortoise_wing, TORTOISE_PAD_ROOT, dict(left=0, top=0, right=0, bottom=0)),
        ("frog", frog_body, frog_wing, dict(left=0, top=0, right=0, bottom=0), dict(left=0, top=0, right=0, bottom=0)),
    ):
        if only and element not in only:
            continue
        sb = Image.open(os.path.join(ASSETS, f"dragon_{element}_sparkle_body.png")).convert("RGBA")
        sw = Image.open(os.path.join(ASSETS, f"dragon_{element}_sparkle_wing.png")).convert("RGBA")
        jb, jw = body_fn(sb), wing_fn(sw)
        jb.save(os.path.join(ASSETS, f"dragon_{element}_jewel_body.png"), optimize=True)
        if jw is None:     # 翼を飾らない竜種は *_sparkle の翼の絵を DRAGON_PART_SPRITES からそのまま指す（同じ絵を2枚置かない）
            jw = sw
        else:
            jw.save(os.path.join(ASSETS, f"dragon_{element}_jewel_wing.png"), optimize=True)
        print(element, "body", sb.size, "->", jb.size, "wing", sw.size, "->", jw.size)
        report(element, jb, jw, pad_b, pad_w)
        if element == "frog":   # v3.235.0: 蛙竜は跳んでいるときの胴の絵も（尾の飾りは動く尻尾の先だけ）
            sa = Image.open(os.path.join(ASSETS, "dragon_frog_sparkle_body_air.png")).convert("RGBA")
            frog_body(sa, air=True).save(os.path.join(ASSETS, "dragon_frog_jewel_body_air.png"), optimize=True)
            tip, (ax, ay) = frog_tailtip()
            tip.save(os.path.join(ASSETS, "dragon_frog_tailtip.png"), optimize=True)
            print(f"  frog_tailtip: w: {tip.width}, h: {tip.height}, anchor: {{ x: {ax}, y: {ay} }}")
        # v3.233.0（DT-609 手直し）: 尾の飾りを動く尻尾の先に付ける形（胴の絵 *_jewelt と、尻尾の先の絵 *_tailtip）
        if element in TAIL_TIP:
            pad_t, tip_fn = TAIL_TIP[element]
            jt = body_fn(sb, tail="tip")
            jt.save(os.path.join(ASSETS, f"dragon_{element}_jewelt_body.png"), optimize=True)
            report(element + "t", jt, jw, pad_t, pad_w, spec_of=element)
            tip, (ax, ay) = tip_fn()
            tip.save(os.path.join(ASSETS, f"dragon_{element}_tailtip.png"), optimize=True)
            print(f"  {element}_tailtip: w: {tip.width}, h: {tip.height}, anchor: {{ x: {ax}, y: {ay} }}  （胴と同じ縮尺：27/320 論理px／画素）")


if __name__ == "__main__":
    main()
