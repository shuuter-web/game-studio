# AI活用ゲーム開発プラクティス調査 ＋ 本スタジオのギャップ分析

- 調査日: 2026-08-14
- 対象リポジトリ: `game-studio`（コミット `11149df` / Dragon Tide v0.37.1 時点）
- 目的: 世界で標準化しつつある「AIでゲームを作る」実践と、一般的な開発セオリーを集め、
  **本プロジェクトで実践できていないもの**を洗い出して反映する

---

## 0. 結論（3行）

1. **最大の穴は「検証ループ（verification loop）の不在」**。`tests/` は空、CI なし、hooks なし。
   AIが「できました」と言う根拠が、事実上ユーザーの目視だけになっている。
2. **その前提として「決定性（seed）」がない**。`Math.random()` が137箇所・シードなしのため、
   バグ再現・回帰テスト・自動バランス検証・自動プレイテストのすべてが原理的に不可能。
3. 逆に、**コンテキスト工学（CLAUDE.md / skills / subagents / ELEMENTS.md / snapshots）は
   世界の平均より上**。伸ばすべきは「AIに指示する力」ではなく「**AIの成果を機械が採点する力**」。

---

## 1. 世界の標準になりつつある実践（調査結果）

### A. AIエージェント運用（ゲームに限らない開発セオリー）

#### A-1. 「AIに検証手段を渡す」— これが第一原則
Anthropic 公式のベストプラクティスは、全項目の筆頭に「Claude に自分で走らせられるチェックを渡せ」を置いている。
> チェックがなければ「それらしく見える」が唯一の完了シグナルになり、**人間が検証ループそのものになる**。

チェックの実体は何でもよい: テストスイート / ビルドの終了コード / linter /
出力をフィクスチャと差分比較するスクリプト / スクリーンショット比較。
強制の強さは4段階で選ぶ:

| 強度 | 手段 | 特徴 |
|---|---|---|
| 弱 | プロンプト内で「実行して直すまで繰り返せ」と書く | 今日から使える |
| 中 | `/goal` 条件（毎ターン別評価器が再チェック） | 放置耐性が出る |
| 強 | **Stop hook**（スクリプトが通るまでターンを終了させない） | 決定的ゲート |
| 別軸 | **検証サブエージェント**（実装したのとは別のコンテキストが採点） | 自己採点バイアスを排除 |

また「成功しました」と主張させず、**証拠（テスト出力・実行コマンドと戻り値・スクショ）を提示させる**。

#### A-2. Explore → Plan → Implement → Commit の4相分離
仕様駆動開発（SDD）が2026年の主流形。**Specify → Plan → Tasks → Implement** の各相に人間のチェックポイントを置く。
要求は EARS 記法などで「テスト可能な文」に落とす。
Anthropic 版の実践では、大きめの機能はまず **AI に人間をインタビューさせて `SPEC.md` を書かせ、
セッションを切り替えてクリーンな文脈で実装させる**。良い spec の条件は
「関係するファイルとインターフェースを名指しする」「スコープ外を明記する」
「**末尾に end-to-end の検証手順がある**」。

#### A-3. コンテキストは最重要資源
- 性能はコンテキストが埋まるほど劣化する。タスクが切り替わったら `/clear`。
- **同じ問題で2回修正しても直らないなら、文脈が失敗案で汚れている**。捨てて、学んだことを織り込んだプロンプトで再開する方が速い。
- 調査（大量ファイル読み）は subagent に投げ、本会話には要約だけ返す。
- CLAUDE.md は「消したらAIが間違えるか？」で1行ずつ選別する。長いと**規則そのものが無視される**。
  たまにしか要らない知識は skills に逃がす。

