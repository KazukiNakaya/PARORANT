# 25. 味方 Bot の実装仕様（Step 37）

方針：とても弱い味方 Bot を入れ、プレイヤーが**おとり・索敵役として使う**（2026-11-12 ユーザー指示）。撃ち合いで頼れる味方は作らない。進め方は [21](21_impl_rules.md)。値はすべて（仮）。

## 1. ねらう遊び

- 味方を先に行かせて、敵がどこにいるかを知る（味方が見つけた敵がミニマップに出る。倒された場所も分かる）
- 味方に音を立てさせて敵を寄らせ、反対のサイトを攻める（フェイク）
- 味方が撃ち合っている間に、横から倒す（ベイト）
- 味方は勝敗に数えない。**プレイヤーが倒されたらラウンドは負け**（今のまま）

## 2. 仕様

| 項目 | 内容 |
|---|---|
| 人数 | 2 体（`AllyCount`）。スタート画面に「味方 Bot：あり／なし」の選択を足す（初期はあり。保存する） |
| 見た目 | 敵と同じ SWAT。色で区別（敵は赤い輪郭、味方は水色）。頭上に名前。ミニマップに水色の点 |
| 名前 | `DT_BotNames` から。人柄は「ふつう」固定で、頼りない発言をする（§5） |
| 体力・装備 | 体力 100、アーマーなし、クラシック固定。購入なし |
| 強さ | 反応 1.5 秒、初期誤差 20°、収束 2.0 秒、頭は狙わない、棒立ち。与えるダメージは 0.3 倍 |
| 味方への誤射 | 当たらない（プレイヤー ⇔ 味方 Bot はダメージなし）。プレイヤーのフラッシュは味方にも効く |
| スパイク | 設置も解除の妨害もしない |
| 敵の数の表示 | 味方は数えない |
| 復活 | 次のラウンドで全員戻る |

## 3. 命令

プレイヤーはキー 2 つで命令する（初期キーは Z と X。`DT_KeyBinds` に足す。空いていなければ別のキー）。

| キー | 命令 | 動き |
|---|---|---|
| Z | 行け | 照準の先の床へ、命令を受けていない味方（いなければ近い方）1 体が走って行く。着いたらその場で見張る。走るので足音が出る |
| X | 集まれ | 全員がプレイヤーの後ろ 3〜5m について来る（初期状態） |

- 命令した場所に印を 2 秒出す。チャットに返事が出る（`了解` `行きます` `えぇ…`）
- ついて来るとき、プレイヤーが歩けば歩く（足音を合わせる）。プレイヤーの前には出ない
- 敵を見つけたら、その場で止まって撃つ（追いかけない）。見失ったら命令の動きに戻る
- 購入フェーズ中はスポーンで待つ

## 4. 情報の出方

| 出来事 | プレイヤーに見えるもの |
|---|---|
| 味方が敵を見つけた | その敵を 2 秒表示（リコンと同じ `RevealUntil`）、ミニマップに赤い点、チャットに `{場所}に敵！` |
| 味方が撃たれた | チャットに `撃たれてる！` |
| 味方が倒された | キルログ、倒した敵を 3 秒表示、チャットに `やられた…` |

報告は 80% で正しい場所、20% で言わない（嘘の場所は言わない。混乱が大きいため）。

## 5. 敵 Bot 側の変更（この Step の一番大きい部分）

今の敵 Bot は「プレイヤーだけ」を相手にしている。相手を選べるようにする。

- `BP_PR_Bot` に `Team`（0 防衛、1 攻撃）を足す。プレイヤーは攻撃側として扱う
- `BP_PR_AIController` に `TargetActor` を足し、今プレイヤーを直接見ている処理（`CanSeeTarget`、狙い、撃つ判定、最後に見た位置）を `TargetActor` に対して行う
- 相手の選び方（`Think` ごと）：見えている敵対キャラクターのうち、①自分を撃ってきた相手、②一番近い相手、の順。交戦中の相手が見えている間は変えない（2 秒は固定）
- 聞く：味方 Bot の走る足音・銃声も、プレイヤーの音と同じに扱う（警戒、Director への報告）。**これがおとりの仕組み**になる
- Director：脅威度は、味方 Bot による出来事も同じ点数で加える。Bot からは、相手がプレイヤーか味方 Bot かを区別しない
- チャット（[23](23_bot_human.md) §6）：`KilledPlayer` はプレイヤーを倒したときだけ。味方 Bot を倒したときは `KilledAlly`（`1` `次` など短く）を足す
- 味方 Bot 自身は、同じ `BP_PR_AIController` に `bAlly` のモードを足して作る（State 7：ついて行く、State 8：命令の場所へ行って見張る）。Director には登録しない
- 設置後：敵は今までどおり全員で取り返す。スパイクの近くにいる味方 Bot とも撃ち合う

## 6. 作る順番

| 段階 | 内容 | 確認 |
|---|---|---|
| 1 | `Team` と `TargetActor` への置き換え（味方 Bot はまだ出さない） | 今までどおり敵がプレイヤーと撃ち合う。動きが変わらない |
| 2 | 味方 Bot を出す、ついて来る、見た目と名前 | 2 体がスポーンに出て、ついて来る。誤射が当たらない |
| 3 | 命令（Z / X）と印 | 命令した場所へ走り、着いて見張る |
| 4 | 敵が味方 Bot を見る・聞く・撃つ、Director への報告 | 味方を A へ走らせると、敵が A へ寄る（`[Director]` のログ） |
| 5 | 情報の表示とチャット | 味方が見つけた敵がミニマップに出る |
| 6 | スタート画面の選択、敵の数・称号・勝敗に数えないことの確認 | 「なし」で今までと同じ遊びになる |

## 7. 完了条件

- 味方 2 体を B へ行かせて A を攻めると、敵の寄りが B に向く
- 味方が倒されてもラウンドは続き、プレイヤーが倒されると負けになる
- 味方 Bot が敵を倒せることはあるが、まれ（10 ラウンドで 1〜2 回程度が目安）
- 「なし」を選ぶと、味方に関する表示・処理が一切出ない
- **手触りはユーザーが確認する**（強すぎて遊びが簡単にならないか、邪魔にならないか）

