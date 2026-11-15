# 23. Bot の人間っぽさの実装仕様（Step 30〜32・34）

方針は [20](20_canal_town_concept.md) §6。土台は [11](11_bot_combat.md)（撃ち合い）と [12](12_macro_ai.md)（寄り・裏取り）。進め方は [21](21_impl_rules.md)。2026-11-12 作成。
関数名・変数名は仕様書からの引用。実物と違えば実物に合わせる。

## 1. 難易度との関係（全 Step 共通）

難易度は「撃ち合いの強さと敵の数」で管理する方針（[13](13_hud_difficulty.md) §3）を変えない。

| | イージー | ノーマル | ハード | ベリーハード・パロラント |
|---|---|---|---|---|
| 撃ち合い中の移動 | 棒立ち | 棒立ち | 動く | 動く |
| 撃ち合いの型（§3） | 標準のみ | 標準＋しゃがみ | 全部 | 全部 |
| 覗き方（§4） | 全部（下手） | 全部 | 全部 | 全部 |
| ミスの倍率 `MistakeMul`（§5） | 2.0 | 1.3 | 0.8 | 0.4 |
| チャット（§6） | 多い | ふつう | ふつう | 少ない（報告が減る） |
| Bot のスキル（§7） | 使わない | 1 ラウンド 1 回まで | 2 回まで | 2 回まで |

値は `ApplyDifficulty` で設定する。

## 2. Step 30：未実装の残り

[12](12_macro_ai.md) §8・§9 の仕様のうち、§13 で未実装だったもの。仕様の本文は 12 を正とする。

| # | 項目 | 実装の要点 | 確認 |
|---|---|---|---|
| 1 | 到着後の見張りと確認 | Reinforce（State 5）で着いたら入口の方を向いて 3 秒待ち、何も無ければ報告された位置へ歩いて行く | 1 体倒して寄らせ、着いた Bot が止まってから歩き出すのを位置の記録で確認 |
| 2 | 2 体の合流待ち | 同じ出来事で 2 体以上が寄るとき、先に着く方が目的地の 8m 手前で最大 2.5 秒待つ。ノーマル以上 | 2 体寄りを起こし、到着時刻の差が 1 秒以内 |
| 3 | 空振り | 着いて 6 秒何も無ければ、Bot が一番少ないサイトへ戻る | ログ `[Director] whiff` |
| 4 | 穴埋め | Bot が 0 体のサイトがあり、10 秒情報が無ければ、近い 1 体が移る | A の Bot を全部倒して隠れ、10 秒後に 1 体が A へ来る |
| 5 | 密集崩し | 1 サイトに 2 体以上いて `DenseTime`（30 秒）情報が無ければ、個性の「残る」が低い 1 体が反対へ | スタックの配置で 30 秒待つ |
| 6 | 裏取りの忍び足 | 最後の 20m は歩き（速度 300）。`bSilentStep` が true の間、`BP_PR_Bot` の足音を鳴らさない | 作戦を裏詰めに固定し、終盤の速度と足音なしを確認 |
| 7 | 遮蔽に隠れてのリロード | [11](11_bot_combat.md) の Retreat / Repeek が実際に起きるか確かめ、起きなければ直す | ハードで、Bot の弾を減らして撃たせ、遮蔽へ走ってリロードする |
| 8 | ピストルの向き | Step 10 の残り。Bot がピストルを持ったときの `GunMesh` の向き | R1 のスクリーンショット |

完了条件：上の 8 項目の確認結果を書く。[12](12_macro_ai.md) §13 の「未実装」の記述を更新する。

### 2.1 実装結果（Step 30、2026-11-12）

実物との違い：寄る State は 5 ではなく **4**（`Reinforce` が `SetState 4`）。Step 30 の動きは `IdleThink` の State==4 の分岐で `ReinforceThink` に入る（State 3 の `AlertThink` は変えていない）。

足した変数（初期値）：
- `BP_PR_AIController`：`RPhase`（0）、`RPhaseTime`、`RArriveTime`、`RCheckLoc`、`RGroup`（0）、`RWaitStart`（-1）、`bRWaitDone`、`bPartnerTmp`、`FlankAcc`。Tuning：`WatchTime` 3、`WhiffTime` 6、`ArriveDist` 350、`PartnerWaitDist` 800、`PartnerWaitMax` 2.5、`FlankWalkDist` 2000、`FlankWalkSpeed` 300
- `BP_PR_Director`：`GroupSeq`、`LastEventLoc`、`BalStart`（-1）、`bBalInit`、`StartA`、`StartB`、`BalAcc`、`bTmpFree`、`TmpHold`、`TmpMover`、`TmpScore`、`TmpLoc`。Tuning：`FillTime` 10。既存の `DenseTime` は難易度の値を入れる
- `BP_PR_Bot`：`bSilentStep`（false）

足した・変えたグラフ：
- 新規（AIController）：`ReinforceInit`、`ReinforceThink`、`ReinforceMove`、`ReinforceWatch`、`PartnerFar`、`FaceTo`、`UpdateSilentStep`。変更：`Reinforce`（最後に `ReinforceInit`）、`IdleThink`（State==4 の分岐）、`Think`（速度のあとに `UpdateSilentStep`）
- 新規（Director）：`MarkEvent`、`HoldArea`、`CountSite`、`IsHoldFree`、`Rebalance`、`Whiff`、`SiteFix`、`BalanceTick`。変更：`ApplyEvent`（`Predict` の前に `MarkEvent`）、`Poll`（先頭で `BalanceTick`）
- `BP_PR_Bot`：Tick の足音の条件に `NOT bSilentStep` を足した

動き：
- 到着後（1）：`Reinforce` が `ReinforceInit` で報告位置（`Director.LastEventLoc`）と出来事の番号（`GroupSeq`）を受け取る。着く（目的地から 350cm 以内、または止まって 1 秒）と `WatchTime` 3 秒、報告位置の方を向いて待ち、そのあと速度 300 で報告位置まで歩く（最大 3.5 秒）。向きは入口でなく報告位置の方（仮決め。`BP_HoldPoint` に入口の向きは無い）
- 合流待ち（2）：難易度がノーマル以上、同じ出来事で寄る仲間がいて、目的地まで 800cm 以内で、その仲間がまだ 800cm より遠いとき、止まって待つ。最大 `PartnerWaitMax` 2.5 秒。難易度はイージーでは待たない
- 空振り（3）：着いて `WhiffTime` 6 秒で `Director.Whiff` を呼ぶ。`Whiff` は A / B の Bot の数（持ち場のエリアで数える。自分は除く）が少ない方、同数なら元の持ち場のエリアを選び、`Rebalance` で空いている持ち場（前に出る持ち場は除く）へ持ち場を付け替えて State 0 に戻す。ログ `[Director] whiff`
- 穴埋め（4）：ラウンド開始時に Bot がいたサイトが空になり、`FillTime` 10 秒情報が無いとき、State 0 の Bot（ミッド、または 2 体以上いるサイトの Bot）のうち目的地に近い 1 体が移る。ログ `[Director] fill`
- 密集崩し（5）：サイトに 2 体以上いて、反対のサイトがそれより 2 体以上少なく、`DenseTime` 秒情報が無いとき、個性の「残る」が一番低い State 0 の 1 体が反対へ移る（残る：堅実 0.85、寄り屋と裏取り屋 0.30、前のめり 0.15。0.30 同士は先に見つけた方、仮決め）。反対が 1 体少ないだけでは動かさない（行き来を避けるため、仮決め）。ログ `[Director] dense`
- 忍び足（6）：`Think` のたびに `UpdateSilentStep` が、State 6 で残りの経路が `FlankWalkDist` 2000cm 以内なら `Bot.bSilentStep` を true にして速度を 300 にする。それ以外は false。true の間は足音を鳴らさない

