# Dragon Tide リリース運用

対象はSteam / Windows、Android、iOS。すべて買い切り。共通ソースの更新から各ストア向け成果物を作るための手順をまとめる。設計判断は [ADR-0008](../decisions/ADR-0008-dragon-tide-distribution.md) を参照。

## 実装と検証の現在地（2026-11-06）

GitHub masterのv3.88.2（`d514e58`）を取り込んだ専用ブランチ `feat/dragon-tide-release-pipeline` で実装。元の作業フォルダの未コミット変更は保持している。

- 保存読込・梱包・タグ整合性・Steamファイル照合の13件の自動テストを通過。
- Windows実行ファイルとZIPを生成し、ZIP整合性・全配布ファイルのハッシュを確認。
- 非表示Electronで起動し、同じ保存領域を使って包装前から包装済みアプリへ再起動してもlocalStorageのテスト値が残ることを確認。実際のプロフィールとラン形式は別のfixtureテストで確認。
- Androidプロジェクト生成と再同期で、v3.88.2 / build 1の反映を確認。
- [初回GitHub Actions実行](https://github.com/shuuter-web/game-studio/actions/runs/42136073373)で、共通検査・Windows・Android・iOSの全ジョブが成功。Windows ZIP、Android未署名AABとデバッグAPK、iOS未署名xcarchiveをartifactに保存済み。Windowsでは包装済みアプリの起動・保存領域引き継ぎ検査も通過。
- [ドラフトPR #1](https://github.com/shuuter-web/game-studio/pull/1)でレビュー可能。署名とストア提出は未実施で、正式アプリID・各ストアの資格情報設定が残る。

ゲーム内容の再プレイ・再評価は今回の検証範囲に含めていない。

## 管理するもの

| 対象 | 管理方法 |
|---|---|
| ゲーム本体 | `prototypes/dragon-tide/index.html` と同ディレクトリのアセット |
| 配布の設定・ラッパー | `release/dragon-tide/` |
| 表示バージョン | ゲーム内の `GAME_VERSION`。配布側に別の手入力値を持たせない |
| 配布番号 | `release/dragon-tide/config.json` の `buildNumber`。新しい配布ごとに単調増加 |
| リリースタグ | `dragon-tide-vX.Y.Z-build.N` |
| Windows包装 | Electron 45.2.1 |
| Android / iOS包装 | Capacitor 8.6.0 |

各OSの生成済みゲームを直接修正しない。修正は共通ソースに入れて再生成する。

## 初回配布までに確定する情報

- SteamworksのアプリとWindows向けDepot、アップロードに使う認証方法。
- Google PlayのアプリとAndroid署名情報。
- Apple Developer / App Store Connectのアプリ、署名に使うチーム・証明書等。
- 正式なアプリID。`config.json` の暫定値は `com.shuuterweb.dragontide`。正式な所有・使用を確認し、同ファイルの `identityConfirmed` を `true` にする。Steamの `steam.appId` と `steam.windowsDepotId` も同ファイルに設定する。
- 製品用のアプリアイコン。現在はプラットフォーム既定のアイコンなので、ストア提出前に置き換える。
- ストアの価格、販売地域、説明、画像、サポート情報。

署名情報と認証情報はローカルの安全な設定またはCIのSecretsで渡す。リポジトリやビルドログに書き出さない。識別子・署名・アカウントが未設定の段階では、成果物作成までとストア提出完了を区別する。

## 日常の更新手順

1. 最新の開発基準からゲームを更新する。バグ修正を含む新しいゲーム版では `GAME_VERSION` を更新する。
2. `git fetch origin --tags` でリリースタグを取得する。`release/dragon-tide/` で `npm run release:next` を実行すると、設定値と取得済みタグの最大値より大きい `buildNumber` を `config.json` に書き込み、次のタグ名を表示する。未取得のタグや別の担当者が確保した番号は検出できないため、同時リリースでは番号の割当を調整する。同一ゲーム版の包装修正やストア再提出も別の配布番号にする。
3. セーブ形式、地形生成、アプリID・保存先に変更があるかを確認する。変更があれば下記の互換性判断を行う。
4. `release/dragon-tide/` で依存関係をインストールし、検査と必要な成果物の生成を行う。
5. 変更をコミットし、そのコミットへ `dragon-tide-vX.Y.Z-build.N` のタグを付ける。タグのゲーム版・配布番号とソースを一致させる。
6. タグをpushして未署名ビルドを作る。署名ビルドはGitHub Actionsの手動実行で、そのリリースタグを選び `sign_android` / `sign_ios` を有効にする。CIの成果物、対象コミット、署名の有無を確認し、テスト配信先へ提出する。
7. 起動・アセット同梱・更新時の保存保持を確認し、各ストアの手順で本番公開する。

ゲーム内容の再評価や全ステージの再プレイは、この配布手順の必須ゲートではない。ユーザーが行う通常のテストプレイと分けて、配布に伴う破損を検出する。

## ローカルのコマンド

以下は `release/dragon-tide/` で実行する。Node.js 22以上が必要で、CIは24.14.0を使用する。依存関係はロックファイルに従って取得する。

```powershell
npm ci
npm run check
npm run build:web
```

対象に応じて続ける。

| コマンド | 用途 |
|---|---|
| `npm run build:windows` | Windows向け未署名アプリとZIPの生成 |
| `npm run test:desktop -- --packaged` | 生成したWindows版の起動・保存保持のスモークテスト |
| `npm run mobile:sync -- android` | Androidプロジェクトの生成・同期 |
| `npm run mobile:sync -- ios` | iOSプロジェクトの生成・同期 |
| `npm run release:next` | 次の配布番号を設定し、対応するタグ名を表示 |
| `npm run build:windows -- --release` | 正式な識別子・一致するタグ・clean checkoutを検査してWindows版を生成。実行ファイルへの署名はしない |
| `npm run mobile:sync -- android --release` | 同じ正式配布条件を検査してAndroid版を同期 |
| `npm run mobile:sync -- ios --release` | 同じ正式配布条件を検査してiOS版を同期 |
| `npm run steam:prepare` | 正式配布条件とWindows成果物の一致を確認し、SteamPipe用VDFを生成 |

AndroidはAndroid SDK等、iOSはmacOS / Xcodeと署名環境が必要になる。`mobile:sync` の成功だけでは、署名済みAABやiOSアーカイブの生成・ストア提出の成功を意味しない。ネイティブのビルドと提出は、対象OSのCIまたは開発環境で続ける。

正式配布用コマンドは、`identityConfirmed: true`、`GAME_VERSION` / `buildNumber` に一致するリリースタグ、変更のないcheckoutが必要である。設定をコミットしてタグを付けた後、そのタグから生成する。`steam:prepare` はSteamのID設定に加え、現在のタグ・コミット・識別子に一致するWindows成果物を要求する。VDF生成だけではSteamへアップロードしない。

### 成果物

以下のパスは `release/dragon-tide/` からの相対パス。

| 対象 | 出力 |
|---|---|
| 共通Web | `dist/web/`、`dist/web/release-manifest.json` |
| Windows | `dist/windows/win-unpacked/`、`dist/windows/DragonTide-<version>-build.<N>-windows-x64.zip`、`dist/windows/build-manifest.json` |
| SteamPipe | `dist/steam/app_build_<AppID>.vdf`、`dist/steam/depot_build_<DepotID>.vdf` |
| Android AAB | `android/app/build/outputs/bundle/release/*.aab` |
| AndroidデバッグAPK | `android/app/build/outputs/apk/debug/*.apk` |
| iOSアーカイブ | `dist/ios/DragonTide.xcarchive`、CI保管用の `dist/ios/*.xcarchive.tar.gz` |
| 署名済みiOS IPA | `dist/ios/export/*.ipa` |

Windowsの `build-manifest.json` は成果物のハッシュ等を持つ。配布したZIP・manifest・タグを一組で保存する。CIのartifact保管期間は90日なので、長期保管が必要な正式リリースは期限前に別途保管する。未署名AABと未署名iOSアーカイブは、そのままストア提出用には使わない。

## 保存データを守る

現行プロフィールはv1、ラン保存はv2。アプリの表示版と保存スキーマの版は別に管理する。アプリID、WebView origin、ユーザーデータの保存先を公開後に変更しない。

| 変更 | 更新時の扱い |
|---|---|
| バランス・表示など、保存の読み方を変えない変更 | 既存データをそのまま読み込むことを確認 |
| 保存のフィールド・構造の変更 | 旧版のデータを使い移行処理を確認。新規開始だけで確認を済ませない |
| 地形生成・建物の並びや件数の変更 | ランのbitsetが同じ対象を指すか確認。互換でなければ専用の移行・旧生成方式・ラン再開始方針を設計 |
| アプリID・保存先の変更 | 通常更新として行わず、別途データ移行を設計 |

ランの互換性を維持できないときでも、プロフィールの解放や獲得済みの進行を消すことを既定動作にしない。影響範囲と対処をリリースノートへ記録する。ブラウザ版や他OSからの自動移行・クロスセーブは、この基盤では提供しない。

## CIと公開の境界

CIは検査と成果物作成を担当し、ストアへの実公開は手動で行う。署名を設定していないビルドは未署名として扱い、署名済みと取り違えない。署名情報がある場合のビルドでも、各ストアの審査・公開処理は別途必要である。

ワークフローは `.github/workflows/dragon-tide-release.yml`。対象ファイルのPRとmaster更新では検査を行い、リリースタグのpushまたは手動実行ではOS別成果物を作成する。手動実行の `sign_android` / `sign_ios` は既定で `false`。Windowsは未署名、Androidは未署名AABとデバッグAPK、iOSは未署名xcarchiveを生成する。署名を有効にしたAndroidは署名済みAAB、iOSは署名済みアーカイブとIPAを生成する。

AndroidジョブはJava 21 / Android API 36、iOSジョブは `macos-26` / Xcode 26の環境を使用する。GitHub Environmentsは未署名用 `build-only`、Android署名用 `android-release`、iOS署名用 `ios-release` を使う。必要に応じて署名用Environmentへ承認・タグ制限を設定する。

### 署名用Secrets

GitHubの対応するEnvironmentへ、以下の名前を正確に登録する。

| Environment | Secret | 内容 |
|---|---|---|
| `android-release` | `DT_ANDROID_KEYSTORE_BASE64` | アップロード用キーストアのBase64 |
| `android-release` | `DT_ANDROID_KEYSTORE_PASSWORD` | キーストアのパスワード |
| `android-release` | `DT_ANDROID_KEY_ALIAS` | 署名キーのalias |
| `android-release` | `DT_ANDROID_KEY_PASSWORD` | 署名キーのパスワード |
| `ios-release` | `DT_IOS_CERTIFICATE_BASE64` | Apple Distribution証明書と秘密鍵を含むP12のBase64 |
| `ios-release` | `DT_IOS_CERTIFICATE_PASSWORD` | P12のパスワード |
| `ios-release` | `DT_IOS_PROFILE_BASE64` | アプリID・チームに一致するApp Store配布用プロビジョニングプロファイルのBase64 |
| `ios-release` | `DT_IOS_TEAM_ID` | Apple Developer Team ID |

`DT_ANDROID_KEYSTORE_PATH` はCIが一時ファイルの場所として設定する環境変数で、Secretとして登録する必要はない。iOSのP12は有効な配布用署名identityを1つ含むことが必要。iOSヘルパーはmacOSで `node scripts/ios-signing.mjs build` によりアーカイブとIPAを生成し、使用した一時署名情報を後処理する。中断で署名状態が残った場合は、同じ環境で `node scripts/ios-signing.mjs cleanup` を実行する。ローカルで使う場合も同名の環境変数と `npm run mobile:sync -- ios --release` が必要である。

**署名ビルドと実ストアへの提出は、現時点では未実行。** Secretsを設定しただけで提出可能と判断せず、最初の署名ビルドの成果物とストアでの受理を確認する。

更新はSteamPipe / Google Play / App Storeを通す。独自OTAやアプリ内でのコード差し替えを追加しない。

| 配布先 | テストと本番の分け方 |
|---|---|
| Steam | テスト用ブランチで確認してから本番ブランチへ公開 |
| Google Play | 内部テスト等で確認してから製品版へ公開 |
| App Store | TestFlight等で確認してから審査・公開 |

## ビルド失敗・緊急修正

- ソースを変更しないCI失敗は、原因を解消して同じコミットから再実行する。すでに提出した配布番号を新しい提出に再利用しない。
- ソース・設定・署名条件を変更して新しく提出する場合は、配布番号を増やす。公開済みタグを別コミットへ付け替えない。
- 問題のある配布を停止し、正常だったコミットを基に修正版を作る。モバイルは過去の配布番号へ戻して提出せず、より大きい番号で修正版を提出する。
- Steamで以前のビルドへ戻す場合も、新版が書いたセーブを旧版が読めるかを先に確認する。バイナリを戻すだけではデータの互換性は戻らない。
- リリースごとにタグ、コミット、配布番号、成果物、署名の有無、提出先、セーブ互換性の判断を記録する。

## この基盤と別に残る作業

開発者登録、正式アプリIDの確定、製品用アイコンへの置換、ストアのアプリ作成と商品情報、署名情報の登録、実ストアへの提出・審査・公開は未完了であり、アカウントと設定情報がそろってから行う。Steam実績・クラウドセーブ・コントローラー対応は販売・更新基盤とは別の機能として扱う。

2026-11-03の依存関係検査では、本番依存の `npm audit` 指摘は0件、開発依存を含めるとビルド依存のglob / minimatchに由来するmoderateが16件ある。強制修正によるダウングレードは行っていない。依存更新時に再確認する。
