---
description: Gemini APIでゲーム用画像アセットを生成→クロマキー透過PNG化→検証（$ARGUMENTS: 何の素材か）
---

Gemini API でゲーム用の画像アセットを生成し、透過PNGに加工して検証するパイプライン。
対象素材: $ARGUMENTS

## 前提

- スクリプト一式: `C:\forge\ClaudeCodeForge`（詳細はそこの CLAUDE.md）
- Python: `C:\Users\syuta\AppData\Local\Programs\Python\Python311\python.exe`（システムPython、PIL/numpy導入済み）
- `GEMINI_API_KEY` はUser環境変数。Git Bash からは明示読み込みが必要（下記）

## 1. プロンプト設計（透過前提の定型）

プロンプトに必ず含める要素:
- **背景**: `Solid flat pure green background (#00FF00) for chroma key removal, no ground, no shadow, no other objects`
- **画風**（Dragon Tide 系）: `Flat cel-shaded illustration style, bold clean silhouette, thick dark ink outlines, high contrast, no painterly texture`
- **構図**: 向き（例: 鼻先が画像上方向）、`perfectly centered and symmetric`、`comfortable green margin on all sides`（フレーム端に接すると切れる）
- **除外指定**: ゲーム側で動的描画するパーツ（尻尾など）は「描くな」と明示。1回で伝わらないことがあるので、結果を見て言い換えて再生成する
- **注意**: プロンプトは **ASCII のみ**にする（em ダッシュ — 等があると cp932 で UnicodeEncodeError）。保険で `PYTHONIOENCODING=utf-8` も設定

## 2. 生成（Git Bash から）

```bash
cd /c/forge/ClaudeCodeForge && \
export GEMINI_API_KEY=$(powershell -Command "[System.Environment]::GetEnvironmentVariable('GEMINI_API_KEY','User')" | tr -d '\r') && \
export PYTHONIOENCODING=utf-8 && \
/c/Users/syuta/AppData/Local/Programs/Python/Python311/python.exe generate_gemini.py "<prompt>" --aspect 1:1 --size 1K
```

出力: `C:\forge\ClaudeCodeForge\output\gemini-generated\<timestamp>.jpg`
生成結果を Read で目視確認し、狙いと違えばプロンプトを調整して再生成（1〜3回の試行は普通）。

## 3. クロマキー透過PNG化

```powershell
& "C:\Users\syuta\AppData\Local\Programs\Python\Python311\python.exe" `
  "C:\forge\ClaudeCodeForge\chroma_key.py" <input.jpg> <output.png> [--crop-bottom-frac F] [--pad N]
```

- 背景色は角からサンプリング（JPEG圧縮ズレ対応）、スピル抑制・bbox自動クロップ付き
- `--crop-bottom-frac`: 下側の不要パーツ（消しきれなかった尻尾など）を先に切除
- 出力先はゲームの `assets/` ディレクトリ（例: `prototypes/dragon-tide/assets/`）

## 4. 検証（必須）

**アルファ検証**（数値）: 角の alpha ≈ 0、コンテンツ中心の alpha = 255 を PIL+numpy で確認。

**縁のフリンジ検証**（目視）: 市松模様に合成した `_check_*.jpg` を作って Read で確認。緑ハローが残っていないこと。確認後は `_check_*.jpg` を必ず削除する。

**スプライト用の追加計測**（回転させて使う素材のみ）:
- 左右対称性: アルファ質量重心の x が画像中心 ±1px 以内か
- **回転ピボット**: 画像中心ではなく**アルファ質量重心**（alpha>30 の画素の x,y 平均）を実測して使う。翼など質量が偏った素材では中心ピボットだと回転が破綻する（Dragon Tide で実証済み）

## 5. 後続

- ゲームへの組み込みは別途（Dragon Tide なら組み込み後 `/deploy-dragon-tide`）
- 外から確認したい場合は Notion へ: `C:\forge\ClaudeCodeForge\notion_upload.py <files...>`（NOTION_TOKEN 読み込みが必要、ページID等は ClaudeCodeForge の CLAUDE.md 参照）
