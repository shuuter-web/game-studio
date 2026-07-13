# Dragon Tide — 要素名リファレンス（v0.15.0時点）

> **世界観**: 竜たちは「たくさんの卵を奪って町に持ち帰った人間」に怒って襲撃している。
> 町が卵を落とす＝奪われた卵の奪還（v0.15設定、Shooter指示）。
> **デザイン3本柱**: アクアリウム（見て楽しい・世界と竜の関係）× 塊魂（成長して攻略）×
> Balatro（竜種でプレイ感が変わる）。敗北要素なし・音は当面後回し。

`prototypes/dragon-tide/index.html` の現在の実装から拾った要素名の一覧。
今後「◯◯を追加/調整して」と指示する際に、コード上の識別子を指し示すための資料。
実装が変わったら都度更新すること。

---

## 1. ドラゴンの武器タイプ / 属性

群れ全体が★進化で単一の武器タイプに100%転換する（複数種混在ではない）。

| weapon(内部名) | element(見た目) | 呼称 | 特徴 |
|---|---|---|---|
| `beam` | `fire` | 🔥 火竜（初期） | 持続ビーム。射程80 / dps 3.0 |
| `bullet` | `ice` | ❄️ 氷竜 | 直進弾丸。射程220 / 速度400 / 威力6 / 間隔1.2s |
| `missile` | `shadow` | 🌑 影竜 | 加速ホーミング。威力15 / 加速600 / 爆発範囲30 |
| `melee` | `crimson`（緋竜） | 🐾 緋竜 | 体当たり特化。衝突ダメ25（通常の約3倍）/ 個体HP+50% |

- 配色定義: `DRAGON_ELEMENT_COLORS`（index.html:8084）
- 武器→属性: `WEAPON_ELEMENT`（index.html:5597） / HUD表示: `WEAPON_HUD`（5600）
- ★進化カード: `evo_bullet` / `evo_missile` / `evo_melee` ＋ `stay_fire`（`CARD_STAY_FIRE`） —
  **v0.14: ランの最初のレベルアップでのみ「火竜を続ける＋進化3種」の4択を提示
  （他の強化は混ざらない）。選択後は二度と出ない**
  （フラグ `evolutionChosen`、resetProgressionでリセット）
- 画像: `DRAGON_IMAGE_SOURCES`（ice/shadow, 8120） / `DRAGON_FIRE_IMAGE_SOURCES`（fireのみbody/wing分離, 8126）

---

## 2. 移動体（mover）— `MOVER_DEFS`（index.html:2249）

時代モチーフの「動く要塞」。

| 内部名 | 時代 | 呼称 | hp | speed | xp | attack | 特徴 |
|---|---|---|---|---|---|---|---|
| `mammoth` | 石器 | マンモス | 45×3体 | 38 | 35×3 | `shockwave`（押し飛ばし、範囲90） | **packCount:3**（3頭の群れで湧く）、pingpong移動 |
| `colossus` | 古代 | コロッサス | 250 | 26 | 160 | `beam`（dps5.0） | patrol移動、`hover:true` |
| `knights` | 中世 | 騎士 | 24×8体 | 48 | 17×8 | `fan`（単発矢、間隔1.6s） | **packCount:8**（8体の隊で湧く）、pingpong移動 |
| `ironclad` | 近世 | 陸上甲鉄艦 | 400 | 30 | 240 | `broadside`（3連砲×2方向） | loop移動、最硬 |
| `balloon` | 近世 | 爆撃気球 | 150 | 24 | 200 | `bomb`（AoE、範囲44） | `flying:true`（地形無視） |
| `raider` | — | レイダー | 25 | 82 | 15 | `fan`（単発） | ボス城塞湧きの小型追撃兵、eggChance 0.2 |

- ステージ別出現構成: `MOVER_SPAWNS_BY_STAGE`（2291）
- **v0.15: HP/XPのステージスケールは全廃**（種類固定値）。代わりに攻撃の苛烈さ
  `moverStageFerocity()`=1+0.20×stage が攻撃間隔の短縮とビームDPSに乗る
  （目に見える脅威で強化を表現。ボスHPのみ `calcBossHp` のスケール存続）
- 索敵/交戦距離: `MOVER_PURSUIT_RANGE`=650 / `MOVER_ENGAGE_RANGE`=450
- 画像: `ENEMY_IMAGE_SOURCES`（8135） / 描画メタ: `ENEMY_SPRITE_META`（8166）

**v0.13 pack（群れ）システム:**
- `packCount` 持ちの敵（mammoth=3 / knights=8）は**個別の敵エンティティ**として頭数分湧く
  （v0.12の「1体を隊列描画」は剛体回転で外周が滑る違和感があったため廃止）
