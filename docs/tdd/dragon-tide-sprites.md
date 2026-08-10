# Dragon Tide — スプライト生成方針とパーツ分割カテゴリ

- 作成: 2026-08-10 ／ 対象コード: `prototypes/dragon-tide/index.html`（**v0.35.0** 時点）
- 目的：**竜種ごとに専用アセットを1つ持つ**（[dragon-tide-species.md](../gdd/dragon-tide-species.md) §4）方針のもと、
  「どのキャラをどう分割して作るか」を決める。
- 生成の共通手順は `/gen-game-asset`（`.claude/commands/`）と `C:\forge\ClaudeCodeForge` が正。
  本書は**Dragon Tide 固有の分割・座標仕様**を扱う。

---

## 1. 現状

| 対象 | 画像 | 方式 | 状態 |
|---|---|---|---|
| 火竜 | `dragon_fire_body.png` (613×1138) ＋ `dragon_fire_wing.png` (1376×768) | **胴体・翼 分離** | ✅ お手本 |
| 氷竜 | `dragon_ice.png` (1010×791) | 一体画像＋全体スケール | ⚠️ **分離へ移行する** |
| 影竜 | `dragon_shadow.png` (982×532) | 一体画像＋全体スケール | ⚠️ **分離へ移行する** |
| 緋竜 | なし（火竜画像の赤ティント流用） | — | ⚠️ 専用画像を作る |
| 隼竜・燕竜・蜂竜・ガーゴイル | なし | ベクター描画＋専用パレット | ⚠️ 専用画像を作る |
| 敵（mover）全般 | 各1枚 | 一体画像＋`ENEMY_SPRITE_META` | 現状維持（§4-G） |

### なぜ分離するのか

一体画像に羽ばたきをつけると、`scale(flapFactor, 1)` が**画像全体**にかかるため
**胴体まで横方向に伸縮する**（＝呼吸するように太さが変わって不自然）。
火竜はこれを避けるために胴体と翼を分け、**翼のスパン軸にだけ**伸縮をかけている。
氷竜・影竜は旧方式のまま残っているので、火竜と同じ方式に揃える。

**実行時コストは増えない**：パーツ合成は起動時のプリレンダ（`buildElementSprites`）で行い、
毎フレームは合成済みcanvasを1枚 `drawImage` するだけ。分割数が増えてもフレーム負荷は同じ。

---

## 2. 標準仕様（カテゴリA・有翼竜）— 火竜方式

### 2-1. 用意する画像は2枚

| ファイル | 内容 | 向き・構図 |
|---|---|---|
| `dragon_<species>_body.png` | 胴体＋頭＋脚。**翼は含めない** | **鼻先が画像の上（−Y）**。左右対称 |
| `dragon_<species>_wing.png` | **片翼のみ**（右翼は水平反転で使う） | 付け根が画像の**右上**、翼端が左下へ広がる |

**尻尾は描かない。** 尻尾はコード側が毎フレーム動的に描く（`drawBoids` の緩和チェーン）。
胴体画像に長い尻尾が入っていると二重に見える。火竜も**ごく短いスタブ**しか持っていない。

### 2-2. コードに登録するメタデータ

火竜の実値（`prototypes/dragon-tide/index.html`）が雛形：

```js
// 胴体：回転ピボット＝アルファ質量重心（画像中心ではない）
const DRAGON_FIRE_BODY_PIVOT = { cx: 164.6, cy: 545.3, w: 613, h: 1138 };
// 肩（翼の付け根）の胴体画像座標。左右対称中心は cx と一致させる
const DRAGON_FIRE_SHOULDER   = { left: { x: 30, y: 420 }, right: { x: 298, y: 420 } };
// 翼：骨が収束する付け根（フック状の部分）
const DRAGON_FIRE_WING_ANCHOR = { x: 855, y: 130 };
// 描画サイズ（論理px）
const DRAGON_FIRE_BODY_DRAW_H = 27;   // 胴体の高さ（鼻〜脚）
const DRAGON_FIRE_WING_DRAW_W = 26;   // 翼の幅（スパン方向）
```

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

翼（wing）に足す:
```
A SINGLE dragon wing only, no body, no head.
The wing root (where the bones converge) is at the UPPER RIGHT of the image,
the wing tip spreads toward the LOWER LEFT.
Membrane fully spread, seen from directly above.
```

- **除外指定は1回で通らないことがある**（尻尾・翼が勝手に付く）。結果を見て言い換えて再生成する。
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
2. 画像ソース定義に追加（現状は `DRAGON_IMAGE_SOURCES` / `DRAGON_FIRE_IMAGE_SOURCES` に分かれている）
3. ピボット・アンカー・描画サイズを実測して定数に登録
4. プレビューで**ピクセル解析**して確認（不透明px数・平均色・左右対称性）
5. `/deploy-dragon-tide`

**アセットを差し替えたら URL に `?v=N` を付けてキャッシュを切る**
（`building_ruin.png?v=2` が前例。古い画像が残って表示される事故を防ぐ）。

---

## 6. 作業順の推奨

1. **氷竜・影竜を分離方式へ移行**（既に画像があるので、翼を切り出すか描き直すだけ）。
   ここで「A方式を2種類目・3種類目に適用する」流れが固まる。
2. **緋竜の専用画像**（今は火竜の赤ティント）。A方式。
3. **隼竜・燕竜**（A方式）→ **蜂竜**（B）→ **ガーゴイル**（C）。v0.35 で挙動は入っているので絵だけ差し替わる。
4. UFO・鬼火（D）は挙動の実装と同時。
5. E・F は該当竜種を作るときに。

**1と2で A方式の型が固まるまで、新カテゴリ（B〜F）には手を出さない。**
先に型を確立しないと、同じ調整を何度もやり直すことになる。

---

## 7. 既知の落とし穴

- **`data/balance/dragon-sprite-pivots.json` の `fire` エントリは古い**
  （旧一体画像 1024×917 の値。現行コードは分離後の `DRAGON_FIRE_BODY_PIVOT` を使う）。
  分離方式へ移行するとき、この JSON を**パーツ単位の構造に作り直す**こと。
  現状コードは「data/ を配信しない」ため値をインラインに複製している＝**二重管理**。
  どちらかに寄せる判断が要る（ADR候補）。
- **画像中心をピボットにしてはいけない**（§2-2）。回転が破綻する。
- **尻尾を描かせない**。プロンプトで明示しても付いてくることがあるので、
  `chroma_key.py --crop-bottom-frac` で落とすか再生成する。
- **フレーム端に接した絵は切れる**。プロンプトに緑マージンの指定を必ず入れる。
- **プロンプトは ASCII のみ**（cp932 で UnicodeEncodeError）。
- 縁の緑ハローは市松合成で目視確認。確認用 `_check_*.jpg` は**必ず削除**する。
- 竜のプリレンダは1種あたり16コマ≒672KB。`spriteCache`（上限3種）で回しているので
  **種類を増やしてもメモリは増えない**が、上限を上げるときはここを見直す。
