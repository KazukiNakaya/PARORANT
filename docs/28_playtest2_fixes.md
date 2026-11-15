# 28. 試遊後の手直し（Step 39）

2026-11-15、ブランチ `step39/playtest-fixes`。ユーザーが Step 27〜38 をまとめて試遊し、「OK そうです、進めて」と了承した。あわせて出た 3 点の手直しと、起動マップの切り替えを行う。

## 1. やること

| 番号 | 内容 | 主な対象 |
|---|---|---|
| 1 | 起動マップを L_Canal に切り替える | `Config/DefaultEngine.ini` |
| 2 | 購入バリアを、青い板から、向こうが透けて見えるガラスのような壁にする | `BP_SpawnBarrier`、新しい素材 |
| 3 | リコールの目印に時間制限を付ける（置いてから 25 秒） | `BP_PR_Character`、`BP_PR_RecallBeacon`、`WBP_GameHUD` |
| 4 | 画面上部の残り人数のマークに、味方 Bot を含める | `WBP_GameHUD`（と `BP_PR_GameMode`） |

## 2. 仕様

### 2.1 起動マップ

- `GameDefaultMap` と `EditorStartupMap` を `/Game/PARORANT/Maps/L_Canal.L_Canal` にする。
- L_Pind は消さない（開発用に残す。エディタで開いて PIE すれば今までどおり動く）。
- 「もう一度」「タイトルへ」は今いるレベルを読み直す作りなので、変更しない。もしレベル名を直接書いている場所が見つかったら、直さずに報告する。

### 2.2 購入バリア

ねらい：購入フェーズの間、向こうの通りが見えていて、「ここから先へはまだ出られない」と分かる壁にする。今は不透明に近い青い板で、先が見えない。

- 新しい素材 `M_SpawnBarrier`（`Content/PARORANT/Art/` の中。置き場所は既存の素材にならう）と、そのインスタンス `MI_SpawnBarrier`。
  - Translucent、Unlit、両面。影を落とさない・受けない。
  - 色は青緑（水色寄り）。板の中ほどは薄く（不透明度 0.12〜0.2 ほど）、**向こうの人や建物がはっきり見える**こと。
  - 見る角度が浅いところ（フレネル）と、板の上下の縁を、少し明るく濃くして、「そこに面がある」と分かるようにする。
  - 動きを少し付ける：細い横縞または斜めの縞が、ゆっくり上へ流れる（テクスチャを足さず、座標と時間の計算で作る）。目立ちすぎない強さにする。
  - 色、中ほどの不透明度、縁の強さ、縞の強さと速さは、インスタンスで変えられるパラメータにする。
- `BP_SpawnBarrier` の見た目の部品の素材を `MI_SpawnBarrier` に替える。**当たり判定、幅（`Width`）、`SetBarrierActive` の動き、位置は変えない**。
- L_Canal の 3 か所と L_Pind の 3 か所の両方に効く（Blueprint 側の変更なので、レベルは触らないはず）。
- 特定のゲームの模様（六角形の柄など）は写さない。単純な縞と縁の光だけにする。

### 2.3 リコールの時間制限

今：E で目印を置き（ここで 1 回分を使う）、もう一度 E で経路をたどって戻る。目印は、戻る・倒される・ラウンドが変わるまで残る。

変更：**目印は、置いてから 25 秒で消える**。

- `BP_PR_Character` に変数 `RecallLife`（float、既定 25.0）と、置いた時刻（または残り時間）を持つ。
- 置いてから `RecallLife` 秒たったら、`ClearBeacon` と同じ後始末をする（目印を消す、戻り用の経路の記録を消す、HUD の「戻る」の行とミニマップの水色の点が消える）。**回数は戻さない**。
- 戻っている最中（`bRecalling`）に時間が来ても、戻りは中断しない。戻り終わってから通常どおり目印が消える。
- 残り時間が分かるようにする：
  - HUD の「E / 戻る」の行に残り秒を出す（例：`戻る 18`。整数、切り上げ）。
  - 残り 5 秒からは、目印の光を点滅させる（速さは 1 秒に 2 回ほど）。