#### A-4. 4つの拡張プリミティブの使い分け
| 種類 | 役割 | 性質 |
|---|---|---|
| CLAUDE.md | 常時ロードの共通前提 | 助言的（守られないことがある） |
| Skills | 反復手順・ドメイン知識（オンデマンド） | 助言的 |
| Subagents | 隔離コンテキストの専門ワーカー | 助言的 |
| **Hooks** | ライフサイクルで走る**スクリプト** | **決定的（必ず実行される）** |

「毎回必ず起きてほしいこと」を CLAUDE.md に書くのは設計ミスで、それは hook の仕事。

#### A-5. 敵対的レビュー（writer / reviewer 分離）
実装したセッションは自分のコードに肩入れするので、**差分だけを見る新規コンテキストのレビュアー**を通す。
ただし「ギャップを探せ」と言われたレビュアーは健全なコードにも指摘を作るため、
**「正しさと要件充足に関わるものだけ報告せよ」と制約する**（過剰設計の防止）。

#### A-6. バージョン管理を安全網にする
超細粒度コミット＝「ゲームのセーブポイント」。実験は branch / worktree に隔離。
git 履歴と diff 自体を、次のAIへの文脈として使う。

#### A-7. コードベースの形が AI の精度を決める
研究上の知見として、**LLM は放置するとモノリス（中央値1〜3ファイル）を好む**が、
実際の編集精度は **小さく凝集したファイル＋明確なインターフェース＋テスト**の方が高い。
モジュール分割は変更の「爆発半径」を縮め、幻覚編集・壊れた参照・副作用を減らす。
モジュラーモノリスが大半のチームの最適解。

#### A-8. 典型的な失敗パターン
| 失敗 | 症状 | 対処 |
|---|---|---|
| kitchen sink セッション | 無関係タスクを混ぜて文脈が汚れる | `/clear` |
| 修正の無限ループ | 2回直しても直らない | 捨てて再スタート |
| 肥大 CLAUDE.md | 規則が無視される | 剪定、hook 化 |
| trust-then-verify ギャップ | 「それらしい」実装がエッジケースで壊れる | 検証手段を必ず用意 |
| 無限探索 | スコープなしの「調査して」で文脈が溢れる | subagent に隔離 |

### B. ゲーム開発に固有の実践

#### B-1. 決定性シミュレーション＋シード（最重要）
- 固定シードで走らせ、**失敗したシードをそのまま永久の回帰テストにする**。
  「シードが増えるほどテストが増える」フィードバックループ。
- 本番/過去実行を **ゴールデントレース**として保存し、新バージョンで再生して差分を見る。
- ゲームでは「対話プレイ」と「自動実行」が同じ状態遷移を共有する形にし、
  決定的ヒューリスティック方策のボットを固定シードで走らせると、
  **難易度の急変・到達不能状態・フリーズ・報酬/マップ生成のリグレッションを検出する計測器**になる。
- 大規模には「数千シードを毎晩回す」だけで、仕組み自体は変わらない。

#### B-2. AIエージェントによる自動プレイテスト／QA
2026年には indie でも実用段階。要点は「**エージェントにゲーム状態を露出するインターフェースを作る**」こと
（MCP経由でアクター操作・関数呼び出し・プロパティ検査・UI状態検査を公開する構成が典型）。
- **得意**: 状態整合性バグ（ゲーム規則と矛盾する変数状態）、異常手順によるクラッシュとその再現手順、
  夜間ベースライン比較による回帰検出、組合せ爆発するエッジケース、セーブ/ロード整合性。
- **不得意**: 手触り・ジュース、クラッシュしない見た目のバグ、物語の良し悪し、新規の創発的発見。
- 小規模チームの入り方: 「最も危険なシステムを1つ選ぶ → 自然言語でテストケース10件 → 手動実行 → 1週間で自動化」。
  初期投資3〜5日、以後は週1〜2時間の保守。

#### B-3. モンテカルロによるバランス調整
シミュレータで数百〜数千試合を回して勝率・分散を出し、パラメータを調整する手法は
カードゲーム/RPG領域で確立済み。**組合せが爆発する設計（デッキ構築・ビルド・種族×カード）ほど効く**。
LLMマルチエージェントで自動バランシングする研究（RuleSmith 等）も出ている。

