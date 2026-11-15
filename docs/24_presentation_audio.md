# 24. 演出と音の実装仕様（Step 33・36）

方針は [20](20_canal_town_concept.md) §8。進め方は [21](21_impl_rules.md)。2026-11-12 作成。

## 1. 範囲

| Step | 内容 |
|---|---|
| 33 | 連続キルの音、ラウンド終了の称号、やられた理由の表示 |
| 36 | 環境音と音楽 |

キルログは Step 32（[23](23_bot_human.md) §6.2）。

## 2. Step 33：連続キルの音

- `BP_PR_GameMode.RoundKills`（そのラウンドでプレイヤーが倒した数。`StartRound` で 0）
- `AddKill` で `RoundKills` を増やし、`SFX_Kill` をピッチを変えて鳴らす

| 何人目 | ピッチ |
|---|---|
| 1 | 1.00 |
| 2 | 1.12 |
| 3 | 1.26 |
| 4 | 1.41 |
| 5 以上 | 1.59＋`SFX_Ace`（新規、和音） |

- 敵が 3 人の難易度では、3 人目（全滅）で `SFX_Ace` も鳴らす
- ヘッドショットの音（`SFX_Headshot`）は今のまま重ねる
- 画面中央下に、キルのたびに 1.2 秒だけ印（1〜5 個の菱形）を出す

## 3. Step 33：ラウンド終了の称号

勝ったラウンドで、条件に合うものを 1 つだけ、結果の文字（ROUND WIN）の下に出す。上にあるものを優先する。

| 称号 | 表示 | 条件 |
|---|---|---|
| エース | `ACE` | そのラウンドの敵を全員、自分で倒した（爆発で倒れた敵がいない） |
| 無傷 | `FLAWLESS` | 体力もアーマーも減らずに勝った |
| クラッチ | `CLUTCH` | 勝った時点の体力が 30 以下、または設置後に敵 2 人以上を倒して勝った |
| 節約 | `THRIFTY` | メイン武器なし（ハンドガンかナイフだけ）で勝ち、敵の誰かがスペクターかヴァンダルを持っていた |
| 滑り込み | `JUST IN TIME` | 残り 5 秒以内に設置して勝った |

負けたラウンドは、理由を 1 行で出す（今の `ResultText` を整理）：`解除された` / `時間切れ` / `倒された`。

- 判定は `EndRound` で行う。必要な記録（受けたダメージの合計、設置時の残り時間、設置後のキル数、敵の武器）を `BP_PR_GameMode` に足す
- 称号が出たら `SFX_Title`（新規、短い和音）を鳴らす
- リザルト画面（`WBP_Result`）に、試合で取った称号の数を 1 行で出す（例：`ACE ×1  CLUTCH ×2`）
- 味方 Bot（Step 37）を入れた後：エースは「自分で全員倒した」のまま。味方が倒した敵がいれば付かない

## 4. Step 33：やられた理由の表示

プレイヤーが倒されたとき、死亡演出（[14](14_playtest_fixes.md) §6）の倒れた視点のまま、画面の右側に出す。次のラウンドのキャラクターが出たら消す。

| 表示 | 内容 |
|---|---|
| 倒した相手 | 名前、武器、距離（m）、ヘッドショットかどうか |
| 受けたダメージ | そのラウンドに受けた分を、相手ごとに合計（例：`kado_machi  ヴァンダル  140（2 発、頭 1）`） |
| 与えたダメージ | そのラウンドに与えた分を、相手ごとに合計と残り体力（例：`ponkotsu_aim  84（3 発）  残り 16`） |
| 相手の位置 | 倒した Bot の、撃った瞬間の位置に印を 4 秒出す（リコンと同じ壁越しの菱形）。ミニマップにも赤い点 |

