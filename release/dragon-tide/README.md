# Dragon Tide 配布ビルド

ゲーム本体は `../../prototypes/dragon-tide/` で更新する。ここはSteam Windows・Android・iOSの共通配布基盤。

```sh
npm ci
npm run check
npm run build:windows
npm run test:desktop -- --packaged
npm run mobile:sync -- android
```

更新時は `npm run release:next` で配布番号を進め、ゲームと設定をコミットして表示されたタグを付ける。GitHub Actionsがそのタグから各OS用の成果物を生成する。署名用Secrets、正式アプリID、ストア設定は初回に登録する。

具体的なコマンド・署名・提出・復旧手順は [リリース運用](../../docs/releases/dragon-tide.md) を参照。
