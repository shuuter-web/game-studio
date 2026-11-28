"""Dragon Tide（DT-609）: 2回目の進化の飾りを、全身カットの宝石の絵（*_sparkle）に描き足して *_jewel を作る。

  python3 tools/gen_gem_ornaments.py [竜種...]   # 火竜・氷竜・影竜・緋竜・飛竜・隼竜・燕竜・蜂竜・鮫竜・雷雲竜・亀竜・蛙竜・UFO・彗星竜・爆竜・屍竜（名指しでその竜種だけ）の *_jewel_body.png / *_jewel_wing.png を書き出し、DRAGON_PART_SPRITES に貼る値を出す

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
# v3.255.0（DT-650 11/28 Shooter「サンゴのツノが翼にかかっちゃってるので、前後反転してかからないように」）:
# 横・後ろへ張っていた枝（幹 108°）を前後に反転し、横・前へ張る（幹 72°・枝の向きのずれと反りも裏返す）
SHARK_CORAL_TRUNK = (72, 136, 26)             # 幹の向き（0＝顔の向き・90＝真横）・長さ・太さ
SHARK_CORAL_BRANCHES = ((0.3, -50, 66, 17), (0.5, 42, 56, 15), (0.75, -44, 46, 13))
SHARK_CORAL_BEND = -0.35                      # 幹の反り（負＝前へ反る）。枝はこの 0.86 倍
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
    trunk, spine = curved_blade(rx, ry, length, width, math.radians(sd * ang), sd * SHARK_CORAL_BEND)
    shapes = [(trunk, spine)]
    pts = spine + [spine[-1]]
    for at, dang, blen, bw in SHARK_CORAL_BRANCHES:
        bx, by = pts[min(len(pts) - 1, int(at * len(pts)))]
        shapes.append(curved_blade(bx, by, blen, bw, math.radians(sd * (ang + dang)), sd * SHARK_CORAL_BEND * 0.86))
    for poly, sp in shapes:
        canvas.shape([poly], CORAL, axis=(0.4, 1.0), outline=4.0, ridge=sp)
    for poly, sp in shapes:   # 枝の先の粒（先の少し手前に置いて、細い先を丸くする）
        ex, ey = sp[-1]
        canvas.shape([ellipse_poly(ex, ey, 9, 9, 14)], CORAL, axis=(-0.4, 1.0), outline=2.0)
    canvas.shape([ellipse_poly(rx, ry, 12, 12, 16)], NACRE, axis=(-0.4, 1.0), outline=2.5)   # 根元の真珠


def shark_body(src, tail="root"):
    """鮫竜（サファイア）：えらの後ろから横・前へ大きく枝を張る赤珊瑚（v3.255.0 で前後反転）（根元に真珠）・背骨に乗って後ろへ反る真珠層の背びれ。
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


# ---------------------------------------------------------------- v3.258.0（案帳 DT-652〜655）: UFO・彗星竜・爆竜・屍竜
# 4竜種とも専用の絵（DRAGON_PARTS_ALIAS で借りていない）なので、その輪郭のまま宝石にして飾る。尾の飾りは動く尻尾の先（"tip"）。UFO は尻尾が無い
LAPIS = dict(light=(150, 176, 255), base=(34, 56, 176), dark=(12, 18, 86), line=(4, 6, 34))
TURQUOISE = dict(light=(214, 255, 246), base=(46, 196, 192), dark=(14, 116, 128), line=(4, 40, 48))
FIRE_OPAL = dict(light=(255, 234, 150), base=(252, 122, 30), dark=(186, 46, 10), line=(66, 14, 0))
URANIUM = dict(light=(236, 255, 196), base=(124, 236, 72), dark=(38, 146, 30), line=(8, 48, 10))
BLACK_GLASS = dict(light=(170, 176, 196), base=(34, 34, 44), dark=(6, 6, 12), line=(0, 0, 0))
GLINT = dict(light=(255, 255, 255), base=(255, 255, 255), dark=(230, 236, 255), line=(255, 255, 255))   # 玉の照り（縁なし）


def star4(cx, cy, r_out, r_in, rot_deg=0.0):
    """4つの角の星（流れ星・火花の形）"""
    pts = []
    for i in range(8):
        a = math.radians(rot_deg + i * 45)
        r = r_out if i % 2 == 0 else r_in
        pts.append((cx + math.sin(a) * r, cy - math.cos(a) * r))
    return pts


# UFO（ムーンストーン）：v3.258.0 は円盤の縁の下から回る向きへ反る火蛋白石の羽根4枚（風車）だった。
# v3.261.0（DT-652 手直し・11/28 Shooter「2進化のパーツは、刃ではなくて、析出した結晶がUFOの外周を覆って少し大きくなってる感じに」）:
# 円盤の縁の上に、火蛋白石の結晶の柱（先の尖った六角柱を上から見た形）がびっしり生えて外周を覆い、円盤がひと回り大きく見える形に。
# 長い結晶と短い結晶を決まった並びで交互に置く（乱数は使わない）。自転するので、どの向きにも同じように並ぶ
UFO_PAD = dict(left=40, top=40, right=40, bottom=40)   # 結晶が縁から外へはみ出す分
UFO_CX, UFO_CY, UFO_R = 159.5, 159.5, 156     # 円盤の真ん中と半径（dragon_ufo_body.png）
UFO_CLUSTERS = 16                             # 外周の結晶の房の数
UFO_CRYSTAL_ROOT = 0.84                       # 結晶の根元（半径の割合。縁の帯を覆うように内側から生やす）
# 房の中の結晶：（房の真ん中からの角度のずれ°, 傾き°, 縁から外へ出る長さ, 太さ）。房ごとに長さを UFO_CLUSTER_SCALE で変える
UFO_CLUSTER = ((-7.5, -24, 14, 24), (7.0, 20, 18, 26), (0.0, -3, 30, 32))
UFO_CLUSTER_SCALE = (1.0, 0.7, 0.9, 0.6)     # 房ごとの大きさの並び（4つごとに繰り返す。不揃いに見せる）
UFO_CLUSTER_ROT = (0, 4, -3, 2)               # 房ごとの向きのずれ°
def crystal(cx, cy, length, width, angle):
    """先の尖った六角柱の結晶を上から見た形。根元 (cx,cy) から angle の向きへ。返り値は（形, 片側の暗い面, 芯）"""
    dx, dy = math.sin(angle), -math.cos(angle)
    nx, ny = -dy, dx
    hw = width * 0.5
    shoulder = length * 0.68
    b_l, b_r = (cx + nx * hw * 0.9, cy + ny * hw * 0.9), (cx - nx * hw * 0.9, cy - ny * hw * 0.9)
    s_l = (cx + nx * hw + dx * shoulder, cy + ny * hw + dy * shoulder)
    s_r = (cx - nx * hw + dx * shoulder, cy - ny * hw + dy * shoulder)
    tip = (cx + dx * length, cy + dy * length)
    mid_b, mid_s = (cx, cy), (cx + dx * shoulder, cy + dy * shoulder)
    return [b_l, s_l, tip, s_r, b_r], [mid_b, mid_s, tip, s_r, b_r], [mid_b, mid_s, tip]