- 記録：ダメージの共通処理（`TakeWeaponDamage`）に、与えた側・受けた側・量・部位を `BP_PR_GameMode` の配列へ足す処理を入れる。`StartRound` で空にする
- 爆発で倒れたときは「スパイクの爆発」とだけ出す
- ねらい：「どこから撃たれたか分からない」理不尽さを減らし、与えたダメージで「惜しかった」を見せる
- 完了条件：Bot に倒されて、名前・武器・距離・ダメージの内訳が実際と合う。印が撃たれた方向に出る。次のラウンドで消える

## 5. Step 36：環境音と音楽

### 5.1 作り方
追加のツールは使わない。今の効果音と同じく、Python（numpy）で合成して wav を書き出す（`SourceAudio/gen.py` の方式）。新しいスクリプト `SourceAudio/gen_ambience.py` を作る。

- 合成でできるのは、単純な音（鐘、警報、水のさざ波、鼓動、持続音）まで。本物の録音のような環境音や、旋律のある曲は作れない
- 後から、録音素材や AI で作った音に差し替えられるよう、アセット名を固定する（差し替えるだけで済む）

### 5.2 作る音
| アセット | 長さ | 中身 | 使う場面 |
|---|---|---|---|
| `AMB_Canal` | 30 秒ループ | 水のさざ波（低域を通したノイズに、ゆっくりした揺れ）、弱い風、ときどき遠い鳥（短い高音のさえずり） | 試合中ずっと、音量 0.25 |
| `AMB_Indoor` | 20 秒ループ | こもった持続音 | A の屋内にいる間、`AMB_Canal` と入れ替え（任意。時間が無ければ省く） |
| `SFX_Bell` | 2.5 秒 | 鐘（倍音がずれた複数の正弦波、長い減衰） | 跳ね橋の予告〜上がっている間、1.5 秒ごと |
| `SFX_BridgeMove` | 1 秒 | 木のきしみ（低いのこぎり波＋ノイズ） | 橋が上がる・下りる |
| `MUS_Last10` | 10 秒 | 時計の刻み（0.5 秒ごと）が後半 0.25 秒ごとになる、低い持続音がせり上がる | 戦闘フェーズの残り 10 秒（未設置のとき） |
| `MUS_PostPlant` | 8 秒ループ | 低い持続音と鼓動（2 拍）。設置後のビープ（今の `SFX_Beep`）と重なってよい音域にする | 設置後フェーズ |
| `MUS_Title` | 20 秒ループ | 静かな和音の移り変わり（任意） | タイトル |
| `SFX_Ace` / `SFX_Title` | 1 秒 | 和音 | Step 33 |

- ループ音は、頭と末尾を 0.5 秒かけて重ねてつなぐ（切れ目で音が跳ねないように）。取り込み後、SoundWave の Looping を有効にする
- wav は `SourceAudio/` に置き、`/Game/PARORANT/Audio/` へ取り込む

### 5.3 鳴らし方
- `BP_PR_GameMode` に AudioComponent を 2 つ（環境音用、音楽用）。フェーズの切り替えで出し入れする。切り替えは 0.5 秒のフェード
- 環境音は、試合開始（`StartRound` の初回）から流し続ける
- 音楽の音量は効果音・足音より小さくする（足音が聞こえなくなると遊びが壊れる）。初期値 0.35
- 設定画面に「音楽」「環境音」の音量（0〜100%）を足し、保存する（感度と同じ保存先）

### 5.4 完了条件
- ループの切れ目で音が跳ねない（波形の先頭と末尾の差を数値で確認）
- フェーズごとに正しい音が鳴る・止まる（ログ `[Audio] music=PostPlant`）
- **耳での確認はユーザーに頼む**（音量のバランス、足音が聞こえるか、うるさくないか）

## 6. Step 33 の実装結果（途中、2026-11-13。ここで一度止めた）