確認（L_Canal の PIE、難易度は起動時の初期値のままイージー。確率で決まるところは関数の直接呼び出しで起こした）：
- 1・3：`ApplyEvent` で A に出来事を起こし、2 体が寄った。`reinforce arrive`（t=60.2、62.6）→ 3.0 秒後に `watch done`（歩きへ）→ `check walk finished` → 着いて 6 秒で `[Director] whiff: cntA=0 cntB=1` と `rebalance: bot moved to area 0`
- 2：コントローラの難易度を 1 にして、`Reinforce` を 2 体に呼び、`RGroup` を 9 に揃えた。先の 1 体が `partner wait start`（49.28）→ `partner wait end`（51.78、2.5 秒）、到着は t=132.405 と 132.510（差 0.1 秒）
- 4：`FillTime` を 3 秒にして A の Bot に `Die` を呼んだ。3 秒後に `[Director] fill: site A empty` と `rebalance: bot moved to area 0`。B を空にしても同じ（`fill: site B`）
- 5：`DenseTime` を 3 秒、`StartB` を 0 にして A に 2 体を集めた。3 秒後に `[Director] dense: site A stacked` と `rebalance: bot moved to area 2`
- 6：`StartFlank(1)` のあと、Bot を A の背後の経路の終わりの近く（-2800, -2800）へ動かし `FlankIdx` を 3 にした。`bSilentStep` が true、速度 180〜240（300 以下）。普通の裏取りの途中では false
- 実行時のエラー（Accessed None）はログに出ていない。変更した Blueprint（AIController、Director、Bot）は、編集のたびのコンパイルが通った。全 Blueprint の一括コンパイルは実行していない
- 0（`L_Pind` の直書き）：`WBP_Title.OnPlay`、`WBP_Result.OnAgain` / `OnTitle` はすでに `GetCurrentLevelName` で今のレベルを開く。GameMode の「L_Pind」は文字のログ 1 件だけ（`[Map] MapInfo not found ... (L_Pind values)`）で、変更不要。「試合の終わりから再戦・タイトル」の通しは PIE で押せていない（UI のボタンはクリックできない）

7（遮蔽に隠れてのリロード）：
- `BurstTick` は残弾 0 か体力が `RetreatHP` 未満で `StartRetreat`、`FindCover` は周囲 16 点（350 / 600cm）から、プレイヤーの目からの線が遮られ、自分からは通る点を探す。`RetreatTick` がリロード（`WReload`）→ 3〜4 秒待ち → 捜索へ
- 残弾を 2 にしてプレイヤーの前へ動かすと、撃ち切ってリロードが起き、弾が戻った。そのとき `CoverDest` に遮蔽の点が入っていた。ただし Bot の移動を位置の記録で追えず、遮蔽へ走って隠れたことは確認できていない。直すところは見つかっていないので変更なし

8（ピストルの向き）：
- `ApplyGunVisual` の Classic の `GunMesh` の相対回転は (0, 70, 0)（一人称の腕用に調整した値）。Bot の手に付けた状態を、ejected カメラのスクリーンショットで見ようとしたが、Bot が近く、銃が映らなかった。未確認、変更なし

仕様との差分：
- 向きは報告位置の方（上）。穴埋めと密集崩しの Bot の移動は `Reinforce` ではなく、持ち場の付け替え（`HoldThink` が歩く）。密集崩しは「反対が 2 体以上少ない」条件を足した。`DenseTime` は [12](12_macro_ai.md) §10 の難易度の値（45 / 30 / 20 / 15）にした（[23](23_bot_human.md) §2 の表の 30 は、ノーマルの値）

未確認：ハード以上での動き、実プレイ（プレイヤーが本物の敵のとき）での見張りと確認の手応え、遮蔽へ隠れるリロード、ピストルの向き、再戦・タイトルへの通し

## 3. Step 31：撃ち合いの型

うまいプレイヤーがやる動きを、接敵ごとにランダムに 1 つ選ぶ。`DuelMode`（Hold / Strafe / Stop / Burst / Retreat / Repeek）の値の組み合わせで作り、新しい状態はなるべく足さない。

### 3.1 型 `DuelStyle`
| 値 | 型 | 動き |
|---|---|---|
| 0 | 標準 | 今の動き（Strafe 0.2〜0.45 秒 → Stop → Burst） |
| 1 | ジグル撃ち | 左右に小さく刻む。Strafe 0.12〜0.2 秒 → Stop → 1〜2 発 → 必ず反対へ。止まっている時間が短い |
| 2 | しゃがみ撃ち | Burst の 2〜3 発目でしゃがみ、撃ち終わるまでしゃがんだまま。撃ち終わったら立つ。プレイヤーの照準が頭の高さからずれる |
| 3 | 大きく出る | 最初の Strafe だけ 0.5〜0.7 秒と長く取り、角から離れた位置で止まって撃つ。2 回目以降は標準 |
| 4 | 撃ち逃げ | Burst を 1〜3 発で切り上げ、すぐ Retreat（近くの遮蔽へ）。1.0〜2.5 秒後に Repeek。体力に関係なく行う |
| 5 | 決め撃ち | 見失った直後（3 秒以内）に同じ角から相手が出てきたら、反応時間を 0.1 秒にして撃ち始める。型というより条件付きの上書き |

### 3.2 選び方
接敵（State が交戦に入った瞬間）ごとに 1 回だけ抽選する。途中で変えない。

| 条件 | 標準 | ジグル | しゃがみ | 大きく出る | 撃ち逃げ |
|---|---|---|---|---|---|
| 基本の重み | 4 | 2 | 2 | 1 | 1 |
| 距離 8m 以下 | — | ×0.5 | ×2 | — | ×0 |
| 距離 25m 以上 | — | ×2 | ×0.5 | ×0 | ×2 |
| 個性：前のめり | — | — | ×1.5 | ×3 | ×0 |
| 個性：堅実 | — | — | — | ×0 | ×3 |
| 武器：スペクター | — | — | ×2 | — | — |
| 武器：ハンドガン | — | ×2 | ×0.5 | — | — |
| 待ち構えていた（Hold から接敵） | 最初の 1 回は動かず撃つ（今のまま）。型は 2 回目の Burst から使う |

- イージーは標準のみ。ノーマルは標準としゃがみ（棒立ちのまましゃがむ）のみ
- 決め撃ちは抽選と別。ハード以上で 50%、ノーマルで 20%（仮）
- ログ `[Bot] style=2 dist=12.3`

### 3.3 しゃがみの作り
- `BP_PR_Bot` に `SetBotCrouch(bool)` を足す。Character の `Crouch` / `UnCrouch` を使う（`CanCrouch` を有効に）。移動速度は 250
- 当たり判定：頭・胴・脚の部品が、しゃがんだ姿勢の位置へ動くこと。骨に付いていれば自動で動く。カプセルに付いているなら、しゃがみ中だけ相対位置を下げる（頭の高さ 約 165 → 約 110cm）。**PIE で、しゃがんだ Bot の頭を撃ってヘッドショットになること、立っていたときの頭の位置を撃って当たらないことを確認する**
- 目の位置（視線のトレースの始点）と銃口も下げる
- アニメ：しゃがみの素材が無い（[11](11_bot_combat.md) §6）。次の順で試す
  1. Blender MCP で、`SK_Swat8` のスケルトンにライフルを構えたしゃがみのポーズ（1 フレーム）を作り、アニメとして取り込む。`ABP_PR_Swat` に `bCrouched` を足し、立ち⇔しゃがみを 0.15 秒でブレンドする
  2. うまくいかなければ、`ABP_PR_Swat` で腰の骨を 45cm 下げ、両足を Two Bone IK で元の位置に留める
- しゃがんだまま移動はしない（撃つ間だけ）ので、しゃがみ歩きのアニメは不要

### 3.3.1 実装結果（しゃがみの見た目、Step 31 仕上げ、2026-11-13）

第二案（腰を下げて足は IK で床に留める）を Unreal の中だけで作った。Blender は使っていない。
- `SetBotCrouch`：`Crouch` / `UnCrouch` のあとに `SwatMesh` の相対位置を変える（しゃがみ Z=-40、立ち Z=-88）。カプセルの半分の高さが 88→40 に縮んでアクターが 48cm 下がるので、足は床に戻る
- `ABP_PR_Swat`：AnimGraph の最後（Layered Blend Per Bone のあと）に、Transform (Modify) Bone（Hips、コンポーネント空間、加算、Z=-40）と Two Bone IK（LeftFoot、RightFoot。エフェクタはコンポーネント空間の固定位置、膝の向きは前）を足した。EventGraph が Bot の `bCrouched` を読み、`PoseCrouchA`（0〜1。`FInterpTo_Constant`、速さ `CrouchBlendSpeed`=6 で約 0.17 秒）を作る。IK の強さ `CrouchIKAlpha`＝min(PoseCrouchA×3, 1)。立っているときは両方 0 なので、走り・横走り・発砲・死亡のアニメは変わらない
- 腰の下げ量は 40cm（仕様の約 48cm より浅い）。48cm だと見た目の頭が当たり判定の頭より約 18cm 低く（15cm 以内の条件を超える）、40cm で約 13cm になるため
- 注意：ABP の変数名 `CrouchAlpha` は `BP_PR_Character` と重なり、書き込みノードが別クラスへの設定になる不具合があったため `PoseCrouchA` にした
- 測定（床から。テスト用の Bot を空中の床に置き、コントローラを外して `SetBotCrouch(true)` とアクターの 48cm 下げで再現）：立ち 頭頂（`HeadTop_End`）168.9、当たり判定の Head 中心 172.2。しゃがみ 頭頂 128.8、Head 中心 124.2、足首 11.0 / 11.6（床に付いている）、`Leg` の底 -0.8。見た目の頭の中心（頭頂 −11.5cm と仮定）と Head 中心のずれ：立ち 約 18cm、しゃがみ 水平 (6.7, 8.5)・上下 6.9 で約 13cm。胴・頭・脚の当たり判定の高さは変えていない
- スクリーンショット：[crouch31_stand.png](images/crouch31_stand.png)、[crouch31_crouch.png](images/crouch31_crouch.png)（横から）
- 既知の見た目：右足は固定の位置（腰の少し後ろ）に動く。足の位置は立ち姿の測定値を直書き（左足 (12.7, 22.7, 8.8)、右足 (-6, -8, 9.4)）