def ufo_body(src, tail="root"):
    p = UFO_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    front = Canvas(*sprite.size)
    cx, cy = p["left"] + UFO_CX, p["top"] + UFO_CY
    layers = [Canvas(*sprite.size) for _ in UFO_CLUSTER]   # 房の中の結晶ごとに層を分ける（真ん中の大きい結晶を手前に）
    base = UFO_R * (1 - UFO_CRYSTAL_ROOT)
    for k in range(UFO_CLUSTERS):
        sc = UFO_CLUSTER_SCALE[k % len(UFO_CLUSTER_SCALE)]
        rot = UFO_CLUSTER_ROT[k % len(UFO_CLUSTER_ROT)]
        for layer, (da, lean, out_len, width) in zip(layers, UFO_CLUSTER):
            a = math.radians(k * 360 / UFO_CLUSTERS + da + rot)
            rx, ry = cx + math.sin(a) * UFO_R * UFO_CRYSTAL_ROOT, cy - math.cos(a) * UFO_R * UFO_CRYSTAL_ROOT
            poly, dark, ridge = crystal(rx, ry, base + out_len * (0.55 + 0.45 * sc) + 6, width * (0.8 + 0.2 * sc), a + math.radians(lean))
            layer.shape([poly], FIRE_OPAL, axis=(math.sin(a), -math.cos(a)), outline=3.8, ridge=ridge, facet=dark)
    out = Image.new("RGBA", sprite.size, (0, 0, 0, 0))
    out.alpha_composite(sprite)
    for layer in layers:
        out.alpha_composite(layer.finish())
    return out


def ufo_wing(src):
    return None


# 彗星竜（サンストーン）：後頭部（角の後ろ）から後ろ・外へなびく瑠璃（ラピスラズリ）の尾2本と、その先の金の星。
# 尾の先に大きな瑠璃の4つの角の星（金の芯・後ろの角が長い流れ星）。夜空の青で、サンストーンの金と反対の色。翼は飾らない
COMET_PAD_ROOT = dict(left=34, top=0, right=34, bottom=90)
COMET_PAD_TIP = dict(left=34, top=0, right=34, bottom=0)
COMET_CX = 58.5
COMET_HEAD_BACK = (16, 74)            # 後頭部の左右の付け根（真ん中からのずれ, 高さ）
COMET_STREAMER = (70, 28, 162, 0.35)  # 長さ・太さ・向き（0＝顔の向き・180＝真後ろ）・反り（外へ）。外へ広げすぎると開いた翼の前の縁にかかる
COMET_TAIL_Y = 300


def comet_star(canvas, tx, ty):
    """彗星竜の尾の飾り：瑠璃の大きな4つの角の星（後ろの角が長い）と金の芯"""
    pts = star4(tx, ty + 42, 42, 13)
    pts[0] = (tx, ty - 2)
    pts[4] = (tx, ty + 42 + 52)
    canvas.shape([pts], LAPIS, axis=(0.5, 1.0), outline=3.5, ridge=[(tx, ty + 4), (tx, ty + 88)])
    canvas.shape([star4(tx, ty + 42, 16, 6, 45)], GOLD, axis=(0.4, 1.0), outline=2.2)


def comet_body(src, tail="root"):
    p = COMET_PAD_ROOT if tail == "root" else COMET_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx = p["left"] + COMET_CX
    dx, hy = COMET_HEAD_BACK
    length, width, ang, bend = COMET_STREAMER
    for sd in (-1, 1):
        rx = cx + sd * dx
        poly, spine = curved_blade(rx, hy, length, width, math.radians(sd * ang), sd * bend)
        back.shape([poly], LAPIS, axis=(0.3, 1.0), outline=4.0, ridge=spine)
        ex, ey = spine[-1]
        front.shape([star4(ex, ey, 17, 6)], GOLD, axis=(0.4, 1.0), outline=2.5)
        front.shape([ellipse_poly(rx, hy + 2, 9, 9, 16)], GOLD, axis=(0.4, 1.0), outline=2.5)
        front.shape([ellipse_poly(rx, hy + 2, 4, 4, 12)], LAPIS, outline=1.5)
    if tail == "root":
        comet_star(back, cx, COMET_TAIL_Y)
    return stack(back, sprite, front)


def comet_tailtip():
    c = Canvas(96, 104)
    comet_star(c, 48, 4)
    return c.finish(), (48, 4)


def comet_wing(src):
    return None


