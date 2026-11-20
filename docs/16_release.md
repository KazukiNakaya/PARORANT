# 16. リリースの手順

exe の作り方と公開先。v1.0（2026-11-10）で試して分かったことを含む。2026-11-17 に v2.1 の時点の内容へ見直した。

## 置き場所

| 何を | どこに |
|---|---|
| 開発の本体（Unreal のアセット、履歴、タグ） | Azure DevOps `PALORANT` |
| README、docs、exe の zip（Release） | GitHub `KazukiNakaya/PARORANT`（Public） |

- Azure DevOps には exe を置く Release 機能がないため、GitHub の Release を使う
- 同じリポジトリを GitHub にも push することはできない。履歴に 100MB を超えるファイル（`download/swat_operator_remastered.glb`）があり拒否される
- GitHub のリポジトリは README と docs のコピーで、Azure とは履歴がつながっていない。作業フォルダは `Release/GitHub`（プロジェクト内、Git の管理外）。`PARORANT.png` と `docs/` と `README.md` をコピーして push する（`orders/` と Unreal のアセットは置かない）
- GitHub は 1 ファイル 100MiB までなので、README のプレイ動画（GIF）はそれより小さく縮めてから置く。元の大きい GIF は `download/gif_original/`（Git の管理外）に残す
- GitHub のリポジトリは Public（誰でも README と zip を見られる）。新しい素材を足すときは、再配布の条件を確認してから載せる

## exe の作り方

**Unreal Editor を閉じてから行う。** MCP 用の `Plugins/EngineWire` を一時的に外す必要があるため。

1. `Plugins/EngineWire` をプロジェクトの外へ移し、`PARORANT.uproject` の `Plugins` から `EngineWire` の行を消す
2. パッケージする

   ```
   RunUAT.bat BuildCookRun -project=<uprojectのフルパス> -noP4 -platform=Win64 -clientconfig=Shipping -build -cook -map=/Game/PARORANT/Maps/L_Canal+/Game/PARORANT/Maps/L_Pind -stage -pak -prereqs -archive -archivedirectory=<出力先> -utf8output -unattended
   ```

3. `PARORANT.uproject` と `Plugins/EngineWire` を元に戻す
4. できた `Windows/PARORANT.exe` を起動し、タイトルと試合の開始を確認する
5. `Windows` フォルダの中身（`Manifest_*.txt` を除く）を `PARORANT-v<番号>-Win64.zip` にする

## なぜ EngineWire を外すのか

外さないと、ビルドは成功しても exe が起動しない。原因の調査の経過と、そのまま使えるスクリプトは [17](17_build_with_enginewire.md) にまとめた。

## バージョンとタグ

- `Config/DefaultGame.ini` の `ProjectVersion` を上げる
- `docs/README.md` の改訂履歴と、`README.md` の更新履歴に行を足す
- 注釈付きタグ `v<番号>` を付け、Azure に push する。GitHub の Release にも同じ名前を使う

## GitHub への反映と Release

1. `Release/GitHub` で `git pull` してから、`README.md`・`PARORANT.png`・`docs/` を上書きコピーする（開発側で消したファイルは GitHub 側でも消す）
2. 差分を確認してコミットし、`main` に push する
3. `gh release create v<番号> <zip> --repo KazukiNakaya/PARORANT --title "PARORANT v<番号>" --notes-file <本文>` で Release を作る。本文は「遊び方」「変更点」「既知の問題」

## 置き場所（ローカル）

リリースに使うものは、プロジェクト内の `Release/` にまとめる（`.gitignore` の対象。ソースの zip にも入らない）。

| フォルダ | 中身 |
|---|---|
| `Release/Builds` | exe のビルド一式（`v<番号>/Windows`）、配布用の zip、ビルドのログ、ソース一式の作業フォルダ |
| `Release/GitHub` | GitHub `KazukiNakaya/PARORANT` の作業用の clone（README・docs のコピー） |

## ソース一式の zip

v2.1 から、GitHub の Release に `PARORANT-v<番号>-Source.zip` も上げる（素材を含めてよいことはユーザーが確認済み、2026-11-20）。

1. Git で管理しているファイルのうち、`docs/`・`orders/`・`Plugins/`（MCP 用の EngineWire）・`.gitattributes`・`.gitignore`・`requirements.txt` を除いたものを `Release/Builds/source_v<番号>/PARORANT/` にコピーする（`git ls-files` から。`download/` や `Saved/` は入らない）
2. コピーした `PARORANT.uproject` から `EngineWire` の項目を消す。`Config/DefaultEngine.ini` の `SecurityToken=`（Android 用のファイルサーバーの値）の行を消す
3. 開き方の案内 `ソースについて.txt` を添える
4. Windows の `tar -a -c -f PARORANT-v<番号>-Source.zip PARORANT` で zip にする（.NET の `ZipFile` は Windows PowerShell 5.1 だとパスの区切りが `\` になるため使わない）
5. `gh release upload v<番号> <zip> --repo KazukiNakaya/PARORANT`
