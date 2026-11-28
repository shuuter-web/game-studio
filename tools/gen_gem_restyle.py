"""Dragon Tide（DT-609）: いまの竜の絵を下絵に渡し、形を保ったまま材質だけ「原石」「全身カットの宝石」に描き直す。

  python3 tools/gen_gem_restyle.py <竜種> <rough|sparkle> <body|wing|body_air> ["<材質の描写>"]
  （body_air は蛙竜の跳んでいるときの胴。v3.235.0）

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
TRIES = int(os.environ.get("GEM_TRIES", "4"))                   # 覆いが足りないときに描き直させる回数
COVER_OK = 0.97               # 生成の絵が下絵の「ある」所をこれだけ覆えば使う
PAD_RATIO = 0.18              # 下絵のまわりに足す緑の余白（生成が端まで描いて切れないように）

# 竜種ごとの宝石（2つの段階で同じ石。原石＝磨く前、sparkle＝全身カット）
GEMS = {
    "falcon": "clear rock crystal quartz with a faint icy blue tint (colorless transparent gemstone)",
    "swallow": "paraiba tourmaline, vivid neon teal blue-green gemstone",
    "hornet": "golden yellow citrine gemstone, with the dark stripes made of polished black onyx",
    # v3.235.0（DT-609「続けて他の竜も」）: 鮫竜・蛙竜・亀竜・雷雲竜
    "shark": "deep cornflower-blue sapphire gemstone (ocean blue, saturated)",
    "frog": "vivid lime-green peridot gemstone (bright yellowish green)",
    "tortoise": "translucent VIVID saturated imperial-green jadeite jade gemstone (bright leaf green like a tortoise, recolour everything green, NOT grey, NOT stone grey)",
    "thunder": "bright lemon-gold heliodor (golden yellow beryl) gemstone, electric and luminous",
    # v3.258.0（DT-652〜655）: UFO・彗星竜・爆竜・屍竜
    "ufo": "rainbow moonstone gemstone: luminous milky silvery-white with a strong electric cyan-blue glow (adularescence), bright and cool, NOT dull grey",
    "comet": "golden sunstone gemstone: BRIGHT luminous pale cream-gold and light honey-yellow (like the input colours, NOT brown, NOT tan, NOT pink), full of tiny glittering gold spangles like stardust",
    "bomber": "imperial topaz gemstone: vivid saturated sherry-orange to reddish orange, warm and fiery",
    "bone": "white precious opal for every bone (milky white with soft pastel rainbow play-of-colour flecks), and violet-blue tanzanite for the purple parts",
    # DT-656・661・662（11/28）: 塊竜・鉄鎖竜・鯨竜（本デザインをゲームに入れて宝石に）
    "ball": "mandarin spessartite garnet gemstone: vivid juicy tangerine orange, bright and fiery (NOT brown)",
    "flail": "steel-grey spinel gemstone: cool silvery gunmetal grey with bright mirror-like silver reflections, like polished steel turned into a gem",
    "whale": "London blue topaz gemstone: deep slate ocean blue, with the pale belly in milky white moonstone",
    # DT-664（11/28 Shooter「全身を宝石化するのではなく、水晶の部分が増えて光る方向で。メカっぽさは残す」）: 光線竜は石の種類ではなく水晶の量
    "ray": "glowing clear cyan quartz crystal",
}

# 専用の絵が無く、別の竜種の絵を借りている竜種（index.html の DRAGON_PARTS_ALIAS と同じ）。宝石の絵はその輪郭のまま作る
# v3.244.0（DT-609 11/27）: 鮫竜・亀竜・雷雲竜は専用の絵（tools/gen_dragon_design.py）ができたので、借りる絵は無くなった
SOURCE = {}

# v3.235.0: 緑の宝石（ペリドット・翡翠）は緑の背景だと石まで抜け（覆いが2〜3割）、緑かぶり消しで色もくすむので、マゼンタの背景で抜く
MAGENTA = (255, 0, 255)
# v3.247.0（DT-650 11/27 Shooter「蛙竜の1進化は、一部しか宝石じゃないので、他の竜と同様全身宝石に」）: 竜種ごとに足す注意。
# 蛙竜は背の模様の所だけが大きな1つの石になり、脚・頭はくすんだ緑の肌のまま残った（光る面も背中だけになった）
EXTRA = {
    "frog": (" The WHOLE creature must be gemstone: the head, the eyes, all four legs, the feet and the toes are ALL cut into many "
             "SMALL facets of the same brilliant {gem}, evenly all over the body like a cut gem figurine. NO plain skin areas, NO "
             "single big round gem in the middle of the back, ignore the spots and the belly pattern of the input. Keep it BRIGHT, light and luminous like the brightest parts of the input (glowing light lime green), not dark."),
    # v3.253.0（DT-650 11/28 Shooter「雷雲竜の黒い部分がかっこいいので、宝石になっても黒さは維持して欲しい。特に翼」）:
    # 全身カットにすると翼の雷雲の膜まで黄金になり、背の雷雲も銀に褪せた。雷雲の所だけ黒い石で切る
    "thunder": (" IMPORTANT: keep the two-tone colour scheme of the input. Only the lightning-bolt bones, horns, claws and the yellow "
                "scales are {gem}. Every DARK storm-cloud part (the whole wing membrane between the lightning bones, and the cloud "
                "mane along the back) must stay DARK: cut it as polished jet-black onyx / black diamond facets (near-black charcoal "
                "with steel-blue glints and thin white facet edges). Do NOT turn the dark cloud parts yellow, gold, grey or silver."),
    # v3.255.0（DT-650 11/28 Shooter「鮫竜の進化の胴体が、小さなサメが大きな宝石の上に乗ってるみたいになってる」）:
    # 全身カットで、輪郭いっぱいの宝石の塊の上に、ひと回り小さい鮫の線画（目・えら・背びれ）が乗った絵になった。鮫の形そのものを石で切らせる
    "shark": (" The shark's OWN body is the gem: the facets follow the shark's anatomy (snout, eyes, gill slits, dorsal fin, pectoral "
              "fins, belly, legs) at FULL SIZE, filling the input silhouette edge to edge. Do NOT draw a smaller shark, a shark outline "
              "or shark line-art on top of / inside a big gem block, and no second inner outline. The outer ink outline IS the shark's outline."),
    # v3.258.0（DT-652〜655）: 鮫竜の「大きな宝石の上に小さな鮫」と同じ崩れを先に防ぐ（竜の形そのものを石で切らせる）
    "comet": (" The dragon's OWN body is the gem: the facets follow its anatomy (head, neck, legs, toes, the glowing core on the back, "
              "tail) at FULL SIZE, filling the input silhouette edge to edge. Do NOT draw a smaller dragon or dragon line-art on top of / "
              "inside a big gem block, no second inner outline. Keep everything the input has (such as a glowing core) and add nothing new."),
    "bomber": (" The dragon's OWN armoured body is the gem: keep the armour plate divisions and the rivets as the facet layout, at FULL "
               "SIZE, filling the input silhouette edge to edge. Do NOT draw a smaller dragon on top of / inside a big gem block, no second inner outline."),
    "bone": (" Keep it a SKELETON: every bone (skull, spine, ribs, leg bones, tail vertebrae, wing bones) is cut from {gem}, with the "
             "gaps between the bones kept empty exactly like the input. The purple flame in the chest and the purple eye glow stay "
             "glowing violet. On a wing, the torn membrane between the bones is the violet tanzanite, the bones are the white opal. "
             "Do NOT fill the skeleton into a solid body, do NOT draw a smaller skeleton on top of a gem block. Do not add eyes, skulls or anything new."),
    "ufo": (" It is a round flying-saucer disc seen from straight above: the WHOLE disc is the gem (the outer rim ring, the concentric "
            "panels and the central glass dome), filling the input circle edge to edge. Keep the small glowing cyan lights around the "
            "rim as little round cyan gems. No dragon, no other object, the same perfect circle."),
    # DT-656（11/28「ほかの竜種より小さく見えるので、カット面を大きく」）: 塊竜は帯の鎧を大きな面で切る
    "ball": (" The dragon's OWN body is the gem at FULL SIZE, filling the input silhouette edge to edge, no smaller dragon on top of a gem block. "
             "Use only a FEW BIG BOLD facets (each armour band is cut into 2-4 large flat facets), much larger facets than a usual cut gem, "
             "so the facets stay readable when the sprite is tiny. Keep the curled round shape and the curled tail."),
    # DT-661（11/28 Shooter「進化する時に鎖が消えないように注意して下さい」）
    "flail": (" The dragon's OWN armoured body is the gem at FULL SIZE, filling the input silhouette edge to edge (keep the armour plate "
              "divisions, the spiked pauldrons and the helmeted head). VERY IMPORTANT: the thick diagonal CHAIN across the back must stay "
              "clearly visible as a chain of big separate links, cut from dark polished black hematite with bright silver edges, contrasting "
              "with the grey spinel body. Do NOT dissolve or remove the chain."),
    "whale": (" The whale dragon's OWN body is the gem at FULL SIZE, filling the input silhouette edge to edge: the facets follow its "
              "anatomy (wide head, blowhole, spine knobs, pale belly edges, flipper legs). Do NOT draw a smaller whale on top of a gem block, no second inner outline."),
}
# v3.258.0: 原石にも効かせる注意（骨のすき間を埋めない・円盤のまま）
EXTRA_ROUGH = {
    "bone": " Keep it a SKELETON with the gaps between the bones empty exactly like the input; bones are rough white opal ore, the purple parts rough violet tanzanite.",
    "ufo": " It is a round flying-saucer disc seen from straight above: keep the perfect circle, the rim ring, the concentric panels, the central dome and the little rim lights.",
    "flail": " Keep the thick diagonal CHAIN across the back clearly visible as big separate links of rough dark hematite ore.",
    "ball": " Keep the big armour bands and the curled tail; the ore chunks are big and simple.",
}
MAGENTA_BG = {"frog", "tortoise"}

STAGE_PROMPTS = {
    "rough": ("Redraw this exact creature as if it were carved from a ROUGH, UNCUT {gem} ORE: raw crystal chunks and natural crystal "
              "clusters, matte, no polished facets, no sparkle stars. Keep the species colour strong and saturated (not faded, not brown, "
              "not grey rock). Do not add a rock base, slab or crystals around the creature: only the creature itself."),
    "sparkle": ("Redraw this exact creature as if its WHOLE BODY were a brilliant FACET-CUT {gem}: the surface is divided into many "
                "triangular and kite-shaped polished facets with thin white edge highlights, deep saturated colour inside, bright "
                "reflections and a few small white sparkle stars."),
}

# DT-664（11/28 Shooter「光線竜の進化は全身を宝石化するのではなく、水晶の部分が増えて光る方向で。メカっぽさは残すように」）:
# 光線竜は石の種類で描き直さず、紺の装甲（機械）はそのままで水晶の所だけを増やす。進化前はいまの本デザイン（ray）のまま
SPECIES_STAGE_PROMPTS = {
    ("ray", "sparkle"): ("Keep this exact mecha laser dragon and its dark teal-navy METAL armour plates exactly as they are (matte metal "
                         "with panel lines, NOT gemstone: keep the mechanical robot look). Only ADD MORE CRYSTAL: many clear glowing "
                         "cyan quartz crystals now grow out of the armour: clusters of pointed crystals along the spine, on both shoulders, "
                         "on the hips and at the back of the head, the snout lens bigger and brighter, and the glowing cyan circuit lines "
                         "thicker and brighter. The crystals are faceted clear bright cyan with white edge highlights. About one third "
                         "of the body is crystal, the rest stays dark navy mecha armour."),
}
SPECIES_STAGE_PROMPTS_WING = {
    ("ray", "sparkle"): ("Keep this exact angular mecha wing and its dark teal-navy METAL membrane exactly as it is (matte metal, NOT "
                         "gemstone, keep the mechanical look). Only ADD MORE CRYSTAL: a row of bigger pointed clear glowing cyan quartz "
                         "crystals along the leading edge, small crystal clusters at the bone joints, and the glowing cyan light "
                         "lines along the bones thicker and brighter. Crystals are faceted bright cyan with white edge highlights."),
}

COMMON = ("Keep EXACTLY the same silhouette, pose, outline, proportions, size and position as the input image: same head, horns, "
          "limbs, tail, wing bones and membrane edges, nothing added or removed. Top-down view, flat cel-shaded game sprite with a "
          "thick dark ink outline. Solid flat pure {bg_name} background ({bg_hex}), no shadow, no text.")


# v3.235.0: 翼だけの下絵に頭・胴・尻尾を描き足して竜を丸ごと描くことがあった（覆いが7割に落ちる）ので、部位を言い切る
PART_HINTS = {
    "wing": "The input is ONLY ONE SINGLE DETACHED WING seen from above (no head, no body, no tail, no legs): draw ONLY that one wing. ",
    "body": "The input is the body WITHOUT wings: do not add wings. ",
    "body_air": "The input is the body WITHOUT wings, legs stretched out in a jump: do not add wings. ",
}


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


def key_magenta(img):
    """key_green の色を入れ替えたもの（マゼンタ＝赤と青が緑より強い所を抜き、縁のマゼンタかぶりも消す）"""
    a = np.array(img).astype(np.float32)
    r, g, b = a[..., 0], a[..., 1], a[..., 2]
    excess = np.minimum(r, b) - g
    alpha = np.clip(1 - (excess - 30) / 70, 0, 1)
    over = excess > 0
    a[..., 0] = np.where(over, r - excess * 0.85, r)
    a[..., 2] = np.where(over, b - excess * 0.85, b)
    a[..., 3] = alpha * 255
    return Image.fromarray(np.clip(a, 0, 255).astype(np.uint8), "RGBA")


def bbox(alpha, thresh=40):
    return Image.fromarray((alpha > thresh).astype(np.uint8) * 255).getbbox()


def main():
    species, stage, part = sys.argv[1:4]
    gem = sys.argv[4] if len(sys.argv) > 4 else GEMS[species]
    src = Image.open(os.path.join(ASSETS, f"dragon_{SOURCE.get(species, species)}_{part}.png")).convert("RGBA")
    if os.environ.get("GEM_SRC"):   # 下絵を別の絵にする（DT-650: 蛙竜は前の明るい全身カットを下絵に、カットを脚・頭まで広げる）。輪郭は元の絵のまま
        alt = Image.open(os.environ["GEM_SRC"]).convert("RGBA")
        alt_arr = np.array(alt)
        alt_arr[..., 3] = np.array(src)[..., 3]
        src = Image.fromarray(alt_arr, "RGBA")
    src_a = np.array(src)[..., 3]
    # 生成に渡す下絵：緑の上に置いて、余白を足して大きめに（小さい絵だと描き込みが粗くなる）
    pad = int(max(src.size) * PAD_RATIO)
    scale = 1024 / (max(src.size) + pad * 2)
    magenta = species in MAGENTA_BG
    bg, key = (MAGENTA, key_magenta) if magenta else (GREEN, key_green)
    common = COMMON.format(bg_name="magenta" if magenta else "green", bg_hex="#FF00FF" if magenta else "#00FF00")
    canvas = Image.new("RGBA", (src.width + pad * 2, src.height + pad * 2), bg + (255,))
    canvas.alpha_composite(src, (pad, pad))
    canvas = canvas.resize((round(canvas.width * scale), round(canvas.height * scale)), Image.LANCZOS).convert("RGB")
    # v3.235.0: 生成が下絵より細く描くと（輪郭の内側に余白・光の粒が外接矩形を広げる）下絵の色がのぞくので、
    # 下絵の「ある」所を生成の絵がどれだけ覆うかを測り、足りなければ描き直させる（最大 TRIES 回。いちばん覆った絵を使う）
    sb = bbox(src_a)
    best = None
    for attempt in range(TRIES):
        extra = (EXTRA if stage == "sparkle" else EXTRA_ROUGH).get(species, "").format(gem=gem)
        stage_prompt = (SPECIES_STAGE_PROMPTS_WING if part == "wing" else SPECIES_STAGE_PROMPTS).get((species, stage)) \
            or STAGE_PROMPTS[stage].format(gem=gem)
        raw = generate(PART_HINTS.get(part, "") + stage_prompt + extra + " " + common, canvas)
        if os.environ.get("GEM_RAW_DIR"):
            raw.save(os.path.join(os.environ["GEM_RAW_DIR"], f"{species}_{stage}_{part}_{attempt}.png"))
        out = key(raw)
        # 生成した絵の外接矩形を下絵の外接矩形に合わせて伸縮し、下絵のアルファで切る（輪郭を下絵とそろえる）
        gb = bbox(np.array(out)[..., 3])
        fitted = out.crop(gb).resize((sb[2] - sb[0], sb[3] - sb[1]), Image.LANCZOS)
        fa = np.zeros_like(src_a)
        fa[sb[1]:sb[3], sb[0]:sb[2]] = np.array(fitted)[..., 3]
        inside = src_a > 90
        cover = float((fa[inside] > 128).mean())
        print(f"  試し{attempt + 1}: 下絵を覆う割合 {cover:.3f}", file=sys.stderr)
        if best is None or cover > best[0]:
            best = (cover, fitted)
        if cover >= COVER_OK:
            break
    fitted = best[1]
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