# 爆竜（インペリアル・トパーズ）：竜そのものを爆弾に見立てる。腰の左右から後ろ・外へ張るトルコ石の尾翼（水平尾翼。金の鋲）・
# 背に乗る黒いガラスの丸い爆弾（金の口金・導火線の火花）・尾の先のトルコ石の爆弾の尾翼。翼は飾らない（肩が前にあり翼が胴の前半を覆う）
# v3.260.0（DT-654 手直し・11/28 Shooter「飛行機コンセプト面白くて良い。左右翼パーツはもうちょっとだけ長く、尾翼のパーツは尻尾の先ではなく根元で。
#   爆弾のペイントは、丸い爆弾ではなくて飛行機に積まれる爆弾に」）: 腰の尾翼を長く（96→118）、尾翼の飾りはゲームでも胴の絵の尾の付け根（"root"）に、
#   背の爆弾は細長い航空爆弾（前が丸い胴・金の帯・後ろに十字の尾翼を上から見た形）に
BOMBER_PAD_ROOT = dict(left=64, top=0, right=64, bottom=80)   # v3.260.0: 尾翼を長くしたぶん左右の余白を足した（44→64）
BOMBER_PAD_TIP = dict(left=64, top=0, right=64, bottom=0)
BOMBER_CX = 89.0
BOMBER_FIN_ROOT = (46, 232)           # 水平尾翼の付け根（真ん中からのずれ, 高さ）
BOMBER_FIN = (118, 40, 122)           # 長さ・付け根の幅・向き（90＝真横・180＝真後ろ）
BOMBER_BOMB = (122, 252, 21)          # 背の航空爆弾の鼻先の高さ・尾の端の高さ・胴の半径（前が鼻・後ろが尾翼）
BOMBER_TAIL_Y = 306


def bomber_tailfins(canvas, tx, ty):
    """爆竜の尾の飾り：爆弾の尾翼（左右に後ろへ反る2枚＋真ん中の縦の尾翼を上から見た筋）と、根元の金の輪"""
    for sd in (-1, 1):
        canvas.shape([[(tx + sd * 5, ty + 4), (tx + sd * 32, ty + 44), (tx + sd * 30, ty + 62), (tx + sd * 6, ty + 46)]], TURQUOISE,
                     axis=(sd * 1.0, 0.4), outline=3.0)
    canvas.shape([[(tx - 6, ty + 2), (tx + 6, ty + 2), (tx + 5, ty + 64), (tx - 5, ty + 64)]], TURQUOISE, axis=(1.0, 0.2), outline=3.0,
                 ridge=[(tx, ty + 6), (tx, ty + 60)])
    canvas.shape([ellipse_poly(tx, ty + 3, 11, 7, 18)], GOLD, axis=(0.4, 1.0), outline=2.5)


def bomber_bomb(canvas, cx, nose_y, end_y, r):
    """背に乗る航空爆弾を上から見た形：前が丸い細長い黒いガラスの胴・金の帯2本・後ろへすぼまる尾の筒と十字の尾翼（左右2枚と真ん中の縦の1枚）"""
    body_end = end_y - r * 1.5            # 胴が尾の筒へすぼまり始める所
    pts = []
    for i in range(13):                   # 鼻先の半円
        a = math.pi * i / 12
        pts.append((cx - math.cos(a) * r, nose_y + r - math.sin(a) * r))
    pts += [(cx + r, body_end - r * 0.6), (cx + r * 0.42, end_y - r * 0.2), (cx - r * 0.42, end_y - r * 0.2), (cx - r, body_end - r * 0.6)]
    for sd in (-1, 1):                    # 尾翼（左右）：尾の筒から後ろ・外へ
        canvas.shape([[(cx + sd * r * 0.4, body_end - r * 0.2), (cx + sd * r * 1.55, end_y - r * 0.1), (cx + sd * r * 1.55, end_y + r * 0.35),
                       (cx + sd * r * 0.4, end_y + r * 0.1)]], TURQUOISE, axis=(sd * 1.0, 0.4), outline=3.0)
    canvas.shape([pts], BLACK_GLASS, axis=(-0.6, 1.0), outline=4.0, ridge=[(cx, nose_y + 6), (cx, end_y - 6)])
    canvas.shape([[(cx - 3.5, body_end - r * 0.3), (cx + 3.5, body_end - r * 0.3), (cx + 3, end_y + r * 0.45), (cx - 3, end_y + r * 0.45)]],
                 TURQUOISE, axis=(1.0, 0.2), outline=2.4)   # 真ん中の縦の尾翼（上から見て細い筋）
    for t in (0.22, 0.5):                 # 金の帯
        y = nose_y + (body_end - nose_y) * t
        canvas.shape([[(cx - r - 1, y - 4), (cx + r + 1, y - 4), (cx + r + 1, y + 4), (cx - r - 1, y + 4)]], GOLD, axis=(0.4, 1.0), outline=2.0)
    canvas.shape([ellipse_poly(cx - r * 0.42, nose_y + r * 0.9, r * 0.22, r * 0.5, 14)], GLINT, outline=0.1)   # 照り


def bomber_body(src, tail="root"):
    p = BOMBER_PAD_ROOT if tail == "root" else BOMBER_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx = p["left"] + BOMBER_CX
    dx, fy = BOMBER_FIN_ROOT
    length, base_w, ang = BOMBER_FIN
    for sd in (-1, 1):
        a = math.radians(sd * ang)
        ux, uy = math.sin(a), -math.cos(a)          # 尾翼の向き
        nx, ny = -uy, ux
        rx, ry = cx + sd * dx, fy
        tipx, tipy = rx + ux * length, ry + uy * length
        poly = [(rx + nx * base_w / 2, ry + ny * base_w / 2), (tipx + nx * 9, tipy + ny * 9), (tipx - nx * 9, tipy - ny * 9),
                (rx - nx * base_w / 2, ry - ny * base_w / 2)]
        back.shape([poly], TURQUOISE, axis=(0.3, 1.0), outline=4.0, ridge=[(rx, ry), (tipx, tipy)])
        for t in (0.55, 0.85):   # 金の鋲（爆竜の鋲留めの装甲に合わせる）
            sx, sy = rx + ux * length * t, ry + uy * length * t
            back.shape([ellipse_poly(sx, sy, 4.5, 4.5, 12)], GOLD, axis=(0.4, 1.0), outline=1.6)
    bomber_bomb(front, cx, *BOMBER_BOMB)
    if tail == "root":
        bomber_tailfins(back, cx, BOMBER_TAIL_Y)
    return stack(back, sprite, front)


def bomber_tailtip():
    c = Canvas(76, 72)
    bomber_tailfins(c, 38, 4)
    return c.finish(), (38, 4)


def bomber_wing(src):
    return None


