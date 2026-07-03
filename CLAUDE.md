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
**`/seed-sprint <お題> [full]` で一括実行できる**（`.claude/skills/seed-sprint/`。lite=発散〜保存、full=judge判定込み）。
**ユーザーがお題を出して案出しを頼んだら、明示がなくてもこのスキルを自動で使う**（手動で工程を再現しない）。

1. **お題設定**（producer）: テーマ・制約を1つ決める（例「親指1本で遊べるWebカジュアル」）。
   お題に**抽象語（可愛い／癒し／ヒキ／怖い 等）が含まれる場合は、発散前にその語を作業定義し直す**
   （一度ラフに出させてから再定義→再発散、が有効）。例：可愛い＝ベビースキーマ核 ×「守りたい/応援したい/
   なりたい」×“操作で可愛さを生産する動的設計”。詳細はメモリ参照。
2. **発散**（idea-scout）: 種を8〜12件ラフ生成（ログライン＋コアループのみ）。
   起案条件に「**コアループ由来の快感 × 競合の薄い題材**」を明示し、既存有名作の「◯◯版」焼き直しを抑える。
   ただし新規性に振り切らず、**「商業的に売れそうと一目で伝わるヒキ」を10件中2〜3件は必ず混ぜる**
   （“ルールが分かりやすいだけ”はヒキではない。ヒキゼロは失格）。
3. **一次足切り**（producer）: コアループだけ見て3〜5件に即決で絞る
4. **肉付け**（game-designer / narrative-designer / ui-ux-designer / system-designer 並列）:
   残りを PLAYSEED 全項目フル記入。**トライアングル自己採点（項目10）まで必ず埋める**
   （judge が起案者の自己採点との差分を見て精度を上げる）
5. **判定**（greenlight-judge）: トライアングル判定で採点（合計11以上 or 1軸=5 を採用）
6. **出口振り分け**（producer）: 採用→最大の賭けを `prototypes/` で検証 → 通れば GDD化

- 採用・保留の種は `ideas/seeds/PS-XXX.md` に保存（テンプレ `ideas/seeds/_template.md`）。
- **発散した全種（採否前・不採用含む）は `ideas/seeds/_raw-seeds-log.md` に必ず記録**（練習回も含め蓄積し、月次で見返す）。
- **producer が段落レベルで詳述した案（本命・対抗・次点として個別に論じた案）は、判定未実施でも
  `ideas/seeds/PS-XXX.md` にフル記入で保存する**（1行ログだけで終わらせない。`status: seed` で保存し、
  `_raw-seeds-log.md` 側から `→ PS-0XX` でリンクする）。目安：一言要約を超えて複数文で
  コアループ・フック・ヒキを説明した時点でファイル化対象。
- `status` で生死を管理：seed → picked → promoted(GDD化) / dropped。
- **採用後は GDD化より先に「最大の賭け」を最小プロトで潰す**。
- 月次で `dropped` を見返し、市場が動いて化けた種を拾い直す。

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
- **構文チェックの正攻法**: `<script>` 内JSを **BOMなしUTF-8** で抽出して `node --check`。
  PowerShell では `[System.IO.File]::WriteAllText($out, $js, (New-Object System.Text.UTF8Encoding($false)))`
  を使う（`Out-File` はUTF-16になり文字化けで誤判定する）

関連コマンド: デプロイ一式は `/deploy-dragon-tide`、画像アセット生成は `/gen-game-asset`（`.claude/commands/`）。