#### B-4. テレメトリは「最初の10イベント」から
- **高シグナルなゲームプレイ／進行イベントから始め、UIの細かいイベントは
  「実際の意思決定に答えるとき」だけ足す**。
- 押さえる領域: セッション、オンボーディング、レベル/ステージのファネル、経済。
- ヒートマップ（どこで死ぬか・どこに行くか）は設計の穴を可視化する。

#### B-5. 最初の60秒（FTUE）とジュース
- **最初の60秒で失敗した人の離脱率は突出して高い**。約60%は「早すぎる難化」で辞める。
- 良いオンボーディングは継続率を最大50%押し上げるという報告。
- ジュース＝視覚（パーティクル・シェイク）＋音＋触覚の束。
  **プレイヤーが起こせる全インタラクションに明確なフィードバックを付ける**のが基本線。
- 一方で「fun factor は定量だけでは測れない」ため、**定量（ファネル）と定性（無介入観察）の併用**が前提。

#### B-6. AI生成アセットのパイプライン
- 一貫性の解法は「**参照20〜30枚でスタイルを学習させ、そこから量産**」。
- 実運用は「AIで20案生成 → 3〜5案採用 → 手作業で仕上げ」。制作時間は約60%削減されるが、
  **土台の美術知識は依然必要**というのが2026年の共通見解。
- ComfyUI がインディーの標準ツール化（ローカル生成・アトラス出力）。

#### B-7. AI開示（配信するなら必須の法務メモ）
Steam は2026年1月に開示要件を改定し、**「プレイヤーが消費する成果物」に焦点を絞った**。
- 開示が要る: ゲームに同梱される生成アセット（アート・音・テキスト）、**ストアページ/マーケ素材**。
- 開示が不要（明示的に除外）: コーディング支援・デバッグ・出荷しないコンセプトアート等の**開発ツール用途**。
- **ライブ生成**（実行時にLLM等が生成）は別枠で、不適切出力の防止策の記述が必要。違反は削除対象。
  オーバーレイに通報ボタンも追加済み。

---

## 2. 本スタジオが既にできていること（維持すべき資産）

| 実践 | 実体 | 世界標準との対応 |
|---|---|---|
| コンテキストの明文化 | `CLAUDE.md`（規約・ワークフロー・**preview_* の実証済み落とし穴**） | A-3。特に「落とし穴」節は良質な context engineering |
| 手順のスキル化 | `.claude/skills/seed-sprint`, `/deploy-dragon-tide`, `/gen-game-asset` | A-4 |
| 役割分割 | 14サブエージェント（producer 起点） | A-4 / A-5 の下地 |
| 発散と収束の分離 | idea-scout ↔ greenlight-judge（自己採点と第三者採点の突合） | A-5 の発想をゲーム企画に応用済み |
| 識別子の索引 | `prototypes/dragon-tide/ELEMENTS.md` | A-7 の代替。モノリスをAIに扱わせる緩和策として有効 |
| 過去版の保全 | `prototypes/dragon-tide/snapshots/` | B-1 のゴールデン記録の萌芽 |
| 記憶の永続化 | `memory/*.md` + MEMORY.md 索引 | 好み・失敗の再発防止 |
| 最小の自動チェック | deploy スキル内の `node --check`（BOMなしUTF-8で抽出） | A-1 の最小実装 |
| 生成アセット運用 | Gemini/Forge によるアセット30点、クロマキー透過→検証 | B-6 |

---

## 3. できていないこと（ギャップ）— 優先度順

### 🔴 G1. 機械が採点する検証ループがない
- **証拠**: `tests/` は `.gitkeep` のみ。`package.json` / CI 設定 / `.claude/settings.json` が存在しない。
  自動チェックは deploy 時の構文チェック1本だけ。
