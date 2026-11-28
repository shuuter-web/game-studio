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

# DT-656〜664（11/28）: 借りている絵のままの9竜種（塊竜・土竜・磁竜・双子竜・鬼火・鉄鎖竜・鯨竜・砲撃竜・光線竜）の本デザイン。
# 見せて決まるまでゲームには入れないので assets/design_candidates/ に書く。構図の見本：胴は尻尾の無い絵（ゲームが尻尾を描く竜種は
# NO_TAIL を足す。塊竜・鬼火は noTail＝ゲームが尻尾を描かないので、胴の絵の中に尻尾をまとめる）、翼は借りている翼。
SOURCE_V3 = {
    "ball": ("heavy", "fire"), "mole": ("fire", "crimson"), "magnet": ("fire", "shadow"), "twin": ("crimson", "swallow"),
    "wisp": ("fire", "ice"), "flail": ("crimson", "heavy"), "whale": ("crimson", "gargoyle"), "cannon": ("crimson", "heavy"),
    "ray": ("fire", "swallow"),
}
TAILED_IN_BODY = {"ball", "wisp"}   # SPECIES_DEFS の noTail
DESIGNS_V3 = {
    # 塊竜：群れが玉になって転がる。玉の表面に小さく貼り付くので、大きな面で読める丸い形（あとで面の大きい宝石にする）
    "ball": {
        "body": ("a CLUMP DRAGON curled up like a PANGOLIN / ARMADILLO: a short, very ROUND, compact chunky body whose whole back is covered "
                 "by 5 big broad overlapping rounded ARMOUR BANDS running across the back (like a pill bug), a small round head with a "
                 "short blunt snout and two tiny rounded horns, four short stubby clawed legs barely sticking out, and a short thick "
                 "tail CURLED tightly around one side of the body so the whole silhouette is almost a circle. Warm orange (#e0904a) "
                 "bands with darker burnt-orange (#c07030) rims and creamy tan belly edges. Big simple shapes that stay readable when tiny."),
        "wing": ("ONE small round stubby wing of a pangolin-like clump dragon: a short rounded leathery orange (#e0904a) membrane between "
                 "3 thick short finger bones, the leading edge covered by 3 big overlapping rounded armour bands like pangolin scales, "
                 "darker burnt-orange (#c07030) rims. Compact, rounded, simple big shapes."),
    },
    # 土竜（もぐら）：地中を進み、線に沿って地面を割る
    "mole": {
        "body": ("a MOLE DRAGON (a burrowing dragon like a STAR-NOSED MOLE): a stout cylindrical body, a pointed snout ending in a pink "
                 "fleshy STAR-SHAPED NOSE with many little tentacles, tiny eyes, two HUGE SPADE-LIKE DIGGING FOREPAWS with big ivory "
                 "shovel claws held out to the sides at the front, small hind legs, short velvety earth-brown (#b08850) fur-like scales "
                 "with darker brown (#8a6a40) stripes down the back, a few clods of dirt and small pebbles stuck on the back, a "
                 "rocky ridge of short stone spikes along the spine."),
        "wing": ("ONE wing of a mole dragon: an earth-brown (#b08850) leathery membrane between thick finger bones, the leading edge "
                 "crusted with rocks and clumps of soil, a big ivory digging claw at the wrist, darker brown (#8a6a40) ragged edges."),
    },
    # 磁竜：壊れた建物の破片を周りに回す
    "magnet": {
        "body": ("a MAGNET DRAGON: a sleek dragon with lavender-purple (#b090e0) metallic scales, two big curved horns that together form a "
                 "U-shaped HORSESHOE MAGNET above the back of the head, one horn tip painted RED and the other SILVER-WHITE (the two "
                 "poles), dark violet (#6a4ea0) plates along the spine shaped like stacked bar magnets, small silver iron filings "
                 "bristling in curved field-line arcs on the shoulders, clawed legs."),
        "wing": ("ONE wing of a magnet dragon: lavender-purple (#b090e0) metallic membrane, the wing bones are curved silver bars bent "
                 "like MAGNETIC FIELD LINES fanning out from the root, the tips of the bones alternately RED and SILVER-WHITE like "
                 "magnet poles, dark violet (#6a4ea0) trailing edge."),
    },
    # 双子竜：群れが左右2列に分かれ、2列の間を雷のアーチで焼く
    "twin": {
        "body": ("a TWIN DRAGON: ONE body with TWO NECKS AND TWO HEADS side by side (a left head and a right head, both pointing "
                 "forward/up, necks splitting at the shoulders in a V), a small crackling ELECTRIC ARC spark jumping between the two "
                 "heads' horns, golden yellow (#ffe070) scales with darker gold (#e0c040) back plates, the left half has a thin white "
                 "stripe and the right half a thin amber stripe along the spine, clawed legs."),
        "wing": ("ONE wing of a twin dragon: golden yellow (#ffe070) membrane between finger bones, the bones are DOUBLED (each bone "
                 "is a pair of parallel thin bones running side by side), a zig-zag crackle of white-yellow electricity running along "
                 "the leading edge, darker gold (#e0c040) trailing edge."),
    },
    # 鬼火：ゲームでは灯（火）で描く。竜の絵は図鑑用
    "wisp": {
        "body": ("a WILL-O'-WISP DRAGON: a slender ghostly spirit dragon whose body is made of cold pale-blue FLAME: pale sky blue "
                 "(#a0d8ff) body with white-blue hot core along the spine, flickering flame tongues rising from the back of the head "
                 "and along the spine like a mane, big hollow glowing white eyes, thin wispy clawed legs, and a tail that "
                 "DISSOLVES INTO A FLICKERING FLAME TIP curving to one side (the tail is part of this sprite). Deeper blue (#5a8ed0) "
                 "flame shading. The flames are SOLID OPAQUE cel-shaded shapes with a thick dark navy outline, NOT translucent, NO glow halo."),
        "wing": ("ONE wing of a will-o'-wisp dragon made of cold blue FIRE: the membrane is a row of pale sky blue (#a0d8ff) flame "
                 "tongues streaming backward, thin white-blue bone-like flame veins, deeper blue (#5a8ed0) flame shading. SOLID OPAQUE "
                 "cel-shaded flames with a thick dark navy outline, NOT translucent, NO glow halo."),
    },
    # 鉄鎖竜：群れ全体で鎖につないだ鉄球を引く
    "flail": {
        "body": ("an IRON CHAIN DRAGON (flail dragon): a heavy armoured dragon with steel grey (#b8bcc4) riveted iron plates like a "
                 "knight's armour on the back, big round spiked iron shoulder pauldrons, a heavy CHAIN of thick iron links wrapped "
                 "DIAGONALLY across the back from the left shoulder to the right hip, a few short iron spikes on the spine, a blunt "
                 "helmeted head with two short horns, dark gunmetal (#6a6e76) shading and rust-brown rivets, clawed legs."),
        "wing": ("ONE wing of an iron chain dragon: the wing bones are made of iron CHAIN LINKS, the membrane is overlapping riveted "
                 "steel grey (#b8bcc4) iron plates like armour, dark gunmetal (#6a6e76) shading, a small spiked iron ball at the wrist."),
    },
    # 鯨竜：数体だけの巨体。止まると息を吸って周りを吸い寄せる
    "whale": {
        "body": ("a WHALE DRAGON: a huge massive broad body shaped like a SPERM/HUMPBACK WHALE seen from above, a very wide blunt "
                 "rounded whale head with a BLOWHOLE (two dark slits) on top of the head, small eyes at the sides, a few white "
                 "BARNACLE clusters on the head and back, slate blue (#5f8fb8) back with a darker navy (#3e6488) spine ridge of small "
                 "rounded knobs, pale cream-white belly visible along both sides, four short thick flipper-like clawed legs."),
        "wing": ("ONE wing of a whale dragon shaped like a long HUMPBACK WHALE FLIPPER: a long narrow slightly curved flipper with a "
                 "bumpy KNOBBED leading edge (tubercles), slate blue (#5f8fb8) on top with white patches and white barnacles, no "
                 "membrane and no finger bones, smooth whale skin."),
    },
    # 砲撃竜：旗へ山なりの砲弾を撃ち込む
    "cannon": {
        "body": ("a BOMBARD DRAGON (artillery dragon): a sturdy dragon carrying a short fat brass MORTAR CANNON mounted upright on the "
                 "middle of its back (seen from above as a thick brass ring with a dark round open MUZZLE), riveted bronze armour "
                 "plates around the mortar, a bandolier of round black cannonballs across the back, golden brass (#e8c050) scales "
                 "with darker bronze (#a07830) plates, a blunt head with two short horns like a helmet, clawed legs."),
        "wing": ("ONE wing of a bombard dragon: a golden brass (#e8c050) membrane reinforced with riveted bronze (#a07830) metal "
                 "plates along the bones, the bones are brass rods with rivets, a small brass gear at the wrist."),
    },
    # 光線竜：向いている前へ細長い光線弾を撃ち続ける
    "ray": {
        "body": ("a LASER DRAGON: a sleek narrow streamlined dragon, a sharp pointed head with a big glowing cyan CRYSTAL LENS set at "
                 "the tip of the snout, straight swept-back crystal horns, bright cyan (#7af7ff) glowing ENERGY LINES running in "
                 "straight parallel lines along the body like circuit traces, dark teal-navy (#1e5068) armour plates, angular "
                 "prism-like spines along the back, slim clawed legs. Opaque cel-shaded, NO glow halo."),
        "wing": ("ONE wing of a laser dragon: a sharp angular swept-back wing, dark teal-navy (#1e5068) membrane with straight bright "
                 "cyan (#7af7ff) glowing light-conduit lines running along each bone, a row of clear cyan PRISM crystals along the "
                 "leading edge. Opaque cel-shaded, NO glow halo."),
    },
}
# DT-657・663（11/28 Shooter の手直し）: 見せた本デザインを直す。
#   土竜「鼻の頭のイソギンチャクみたいな部分が気持ち悪い」→ 見せた絵（design_candidates）を下絵に、鼻の先だけ描き直す（EDITS_V4）
#   砲撃竜「砲口を見せるのではなく、ずんぐりデカい体に砲塔が乗るかたちで。砲塔はパーツ分けして回転できるように。砲身は短く太く」
#   → 胴（砲塔の台座だけ）と砲塔（別の絵。砲身は上＝頭の向き）を作り直す（DESIGNS_V4）
EDITS_V4 = {
    "mole": {
        "body": ("Keep this exact mole dragon, its pose, colours, body, digging forepaws, claws, back and everything else EXACTLY as "
                 "they are. ONLY change the tip of the snout: REMOVE the pink star-shaped nose with its many little tentacles "
                 "completely, and give it instead a simple, cute, smooth rounded mole nose: a small plain pink oval nose pad with two "
                 "tiny nostrils at the end of a tapered snout. No tentacles, no rays, no fleshy star. Nothing else changes."),
    },
}
DESIGNS_V4 = {
    "cannon": {
        "body": ("a BOMBARD DRAGON built like a chunky cartoon TANK: a very STOCKY, WIDE, BIG and heavy rounded-boxy body (clearly "
                 "wider and bulkier than a normal dragon, like a tank hull), thick riveted brass armour plates, a short thick neck and "
                 "a small blunt helmeted head with two short horns at the front, four short thick stubby legs with big clawed feet "
                 "sticking out at the four corners. In the middle of the back there is a flat round TURRET RING: an EMPTY circular "
                 "mounting plate with rivets and NOTHING mounted on it (no cannon, no barrel, no muzzle: the turret is a separate "
                 "sprite). Golden brass (#e8c050) with darker bronze (#a07830) plates and dark gunmetal details."),
        "turret": ("strictly top-down view of ONE SINGLE TANK TURRET only (no dragon, no body, no legs, no wings): a big round chunky "
                   "domed brass turret with rivets, a small round hatch and a little periscope, and ONE SHORT, VERY THICK, FAT cannon "
                   "barrel lying HORIZONTALLY and pointing toward the TOP of the image, seen from directly ABOVE (we see the top side of a "
                   "short fat cylinder, like a tank gun seen from a helicopter: a thick rectangle with rounded rivet bands, NOT looking "
                   "into the muzzle hole). The barrel is SHORT (about as long as the turret's radius) and as wide as a third of the "
                   "turret, with a thicker reinforced muzzle band at its tip. Golden brass (#e8c050), darker "
                   "bronze (#a07830), dark gunmetal inside the muzzle. Chunky cartoon military style."),
    },
}
OPAQUE = " The creature is fully OPAQUE inside its outline (no holes, no see-through parts)."

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
    v4_edit = "--v4" in sys.argv and species in EDITS_V4
    v4 = "--v4" in sys.argv and species in DESIGNS_V4
    v3 = species in DESIGNS_V3
    if v4_edit:
        ref = os.path.join("design_candidates", f"dragon_{species}_{part}.png")   # 見せた絵を直す
    elif v4:
        ref = f"dragon_{SOURCE_V3[species][0]}_body.png"   # 砲塔も胴の見本（尻尾の無い絵）を絵柄の見本に
    elif v3:
        ref = f"dragon_{SOURCE_V3[species][0 if part == 'body' else 1]}_{part}.png"
    elif v2 and species in EDITS_V2:
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
    if v4_edit:
        prompt = EDITS_V4[species][part] + " Same art style. Solid flat pure green background (#00FF00), no shadow, no text."
    elif v4 and part == "turret":
        prompt = ("Use the input sprite ONLY as a reference for the art style (flat cel-shaded, thick dark ink outline). Draw "
                  + DESIGNS_V4[species][part] + OPAQUE + " " + STYLE)
    elif v4:
        tail = NO_TAIL if species not in TAILED_IN_BODY else ""
        prompt = FRAME[part] + DESIGNS_V4[species][part] + tail + OPAQUE + " " + STYLE
    elif v3:
        tail = NO_TAIL if part == "body" and species not in TAILED_IN_BODY else ""
        prompt = FRAME[part] + DESIGNS_V3[species][part] + tail + OPAQUE + " " + os.environ.get("DESIGN_EXTRA", "") + STYLE
    elif v2 and species in EDITS_V2:
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
    # 胴は高さ 320、翼は幅 320（砲塔は高さ 200。胴に重ねる大きさは見本ページで決める）（ほかの竜種の絵と同じ決まり。DRAGON_PART_SPRITES の bodyDrawH・wingDrawW はこの寸法が前提）
    k = (200 / out.height) if part == "turret" else 320 / (out.height if part == "body" else out.width)
    out = out.resize((max(1, round(out.width * k)), max(1, round(out.height * k))), Image.LANCZOS)
    dest_dir = os.path.join(ASSETS, "design_candidates") if v2 or v3 or v4 or v4_edit else ASSETS
    os.makedirs(dest_dir, exist_ok=True)
    dest = os.path.join(dest_dir, f"dragon_{species}_{part}.png")
    out.save(dest, optimize=True)
    alpha = np.array(out)[..., 3]
    # 胴の絵は輪郭の中が不透明であること（v3.251.0 の蛙竜の教訓。中央値が255近いか）
    print(dest, out.size, "alpha median", int(np.median(alpha[alpha > 40])))


if __name__ == "__main__":
    main()
