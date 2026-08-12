# Dragon Tide — スプライト生成方針とパーツ分割カテゴリ

- 作成: 2026-08-10 ／ 更新: 2026-08-12 ／ 対象コード: `prototypes/dragon-tide/index.html`（**v0.36.2** 時点）
- 目的：**竜種ごとに専用アセットを1つ持つ**（[dragon-tide-species.md](../gdd/dragon-tide-species.md) §4）方針のもと、
  「どのキャラをどう分割して作るか」を決める。
- 生成の共通手順は `/gen-game-asset`（`.claude/commands/`）と `C:\forge\ClaudeCodeForge` が正。
  本書は**Dragon Tide 固有の分割・座標仕様**を扱う。

---

## 1. 現状

| 対象 | 画像 | 方式 | 状態 |
|---|---|---|---|
| 火竜 | `dragon_fire_body.png` (613×1138) ＋ `dragon_fire_wing.png` (1376×768) | **胴体・翼 分離** | ✅ お手本 |
| 氷竜 | `dragon_ice_body.png` (430×928) ＋ `dragon_ice_wing.png` (1320×671) | **胴体・翼 分離** | ✅ v0.36.0 で移行（描き直し） |
| 影竜 | `dragon_shadow_body.png` (464×903) ＋ `dragon_shadow_wing.png` (1249×617) | **胴体・翼 分離** | ✅ v0.36.1 で移行（描き直し） |
| 緋竜 | `dragon_crimson_body.png` (370×882) ＋ `dragon_crimson_wing.png` (1327×707) | **胴体・翼 分離** | ✅ v0.36.2 で専用画像を作成 |
| 隼竜・燕竜・蜂竜・ガーゴイル | なし | ベクター描画＋専用パレット | ⚠️ 専用画像を作る |
| 敵（mover）全般 | 各1枚 | 一体画像＋`ENEMY_SPRITE_META` | 現状維持（§4-G） |

**竜はすべて分離方式になったので `DRAGON_IMAGE_SOURCES` は空**。一体画像の描画パスは
「翼を羽ばたかせない竜種を1枚絵で足したくなったとき」用のフォールバックとして残してある。

### なぜ分離するのか

一体画像に羽ばたきをつけると、`scale(flapFactor, 1)` が**画像全体**にかかるため
**胴体まで横方向に伸縮する**（＝呼吸するように太さが変わって不自然）。
火竜はこれを避けるために胴体と翼を分け、**翼のスパン軸にだけ**伸縮をかけている。
氷竜・影竜も v0.36 で同じ方式に揃えた（描き直し）。

**実行時コストは増えない**：パーツ合成は起動時のプリレンダ（`buildElementSprites`）で行い、
毎フレームは合成済みcanvasを1枚 `drawImage` するだけ。分割数が増えてもフレーム負荷は同じ。

---

## 2. 標準仕様（カテゴリA・有翼竜）— 火竜方式

### 2-0. ★wingAnchor は「手首」ではなく「翼の内側端」（v0.36 で修正）

**最初にここを間違えた。** 手首の関節をアンカーにすると、翼画像には関節より内側（肩側）に
スパンの約30%の膜があるため、それが**背中を越えて反対側まで被る**
（火竜で中心線を6.6論理px、氷竜で5.1論理px 越えていた）。
ゲーム内では小さいので長期間気づかず、拡大して初めて分かった。

- アンカーは**翼画像の内側端（肩側の付け根）**に置く。翼はそこから外へ広がる。
- 内側端は機械的に求められる：**右から走査して「厚み30px以上」になる最初の列**
  （細い残渣を拾わないための閾値）。
- **描画順は 翼 → 胴体**。逆だと翼が背中を覆ってシルエットが読めない。
- 折り畳み（flapFactor）もこのアンカー基準になるので、畳むと**胴体側へ縮む**（正しい挙動）。

**アンカーと肩の位置は画像ごとに違う**（生成物は毎回同じにならない）ので、
必ず竜種ごとに値を持つ。目安として、既存3種は
「肩オフセット ≒ 3.5論理px」「肩は重心より約3.6論理px 前方」「wingDrawW = 30」で揃えてある。
仕上がりの目安は**翼幅 / 体長 ≒ 1.9〜2.0**。

### 2-1. 用意する画像は2枚

