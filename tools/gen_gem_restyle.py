"""Dragon Tide（DT-609）: いまの竜の絵を下絵に渡し、形を保ったまま材質だけ「原石」「全身カットの宝石」に描き直す。

  python3 tools/gen_gem_restyle.py <竜種> <rough|sparkle> <body|wing> ["<材質の描写>"]

  例: python3 tools/gen_gem_restyle.py falcon sparkle body
      → prototypes/dragon-tide/assets/dragon_falcon_sparkle_body.png

輪郭はゲームの当たり・翼の付け根の位置に効くので、生成した絵は
「緑抜き → 下絵の外接矩形に合わせて伸縮 → 下絵のアルファで切る」で、下絵とまったく同じ輪郭にする
（だから DRAGON_PART_SPRITES の寸法は元の竜種の値のまま使える）。
v3.205.0 の影竜・緋竜・飛竜は手元で同じ手順で作った。v3.208.0 で隼竜・燕竜・蜂竜を作るときにスクリプトにした。
生成は tools/gen_sprite_cloud.py と同じ口（generativelanguage.googleapis.com。鍵はプロキシが差し込む）。
"""
import base64
import io
import json
import os
import sys
import urllib.request

import numpy as np
from PIL import Image

HERE = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.normpath(os.path.join(HERE, "..", "prototypes", "dragon-tide", "assets"))
MODEL = os.environ.get("SPRITE_MODEL", "gemini-3.1-flash-image")
GREEN = (0, 255, 0)
PAD_RATIO = 0.18              # 下絵のまわりに足す緑の余白（生成が端まで描いて切れないように）

# 竜種ごとの宝石（2つの段階で同じ石。原石＝磨く前、sparkle＝全身カット）
GEMS = {
    "falcon": "clear rock crystal quartz with a faint icy blue tint (colorless transparent gemstone)",
    "swallow": "paraiba tourmaline, vivid neon teal blue-green gemstone",
    "hornet": "golden yellow citrine gemstone, with the dark stripes made of polished black onyx",
}

STAGE_PROMPTS = {
    "rough": ("Redraw this exact creature as if it were carved from a ROUGH, UNCUT {gem} ORE: raw crystal chunks and natural crystal "
              "clusters, matte, no polished facets, no sparkle stars. Keep the species colour strong and saturated (not faded, not brown, "
              "not grey rock)."),
    "sparkle": ("Redraw this exact creature as if its WHOLE BODY were a brilliant FACET-CUT {gem}: the surface is divided into many "
                "triangular and kite-shaped polished facets with thin white edge highlights, deep saturated colour inside, bright "
                "reflections and a few small white sparkle stars."),
}

COMMON = ("Keep EXACTLY the same silhouette, pose, outline, proportions, size and position as the input image: same head, horns, "
          "limbs, tail, wing bones and membrane edges, nothing added or removed. Top-down view, flat cel-shaded game sprite with a "
          "thick dark ink outline. Solid flat pure green background (#00FF00), no shadow, no text.")


def generate(prompt, image):
    buf = io.BytesIO()
    image.save(buf, "PNG")
    body = json.dumps({
        "contents": [{"parts": [
            {"inlineData": {"mimeType": "image/png", "data": base64.b64encode(buf.getvalue()).decode()}},
            {"text": prompt},
        ]}],
        "generationConfig": {"responseModalities": ["IMAGE"]},
    }).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=body, headers={"Content-Type": "application/json", "x-goog-api-key": "dummy"})
    with urllib.request.urlopen(req, timeout=240) as res:
        data = json.load(res)
    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return Image.open(io.BytesIO(base64.b64decode(part["inlineData"]["data"]))).convert("RGBA")
    raise SystemExit("画像が返ってこなかった: " + json.dumps(data)[:400])


def key_green(img):
    """gen_sprite_cloud.py と同じ緑抜き（縁の緑かぶりも消す）"""
    a = np.array(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    excess = g - np.maximum(r, b)
    alpha = np.clip(1 - (excess - 30) / 70, 0, 1)
    a[..., 1] = np.where(excess > 0, np.maximum(r, b) + excess * 0.15, g)
    a[..., 3] = alpha * 255
    return Image.fromarray(a.astype(np.uint8), "RGBA")


def bbox(alpha, thresh=40):
    return Image.fromarray((alpha > thresh).astype(np.uint8) * 255).getbbox()


def main():
    species, stage, part = sys.argv[1:4]
    gem = sys.argv[4] if len(sys.argv) > 4 else GEMS[species]
    src = Image.open(os.path.join(ASSETS, f"dragon_{species}_{part}.png")).convert("RGBA")
    src_a = np.array(src)[..., 3]
    # 生成に渡す下絵：緑の上に置いて、余白を足して大きめに（小さい絵だと描き込みが粗くなる）
    pad = int(max(src.size) * PAD_RATIO)
    scale = 1024 / (max(src.size) + pad * 2)
    canvas = Image.new("RGBA", (src.width + pad * 2, src.height + pad * 2), GREEN + (255,))
    canvas.alpha_composite(src, (pad, pad))
    canvas = canvas.resize((round(canvas.width * scale), round(canvas.height * scale)), Image.LANCZOS).convert("RGB")
    out = key_green(generate(STAGE_PROMPTS[stage].format(gem=gem) + " " + COMMON, canvas))
    # 生成した絵の外接矩形を下絵の外接矩形に合わせて伸縮し、下絵のアルファで切る（輪郭を下絵とそろえる）
    gb = bbox(np.array(out)[..., 3])
    sb = bbox(src_a)
    fitted = out.crop(gb).resize((sb[2] - sb[0], sb[3] - sb[1]), Image.LANCZOS)
    # 生成がわずかに細くて下絵の縁が残るところは、下絵の色がのぞく（緑や黒の欠けにしない）
    result = src.copy()
    result.alpha_composite(fitted, (sb[0], sb[1]))
    arr = np.array(result)
    arr[..., 3] = src_a
    dest = os.path.join(ASSETS, f"dragon_{species}_{stage}_{part}.png")
    Image.fromarray(arr, "RGBA").save(dest, optimize=True)
    print(dest, src.size)


if __name__ == "__main__":
    main()