- 同一packは経路（`waypoints`）を共有し、`speedMult`（±8%の歩調ゆらぎ）で追い越し・遅れが出る
- はぐれ個体は群れ重心へ引き戻し（`PACK_COHESION_DIST`=160）、
  重なりは相互押し出しで防止（`PACK_SEPARATION_GAP`=6）— いずれも updateMovers 内
- pack個体のHPバーは**被弾時のみ表示**（常時表示だとバーだらけになるため）
- pack採番: `nextPackId` / hp・xp・卵は1体あたりに分割済み（合計は旧値とほぼ同等）
- 単体スプライト: `mover_mammoth_single.png` / `mover_knight_single.png`（旧一枚絵は不使用）

---

## 3. 建物 — `BUILDING_SIZE_PARAMS`（index.html:470）

| 内部名(size) | hp範囲 | radiusBase | 備考 |
|---|---|---|---|
| `tiny` | 3〜6 | 6 | 極小集落。ハムレット単位でクラスタ配置 |
| `small` | 6〜10 | 10 | 育成フィーダー。すぐ壊れて卵が出る |
| `medium` | 25〜35 | 16 | 中型 |
| `large` | 60〜85 | 28 | 大型（領主館・聖堂等） |
| `boss` | — | 46（`BOSS_RADIUS`） | `BOSS_PARAMS`系で個別管理 |
| `wall` | ステージ別 | 26（`WALL_SEG_RADIUS`） | 城壁セグメント |

**特殊フラグ:**
- `_landmark: "temple" | "windmill"`（1299）— 町の広場中央、large級HP×1.3、町ごとに交互配置
- `_isCapital`（首都要塞建物、`makeCapitalBuilding` 2095、HP=large×`CAPITAL_HP_MULT`1.30）
- `_isCapitalSmall`（城下雑魚建物、`makeCapitalSmallBuilding` 2119）
- `_isWall`（城壁セグメント、`makeWallSegment` 2163、XP固定12）
- `isEggBearer`（陥落時に卵`EGG_DROP_COUNT`=1個ドロップ）
- `fallen`（陥落済み、廃墟スプライト `assets/building_ruin.png`）

画像: `BUILDING_IMAGE_SOURCES`（8146）= small/medium/large/ruin/temple/windmill/bridge
城壁設定: `WALL_STAGE_CONFIG`（2145、ステージ4以降 `doubleRing`二重リング）

---

## 4. ボス

現状1種類（`citadel`）、ステージごとにテーマカラーのみ変化。

- `size:"boss"` / `shape:"bossCircle"` / 画像 `assets/boss_citadel.png`
- 生成: `makeBossBuilding()`（1651） / HP: `calcBossHp = 600 × 1.4^stageIndex`
- `BOSS_RADIUS`=46 / `BOSS_ATTACK_RADIUS`=380
- 攻撃: 反発衝撃波（`BOSS_NOVA_INTERVAL`6.0s毎, 範囲260, ダメ2.5）、跳ね返し弾（`BOSS_SHOT_KNOCKBACK_DIST`46）
- テーマ: `STAGE_CONFIGS[i].boss`（color/glowColor/projectileColor）
- **v0.12 リング回転**: 城塞画像をロード時に同心円4層（外壁3リング＋コア）へ分解し
  互い違いにゆっくり回転させる（`buildBossRingLayers` / `bossRingLayers` / `BOSS_RING_SPEEDS`）。
  リング境界はアルファの半径プロファイルから自動検出（閾値 `BOSS_RING_GAP_ALPHA`=130）。
  分解失敗時は従来の一枚絵描画に自動フォールバック

---

## 5. 地形・地面

| 内部名 | 説明 |
|---|---|
| `riverPolyline` / `riverWidth` | 川（`generateRiver()` 1877）。幅48〜70のランダム |
| `bridgePlacements` / `computeBridges()` | 街道×川の交点に架橋（1909）、画像 `assets/bridge.png` |
| `townRoadEdges` | 町間の道路網（`buildTownRoadNetwork()` 1845） |
| `streets`（`_townMeta.streets`） | 町内の放射状の通り（1277） |
| `fields`（`_townMeta.fields`） | 農地。街道沿いに3〜6件配置（1372） |
| `GROUND_TILE_SOURCE` | 地面テクスチャ `assets/ground_tile.jpg`（低コントラストで敷く） |
| `WORLD_W` / `WORLD_H` | ワールド全体サイズ |
| `PLAZA_R` / `RING_R` / `townR` | 町の広場半径・環状路半径・町全体半径 |

---

## 6. 進行系ステータス/パラメータ

