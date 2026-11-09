# 16. リリースの手順

exe の作り方と公開先。v1.0（2026-11-10）で試して分かったことを含む。

## 置き場所

| 何を | どこに |
|---|---|
| 開発の本体（Unreal のアセット、履歴、タグ） | Azure DevOps `PALORANT` |
| README、docs、exe の zip（Release） | GitHub `KazukiNakaya/PARORANT`（Private） |

- Azure DevOps には exe を置く Release 機能がないため、GitHub の Release を使う
- 同じリポジトリを GitHub にも push することはできない。履歴に 100MB を超えるファイル（`download/swat_operator_remastered.glb`）があり拒否される
- GitHub のリポジトリは README と docs のコピーで、Azure とは履歴がつながっていない。`PARORANT.png` と `docs/` と `README.md` をコピーして push する
- Public にする場合は、使用素材の再配布条件とパロディの権利面を先に確認する

## exe の作り方

**Unreal Editor を閉じてから行う。** MCP 用の `Plugins/EngineWire` を一時的に外す必要があるため。

1. `Plugins/EngineWire` をプロジェクトの外へ移し、`PARORANT.uproject` の `Plugins` から `EngineWire` の行を消す
2. パッケージする

   ```
   RunUAT.bat BuildCookRun -project=<uprojectのフルパス> -noP4 -platform=Win64 -clientconfig=Shipping -build -cook -map=/Game/PARORANT/Maps/L_Pind -stage -pak -prereqs -archive -archivedirectory=<出力先> -utf8output -unattended
   ```

3. `PARORANT.uproject` と `Plugins/EngineWire` を元に戻す
4. できた `Windows/PARORANT.exe` を起動し、タイトルと試合の開始を確認する
5. `Windows` フォルダの中身（`Manifest_*.txt` を除く）を `PARORANT-v<番号>-Win64.zip` にする

## なぜ EngineWire を外すのか

| やったこと | 結果 |
|---|---|
| そのままパッケージ | ビルドは成功するが、exe が何も表示せず終了する。Development 版のログに `Unable to load plugin 'GameplayAbilities'. Aborting.`。EngineWire が依存先として有効にするプラグインを、付属の `UnrealGame` が読み込めない |
| `EngineWire` に `"TargetAllowList": ["Editor"]` を付ける | プロジェクト専用の実行ファイルのコンパイルが必要になる。エディタ起動中は Live Coding で止まり、閉じても UE 5.3 と新しい Visual Studio の組み合わせで `__has_feature`（C4668）のエラーになる |
| `-skipbuild` | `PARORANT-Win64-Shipping.target` が無いと言われ失敗する |
| **EngineWire を外してパッケージ** | コンパイル不要で成功し、起動する |

Shipping 版はログを出さないので、起動しないときは `-clientconfig=Development` で作って `Windows/PARORANT/Saved/Logs/PARORANT.log` を読む。

## バージョンとタグ

- `Config/DefaultGame.ini` の `ProjectVersion` を上げる
- `docs/README.md` の改訂履歴と、`README.md` の更新履歴に行を足す
- 注釈付きタグ `v<番号>` を付け、Azure に push する。GitHub の Release にも同じ名前を使う