- **効き方**: A-1 の通り、これが無い限り Claude の完了判断は「見た目」で決まり、
  ユーザーが毎回の検証装置になる。129コミット分の手動検証コストが積み上がっている。
- **最小の一手**: `prototypes/dragon-tide/index.html` からJSを抽出して
  (1) `node --check`、(2) 主要関数のスモークテスト、を1コマンドで走らせる `check` スクリプトを作り、
  **PostToolUse または Stop hook で強制**する。

### 🔴 G2. 決定性（シード）がない
- **証拠**: `Math.random()` が137箇所、シード付きRNGなし。
- **効き方**: G1・G3・G4・G6 すべての前提。今は「たまに起きるバグ」を再現する手段が無い。
- **最小の一手**: `mulberry32` 等のシード付きRNGを1つ置き、`Math.random()` を `rng()` に一括置換。
  URLパラメータ `?seed=` で固定できるようにする。バグが出たシードを `tests/seeds/` に貯める。
- **注意**: 演出用の乱数（パーティクル）とゲームロジック用の乱数は**別ストリームに分ける**
  （描画をスキップしてもロジックが同じ結果になるように）。

### 🔴 G3. ヘッドレス自動プレイ（AIプレイテスト）がない
- **証拠**: Dragon Tide の設計3本柱は「Balatro＝竜種でプレイ感が変わる」。
  竜種は v0.37 時点で10種超、★カードとステージ8種の組合せがあるが、検証は手動プレイのみ。
- **効き方**: B-2/B-3。組合せ爆発している設計こそ自動プレイの費用対効果が最大。
- **最小の一手**: 描画をスキップして `update(dt)` だけを固定ステップで回す `runHeadless(seed, policy, steps)` を実装。
  素朴なボット方策（最寄りの敵へ線を引く等）で1000シード回し、
  「クリア時間の分布」「竜種別の生存/撃破数」を CSV 出力する。
- **副次効果**: CLAUDE.md に書かれた既知の罠（プレビューでは canvas サイズ0、FPS計測不能）を
  **ヘッドレス化そのものが回避する**。

### 🟠 G4. テレメトリがない
- **証拠**: `localStorage` はベスト記録とラン保存のみ。離脱地点・カード選択率・死因の記録なし。
- **効き方**: B-4/B-5。「最初の60秒」で何が起きているかが完全に不可視。
- **最小の一手**: まず**ローカルだけ**でよい。`events: {t, type, payload}[]` をラン中に貯め、
  ラン終了時に localStorage へ。デバッグメニューから JSON をコピーできるようにする。
  最初のイベントは10個に絞る:
  `run_start / first_input / stage_enter / stage_clear / card_offered / card_picked /
   dragon_lost / boss_engaged / run_end / quit`。

### 🟠 G5. 単一12,393行・555KB のHTML
- **証拠**: `prototypes/dragon-tide/index.html` = 12,393行、`<script>` は572行目から12,391行目まで。関数320個。
- **効き方**: A-7。編集の爆発半径が最大で、AIの誤編集リスクとコンテキスト消費が両方効いてくる。
  `ELEMENTS.md` で緩和しているが、根治ではない。
- **最小の一手（プロトを壊さない範囲で）**: ES modules に分割し `index.html` は
  `<script type="module" src="src/main.js">` だけにする。分割の第一段は
  `data/`（STAGE_CONFIGS 等の定数）→ `sim/`（更新ロジック）→ `render/`（描画）→ `ui/`。
  ファイル配信は既に `npx serve` なので module 化に障害はない。
  **`sim/` を `render/` から切り離すこと自体が G3 の前提**でもある。

### 🟠 G6. データ駆動が名目倒れ
- **証拠**: `data/balance/dragon-tide.json` は存在するが、`index.html` からの参照は **0件**。
  実際の数値は `STAGE_CONFIGS` / `WALL_STAGE_CONFIG` としてコード内に埋まっている。