| 変数名 | 用途 |
|---|---|
| `playerLevel` / `playerXp` | プレイヤーレベル・経験値（5197） |
| `xpForNext(level)` | 次Lv必要XP = `160 × 1.35^(min(level,10)-1)`。**v0.14: Lv10以降は2383で頭打ち**（`XP_LEVEL_CAP`） |
| （廃止）`moverStageXpMult` | v0.14で廃止。敵XPは種類固定（HPスケール `moverStageHpMult` は存続） |
| `pendingCards` / `upgradeCounts` | 未消化カード数 / カードid→取得回数 |
| `runKills` / `runMaxFlock` / `runTotalXp` / `runStartTime` | リザルト統計（5203） |
| `N`（現群れ数） | 初期`BOIDS_INITIAL`=10、上限`BASE_FLOCK_CAP`=100、配列上限`MAX_BOIDS`=150 |
| `boidHp[i]` / `BOID_MAX_HP`=30 | 個体HP（7発で撃破目安） |
| `boidDead[i]` / `boidDowned[i]` | 死亡/ダウンフラグ |
| `flockLeaderIdx` / `leaderBodyScale()` | v0.15: リーダー竜1匹だけレベルで体格成長（+7%/Lv、最大+70%。死亡時は生存個体へ引き継ぎ） |
| `settlement.hp` / `maxHp` | 建物HP |
| `flockWeapon` | 群れ全体の現在武器タイプ |
| `EGG_DROP_COUNT`=1 | 陥落建物の卵ドロップ数 |
| `xpValueOf(settlement)` | 撃破時XP（`_isWall`→12, `_isCapital`→30, 他サイズ別） |

---

## 7. その他の主要定数

| 定数名 | 内容 | 行 |
|---|---|---|
| `MOVER_DEFS` | mover種定義一式 | 2249 |
| `MOVER_SPAWNS_BY_STAGE` | ステージ別mover出現構成 | 2291 |
| `BUILDING_SIZE_PARAMS` | tiny/small/medium/largeのhp/radius | 470 |
| `STAGE_CONFIGS` | 全8ステージ定義（name/subtitle/bgColor/townBaseHues/buildings/boss/townCount等） | 585 |
| `DRAGON_ELEMENT_COLORS` | fire/ice/shadow/crimson配色 | 8084 |
| `WEAPON_ELEMENT` / `WEAPON_HUD` / `WEAPON_FLASH_COLOR` | 武器↔属性↔表示 | 5597, 5600, 5608 |
| `DRAGON_IMAGE_SOURCES` / `DRAGON_FIRE_IMAGE_SOURCES` | 竜画像アセット | 8120, 8126 |
| `ENEMY_IMAGE_SOURCES` / `ENEMY_SPRITE_META` | mover/boss画像・描画メタ | 8135, 8166 |
| `BUILDING_IMAGE_SOURCES` | 建物画像アセット | 8146 |
| `CARD_DEFS` / `CARD_ORB` / `CARD_RARITY_WEIGHT` | レベルアップ強化カード全定義 | 5212-5239 |
| `WALL_STAGE_CONFIG` | ステージ別城壁設定 | 2145 |
| `BOSS_FIRE_PARAMS` | ボス投射パラメータ | 562 |

**ステージ名（`STAGE_CONFIGS[].name`）:**
1. STONE AGE（石器時代） 2. ANCIENT ERA（古代文明） 3. MEDIEVAL AGE（中世） 4. MODERN FORTRESS（近世要塞）
5. INDUSTRIAL AGE（産業革命） 6. ELECTRIC AGE（電気時代） 7. GREAT WAR（大戦） 8. FINAL DOMINION（終末）
（行588, 651, 713, 771, 830, 888, 947, 1007）

---

## 主要定義ファイル位置まとめ

- ドラゴン武器/属性: `index.html:5587-5667`、スプライト・配色: `8084-8276`
- MOVER_DEFS: `index.html:2249-2287` / MOVER_SPAWNS_BY_STAGE: `2291-2299`
- BUILDING_SIZE_PARAMS: `index.html:470-479`
- STAGE_CONFIGS: `index.html:585〜1050`付近
- makeBuilding: `index.html:1403-1431`
- makeBossBuilding: `index.html:1651〜`
- makeCapitalBuilding / makeCapitalSmallBuilding: `index.html:2095-2128`
- makeWallSegment / WALL_STAGE_CONFIG: `index.html:2136-2180`
- 地形（川・橋・道路）: `index.html:1843〜1930`付近
- XP/レベル進行: `index.html:5190-5258`
- CARD_DEFS: `index.html:5212-5239`
- 画像アセットマッピング一式: `index.html:8100〜8280`
