# Dragon Tide 各プラットフォーム対応・販売準備の共有メモ

確認日 2026-11-26。ゲーム開発担当と配布担当の認識を合わせるための実装説明。

## 前提と確認対象

- Steam・Android・iOSはすべて買い切りを想定。
- ユーザーはスマホとPCでテストプレイ済み。今回の配布基盤は、各OSへの梱包・更新・保存の継続を扱う。
- 販売名義は個人を検討中。全ストア未登録。正式アプリ名は検討中。「Dragon Tide」と `com.shuuterweb.dragontide` は現在の仮設定。
- 配布基盤は `feat/dragon-tide-release-pipeline` の `58d90bd` に実装済み。確認時点でPR #1はドラフト・未マージ。
- masterの確認対象は `c2e404b`、ゲーム版は **v3.221.0**。masterにはまだ `release/dragon-tide/` と配布CIが入っていない。
- Windows・Android・iOSの全CI成功は **v3.88.2時点**。最新masterのアプリ版ビルド・署名・ストア受理は未検証。

[配布基盤PR #1](https://github.com/shuuter-web/game-studio/pull/1) / [全OSビルド成功記録](https://github.com/shuuter-web/game-studio/actions/runs/42136073373) / [配布基盤の実装](https://github.com/shuuter-web/game-studio/tree/58d90bdaf7ab90a28c6d2c4277d917bced4619a7/release/dragon-tide)

## 共通のゲーム本体と配布物の関係

ゲームロジック・描画・操作は既存のHTML／JavaScript／Canvas 2Dを共通利用する。各OSのアプリにHTMLとアセットを同梱し、その端末内のブラウザ実行環境で動かす。

```text
prototypes/dragon-tide/index.html + assets/
                    |
           共通Webビルド dist/web/
                    |
       +------------+------------+
       |            |            |
    Electron     Capacitor    Capacitor
    Chromium     Android      iOS
                 WebView      WKWebView
       |            |            |
 Windows EXE/ZIP  AAB/APK    xcarchive/IPA
       |            |            |
     Steam      Google Play   App Store
```

`scripts/build-web.mjs` は共通ソースをコピーし、配布版の印を持つ `release-runtime.js` をHTMLへ追加する。ゲーム側はその印がある場合にデバッグパネルとNキーのステージ送りを無効化する。版番号・コミット・ファイルハッシュはmanifestへ記録する。

資産はアプリ内から読み込む。プレイ時にGitHub Pages等の最新版へアクセスする設定はなく、コードの更新はストア経由で配る。追加アセットは `assets/` に置く。将来ほかのディレクトリや外部通信を使う場合は同梱対象とオフライン動作への影響を配布担当へ共有する。

## 各プラットフォームの実装

| 対象 | 実行方式 | ビルドと配布 |
|---|---|---|
| Steam向けWindows x64 | Electron 45.2.1にChromiumを同梱。独自URL `dragontide://game/index.html` でゲームをロードする | electron-builderでEXE一式とZIPを作る。SteamPipe用VDFを生成し、SteamCMDでアップロードする運用 |
| Android | Capacitor 8.6.0のAndroidアプリ内でAndroid WebViewを使う。Web資産をAndroidプロジェクトに同期する | GradleでAAB・APKを作る。未署名AABとデバッグAPKのCI生成は確認済み。署名用Secretsを設定するとアップロード鍵で署名したAABを生成できる構成 |
| iOS | Capacitor 8.6.0のiOSアプリ内でWKWebViewを使う。Web資産をXcodeプロジェクトに同期する | macOS／Xcodeでxcarchiveを作る。未署名アーカイブのCI生成は確認済み。証明書・プロファイル・Team ID設定後に署名済みIPAをexportする構成 |

Windowsは固定のユーザーデータ領域とセッションを使用する。ゲーム側のNode.jsアクセスを無効にし、context isolationとsandboxを有効にしている。

Android／iOSの `android/`・`ios/` は生成物としてgit管理外。ネイティブ設定を追加する場合は、再生成後も再現できるよう `capacitor.config.json` や生成スクリプトへ反映する。OS固有機能は必要に応じてCapacitorプラグイン等で追加する。

Steamの現在の対応範囲はWindows実行物の生成とSteamPipe準備。Steam実績・Steam Cloud・Steamworks購入認証、コントローラー操作の追加、macOS／Linux／Steam Deck向け専用対応は未実装・未検証。ゲーム側の既存タッチ／マウス入力をそのまま使用する。

[Electron公式](https://www.electronjs.org/docs/latest/) / [Capacitor公式](https://capacitorjs.com/docs)

## 保存と更新時の互換性

保存はゲーム側の `localStorage` を継続利用する。保存スキーマの移行はゲーム側で実装する。

| 対象 | 固定する保存先・識別子 |
|---|---|
| Windows | `appData/DragonTide`、セッション `persist:dragon-tide`、origin `dragontide://game` |
| Android | applicationId、origin `https://localhost` |
| iOS | bundle identifier、origin `capacitor://localhost` |

これらは初回配布後の更新で維持する。ゲームの表示名変更と保存先変更は別の判断になる。ブラウザ版の保存をアプリへ自動移行する処理と、OS間クロスセーブは未実装。

**現時点で解消が必要な差分**として、配布基盤はプロフィールv1／ランv2を前提に検査する一方、masterはプロフィールv1／ランv3になっている。masterのコメントにはv3.185.0で世界図を導入し、ランv2を読み捨てる方針が記載されている。最新版を統合すると既存の配布検査はこの差を検知するため、意図する移行方針に合わせて設定・fixture・検査を更新する。

保存形式番号が同じでも、シードから再生成する建物の順序が変わると、破壊状況のbitsetが対応しなくなる可能性がある。世界生成を変更したときは、途中ランを継続できるか、再開始するかを明示し、プロフィールの解放・進行への影響を確認する。

Windowsの保存領域引き継ぎと旧形式fixtureの読込は検査済み。Android／iOSの実際のアプリ更新・再インストール・端末移行での保存挙動は、初回の署名付き配信で確認する対象。

## 頻繁な更新の進め方

配布基盤を統合した後は、ゲームの更新と同じコミットから各OS版を生成する。

1. `prototypes/dragon-tide/index.html` と `assets/` を更新し、`GAME_VERSION` を進める。
2. `release/dragon-tide/` で `npm run release:next` を実行し、配布番号 `buildNumber` を進める。
3. `npm run check` で構文・資産・保存形式・配布番号の整合を検査する。
4. 変更をコミットし、`dragon-tide-vX.Y.Z-build.N` タグを付けてpushする。
5. GitHub Actionsで各OSの成果物を生成する。署名付きAndroid／iOS版は、署名情報設定後にそのタグを指定して手動実行し、`sign_android`／`sign_ios` を有効にする。
6. Steam、Google Play、App Storeへアップロード・提出し、各ストアの更新配信を使う。

CIの自動化は成果物生成まで。ストアへのアップロード、審査提出、本番公開は現実装では手動。masterへの通常pushは共通検査、タグまたは手動実行は全OSビルド、PRは配布コード変更時に全OSビルドを行う。

ゲームの表示版は `GAME_VERSION` から取得する。AndroidのversionCodeとiOSのbuildには `buildNumber` を使う。表示版が同じ包装修正でも配布番号を増やす。既存のタグを付け替えず、修正版には新しい番号を使う。公開済みの過去タグから同一ソースを再ビルドする経路もある。

[コマンド・Secrets・復旧の詳細手順（配布ブランチ）](https://github.com/shuuter-web/game-studio/blob/58d90bdaf7ab90a28c6d2c4277d917bced4619a7/docs/releases/dragon-tide.md)

## アプリ名と登録情報の確定

正式なアプリ名が未定でも開発を継続できる。ストア上の表示名、OS上の表示名、アプリ識別子、保存先をそれぞれ管理する。

- 現状は `Dragon Tide` がWindowsの商品名・ウィンドウ名・EXE名・ZIP名・Steam準備スクリプト等に複数記載されている。名前が決まったら参照箇所をまとめて更新する。
- `com.shuuterweb.dragontide` は仮IDで、`identityConfirmed` はfalse。正式なapplicationId／bundle identifierはストア登録・初回配布前に決める。表示名と同じ綴りにする必要はない。
- Steam App ID・Windows Depot IDはストア側で発行された値を設定する。
- 現状のアイコンはプラットフォーム既定素材。製品用アイコン、ストア画像・説明、価格、サポート情報の用意が残る。
- 開発者アカウント登録、署名情報設定、署名済み提出物の受理、配布基盤PRと最新版ゲームの統合が次の作業。

## 個人販売か法人販売か

現時点の提案は、個人販売を基本案とし、**販売者として公開する名前・住所と、近い将来の法人化予定を先に確認する**こと。少人数で最初の作品を販売する段階では、販売先の技術要件だけを理由に法人化する必要はない。会社名での販売者表示、共同事業の権利保有、法人名義の契約を初回から必要とする場合は、登録前の法人化を検討する。

| ストア | 個人で登録した場合の留意点 | 後から法人化する場合 |
|---|---|---|
| Apple | 個人・個人事業の販売者名には本人の法的氏名が表示される。屋号だけでは組織登録できない | 法人格を用意したうえでAppleへ個人から組織への変更を相談する。組織登録では通常D-U-N-S番号等が必要 |
| Google Play | 開発者表示名は法的氏名と別に設定できるが、法的氏名等も公開される。有料販売では住所全体が公開される | 組織用の支払いプロファイル作成・本人／組織確認などを伴う変更手順がある。本人確認用と販売者用の支払いプロファイルの扱いも確認する |
| Steam | 個人事業として登録可能。契約・口座・税務情報の名義には法的氏名を使う | 法人格変更時はValveへの確認と契約・売上受取先等の変更手続きが必要になるため、設立予定が近ければ登録前に整理する |

税務上どちらが有利かは利益見込み・他の所得・設立維持費などによって変わるため、このメモでは売上額の一律基準を置かない。法人化の判断時に税理士等へ具体的な条件で確認する。

ストア条件は2026-11-26に確認。公式情報は次を参照する。

- [Appleの個人／組織登録と販売者表示](https://developer.apple.com/help/account/membership/program-enrollment/)
- [Google Playの登録情報と公開範囲](https://support.google.com/googleplay/android-developer/answer/13628312?hl=en)
- [Google Playの個人から組織への変更](https://support.google.com/googleplay/android-developer/answer/16260648?hl=en)
- [Steamworksの登録名義FAQ](https://partner.steamgames.com/doc/gettingstarted/faq)

契約への同意、本人確認、支払い、銀行・税務情報の登録は販売者本人が行う。設定・ビルド・署名組込み・提出素材の準備は、それらの決定に合わせて開発側で進められる。
