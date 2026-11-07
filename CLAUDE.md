# Game Studio - Claude Code 運用ルール

このリポジトリは複数のゲームアイディアを試作・本制作するためのスタジオです。
14体のサブエージェントが役割分担して動きます。

## エージェント一覧

### 司令塔
- `producer` - タスク分解と委譲、進捗管理

### 発想・選別（GDD前 / PLAYSEED段階）
- `idea-scout` - 種（PLAYSEED）の量産・発散、トレンド収集
- `greenlight-judge` - トライアングル判定による種の客観採点・足切り

### 企画・設計
- `game-designer` - コアメカニクス、ゲームループ
- `narrative-designer` - シナリオ、世界観、キャラクター
- `system-designer` - 数値バランス、経済、進行設計

### 技術
- `tech-lead` - アーキテクチャ、技術選定、レビュー
- `gameplay-engineer` - ゲームロジック実装
- `tools-engineer` - ビルド、CI/CD、開発環境
- `graphics-engineer` - 描画、シェーダー、最適化

### 体験
- `ui-ux-designer` - UI/UX設計
- `audio-director` - サウンドデザイン指示
- `localization-director` - 多言語対応設計

### 品質
- `qa-engineer` - テスト、品質保証

## 基本ワークフロー

1. **入口は producer**: 新規要望はまず producer に振る
2. **計画レビュー**: 実装前に Plan Mode で計画を確認
3. **ドキュメント駆動**: 重要判断は ADR、設計は TDD/GDD に残す
4. **小さく区切る**: 1機能 = 1ブランチ = 数コミット

## 作業ごとの手順書（該当する作業の前に必ず読む）

- **企画検討（Seed Sprint・企画書の公開）** → [`docs/process/seed-sprint.md`](docs/process/seed-sprint.md)
  - ユーザーがお題を出して案出しを頼んだら、明示がなくてもこの手順で回す
- **Dragon Tide 案帳（チケットの流れ・定時チェック）** → [`docs/process/dragon-tide-board.md`](docs/process/dragon-tide-board.md)
  - 地域・竜種・特殊個体・ラッシュイベント・敵などの案は、チャットに並べず案帳に1案1チケットで出す
  - 案帳：https://claude.ai/artifact/QCAvoU291kLKCVQsKuQahX
  - 案帳のチケットを読む・書く・実装する前、定時チェックのときに読む

## ディレクトリ構造

```
.
├── .claude/
│   ├── agents/          # サブエージェント定義
│   ├── commands/        # カスタムスラッシュコマンド
│   └── skills/          # スキル（/seed-sprint 等のワークフロー手順書）
├── docs/
│   ├── gdd/             # Game Design Documents
│   ├── tdd/             # Technical Design Documents
│   ├── decisions/       # ADR (Architecture Decision Records)
│   ├── narrative/       # 世界観・キャラクター・シナリオ
│   ├── system-design/   # 数値設計の意図
│   ├── ui/              # UI/UX設計
│   ├── audio/           # サウンド設計
│   ├── localization/    # 多言語化設計
│   ├── qa/              # テスト計画・バグ管理
│   ├── process/         # 作業ごとの手順書（Seed Sprint・案帳の運用）
│   └── roadmap.md       # マイルストーン
├── ideas/               # アイディア倉庫（GDD化前）
│   └── seeds/           # PLAYSEED 種（_template.md / PS-XXX.md）
├── prototypes/          # 試作（複数同時可）
├── projects/            # 本制作（複数同時可）
│   └── <project-name>/
│       ├── CLAUDE.md    # プロジェクト固有ルール
│       └── src/
├── data/
│   └── balance/         # 数値データ（CSV/JSON）
├── locales/             # 翻訳ファイル
└── tests/               # 自動テスト
```

## コーディング規約（共通）
- TypeScript: strict、`any` 禁止
- 命名は省略しない
- コメントは「なぜ」を書く
- マジックナンバー禁止、データは `data/` に切り出し
- すべてのユーザー向け文字列は i18n を通す（ハードコード禁止）。
  ただし `prototypes/` の単一HTMLプロトは免除（インライン辞書可・本制作移行時に `locales/` へ抽出）

## コミットメッセージ
Conventional Commits 形式:
- `feat:` 新機能
- `fix:` バグ修正
- `docs:` ドキュメント
- `refactor:` リファクタリング
- `test:` テスト追加・修正
- `chore:` その他

## 大事な原則
- **エンジン非依存**: コアロジックはエンジンに依存しない層に置く
- **ローカライズ前提**: 全UIは多言語対応を最初から想定
- **データ駆動**: バランス調整がコード変更を伴わないようにする

