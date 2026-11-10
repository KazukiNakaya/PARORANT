# 17. EngineWire を入れた Blueprint プロジェクトの exe 化

v1.0 のパッケージで起きた問題と、解決までの経過、次回から使う手順の記録。公開先やタグの付け方は [16](16_release.md) にある。

## 1. 結論

**パッケージの間だけ `Plugins/EngineWire` と `PARORANT.uproject` の `EngineWire` の行を外す。** これでコードのコンパイルが不要になり、起動する exe ができる。パッケージが終わったら両方を元に戻す。

## 2. 環境

| 項目 | 内容 |
|---|---|
| エンジン | Unreal Engine 5.3（Epic Games Launcher 版） |
| プロジェクト | Blueprint のみ（C++ のモジュールなし） |
| プラグイン | `Plugins/EngineWire`（Editor を MCP で操作するためのプラグイン） |
| コンパイラ | Visual Studio 2022 |
| 出力 | Win64 / Shipping |

`EngineWire.uplugin` のモジュール 3 つはすべて `Editor` 用だが、依存プラグインを 39 個有効にしている。その中に `GameplayAbilities`、`Niagara`、`EnhancedInput` などがある。

## 3. 手順

Unreal Editor を**閉じて**から、PowerShell で次を実行する。失敗しても `finally` でプラグインと uproject は元に戻る。

```powershell
$proj = "C:\Users\kazuk\Documents\Repository\UnrealEngine\PARORANT"
$rel  = "C:\Users\kazuk\Documents\PARORANT_Release"
$ver  = "v1.0"
$up   = "$proj\PARORANT.uproject"
$bak  = "$rel\PARORANT.uproject.bak"
$pl   = "$proj\Plugins\EngineWire"
$tmp  = "$rel\_EngineWire_tmp"

if (Get-Process | Where-Object { $_.Name -like "UnrealEditor*" }) { throw "エディタを閉じてください" }
if (Test-Path $tmp) { throw "前回の退避が残っています: $tmp" }

Copy-Item $up $bak -Force
Move-Item $pl $tmp
try {
  $j = Get-Content $up -Raw -Encoding UTF8 | ConvertFrom-Json
  $j.Plugins = @($j.Plugins | Where-Object { $_.Name -ne "EngineWire" })
  [IO.File]::WriteAllText($up, ($j | ConvertTo-Json -Depth 6), (New-Object Text.UTF8Encoding($false)))

  & "C:\Program Files\Epic Games\UE_5.3\Engine\Build\BatchFiles\RunUAT.bat" BuildCookRun `
    -project="$up" -noP4 -platform=Win64 -clientconfig=Shipping -build -cook `
    -map=/Game/PARORANT/Maps/L_Pind -stage -pak -prereqs `
    -archive -archivedirectory="$rel\$ver" -utf8output -unattended *> "$rel\package_$ver.log"
  "EXIT=$LASTEXITCODE"
} finally {
  Copy-Item $bak $up -Force
  Move-Item $tmp $pl
}
```

終わったら次を確認する。

1. `EXIT=0` で、ログの最後が `BUILD SUCCESSFUL`
2. `git status` に `PARORANT.uproject` と `Plugins/EngineWire` の変更が出ていない
3. `<出力先>\Windows\PARORANT.exe` を起動し、タイトルが出て「プレイ」で試合が始まる
4. タスクマネージャーでのプロセス名は `UnrealGame-Win64-Shipping`（`PARORANT.exe` は起動用の小さな exe）

v1.0 の所要時間は、シェーダーのキャッシュが無い初回で約 13 分、キャッシュがある 2 回目以降で 1〜2 分。zip にすると 390MB。

## 4. 試したことと結果

| # | やったこと | 結果 | 分かったこと |
|---|---|---|---|
| 1 | Git Bash から `cmd //c RunUAT.bat` | バッチが見つからず、すぐ終了 | PowerShell からフルパスで呼ぶ |
| 2 | そのままパッケージ（Shipping） | ビルドは成功。exe は画面もエラーも出さずに終了（終了コード 1） | Shipping はログを出さないので、ここでは原因が分からない |
| 3 | 本体の exe を引数 `PARORANT` で直接起動 | `ICU data directory was not discovered` | **引数の誤りによる別のエラーで、原因とは無関係**。起動用 exe が渡す引数は `../../../PARORANT/PARORANT.uproject` |
| 4 | `EngineWire` に `"TargetAllowList": ["Editor"]` を指定（エディタ起動中） | `Unable to build while Live Coding is active`（終了コード 6） | この指定にすると、プロジェクト専用のコンパイルが走るようになる |
| 5 | 4 の設定のまま `-skipbuild` | `Missing receipt ... PARORANT-Win64-Shipping.target`（終了コード 103） | コンパイルを省略できない |
| 6 | 4 の設定でエディタを閉じてビルド | `ConcurrentLinearAllocator.h(31): error C4668: '__has_feature'`（終了コード 6） | UE 5.3 のヘッダーが今のコンパイラで通らない。エンジン本体の修正は避けた |
| 7 | uproject を元に戻し、Development でパッケージ | 成功。exe は終了するが、ログに `LogPluginManager: Error: Unable to load plugin 'GameplayAbilities'. Aborting.` | **ここで原因が判明** |
| 8 | EngineWire を外して Shipping でパッケージ | 成功。タイトルと試合開始を確認 | 解決 |

## 5. 原因

| | 内容 |
|---|---|
| 確認済み | 配布版の起動時に `GameplayAbilities` の読み込みに失敗して終了する（#7 のログ） |
| 確認済み | `GameplayAbilities` は `EngineWire.uplugin` の依存に含まれ、`PARORANT.uproject` 自体には書かれていない |
| 確認済み | EngineWire を外すと起動する（#8） |
| 確認済み | 外した状態ではコンパイルなしで、エンジン付属の `UnrealGame-Win64-Shipping.exe` が使われる |
| 推測 | 付属の `UnrealGame` には `GameplayAbilities` のコードが入っておらず、依存として要求されたプラグインを読み込めない |
| 推測 | `TargetAllowList` を付けると、プラグインの有効・無効が既定と異なるため、UAT がプロジェクト専用のビルドが必要と判断する |

## 6. つまずきやすい点

- **起動しないときは、まず Development でパッケージする。** Shipping はログを出さない。ログは `<出力先>\Windows\PARORANT\Saved\Logs\PARORANT.log` にできる
- **PowerShell の `*>` で書いたログは UTF-16 になる。** Git Bash の `grep` では何もヒットしないので、`Get-Content` と `Select-String` で読む
- **失敗したビルドの副産物を消す。** プロジェクト直下の `Binaries/` と `Plugins/EngineWire/Intermediate/` は、#4〜#6 の試行でできたもの。どちらも再生成できる
- **ゲームが依存プラグインの機能を使い始めたら、この手順は見直す。** v1.0 は外した状態で動いているが、確認したのはタイトルと試合開始まで（ユーザーも exe からの起動を確認済み）

## 7. 試していないこと

| 案 | 内容 |
|---|---|
| `"Enabled": false` だけにする | フォルダを動かさずに済むかもしれないが、#4 と同じくコンパイルが必要になる可能性がある |
| 古い MSVC ツールセットを入れる | #6 の解消が期待できる。将来 C++ を足すなら必要になる |
| EngineWire 側で依存を減らす | プラグインの作者側の対応になる |