済み（コンパイル 0 エラー。**PIE ではまだ動かしていない**）：
- 音：`SourceAudio/gen_pres.py`（`gen.py` は再実行しない。既存 wav を書き換えないため）で `SFX_Ace.wav`（1.000 秒、最大振幅 0.761）と `SFX_Title.wav`（0.800 秒、最大振幅 0.708）を合成し、`/Game/PARORANT/Audio/` に取り込んだ。聞こえ方は未確認
- `.venv`（プロジェクト直下）を作り、numpy を入れた（`requirements.txt`）。`.gitignore` に `/.venv/` と `__pycache__/` を足した
- `BP_PR_GameMode` の変数：`RoundKills`、`KillsAfterPlant`、`PlantRemain`（-1）、`DmgTaken`、`RoundTitle`、`TitleAce/Flawless/Clutch/Thrifty/JIT`、Tuning の `KillPitch`（1.0/1.12/1.26/1.41/1.59）、`KillMarkTime` 1.2、`AceKillMin` 5、`ClutchHP` 30、`ClutchKills` 2、`JitSec` 5、`RevealSec` 4。ダメージ記録用（まだ書き込む処理なし）：`TkName/TkAmt/TkShots/TkHeads/TkWeap`、`DlName/DlAmt/DlShots/DlLeft`、`KillerName/KillerWeap/KillerDist/KillerHead`、`DeathInfoStr`、`bDeathInfo`、`TmpInfo`、`TmpHeavy`
- `BP_PR_GameMode.KillFx`（`RoundKills`+1、設置後なら `KillsAfterPlant`+1、`KillPitch[min(n,5)-1]` を出力、`RoundKills`≧5 または ≧`StartBots` で `SFX_Ace`、ログ `[Audio] kill n=… pitch=… ace=…`）。`AddKill` の `SetStatKills` の後に挟み、出力の `Pitch` を既存の `SFX_Kill` の `PlaySound2D` のピッチにつないだ
- `RoundInit`（`StartRound` の `Set ResultText` の後。ラウンドの記録を 0 に戻し、ダメージ記録の配列を空にする）、`PlantHook`（`PlantSpike` で `SpawnActor Spike` の直後、`PhaseEndTime` を上書きする前に `PlantRemain` ＝ 残り時間を記録）
- `WBP_GameHUD`：TextBlock `KillMark`（画面中央下、下端から 230、中央揃え）、`TitleText`、`DeathInfoBox`（この 2 つは配置の調整がまだ）、関数 `UpdatePres`（`UpdateFeed` と `UpdateDeathHide` の間。菱形 1〜5 個を `LastKillTime` から `KillMarkTime` 秒だけ出す。`RoundTitle` を `Phase`≧3 で、`DeathInfoStr` を `bDeathInfo` のとき出す）

未実装（次にやること）：
1. `JudgeTitle(bWin, Reason)`（`EndRound` の `DecideAttack` の後。優先順位 ACE > FLAWLESS > CLUTCH（生きていて体力 ≦ `ClutchHP`、または `KillsAfterPlant` ≧ `ClutchKills`）> THRIFTY（`PrimaryId` が None かつ敵に Spectre／Vandal。`GetAllActorsOfClass(BP_PR_Bot)` で `WeaponId` を調べる）> JUST IN TIME（`PlantRemain` が 0 以上 `JitSec` 以下）。負けは `SPIKE DEFUSED`→解除された、`TIME UP`→時間切れ、`KILLED`→倒された）、`SFX_Title`、`TitleSummary`、`WBP_Result` の 1 行
2. ダメージ記録：`BP_PR_Bot` の `TakeWeaponDamage`（`SetArmor` の後）と `BP_PR_Character` の `TakeWeaponDamage`（`Set Armor` の後。`DmgTaken` もここで足す）から GameMode の `LogDealt`／`LogTaken` を呼ぶ。`KilledHook` の呼び出し（Tick の `Killed Hook` の後）から `BuildDeathInfo`（文字列の組み立て、`bDeathInfo`、倒した Bot の `RevealUntil` を今＋`RevealSec`）
3. `TitleText`、`DeathInfoBox` の配置（アンカー、`copyStyleFrom` で `KillFeedBox` の縁取り）、PIE での確認とスクリーンショット（`docs/images/pres33_*.png`）