| ファイル | 内容 | 向き・構図 |
|---|---|---|
| `dragon_<species>_body.png` | 胴体＋頭＋脚。**翼は含めない** | **鼻先が画像の上（−Y）**。左右対称 |
| `dragon_<species>_wing.png` | **片翼のみ**（右翼は水平反転で使う） | 付け根が画像の**右上**、翼端が左下へ広がる |

**尻尾は描かない。** 尻尾はコード側が毎フレーム動的に描く（`drawBoids` の緩和チェーン）。
胴体画像に長い尻尾が入っていると二重に見える。火竜も**ごく短いスタブ**しか持っていない。

### 2-2. コードに登録するメタデータ

**v0.35.2 で `DRAGON_PART_SPRITES` に一本化した**（旧 `DRAGON_FIRE_*` 定数は廃止）。
竜種を足すときはこのテーブルに1エントリ追加するだけでよい。

```js
const DRAGON_PART_SPRITES = {
  fire: {
    body: "assets/dragon_fire_body.png",
    wing: "assets/dragon_fire_wing.png",
    bodyPivot:  { cx: 164.6, cy: 545.3, w: 613, h: 1138 },  // アルファ質量重心
    shoulder:   { left: { x: 39.6, y: 425 }, right: { x: 289.6, y: 425 } },  // cx ±125
    wingAnchor: { x: 1268, y: 387 },                         // **翼の内側端**（§2-0）
    bodyDrawH: 27,   // 胴体の描画高さ（論理px、鼻〜脚）
    wingDrawW: 30,   // 翼の描画幅（論理px、スパン方向）
  },
};
// 別属性の絵を流用する場合（緋竜は火竜の絵を赤ティント）
const DRAGON_PARTS_ALIAS = { crimson: "fire" };
```

描画方式は **属性ごとに** 決まる（`renderDragonFrame`）：
**分離方式**（`DRAGON_PART_SPRITES` に登録＋画像が揃っている）→ **一体画像**（`dragonImages`）→ **ベクター**。
v0.35.2 以前はグローバルな `dragonImagesLoaded` で全属性まとめて判定していたため、
**1枚欠けると全竜種がベクターに落ちていた**。今は欠けた竜種だけが落ちる。

**ピボットは必ず画像中心ではなくアルファ質量重心**を使う。
竜の画像は翼と頭に質量が集中し脚側が空白なので、中心を軸にすると
回転時に頭が進行方向を向かず**脚側が前に来て破綻する**（実証済み）。

### 2-3. 測り方

`alpha > 30` の非透明ピクセルの x, y 平均を取る（`/gen-game-asset` §4 と同じ）。
肩アンカーは実測できないので、**胴体シルエットが最も横に張り出す行**を目視で選び、
プレビューで翼の付き位置を見ながら微調整する。

### 2-4. 羽ばたきの与え方

```
flapFactor = 0.4 + 0.6 * cos(wingAngle)      // 0.13〜1.0、常に正（反転しない）
左翼: translate(肩) → scale(flapFactor, 1) → drawImage(翼)
右翼: translate(肩) → scale(-flapFactor, 1) → drawImage(翼)   // 水平反転
胴体: スケールをかけない（固定サイズ）
```

---

## 3. 生成プロンプトの型（竜のパーツ）

`/gen-game-asset` の定型に、竜パーツ固有の指定を足す。**ASCIIのみ**で書くこと。

共通（両パーツ）:
```
Top-down view seen from directly above.
Flat cel-shaded illustration style, bold clean silhouette, thick dark ink outlines,
high contrast, no painterly texture.
Solid flat pure green background (#00FF00) for chroma key removal,
no ground, no shadow, no other objects.
Perfectly centered and symmetric, comfortable green margin on all sides.
```

胴体（body）に足す:
```
Dragon body and head only, seen from directly above, snout pointing toward the TOP of the image.
NO WINGS. NO TAIL - the body ends just behind the hind legs with only a tiny tail stub.
Bilaterally symmetric along the vertical axis.
```

翼（wing）に足す ― **氷竜・影竜で実際に通った版**（単純に「片翼」と言うだけでは
二枚翼や左右対称のコピーが出る。胴体が画面外にある想定を明示するのが効く）:
```
ONE single dragon wing, isolated, ENTIRELY INSIDE the frame.
Nothing touches the image edges - leave a comfortable green margin on ALL FOUR sides.
Composition: the shoulder end of the wing is in the RIGHT THIRD of the image,
the wrist knuckle is in the UPPER RIGHT area, and from there the outer wing sweeps
LEFTWARD with the wing tip ending before the LEFT EDGE.
Only ONE wing. Do NOT draw a second wing. Do NOT draw a mirrored copy.
No body, no head, no neck, no tail, no legs.
Bat-like membrane fully spread with long finger bones fanning out
and a scalloped trailing edge along the bottom.
```
アスペクトは翼が `16:9`、胴体が `1:1`。