### 3.4 完了条件
- ハードで、5 種類の型がそれぞれ起きることをログと速度・高さの記録で確認する（型を一時的に固定する Tuning 変数 `DebugStyle` を作る。-1 で抽選）
- ノーマルで、移動せずにしゃがみ撃ちが起きる。イージーでは起きない
- しゃがみ中の当たり判定が上の確認どおり

## 4. Step 31：覗き方

「見えていない相手のいる角へ近づく」とき（捜索 State 2、寄りの到着後の確認、取り返し）の動き。

| 値 `PeekType` | 覗き方 | 動き | 主に使う場面 |
|---|---|---|---|
| 0 | 少しずつ見る | 角の 3m 手前から歩き（300）で、角を外回りに開いていく。0.6 秒進んで 0.4 秒止まる、を繰り返す | 捜索、取り返し |
| 1 | 一瞬だけ出る | 角から 0.25 秒だけ体を出して戻る。相手が見えたら、0.5〜1.2 秒後に撃ちに出る（このとき型は「大きく出る」） | 相手が最近いた角 |
| 2 | 大きく飛び出す | 走りで角から 2〜3m 離れた位置へ出て、止まって撃つ | 前のめりの個性、2 体での突入 |
| 3 | 置いておく | 進まない。音がした角へ照準を合わせて 2〜5 秒待つ。出てきたら反応時間を半分にして撃つ | 足音・銃声を聞いたとき（警戒 State 3） |

- 「角」の求め方：Bot から目的地（最後に見た位置や報告された位置）へのナビメッシュの経路を取り、Bot の目から見えない最初の経由点の 1 つ手前を角とする
- 選び方：場面ごとの既定を上の表のとおりとし、個性で振る（前のめりは 2 を 50%、堅実は 3 を 50%、ほかは既定 70%・残りを均等）
- 「一瞬だけ出る」で戻る先は、出る前に立っていた位置
- ログ `[Bot] peek=1`
- 完了条件：`DebugPeek` で固定して 4 種類を確認する。捜索中の Bot が、今のように最後に見た位置へ一直線に歩いて来ないこと

### 4.1 実装結果（覗き方、Step 31、2026-11-12）

使う場面は **捜索（State 2）と警戒（State 3）だけ**。寄りの到着後の確認（Reinforce）と取り返しには入れていない（未対応）。

足した変数：`PeekType`（-1）、`PeekPhase`、`PeekT`、`PeekSide`、`PeekCornerLoc`（角。関数名 `PeekCorner` と衝突するため改名）、`PeekHome`、`PeekDest`、`PeekHoldUntil`。Tuning：`DebugPeek`（-1 で抽選）、`PeekWalkPct` 0.7、`PeekAggrPct` 0.5、`PeekSafePct` 0.5、`PeekStepMove` 0.6、`PeekStepStop` 0.4、`PeekOutTime` 0.25、`PeekOutDist` 200、`PeekDashDist` 250、`PeekHoldMin/Max` 2/5、`PeekArrive` 80、`PeekArriveSlack` 60、`PeekSlowArrive` 300、`PeekRunSpeed` 675、`PeekTimeout` 15、`PeekReactMul` 0.5、`PeekAlertHoldPct`（未使用）。

グラフ：`PeekBegin(Scene, Dest)`（抽選、`PeekBeginK`）、`PeekCorner`（`FindPathToLocationSynchronously` の経路点を先頭から目の高さで線トレースし、最初に隠れる点の 1 つ手前を角にする）、`PeekTick`（`PeekSpeedK` と `PeekStepK` が `PeekPhase` で進める）、`PeekContact`（`ContactInit` の最後。`PeekContactK`）、`PeekLog`（`[Bot] peek=N`）。変更：`SearchThink`（移動の代わりに `PeekBegin` と `PeekTick`。旧 MoveTo は削除）、`AlertThink`（`PeekBegin` と待ち）、`ContactInit`。

動き：
- 0 少しずつ見る：角へ（角の手前 300cm、`PeekArrive`+`PeekArriveSlack` 以内で到着とみなす）→ 0.6 秒歩く・0.4 秒止まるを、目的地（最後に見た位置に横ずれ 200cm）へ向けて繰り返す
- 1 一瞬だけ出る：角へ → 角の先 200cm へ 0.25 秒 → 出る前の位置へ戻る → 0 に移る
- 2 大きく飛び出す：速度 675 で角へ → 角から 250cm 先へ走って止まる → 2 秒待つ → 0 に移る
- 3 置いておく：その場で 2〜5 秒（`PeekHoldUntil`）目的地を向いて待つ。待ち中に接敵すると `ReactOverride` に反応時間×0.5。待ったあと 0 と同じ（警戒では待ったあと音の位置へ移動）
- 抽選：前のめりは `PeekAggrPct` で 2、堅実は `PeekSafePct` で 3、ほかは `PeekWalkPct`（既定の型：捜索 0、警戒 3）、残りを均等に。警戒では 3 以外を引いた場合は待たずにそのまま音の位置へ
- ログ `[Bot] peek=N`。`DebugPeek` で固定

確認（L_Canal の PIE、プレイヤーを見ないよう `SightRange` を 50 に）：`DebugPeek` 0/1/2/3 でログ `peek=0..3` が出て、位置とフェーズの記録で、0 は歩き（300）と停止の繰り返し、1 は `PeekPhase` 2→5→（0 へ）、2 は速度 675 で約 1000cm を 1.5 秒（フェーズ 7→8 の 2 秒待ち）、3 は `PeekHoldUntil` までフェーズ 0 のまま 4.5 秒待って動き出した。警戒（State 3）で `PeekPhase`=50 のまま約 3 秒待ち、そのあと移動を始めた。捜索の Bot は最後に見た位置へ一直線ではなく、角を経由して歩き止まりを繰り返す。

仕様との差分：
- 「一瞬だけ出る」で相手が見えたとき、0.5〜1.2 秒後に出直す動きは作らず、見えた時点でそのまま交戦（型だけ `PeekContactK` が 3（大きく出る）に変える）。「外回りに開く」は目的地を横にずらす（`PeekSide`）ことで代用
- 寄りの確認と取り返しには未適用。使う場面の「個性の既定」は捜索 0・警戒 3 のみ
- 角を求める経路は目的地までのナビメッシュ経路（`PeekDest`）。経路点の高さ（床の高さ 10）が Bot の位置（90）と違うため、到着の判定は水平距離（2D）。ナビの停止は受け入れ半径+約 35cm 手前になるので `PeekArriveSlack` を足した

## 5. Step 31：ミス（簡単に作れる範囲）

各ミスは「起きる確率 × `MistakeMul`（§1）× 個性の係数」で、判定は出来事ごとに 1 回。

| ミス | 起きるとき | 動き | 基本の確率 |
|---|---|---|---|
| 焦る | 距離 6m 以下で、待ち構えずに接敵した | その接敵の最初の Burst を、止まらずに撃つ（Stop を飛ばす）。発数は 6〜10 発 | 25% |
| 悪いリロード | Burst の後、残弾が 6 割未満で、相手が見えていない | その場でリロードする（遮蔽へ行かない） | 20% |
| 空振りの警戒 | 捜索が終わって持ち場へ戻るとき | 最後に見た方向を向いたまま、さらに 3〜6 秒動かない | 30% |
| 釣られる | 警戒（State 3）に入るとき | 音の位置の 5m 手前で止まらず、音の位置まで行く | 20% |
| 視野が狭い | 交戦が終わって 4 秒以内 | 視野角を左右 45° → 25° に狭める（背後や横から近づきやすい） | 常時（ミスの倍率が 1.0 以上のとき） |