## 7. Step 33 の実装結果（続き、2026-11-13）

確認は L_Canal の PIE（イージー）。画像は `docs/images/pres33_*.png`。

### 7.1 連続キル（§2）
- `AddKill` を呼ぶと `[Audio] kill n=1 pitch=1.0 ace=false` → n=2 1.12 → n=3 1.26 `ace=true`（敵 3 人なので全滅）→ n=4 1.41 → n=5 1.59。`KillPitch` の既定値は 1.0／1.12／1.26／1.41／1.59。`StartRound` で `RoundKills` が 0 に戻り、次の `AddKill` は n=1。`ace=true` の分岐で `SFX_Ace` の `PlaySound2D` を呼ぶ（聞こえ方は未確認）
- `KillMark`：`◆` は文字化けせず、画面中央下、スキル表示の上に出る（`pres33_killmark.png`、5 個）
- 敵 3 人のとき、`StartBots` 以上は `ace=true` のままなので 4 個目以降も true（3 人しかいないので実際には起きない）

### 7.2 称号（§3）
- 追加：`JudgeTitle(bWin, Reason)`（`EndRound` の `DecideAttack` の後）、`TitleCode`（純粋な判定。1 ACE、2 FLAWLESS、3 CLUTCH、4 THRIFTY、5 JUST IN TIME、0 なし）、`TitleSummary`（リザルトの 1 行）、変数 `ClutchHPRate`（0.3。CLUTCH の体力の条件を最大体力の 30％以下にした。`ClutchHP` は使わなくなった）
- 勝ち：条件を満たす最初の称号を `RoundTitle` に入れて `SFX_Title` を鳴らし、`TitleAce` など 5 つの回数を足す。THRIFTY は `GetAllActorsOfClass(BP_PR_Bot)` で Spectre／Vandal を持つ Bot を調べ、プレイヤーの `PrimaryId` が None のとき
- 負け：`SPIKE DEFUSED`→解除された、`TIME UP`→時間切れ、`KILLED`→倒された を `RoundTitle` に入れる（音なし）
- 確認：変数（`RoundKills` など）を設定して `EndRound` を呼び、5 種類すべてで `RoundTitle` と回数が増えること、`EndRound(false, "SPIKE DEFUSED")` で `解除された` になることを確認。ACE は敵 3 人・キル 3、FLAWLESS は被ダメージ 0、CLUTCH は設置後キル 2、THRIFTY は Spectre／Vandal の Bot がいてメイン武器なし、JUST IN TIME は `PlantRemain` 3。画面：`TitleText` を結果の文字（ROUND WIN／LOSS）の下に出す（`pres33_deathinfo.png` の「倒された」の行）。最初は結果の文字と重なったので位置を y=-100 に下げた。勝ちの称号の実画面の撮り直しは未実施（最初の位置で FLAWLESS が出ることだけ確認）
- `WBP_Result`：`ResTitles` を `ResHS` の下に追加し、`称号  ACE ×1   CLUTCH ×2` の形（なければ `なし`）。コンパイルは通ったが、リザルト画面を開いての見た目は未確認