- **効き方**: CLAUDE.md の「バランス調整がコード変更を伴わないように」が守られていない。
  加えて、balance JSON が現実と乖離した**嘘のドキュメント**になっており、AIを誤誘導する。
- **最小の一手**: どちらかに寄せる。(a) JSON を正典にして起動時に読む、
  (b) 使わないなら削除し、コードを正典と明記する。**放置が最悪**。
  （v0.35.1 で「ピボット値の二重管理をやめてコードを正典に一本化」という前例がある＝同じ判断を再適用すればよい）

### 🟡 G7. ADR が1件もない
- **証拠**: `docs/decisions/` は `.gitkeep` のみ。一方で大きな方針転換は多数
  （v0.32 操作を「指が常に操縦点」へ単純化 / v0.34 竜種を「攻撃×動き×見た目」に分離 /
  v0.30→v0.31 母竜ブレスを常時発動→★カード取得へ / v0.28.2 トップビューにドーム表現は不採用）。
- **効き方**: 「なぜそうしたか」がコミットメッセージにしか無いため、
  新しいセッションのAIが**同じ却下済み案を再提案する**。実際 memory に
  「トップビューなので立面表現は禁止」を退避させているのは、この不足の埋め合わせ。
- **最小の一手**: 1件5行のADR（決定 / 背景 / 却下案とその理由 / 影響）。過去分は上記4件を遡って書けば足りる。

### 🟡 G8. hooks / settings.json がなく、規約がすべて「お願い」
- **証拠**: `.claude/` に `settings.json` なし（agents / commands / skills / launch.json のみ）。
- **効き方**: A-4。「日本語コミットメッセージ形式」「Dragon Tide は必ず deploy まで」
  「i18n を通す」などが、守られたかどうかを誰も機械的に確認していない。
- **最小の一手**: (1) `index.html` 編集後に構文チェックを走らせる PostToolUse hook、
  (2) master へ直コミットを止める PreToolUse hook。

### 🟡 G9. 実装単位の SPEC と受け入れ条件がない
- **証拠**: GDD/TDD はあるが、機能単位の「完了の定義」が無い。
  `docs/gdd/dragon-tide-next-steps.md` はあるが受け入れ条件形式ではない。
- **最小の一手**: 中規模以上の変更前に `SPEC.md`（対象ファイル・スコープ外・**末尾にE2E検証手順**）を1枚。
  A-2 の「AIにインタビューさせて spec を書かせ、別セッションで実装」を seed-sprint と同様にスキル化できる。

### 🟡 G10. 種→プロトの kill criteria が数値化されていない
- **証拠**: CLAUDE.md に「採用後は GDD化より先に最大の賭けを最小プロトで潰す」とあるが、
  **何をもって「潰せた」とするかの合格ラインがない**。`prototypes/` には7件が残存し、
  どれが生きていてどれが死んだのかがファイルからは分からない（`ideas/seeds` の status とは繋がっていない）。
- **最小の一手**: プロト着手時に「賭け / 測り方 / 合格ライン / 期限」の4行を
  `prototypes/<name>/BET.md` に書く。期限が来たら PS-XXX の status を更新する。

### 🟡 G11. 人間のプレイテスト工程がない
- **証拠**: `docs/qa/` は `.gitkeep` のみ。
- **効き方**: B-2 の通りAIエージェントは「手触り・ジュース・面白さ」を評価できない。
  自動化を入れても**ここは埋まらない**ので、別建てで必要。
- **最小の一手**: 5人・無介入観察・「最初の60秒で何をしたか」だけ記録する軽量プロトコル。

### 🟢 G12. i18n 未実施（自覚あり・現時点では妥当）
- **証拠**: `index.html` にインライン辞書があり「本制作移行時に locales/ へ抽出する」とコメント済み。`locales/` は空。
- **判断**: プロト段階では正しい判断。ただし**「単一ファイルプロトの間は i18n 免除」を CLAUDE.md に明記**して、
  規約と実態の乖離を消しておくべき（乖離した規約は他の規約の信頼性も下げる）。