## 8. 実装結果（段階 1、2026-11-14）

- 段階 1：`Target` を **`TargetActor`** に改名（`rename_variable`。グラフの参照は追従）。置き換えた所（`Target` の読み書き 14 か所）：`CanSeeTarget`（線トレースの当たり先と位置）、`EngageSeen`、`Think`（セット）、`NewContact`（2 か所）、`DuelTick`、`DuelAim`、`FindCover`、`PickStyle`、`ContactInit`。もともと型は `Actor` で、プレイヤー専用の処理は `Think` の「プレイヤーを取得→キャスト→死亡判定→セット」だけだった
- 足したもの：`BP_PR_Bot.Team`（int、0 防衛、1 攻撃。Expose on Spawn、`Category=Ally`）、`BP_PR_AIController.LastAttacker`（Actor、まだ使っていない）、関数 `PickTarget() -> (Picked: Actor, bNone: bool)`。`Think` は `PickTarget` を呼び、`bNone` が true なら今までどおり `IdleThink`、false なら `TargetActor` にセットして `CanSeeTarget` へ進む。今の `PickTarget` の候補はプレイヤー 1 人（`bNone`＝プレイヤーが死亡）なので、結果は変更前と同じ
- `Think` の古い「プレイヤー取得とキャスト」のノードは、配線を外しただけで残っている（MCP にノード削除が無いため。lint の unreachable 警告 1 件）
- **残した所（仕様との差分）**：`CheckHearing`（聞く音の出どころ）は、まだ `GetPlayerCharacter` を直接読んでいる。味方 Bot の音を聞くのは段階 4 なので、そのとき `PickTarget` と同じ候補の形に直す。`PickTarget` の「自分を撃ってきた相手」「一番近い相手」の選び方（`LastAttacker`）も、候補が複数になる段階 2 の味方側の選択と段階 4 で入れる
- 確認（L_Canal の PIE、イージー）：Bot 3 体の `TargetActor` がプレイヤー、プレイヤーを Bot の前 8m へ置くと `[Bot] style=0 dist=7〜9` が出て、体力が 6 秒で 300→222 に減った（撃ってくる）。実行ログの `Blueprint Runtime Error` は 0 件。**ハードでの 10 回の接敵、見失い・捜索・取り返し・スモーク・`[Director]` の寄り**は、変更が `Think` の相手の取り方だけで、それらの関数に触れていないため再確認していない（未確認）

### 8.1 段階 2 への引き継ぎ（段階 2 は未着手。調査の結果）

- **味方を除く必要がある場所**（`Get All Actors Of Class` の検索結果。Bot／AIController を数えるもの）：GameMode `SpawnGroup`・`AliveBots`・`SayAlive`・`JudgeTitle`・`CleanupRound`（6 回の検索）、Director `CountAlive`・`Lottery`・`Poll`・`Heard`・`Predict`・`CountSite`・`IsHoldFree`・`Rebalance`・`SiteFix`、AIController `StartFlank`・`PartnerFar`・`FindPers`、HUD `CountEnemies`・`DrawReveal`・`DrawAnchors`・`DrawMinimap`（3 回）・`MapScan`・`DrawBlind`、`BP_PR_AlarmBot`、`BP_PR_SkillRecon`、`BP_PR_SkillFlash`（フラッシュは味方にも効かせる）。まだ 1 か所も変えていない
- `GetPlayerPawn` を直接読む所：Bot `DeathHook`（`bByPlayer` 判定）・Tick の足音（距離）、`TakeWeaponDamage`（`DamageInstigator`＝プレイヤーの判定）、武器 `Fire`、`BlindSelf`
- 先に守ること：①`OnPossess` が `NextSlot` を取るのは生成直後なので、味方の判定は `Bot.Team`（Expose on Spawn、済）で行い、味方は `ChatSlot=-1` のまま別変数に名前を持つ ②`Think` の先頭に `bAlly` の分岐を作り、`CheckHearing`・Hold・Search・Alert・Reinforce・Flank・`RetakeSkill`・覗きを通さない ③味方の強さは `ApplyDifficulty`／`ApplyMistake` の後に上書き ④`Die` の `DirReport` は `Team==0` のときだけ ⑤`SpawnDefenders` がラウンドごとに Bot を消すなら、その直後に味方を出す
- 編集の道具：`write_graph_from_code` は新しい関数の戻り値ノードを作れない（`add_function` で作った戻り値ノードを再利用できない）。関数は `add_function` で作り、`edit_graph` の batch（`create_node`、`connect_pins`。別の呼び出しでは別名が使えないので GUID で指定）で配線する。ノード削除の操作は無い

## 9. 実装結果（段階 2、2026-11-14）

### 9.1 作ったもの

