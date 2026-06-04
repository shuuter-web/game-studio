# Game Studio

複数のゲームアイディアを試作・本制作するための Claude Code ベースのスタジオ。

## セットアップ

```bash
# このディレクトリで Claude Code を起動
cd game-studio
claude
```

サブエージェントは自動的に `.claude/agents/` から読み込まれます。

## 使い方

### 基本: producer に話しかける

```
> 新しいアクションパズルのアイディアがある。重力を反転させながら進む横スクロール。
  まず形にしたい。
```

producer が要件を整理し、`game-designer` → `tech-lead` → `gameplay-engineer` の順で
タスクを振っていきます。

### 明示的にエージェントを指定する

```
> Use the localization-director subagent to review the current UI strings 
  for character length issues in German.
```

### 既存アイディアの試作開始

```
> ideas/003-gravity-puzzle.md を prototype 化したい。
```

## 推奨フロー

1. **アイディアを `ideas/` に Markdown で投げ込む**（粗くてOK）
2. **producer に「これを形にしたい」と相談**
3. **game-designer が GDD を起こす**
4. **tech-lead が技術判断と TDD を作る**
5. **エンジニア陣が実装、qa-engineer が検証**
6. **localization-director が多言語化を並行設計**

## アイディア倉庫テンプレ

`ideas/NNN-<short-name>.md`:

```markdown
# [仮タイトル]

## ハイコンセプト
1-2文で

## なぜ作りたいか
動機・狙い

## コアの遊び
30秒の体験を文章で

## 参考タイトル
- ○○ の □□ な部分
- △△ の ×× な部分

## 規模感
プロトタイプ / 短編 / 中編 / 大規模

## メモ
未整理のアイディア
```

## カスタムスラッシュコマンド（将来追加予定）

- `/new-idea` - アイディアテンプレを生成
- `/start-prototype <id>` - アイディアから試作プロジェクトを起こす
- `/release-check` - リリース前チェックリスト実行

## トラブルシューティング

エージェントが期待通りに動かない場合：
1. `/agents` でエージェント一覧を確認
2. `.claude/agents/<name>.md` の description を見直す
3. 明示的に "Use the X subagent" で呼び出してみる