### 🟢 G13. AI開示・アセット権利のメモがない
- **証拠**: 生成アセット30点を同梱。配信計画の記録なし。
- **最小の一手**: 配信するなら Steam の開示区分（同梱アセットは要開示 / コーディング支援は不要 /
  ライブ生成は別枠）を1枚のメモにしておく。今すぐ困る話ではないが、後から棚卸しすると高くつく。

### 🟢 G14. 並列セッション / worktree / writer-reviewer 分離が未使用
- **証拠**: ブランチは `master` と `feat/playseed-format` の2本。`/code-review` は使えるが運用ルールに無い。
- **最小の一手**: 大きめ変更のとき「実装セッション」と「差分だけ見るレビューセッション」を分ける。
  レビュアーには**「正しさと要件に関わるギャップだけ」**と制約を付ける（過剰指摘の抑制）。

---

## 4. 反映プラン

### スプリント1「機械に採点させる」（G2 → G1 → G8）— ✅ 完了 2026-08-16
1. ✅ シード付きRNG（mulberry32）を導入。ロジック用 `random()` / 演出用 `fxRandom()` の2ストリームに分離。
   `?seed=` でラン固定、現在シードはHUD表示（Dragon Tide v0.38.0）
2. ✅ `tools/check.mjs`（4検査: 構文 / `Math.random()` 直呼び / 参照アセットの実在 / `GAME_VERSION` 形式）。
   `--hook` モード内蔵。検査の追加は `CHECKS` に関数を足すだけ
3. ✅ `.claude/settings.json` に PostToolUse フック（`Edit|Write|MultiEdit` 後に自動実行、失敗で差し戻し）
4. ✅ CLAUDE.md / `/deploy-dragon-tide` を実態に合わせて更新（手書きPowerShell抽出の手順は廃止）

> ここまでで「AIが自分の成果を採点できる」状態になった。以降の全作業の速度が変わる。
> **未了**: 決定性の実機検証（同一シードで同一展開になることの確認）と、v0.38.0 のデプロイ。

### スプリント2「回して測る」（G3 → G4 → G6）
4. `sim/` と `render/` の分離 → `runHeadless(seed, policy, steps)`
5. 1000シードのバッチ実行 → 竜種別・ステージ別の統計CSV
6. テレメトリ10イベント（ローカル）／balance JSON の生死を決着

### スプリント3「記録と人間」（G5 → G7 → G9〜G11）
7. ES modules への段階的分割
8. 過去の重要判断4件を遡ってADR化 + 以後の運用ルール
9. `SPEC.md` 運用、`BET.md`（kill criteria）、5人プレイテストのプロトコル

### CLAUDE.md への追記案（抜粋）
```markdown
## 検証ルール（AIは自己申告で完了としない）
- `prototypes/dragon-tide/index.html` を編集したら必ず `check` を実行し、**出力を貼って**から完了報告する
- 乱数は `rng()` を使う（`Math.random()` 直呼び禁止）。バグは再現シードとセットで報告する
- 中規模以上の変更は SPEC（対象ファイル / スコープ外 / E2E検証手順）を先に1枚書く
- プロト段階の単一HTMLは i18n 免除（インライン辞書可）。本制作移行時に `locales/` へ抽出する
```

---

## 5. 出典