# 屍竜（白いオパールの骨＋タンザナイトの膜）：後頭部から首の上を後ろへなびくウランガラス（緑に光るガラス）の鬼火の炎（舌3枚）・
# 尾の骨の左右に後ろへ反る黒いガラスの棘3対・尾の先に黒いガラスの大鎌の刃（刃の縁はウランガラス）。紫の灯と反対の緑、骨の白と黒で締める。
# v3.259.0（DT-655 手直し・11/28 Shooter「進化後に光る場所があんまり無いので翼も光らせられますか」「鬼火の炎いい感じなのでもう1、2箇所に」）:
#   翼の膜（タンザナイト）を内から光らせて縁に紫のにじみ、翼の手首の爪の骨と腰（骨盤の左右）にも小さな鬼火の炎、鬼火のまわりに緑のにじみ
BONE_PAD_ROOT = dict(left=40, top=0, right=40, bottom=110)
BONE_PAD_TIP = dict(left=40, top=0, right=40, bottom=0)
BONE_WING_PAD = dict(left=10, top=10, right=10, bottom=10)   # 翼のにじみの分
BONE_CX = 48.5
BONE_WISP_ROOT = 54                   # 鬼火の炎の付け根（後頭部）の高さ
BONE_WISP_TONGUES = ((-24, 58, 15, -0.6), (24, 58, 15, 0.6), (0, 84, 18, 0.45))   # 炎の舌（向きのずれ°, 長さ, 太さ, 揺れ）。左右へ広げると開いた翼にかかる
BONE_HIP_WISP = (29, 184, 0.5, 26)   # 腰の鬼火（真ん中からのずれ, 高さ, 大きさ, 外への向き°）
BONE_WING_WISP = (176, 12, 0.7, 28)   # 翼の手首の爪の骨の鬼火（x, y, 大きさ, 外への向き°。翼の絵は左の翼で、外＝左）
BONE_SPINES = (228, 252, 276)         # 尾の骨の棘の高さ
BONE_SPINE = (40, 16, 128)            # 棘の長さ・太さ・向き
BONE_TAIL_Y = 312
URANIUM_CORE = dict(URANIUM, base=(226, 255, 200), dark=(170, 240, 120))
WISP_GLOW = (150, 255, 110)           # 鬼火のまわりのにじみの色
MEMBRANE_GLOW = (160, 120, 255)       # 翼の膜の光とにじみの色


def bone_wisp(canvas, x, y, scale=1.0, turn=0.0, spread=0.25):
    """ウランガラスの鬼火の炎（舌3枚と芯の白い炎）。根元 (x,y) から後ろ（turn° だけ回す）へなびく"""
    for dang, length, width, lean in BONE_WISP_TONGUES:
        rx = x + dang * spread * scale   # 舌の付け根を少しずつ離す（くっつくと1枚の板に見えた）
        canvas.shape([flame(rx, y, length * scale, width * scale, math.radians(180 + dang + turn), lean=lean)], URANIUM,
                     axis=(0.0, 1.0), outline=3.0 * max(0.6, scale))
    for dang, length, width, lean in BONE_WISP_TONGUES:   # 芯の白い炎（舌の内側）
        canvas.shape([flame(x + dang * spread * scale, y + 3 * scale, length * 0.55 * scale, width * 0.45 * scale,
                            math.radians(180 + dang + turn), lean=lean)], URANIUM_CORE, axis=(0.0, 1.0), outline=0.1)