- 個性の係数：前のめりは「焦る」「釣られる」が 1.5 倍、堅実は全部 0.5 倍
- 見送り：撃ち合い中の味方への誤射、弾切れに気付かない、など判定が増えるもの
- 完了条件：各ミスを確率 100% にして 1 回ずつ起こし、元の確率に戻す。ログ `[Bot] mistake=panic`

### 5.1 実装結果（Step 31、2026-11-12）

覗き方（§4）は §4.1 に記録。型・しゃがみ・ミス（5 種類のうち 4 種類）は実装した。続きの作業（2026-11-12）：乗数の数値は `PickStyleK` の Tuning 変数にした（`StyleNearDist` 800 / `StyleFarDist` 2500 / `JigNearMul` 0.5 / `JigFarMul` 2 / `JigHandMul` 2 / `CrouchNearMul` 2 / `CrouchFarMul` 0.5 / `CrouchAggMul` 1.5 / `CrouchSpecMul` 2 / `CrouchHandMul` 0.5 / `WideAggMul` 3 / `RunFarMul` 2 / `RunSafeMul` 3。値は同じ）。型 1 の止まる時間は `JigStopTime` 0.15（標準は `StopTime` 0.35）を `StrafeTick` で使う。**`ApplyMistake` が `StyleSet` を入れていなかった不具合を直した**（イージー 0、ノーマル 1、ハード以上 2。以前はどの難易度も 2 のままで、イージーでも型が出る状態だった）。

実装上の注意（この環境の MCP の制約）：変数を読む式を `write_graph_from_code` で書けないため、変数を読む計算は「入力を引数に取る `〜K` 関数（計算だけ）」と「変数を読んで `〜K` に渡す薄い関数」に分けた。数値の乗数（距離 ×0.5 など）は `PickStyleK` の中の直書き（基本の重み 4/2/2/1/1 だけ Tuning 変数）。

足した変数（初期値）：
- `BP_PR_Bot`：`bCrouched`（false）。CMC の `MaxWalkSpeedCrouched`＝250、`NavAgentProps.bCanCrouch`＝true
- `BP_PR_AIController` Tuning：`MistakeMul`（1.0、`ApplyDifficulty` が 2.0 / 1.3 / 0.8 / 0.4 / 0.4 を入れる）、`SnapChance`（0、同 0 / 0.2 / 0.5）、`StyleSet`（2、同 0 標準のみ / 1 標準＋しゃがみ / 2 全部）、`DebugStyle`（-1）、`DebugPeek`（-1、未使用）、`StyleWStd/Jig/Crouch/Wide/Run`（4/2/2/1/1）、`SnapReact`（0.1）、`JigStrafeMin/Max`（0.12/0.2）、`WideStrafeMin/Max`（0.5/0.7）、`RunWaitMin/Max`（1.0/2.5）、`PanicChance`（0.25）、`BadReloadChance`（0.2）、`WhiffWatchChance`（0.3）、`LureChance`（0.2）、`FovCosWide/Narrow`（0.707/0.906）、`NarrowTime`（4）
- 同 AI：`DuelStyle`、`bHeldContact`、`BurstCount`、`StrafeCount`、`BurstShots`、`CrouchAt`、`ReactOverride`（-1）、`Pers`（-2）、`StyleRoll`/`StyleW1〜4`/`StyleDist`/`MistakeRoll`（未使用）、`bPanic`、`NarrowUntil`、`FreezeUntil`、`bLure`（未使用）、`JigDir`、`MistakeHit`
- `BP_PR_GameMode`：関数 `PersOf(Idx)`（Director と同じ `Personality[Idx % 5]`）

足した・変えたグラフ：
- 新規（AIController）：`ApplyMistake`（`ApplyDifficulty` の最後から呼ぶ）、`FindPers`、`PickStyle`/`PickStyleK`、`ContactInit`/`ContactK`、`StrafeHook`/`StrafeHookK`、`BurstHook`/`BurstHookK`、`AfterShot`、`CrouchGuard`、`MistakeK`、`EngageLostHook`、`WhiffWatch`、`LureCheck`、`BLog`/`BLogF`/`BLogSD`（ログ）。使っていない空の関数：`ApplyDifficulty2`、`MistakeP`、`EffReact`
- 変更：`NewContact`（最後に `ContactInit`）、`StartStrafe`（最後に `StrafeHook`）、`StartBurst`（最後に `BurstHook`）、`BurstTick`（1 発ごとに `AfterShot`、バースト終了の撤退条件に「型==撃ち逃げ」を OR）、`RetreatTick`（Retreat→Repeek の待ちを撃ち逃げのとき `RunWaitMin/Max`）、`DuelLegs`（反応時間を `ReactOverride` があればそれにする）、`Think`（速度のあとに `CrouchGuard`、見えていないときの `IdleThink` の前に `FreezeUntil` の待ち）、`EngageLost`（最後に `EngageLostHook`）、`SearchThink`（捜索の時間切れに `WhiffWatch`）、`AlertThink`（移動の前に `LureCheck`、停止距離を選ぶ）、`CanSeeTarget`（内積から「狭い視野のとき 0.199」を引く）
- `BP_PR_Bot`：`SetBotCrouch`、`IsSpectre`

しゃがみの作り方（Step 31 の時点の簡易版。**見た目は 2026-11-13 に §3.3.1 のとおり直した**。第一案の Blender のポーズは作っていない）：`SetBotCrouch(true)` が `Crouch` を呼ぶ。カプセルの半分の高さが 88→40 に縮み、アクターの位置が 48cm 下がる。`Head` / `Body` / `Leg` と `SwatMesh` はカプセルの子なので、当たり判定・目（`GetEyes`＝位置+60）・銃（`SwatMesh` の手のソケット）が一緒に 48cm 下がる。見た目は「モデル全体が 48cm 沈む」（足は床に埋まる。膝を曲げたポーズではない）。測定：立ち 頭 z=172.2 → しゃがみ 頭 z=124.2（床 2.0 から 170 → 122cm、仕様の約 110 より 12cm 高い）。`ABP_PR_Swat` には触っていない。しゃがみの解除は `CrouchGuard`（毎 Think：しゃがんでいて、State 1・Burst・型 2 の組でなければ立つ）。

動き：
- 抽選：接敵（State が 1 でない状態から見えた瞬間）に 1 回。表は §3.2 のとおり（距離は接敵時の Bot とプレイヤーの距離）。`DebugStyle` が 0 以上なら固定。ログ `[Bot] style=N dist=m`
- 型 1：Strafe を 0.12〜0.2 秒にして必ず反対向き（`JigDir` で交互）、バースト 1〜2 発。型 3：その接敵の最初の Strafe だけ 0.5〜0.7 秒。型 4：バースト 1〜3 発のあと体力に関係なく Retreat、Repeek までの待ち 1.0〜2.5 秒。型 2：バースト内の 2〜3 発目でしゃがみ（`AfterShot`）、バーストが終わると解除。型 5（決め撃ち）：見失って 3 秒以内・前の位置から 4m 以内で出てきたとき、`SnapChance` の確率で反応時間を 0.1 秒に
- 待ち構えていた接敵（State 0 の止まった状態から見た）では、最初のバーストには型を使わない（2 回目から）
- ミス：焦る（`ContactK`：動いていて 6m 以下の新しい接敵のとき `bStopFail` を立てて Stop を飛ばし、最初のバーストを 6〜10 発）、悪いリロード（`EngageLostHook`：交戦が終わるとき残弾 6 割未満ならその場でリロード）、空振りの警戒（`WhiffWatch`：捜索の時間切れで 3〜6 秒 `IdleThink` を止めて動かない）、釣られる（`LureCheck`：`AlertThink` の移動の停止距離を 500→50cm）、視野が狭い（`EngageLostHook`：`MistakeMul` が 1.0 以上なら交戦終了から `NarrowTime` 4 秒、`CanSeeTarget` の視野を 45°→25°）。確率は 基本確率 × `MistakeMul` × 個性（前のめり：焦る・釣られる 1.5 倍、堅実：全部 0.5 倍。Director と同じ `GameMode.Personality[配列の順 % 5]` を `FindPers` で引く）

仕様との差分：
- 覗き方（§4）が未実装（上）
- しゃがみのポーズ（上）。頭の高さは 122cm（仕様の約 110）
- 型 3（大きく出る）の「最初の Strafe」は、今の流れでは最初のバーストのあと。型 1 は Stop の短縮（仕様の「止まっている時間が短い」）を入れていない（Strafe 0.12〜0.2 秒と必ず反対への切り替えだけ）。型 4 の「近くの遮蔽が無いとき」は今の `StartRetreat` のとおり（その場リロード→Strafe）
- 「待ち構えていた」の判定は、`NewContact` の時点の速度が 200 以下（DuelMode 0）
- 「悪いリロード」は仕様の「Burst の後」ではなく、交戦が終わる（`EngageLost` の時間切れ）とき。個性の係数の「釣られる」は `Kind` 3、「焦る」は `Kind` 0
- 乗数の数値（距離・個性・武器の ×0.5 など）は `PickStyleK` の中の直書き