- 時計は、購入フェーズでも戦闘中でも同じに進む（止めない）。ラウンドが変われば今までどおり消える。
- `RecallLife` を 0 以下にすると、時間制限なし（今までの動き）になる。

### 2.4 残り人数のマーク

今：スコアの左（自分の側）は人型 1 つ（自分）、右（敵の側）は開始時の敵の人数ぶん。倒した敵は暗くなる。

変更：**左に、自分＋味方 Bot の人数ぶんを並べる**。

- ラウンド開始時に実際に出た味方の数（`SpawnAllies` が出せなかった 1 体は数えない）＋ 1。味方「なし」なら今までどおり 1 つ。
- 並び：スコアに近い側が自分、その外側に味方（1 体目、2 体目）。
- 倒された味方は暗くする（敵と同じ暗さ）。自分が倒されたときは自分のマークを暗くする（今そうなっていなければ、あわせてそうする）。
- 色は今の味方色のまま。自分と味方 Bot を見分ける色分けはしない。
- ラウンドが変わったら全員明るく戻る。
- 敵の側は変えない。

## 3. 確認のしかた

キー入力は PIE に届かないので、これまでと同じく、関数の直接呼び出し、変数の書き換え、ログ、画面の撮影で確かめる。

- 2.1：エディタを再起動しなくても確かめられる範囲で、ini の値と、`L_Canal` の PIE が動くこと。
- 2.2：購入フェーズの画像（バリアの手前から、向こうの通りが透けて見える）を L_Canal で 1 枚以上。戦闘に入ると消えること。バリアを通れないこと（プレイヤーの位置をバリアの向こうへ歩かせる代わりに、当たり判定の設定が変わっていないことを読む）。
- 2.3：`RecallLife` を一時的に短く（3 秒など）して、置く → 時間で消える → HUD の行とミニマップの点が消える → その後 E 相当を呼んでも戻らない、を確かめる。25 秒の既定に戻す。戻りの最中に時間が来る場合も 1 回確かめる。
- 2.4：味方 2 体で左に 3 つ、味方を 1 体倒して 1 つ暗くなる、味方「なし」で 1 つ、の画像。
- 全 Blueprint のコンパイル、PIE の実行時エラーが増えていないこと。
- **ユーザーの保存データ（難易度、味方のあり・なし、音量、キー設定、感度、チャット表示）と `bSkipTitle` は、確認のあと必ず元に戻す。**

## 4. 実装結果

（2026-11-15、Step 39。画像は `docs/images/step39_*.png`）

### 変えたもの

| 項目 | 変えたアセット・変数・関数 |
|---|---|
| 2.1 | `Config/DefaultEngine.ini` の `GameDefaultMap`・`EditorStartupMap` を `/Game/PARORANT/Maps/L_Canal.L_Canal` に。`docs/05_map.md` に 1 行追記。ほかのレベル名の直書きは見つからなかった（`BP_PR_GameMode` の中にログの文字 `L_Pind values` が残るだけ。動作に関係なし） |
| 2.2 | 新規 `Materials/M_SpawnBarrier`（Translucent・Unlit・両面。パラメータ `Color`、`BaseOpacity` 0.15、`EdgeStrength` 0.5、`StripeStrength` 0.1、`StripeSpeed` 0.25）、`Materials/MI_SpawnBarrier`。`BP_SpawnBarrier` の `Visual` の素材を差し替え、`CastShadow` を false に |
| 2.3 | `BP_PR_Character`：変数 `RecallLife`（float、25.0）、`RecallPlacedAt`（float）、関数 `RecallRemain`（pure、残り秒）、`RecallLabel`（pure、HUD 用の文字）、`RecallExpire`（時間切れの後始末と点滅）。`RecallPlace` の最後に `RecallPlacedAt` に時刻を入れ、`RecallTick` の戻っていないとき（`RecallRecord` の後）に `RecallExpire` を呼ぶ。`WBP_GameHUD.SkillLabel` の「戻る」の文字を `RecallLabel` に差し替え |
| 2.4 | `BP_PR_GameMode`：変数 `StartAllies`（int）、`TmpAllyAlive`（bool）、関数 `AllyAlive(Idx)`（その `AllyIdx` の味方が生きているか）。`SpawnAllies` の先頭で `StartAllies`=0、味方を 1 体出すたびに +1。`WBP_GameHUD`：`AllyFace1`、`AllyFace2`（`AllyBox` の中、左から `AllyFace2`・`AllyFace1`・`AllyFace0`。大きさ 44×44、`T_PR_FaceIcon`、間 4px）、関数 `UpdateAllyFaces`（`UpdateFaces` の先頭から呼ぶ） |