### 7.3 やられた理由（§4）
- 追加（GameMode）：`LogTaken`（`TkName/TkAmt/TkShots/TkHeads/TkWeap` に相手ごとの合計。`DmgTaken` も足す）、`LogDealt`（`DlName/DlAmt/DlShots/DlLeft`）、`FmtTaken`／`FmtDealt`（1 行の文字列）、`BuildDeathInfo(KName, KWeap, KDist, bHead)`（`DeathInfoStr` と `bDeathInfo`。`KName` が空なら「スパイクの爆発で倒された」だけ）
- 呼び出し：`BP_PR_Character.LogTakenHook`（`TakeWeaponDamage` の、チートでもリコール中でもない側。`SetHealth` の前）、`BP_PR_Character.DeathInfoHook`（Tick の `KilledHook` の後。倒した Bot の `RevealUntil` を今＋`RevealSec` にする）、`BP_PR_Bot.DealtHook`（`TakeWeaponDamage` の `SetArmor` の後。与えた側がプレイヤーのときだけ。残りは `max(Health, 0)`）
- 配置：`DeathInfoBox` は右中央（アンカー右・縦中央、位置 x=-24 y=90、幅 560、高さ 380、右揃え、文字 20、縁取りは `KillFeedBox` と同じ）。キルログ（右上）、チャット（左下）、スキル、武器名と重ならない
- 確認（`pres33_deathinfo.png`）：Bot にダメージを与え（sirokuma 30×2、W_key_only 50 の頭）、プレイヤーが neko_no_te（Sheriff）から 80×2、W_key_only（Classic）から 150 の頭で倒された。表示は「倒された W_key_only Classic 37m HEADSHOT」「受けたダメージ neko_no_te Sheriff 160（2 発、頭 0）／W_key_only Classic 150（1 発、頭 1）」「与えたダメージ sirokuma 60（2 発）残り 80／W_key_only 50（1 発）残り 83」で、記録と一致。別の回で 500 ダメージ 1 発の被ダメージ（`sirokuma Classic 500（1 発、頭 0）`）も確認
- 相手の位置の印：倒した Bot の `RevealUntil` が今＋4（88.6）になることを確認。リコンの `RevealOne` が期限内の Bot を薄い輪郭で出す（`pres33_reveal_lit.png`。`RevealUntil` を大きくした Bot）。死亡直後の撮影（`pres33_reveal.png`）では、撮るまでに 4 秒（ゲーム時間）経っていて出ていなかった
- 仕様との差分：位置は「撃った瞬間」ではなく、倒した Bot の今の位置を `RevealSec`（4 秒）の間出す（リコンの再利用）。ミニマップの赤い点は未実装。距離は倒された時点の `GetDistanceTo`÷100（m）。爆発で倒れたときの文字は `BuildDeathInfo` に実装したが、実際の爆発では未確認（`KillerName` の判定は Bot へのキャスト失敗）

### 7.4 実行ログ・未確認
- `Saved/Logs/PARORANT.log` の `Blueprint Runtime Error` は 0 件。`Accessed None` はすべて AssetCheck の lint 警告（実行時ではない）
- 一時的に変えたもの：`BP_PR_GameInstance.bSkipTitle` を true にして PIE を起動し、確認後に false へ戻した。PIE 内の変数（`KillMarkTime`、`RoundKills` など）は PIE の終了で破棄
- 未確認：`SFX_Ace`／`SFX_Title` の聞こえ方、爆発で倒されたときの表示、実戦（実際に撃ち合って倒される）での記録、ミニマップの赤い点（未実装）

### 7.5 Step 33 の未確認の確認（Step 34 の最初、2026-11-13）
- 勝ちの称号の画面：`EndRound(true, …)` を呼んで確認。ACE（`pres33_title_ace.png`）と JUST IN TIME（`pres33_title_jit.png`、いちばん長い）が、結果の文字（ROUND WIN - SPIKE DEFUSED）の下に出て、重ならず、はみ出さない。位置の変更は不要
- `SFX_Title`：`JudgeTitle` の再生の直後にログ `[Audio] title code=N` を足した。`JudgeTitle` を呼んで `[Audio] title code=2` が出て、再生の呼び出しが通ることを確認（聞こえ方は未確認）
- リザルト画面の称号の行：`ShowResult` を呼んだ画面を撮影（`pres33_result.png`。`称号  FLAWLESS ×1   CLUTCH ×2   JUST IN TIME ×1`）。**直した点**：`ResTitles` がボタンの下に付いて接していたので、`Col` の `ResHS` の次（ボタンの上）に移し、余白（上 8・下 16）を付けた。`WBP_Result` を再コンパイルしないとプレビューに反映されない