確認（L_Canal の PIE。ハード相当は、コントローラの `bStand`=false・`StyleSet`=2 を直接設定。GameInstance の難易度は変えていない）：
- 型 1：`DebugStyle`=1 で `[Bot] style=1 dist=…`、DuelMode が 1（Strafe）と 3（Burst）を 0.25 秒ごとに行き来し、`StrafeDir` が毎回 ±1 に反転、`BurstLeft` 1
- 型 2：`DebugStyle`=2 で `style=2`。バースト中に `bCrouched` が true、アクターの z が 90.2→42.2、頭の z が 172.2→124.2、0.4 秒後に false に戻った
- 型 4：`DebugStyle`=4 で、バースト 1〜2 発（`BurstLeft` 2）のあと体力 100 のまま DuelMode 4（Retreat）→ 5（Repeek 待ち、2 秒以上）
- しゃがみ中の当たり判定：Bot 0 に `SetBotCrouch(true)` のあと、頭の高さ（z=124.1）への水平の射線が `Head`（コンポーネント。武器の `GetHitDamage` はこの名前のタグでヘッドショットにする）に当たり、立っていたときの頭の高さ（z=172.1）の射線は何にも当たらない。胴の高さ（z=76.6）は `Body`
- ミス：確率の変数を 100 にし `MistakeMul`=1.5 で、`WhiffWatch`・`LureCheck`・`EngageLostHook`（狭い視野）を直接呼んで `[Bot] mistake=whiffwatch` / `lure` / `narrow` のログ、`ContactK` を直接呼んで `[Bot] mistake=panic` のログ。確認のあと、その PIE の変数は PIE を止めて破棄（アセットの値は変えていない）
- 実行時エラー：ログの `Blueprint Runtime Error` は 0 件（ただし、死んだ Bot のコントローラに `EngageLostHook` を直接呼んだときだけ `Bot` が None のエラーが出た。実際の流れでは `Think` が `IsValid(Bot)` の中で呼ぶので起きない）
- 全 Blueprint の一括コンパイル：25 個、失敗 0

確認の追記（2026-11-13、Step 31 仕上げ。難易度ごとに PIE を起動し直し、ナビメッシュの無い空中の床に Bot を輪にして置き、プレイヤーを視界へ入れて接敵を作った。接敵ごとにログ `[Bot] style=` を数えた。確認後、セーブの難易度は元の 0（イージー）に戻した）：
- イージー（`StyleSet` 0、`MistakeMul` 2.0）：接敵 9 回、すべて `style=0`
- ノーマル（`StyleSet` 1、`bStand` true、`MistakeMul` 1.3）：接敵 10 回、`style=0` が 8、`style=2` が 2。型 1・3・4 は出ない。棒立ち（速度 0）のまましゃがみ、`bCrouched` が true になり実際にカプセルが縮んでアクターの z が 48cm 下がり、また立った（ログ `[Bot] crouch on`）
- ハード（`StyleSet` 2、`bStand` false、`MistakeMul` 0.8、`SnapChance` 0.5）：距離 15m・19m の接敵 20 回、`style=0` が 8、`1` が 2、`2` が 5、`3` が 1、`4` が 4（40% / 10% / 25% / 5% / 20%）。表の重み（4:2:2:1:1 ＝ 40 / 20 / 20 / 10 / 10%）に対し、個性（前のめり・堅実）の補正が入るので大きな外れではない。動く型の確認では 20 回の接敵に速度 400〜660 の左右移動が出た
- 型 3：`DebugStyle`=3 の新しい接敵で、最初の Strafe は約 0.75 秒・約 430cm 移動して止まり、そのあとの Strafe は約 0.3 秒・約 100cm（時間を 0.2〜0.3 倍にして 0.1 秒間隔で位置を記録）
- 悪いリロード：ノーマル相当で `BadReloadChance`=100 にし、交戦を終えさせると 10 体中 9 体が `[Bot] mistake=badreload`（`narrow` も同時に出た）
- 焦る：`NewContact` からの流れで `[Bot] mistake=panic`（`PanicChance`=100。動いている Bot＝空中に打ち上げた Bot が距離 3m で接敵）。**不具合を直した**：`ContactInit` の「待ち構えていた」の判定が `DuelMode`==0 だけで、歩いて近づく Bot も待ち構え扱いになり、「焦る」が実際の流れでほぼ起きなかった。速度 200 以下も条件に足した（`ContactInit` の `Held` ＝ DuelMode が 0 かつ Bot の速度が 200 以下）
- ランタイムエラー：ログの `Blueprint Runtime Error` は 0 件（AssetCheck の lint 警告は除く）。ただし、StartRound をしないまま Bot を置くと GameMode の `Personality` 配列（長さ 0）の添字警告が出る（実際のラウンドでは出ない）。ナビメッシュの無い床の Bot が `reinforce whiff` を 0.1 秒ごとに繰り返し出す（確認用の置き方による）

未確認：
- 型 5（決め撃ち）の実際の動き：「見失って 3 秒以内の再接敵」は、交戦が終わる（`EngageLost`）までが長く（見えなくして 30 秒以上経っても State 1 のまま）、自然な流れで作れなかった。`State` を 0 に書き換える、`NewContact` を直接呼ぶ、でも `style=5` は出なかった。ログ分岐と判定は ContactK の中にある
- 覗き方の寄り確認・取り返しへの適用、相手が見えたあとの出直し
- 全 Blueprint の一括コンパイル（今回は変更した 3 個がそれぞれコンパイルでき、エラー 0）

## 6. Step 32：名前、チャット、キルログ

### 6.1 名前と人柄
- `DT_BotNames`（新規）：名前を 20 個ほど。ランクマッチにいそうな名前にする。実在のゲームのキャラクター名は使わない

  例：`ponkotsu_aim`、`xX_Shinobi_Xx`、`mid_wa_ore`、`takoyaki99`、`EcoRoundKing`、`NoHeal4U`、`tanuki_soba`、`AFK_kamo`、`1tap_or_die`、`kado_machi`（角待ち）、`sirokuma`、`ramen_daisuki`、`yoru_dake_tsuyoi`、`W_key_only`、`heta_no_yokozuki`

- 試合開始時に、枠ごとに名前と人柄 `Manner` を決めて `BP_PR_GameMode` に持つ（個性 `Personality` と同じ持ち方。ラウンドをまたいで同じ）
- `Manner`：0 礼儀正しい／1 ふつう／2 口が悪い。口が悪いのは 1 チームに 1 人まで（確率 60% で 1 人入る）。前のめりの個性は口が悪くなりやすい
- プレイヤーの名前は `YOU`

### 6.2 キルログ
今の「最新の 1 件を Canvas に描く」方式（[06](06_ui.md) の v0.21）を置き換える。

- `WBP_GameHUD` の右上に `KillFeedBox`（縦に最大 5 件、1 件 5 秒で消える）
- 1 件の表示：`倒した人  [武器名]  倒された人`、ヘッドショットは印を付ける。自分が関わる行は目立つ色
- `BP_PR_GameMode.PushKill(KillerName, VictimName, WeaponName, bHead, bPlayerInvolved)`
- Bot がプレイヤーを倒したとき、スパイクの爆発で倒れたときも出す
- `BP_PR_HUD.DrawKillFeed` は呼ばないようにする

### 6.3 チャット
- `WBP_GameHUD` の左下（体力表示の上）に `ChatBox`（最大 6 行、1 行 8 秒で消える）。表示は `[ALL] 名前: 本文`。口が悪い発言も色は同じ
- `BP_PR_GameMode.PushChat(Name, Text)`
- `DT_BotChat`（新規、`S_BotChat`：`Event` Name、`Manner` int（-1 は誰でも）、`Text`、`Weight`）
- `BP_PR_GameMode.BotSay(Slot, Event)`：その Bot の人柄に合う行から重み付きで 1 つ選んで出す。全体で 2 秒に 1 行まで。同じ Bot は 6 秒に 1 回まで。倒された Bot も発言できる（全体チャットなので）
- 英語の短い言い回しと日本語を混ぜる。きつすぎる言葉、差別的な言葉は入れない