### 動き

- **バリア**：板の縦方向の位置（`WorldPosition.z − ObjectPosition.z`）から、上下の縁（±170〜200cm）を明るく濃く、フレネルで浅い角度を明るく、40cm 間隔の細い横縞が 1 秒に 0.25 周期ぶん上へ流れる。中ほどの不透明度は 0.15。当たり判定（`Blocker`）、`Width`、`SetBarrierActive`、位置には触っていない
- **リコール**：目印を置いた時刻から `RecallLife` 秒（`GetGameTimeInSeconds` なので購入フェーズでも戦闘中でも同じに進む）で `ClearBeacon`（目印を消す・経路を空にする。回数は戻さない）。戻っている最中（`bRecalling`）は `RecallExpire` が呼ばれないので中断せず、戻り終わりの `RecallEnd` → `ClearBeacon` で消える。`RecallLife` が 0 以下なら何もしない。HUD の行は `戻る 18`（切り上げの整数）、時間制限なしのときは `戻る`。残り 5 秒以下は 0.25 秒ごとに目印（`Mesh` と子の `Light`）の表示を切り替える（1 秒に 2 回）
- **残り人数**：左の並びは、スコアに近い側から 自分（`AllyFace0`）・味方 1 体目（`AllyIdx`=0、`AllyFace1`）・2 体目（`AllyFace2`）。`StartAllies` より外の枠は Hidden。味方の色は今の水色のまま、倒された（`bDead`）か、いなくなったら暗い色（敵と同じ）。自分は元からの `bDead` 判定

### 確認できたこと

- 2.1：`DefaultEngine.ini` の 2 つの値。エディタを再起動せずに、L_Canal の PIE が起動して試合（購入フェーズ→戦闘）が進んだ
- 2.2：L_Canal の購入フェーズで、バリアの手前から向こうの通り・建物が透けて見える（`step39_barrier_buy.png`。上下の縁と細い縞が明るい）。戦闘に入るとバリアが消える（`step39_barrier_combat.png`）。当たり判定は触っていない（`BP_SpawnBarrier` の変更は `Visual` の素材と `CastShadow` のみ、`Blocker`・`Width`・`SetBarrierActive` は同じ）。L_Canal の 3 か所に効いている（`instancesUpdated` 3）
- 2.3（PIE。`RecallLife` を PIE 中の変数の書き換えで短くして確認。アセットの値は 25.0 のまま）：
  - 置く直後に HUD が `戻る 9`、5 秒後に `戻る 4`、時間が来ると目印のアクターが 0 個になり行が「リコール」に戻る（`step39_recall_a/b/c.png`）
  - ミニマップの水色の点（味方 Bot の点と重ならない位置で確認）が、置いた直後は出て、時間が来ると消える（`step39_recall_dot2_on.png`、`step39_recall_dot2_off.png`）
  - 時間が来たあと、`RecallPath` が空、`bRecalling` が false、`SkillSpecialPress(1)`（E 相当）を呼んでも戻らず位置が変わらない
  - 戻っている最中に時間が来る場合：`RunSpeed` を 4 にして戻りを遅くし、`RecallLife` を 1 にして経過時間を超えさせた。`bRecalling` が true のまま目印が残り、HUD は `戻る 0`（`step39_recall_expired_while_recalling.png`）。`RunSpeed` を 675 に戻すと戻り終えて `bRecalling` false、目印が消えた