## 8. Step 36 の実装結果（環境音と音楽、2026-11-13）

確認は L_Canal の PIE（`bSkipTitle` を一時的に true、確認後に false へ戻した）。**聞こえ方（音色、音量のバランス、ループの違和感）は未確認**。画像：`docs/images/audio36_setting.png`（`preview_widget`）、`audio36_setting_pie.png`（PIE の設定画面）。

### 8.1 作った音（`SourceAudio/gen_ambience.py`、`../.venv/Scripts/python gen_ambience.py`。モノラル 44.1kHz、`/Game/PARORANT/Audio/` に取り込み）
| アセット | 長さ | 最大振幅 | 先頭と末尾の差 \|x[0]-x[-1]\| | つなぎ目の前後の 1 サンプルの差（先頭／末尾） | 使い方 |
|---|---|---|---|---|---|
| `AMB_Canal`（ループ） | 30.000 秒 | 0.781 | 0.00421 | 0.00543 ／ 0.00293 | 試合中ずっと。音量 0.25 |
| `MUS_PostPlant`（ループ） | 8.000 秒 | 0.781 | 0.00323 | 0.00330 ／ 0.00327 | 設置後（Phase 2） |
| `MUS_Last10` | 10.000 秒 | 0.781 | 0.00143（ループしない） | － | 戦闘の残り 10 秒（未設置） |
| `SFX_Bell`（作り直し） | 2.500 秒 | 0.684 | 0（末尾を 0.06 秒で消す） | － | `BP_Drawbridge`（Step 35 のまま） |
| `SFX_BridgeMove` | 1.000 秒 | 0.586 | 0.00003 | － | 橋が上がる・下りる（`StartRaise`／`StartLower` に追加） |

- ループは「周期の整数倍だけで作る」ので、先頭と末尾が数学的につながる（ノイズは FFT の帯域成形＝円状、持続音は周期に整数回、鳥・鼓動の余韻は先頭へ回り込ませる）。仕様の「0.5 秒の重ね」の代わりにこの方式。つなぎ目の差は、隣り合うサンプルの差と同じ大きさ（`MUS_PostPlant` は鼓動の立ち上がりがつなぎ目にないので、平均の差の 2.6 倍に見えたのは全体の平均が小さいため。つなぎ目の前後の差は 0.0033 で同じ）
- `AMB_Canal`＝低域のノイズ（80〜700Hz）に周期 5・3・7.5 秒の揺れ＋小さな波（600〜2500Hz）＋弱い風（40〜260Hz）＋遠い鳥 9 回（2.6〜3.6kHz の短い上昇／下降）。`MUS_PostPlant`＝55／82.5／110Hz の持続音＋鼓動（0.8 秒ごと、ドッ・ドッの 2 拍、低音）。`MUS_Last10`＝55→82.4Hz の持続音がせり上がり、時計の刻み（前半 0.5 秒ごと、後半 0.25 秒ごと）。`SFX_Bell`＝330Hz 基準の倍音がずれた 9 本の正弦波（うなり付き）と叩いた雑音
- 取り込みは `/Game/PARORANT/Audio/<名前>.<名前>` の形で指定（二重フォルダにならない）。`AMB_Canal`／`MUS_PostPlant` は `bLooping`=true。`gen.py` は実行していない
- 作らなかったもの（仕様で任意）：`AMB_Indoor`、`MUS_Title`

