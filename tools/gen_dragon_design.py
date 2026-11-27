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
# v3.247.0（DT-650 11/27）: 2回目のデザイン。胴の絵は尻尾を描かず、腰の後ろの短い付け根で終わる（ゲームが動く尻尾を描くので、
# 胴の絵にも尻尾があると2本になる。11/27 Shooter「雷雲竜は尻尾が画像と描画で2本」）。構図の見本は尻尾の無い火竜の胴
SOURCE_V2 = {"body": "fire", "wing": None}

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

# v3.247.0（DT-650 11/27 Shooter「鮫竜はもっと鮫らしく」「亀竜は恐竜の鎧竜、アンキロサウルスのイメージ」）
DESIGNS_V2 = {
    "shark": {
        "body": ("a SHARK DRAGON that unmistakably reads as a GREAT WHITE SHARK from above: a thick torpedo-shaped shark body that is "
                 "widest at the chest, a broad flat CONICAL shark snout, small black eyes set at the sides of the head, five dark GILL "
                 "SLITS on each side behind the head, a big triangular shark DORSAL FIN standing up in the middle of the back, two small "
                 "clawed forelegs and two small hind legs tucked close to the belly like fins. Steel ocean blue (#6aa8e0) on the back "
                 "fading to a pale white belly visible along both sides (countershading), a few pale scars."),
        "wing": ("ONE wing of a shark dragon shaped like a huge stiff shark PECTORAL FIN: a thick swept-back triangular fin, steel ocean "
                 "blue (#6aa8e0) on top with a pale white trailing edge, no bones and no membrane, smooth shark skin."),
    },
    "tortoise": {
        "body": ("an ANKYLOSAURUS DRAGON (armoured dinosaur): a very wide low heavy body covered all over the back with rows of bony "
                 "ARMOUR PLATES and round OSTEODERM studs, rows of short sharp SPIKES sticking out sideways along both flanks, a small "
                 "wide armoured head with a beak and two pairs of short backward horns at the back corners of the skull, four thick "
                 "stubby clawed legs. Moss green skin (#8cc070) with darker olive-green and bone-tan armour plates."),
        "wing": ("ONE small stubby wing of an ankylosaurus dragon: a short leathery moss-green (#8cc070) membrane between thick short "
                 "finger bones, the leading edge covered with a row of bony olive-green armour plates and short sharp spikes."),
    },
}
EDITS_V2 = {
    "thunder": {
        "body": ("Keep this exact creature, its design, colours, pose, head, horns, storm cloud mane and legs EXACTLY as they are, but "
                 "REMOVE ITS LONG TAIL completely: the body must end just behind the hind legs with only a very short tapered stub. "
                 "Nothing else changes."),
    },
}
NO_TAIL = (" IMPORTANT: draw NO TAIL: like the input, the body ends just behind the hind legs with only a very short tapered stub "
           "(the game draws the tail separately).")

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
    v2 = "--v2" in sys.argv   # DT-650: 2回目のデザインを assets/design_candidates/ に書く（ゲームの絵は書き換えない。見せて決まってから入れる）
    if v2 and species in EDITS_V2:
        ref = f"dragon_{species}_{part}.png"   # いまの絵を直す
    elif v2:
        ref = f"dragon_{SOURCE_V2[part] or species}_{part}.png"
    else:
        ref = f"dragon_{SOURCE[species]}_{part}.png"
    src = Image.open(os.path.join(ASSETS, ref)).convert("RGBA")
    pad = int(max(src.size) * PAD_RATIO)
    canvas = Image.new("RGBA", (src.width + pad * 2, src.height + pad * 2), GREEN + (255,))
    canvas.alpha_composite(src, (pad, pad))
    scale = 1024 / max(canvas.size)
    canvas = canvas.resize((round(canvas.width * scale), round(canvas.height * scale)), Image.LANCZOS).convert("RGB")
    if v2 and species in EDITS_V2:
        prompt = EDITS_V2[species][part] + " Same art style. Solid flat pure green background (#00FF00), no shadow, no text."
    elif v2:
        prompt = FRAME[part] + DESIGNS_V2[species][part] + (NO_TAIL if part == "body" else "") + " " + STYLE
    else:
        prompt = FRAME[part] + DESIGNS[species][part] + " " + STYLE
    raw = generate(prompt, canvas)
    if os.environ.get("GEM_RAW_DIR"):
        raw.save(os.path.join(os.environ["GEM_RAW_DIR"], f"design_{species}_{part}.png"))
    out = key_green(raw)
    out = out.crop(bbox(np.array(out)[..., 3]))
    # 胴は高さ 320、翼は幅 320（ほかの竜種の絵と同じ決まり。DRAGON_PART_SPRITES の bodyDrawH・wingDrawW はこの寸法が前提）
    k = 320 / (out.height if part == "body" else out.width)
    out = out.resize((max(1, round(out.width * k)), max(1, round(out.height * k))), Image.LANCZOS)
    dest_dir = os.path.join(ASSETS, "design_candidates") if v2 else ASSETS
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"dragon_{species}_{part}.png")
    out.save(dest, optimize=True)
    print(dest, out.size)


if __name__ == "__main__":
    main()
