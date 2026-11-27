"""Dragon Tide（DT-609 11/27）: 仮の絵（DRAGON_PARTS_ALIAS で借りている別の竜種の絵）しか無い竜種に、専用の胴・翼の絵（本デザイン）を作る。

  python3 tools/gen_dragon_design.py <竜種> <body|wing>
  → prototypes/dragon-tide/assets/dragon_<竜種>_<body|wing>.png（胴は高さ 320・翼は幅 320。ほかの竜種の絵と同じ寸法の決まり）

借りている絵を「向き・構図・絵柄の見本」として渡し、竜種の姿は DESIGNS の描写で描き直させる（輪郭は変わってよい）。
輪郭が変わるので、DRAGON_PART_SPRITES の寸法は描いたあとに tools/sprite_meta.py で測り直す。
生成は tools/gen_sprite_cloud.py と同じ口（generativelanguage.googleapis.com。鍵はプロキシが差し込む）。
"""
import os
import sys

import numpy as np
from PIL import Image

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from gen_gem_restyle import ASSETS, GREEN, generate, key_green, bbox  # noqa: E402

# 借りていた絵（index.html の DRAGON_PARTS_ALIAS。ガーゴイルは *_classic＝いまの石の絵）
SOURCE = {"shark": "swallow", "tortoise": "gargoyle", "thunder": "shadow"}

# 竜種ごとの姿（色は SPECIES_DEFS の color に合わせる。遊びの個性＝鮫竜：止まれず泳ぐ突進／亀竜：とても遅く重い甲羅弾／雷雲竜：雷を落とす）
DESIGNS = {
    "shark": {
        "body": ("a SHARK DRAGON: a sleek streamlined dragon whose head is a shark's head (pointed snout, small dark eyes, three gill slits "
                 "on each side of the neck), a tall curved shark DORSAL FIN on the middle of the back, small fin-like clawed forelegs and "
                 "hind legs held close to the body, and a long tapering tail. Ocean blue (#6aa8e0) on top with darker navy blue stripes "
                 "along the spine and a pale white belly edge visible at the sides."),
        "wing": ("ONE wing of a shark dragon shaped like a huge shark PECTORAL FIN: a stiff blue fin membrane (#6aa8e0 with darker navy "
                 "rays fanning out like fin rays), a pale leading edge, and a smooth swept-back trailing edge."),
    },
    "tortoise": {
        "body": ("a TORTOISE DRAGON: a stocky heavy dragon carrying a big domed TURTLE SHELL on its back (hexagonal scutes, dark green "
                 "rims), a blunt beaked turtle-like dragon head with two short horns, four thick stubby elephant-like clawed legs "
                 "sticking out of the shell, and a short thick pointed tail. Moss green skin (#8cc070) and darker olive-green shell."),
        "wing": ("ONE small stubby wing of a tortoise dragon: a leathery moss-green (#8cc070) membrane stretched between thick short "
                 "finger bones, with olive-green armour scutes like small turtle-shell plates along the leading edge."),
    },
    "thunder": {
        "body": ("a THUNDERHEAD DRAGON: a dragon made of a storm: golden yellow scales (#ffe070), a fluffy dark slate-grey STORM CLOUD "
                 "mane running from the back of the head down the spine, two zig-zag LIGHTNING-BOLT shaped horns, small sparks crackling "
                 "on the cloud, clawed legs, and a tail ending in a small cloud puff."),
        "wing": ("ONE wing of a thunderhead dragon: the wing bones are ZIG-ZAG LIGHTNING BOLTS in bright golden yellow (#ffe070), and "
                 "the membrane between them is a dark slate-grey STORM CLOUD with lighter grey puffy edges."),
    },
}

FRAME = {
    "body": ("Use the input sprite ONLY as a reference for the camera, the framing and the art style: strictly top-down view looking "
             "straight down at the creature's back, the HEAD POINTS TO THE TOP of the image, symmetric pose, same overall length and "
             "similar width as the input, NO WINGS (the wings are separate sprites). Redesign the creature itself as "),
    "wing": ("Use the input sprite ONLY as a reference for the camera, the framing, the orientation and the art style: strictly "
             "top-down view of ONE SINGLE DETACHED WING (no head, no body, no tail, no legs), the wing ROOT that attaches to the "
             "shoulder is at the RIGHT EDGE (top right), the wing extends to the LEFT, the leading edge is at the top, similar size "
             "and proportions as the input wing. Redesign the wing as "),
}
STYLE = ("Flat cel-shaded game sprite, clean bold silhouette, thick dark ink outline, high contrast, no painterly texture. "
         "Solid flat pure green background (#00FF00), no shadow, no ground, no text.")
PAD_RATIO = 0.18


def main():
    species, part = sys.argv[1:3]
    src = Image.open(os.path.join(ASSETS, f"dragon_{SOURCE[species]}_{part}.png")).convert("RGBA")
    pad = int(max(src.size) * PAD_RATIO)
    canvas = Image.new("RGBA", (src.width + pad * 2, src.height + pad * 2), GREEN + (255,))
    canvas.alpha_composite(src, (pad, pad))
    scale = 1024 / max(canvas.size)
    canvas = canvas.resize((round(canvas.width * scale), round(canvas.height * scale)), Image.LANCZOS).convert("RGB")
    raw = generate(FRAME[part] + DESIGNS[species][part] + " " + STYLE, canvas)
    if os.environ.get("GEM_RAW_DIR"):
        raw.save(os.path.join(os.environ["GEM_RAW_DIR"], f"design_{species}_{part}.png"))
    out = key_green(raw)
    out = out.crop(bbox(np.array(out)[..., 3]))
    # 胴は高さ 320、翼は幅 320（ほかの竜種の絵と同じ決まり。DRAGON_PART_SPRITES の bodyDrawH・wingDrawW はこの寸法が前提）
    k = 320 / (out.height if part == "body" else out.width)
    out = out.resize((max(1, round(out.width * k)), max(1, round(out.height * k))), Image.LANCZOS)
    dest = os.path.join(ASSETS, f"dragon_{species}_{part}.png")
    out.save(dest, optimize=True)
    print(dest, out.size)


if __name__ == "__main__":
    main()