### 8.2 足した変数・グラフ
- `BP_PR_GameMode`：AudioComponent 3 個（`AmbComp`、`MusLast`、`MusPlant`。すべて `bAutoActivate`=false。`MusLast`／`MusPlant` は固定の音を持つ）。変数（Audio）`AmbOn`、`CurMusic`（0 なし／1 Last10／2 PostPlant）、`MusicBaseVol` 0.35、`AmbBaseVol` 0.25（開始時に `MapInfo.AmbVolume` から入る）、`Last10Sec` 10、`AudioFade` 0.5
- 関数：`AudioTick`（`MatchTick` の `SetCheatLastT` の後、フェーズの分岐の前に挿入。0.1 秒ごと）、`SetMusic(Id)`、`ApplyAudioVol`
- `BP_PR_MapInfo`：`AmbSound`（クラスの既定は None＝鳴らない。L_Canal の `BP_PR_MapInfo_C_0` に `AMB_Canal` を設定してレベルを保存）、`AmbVolume`（0.25）
- `SG_PR_Settings`／`BP_PR_GameInstance`：`MusicVol`、`AmbVol`（既定 1.0＝100％。0〜1）。`SetMusicVol(Value)`／`SetAmbVol(Value)`（0〜1 に丸め→保存→`GameMode.ApplyAudioVol`）。`SaveSens`（保存の直前に 2 つを書く）、`LoadSens`（0〜1 に丸めて読む）
- `WBP_KeyBinds`：`ChatRow` の下に `MusRow`／`AmbRow`（ラベル、幅 360 のスライダー、`NN%` の文字。`SensRow` と同じ作り）、`UpdateMusText`／`UpdateAmbText`、`OnValueChanged(MusSlider／AmbSlider)`、`Construct` の最後でスライダーと文字を `GameInstance` の値にする
- `BP_Drawbridge`：`StartRaise`／`StartLower` の最後に `SFX_BridgeMove` の `PlaySoundAtLocation`（橋の中央、音量 0.8）。仕様の表にあったが Step 35 で未配線だったため

### 8.3 動き（仕様との対応）
- 環境音：`MatchTick` の最初の 1 回（イントロの後）で `MapInfo.AmbSound` が有効なら `SetSound`→`FadeIn`（0.5 秒）。`Phase`≦3 の間ずっと鳴る（ラウンドの切り替えでは止まらない）。`Phase`==4（試合終了、リザルト）で `FadeOut`。L_Pind（`AmbSound` なし）は鳴らない
- 音楽：`Phase`==2 → `MUS_PostPlant`。`Phase`==1 かつ 残り（`PhaseEndTime`−今）≦ `Last10Sec` → `MUS_Last10`。それ以外は無し。変化があるときだけ、前の音を `FadeOut`、新しい音を `FadeIn`（0.5 秒）。残り 10 秒に設置すると Last10 が消えて PostPlant が入る（同時に 0.5 秒重なる）。ラウンド終了（`Phase`==3）で止まる
- 音量：環境音＝`AmbBaseVol`×`AmbVol`、音楽＝`MusicBaseVol`×`MusicVol`（再生側で `SetVolumeMultiplier`。既存の音量設定が無いので、SoundClass／SoundMix は使っていない）。`ApplyAudioVol` は `AudioTick` が毎回呼ぶほか、設定のセッターが直接呼ぶ（設定画面を開くとゲームが止まり、`MatchTick` のタイマーも止まるため）
- Bot の聴覚（`CheckHearing`）、既存の効果音には触っていない

