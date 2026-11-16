"""Dragon Tide: クラウドの定時チェックから画像を1枚生成 → 緑抜き → 余白を詰めて縮小。

  python3 tools/gen_sprite_cloud.py <out.png> "<描写>" [長辺px=128] [--raw] [--black]

手元の Windows 用（tools/gen_enemy_sprite.sh）は ClaudeCodeForge に頼っていて、クラウドでは動かない。
こちらは generativelanguage.googleapis.com を直接呼ぶ（鍵はプロキシが差し込むので dummy でよい）。
--raw は「真上から」の決まり文句を付けない。--black は黒地を明るさ＝透明度にして抜く（光の絵用）。
"""
import sys, json, base64, io, os, urllib.request
import numpy as np
from PIL import Image

MODEL = os.environ.get("SPRITE_MODEL", "gemini-3.1-flash-image")
TOP = ("STRICT OVERHEAD MAP VIEW. The camera is a bird directly above, looking straight DOWN at the ground. "
       "You see ONLY the TOP surfaces. No perspective, no side faces, nothing seen in elevation. "
       "Flat cel-shaded illustration style, bold clean silhouette, thick dark ink outlines, high contrast, no painterly texture. "
       "Solid flat pure green background (#00FF00) for chroma key removal, no ground, no shadow, no other objects, no text. "
       "IMPORTANT: the subject occupies only the middle 65 percent of the image, with a WIDE EMPTY GREEN BORDER on all four sides. "
       "The forward direction of the subject points toward the TOP of the image. ")

def generate(prompt):
    body = json.dumps({"contents": [{"parts": [{"text": prompt}]}],
                       "generationConfig": {"responseModalities": ["IMAGE"]}}).encode()
    req = urllib.request.Request(
        f"https://generativelanguage.googleapis.com/v1beta/models/{MODEL}:generateContent",
        data=body, headers={"Content-Type": "application/json", "x-goog-api-key": "dummy"})
    with urllib.request.urlopen(req, timeout=180) as res:
        data = json.load(res)
    for part in data["candidates"][0]["content"]["parts"]:
        if "inlineData" in part:
            return Image.open(io.BytesIO(base64.b64decode(part["inlineData"]["data"]))).convert("RGBA")
    raise SystemExit("画像が返ってこなかった: " + json.dumps(data)[:400])

def key_green(img):
    a = np.array(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    # 緑がほかの2色よりどれだけ強いか。強いほど透明。縁の緑かぶりは緑を赤青の大きい方まで下げて消す
    excess = g - np.maximum(r, b)
    alpha = np.clip(1 - (excess - 30) / 70, 0, 1)
    a[..., 1] = np.where(excess > 0, np.maximum(r, b) + excess * 0.15, g)
    a[..., 3] = alpha * 255
    return Image.fromarray(a.astype(np.uint8), "RGBA")

def key_black(img):
    a = np.array(img).astype(np.float32)
    lum = a[..., :3].max(axis=2)
    a[..., 3] = np.clip((lum - 12) / 110, 0, 1) * 255
    return Image.fromarray(a.astype(np.uint8), "RGBA")

def main():
    args = [x for x in sys.argv[1:] if not x.startswith("--")]
    flags = {x for x in sys.argv[1:] if x.startswith("--")}
    out, desc = args[0], args[1]
    size = int(args[2]) if len(args) > 2 else 128
    img = generate(desc if "--raw" in flags else TOP + desc)
    img = key_black(img) if "--black" in flags else key_green(img)
    box = Image.fromarray((np.array(img)[..., 3] > 40).astype(np.uint8) * 255).getbbox()
    if box: img = img.crop(box)
    k = size / max(img.size)
    img = img.resize((max(1, round(img.width * k)), max(1, round(img.height * k))), Image.LANCZOS)
    img.save(out, optimize=True)
    print(out, img.size)

if __name__ == "__main__":
    main()