- **味方の出し方**：`BP_PR_GameMode.SpawnAllies`（`StartRound` の `SetStartBots` と `SetBarriers` の間）。プレイヤーの位置（ラウンド開始時は PlayerStart 上）から後ろ `AllyBackSpawn`(250)、左右 `AllySideSpawn`(150)（1 体目が左、2 体目が右）を `K2_ProjectPointToNavigation` に通して +100 の高さで `BP_PR_Bot` を出す（`Team`=1、`AllyIdx`、`WeaponId`=Classic、`StartArmor`=0、`HoldPoint` なし）。ナビメッシュに乗らなければその 1 体は出さない。変数は GameMode の `AllyCount`(2。0 で出ない)、`AllyBackSpawn`、`AllySideSpawn`。`CleanupRound` は `BP_PR_Bot`（味方も含む）を全部消すので、次のラウンドで全員戻る。変更なし
- **敵と味方の分離（数から除く仕組み）**：`BP_PR_Bot` の子 **`BP_PR_EnemyBot`**（`AIControllerClass`=`BP_PR_EnemyAIController`）と、`BP_PR_AIController` の子 **`BP_PR_EnemyAIController`** を作った。`SpawnBot` は `BP_PR_EnemyBot` を出す。味方は素の `BP_PR_Bot`＋`BP_PR_AIController`。敵の数を数える `Get All Actors Of Class` の検索クラスを `BP_PR_EnemyBot` と `BP_PR_EnemyAIController` へ変えたので、味方は検索に出てこない
- **`BP_PR_Bot`**：`AllyIdx`（Expose on Spawn）、`AllyDmgMul`(0.3)。`TakeWeaponDamage` の先頭に「自分が味方 かつ 撃ったのがプレイヤー」なら何もしない分岐（統計・体力・フラッシュ以外の処理を全部飛ばす）、撃ったのが味方なら `Damage` に 0.3 を掛ける。`Die` の `DirReport` は自分が味方のときは飛ばす
- **`BP_PR_Character.TakeWeaponDamage`**：撃ったのが味方 Bot のときは、既存の「無効」分岐の条件に足して何も起きない
- **`BFL_PR.IsAllyActor(A) -> bool`**（pure）：`A` が `BP_PR_Bot` で `Team`==1 なら true
- **`BP_PR_AIController`**：変数 `bAlly`、`AllyName`、`AllyIdx`、`AllyKeep`、`AllyPick`、`AllyBest`、`AllyOrder`・`AllyOrderLoc`（段階 3 用、未使用）、Tuning の `AllyLoseSec`(1.5)、`AllyBackDist`(400)、`AllySideDist`(150)、`AllyMoveTol`(100)、`AllyWalkSpeed`(300)、`AllyRunSpeed`(675)、`AllyReact`(1.5)、`AllyAimErr`(20)、`AllyTau`(2.0)。関数 `AllyInit`、`AllyStats`、`AllyScan`、`AllyFollow`、`AllyThink`
  - `OnPossess`：`SetBot` の後に `AllyInit`（`bAlly`=`Bot.Team`==1。味方なら `AllyIdx` と `AllyName`=`GameMode.NameOf(10+AllyIdx)`）→ 味方なら `NextSlot` を使わず（`ChatSlot`=-1 のまま）`ApplyDifficulty` へ。`ApplyDifficulty` の後に `AllyStats`（`bAlly` のときだけ：`ReactionTime`、`AimError`、`AimTau` を Ally 変数から、`HeadChance`=0、`bStand`=true、`RetreatHP`=-1、`SnapChance`=0、`MistakeMul`=0）
  - `Think` の先頭：`bAlly` なら `AllyThink`、でなければ今までどおり
  - `AllyThink`：死亡なら何もしない。`Phase`==0（購入フェーズ）は `StopMovement` で待つ。`AllyScan` で見える敵（`EnemyBot` 以外の味方を除く `Team`==0 で生きている `BP_PR_Bot`）のうち一番近い相手を `TargetActor` にし、見えれば（状態が 1 でなければ `[Ally] engage` を出して）`EngageSeen` を呼ぶ（その場で止まって撃つ）。見えなくなって `AllyLoseSec` 秒たつと状態 7 に戻して `[Ally] lost`、ついて来る動き（`[Ally] follow`）
  - `AllyFollow`：プレイヤーの後ろ `AllyBackDist` 左右 `AllySideDist`（`AllyIdx`==0 が左）を目標にし、目標との距離が `AllyMoveTol` を超えたら `SimpleMoveToLocation`、以内なら止まる。プレイヤーの速度が 400 超なら `AllyRunSpeed`、以下なら `AllyWalkSpeed`。向きはプレイヤーの向きに合わせる
  - `NewContact`・`OnDamaged`：`bAlly` なら Director への `DirReport` を通らない（`OnDamaged` は丸ごと飛ばす）
- **HUD（見た目と名前）**：`BP_PR_HUD.DrawMinimap` の最後に、味方（`Team`==1 で生きている Bot）を水色の点（`MapDotActor`、常に表示）と、頭上（+110）に水色の名前（`AllyName`）を描く処理を足した。体の色は変えていない（名前の色が水色。マテリアルの色は Step 38）

### 9.2 数から除いた所の一覧（変えた／変える必要が無かった）

変えた（検索クラスを `BP_PR_EnemyBot` または `BP_PR_EnemyAIController` へ）：GameMode `AliveBots`・`SayAlive`・`JudgeTitle`（ACE の条件）／Director `CountAlive`・`Heard`（`BP_PR_EnemyBot`）、`Lottery`・`Poll`・`Predict`・`CountSite`・`IsHoldFree`・`SiteFix`（`BP_PR_EnemyAIController`）／AIController `PartnerFar`・`FindPers`（`BP_PR_EnemyAIController`）／HUD `CountEnemies`・`DrawReveal`・`DrawMinimap`（敵の点と `MapReveal`）・`MapScan`・`DrawBlind`／`BP_PR_AlarmBot`・`BP_PR_SkillRecon`。`StartBots`（`AliveBots` を使う）、勝敗の判定（`AliveBots` ＝敵の数）、`DeathHook` の Clutch 判定（`AliveBots`）、名前の席（味方は `NextSlot` を使わない）、Bot のスキルの回数（敵の `AliveBots` 側で数える）、プレイヤーのキル数・連続キルの音（味方はプレイヤーが倒せないので増えない）もこれで除かれる

変える必要が無かった：`CleanupRound`（味方も消すのが正しい）、`SkillFlash`（フラッシュは味方にも効く）、`SpawnGroup`・`Rebalance`・`StartFlank`（数えるのは `HoldPoint`／`FlankPoint`）、`DrawAnchors`、`BP_Spike.Explode`（爆発は味方にも当たる）、`BP_PR_Character` の `GetPlantSite` など（Bot を数えない）

### 9.3 確認（L_Canal、イージー。L_Pind でも PIE で起動して確認）