### 8.4 確認（ログと数値）
- 環境音：`[Audio] amb start`（イントロ後）。`au.DumpActiveSounds` で `AMB_Canal` が 1 つ、音量 0.25。ラウンド 1→2 をまたいでも `AmbOn` は true のまま、再開始のログは出ない（二重にならない）
- Last10：`PhaseEndTime` を今＋約 25 秒にして待つと `[Audio] music=Last10 fade in`（10:53:27）、ラウンド終了で `music=Last10 fade out`（10:53:37、約 10.3 秒後）。`Phase`=2 にすると `music=PostPlant fade in`、`EndRound(true, "SPIKE DEFUSED")` の呼び出しで `music=PostPlant fade out`。`au.DumpActiveSounds`：`AMB_Canal`＋`MUS_PostPlant` の 2 つ（二重なし）
- 試合終了：`PlayerScore`=99、`Phase`=3、`PhaseEndTime`=0 で `Phase` 4 になり `[Audio] amb stop`、`AmbComp.bIsActive`=false
- 設定：`SetMusicVol(0.5)` で `MusLast`／`MusPlant` の `VolumeMultiplier` が 0.35→0.175、`SetAmbVol(0.4)` で `AmbComp` が 0.25→0.1（すぐ反映）。PIE を止めて起動し直すと `GameInstance.MusicVol`=0.5、`AmbVol`=0.4 が残っていた（`bShowChat`、`Difficulty` は変わらず）。確認後に両方 1.0 へ戻して保存。PIE で `OpenMenu` を呼んだ画面（`audio36_setting_pie.png`）で 2 つのスライダーが「100%」で出て、キー一覧と重ならない
- L_Pind の PIE：ラウンドが進み、環境音は鳴らず（`au.DumpActiveSounds` が 0）、`Phase`=2 で `MUS_PostPlant` のみ。タイトル画面（`bSkipTitle`=false）で再生中の音は 0
- 実行ログ：`Saved/Logs/PARORANT.log` の `Blueprint Runtime Error` は 0 件。変更した Blueprint（`BP_PR_GameMode`、`BP_PR_MapInfo`、`BP_PR_GameInstance`、`SG_PR_Settings`、`BP_Drawbridge`、`WBP_KeyBinds`）はどの編集もコンパイル 0 エラー
- 一時的に変えて戻したもの：`BP_PR_GameInstance.bSkipTitle`（true→false）、保存の `MusicVol`／`AmbVol`（0.5／0.4→1／1）。PIE 内の `Phase` などは PIE の終了で破棄

### 8.5 仕様との差分・仮決め
- AudioComponent は 3 個（仕様は 2 個）。Last10 から PostPlant への入れ替えを 0.5 秒重ねるため、音楽を 2 個に分けた
- 音楽の `Phase`==1 の判定は「戦闘中（未設置）」。`MusicBaseVol` 0.35 は固定の係数で、スライダーの 100％＝0.35、最大もそこ（スライダーで上げても 0.35 を超えない）。環境音も同様（100％＝0.25）
- 鐘の間隔は Step 35 の 1.7 秒のまま（仕様は 1.5 秒）。`AMB_Indoor`、`MUS_Title` は作っていない。「初期値に戻す」ボタンは音量を戻さない（感度とキーだけ）
- `AudioTick` は `MatchTick`（0.1 秒）から呼ぶので、フェードの開始に最大 0.1 秒の遅れ
- 環境音は `Phase`==4 で止める。試合のやり直しでレベルを開き直すと GameMode が作り直されて再び始まる

### 8.6 未確認・試遊で聞いてほしい点
- 未確認：すべての聞こえ方（音色、音量のバランス、ループの違和感、フェードの感じ）。スライダーを実際にマウスで動かしたとき（`OnValueChanged` のイベントの結線はコンパイルのみ。セッターの呼び出しは関数の直接呼び出しで確認）。橋の動作音
- 聞いてほしい点：(1) 環境音が足音・銃声を邪魔しないか（0.25）、水・風・鳥が不自然でないか、30 秒のつなぎ目 (2) 残り 10 秒の時計の刻みが分かるか、うるさくないか (3) 設置後の鼓動と `SFX_Beep` が重なって聞こえにくくないか (4) 音楽 0.35 で足音が聞こえるか (5) 鐘（2.5 秒、1.7 秒ごとで重なる）の音色と橋のきしみ (6) 設定の音量を変えたとき、鳴っている音がすぐ変わるか、保存されるか