- **除外指定は1回で通らないことがある**（尻尾・翼が勝手に付く）。結果を見て言い換えて再生成する。
- **体格を盛る指定は控える。** 緋竜で「heavily muscled / thick forelimbs / claws spread outward」と
  書いたら**人型のボディビルダー**が出てきて他3種と画風が揃わなかった。
  「compact reptilian silhouette」「NOT humanoid and NOT bodybuilder muscular」を明示して作り直した。
  前脚を大きく横へ張り出させると**翼の付け根と干渉**するので構図としても不利。
  氷竜の翼は**3回目で通った**（1回目=二枚翼、2回目=右端が切れる、3回目=OK）。
  影竜はこの版で**1回で通った**。
- 生成後は必ず**市松合成での縁チェック**と**アルファ検証**（`/gen-game-asset` §4）。

---

## 4. パーツ分割カテゴリ

**キャラの種類ごとに分割の型を決める。** 新キャラを作るときはまずこの表でカテゴリを選ぶ。

| | カテゴリ | 画像 | メタデータ | 動かし方 | 該当 |
|---|---|---|---|---|---|
| **A** | **有翼竜・標準** | body ＋ wing×1 | bodyPivot / shoulder / wingAnchor / drawサイズ | 翼のスパン軸を伸縮（§2-4） | 火竜・氷竜・影竜・緋竜・隼竜・燕竜・鶴竜・鮫竜・雷雲竜 |
| **B** | **有翼・小型高速** | body ＋ wing×1（翼を小さく） | A と同じ ＋ **羽ばたき周期を種別化** | 振幅を抑え周期を速く（虫の羽音感） | 蜂竜 |
| **C** | **硬質・非羽ばたき** | body ＋ wing×1（石の翼） | A と同じ ＋ `flap: "rigid"` | **伸縮させず**、翼角度をゆっくり小さく往復 | ガーゴイル |
| **D** | **無翼・浮遊単体** | body 1枚（＋任意で glow/ring 1枚） | pivot ＋ `forward: "none"` | 羽ばたき無し。UFO=自転／鬼火=明滅・上下動 | UFO・鬼火 |
| **E** | **多パーツ大型** | core ＋ 付属パーツ×N（腕・ヒレ・甲羅） | パーツごとに pivot＋軌道パラメータ | パーツが独立に動く（既存 `updateBehemothArm` が前例） | 鯨竜・亀竜／敵の巨獣 |
| **F** | **長胴・節連結** | head ＋ segment（繰り返し）＋ tail | 節数・節間距離・遅延係数 | 節が前の節を遅延追従（既存の尻尾チェーンを胴体へ拡張） | 蛇竜 |
| **G** | **敵・一体画像** | 1枚 | `ENEMY_SPRITE_META`（px/py/forward/drawScale/hover） | 回転のみ。羽ばたき分離しない | 敵 mover 全般 |

### カテゴリ選択の基準

- **翼を羽ばたかせるか** → する＝A/B/C、しない＝D
- **翼の素材が撓むか** → 撓む＝A/B、撓まない（石・金属）＝C
- **パーツが独立して動くか** → する＝E
- **胴が長く波打つか** → する＝F
- **味方（竜種）か敵か** → 敵は G のままでよい（羽ばたきを要求されないので1枚で足りる）

### カテゴリ別の生成メモ

- **B（蜂竜）**：翼は透けた小さい膜。`DRAGON_FLAP_SPEED` を種別化して速く回す。
  現状 `DRAGON_FLAP_SPEED` はグローバル定数なので、**種別化はコード変更が必要**。
- **C（ガーゴイル）**：石なので膜を持たない。翼は板状に描き、`flapFactor` を固定（=1）にして
  代わりに翼の**回転角**を小さく揺らす。撓ませると石に見えない。
- **D（UFO）**：`forward: "none"`＝進行方向へ回転させない（円盤は常に同じ向き）。
  自転は別に角度を足す。牽引光線の緑円柱は**コード側の描画**なので画像に含めない。