| Event | いつ | 確率 | 礼儀正しい | ふつう | 口が悪い |
|---|---|---|---|---|---|
| `RoundStart` | 戦闘開始 | 15% | `glhf` | `よろ` | `ez game` |
| `Spotted` | 接敵した瞬間（報告） | 40% | `{場所}に 1 人います` | `{場所}!` | `{場所} いるって` |
| `Rotate` | 寄りに出る | 35% | `{サイト} 寄ります` | `{サイト} 行く` | `しゃーない行くわ` |
| `KilledPlayer` | プレイヤーを倒した | 50% | `gg` | `ないす` | `ez` `noob` `?` |
| `Died` | プレイヤーに倒された | 45% | `nice shot` | `why!?` `え、そこ？` | `は？` `lag` `運だけ` |
| `DiedHeadshot` | ヘッドショット 1 発で倒された | 60% | `nice shot!` `うま` | `ns` `ワンタップ…` | `チート？` `まぐれ` |
| `MateDied` | 味方が倒された | 20% | `どんまい` | `まじか` | `何してんの` |
| `RoundWin` | Bot 側がラウンドを取った | 40% | `gg` | `ナイス` | `GG EZ` `noob` |
| `RoundLoss` | Bot 側がラウンドを落とした | 25% | `nt` | `つよ` | `味方が弱い` |
| `Flashed` | フラッシュを食らった | 30% | `見えません` | `まぶし` | `うざ` |
| `Clutch` | 最後の 1 人になった | 30% | `がんばります` | `1 人かよ` | `俺だけでいい` |
| `Planted` | スパイクを設置された | 30% | `{サイト} 解除行きます` | `{サイト} 設置` | `誰も見てないの？` |
| `MatchWin` / `MatchLoss` | 試合終了 | 80% | `gg wp` | `gg` | `ez` / `gg（言わない）` |

- `{場所}` は [22](22_map_canal.md) §2.2 の `BP_AreaName.DisplayName`、`{サイト}` は A / B
- **チャットは情報になる**：`Spotted` と `Rotate` は本当のことを言う。プレイヤーはこれを読んで裏をかける。難易度が高いほど出る確率を下げる（ベリーハード以上は `Spotted`・`Rotate`・`Planted` を 0.3 倍）
- 設定画面に「チャットを表示」のチェック（初期オン）を足す

### 6.4 完了条件
- 1 試合遊んで、キルログが複数行並ぶ。Bot に倒された行も出る
- 各 Event を 1 回ずつ起こして表示を確認する（確率を一時的に 100% に）
- `Spotted` の場所の名前が、実際の位置と合っている
- 口が悪い Bot が 1 チームに 2 人以上いない

### 6.5 実装結果（Step 32 の途中、2026-11-13。ここまでで一度止めた）

済み：
- 型 5（決め撃ち）の修正：見えない時間を `LastSeenTime`（`RetreatTick` が更新し続ける）ではなく `VisibleTime`（本当に見えた最後の時刻）から測るようにし（`ContactInit`）、`ContactK` の条件に「見えなかった時間が 0.3 秒より長い」を足した。`ContactK` を直接呼び、`SinceSeen`=1.5 で `[Bot] style=5`、0.1 では出ないことを確認。**自然な流れ（実際に見失って 3 秒以内に再び見える）での確認は未確認**（この環境では PIE のゲーム時間が呼び出しの合間にほとんど進まず、プレイヤーの出し入れの時間が作れなかった）。なお、既に `EngageSeen` は State 1 でも見えない時間が 0.5 秒を超えれば `NewContact` を呼ぶ作りで、`LoseTime`（3 秒）で State 1 が終わる。「State 1 が 30 秒以上残る」ことは今回は確認できなかった
- データ：`/Game/PARORANT/Data/` に `S_BotName`、`DT_BotNames`（N01〜N20）、`S_BotChat`（Event、Manner、Text、Weight）、`DT_BotChat`（50 行。行名は `<Event>_<Manner><a/b/c>`。口が悪い人柄の `MatchLoss` は行なし＝言わない）。名前は仕様の例から 1 つ（`xX_Shinobi_Xx`）を `xX_Kage_Xx` に変え、5 つを新規に足した。実在の人物・商標は使っていない
- `BP_PR_GameMode`：変数 `KFTexts`/`KFExp`/`KillFeedStr`/`KFLastT`、`CTexts`/`CExp`/`ChatStr`/`CLastT`、`NameBase`、`RudeSlot`、`NextSlot`、`LastChatT`、`LastSaySlot`、`LastSayT`、`ChatMul`（Tuning。確認用に 100% へ上げる倍率）。関数 `PushKill(KillerName, VictimName, WeaponName, bHead, bPlayerInvolved)`（最大 5 件、各 5 秒の期限を `KFExp` に持つ。表示用の文字列は `JoinKF` が `KillFeedStr` に作る）、`PushChat(CName, CText)`（最大 6 件、8 秒。`JoinChat` が `ChatStr`）、`EnsureInit`（初回に `NameBase`=0〜19、`RudeSlot`=60% で 0〜7、40% で -1）、`MannerOf(Slot)`（`RudeSlot` なら 2、そうでなければ (Slot×7+NameBase)%3==0 で 0、それ以外 1。口が悪いのは全体で最大 1 人）
- 確認（PIE）：`PushKill("YOU","takoyaki99","Vandal",true,true)` で `KillFeedStr` が `> YOU  [Vandal] [HS]  takoyaki99`、`PushChat` で `ChatStr` が `[ALL] takoyaki99: why!?`、`MannerOf(3)`=1（`NameBase`=1、`RudeSlot`=5）

### 6.6 実装結果（Step 32 の続き、2026-11-13）

作ったもの：
- 名前：`BP_PR_AIController.ChatSlot`（-1）を `OnPossess` で `GameMode.NextSlot` から受け取り、`NextSlot` を +1。`GameMode.SpawnDefenders` の先頭で `NextSlot`=0 に戻すので、ラウンドをまたいでも同じ順番の席が同じ名前・人柄。`NameOf(Slot)`（`(NameBase+Slot*3)%20+1` 行目の `DT_BotNames`）。`AIController.MyName()`、`Say(Event, Extra)`（`ChatSlot`>=0 のとき `GameMode.BotSay`）、`SayAt(Event, Loc)`（`BFL_PR.AreaInfoAt` の `DisplayName` を `Extra` にして `Say`）。試合の最初に `EnsureInit`（NameBase が -1 のとき決める）。再戦はレベルを開き直すので決め直しになる
- `GameMode.BotSay(Slot, Event, Extra)`：全体 `ChatGap`（2 秒）、同じ Bot は `SameGap`（6 秒、直前に話した Bot だけ見る簡易版）、確率は `DT_BotChat` の `Chance_<Event>` 行（`Event`="Chance"、`Weight`＝%）×`ChatMul`、`Spotted`/`Rotate`/`Planted` は難易度が `ChatLowDiff`（3＝ベリーハード）以上なら ×`DiffChatMul`（0.3）。人柄に合う行（`Manner`==-1 か `MannerOf(Slot)`）から重み付きで 1 つ（1 回の走査で選ぶ）。`{場所}`・`{サイト}` は `Extra` で置き換える。作業用の変数：`TmpTotal`、`TmpText`
- 表示：`WBP_GameHUD` に `KillFeedBox`（右上、x=1380 y=150）、`ChatBox`（左下、x=20 y=560）、関数 `UpdateFeed`（Construct のタイマーの連鎖で `UpdateArea` のあとに呼ぶ。`KillFeedStr`/`ChatStr` を表示し、`KFLastT` から `KFShowTime`（5 秒）、`CLastT` から `ChatShowTime`（8 秒）で透明にする。チャットは `GameInstance.bShowChat` が false でも透明）。旧 `BP_PR_HUD` の `DrawKillFeed` は呼び出しを外した（関数は残す）
- 設定：`GameInstance.bShowChat`（既定 true）、`SG_PR_Settings.bShowChat`、`SaveSens`/`LoadSens` に保存・読み込み、`GameInstance.SetShowChat`、`WBP_KeyBinds` に「チャットを表示」のチェック（`ChkChat`、x=700 y=640）
- 呼び出し：`BP_PR_Bot.DeathHook(bHead, bByPlayer)`（`TakeWeaponDamage` の体力 0 以下の分岐。プレイヤーが倒したとき `PushKill("YOU", 名前, 武器 ID, HS, true)`、`Died`/`DiedHeadshot`、`MateDied`）、`BP_PR_Character.KilledHook(Src, bHead)`（`AddDeath` の後。`PushKill(Bot の名前, "YOU", Bot の武器 ID)` と `KilledPlayer`）、`NewContact` の最後で `Spotted`（プレイヤーの位置の場所名）、`Reinforce` の最後で `Rotate`（目的地の場所名）、`MatchTick` の戦闘開始で `RoundStart`、`EndRound` の最後で `RoundWin`/`RoundLoss`（試合が決まるラウンドは `MatchWin`/`MatchLoss`）

