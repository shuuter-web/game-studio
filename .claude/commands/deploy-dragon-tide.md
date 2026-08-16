---
description: Dragon Tide の変更を検証して master に反映（構文チェック→バージョン→コミット→cherry-pick→push）
---

Dragon Tide（`prototypes/dragon-tide/index.html`）の変更を検証し、GitHub Pages（master）へ反映する定型手順。以下を順に、省略せず実行すること。

## 1. 機械チェック（必須）

```bash
node tools/check.mjs prototypes/dragon-tide/index.html
```

構文（BOMなしUTF-8での抽出と `node --check`）・`Math.random()` の直接呼び出し・
参照アセットの実在・`GAME_VERSION` の形式をまとめて検査する。
**EXITCODE 0 以外なら修正してから先に進む**（自前でJSを抽出しようとしない）。

## 2. プレビュー動作確認

`preview_start`（launch.json の `dragon-tide`、port 5503）→ `preview_eval` で変更内容を数値検証、`preview_console_logs`（level: error）でエラーなしを確認。**プレビュー環境の既知の落とし穴はプロジェクト CLAUDE.md の該当セクションを必ず参照**（screenshotタイムアウト、viewH=0、FPS計測不能、reload直後のレース）。

## 3. GAME_VERSION のバンプ（毎回必須）

`index.html` 内の `const GAME_VERSION = "vX.Y.Z";` を1つ上げる（機能追加=minor、調整/修正=patch）。画面左下に表示され、ユーザーが最新版か判別に使う。**忘れやすいので必ずこのタイミングで確認する。**

## 4. コミット（対象ファイルのみ）

```
git branch --show-current   # 現在ブランチを必ず確認（master とは限らない）
git status --short
```

**意図したファイルだけ** を `git add`（index.html、追加した assets/ 等）。ユーザーの作業中ファイル（ideas/ 等）を巻き込まない。コミットメッセージは Conventional Commits + バージョン入り:
`feat: Dragon Tide vX.Y.Z — <変更内容>`（末尾に Co-Authored-By）。

## 5. master への反映

**現在ブランチが master ならそのまま `git push origin master` して終了。**

master 以外のブランチ（例: feat/xxx）にいる場合、**チェックアウトを切り替えずに** worktree + cherry-pick で master にだけ反映する（ユーザーのブランチ・作業ツリーに触れないため）:

```bash
cd "C:\Users\syuta\OneDrive\game-studio"
git worktree add ../gs-master-tmp master
cd ../gs-master-tmp
git cherry-pick <コミットhash>
git push origin master
cd ../game-studio
git worktree remove ../gs-master-tmp --force
```

**既知の問題:** OneDrive 配下のため `git worktree remove` が Permission denied で失敗することがある。その場合は `rm -rf /c/Users/syuta/OneDrive/gs-master-tmp` で直接削除し、`git worktree list` に残骸がないことを確認する。

cherry-pick が競合したら中断してユーザーに報告（勝手に解決しない）。

## 6. 最終確認と報告

```
git log --oneline -1 origin/master
```

反映されたhashを確認し、ユーザーに以下を報告:
- 公開URL: https://shuuter-web.github.io/game-studio/prototypes/dragon-tide/ （反映まで数分）
- 新バージョン番号（画面左下で確認できる旨）
- 変更内容と検証結果の要約