- 味方 2 体が出る（`BP_PR_Bot0`・`BP_PR_Bot1`、位置は x=スポーン後ろ272、y=±150）、`Team`=1、体力 100、フェーズ 1 で `[Ally] follow` が 2 体分出る。プレイヤーを 1200 前へ移すと味方が約 4〜5m 後ろまでついて来た（目標から 100 以内で止まる）。購入フェーズ中は `Phase`==0 で待つ
- 敵（`EnemyBot1`、約 11m 先）の見える所へ味方を置くと `[Ally] engage` が出て、敵の体力が 100 から 89.4 に減った（味方は撃っている。敵は味方を撃たないので味方の体力は 100 のまま）
- 誤射：プレイヤーを `DamageInstigator` にした `TakeWeaponDamage(50)` を味方に呼んで体力が 50 のまま、味方を `DamageInstigator` にした `TakeWeaponDamage(40)` をプレイヤーに呼んで体力 300 のまま。味方から敵への `TakeWeaponDamage(50)` は、アーマー 50 の敵が体力 100→94.9・アーマー 50→40.1（合計 15＝0.3 倍）
- 敵 3 体を倒すと `[Audio] kill n=3 ace=true` と称号が出てラウンドが終わった（味方が生きたまま、敵の数だけで判定）。次のラウンドで味方 2 体がまた出る
- 実行ログの `Blueprint Runtime Error` 0 件、`Accessed None` 0 件
- スクリーンショット：`docs/images/ally37_follow.png`（頭上の水色の名前）、`docs/images/ally37_minimap.png`（ミニマップの水色の点）

### 9.4 仕様との差分

- `PickTarget` に味方の分岐を入れず、`AllyScan`（`AllyThink` から呼ぶ）で相手を選ぶ。`PickTarget` の戻り値ノードを再利用できないため
- 敵と味方を子クラスで分け、数える所は検索クラスの付け替えにした（共通の関数・各ループの分岐は使っていない）。同じ効果で、ループごとの確認が要らない
- `DirReport` を `Team`==0 のときだけにするのは、`Die` の中だけ（`NewContact`・`OnDamaged` は `bAlly` で飛ばす）
- 味方が倒されたときのキルログは出していない（段階 5 の情報表示と一緒に作る）
- 体の色は変えず、名前の水色とミニマップの水色の点で区別
- 味方の名前は `MyName()` に反映していない（`AllyName` を HUD が直接読む）。段階 5 のチャットで `MyName` を直す
- 味方の足音は `BP_PR_Bot` の既存の Tick のまま（速度 150 超で、プレイヤーとの距離 15m 以内のとき鳴る）

### 9.5 未確認

- 実際にキーで歩いてついて来る手触り（プレイヤーの速度で歩きと走りの切り替え。400 を境にしている）
- 味方がプレイヤーの前に出ないこと（目標が常に後ろなので出ない設計だが、狭い通路での追い越しは未確認）
- 味方が倒されたあとのラウンドの続き（`Die` の `DirReport` 飛ばしだけ。実際に敵に倒させる確認はしていない）
- プレイヤーが倒されて負けること（味方に関する変更は無いが、味方が生きている状態では見ていない）
- ハードでの敵の接敵・寄り・取り返し・スモーク（敵の処理には触れていない。検索クラスの付け替えのみ）
- `AllyCount`=0 の PIE（変数は 2 のままで確認。0 のときは `SpawnAllies` のループが回らない）

### 9.6 次の担当（段階 3〜6）への引き継ぎ

- `AllyOrder`（0 ついて来る、1 命令）、`AllyOrderLoc` を `AllyThink` の「見えない」分岐（状態 7 の `AllyFollow` を呼ぶ所）の前に分岐して使う。`AllyFollow` は目標を `AllyOrderLoc` に変えるだけで流用できる
- 敵に味方を見せる（段階 4）：敵の `PickTarget` に味方の分岐を足す。味方は素の `BP_PR_Bot` なので `GetAllActorsOfClass(BP_PR_Bot)` で `Team`==1 を拾える。`Say` は `ChatSlot`>=0 のときだけなので味方は喋らない（段階 5 で `MyName` を `AllyName` にする）
- Director に味方の出来事を入れるときは、`NewContact`・`OnDamaged` の `bAlly` 分岐を外して `DirReport` を通す（`Die` は `IsAllyActor` の分岐）
- 敵の検索を `BP_PR_EnemyBot`／`BP_PR_EnemyAIController` へ分けたので、新しく敵の数を数える所は同じクラスを使うこと
- 編集の道具：`edit_graph` の batch は、トップレベルの `graphName` に関数名を渡し、関数の中身は `fromNodeId`／`toNodeId` に `$別名` か GUID を使う。`add_function` の `pure:true` を後から変えられないので、純粋にしたい関数は最初から `pure` で作る（impure で作ると exec ピンが残り、未接続だと呼び出しが無視される）。`delete_node`・`remove_function` は同意の nonce が要る

## 10. 実装結果（段階 0・3・4、2026-11-14）

### 10.1 段階 0（体の色と確認）
- 体の色：マテリアル `M_AllyBody`（`T_Swat_Body_BC`/`_N` × `Tint`）と `M_AllyHead`（`T_Swat_Head_BC`/`_N` × `Tint`）を作り、`AllyInit` の味方の分岐で `SwatMesh` の `Body_001`、`HeadGear_001` スロットを `SetMaterialByName` で差し替え（5.3 にオーバーレイ マテリアルは無い）。`Tint`=(1.5, 4, 9)。敵は変更なし。`docs/images/ally37_color.png`、`ally37_order.png`
- 確認：味方に `Die` → ラウンドは続く。プレイヤーに `TakeWeaponDamage(1000)` → ラウンドは負けて次のラウンドが始まる（味方は生きていた）。`Blueprint Runtime Error` 0 件
- **`AllyCount`=0**（段階 4 の後に確認）：味方は出ず、ログに `[Ally]` は出ない。敵がプレイヤーを見つけて `Spotted` を言い、プレイヤーの体力が 300→248 に減った。確認後 2 へ戻した