def glow_under(img, mask, color, radius, strength):
    """mask（真偽の配列）のまわりに color のにじみを敷く（絵の下に置く）"""
    m = Image.fromarray((mask * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(radius))
    a = np.clip(np.array(m, np.float32) / 255 * 2.2, 0, 1) * strength   # 縁の近くまでしっかり、外へ行くほど薄く
    halo = np.zeros((img.height, img.width, 4), np.uint8)
    halo[..., :3] = color
    halo[..., 3] = (a * 255).astype(np.uint8)
    out = Image.fromarray(halo, "RGBA")
    out.alpha_composite(img)
    return out


def bone_scythe(canvas, tx, ty):
    """屍竜の尾の飾り：黒いガラスの大鎌の刃（片側へ大きく反る）。刃の縁にウランガラスの筋、根元に骨の輪"""
    poly, spine = curved_blade(tx, ty + 6, 126, 46, math.radians(132), -1.5)
    canvas.shape([poly], BLACK_GLASS, axis=(0.6, 1.0), outline=3.5)
    edge, _ = curved_blade(tx + 3, ty + 11, 118, 15, math.radians(130), -1.5)
    canvas.shape([edge], URANIUM, axis=(0.6, 1.0), outline=1.6, ridge=spine)
    canvas.shape([ellipse_poly(tx, ty + 3, 10, 8, 16)], IVORY, axis=(0.4, 1.0), outline=2.5)


def bone_body(src, tail="root"):
    p = BONE_PAD_ROOT if tail == "root" else BONE_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx = p["left"] + BONE_CX
    bone_wisp(front, cx, BONE_WISP_ROOT)
    hx, hy, hs, hturn = BONE_HIP_WISP
    for sd in (-1, 1):
        bone_wisp(front, cx + sd * hx, hy, hs, sd * -hturn)
    length, width, ang = BONE_SPINE
    for y in BONE_SPINES:
        for sd in (-1, 1):
            poly, spine = curved_blade(cx + sd * 6, y, length, width, math.radians(sd * ang), sd * 0.35)
            back.shape([poly], BLACK_GLASS, axis=(0.4, 1.0), outline=3.0, ridge=spine)
    if tail == "root":
        bone_scythe(back, cx, BONE_TAIL_Y)
    fr = front.finish()   # 鬼火のまわりに緑のにじみを敷いてから、棘・骨・鬼火の順に重ねる
    out = glow_under(Image.new("RGBA", sprite.size, (0, 0, 0, 0)), np.array(fr)[:, :, 3] > THRESH, WISP_GLOW, 4, 0.55)
    out.alpha_composite(back.finish())
    out.alpha_composite(sprite)
    out.alpha_composite(fr)
    return out


def bone_tailtip():
    c = Canvas(260, 160)
    bone_scythe(c, 130, 4)
    img = c.finish()
    x0, y0, x1, y1 = img.getbbox()   # 刃がどちらへ反っても切れないよう大きく描いてから、余白を詰める（根元の位置もずらす）
    x0, y0 = min(x0, 130 - 12), 0
    return img.crop((x0, y0, x1 + 2, y1 + 2)), (130 - x0, 4)


def bone_wing(src):
    """翼の膜（タンザナイト）を内から光らせる：膜の奥ほど明るい紫に寄せ、膜のまわりに紫のにじみ。手首の爪の骨に鬼火"""
    p = BONE_WING_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    a = np.array(sprite).astype(np.float32)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    membrane = (al > THRESH) & (b > r + 30) & (b > g + 30)
    inner = np.array(Image.fromarray((membrane * 255).astype(np.uint8), "L").filter(ImageFilter.GaussianBlur(5)), np.float32) / 255
    k = (np.clip(inner, 0, 1) * 0.45 + 0.1)[..., None] * membrane[..., None]
    glow = np.array(MEMBRANE_GLOW, np.float32)
    rgb = a[..., :3]
    lit = 255 - (255 - rgb) * (255 - glow) / 255   # スクリーンで重ねる（面の明暗は残す）
    a[..., :3] = rgb * (1 - k) + lit * k
    sprite = Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")
    sprite = glow_under(sprite, membrane, MEMBRANE_GLOW, 4, 0.75)
    front = Canvas(*sprite.size)
    wx, wy, ws, wturn = BONE_WING_WISP
    bone_wisp(front, wx + p["left"], wy + p["top"], ws, wturn)
    fr = front.finish()
    out = glow_under(sprite, np.array(fr)[:, :, 3] > THRESH, WISP_GLOW, 4, 0.55)
    out.alpha_composite(fr)
    return out


# ---------------------------------------------------------------- DT-656・661・662・664（11/28）: 塊竜・鉄鎖竜・鯨竜・光線竜
# 4竜種とも本デザイン（tools/gen_dragon_design.py）をゲームに入れてから、その輪郭のまま宝石にして飾る
MALACHITE = dict(light=(190, 255, 214), base=(28, 158, 100), dark=(6, 82, 52), line=(2, 34, 20))
RAY_CRYSTAL = dict(light=(246, 255, 255), base=(122, 247, 255), dark=(26, 150, 196), line=(6, 40, 62))
RAY_GLOW = (122, 247, 255)

# 塊竜（スペサタイト・ガーネット）：丸まった甲羅の縁から外へ突き出す孔雀石（マラカイト）の棘を左右3本ずつ（転がる玉を棘の玉に見せる）と、
# 背の帯の上に乗る孔雀石の鋲4つ。尻尾は胴の絵の中に巻いてある（noTail）ので尾の飾りは無し
BALL_PAD = dict(left=50, top=0, right=50, bottom=20)
BALL_C = (118, 190)                   # 丸い甲羅の真ん中（dragon_ball_body.png）
BALL_SPIKE_ROOT = 92                  # 棘の根元（真ん中からの距離。甲羅の縁の内側から生やす）
BALL_SPIKES = ((30, 48, 30), (112, 66, 38), (148, 54, 32))   # （向き°（上＝0・右回り）, 長さ, 太さ）。左右対称。肩（翼の付け根）の横は翼に隠れるので避ける
BALL_STUDS = (110, 152, 196, 238)     # 背の鋲の高さ


def ball_body(src, tail="root"):
    p = BALL_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx, cy = p["left"] + BALL_C[0], p["top"] + BALL_C[1]
    for ang, length, width in BALL_SPIKES:
        for sd in (-1, 1):
            a = math.radians(sd * ang)
            rx, ry = cx + math.sin(a) * BALL_SPIKE_ROOT, cy - math.cos(a) * BALL_SPIKE_ROOT
            poly, dark, ridge = crystal(rx, ry, length + 18, width, a)
            back.shape([poly], MALACHITE, axis=(math.sin(a), -math.cos(a)), outline=4.0, ridge=ridge, facet=dark)
    for y in BALL_STUDS:
        front.shape([ellipse_poly(cx, y, 15, 11, 20)], MALACHITE, axis=(-0.3, 1.0), outline=3.5)
        front.shape([ellipse_poly(cx - 5, y - 4, 5, 3.5, 12)], GLINT, outline=0.1)
    return stack(back, sprite, front)


def ball_wing(src):
    return None


# 鉄鎖竜（スチールグレーのスピネル）：兜の頂から首の上を後ろへなびく緋色の羽根飾り（騎士の兜の飾り毛）・
# 両肩の棘付きの肩当てから外へ扇に張る金の棘3本ずつ・尾の先に金の棘鉄球（モーニングスター）。斜めに掛けた鎖は胴の絵のまま（消さない）
FLAIL_PAD_ROOT = dict(left=40, top=0, right=40, bottom=64)
FLAIL_PAD_TIP = dict(left=40, top=0, right=40, bottom=0)
FLAIL_CX = 96.5
FLAIL_PLUME = ((0, 100, 30, 0.25), (-16, 82, 24, -0.5), (16, 82, 24, 0.5))   # 羽根飾りの房（向きのずれ°, 長さ, 太さ, 揺れ）
FLAIL_PLUME_ROOT = 26                 # 兜の頂の高さ
FLAIL_PAULDRON = (48, 140)            # 左の肩当ての真ん中（右は左右対称）
FLAIL_PAULDRON_SPIKES = ((-60, 46, 16), (-92, 56, 18), (-122, 44, 16))   # 肩当ての棘（向き°, 長さ, 太さ。左の肩当て）
FLAIL_TAIL_Y = 300


def morning_star(canvas, x, y, r=22):
    """金の棘鉄球：根元の輪から下へ、棘8本の玉"""
    canvas.shape([ellipse_poly(x, y + 6, 8, 8, 16)], GOLD, axis=(0.4, 1.0), outline=3.0)
    bx, by = x, y + 12 + r
    for k in range(8):
        a = math.radians(22.5 + k * 45)
        canvas.shape([spike(bx + math.sin(a) * r * 0.7, by - math.cos(a) * r * 0.7, r * 0.75, 11, a)], GOLD,
                     axis=(math.sin(a), -math.cos(a)), outline=3.0)
    canvas.shape([ellipse_poly(bx, by, r, r, 28)], GOLD, axis=(-0.4, 1.0), outline=3.5)
    canvas.shape([ellipse_poly(bx - r * 0.35, by - r * 0.35, r * 0.28, r * 0.2, 12)], GLINT, outline=0.1)


def flail_body(src, tail="root"):
    p = FLAIL_PAD_ROOT if tail == "root" else FLAIL_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx = p["left"] + FLAIL_CX
    for dang, length, width, lean in FLAIL_PLUME:
        front.shape([flame(cx + dang * 0.3, FLAIL_PLUME_ROOT, length, width, math.radians(180 + dang), lean=lean)], SCARLET,
                    axis=(0.0, 1.0), outline=3.5)
    px, py = FLAIL_PAULDRON
    for sd in (-1, 1):
        x = cx + sd * (FLAIL_CX - px)
        for ang, length, width in FLAIL_PAULDRON_SPIKES:
            a = math.radians(ang * -sd)
            back.shape([spike(x + math.sin(a) * 14, py - math.cos(a) * 14, length + 14, width, a, base_w=width * 1.4)], GOLD,
                       axis=(math.sin(a), -math.cos(a)), outline=3.5)
    if tail == "root":
        morning_star(back, cx, FLAIL_TAIL_Y)
    return stack(back, sprite, front)


def flail_tailtip():
    c = Canvas(64, 84)
    morning_star(c, 32, 4)
    return c.finish(), (32, 4)


def flail_wing(src):
    return None


# 鯨竜（ロンドン・ブルー・トパーズ）：頭の上の潮吹き穴から後ろ・外へ噴き上がる真珠層の潮（5本の筋の先に真珠の粒）・
# 尾の先に真珠層の鯨の尾びれ（左右2枚）
WHALE_PAD_ROOT = dict(left=40, top=0, right=40, bottom=70)
WHALE_PAD_TIP = dict(left=40, top=0, right=40, bottom=0)
WHALE_CX = 106.5
WHALE_BLOWHOLE_Y = 66
WHALE_SPOUT = ((180, 84, 18), (-150, 76, 17), (150, 76, 17), (-118, 64, 16), (118, 64, 16), (-88, 50, 14), (88, 50, 14))   # 潮の筋（向き°, 長さ, 太さ）。潮吹き穴のまわりに後ろ半分へ散るしぶき（v1 の長い筋は帯に見えた）
WHALE_TAIL_Y = 306


def whale_fluke(canvas, x, y, scale=1.0):
    """真珠層の鯨の尾びれ：根元から左右へ広がる2枚（先が後ろへ反る）"""
    for sd in (-1, 1):
        poly, spine = curved_blade(x, y + 6 * scale, 62 * scale, 34 * scale, math.radians(sd * 118), sd * 0.7)
        canvas.shape([poly], NACRE, axis=(sd * 0.5, 1.0), outline=3.5, ridge=spine)
    canvas.shape([ellipse_poly(x, y + 6 * scale, 11 * scale, 9 * scale, 16)], NACRE, axis=(0.3, 1.0), outline=3.0)


def whale_body(src, tail="root"):
    p = WHALE_PAD_ROOT if tail == "root" else WHALE_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    front = Canvas(*sprite.size)
    cx, by = p["left"] + WHALE_CX, WHALE_BLOWHOLE_Y + p["top"]
    for ang, length, width in WHALE_SPOUT:
        a = math.radians(ang)
        poly, spine = curved_blade(cx + math.sin(a) * 8, by - math.cos(a) * 8, length, width, a, (0.35 if ang > 0 else -0.35) if abs(ang) != 180 else 0.0)
        front.shape([poly], NACRE, axis=(math.sin(a), -math.cos(a)), outline=3.2, ridge=spine)
        ex, ey = spine[-1] if spine else (cx, by)
        tx, ty = ex + (spine[-1][0] - spine[-2][0]) * 3, ey + (spine[-1][1] - spine[-2][1]) * 3
        front.shape([ellipse_poly(tx, ty, 11, 11, 16)], PEARL, axis=(-0.4, 1.0), outline=2.8)
        front.shape([ellipse_poly(tx - 3, ty - 3, 3, 2.5, 10)], GLINT, outline=0.1)
    front.shape([ellipse_poly(cx, by, 13, 11, 20)], PEARL, axis=(-0.4, 1.0), outline=3.0)
    if tail == "root":
        whale_fluke(back, cx, WHALE_TAIL_Y)
    return stack(back, sprite, front)


def whale_tailtip():
    c = Canvas(160, 80)
    whale_fluke(c, 80, 4)
    img = c.finish()
    x0, y0, x1, y1 = img.getbbox()
    return img.crop((x0, 0, x1 + 2, y1 + 2)), (80 - x0, 4)


def whale_wing(src):
    return None


# 光線竜（11/28 Shooter「全身を宝石化するのではなく、水晶の部分が増えて光る方向で。メカっぽさは残す」）：
# 1回目の進化（*_sparkle）は紺の装甲のまま水晶の所を増やした絵。2回目はさらに、後頭部・両肩・腰から外へ突き出す水晶の柱と、
# 翼の前の縁から突き出す水晶の列、尾の先の水晶の柱の房。どれも水色に光り、まわりに水色のにじみ
RAY_PAD_ROOT = dict(left=44, top=0, right=44, bottom=60)
RAY_PAD_TIP = dict(left=44, top=0, right=44, bottom=0)
RAY_WING_PAD = dict(left=0, top=30, right=0, bottom=0)
RAY_CX = 65
RAY_CLUSTERS = (   # （左の付け根 x, y, [(向き°, 長さ, 太さ), ...]）。右は左右対称
    (46, 92, ((-150, 46, 13), (-168, 34, 11))),                    # 後頭部から後ろ・外へ
    (22, 150, ((-62, 40, 14), (-90, 52, 16), (-116, 38, 13))),     # 肩
    (26, 226, ((-104, 40, 13), (-132, 34, 12))),                   # 腰
)
RAY_TAIL_Y = 306
RAY_WING_SHARDS = (60, 110, 160, 210, 260)   # 翼の前の縁の水晶の x（翼の絵の画素。根元は右の端）


def ray_crystal_tuft(canvas, x, y, scale=1.0):
    """尾の先の水晶の柱の房（下へ3本）"""
    for ang, length, width in ((180, 44, 15), (154, 32, 12), (206, 32, 12)):
        a = math.radians(ang)
        poly, dark, ridge = crystal(x, y + 4 * scale, length * scale, width * scale, a)
        canvas.shape([poly], RAY_CRYSTAL, axis=(math.sin(a), -math.cos(a)), outline=3.0, ridge=ridge, facet=dark)


def ray_body(src, tail="root"):
    p = RAY_PAD_ROOT if tail == "root" else RAY_PAD_TIP
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    back = Canvas(*sprite.size)
    cx = p["left"] + RAY_CX
    for lx, ly, shards in RAY_CLUSTERS:
        for sd in (-1, 1):
            x = cx + sd * (RAY_CX - lx)
            for ang, length, width in shards:
                a = math.radians(ang * -sd)
                poly, dark, ridge = crystal(x, ly, length + 10, width, a)
                back.shape([poly], RAY_CRYSTAL, axis=(math.sin(a), -math.cos(a)), outline=3.0, ridge=ridge, facet=dark)
    if tail == "root":
        ray_crystal_tuft(back, cx, RAY_TAIL_Y)
    bk = back.finish()
    out = glow_under(Image.new("RGBA", sprite.size, (0, 0, 0, 0)), np.array(bk)[:, :, 3] > THRESH, RAY_GLOW, 5, 0.6)
    out.alpha_composite(bk)
    out.alpha_composite(sprite)
    return out


def ray_glow_mask(img):
    """光線竜のきらめきを水晶の所だけに出すための形（index.html の GEM_SPARKLE_MASK の glowSrc）。
    水色に光る所（水晶・光の筋）を拾って少し太らせ、縁をぼかした白の絵。紺の装甲（機械）と水晶のまわりのにじみ（半透明）は光らせない"""
    a = np.array(img).astype(np.float32)
    r, g, b, al = a[..., 0], a[..., 1], a[..., 2], a[..., 3]
    cyan = (al > 200) & (g > 140) & (b > 150) & ((g + b) / 2 - r > 55)
    m = Image.fromarray((cyan * 255).astype(np.uint8), "L").filter(ImageFilter.MaxFilter(5)).filter(ImageFilter.GaussianBlur(1.5))
    out = Image.new("RGBA", img.size, (255, 255, 255, 0))
    out.putalpha(m)
    return out


def ray_tailtip():
    c = Canvas(80, 64)
    ray_crystal_tuft(c, 40, 0)
    img = c.finish()
    out = glow_under(Image.new("RGBA", img.size, (0, 0, 0, 0)), np.array(img)[:, :, 3] > THRESH, RAY_GLOW, 4, 0.6)
    out.alpha_composite(img)
    return out, (40, 4)


def ray_wing(src):
    p = RAY_WING_PAD
    sprite = padded(src, p["left"], p["top"], p["right"], p["bottom"])
    a = body_alpha(sprite)
    back = Canvas(*sprite.size)
    for i, x in enumerate(RAY_WING_SHARDS):
        cols = np.nonzero(a[:, x])[0]
        if not len(cols):
            continue
        y = float(cols.min()) + 8
        ang = math.radians(-12 if i % 2 else 8)
        poly, dark, ridge = crystal(x, y, 34 + (i % 2) * 8, 13, ang)
        back.shape([poly], RAY_CRYSTAL, axis=(math.sin(ang), -math.cos(ang)), outline=3.0, ridge=ridge, facet=dark)
    bk = back.finish()
    out = glow_under(Image.new("RGBA", sprite.size, (0, 0, 0, 0)), np.array(bk)[:, :, 3] > THRESH, RAY_GLOW, 4, 0.55)
    out.alpha_composite(bk)
    out.alpha_composite(sprite)
    return out



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
    # v3.258.0: UFO・彗星竜・爆竜・屍竜も元の輪郭のまま描き直したので、元の竜種の値（UFO は翼が無い）
    "ufo": dict(cx=159.5, cy=159.4, sl=(0, 0), sr=(0, 0), wa=(0, 0)),
    "comet": dict(cx=58.3, cy=178.1, sl=(13.6, 180), sr=(103.4, 180), wa=(316, 69.3)),
    "bomber": dict(cx=89.0, cy=171.9, sl=(16.8, 96), sr=(161.2, 96), wa=(317, 49.6)),
    "bone": dict(cx=48.6, cy=137.7, sl=(8.6, 103), sr=(88.4, 103), wa=(319, 32.0)),
    # DT-656・661・662・664: 本デザインの値（design-preview.html の寸法。whale の肩は手で測った値）
    "ball": dict(cx=120.7, cy=180.1, sl=(18.5, 142), sr=(212.5, 142), wa=(319, 83.2)),
    "flail": dict(cx=96.2, cy=176.2, sl=(15.4, 162), sr=(176.6, 162), wa=(319, 69.1)),
    "whale": dict(cx=106.1, cy=152.0, sl=(40, 125), sr=(172, 125), wa=(319, 38.5)),
    "ray": dict(cx=64.5, cy=171.5, sl=(14.5, 159), sr=(114.5, 159), wa=(319, 63.7)),
}