起こせた Event（前半の確認。`BotSay` を直接呼んだもの）：RoundStart、Spotted、Rotate、KilledPlayer、Died、DiedHeadshot、Clutch、Planted、MatchWin、MatchLoss、MateDied、Flashed。実際の流れでの確認は §6.7。

### 6.7 実装結果（Step 32 仕上げ、2026-11-13）

画面の見た目（L_Canal の PIE。スクリーンショットは `docs/images/chat32_*.png`）：
- 最初の見た目は、白い文字が明るい壁に埋もれる、キルログが左揃えで左上基準の絶対位置（解像度が変わるとずれる）、設定の「チャットを表示」がキー一覧の上に重なる（`RootCanvas` 直下に絶対位置）、という問題があった
- 直した点：`KillFeedBox` を右上基準（`DiffText` の下、右端から 24）の右揃え、`ChatBox` を左下基準に固定。両方とも文字 20、縁取り 2（`OutlineColor` は他の HUD と同じ濃紺）。設定の「チャットを表示」は新しい行 `ChatRow`（`Body` の `CrossRow` の次）に移し、キー一覧と重ならなくした（`chat32_setting.png`）
- 確認：キルログ 5 行（最長の名前と `[HS]` 付き）・チャット 6 行（長い日本語）が箱に収まり、ミニマップ、現在地の名前、体力、スキル、スコア、難易度、クレジットと重ならない（`chat32_killfeed.png`、`chat32_chat.png`、`chat32_both.png`）。実際の流れの撮影は `chat32_flow.png`。日本語・英数字の文字化けなし
- 仕様との差分：§6.2 の「自分が関わる行は目立つ色」は、1 つの TextBlock では行ごとの色を付けられないので、行頭の `> ` の印で代用（色を付けるなら RichTextBlock か行ごとのウィジェットが必要）

実際の流れでの確認（`TakeWeaponDamage` を致死量で呼び、`DamageInstigator` にプレイヤーのパスを渡した）：
- プレイヤーが Bot を倒す：キルログ `> YOU  [Knife]  EcoRoundKing`、ヘッドショットは `[Knife] [HS]`。旧キルログは二重に出ない（呼び出しを外してある）。各行の期限は 5 秒（下記の直し）
- Bot がプレイヤーを倒す：`> AFK_kamo  [Sheriff] [HS]  YOU` と `KilledPlayer`（`gg`）
- Spotted：`ミッドに` ではなくプレイヤーの実際の位置の場所名（スポーン位置で `船着き場!`、`船着き場に 1 人います`）。Died（`why!?`、`nice shot`）、DiedHeadshot（`ワンタップ…`、`うま`）、MateDied（`まじか`、`どんまい`）、Clutch（`1 人かよ`、`がんばります`）、RoundStart（`glhf`、`よろ`）、RoundWin（`gg`）、RoundLoss（`nt`、`つよ`）、MatchWin（`gg wp`）、Planted（`B 解除行きます`。`SiteName` は PlantZone の `A`/`B`）
- 未確認のまま：Rotate（`Reinforce` の流れ。`BotSay` の直接呼び出しでは確認済み）、MatchLoss（`BotSay` の直接呼び出しのみ）。Flashed は Step 34 で呼ぶ
- 名前：ラウンドをまたいでも `ChatSlot` は 0〜2 で同じ席が同じ名前（`NameOf` は `NameBase` と席だけで決まる）。口が悪い人柄は `RudeSlot` が 1 つだけなので 1 人以下（`RudeSlot` が -1 のときは 0 人）
- 「チャットを表示」を切る：チャットは出ず（`ChatStr` には溜まる）、キルログは出る。`bShowChat` は PIE を止めて起動し直しても false のまま残った。確認後、true に戻した

仕様との差分（§6.6 から残るもの）：`Rotate` の `{サイト}` は場所名（`DisplayName`）。Bot 以外（スキル・スパイク）による Bot の死亡はキルログに出さない。

直した不具合・足したもの：
- RoundWin／RoundLoss が表示されなかった件：`EndRound` の分岐は正しかった（`bWin` はプレイヤーの勝ちなので、Bot の RoundLoss＝プレイヤー勝ち）。原因は直前の KilledPlayer／Died／MateDied が `LastChatT`・`LastSayT` を更新するため、`ChatGap` 2 秒と `SameGap` 6 秒に当たって BotSay の最初の分岐で捨てられていたこと。`EndRound` の発言の前に `LastChatT`・`LastSayT` を -100 に戻すようにした（ラウンド終了の発言は間隔の制限を受けない。確率は残る）。単独の `EndRound` で RoundLoss、MatchWin、実際の流れで RoundWin／RoundLoss が出ることを確認
- 発言者が倒された Bot にならないように：`BP_PR_GameMode.SayAlive(Event, Extra, Exclude, bAny)`（生きている Bot の `ChatSlot` から 1 人を等確率で選ぶ。`Exclude` は除く席、`bAny` が true で生きている Bot がいなければ `StartBots` 範囲の乱数の席）。MateDied（`DeathHook`、倒れる Bot を除く）、RoundStart（`MatchTick`）、RoundWin／RoundLoss／MatchWin／MatchLoss（`EndRound`、`bAny`=true）、Planted、Clutch が使う。作業用の変数 `TmpPick`（-1）を追加
- Planted：`PlantSpike` の最後で `SayAlive(Planted, SiteName)`
- Clutch：`DeathHook` で `AliveBots`==2（倒れる Bot はまだ `bDead` が false）のとき `SayAlive(Clutch, 倒れる Bot を除く)`。間隔の制限で消されないよう MateDied より先に呼ぶ
- キルログとチャットの古い行：`PushKill`／`PushChat` が、最後の追加から 5 秒／8 秒以上経っていれば配列を空にしてから追加する（以前は何分前の行が新しい行と一緒に出た）。1 行ごとの期限ではなく、最後の追加からの時間で全部を消す簡易版
- `BotSay` に `[Chat] skip-gap`／`skip-chance`／`skip-notext <Event>` のログを追加（捨てた理由が分かる）

確認時の注意：`ChatGap`・`SameGap` を 0 にして同じ瞬間（同じフレーム）に複数回話させると、時刻の丸め（変数が単精度）で `now - LastChatT` が負になり、間隔の判定で捨てられることがある（`skip-gap Died` のログ）。実際の値（2 秒と 6 秒）では起きない。同じ Bot は 6 秒に 1 回なので、Spotted の直後の Died は出ないことがある（仕様どおり）

実行ログ：`Saved/Logs/PARORANT.log` の `Blueprint Runtime Error` は 0 件、`Accessed None` の実行時メッセージも 0 件（AssetCheck の lint 警告は除く）。変更した `BP_PR_GameMode`、`BP_PR_Bot`、`WBP_GameHUD`、`WBP_KeyBinds` はコンパイル 0 エラー。

試遊で見てほしい点：実際の撃ち合いでのキルログ（複数行、5 秒で消えるか）、チャットの頻度（確率のまま。出すぎ・少なすぎ）、設定画面の「チャットを表示」のクリック、Rotate の発言（寄りの場面）、実解像度（1920×1080）での文字の大きさ。

## 7. Step 34：Bot のスキル

プレイヤー用のアクター（[18](18_skills_minimap.md)、[19](19_skill_tuning.md)）を流用する。

| スキル | 使う場面 | 動き |
|---|---|---|
| スモーク | 取り返し（設置後）で、サイトまで 15m 以内に来たとき | サイトの入口（自分とスパイクの間で、スパイクから 5m の位置）に煙を出す。煙は Bot の視界も遮る（今の仕様どおり）ので、出した Bot は煙を抜けて入る |
| フラッシュ | 覗き方が「大きく飛び出す」のとき、または 2 体での突入の直前 | 角の向こうへ投げ、炸裂（1.0 秒後）に合わせて出る。**プレイヤーにも効く**（今の「自分のフラッシュは見ていたら食らう」の仕組みを使う） |