### 10.2 段階 3（命令）
- キー：**Z＝行け（`IA_AllyGo`）、X＝集まれ（`IA_AllyRegroup`）**。`DT_KeyBinds` は U（チート）、Y、C/E/Q など 21 行で Z・X は空いていた（チートは U。指示の「Z」は誤り）。行 `AllyGo`／`AllyRegroup` を足したので設定画面の一覧に出る（一覧の末尾までは目視していない）
- `BP_PR_Character` の EventGraph：2 つの `EnhancedInputAction`。Z は `GetPlayerCameraManager` の位置と向きから 6000cm の線トレース（Visibility）→ 当たったら `K2_ProjectPointToNavigation`（範囲 150,150,250）→ 成功したら `GameMode.AllyGo(Loc)`。X は `GameMode.AllyRegroup()`
- `BP_PR_GameMode`：`AllyGo(Loc)`（`BP_PR_AIController` を全部走査し、`bAlly` かつ生存の味方のうち、命令なしを優先して近い 1 体＝距離＋(命令中なら 1,000,000) が最小）→ その `AllyOrderGo(Loc)`、`AllyMarkLoc`／`AllyMarkUntil`（+2 秒）、`BotSay(10+AllyIdx, AllyAck)`。`AllyRegroup()`（味方全員の `AllyOrderRegroup`、`BotSay(10, AllyAck)`）。変数 `AllyBestScore`、`AllyBestCtrl`、`AllyMarkLoc`、`AllyMarkUntil`
- `BP_PR_AIController`：`AllyOrderGo`（`AllyOrder`=1、`AllyOrderLoc`、`AllyMode`=8、`AllyArrived`=false、ログ `[Ally] order go`）、`AllyOrderRegroup`（`AllyOrder`=0、`AllyMode`=7、`[Ally] order regroup`）。変数 `AllyMode`（既定 7）、`AllyArrived`。`AllyFollow` は目標を命令中なら `AllyOrderLoc` に切り替え（走る速度、命令の場所を向く）、着いて止まったとき一度だけ `[Ally] order arrive`。`AllyThink` の状態 7 を `AllyMode` に置換
- 印：`BP_PR_HUD.DrawAllyMark`（`DrawReveal` の最後から呼ぶ）。命令の場所の +100 の高さに水色の四角（20×20）を 2 秒。集まれには印なし
- チャット：`DT_BotChat` に `Chance_AllyAck`（100）、`AllyAck_a/b/c`（了解／行きます／えぇ…）。味方の名前で出る（`[ALL] kado_machi: 了解`、`docs/images/ally37_regroup.png`）
- 確認：`AllyGo` で 1 体が走り `[Ally] order go`→`order arrive`（位置 x=-2290、-262 など）。もう一度呼ぶと命令のない方が行った。`AllyRegroup` で戻り返事が出る。**敵が見えている間は命令より交戦が優先**（見える敵がいると動かない）。足音は既存の Bot の Tick の足音のまま

### 10.3 段階 4（敵が味方を見る・聞く・撃つ）
- `BP_PR_AIController`：`LastAttacker`（`OnDamaged` の先頭で `Source` をセット）、`PickBest`、`PickPrev`、`PickBestD`、関数 `ConsiderCand(Cand)`（`TargetActor` に入れて `CanSeeTarget`、見えれば距離−100000（撃ってきた相手）−200000（交戦中の相手）で最小を選ぶ）、`ChooseEnemyTarget`（プレイヤーと生きた味方 Bot を候補にし、誰も見えなければプレイヤー）。`PickTarget` は `ChooseEnemyTarget` を呼び `PickBest` を返す形に変更（`bNone`＝`PickBest` が無効）。交戦中の固定は 2 秒のタイマーではなく「見えている間は変えない」
- 聞く：`HearAlly`（`CheckHearing` の先頭から呼ぶ）。状態が 1・4 以外のとき、生きた味方の速度（XY）>400 かつ距離＜`HearRunNow`（鐘の間は 0＝聞こえない）、または武器の `LastFireTime` から 0.3 秒以内かつ距離＜`HearShotRange` なら、プレイヤーの音と同じに警戒（`InvestigateLocation`=味方の位置、状態 3）
- Director：`NewContact` は `TargetActor` の位置で報告するので味方が相手でも同じ点数で入る（味方自身の `NewContact`・`OnDamaged` は引き続き報告しない）
- `KilledAlly`：`BP_PR_Bot.Die` の味方の分岐で `GameMode.SayAlive(KilledAlly)`。`DT_BotChat` に `Chance_KilledAlly`（60）、`KilledAlly_a/b/c`（`1`／`次`／`やった`）。`KilledPlayer` はプレイヤー死亡時のみ（既存）。確認：`[ALL] kinoko_tarou: 1`（`docs/images/ally37_killed.png`）
- 確認：敵がプレイヤーと味方の両方を撃ち（プレイヤー 300→40、味方 100→48）、敵の `LastAttacker` が味方になった。味方が走っている間に鐘（`[Bridge] bell`）が鳴り、敵の寄りは出なかった

### 10.4 仕様との差分・未確認
- 「2 秒固定」は「見えている間は変えない」に置き換え。強さの値は変更なし
- **未確認**：ハードでの接敵・見失い・捜索・取り返し・スモーク・`[Director]` の寄り（`AllyCount`=0 の接敵と `Spotted` のみ確認）、「味方を A へ走らせると敵が A へ寄る」の `[Director]` ログ（敵の移動は確認したが `[Director]` の寄りのログは出ていない。聞いた警戒は Director を通らない作りで、仕様の確認欄との差）、鐘の外で走る足音への反応の目視、`Cast To BP_PR_Bot` の取りこぼしの網羅確認、キー入力（Z／X）の実機操作、設定画面の 2 行の目視
- 次の担当（段階 5・6）へ：味方の発見をミニマップへ出す（`MapReveal` と同じ方式）、`撃たれてる！`／`やられた…`／`{場所}に敵！` は `BotSay` に `Chance_` 行と `Event` 行を足せば出せる（`Slot`=10+`AllyIdx`）。スタート画面の選択は `AllyCount`（GameMode の既定 2）を GameInstance の保存値で上書きする。編集の道具：`edit_graph` の batch に `ForEachLoop`、`DynamicCast`（`targetClass`）、`EnhancedInputAction`（`inputActionAssetPath`）、`create_node` の `memberClass` に `KismetMathLibrary` などが使える。`write_graph_from_code` は使っていない

## 11. 実装結果（総点検と段階 5・6、2026-11-14）