def report(element, body, wing, pad_b, pad_w, spec_of=None):
    """DRAGON_PART_SPRITES に貼る値。元の胴の重心・肩・翼の付け根を、余白ぶんずらして写す（胴の高さ 27・翼の幅 25 は絵の大きさに比例）"""
    s = SPARKLE_SPEC[spec_of or element]
    base_h = 15 if (spec_of or element) == "ufo" else 27   # UFO の円盤は高さ 15 で描く（DRAGON_PART_SPRITES.ufo）
    L, T = pad_b["left"], pad_b["top"]
    print(f"  {element}_jewel: bodyPivot {{ cx: {s['cx'] + L:.1f}, cy: {s['cy'] + T:.1f}, w: {body.width}, h: {body.height} }}"
          f" shoulder L({s['sl'][0] + L:.1f},{s['sl'][1] + T}) R({s['sr'][0] + L:.1f},{s['sr'][1] + T})"
          f" wingAnchor {{ x: {s['wa'][0] + pad_w['left']}, y: {s['wa'][1] + pad_w['top']:.1f} }}"
          f" bodyDrawH: {base_h * body.height / 320:.2f} wingDrawW: {25 * wing.width / 320 if wing is not None else 0:.2f}")


TAIL_TIP = {   # v3.233.0: 尾の飾りを動く尻尾の先にも付けられる竜種（胴の余白, 尻尾の先の絵を作る関数）
    "ice": (ICE_PAD, ice_tailtip),   # v3.234.0
    "falcon": (FALCON_PAD_TIP, falcon_tailtip),
    "swallow": (SWALLOW_PAD_TIP, swallow_tailtip),
    "hornet": (HORNET_PAD_TIP, hornet_tailtip),
    "shark": (SHARK_PAD_TIP, shark_tailtip),        # v3.235.0
    "thunder": (THUNDER_PAD_TIP, thunder_tailtip),
    "tortoise": (TORTOISE_PAD_TIP, tortoise_tailtip),
    "comet": (COMET_PAD_TIP, comet_tailtip),        # v3.258.0
    "bomber": (BOMBER_PAD_TIP, bomber_tailtip),
    "bone": (BONE_PAD_TIP, bone_tailtip),
    "flail": (FLAIL_PAD_TIP, flail_tailtip),        # DT-661
    "whale": (WHALE_PAD_TIP, whale_tailtip),        # DT-662
    "ray": (RAY_PAD_TIP, ray_tailtip),              # DT-664
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
        ("ufo", ufo_body, ufo_wing, UFO_PAD, dict(left=0, top=0, right=0, bottom=0)),   # v3.258.0（DT-652〜655）
        ("comet", comet_body, comet_wing, COMET_PAD_ROOT, dict(left=0, top=0, right=0, bottom=0)),
        ("bomber", bomber_body, bomber_wing, BOMBER_PAD_ROOT, dict(left=0, top=0, right=0, bottom=0)),
        ("bone", bone_body, bone_wing, BONE_PAD_ROOT, BONE_WING_PAD),
        ("ball", ball_body, ball_wing, BALL_PAD, dict(left=0, top=0, right=0, bottom=0)),   # DT-656・661・662・664
        ("flail", flail_body, flail_wing, FLAIL_PAD_ROOT, dict(left=0, top=0, right=0, bottom=0)),
        ("whale", whale_body, whale_wing, WHALE_PAD_ROOT, dict(left=0, top=0, right=0, bottom=0)),
        ("ray", ray_body, ray_wing, RAY_PAD_ROOT, RAY_WING_PAD),
    ):
        if only and element not in only:
            continue
        sb = Image.open(os.path.join(ASSETS, f"dragon_{element}_sparkle_body.png")).convert("RGBA")
        wing_path = os.path.join(ASSETS, f"dragon_{element}_sparkle_wing.png")
        sw = Image.open(wing_path).convert("RGBA") if os.path.exists(wing_path) else None   # v3.258.0: UFO は翼が無い
        jb, jw = body_fn(sb), (wing_fn(sw) if sw is not None else None)
        jb.save(os.path.join(ASSETS, f"dragon_{element}_jewel_body.png"), optimize=True)
        if jw is None:     # 翼を飾らない竜種は *_sparkle の翼の絵を DRAGON_PART_SPRITES からそのまま指す（同じ絵を2枚置かない）
            jw = sw
        else:
            jw.save(os.path.join(ASSETS, f"dragon_{element}_jewel_wing.png"), optimize=True)
        print(element, "body", sb.size, "->", jb.size, "wing", sw and sw.size, "->", jw and jw.size)
        report(element, jb, jw, pad_b, pad_w)
        if element == "frog":   # v3.235.0: 蛙竜は跳んでいるときの胴の絵も（尾の飾りは動く尻尾の先だけ）
            sa = Image.open(os.path.join(ASSETS, "dragon_frog_sparkle_body_air.png")).convert("RGBA")
            frog_body(sa, air=True).save(os.path.join(ASSETS, "dragon_frog_jewel_body_air.png"), optimize=True)
            tip, (ax, ay) = frog_tailtip()
            tip.save(os.path.join(ASSETS, "dragon_frog_tailtip.png"), optimize=True)
            print(f"  frog_tailtip: w: {tip.width}, h: {tip.height}, anchor: {{ x: {ax}, y: {ay} }}")
        if element == "ray":   # DT-664: きらめきは水晶の所だけ（1回目・2回目の進化の胴）
            ray_glow_mask(sb).save(os.path.join(ASSETS, "dragon_ray_sparkle_glowmask.png"), optimize=True)
            ray_glow_mask(jb).save(os.path.join(ASSETS, "dragon_ray_jewel_glowmask.png"), optimize=True)
        # v3.233.0（DT-609 手直し）: 尾の飾りを動く尻尾の先に付ける形（胴の絵 *_jewelt と、尻尾の先の絵 *_tailtip）
        if element in TAIL_TIP:
            pad_t, tip_fn = TAIL_TIP[element]
            jt = body_fn(sb, tail="tip")
            jt.save(os.path.join(ASSETS, f"dragon_{element}_jewelt_body.png"), optimize=True)
            report(element + "t", jt, jw, pad_t, pad_w, spec_of=element)
            if element == "ray":
                ray_glow_mask(jt).save(os.path.join(ASSETS, "dragon_ray_jewelt_glowmask.png"), optimize=True)
            tip, (ax, ay) = tip_fn()
            tip.save(os.path.join(ASSETS, f"dragon_{element}_tailtip.png"), optimize=True)
            print(f"  {element}_tailtip: w: {tip.width}, h: {tip.height}, anchor: {{ x: {ax}, y: {ay} }}  （胴と同じ縮尺：27/320 論理px／画素）")


if __name__ == "__main__":
    main()
