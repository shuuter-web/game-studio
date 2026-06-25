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

## アイディア量産ワークフロー（Seed Sprint）

GDD化の前段。「お題1つ → 種10件 → 採用2件」のバッチで回す。1スプリント＝半日想定。

1. **お題設定**（producer）: テーマ・制約を1つ決める（例「親指1本で遊べるWebカジュアル」）
2. **発散**（idea-scout）: 種を8〜12件ラフ生成（ログライン＋コアループのみ）。
   起案条件に「**コアループ由来の快感 × 競合の薄い題材**」を明示し、既存有名作の「◯◯版」焼き直しを抑える。
3. **一次足切り**（producer）: コアループだけ見て3〜5件に即決で絞る
4. **肉付け**（game-designer / narrative-designer / ui-ux-designer / system-designer 並列）:
   残りを PLAYSEED 全項目フル記入。**トライアングル自己採点（項目10）まで必ず埋める**
   （judge が起案者の自己採点との差分を見て精度を上げる）
5. **判定**（greenlight-judge）: トライアングル判定で採点（合計11以上 or 1軸=5 を採用）
6. **出口振り分け**（producer）: 採用→最大の賭けを `prototypes/` で検証 → 通れば GDD化

- 種は `ideas/seeds/PS-XXX.md` に保存（テンプレ `ideas/seeds/_template.md`）。
- `status` で生死を管理：seed → picked → promoted(GDD化) / dropped。
- **採用後は GDD化より先に「最大の賭け」を最小プロトで潰す**。
- 月次で `dropped` を見返し、市場が動いて化けた種を拾い直す。

## ディレクトリ構造

```
.
├── .claude/
│   ├── agents/          # サブエージェント定義
│   └── commands/        # カスタムスラッシュコマンド
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
- すべてのユーザー向け文字列は i18n を通す（ハードコード禁止）

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