### 11.1 総点検（段階 0）
- **a. キーの衝突**：重なる。保存済みの設定（`SG`）にチート＝Z がある状態で `FillMissing`（保存に無い行を既定キーで足す）が AllyGo＝Z を足し、Z が二重になる作りだった。直し：`FillMissing` で足す前に「今の割り当てに同じキーがあるか」を調べ、あれば新しい行を**未割り当て（None）**で足す（既存の割り当ては変えない）。確認：ユーザーの実際の保存データで読み込み後に Cheat＝Z、AllyGo＝None、AllyRegroup＝X。None の行は設定画面で選べば使える。後でチートのキーを変えても、保存済みの AllyGo は None のまま（自動では Z に戻らない。仕様）。保存データは書き換えていない（読み込みのみ）
- **b. キー一覧の 2 行**：一覧は `DT_KeyBinds` の全行から作る（行数 23）ので 2 行が出る。スクロールした画面の目視は未確認（docs/images/ally37_keys.png は一覧の上半分）。表示名は「味方に命令：行け／集まれ」
- **c. 子クラス分けの取りこぼし表**（`BP_PR_Bot`／`BP_PR_AIController` を対象にした検索・Cast を全アセットで検索して判定）

| 場所 | 判定 | 内容 |
|---|---|---|
| Director `CountAlive`・`Heard`・`Lottery`・`Poll`・`Predict` ほか | 問題なし | 検索クラスは `BP_PR_EnemyBot`／`BP_PR_EnemyAIController`（味方は入らない） |
| GameMode `AliveBots`・`SayAlive`・`JudgeTitle`・勝敗・リザルト | 問題なし | 敵だけを数える。味方は数えない |
| GameMode `CleanupRound` | 問題なし | 味方も消すのが正しい |
| HUD `CountEnemies`・`DrawReveal`・`MapScan`・`DrawBlind`・敵の点 | 問題なし | 敵クラスで検索 |
| `BP_PR_Bot.TakeWeaponDamage`（プレイヤー→味方、味方→敵） | 問題なし | プレイヤー→味方は何もしない。味方→敵は 0.3 倍。`AddHit`／`AddKill`／クレジットはプレイヤーが撃ったときだけ |
| **`BP_PR_Bot.DealtHook`（与ダメージの記録）** | **取りこぼし→直した** | 撃ったのが誰でも `LogDealt` を出していた（味方が敵に与えた分、敵が味方に与えた分が「与えたダメージ」に混ざる）。`TakeWeaponDamage` で、撃ったのがプレイヤーのときだけ `DealtHook` を呼ぶ分岐を足した |
| `BP_PR_Character.LogTakenHook`（やられた理由）・`KilledHook`・`DeathInfoHook` | 問題なし | 味方からプレイヤーへのダメージは無効なので、味方の記録は出ない |
| `BP_PR_Bot.DeathHook` | 問題なし（差分あり） | プレイヤーが倒したときだけキルログとチャット。**味方が敵を倒した行はキルログに出ない**（11.4） |
| プレイヤーの武器の当たり判定・ヘッドショット | 問題なし | `BPI_Damageable.TakeWeaponDamage` を当たった相手に呼ぶだけ。味方に当たってもダメージなし（ヒットマーカーが出るかは未確認） |
| 連続キル・称号（`AddKill`、`JudgeTitle`） | 問題なし | プレイヤーが倒したときだけ増える。`JudgeTitle` は敵クラス |
| リコン・フラッシュ・アラームボット | 問題なし | リコンは敵クラス。フラッシュは味方にも効く（仕様）。アラームボットは敵クラスで検索 |
| 跳ね橋・鐘（`BP_Drawbridge`） | 未確認 | `BP_PR_Bot` を参照する Cast／検索が無い（オーバーラップ系）。味方が橋に乗ったときの動きは目視していない |
| Bot のスキル（敵が出すフラッシュ・スモーク） | 問題なし | 回数は `AliveBots`（敵）。味方に向けるかは仕様に無い（味方も巻き込む） |
| ABP（`ABP_PR_Swat`）の Cast | 問題なし | 見た目のためで味方・敵とも同じ |

- **d. ハードでの再確認**（セーブの難易度 2。確認後 0 に戻した）：`AllyCount`=2：接敵（`[Bot] style=`）、寄り（`reinforce`／`[Director] whiff`／`rebalance`）、のぞき、チャット（`[Chat] skip-*`）が動き、実行時エラー 0 件。`AllyCount`=0（スタート画面で「なし」を選んだ状態）：`[Ally]` ログ 0、敵が接敵してプレイヤーの体力が減る、エラー 0。**未確認**：見失い→捜索、`PlantSpike` での取り返しとスモーク（スパイクを設置する場面を作っていない）
- **e. おとり**：プレイヤーの音の経路を調べた。**足音**：`Director.Poll` が、プレイヤーの速さ≧500 で敵（`Heard` 範囲 1500）が近くにいれば `Report(位置, 15, 4)`。**銃声**：`WeaponBase.Fire` が `BFL_PR.DirShot`→`Director.ReportShot`（範囲 4000 に敵がいれば `Report(位置, 30, 3)`）。**聞いた敵**：`CheckHearing`（プレイヤー）／`HearAlly`（味方）が、同じ条件で警戒（状態 3、探す位置）に入る。差：**銃声はプレイヤーも味方も（Bot も）同じ経路**だが、**足音は `Poll` がプレイヤーだけを見ていた**ので、味方が走っても Director に報告されなかった。直し：`Director.PollAllies`（`Poll` の足音の判定の前に呼ぶ。速さ≧500 の生きた味方ごとに、同じ `Heard`(1500)→`Report`(15, 4)）。味方の発見・発砲は `NewContact`／`OnDamaged` が相手の位置で報告するので、元から同じ経路。確認（ハード）：`AllyGo` で味方 1 体を敵側へ走らせると `[Director] foot report who=ally` が出て `[Predict] site=B`（Director が B と予測）、敵の `style=` の接敵が出た。プレイヤーが同じ場所を走った場合との比較は、プレイヤーを走らせられないため、条件がコード上で一致していること（速さ≧500、範囲 1500、`Report`(15,4)、同じ `Heard`）で確認
- **f.** `BP_PR_GameInstance.bSkipTitle`=false、`BP_PR_GameMode.AllyCount`=2 を確認してコミット

