# Dragon Tide メタ進行 設計（買い切りアプリ化）

対象コード: `prototypes/dragon-tide/index.html`
この文書は**維持管理する設計ドキュメント**（`snapshots/` の使い捨てとは別）。最新実装は必ずコードを正とする。

## 目的
「1回遊んで終わり」を超える動機付け＝メタループを確立する。ランをまたいで貯まる
永続進行（恒常強化ツリー・チャレンジ・母竜育成）を軸に、買い切りアプリとしての反復価値を作る。

## 全体像とフェーズ状況
- **Phase 0（済 / v0.19.0）**: 永続プロファイル基盤。localStorage を `dragonTide_profile`（永続メタ）と `dragonTide_run`（再開）に再編。
- **Phase 1（済 / v0.19.x）**: ラン開始フロー再設計（初回=火竜即開始10体／2回目以降=竜種選択・毎ステージ基本1体）＋ステージクリアごとのオートセーブ＋つづきから。
- **Phase 2（済 / v0.20.0）**: 恒常強化ツリー（竜晶で購入・全ノード ON/OFF）。← この文書の主対象。
- **Phase 3（未）**: 母竜強化＋母竜専用ブレス。**ラン中の強化が主軸**（レベルアップ強化で伸ばし進化で枝分かれ）、ツリーは解禁・初期技・下限強化の土台。
- **Phase 4（未）**: チャレンジ／コンプ要素と報酬（竜晶＋特定チャレンジによる特別解放の併用）。

## 確定した設計判断（ユーザー合意）
- 経済: メタ通貨「**竜晶**」購入 ＋ 特定チャレンジの特別解放の併用。
- 竜種: 2回目以降は最初から4種すべて選択可。
- 母竜ブレス: ラン中強化が主軸／ツリーは土台（Phase 3）。
- ツリー ON/OFF: プレイヤーの自由調整用（縛り・実験・実績狙い）。
- 敗北要素なし（据え置き）。初期1体は難度ではなく積み上げ体験＋ツリーで底上げ。

---

## Phase 2: 恒常強化ツリー（v0.20.0 実装）

### 竜晶（crystals）の獲得
- **ステージクリアごと**に付与: `crystalsForStageClear(stageIdx) = CRYSTAL_STAGE_BASE(6) + CRYSTAL_STAGE_STEP(3) × stageIdx`
  - stage1クリア=6, stage2=9, … stage8=27。全8ステージ通しで合計 ≈ 132。
- **全クリアボーナス**: `CRYSTAL_ALLCLEAR_BONUS = 40` を最終ステージぶんに加算。
- 付与は `awardCrystals(n)` を通し、ツリーの `crystalGain` 倍率が掛かる。付与のたびに `saveProfile()`。
- 付与フック: `advanceToNextStage`（直前ステージぶん）／ `triggerAllClear`（最終＋ボーナス）。オートセーブと同経路なので二重付与しない（再開の `setupStageForResume` では付与しない）。

### 適用のしくみ（permaBuff）
- `profile.tree[nodeId] = { unlocked, enabled }`。unlocked=購入済み／特別解放、enabled=トグル。
- `recomputePermaBuff()` が「unlocked かつ enabled」なノード効果を集計して `permaBuff` を作る。
- `permaBuff` は `eff*` 各関数と `stageStartFlockCount()` の戻り値に**乗算/加算で合流**（ラン内 `upgradeCounts` とは独立、ステージリセットで消えない）。
- 再計算タイミング: 起動時（`boot`）、ツリー編集時（購入・トグル）、プロファイル初期化時。

### ノード一覧（v0.20.0 初版・9ノード）
`effect.type` は `permaBuff` のフィールド。startFlock/flockCap=加算、他=乗算。

| id | カテゴリ | 名前 | 効果 | cost | 前提 |
|---|---|---|---|---|---|
| flock_start1 | 群れ | 始祖の群れ | 各ステージ開始の竜 +1 | 40 | — |
| flock_start2 | 群れ | 殖える始まり | 各ステージ開始の竜 +1 | 120 | flock_start1 |
| flock_hp | 群れ | 硬鱗の血脈 | 竜HP +15% | 50 | — |
| flock_cap | 群れ | 大群の器 | 群れ上限 +20 | 100 | flock_hp |
| pow_dmg1 | 火力 | 猛る吐息 | 武器威力 +12% | 50 | — |
| pow_dmg2 | 火力 | 業火の系譜 | 武器威力 +15% | 140 | pow_dmg1 |
| pow_speed | 火力 | 疾風の翼 | 群れ速度 +10% | 45 | — |
| eco_magnet | 探索・経済 | 宝玉の磁力 | XP吸引 +30% | 40 | — |
| eco_gain | 探索・経済 | 竜晶の嗅覚 | 竜晶獲得 +25% | 70 | — |

- 数値・ノード構成は初版。プレイテストで `system-designer` が調整する前提。将来ノードは
  `TREE_DEFS` に追記し、必要なら `permaBuff` にフィールドと `recomputePermaBuff` の分岐を足す。
- 一部ノードを `unlockBy: challengeId`（購入不可・特別解放）にする枠は Phase 4 で追加予定。

### UI
- タイトルメニューの「強化ツリー 🔷N」から `openTree()`。全画面オーバーレイ（z-index 55、タイトル z50 の上）。
- カテゴリ別カラム（群れ／火力／探索・経済）。ノードをタップ: 未所持かつ購入可→購入、所持→ON/OFF、前提未達→ロック。
- 実装: `renderTree()`（innerHTML 動的生成）。CSS は `#tree-overlay` 系。

### 検証済み（v0.20.0）
- 購入で竜晶減・前提解禁・前提未達ロック・ON/OFF・`eff*`/`stageStartFlockCount` 反映・localStorage 永続化。
- ステージクリアでの竜晶付与、`crystalGain` 倍率、タイトル残高表示、画面開閉。

---

## デバッグ（v0.19.2〜）
左下バージョン3タップでデバッグパネル。竜晶+100・全クリア（clears/報酬フロー）・プロファイル初期化などで
メタ進行を検証できる。詳細は `prototypes/dragon-tide/snapshots/debug-features_v0.19.2_*.md`。

## 次の作業（Phase 3 / 4）
- Phase 3: `MOTHER_DRAGON.hpMult/dmgMult` 実体化、`updateMotherBreath()` 新設、母竜ブレスのラン中強化カード群、ツリーに母竜ブレス解禁/初期技/下限ノード。
- Phase 4: `CHALLENGE_DEFS`、進捗トラッキング、チャレンジ一覧UI、報酬（竜晶＋特別解放）、コンプ率。
