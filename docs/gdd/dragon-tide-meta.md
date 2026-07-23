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

### ノード一覧（v0.22.0・5ライン18ノード）
`effect.type` は `permaBuff` のフィールド。startFlock/flockCap/motherBreath=加算、他=乗算。ライン＝母竜(mother)/大群(swarm)/不屈(resil)/統率(command)/恵み(bounty)。

| id | ライン | 名前 | 効果 | cost | 前提 |
|---|---|---|---|---|---|
| m_breath | 母竜 | 母なる吐息 | 母竜が周期的に特大ブレス（解禁） | 150 | — |
| m_dmg | 母竜 | 灼熱の母 | 母竜ブレス威力 +30% | 120 | m_breath |
| m_hp | 母竜 | 不朽の母 | 母竜のHP +50% | 100 | — |
| flock_start1 | 大群 | 始祖の群れ | 各ステージ開始の竜 +1 | 40 | — |
| flock_start2 | 大群 | 殖える始まり | 各ステージ開始の竜 +1 | 120 | flock_start1 |
| flock_cap | 大群 | 大群の器 | 群れ上限 +20 | 100 | flock_start1 |
| swarm_revive | 大群 | 早鳴きの潮 | ダウン復帰 -20% | 60 | — |
| pow_dmg1 | 大群 | 猛る吐息 | 武器威力 +12% | 50 | — |
| pow_dmg2 | 大群 | 業火の系譜 | 武器威力 +15% | 140 | pow_dmg1 |
| flock_hp | 不屈 | 硬鱗の血脈 | 竜HP +15% | 50 | — |
| resil_hp2 | 不屈 | 鋼鱗の覚醒 | 竜HP +15% | 130 | flock_hp |
| resil_tough | 不屈 | 竜鱗の共鳴 | 被ダメージ -12% | 90 | — |
| pow_speed | 統率 | 疾風の翼 | 群れ速度 +10% | 45 | — |
| cmd_speed2 | 統率 | 颶風の統率 | 群れ速度 +8% | 110 | pow_speed |
| cmd_reach | 統率 | 見晴らす眼 | 武器射程 +15% | 70 | — |
| eco_magnet | 恵み | 宝玉の磁力 | XP吸引 +30% | 40 | — |
| bounty_xp | 恵み | 成長の律動 | 獲得XP +20% | 80 | — |
| eco_gain | 恵み | 竜晶の嗅覚 | 竜晶獲得 +25% | 70 | — |

- v0.21 で追加した permaBuff フィールド：`reviveMult`（→`effReviveMult`）／`dmgTakenMult`（→`effDmgTakenMult`）／`weaponRange`（→`effWeaponRangeMult`）／`xpGain`（→`addXp` 入口で乗算）。いずれも既存 eff* ハブに合流。
- v0.28 初回ラン短縮：`runStageCount()`＝初回ランのみ `FIRST_RUN_STAGES=4`、以降は `TOTAL_STAGES`（8）。`triggerStageClear` の全クリア判定とHUD表示に使用。
- v0.28 母竜ブレス頻度：ラン中カード **母竜の鼓動**（`mbreath_rate`, `effMotherBreathRate()=0.82^n`, 解禁時のみ）で発動間隔を短縮（`updateMotherBreath` の `MOTHER_BREATH_INTERVAL * effMotherBreathRate()`）。
- v0.22 母竜（Phase 5）：`motherHp`（→`effBoidMaxHpFor(0)`、reset/revive/HPバーに反映）／`motherDmg`／`motherBreath`（解禁フラグ・加算）。**母竜ブレス** `updateMotherBreath()` は `updateWeaponAttacks` 末尾で `isMotherActive()`＋解禁ガードのもと、**7.0秒ごと**（v0.22.1 で頻度を半分に）に周囲最大6対象へバースト（基礎60 × motherDmg × ラン中カード `effMotherBreathDmg`）。ラン中強化カード **母竜の吐息**（`mbreath_dmg`, +30%/枚, 解禁時のみ出現）が主軸。ブレスの系統・進化（枝分かれ）や"虹色演出"名物ノードは後続スライス。

## チャレンジ／コンプ（Phase 6・v0.25）
- `CHALLENGE_DEFS`（7種初版）：`done()` で判定、達成で竜晶付与＋達成トースト。`profile.challenges[id]={done}` で記録。
  - run系：三時代の覇者(STAGE3到達/30)・大群の主(群れ60/50)・全文明制覇(全クリア/100)。
  - ※ノーダウン系はコンセプト（竜は必ず復帰／ダウンOK）に反するため不採用（v0.25.1で削除）。
  - 累計系：エリート狩り(エリート3体/80)・花火師(花火10棟/60)・歴戦の母竜(全クリア5回/150)。