### 11.2 段階 5（情報の表示とチャット）
- 味方が敵を見つけた：`AIController.AllySpot`（`AllyThink` の `[Ally] engage` の直後に呼ぶ）。80%（`AllySpotChance`）で、敵の `RevealUntil`=今+`AllySpotReveal`(2 秒)（リコンと同じ。ミニマップの赤い点と画面の印）、`AreaInfoAt` で場所が分かればチャット `AllySpot`（`{場所}に敵！`／`{場所}いる！`）。20%は何もしない（嘘の場所は言わない）
- 味方が撃たれた：`Bot.AllyHitHook(Src)`（`TakeWeaponDamage` の体力が減った直後。`HitByActor` を記録し、味方で体力が残っていればチャット `AllyHit`＝`撃たれてる！`／`いたっ`）。倒される一撃のときは `AllyHit` を言わず `AllyDown` を優先
- 味方が倒された：`Bot.AllyDownHook`（`Die` の味方の分岐）。チャット `AllyDown`（`やられた…`／`ごめん…`）、キルログ（倒した敵の名前 → 味方の名前。`bPlayerInvolved`=false）、倒した敵を `AllyDownReveal`(3 秒) 表示。倒した相手が敵 Bot でないとき（スパイク等）はチャットだけ。`AllyDown` を敵の `KilledAlly` より先に言う（間隔の制限で消されないため）
- `AIController.MyName` を、味方なら `NameOf(10+AllyIdx)` にした（`AllyName` と同じ名前でチャットとキルログに出る）
- `DT_BotChat` に `Chance_AllySpot`(100)、`Chance_AllyHit`(70)、`Chance_AllyDown`(100) と行 `AllySpot_a/b`、`AllyHit_a/b`、`AllyDown_a/b`。間隔の制限（`ChatGap`／`SameGap`）と「チャットを表示」の切り替えは `BotSay`／`PushChat` の既存のまま
- 足した変数：AIController `AllySpotChance`(80)、`AllySpotReveal`(2)、Bot `HitByActor`、`AllyDownReveal`(3)。足した関数：AIController `AllySpot`、Bot `AllyHitHook`、`AllyDownHook`、Director `PollAllies`
- 確認（ハード、L_Canal）：味方 1 体を倒すと、キルログの行（`ramen_daisuki [Spectre] xX_Kage_Xx`）、倒した敵が 53m の位置に赤い印とミニマップの赤い点（3 秒）、味方の名前のチャット（`[ALL] xX_Kage_Xx: 撃たれてる！`。docs/images/ally37_down.png）。`[Chat] skip-gap AllySpot／AllyHit／AllyDown` のログで、3 つの出来事とも `BotSay` まで届いている。敵を見つけた味方が `[Ally] engage` で `AllySpot` に入ることも確認。**未確認**：`{場所}に敵！` が画面に出た様子（ChatGap で消えた。間隔の制限が強く、敵のチャットと重なると味方の発言が出にくい。試遊で見て、必要なら味方の発言を優先する）

### 11.3 段階 6（スタート画面の選択）
- `WBP_Title`：「味方 Bot」の行（`AllyRow`、`AllyOn`、`AllyOff`、`AllyValue`）を「Bot の強さ」の行を複製して足した。`OnAllyOn`／`OnAllyOff`／`RefreshAlly`（Construct で呼ぶ）。`GameInstance`：`bAllyOn`（初期 true）、`SetAllyOn`（保存）、`SaveSens`／`LoadSens` に追加。`SG_PR_Settings.bAllyOn`（古い保存には無いので初期値 true）。`GameMode.SpawnAllies` は `bAllyOn` なら `AllyCount`、でなければ 0 体
- 「なし」：`SetAllyOn(false)` を保存して再起動した PIE で、味方が出ない（`[Ally]` ログ 0）、味方の名前・点・印が画面に出ない（docs/images/ally37_off.png）、`AllyGo` を呼んでも何も起きない（エラー 0）。敵の遊びは変わらない（敵が接敵して体力が減る）
- 数えない：敵の数の表示・称号・勝敗・リザルトは、検索クラスが敵だけ（11.1 の表）。段階 2 の確認（敵 3 体で `ace`、味方が生きたまま勝つ）と、味方を倒してもラウンドが続くことを確認済み。通しで 1 ラウンド勝つ確認は今回やり直していない
- スクリーンショット：docs/images/ally37_title_1920x1080.png、ally37_title_990x1310.png（`preview_widget`）、ally37_title_pie.png（PIE の実画面。初期は「あり」、難易度の表示はその時のセーブ）。選択が他と重ならず、はみ出さない

### 11.4 仕様との差分・未確認
- 敵の数 3／5 の選択は WBP_Title に無かったので、「Bot の強さ」の行を作りの手本にした
- 味方が敵を倒したときのキルログは出さない（`DeathHook` はプレイヤーが倒したときだけ）
- 未確認：L_Pind での PIE、跳ね橋に乗った味方、ヒットマーカー、ハードの捜索・取り返し・スモーク、`{場所}に敵！` の表示、キー入力（Z／X）の実機操作、設定画面のスクロール後の目視、手触り
- 一時的に変えて戻したもの：`bSkipTitle`（true→false）、セーブの難易度（2→0）、セーブの `bAllyOn`（false→true）。キー設定・感度・音量・`bShowChat` は変えていない

## 12. 実装結果（仕上げ、2026-11-14、ブランチ `step37b/ally-finish`）