- 2.4（PIE）：味方 2 体で左に 3 つ（`step39_faces_3.png`）。味方 1 体の `bDead` を true にすると真ん中（味方 1 体目）の 1 つが暗くなる（`step39_faces_ally1_dead.png`）。`AllyCount`=0 にして `SpawnAllies` を呼ぶと左は 1 つ（`step39_faces_none.png`）。自分の `bDead` を true にすると自分のマークが暗くなる（`step39_faces_self_dead.png`）。次のラウンドで自分のマークは明るく戻る（`step39_faces_round2.png`、このラウンドは味方なし）
- 全 Blueprint のコンパイル：`/Game/PARORANT` の 39 個、失敗 0
- PIE の実行時エラー：ログの `Blueprint Runtime Error` は 0 件。`LogScript` の「アクセスなし」の警告は、PIE を止めるときに 16 行ずつ出る（`GI`・`GM`・`DynamicCast_AsBP_PR_Character`。時刻から見て PIE を止めるときと思われる。リコール・残り人数の変更より前のバリアの確認の PIE のあとにも、同じ内訳 5/5/2/4 の 16 行が出ていた。原因の関数までは特定していない）
- 戻した確認：`GameInstance.bSkipTitle` は false（アセットは `git restore` で元の内容）、`RecallLife` の既定は 25.0、`Saved/SaveGames` の 4 ファイルのハッシュは作業前と同じ。L_Canal のレベルファイルは差分なし

### 未確認のこと

- リコールの目印の点滅の見た目（残り 5 秒以下で表示が切り替わること）。呼び出しの間隔が長く、PIE 中に表示の true/false の両方を捕まえられなかった（残り時間が 5 秒を切った直後にラウンド終了などで目印が消えた）。グラフは `RecallExpire` に書いた（`RecallRemain` ≤ 5 で `floor(Remain×4) % 2 == 0` を `Mesh` の `SetVisibility`（子に伝える）に渡す）
- キー入力（実際の E 押下）で置く・戻る流れ、戻っている最中の画面
- 味方 Bot が実際に撃たれて倒れたときのマークの暗転（`bDead` の書き換えで代用）と、そのあと次のラウンドで味方 2 体が出て 3 つとも明るく戻ること（今回のラウンド 2 は味方なしだった）
- バリアの動く縞の見た目の速さ・強さ（静止画のみ）、ガラスの見た目の好み
- バリアを実際に通れないこと（当たり判定のアセットを変えていないことだけ）

### こちらで決めたこと

- 素材の置き場所：仕様は `Art/` だが、`Art/` は `Props` のみで、既存の素材（`M_RecallBeacon` など）は `Materials/` にあるので `Content/PARORANT/Materials/` に置いた
- 縞は 40cm 間隔・1 秒に 0.25 周期、縁の範囲は上下 30cm、表の不透明度は 0.15、色は (0.05, 0.75, 0.8)
- 影：素材ではなく `BP_SpawnBarrier.Visual` の `CastShadow` を false にした（Unlit の素材は影を受けない）
- 点滅：「目印の光」を、目印の見た目全体（円柱と光）の表示切り替えにした
- 時間切れの判定は `RecallTick`（戻っていないとき）の毎フレーム。置いた時刻は `GetGameTimeInSeconds`
- 味方の枠は最大 2 つ（`AllyCount` の既定が 2。多くしたいときは枠を足す）。味方の数は `SpawnAllies` が出した数を数える（`StartAllies`）
- 起動マップ：`docs/05_map.md` に追記したほか、README に起動マップの記述はなかった