- 追跡カウンタ：`profile.eliteKills`（`damageMover` の `def.elite`）／`profile.fireworksDestroyed`（`detonateFirework`）／`runDowns`（`applyDamageToBoid`、ノーダウン判定）。
- 判定フック：`advanceToNextStage`（到達・群れ・累計）／`triggerAllClear`（全クリア・ノーダウン、`lastRunNoDown = runDowns===0`）で `evaluateChallenges()`。
- UI：タイトルの「チャレンジ N/M」ボタン→ `openChallenges()` の全画面一覧（達成✓／進捗 x/goal／報酬）。達成トースト `#challenge-toast`。
- 次：報酬に**特別解放ノード**（`unlockBy: challengeId`）を加える二層経済、コンプ全達成の大型報酬。

## 攻略対象（Phase 3・v0.23〜）
- **花火要塞**（`isFirework`）：`generateStageLayout` で通常建物から抽選（後半ほど棟数増：stage1-3=1/4-6=2/7-8=3）。回転ピンクのスパークで目印表示（`drawEggBearerMarkers` 内）。撃破＝`settlementFall`→`detonateFirework`：放射スパーク＋炎＋フラッシュ＋**竜晶+15・XP+60**の"うまみ"。単独で面白い当たり枠。
- **エリート「warlord」**（`MOVER_DEFS.warlord`, v0.24）：後半3ステージ限定（`MOVER_SPAWNS_BY_STAGE` の index5/6/7 に 1/1/2 体）の歯ごたえ枠。既存 ironclad スプライトを流用（`def.sprite`）、大型(radius42)・超高HP(1400)・高頻度舷側砲＝弾幕でダウン圧を作る"壁"。撃破報酬も大（XP400・卵5）。`drawMovers` でエリートは大きく明るい赤オーラ表示。「後半が快適すぎる」への対処。
- **財宝馬車「treasure」**（`MOVER_DEFS.treasure`, v0.25.1）：各ステージに1体の"当たり枠"。竜ではない運搬体（`fleer`＝群れから逃げる／`flying`＝地形無視）。攻撃なし（`updateMovers` は `!atk` でスキップ）。撃破で**竜晶+40・XP200・卵2**＋金色スパーク。balloon スプライトを金オーラで流用（`drawMovers` の `def.treasure`）。追いかける楽しさ（Balatro の当たり枠）。
- **巨獣（多パーツボス）**（`behemoth_core`＋`behemoth_arm`×2, v0.26）：後半2ステージ（STAGE6/8）に1体の set-piece。**専用スプライト**（俯瞰コア＋浮遊腕、Gemini生成→クロマキー）。各パーツを個別 mover として持ち、`generateMovers` で核＋腕2本を結線（`arm.parent=core` / `core.armL/armR`）。
  - 腕：`updateBehemothArm` でコアの左右を浮遊（`BEHEMOTH_ARM_ORBIT`）、最寄りの竜へ拳を向け**叩きつけ衝撃波**（`emitShockwave`＝範囲ダメージ＋強ノックバック70）。個別HP500で先に壊せる（壊すと攻撃停止）。
  - コア：HP2200・ゆっくり接近・**扇状の遠隔弾**（fan）。撃破で**腕も道連れ**＋竜晶60・XP600・卵8＋派手演出（段階的解体の塊魂感）。
  - 付随修正：`drawMovers` の `def.attack.type` を `def.attack &&` でガード（財宝馬車/腕など無攻撃 mover の描画時例外を修正。v0.25.1 から潜在）。
- **歯ごたえ枠3種（v0.27・後半集中・挙動ベース・既存スプライト流用）**：
  - **衝撃兵**（`shockman`, sprite mammoth・赤）：単体大型獣。周期的に強ノックバック(push60)の踏鳴らし。shockwave攻撃を `emitShockwave(atk.push)` に集約。stage5/7。
  - **治癒塔**（`healer`, sprite colossus・緑）：停止。近接非依存で周囲の建物/敵HPを回復(radius340/heal14)。放置で長引く優先目標。stage6。
  - **召喚門**（`summoner`, sprite balloon・紫）：停止。レイダーを能動湧き(interval3/cap8)。反復中は `_pendingMovers` に積み末尾でflush。門を壊すと止まる。stage7/8。
- 対処：衝撃兵→不屈/母竜、治癒塔/召喚門→統率で急襲。attack type "heal"/"summon" を updateMovers に追加（近接ゲート前）。
- 各ラインの「単独で面白い"名物ノード"」（母竜=虹色特大ブレス、大群=黄金化、統率=彗星の尾、恵み=竜晶花火）と、母竜ライン・特別解放ノード（`unlockBy: challengeId`）は後続スライスで追加予定。
- 数値・ノード構成は暫定。プレイテストで調整する前提。将来ノードは `TREE_DEFS` に追記し、必要なら `permaBuff` にフィールドと `recomputePermaBuff` の分岐を足す。

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