## 検証（AIは自己申告で完了としない）

`prototypes/` を編集したら、機械が採点したうえで報告する。目視だけで「できました」と言わない。

```bash
node tools/check.mjs                              # 全プロト
node tools/check.mjs prototypes/dragon-tide/index.html
```

検査内容: 構文（`<script>` 抽出 → `node --check`、行番号はHTML基準に読み替え）/
`Math.random()` の直接呼び出し / 参照アセットの実在 / `GAME_VERSION` の形式 /
関数と同じ名前の局所変数がその関数を隠したまま呼んでいないか（呼ぶと実行時に落ちるが構文検査はすり抜ける）。
`Edit`・`Write`・`MultiEdit` の後に PostToolUse フックで自動実行され、失敗すると差し戻される
（`.claude/settings.json`）。検査を足したいときは `tools/check.mjs` の `CHECKS` に関数を追加する。

**乱数は決定性を壊さないこと**（Dragon Tide v0.38.0〜）:
ゲーム状態に影響する乱数は `random()`、見た目だけの乱数は `fxRandom()` を使う。
`Math.random()` の直接呼び出しは禁止（どうしても必要な行には `// allow-math-random`）。
分けている理由は、描画を間引いてもロジック側の乱数列がずれず、
**ヘッドレス実行と実プレイで同じランを再現できる**ようにするため。
`?seed=12345` でランを固定でき、現在のシードはHUDに出る。**不具合は再現シードとセットで報告する。**

## プロトタイプ検証の既知の落とし穴（preview_* ツール）

`prototypes/` の単一HTMLゲームを Claude Code のプレビューで検証するときの実証済みの罠。
時間を溶かした実績があるので必ず先に読むこと。

- **`preview_screenshot` は必ずタイムアウトする**。見た目検証は `preview_eval` でのピクセル解析
  （オフスクリーンcanvasの `getImageData`）や状態検査で代替する
- **プレビューでは canvas サイズが 0（viewH=0）** になり、画面座標に依存する入力ハンドラ
  （UIゾーン判定など）が早期returnする。入力テストは `viewW/viewH` を実機相当（390/844）に
  設定してから行うか、入力フラグ（`isDrawing` 等）を直接立ててロジックだけ検証する
- **実行時FPSは計測不能**（バックグラウンドスロットリングで `fpsEma` 等が0〜数fpsに張り付く）。
  性能judgeはコード構造（per-frameの計算量・描画呼び出し数）で行い、実測はユーザーの実機に委ねる
- **`window.location.reload()` 直後の `preview_eval` はレースで旧コードを掴む**ことがある
  （"Inspected target navigated or closed" エラー、または古い関数定義）。リロード後は
  関数ソース（`fn.toString()`）に新コードの目印が含まれるか確認してから検証を始める
- **構文チェックは手で書かない**: `node tools/check.mjs <path>` を使う（BOMなしUTF-8での抽出も
  行番号の読み替えも中でやっている）。PowerShell の `Out-File` はUTF-16になり文字化けで誤判定するため、
  自前で抽出しようとしないこと

関連コマンド: デプロイ一式は `/deploy-dragon-tide`、画像アセット生成は `/gen-game-asset`（`.claude/commands/`）。

**反映先の原則（Shooter指示）**: プロトタイプの変更は、検証（`tools/check.mjs` ＋ 必要な実測）が通ったら
**そのまま master に反映する**（ブランチで止めて確認を待たない）。ブランチに留めて確認リンクを渡すのは、
ステージ構成や進行の作り替えのような**よほど大きな更新のときだけ**。

**反映先の合言葉とプレビューリンク（Shooter指示）**:
- 反映先は Shooter の一言で決める。**「ブランチ」**＝作業ブランチにコミットして push し、そこで止める。
  **「マスター」**＝master にマージ（`--no-ff`）して push し、作業ブランチも master にそろえる。
  指定がなければ上の原則（検証が通れば master、よほど大きな更新だけブランチ）に従う。
- **反映先がどちらでも、報告には毎回プレビューリンクを付ける**。プレビューリンク＝push したコミットの
  githack 固定URL `https://raw.githack.com/shuuter-web/game-studio/<sha>/<パス>`
  （ブランチなら最新コミット、master ならマージコミットの sha）。
  ブランチ名や `master` で書いたURLはキャッシュで古い版が出ることがあるので使わない（sha 固定なら push 直後から確実に映る）。