### 12.1 直した内容
- **味方の発言が敵のチャットに消されない**：`BP_PR_GameMode` に `LastAllyChatT`（Chat、初期 -100）と `AllyChatGap`（Tuning、1.5 秒）を足した。`BotSay` は `Slot` が 10 以上（味方）のとき、全体の間隔の判定に `LastAllyChatT`／`AllyChatGap` を使い、発言したら `LastAllyChatT` を更新する（`LastChatT` は触らない）。敵の判定は今までどおり（味方の発言は敵を止めない）。同じ席が続けて話さない制限（`SameGap`）と `Chance_` の確率はそのまま。確認（L_Canal、敵の `ChatGap` を 30 秒にして）：敵の `BotSay` の 0.3 秒後に味方の `AllySpot` が出て、`[ALL] 1tap_or_die: 橋への道いる！`（場所の名前入り。docs/images/ally37_spot.png）。別の確認では `船着き場に敵！`。敵の `LastChatT` は動かず、`LastAllyChatT` だけが更新された。**注意**：同じ味方（同じ席）は `SameGap` 6 秒に当たるので、味方 A が `撃たれてる！` を言った直後の `AllySpot` は同じ席なら出ない（仕様）
- **味方が敵を倒したときのキルログ**：`BP_PR_Bot.AllyKillHook(Src, bHead)` を足し、`TakeWeaponDamage` の「体力 0 以下 → `DeathHook`」の直後に呼ぶ。`Src` が味方で自分が味方でないとき、`PushKill(味方の名前, 敵の名前, 武器 ID, bHead, false)`。武器 ID は `GetWId`（`WeaponId` を返す関数）で味方 Bot から読む。プレイヤー用の `AddKill`・連続キル・`RoundKills`・チャットには触れない。確認：味方を `DamageInstigator` にした致死量の `TakeWeaponDamage` で、キルログに `NoHeal4U  [Classic]  onigiri_rush`（先頭の `> ` なし）、`RoundKills` は 0 のまま、`[Audio] kill` のログ件数は変化なし
- **ついて来る目標が路地の壁の中に入ると動けなくなる不具合（確認中に見つけて直した）**：`AllyFollow` の目標（プレイヤーの後ろ 400cm、左右 150cm）が、路地の外（壁の中）に出ると、`SimpleMoveToLocation` が失敗して味方が立ち止まったまま（A の路地 1〜2 で 1 体が約 15m 後ろで止まった）。目標を `K2_ProjectPointToNavigation`（範囲 300,300,300）でナビメッシュへ寄せ、寄せられなければ（ついて来る間は）プレイヤーの位置、命令中は元の場所に向かう。直した後は 2 体とも約 3〜4.5m 後ろまでついて来た

### 12.2 未確認の確認の結果
- **L_Pind の PIE**：味方あり：味方 2 体と敵 3 体が出てラウンドが進み、`[Ally] follow`。味方なし：敵 3 体のみで `[Ally]` ログなし。どちらも `Blueprint Runtime Error` 0 件。確認後は L_Canal を開き直した
- **取り返し**（ハード、味方あり、`PlantSpike` を A サイトに呼ぶ）：スモーク（`[Bot] skill=smoke spawn`）が出て、敵が取り返しに来て、スパイクの約 4m の所に置いた味方と撃ち合い（`[Ally] engage`、敵の `style=`）、スパイクが片付いてスコアに 1 が入った（解除まで進んだ）。敵が味方に気を取られて解除に来ない、ということは起きなかった。ただし味方の与ダメージの量や、どちらが先に撃ったかまでは見ていない
- **見失い → 捜索**（ハード、味方なし）：プレイヤーを敵（`EnemyBot1`）の 5.6m 先に置いて `style=0`（接敵）を出させ、すぐ遠くへ移すと、約 4 秒後に `[Bot] peek=1`（捜索の覗き方）が出た
- **跳ね橋**：味方（`BP_PR_Bot`）を橋の上（X=450、Z=135）に置いて `StartRaise` を呼ぶと、味方が岸へ退避した（橋から出て西へ歩いて行った）。運河には落ちない。**注意**：置いた直後（同じフレーム）に `StartRaise` を呼ぶと退避の判定（`GetOverlappingActors`）に入らなかった。置いてから少し間を置くと入る（確認の手順の問題。実際のゲームでは歩いて乗るので問題ない）。橋が上がっている間（`UpTime` を 45 に延ばして）、南岸の味方に対岸（900,0）への `AllyGo` を呼ぶと、石橋のほうへ回り、石橋の手前（-64, 2453）で止まって動かなくなった（橋は下りた後も止まったまま。固まって動けなくなるのではなく、`AllyOrder` の目標に着いた扱いかどうかは `[Ally] order arrive` のログで確かめていない）。運河には落ちていない（z=90）
- **ついて来る動き**：路地 1〜2 で、プレイヤーを `playtest` で歩かせて（約 650cm/s）、味方 2 体がプレイヤーの後ろ（X が小さい側）に約 4.4〜4.6m の所までついて来た（前に出ない、重ならない）。段差（A の 2 階のスロープ、B の高台）は、B の高台まで歩かせたが敵が近くにいて味方が交戦（`engage`）で止まったため、ついて来る動きの確認にならなかった（未確認）
- **設定画面のキー一覧の末尾**：PIE で `OpenMenu` を呼んで撮ったが（docs/images/ally37_keys_end.png）、キー一覧が枠の中でスクロールする作りで、スクロール位置を末尾へ動かす手段がなく、末尾の 2 行は目視できなかった。画面に見える範囲は変わらず（前進〜武器を拾う）。未確認のまま

### 12.3 一時的に変えて戻したもの
- `BP_PR_GameInstance.bSkipTitle`（false→true→false。再保存したので `.uasset` に差分が出るが値は元どおり）
- 保存データ：PIE の中で `SetAllyOn`（false→true）、`SetDifficulty`（2→0）を呼んだが、確認後の `Saved/SaveGames` の 4 ファイルは最初に控えたものとバイト単位で同じ。キー設定・感度・音量・`bShowChat` は触っていない
- PIE の中だけ：`ChatMul`・`ChatGap`、`AllySpotChance`、`UpTime`（アセットの値は変えていない）

### 12.4 残った未確認・試遊で見てほしい点
- 設定画面のキー一覧を末尾までスクロールして「味方に命令：行け／集まれ」の 2 行を見る
- 階段・スロープ・高台でついて来る動き。橋が上がっている間の `AllyGo`
- 味方の発言の頻度（味方は 1.5 秒間隔なので、敵の発言と同時に 2 行並ぶことがある）