- **D（鬼火）**：芯＋外側のぼんやりした光を**別レイヤー**にすると、外側だけ明滅させられる。
- **E（鯨竜・亀竜）**：巨体は1枚だと回転時の破綻が目立つ。コア＋ヒレ/脚を分けて
  ゆっくり位相差で動かすと「重い生き物」に見える。
- **F（蛇竜）**：胴節は**1枚を使い回す**（節ごとに画像を作らない）。頭と尾だけ専用。

---

## 5. 命名規則と登録手順

```
prototypes/dragon-tide/assets/
  dragon_<species>_body.png     A/B/C: 胴体
  dragon_<species>_wing.png     A/B/C: 片翼
  dragon_<species>.png          D: 単体（無翼）
  dragon_<species>_glow.png     D: 任意の発光レイヤー
  dragon_<species>_core.png     E: コア
  dragon_<species>_<part>.png   E: 付属パーツ（arm / fin / shell …）
  dragon_<species>_head/seg/tail.png   F: 長胴
```

`<species>` は `SPECIES_DEFS` のキー（`fire` `ice` `falcon` `gargoyle` …）に合わせる。

登録手順:
1. `assets/` に置く
2. `DRAGON_PART_SPRITES` に1エントリ追加（分離方式）。一体画像で足すなら `DRAGON_IMAGE_SOURCES`
3. ピボット・アンカー・描画サイズを実測して定数に登録
4. プレビューで**ピクセル解析**して確認（不透明px数・平均色・左右対称性）
5. `/deploy-dragon-tide`

**アセットを差し替えたら URL に `?v=N` を付けてキャッシュを切る**
（`building_ruin.png?v=2` が前例。古い画像が残って表示される事故を防ぐ）。

---

## 6. 作業順の推奨

1. ~~**氷竜・影竜を分離方式へ移行**~~ → ✅ **v0.36.0 / v0.36.1 で完了**（どちらも描き直し）。
   A方式の型と計測手順（§2-0）はここで確立した。
2. ~~**緋竜の専用画像**~~ → ✅ **v0.36.2 で完了**（赤ティント合成と `DRAGON_PARTS_ALIAS` を撤去）
3. **隼竜・燕竜**（A方式）→ **蜂竜**（B）→ **ガーゴイル**（C）。v0.35 で挙動は入っているので絵だけ差し替わる。 ← **次はここ**
4. UFO・鬼火（D）は挙動の実装と同時。
5. E・F は該当竜種を作るときに。

**1と2で A方式の型が固まるまで、新カテゴリ（B〜F）には手を出さない。**
先に型を確立しないと、同じ調整を何度もやり直すことになる。

---

## 7. 既知の落とし穴

- ~~`data/balance/dragon-sprite-pivots.json` との二重管理~~ → ✅ **v0.35.1 で解消**。
  JSON を削除し、**`index.html` 内の定数を正典に一本化**した。
  経緯：プロトは `fetch`/`XHR` を持たない（単一HTMLで `file://` でも動く構成）ので
  誰も JSON を読めず、読まれないので値がずれても検出されず、実際に `fire` の値が
  旧一体画像 1024×917 のまま腐っていた。
  **ピボットはバランス値ではなく「特定PNGの測定値」**で、変わるのは画像を差し替えるときだけ。
  差し替えれば画像ソース登録や描画サイズでどうせコードを触るので、`data/` へ外出しする旨みが無い。
  → 新しい竜種のピボットも**コード内の定数として追加する**（JSON を復活させない）。
  ※`data/balance/dragon-tide.json`（ステージ・バランス値）は**残す**。あちらは
  　system-designer が GDD を参照して書いた設計意図の記録として文書価値がある。
- **画像中心をピボットにしてはいけない**（§2-2）。回転が破綻する。
- **尻尾を描かせない**。プロンプトで明示しても付いてくることがあるので、
  `chroma_key.py --crop-bottom-frac` で落とすか再生成する。
- **フレーム端に接した絵は切れる**。プロンプトに緑マージンの指定を必ず入れる。
- **プロンプトは ASCII のみ**（cp932 で UnicodeEncodeError）。
- 縁の緑ハローは市松合成で目視確認。確認用 `_check_*.jpg` は**必ず削除**する。
- 竜のプリレンダは1種あたり16コマ≒672KB。`spriteCache`（上限3種）で回しているので
  **種類を増やしてもメモリは増えない**が、上限を上げるときはここを見直す。