**AIエージェント運用**
- [Best practices for Claude Code — Claude Code Docs](https://code.claude.com/docs/en/best-practices)
- [My LLM coding workflow going into 2026 — Addy Osmani](https://addyosmani.com/blog/ai-coding-workflow/)
- [Spec-Driven Development (SDD): The Definitive 2026 Guide — BCMS](https://www.thebcms.com/blog/spec-driven-development/)
- [Context Engineering Best Practices for AI-Powered Dev Teams (2026) — Packmind](https://packmind.com/context-engineering-ai-coding/context-engineering-best-practices/)
- [Context Engineering: A Practical Guide for AI Agents (2026) — Sourcegraph](https://sourcegraph.com/blog/context-engineering)
- [Claude Code: Hooks, Subagents & Skills Complete Guide](https://ofox.ai/blog/claude-code-hooks-subagents-skills-complete-guide-2026/)
- [Modular vs Monolith for AI Coding — Itomic](https://www.itomic.com.au/modular-vs-monolith-for-ai-coding-which-is-better/)
- [Creating AI-Friendly Codebases — Davide Consonni](https://medium.com/@dconsonni/creating-ai-friendly-codebases-82cb3203c118)

**決定性・自動テスト・バランス**
- [Deterministic Simulation Testing: A Practical Guide for QA Engineers — The Green Report](https://www.thegreenreport.blog/articles/deterministic-simulation-testing-a-practical-guide-for-qa-engineers/deterministic-simulation-testing-a-practical-guide-for-qa-engineers.html)
- [Deterministic Replay: How to Debug AI Agents That Never Run the Same Way Twice — TianPan.co](https://tianpan.co/blog/2026-04-12-deterministic-replay-debugging-non-deterministic-ai-agents)
- [Mazocarta: A Seeded Procedural Deckbuilder for Instrumented Game Development (arXiv)](https://arxiv.org/pdf/2605.08319)
- [AI-Powered Game QA and Playtesting: Agents That Break Your Game Before Players Do — StraySpark](https://www.strayspark.studio/blog/ai-game-qa-playtesting-agents-mcp)
- [Leveraging LLM Agents for Automated Video Game Testing (arXiv)](https://arxiv.org/pdf/2509.22170)
- [RuleSmith: Multi-Agent LLMs for Automated Game Balancing (arXiv)](https://arxiv.org/pdf/2602.06232)
- [Monte-Carlo Simulation Balancing in Practice — Coulom](https://www.remi-coulom.fr/CG2010-Simulation-Balancing/SimulationBalancing.pdf)

**プレイテスト・テレメトリ・手触り**
- [Pre-Release Experimentation in Indie Game Development: An Interview Survey (arXiv)](https://arxiv.org/html/2411.17183v1)
- [How Can Indie Developers Effectively Playtest Their Games? — Wayline](https://www.wayline.io/blog/how-can-indie-developers-effectively-playtest-their-games)
- [The First 10 Telemetry Events Every Indie Game Should Ship — Gamine AI](https://gamineai.com/blog/the-first-10-telemetry-events-every-indie-game-should-ship)
- [First Time User Experience: The 60 Seconds That Decide If Your Player Stays](https://recognizingpatterns.substack.com/p/first-time-user-experience-your-player)
- [Squeezing more juice out of your game design — GameAnalytics](https://www.gameanalytics.com/blog/squeezing-more-juice-out-of-your-game-design)

**アセット生成・法務**
- [ComfyUI for Game Asset Pipelines: The Indie 2026 Playbook — StraySpark](https://www.strayspark.studio/blog/comfyui-game-asset-pipeline-indie-2026)
- [AI Pixel Art Generation in 2026: Tools, Workflows, and Why Hand-Crafted Still Wins](https://freegamesprites.com/en/news/ai-pixel-art-generation-2026-tools-and-workflows)
- [Steam updates AI disclosure form... 'consumed by players' — PC Gamer](https://www.pcgamer.com/software/ai/steam-updates-ai-disclosure-form-to-specify-that-its-focused-on-ai-generated-content-that-is-consumed-by-players-not-efficiency-tools-used-behind-the-scenes/)
- [Steam's 2026 AI Disclosure Rules: What Indie Developers Actually Need to Know — StraySpark](https://www.strayspark.studio/blog/steam-ai-disclosure-rules-2026-indie-developer-guide)