- 回数は §1 の表（Bot 全体で 1 ラウンドに 1〜2 回）。`BP_PR_Director` が数える
- 使う Bot：スモークは最初にサイトへ着く Bot、フラッシュは前のめり・寄り屋の個性を優先
- 投げる動作のアニメは無いので、0.4 秒立ち止まってから出す（その間は撃たない）
- スモークの持ち主を区別する：プレイヤーが F で展開する処理（[19](19_skill_tuning.md)）が Bot のアンカーを拾わないこと。Bot は投げて即展開でよい
- Bot のフラッシュが味方の Bot にも効くかは、今の判定をそのまま使う（効いてよい。下手さの表現になる）
- プレイヤーへの予告：フラッシュは投げる音、スモークは展開の音が鳴る。チャットの `Planted` と合わせて、取り返しが来る合図になる
- 完了条件：設置して待つと、スモークが入口に出る。Bot のフラッシュでプレイヤーの画面が白くなる。イージーでは使わない。1 ラウンドの回数が上限を超えない

### 7.1 実装結果（Step 34、2026-11-13）

作ったもの（既存のスモーク／フラッシュのアクターをそのまま再利用。Bot 用の新しい効果は無い）：
- `BP_PR_GameMode`（変数 BotSkill カテゴリ）：`BotSkillUsed`（0）、`BotSkillMax`（0）、`BotSmokeDone`（false）、`SmokeApproach` 1500、`SmokeOffset` 500、`SmokeHeight` 50、`FlashOffset` 400、`FlashHeight` 120。関数 `BotSkillInit`（`RoundInit` の最後から呼ぶ。使用数 0、`BotSmokeDone` false、`BotSkillMax`＝`Clamp(GameInstance.Difficulty, 0, 2)`＝イージー 0／ノーマル 1／ハード以上 2。ログ `[Bot] skill budget max=N`）、`BotSmokeWanted(BotLoc)→Ok, Loc`、`BotSpawnSmoke(Loc)`、`BotFlashWanted(Corner, Dest)→Ok, Loc`、`BotSpawnFlash(Loc)`。回数は Director ではなく GameMode が数える（Director は `bActive` が false の難易度がある。使い方は同じ）
- `BP_PR_AIController`：変数 `SkillKind`（0 なし、1 スモーク待ち、2 フラッシュ待ち、3 フラッシュ炸裂待ち）、`SkillUntil`、`SkillLoc`、`FlashTryId`（-1）、Tuning `SkillPause` 0.4、`FlashWait` 0.8、`FlashTrigDist` 600。関数 `SkillBusy`（待ち時間の状態機械。待ち中は true）、`RetakeSkill`、`FlashSkill`。`RetakeThink` の先頭に `RetakeSkill`、`PeekTick` の先頭に `FlashSkill` を挟み、busy の間は元の処理（移動・覗きの進行）を飛ばす
- `BP_PR_SkillFlash`：関数 `Freeze`（`Move` を止めて無効化。Bot が置いたフラッシュが 1800 の初速で飛ばないため）。`BlindOne` の `SetBlindUntil` の直後に `Say("Flashed")`（プレイヤーのフラッシュが Bot に効いたときも同じ処理なので、どちらでも呼ばれる）

動き：
- スモーク（取り返し）：`RetakeThink` が毎回 `BotSmokeWanted` を呼び、Phase 2・スパイク有効・まだ煙を出していない・Bot がスパイクまで 2D で 15m 以内、のとき、使用数を +1 して `BotSmokeDone`＝true にする（最初に着いた Bot だけ）。位置は「スパイク＋（スパイクから Bot への水平単位ベクトル）×500＋z 50」。Bot は 0.4 秒止まり（`StopMovement`、`RetakeThink` の残りを飛ばす）、そのあと `BotSpawnSmoke` が `BP_PR_SmokeField` を直接出す（アンカーは使わない。プレイヤーの F 展開が Bot のアンカーを拾う問題は起きない）。ログ `[Bot] skill=smoke commit used=N`、`[Bot] skill=smoke spawn at …`
- フラッシュ（飛び出す前）：`PeekTick` が `FlashSkill` を呼ぶ。`PeekType`==2（大きく飛び出す）、`PeekPhase`==0（角へ走っている途中）、角まで 2D で 600 以内、その覗きでまだ試していない（`FlashTryId`≠`PeekT`。1 回の覗きにつき 1 回だけ判定）、のとき `BotFlashWanted`。位置は「角＋（角→目的地の水平単位ベクトル）×400＋z 120」。0.4 秒止まって `BotSpawnFlash`（`BP_PR_SkillFlash` を直接出して `Freeze`）、そのあと 0.8 秒待って（炸裂 1.0 秒後に合わせる）覗きを続ける。効果は既存の `BlindOne`／`BlindSelf` のまま（プレイヤーは背を向けていれば効かない、Bot は前方 ±60°・5000cm 以内・視線が通れば 5 秒）
- 回数：使用数が `BotSkillMax` 以上なら `[Bot] skill=deny kind=smoke|flash reason=limit` を出して使わない。スモークは 1 ラウンド 1 回まで（最初の 1 体）。残りの回数はフラッシュに使う
- 投げる音：既存の音の `SFX_Beep` を流用（スモーク ピッチ 0.6、フラッシュ 1.6。仮）。フラッシュは炸裂で既存の `SFX_Hit`

確認（L_Canal の PIE。`BotSkillInit`／`PlantSpike`／`BotSpawnFlash` などを `call_actor_function` で直接呼んだ。難易度は `GameInstance.SetDifficulty` で切り替え、確認後に 0 へ戻した）：
- イージー：`skill budget max=0`、`PlantSpike` の直後に `[Bot] skill=deny kind=smoke reason=limit` が 1 回だけ。煙は出ない
- ハード（`max=2`）：`PlantSpike`（A サイト、スパイク (1700,-2300)）で `skill=smoke commit used=1`、0.4 秒後に `skill=smoke spawn at X=2199.586 Y=-2320.348 Z=110`（スパイクの +499cm、仕様の 5m）
- フラッシュ（ハード、自然な流れ）：Bot の覗きから `skill=flash commit used=1` → 0.5 秒後 `flash spawn at X=-1385.5 Y=202.6 Z=130` → 約 1 秒後 `[Flash] blinded=1`。続けて `commit used=2`、3 回目の判定は `skill=deny kind=flash reason=limit`（上限を超えて使わない）
- プレイヤーへの効果：フラッシュを目の前に出すと画面が真っ白（`docs/images/skill34_flash_white.png`）。コントロール回転を 180° にして背を向けて出すと白くならない（`skill34_flash_away.png`）。スモークの出方（`skill34_smoke.png`）
- Bot に効く：Bot の前方 400cm に出して、その Bot の `BlindUntil` が今＋5 になった（他の 2 体は 0）
- `Flashed`：`ChatMul`＝100 で `ChatStr` に `[ALL] AFK_kamo: まぶし`（`ChatMul`＝1 のときは `skip-chance Flashed`＝確率で省かれる）
- 実行ログの `Blueprint Runtime Error` は 0 件。全 Blueprint の一括コンパイル 25 個、失敗 0

仕様との差分・仮決め：
- 「2 体での突入の直前」のフラッシュは作っていない（覗き方 2 のときだけ）。寄りの到着後（Reinforce）の合図が今のグラフに無いため
- 投げる動作は作らず、目的の場所に直接出す（放物線なし）。仕様の「0.4 秒立ち止まる」は入れた。止まっている間、見えている相手に撃つのは止めていない（`RetakeThink`／`PeekTick` の移動の処理だけを止める）
- 回数は GameMode が数える。スモークを出す Bot は「最初にサイトへ着く Bot」を 15m に入った最初の 1 体で代用。使用数は決めた時点で数えるので、0.4 秒の間に倒されるとその回は無駄になる
- フラッシュを出した Bot 自身や味方の Bot も、今の判定のとおり、前方・視線が通れば目が見えなくなる（仕様どおり。出す位置は角の向こう 4m なので、角に隠れていれば当たらない）。実際に出した Bot が目隠しになるかの確認は、位置が毎回変わるので未確認
- 仕様の「回数の上限は表」の表の値（0・1・2・2）は `Clamp(Difficulty, 0, 2)`。配列にはしていない

未確認：ノーマル（max=1）の実際の流れ、フラッシュを出した本人が目隠しになる頻度、スモークの見た目の確認（`skill34_smoke.png` は目の前の直接生成。実際の取り返しの位置・向きでの見え方）、投げる音の聞こえ方（仮の流用）、2 体のフラッシュを同時に出す・スモークとフラッシュが重なる場面

試遊で見てほしい点：スパイクを設置して待つと、最初に近づいた Bot が立ち止まり、スパイクの手前に煙を出すか／ハードで Bot の覗きの前にフラッシュが飛んできて白くなるか（背を向けて避けられるか）／イージーでは何も使わないか／1 ラウンドに 3 回以上使わないか／煙の中の Bot が取り返し（解除）を続けるか／`Flashed` の「まぶし」などの発言の頻度
