# 18. スキル・ミニマップ・将来対応の一部

Step 21（スキル）、Step 22（ミニマップ）、Step 23（将来対応のうち対応する項目）の仕様と実装計画。2026-11-11 作成。

- Step 24 の手直し（[19](19_skill_tuning.md)）は、この文書より優先する。
- 値に（仮）と付けたものは、遊んでから調整する。
- 相当するスキルは VALORANT の仕様を参考にしたが、数値はこのゲームに合わせて決めた。既存ゲームのアイコンや見た目は再現しない（表示は文字と独自の図形）。

## 1. このスレッドの範囲

| Step | 内容 | ブランチ |
|---|---|---|
| 21 | スキル（7 種類、選択、購入、HUD、Bot への効果） | `step21/skills` |
| 22 | ミニマップ | `step22/minimap` |
| 23 | 将来対応のうち対応するもの（設置の中断、死亡時の武器ドロップ、配置の適応、予測移動、`BP_FlankPoint`） | `step23/future-items` |

順番は 21 → 22 → 23。Step ごとに main へマージする（このリポジトリの流儀どおり、ローカルで `Merge stepN/...` のマージコミット）。
Unreal Editor は 1 つなので、Sonnet のサブエージェントは同時に 1 体だけ動かし、区切りごとに Opus がグラフ・ログ・スクリーンショットで確認する。

**Git の注意**：Unreal Editor が開いている間は、開いているアセット（`L_Pind.umap` など）を git が書き換えられない（`unable to unlink`）。`git switch`・`git stash`・ブランチ間でアセットが違うマージは、エディタを閉じてから行う。エディタを閉じられないときは、`git worktree add` で別フォルダに main を出し、そこでマージする。作業ブランチ上のコミットと push はエディタを開いたままでよい。

### 決定事項（2026-11-11 ユーザー確認）
- スキルはセット1（C）・セット2（E）・セット3（Q）から 1 個ずつ選び、計 3 個を持つ
- 選ぶのはスタート画面（試合中は固定）
- 使用回数は購入画面でクレジットで買う
- スモークは Bot の視界も遮る
- 発動ボタンは左クリック（VALORANT と同じ）。武器を拾うは F へ移す
- 未コミットだった `L_Pind.umap` は手元の版を正としてコミットする
- 敵の人数は見せない方針（[10](10_defense_director.md) §8 の未決事項を閉じる）

## 2. キー割り当て

| 操作 | 新しい初期キー | 変更前 | 置き場所 |
|---|---|---|---|
| スキル1（セット1） | C | — | `DT_KeyBinds`（新規 `IA_Skill1`） |
| スキル2（セット2） | E | — | `DT_KeyBinds`（新規 `IA_Skill2`） |
| スキル3（セット3） | Q | — | `DT_KeyBinds`（新規 `IA_Skill3`） |
| 発動（構えたスキルを使う） | 左クリック | — | 新しいキーは作らず、`IA_Fire` を構え中だけスキルに回す |
| 武器を拾う | F | E | `DT_KeyBinds`（`IA_Interact`） |
| ナイフを眺める | Y | C（`IMC_PR` に固定） | `IMC_PR` から外し、`DT_KeyBinds` に移す |
| テスト用の武器切替 | T | Q | `DT_KeyBinds`（`IA_DebugWeapon`） |

- キー設定の保存スロットを `PR_Settings` → `PR_Settings2` に変える。今までの保存データは読まれず、全員が一度初期値に戻る（`FillMissing` には重複キーの解消が無く、古い保存データの E と新しいスキル2の E が二重になるため）。感度（`PR_Sens`）はそのまま
- `WBP_Title` の操作説明（`Help`、直書き）、README の操作説明、[03](03_combat.md) のキーの表を直す

## 3. スキル共通の仕組み

### 3.1 データの置き場所
キャラクターは死亡でキャラごと作り直される（`ResetPlayer`）ため、キャラには持たせない。

| データ | 置き場所 | 内容 |
|---|---|---|
| 選んだスキル | `BP_PR_GameInstance.SkillSel`（int 配列 3） | セット1：0 ブリンク／1 フラッシュ／2 リコン。セット2：0 リコール／1 ヒール。セット3：0 スモーク／1 アラームボット。既定は全部 0。セーブスロット `PR_Skills` に保存し、次回の初期値にする |
| 残り回数 | `BP_PR_GameMode.SkillCharges`（int 配列 3） | 試合開始時に 0。購入で増え、使うと減る。**ラウンドをまたいでも、死亡しても残る**（VALORANT と同じ） |
| 設置物 | 各アクター（下）。`GameMode.CleanupRound` でまとめて消す | リコールの目印、スモークのアンカーと煙、アラームボット |

関数に BP クラス型の引数を付けない（[07](07_tech_design.md) の注意）。参照は変数で渡す。

### 3.2 スキルの一覧と値

| セット | スキル | 相当 | 最大 | 価格（仮） | 使い方 |
|---|---|---|---|---|---|
| 1（C） | ブリンク | ジェットのテイルウインド | 1 | 150 | C で即発動 |
| 1（C） | フラッシュ | KAY/O のフラッシュ | 2 | 250 | C で即投げ |
| 1（C） | リコン | フェイドのホウント | 1 | 250 | C で構え、左クリックで投げる |
| 2（E） | リコール | ウェイレイのリフラクト | 1 | 200 | E で目印を置き、もう一度 E で戻る |
| 2（E） | ヒール | セージのヒール | 1 | 250 | E で即発動 |
| 3（Q） | スモーク | サイファーのケージ | 2 | 100 | Q で構え、左クリックでアンカーを投げる／狙ったアンカーを発動 |
| 3（Q） | アラームボット | キルジョイのアラームボット | 1 | 200 | Q で足元の前に置く |

- パロラント（難易度 4、武器購入不可）でもスキルは買える（仮）
- 使えるのはフェーズ 0（購入）・1（戦闘）・2（設置後）。購入フェーズは攻撃スポーンの障壁の内側なので、使えても意味は薄い。ヒールだけは戦闘中（1・2）のみ

### 3.3 構え（左クリックで発動するスキル）
- `BP_PR_Character.SkillMode`（int）：0 なし、1 リコン構え、3 スモーク構え
- 構え中は `IA_Fire` の Started を武器の `StartFire` ではなくスキルの発動に回す（`BP_PR_Character` の `IA_Fire` のイベントで分岐。`TryFire` は Bot と共通なので触らない）
- 同じスキルのキーをもう一度押す、1/2/3 で持ち替える、死亡する、で構えを解く
- 構え中は画面下中央に「左クリック：投げる」などの案内を出す

### 3.4 設置の中断
スキルを使う（構えを含む）と設置を中断する。詳細は §6.1。

### 3.5 購入画面
- `WBP_BuyMenu` に「スキル」の見出しと、選んだ 3 つのボタンを足す。表示は「C ブリンク　150　0/1」
- 最大まで持っていれば買えない（灰色）。クレジットが足りなければ買えない
- 購入処理は `GameMode` に `TryBuySkill(Slot)` を足す（武器の `TryBuy` / `ItemState` とは分ける）

### 3.6 HUD
- `WBP_GameHUD` の下中央（アンカー (0.5, 1)、位置 (0, -40)）に `SkillBar` を足す。3 枠で「C ブリンク ●」「E ヒール ○」のようにキー、名前、残り回数（● 残り、○ 空き）を出す
- 構え中の枠は黄色
- 通知（アラームボットの検知）用に `NoticeText` を足す（`GuideText` の下、位置 (0, 150)、2.5 秒表示、橙色）

### 3.7 スタート画面での選択
- `WBP_MapIntro` に選択欄を足す。セットごとに 1 行、ボタンを横に並べる（選択中は赤枠）。各ボタンの下に効果の 1 行説明
- 初期値は前回の選択（`PR_Skills`）
- 表示中はマウスカーソルを出し、入力を UI のみにする。「準備完了」ボタンか 20 秒経過で決定し、今の流れ（0.8 秒でプレイヤー視点へ）に戻る。入力をゲームに戻し、カーソルを消す
- 今の「`Delay 5` で自動で進む」を、「準備完了か 20 秒」に置き換える
- `bSkipTitle` の起動や「もう一度」でスタート画面を通らない場合は、前回の選択のまま始める

## 4. スキルの詳細

### 4.1 ブリンク（セット1）
- C を押すと、押している WASD の方向へ素早く移動する。何も押していなければ前方
- 距離 700cm（仮）を 0.15 秒で移動する。毎フレーム `AddActorWorldOffset`（Sweep あり）で進め、壁に当たったらそこで止まる。上下方向は動かさない（空中でも使える）
- 発動の時間制限なし（押した瞬間に移動）
- 使用中も撃てる

### 4.2 フラッシュ（セット1）
- C で前方へ放物線で投げる（初速 1800、重力あり、壁で跳ね返る）。投げてから 1.0 秒で炸裂（仮）
- 炸裂時に光（PointLight の強い発光を 0.2 秒）と音（既存の効果音を流用）
- **Bot への効果**：炸裂時、生きている各 Bot について次をすべて満たせば、5 秒間目が見えない（`BP_PR_AIController.BlindUntil` = 今 + 5）
  - 距離 5000cm 未満
  - Bot の前方とフラッシュの方向の内積 > 0.5（約 ±60°）。交戦中（State 1）の Bot も同じく判定する（`CanSeeTarget` の視野の判定は交戦中に省かれるため、ここで別に判定する）
  - Bot の目からフラッシュへのトレース（Visibility）が遮られない。スモークにも遮られない
- プレイヤー自身には効かない（仮。VALORANT では自分も眩しくなるが、指示が「敵の視界」なので入れない）

### 4.3 リコン（セット1）
- C で構え、左クリックで前方へ投げる（初速 2000、重力あり、当たったところで止まる）
- 止まってから 0.5 秒後に、半径 2500cm（仮）以内の生きている Bot 全員を 4 秒間（仮）表示する（`BP_PR_Bot.RevealUntil`）。壁越しでも表示
- 表示：画面上に Bot の位置の赤い菱形と距離（`BP_PR_HUD` で `Project` して描く）。Step 22 以降はミニマップにも赤い点
- Bot は表示されたことに反応しない

### 4.4 リコール（セット2）
- 1 回目の E：足元に目印（`BP_PR_RecallBeacon`、小さな光る円柱）を置く。ここで 1 回分を使う
- 2 回目の E：0.4 秒後（この間は無防備）に目印の位置へ移動（`SetActorLocation`、Teleport）。向きは変えない。目印は消える
- 目印はラウンド終了か死亡で消える。消えた時点で、戻る権利もなくなる

### 4.5 ヒール（セット2）
- E で体力を最大（`GameMode.PlayerMaxHealth`）まで即回復。アーマーは回復しない
- 体力が最大のとき、または戦闘中（フェーズ 1・2）以外は使えない（回数を減らさない）
- 体力の上限を超えないよう、代入時に `PlayerMaxHealth` で切る

### 4.6 スモーク（セット3）
- Q で構える。構え中の左クリックは次のどちらか
  - 画面中央から 6° 以内に、まだ発動していない自分のアンカーがあれば、それを発動する（距離・壁越しは問わない）
  - なければ、残り回数があればアンカー（`BP_PR_SmokeAnchor`）を投げる（初速 1500、重力あり、当たったところで止まる）。残り回数を 1 減らす
- 発動すると、アンカーの位置に半径 450cm（仮）の煙（`BP_PR_SmokeField`、半透明の灰色の球、両面表示）を 15 秒出す
- 構え中は、未発動のアンカーの位置に画面上の印を出す
- **Bot への効果**：Bot の目とプレイヤーを結ぶ線分が、発動中の煙の球を通るなら見えない。線分と球の判定は `BFL_PR.IsSmokeBlocked(Start, End)` で行い、`CanSeeTarget` から呼ぶ。煙は殻だけで中は空洞：Start と End がどちらも同じ煙の球の内側にあるなら、その煙では遮らない（同じ煙の中の Bot とプレイヤーは互いに見える）。片方だけ内側（中から外・外から中）、またはどちらも外側で線分が球を通る場合は見えない（docs/19 §2.11）。弾は煙を通り抜ける（射撃のトレースは変えない）
- 煙の一覧は `GameMode.ActiveSmokes`（配列）で持つ

### 4.7 アラームボット（セット3）
- Q で、足元の前 150cm の床（下向きトレース）に `BP_PR_AlarmBot`（小さな箱と点滅する光）を置く
- 半径 700cm（仮）以内に、見通しのある（Visibility のトレースが通り、煙に遮られない）生きている Bot が入ると通知する
  - `NoticeText` に「アラームボットが敵を検知」
  - その Bot を 2 秒間表示（リコンと同じ `RevealUntil`）
  - 同じ Bot には 10 秒に 1 回まで
- ラウンド終了まで残る。Bot は壊さない（攻撃もしない）

## 5. Bot の視界と射撃の変更（Step 21 で入れる）

調査で分かったこと：撃つ判断は毎フレームの `DuelTick` → `DuelLegs` → `BurstTick` / `StrafeTick` → `WFire` で行われ、ここに視線の判定は無い。`CanSeeTarget` が false になっても、`EngageLost` が State を 2 に落とすまでの最大 3 秒（`LoseTime`）は撃ち続ける。

変更：
- `CanSeeTarget` の先頭で、`Now < BlindUntil` なら false。視線のトレースが通った後に `IsSmokeBlocked` なら false
- `BurstTick` と `StrafeTick` の `WFire` の手前に、撃ってよいかの条件 `CanShoot` を足す：`Now >= BlindUntil` かつ `(Now - VisibleTime) < LostFireTime`。`LostFireTime` = 0.5 秒（仮。煙に隠れた直後に数発撃ち込むのは自然なので 0 にはしない）
- 目が見えない間は `DuelAim` も止める（`DuelTick` で分岐）
- この変更で、今ある「見失ってから最大 3 秒、壁越しに撃ち続ける」挙動も 0.5 秒に縮まる。撃ち合いの手応えが変わるので、PIE で確認する

## 6. 将来対応のうち対応する項目（Step 23）

### 6.1 射撃による設置の中断
- `BP_PR_Character` の `IA_Fire` の Started（構え中でない、つまり普通に撃つとき）とスキルの使用で、`PlantProgress > 0` なら 0 に戻し、`bPlantNeedRelease` を true にする
- `PlantTick` は `bPlantNeedRelease` の間は何もしない。`IA_Plant` の Completed（4 キーを離した）で false に戻す。`IA_Plant` の Triggered は毎フレーム来るため、離すまで再開させないのがこの仕組みの目的
- 撃つ動作自体はそのまま行う

### 6.2 プレイヤー死亡時の武器ドロップ
- `BP_PR_Character` の死亡検知（Tick の `Health<=0 && !bDead`）で、`PrimaryWeapon` があれば `Drop`、無ければ `SecondaryWeapon` を `Drop`（VALORANT と同じく一番良い武器を 1 つ）。落とした方の参照（と `PrimaryId` / `SecondaryId`）を空にしてから、既存の処理へ進む（`ResetPlayer` が参照先を Destroy するため）
- 落ちた武器は次のラウンド開始時の `CleanupRound` で消える（持ち主が Character でない武器を消す処理）。Bot は拾わないので、効果は「死んだ場所に武器が落ちて見える」まで

### 6.3 前ラウンドの攻め先による配置の重み（[10](10_defense_director.md) §6）
- ラウンド終了時に「攻めたサイト」を決めて `GameMode.LastAttackSite`（0 なし／1 A／2 B）と `AttackStreak`（同じサイトが続いた回数）に入れる
  - 設置したラウンド：設置したサイト
  - 未設置：そのラウンドの A と B の脅威度の累計（Director に `RoundThreatA` / `RoundThreatB` を足し、報告のたびに加点）の大きい方。両方 0 ならなし
- `PickSetup` の抽選で、そのサイトを厚くする行の重みを上げる。今の抽選は「行名を `Weight` 回プールに入れる」方式なので、全行を `Weight×2` 回入れ、該当行は `Weight×3` 回（1.5 倍）、`AttackStreak >= 2` なら `Weight×4` 回（2 倍）入れる
  - A を厚くする行：`HeavyA`、`StackA`、`PushA`、`Five_HeavyA`、`Five_MidA`。B は同じ名前の B
- `PickDifferentSetup`（前ラウンドと同じ配置なら最大 3 回引き直す）は同じ重み付きのプールから引くので、偏りは引き直しでも保たれる
- ノーマル以上（Difficulty >= 1）。ログ `[Adapt] site=A streak=2`

### 6.4 寄った Bot を確率で戻す
- 実装済み。Director の `LotOne` にある「寄っている途中（State 4）で別のサイトに出来事があったら、道のりの半分より手前なら `FakeBase` × 個性の係数の確率で引き返す（20 秒に 1 回まで）」がこれに当たる
- Step 23 では PIE で動作を確認するだけ。「到着して 6 秒何も無ければ手薄なサイトへ戻る」（空振り）は未実装だが、Step 17 の残りなので今回の範囲外

### 6.5 ハードの「設置前の予測移動」（仮の定義）
`CallRotate` が Director に置き換わったため、元の定義（[04](04_enemy_ai.md)）は使えない。次のように定める。
- 対象：ハード以上（Difficulty >= 2）、設置前（フェーズ 1）
- Director がプレイヤーの目撃・足音の報告を受けたとき、位置から行き先のサイトを予測する
  - A 通路（Y < -3000 かつ X < 600）→ A。B 通路は左右反転で B
  - ミッド（|Y| < 1200 かつ -2800 < X < 1000）：直前の報告位置からの Y の変化が -300 より小さければ A、+300 より大きければ B、それ以外は予測しない
- 予測したサイトにいない、交戦していない Bot のうち一番近い 1 体を、そのサイトへ寄らせる（`Reinforce(SiteDest(サイト))`）
- 1 ラウンドに 2 回まで、前回から 20 秒以上空ける。ログ `[Predict] site=B`

### 6.6 裏取りの経由点を `BP_FlankPoint` にする
- 経由点は今、`BP_PR_AIController.FlankThink` に直書きされている（[12](12_macro_ai.md) の「Director に直書き」は誤り。あわせて直す）。X は -1900、-3400、-2000、300、Y は 1 点目が 0、2 点目以降が `FlankSide × -3400`（cm）
- 新しいアクター `BP_FlankPoint`（変数 `Side`：`FlankSide` と同じ値、`Order`：0〜3）を作り、L_Pind に今の座標どおり 8 個置く（1 点目は左右で同じ位置に 2 個）
- `StartFlank` で、`Side` が一致する `BP_FlankPoint` を `Order` 順に集めて `FlankPath`（Vector 配列）に入れ、`FlankThink` はそれを順にたどる。1 個も無ければ今の直書きの値を使う

## 7. ミニマップ（Step 22）

- 画面左上（余白 24px）に、マップ全体を常に表示する。プレイヤーは中央に固定せず、回転もしない（上が北 = +X）
- 大きさは 1080p で 300×300px。画面の高さに合わせて拡大縮小する。`CheatText` はミニマップの下へ移す
- 画像：L_Pind を真上から写したテクスチャ `T_PR_Minimap_Pind` をエディタで作っておく（実行時に撮ると、ライトが整う前で暗くなったり、Bot が写り込んだりするため）。範囲は X・Y とも -4000〜+4000cm。作り方は、エディタで正投影の SceneCapture2D（幅 8000、真上、上が +X）を一時的に置いて RenderTarget に写し、静的テクスチャに変換する。一時的なアクターはレベルに残さない
- 描画は `BP_PR_HUD` の Canvas に `DrawMinimap` を足す（既存のクロスヘアやキルフィードと同じ方式）
- ワールド座標から画面への変換：u = (Y + 4000) / 8000、v = (4000 − X) / 8000
- 表示するもの
  - 画像（不透明度 0.85）と A／B の文字
  - プレイヤー：向き付きの三角（向きはカメラの Yaw）
  - Bot：プレイヤーから見えている間（0.1 秒ごとに、カメラから Bot の頭へのトレースが通り、画面内にいる）と、リコン・アラームボットで表示されている間（`RevealUntil`）だけ赤い点
  - 設置したスパイク
  - 自分の設置物：リコールの目印、スモークのアンカー（発動中は煙の円）、アラームボット

## 8. 実装の順番と確認

| 段階 | 内容 | 確認（PIE） |
|---|---|---|
| 21-0 | ブランチの準備、キーの変更、`SkillSel` / `SkillCharges`、スタート画面の選択欄、購入画面のスキル欄、HUD の `SkillBar` と `NoticeText`、構え（`SkillMode`）と `IA_Fire` の分岐 | タイトル →「プレイ」→ スタート画面で選ぶ → 購入 → HUD に回数が出る。キー設定の画面に新しい行が出て、重複が無い。「もう一度」「タイトルへ」も通す（Step 15 の未確認だった通しを兼ねる） |
| 21-1 | ブリンク、フラッシュ（Bot の目くらまし）、リコン（壁越し表示）、§5 の視界と射撃の変更 | ブリンクの距離と壁での停止。フラッシュで Bot が 5 秒撃たない（ログ）。リコンで壁越しに表示 |
| 21-2 | リコール、ヒール | 目印へ戻る。体力が最大で止まる |
| 21-3 | スモーク（Bot の視界を遮る）、アラームボット | 煙越しに Bot が撃ってこない。アラームボットで通知 |
| 22 | ミニマップ | 位置と向きが合う。リコンで表示した Bot が出る |
| 23 | §6 の 6 項目 | 撃つと設置がやり直し。死ぬと武器が落ちる。`[Adapt]` `[Predict]` のログ。裏取りが `BP_FlankPoint` をたどる。引き返しが起きる |

各段階の終わりに docs（この文書の実装結果、[03](03_combat.md)、[06](06_ui.md)、README の操作説明）と TASK.md を更新する。

## 9. 実装結果

### 21-0（2026-11-11）
作ったもの：
- キー：`IA_Skill1/2/3`（C/E/Q）を `DT_KeyBinds` に追加。拾う=F、テスト用武器切替=T、ナイフを眺める=Y（`IA_Inspect` を `IMC_PR` から外して `DT_KeyBinds` へ）。`SlotName` を `PR_Settings2` に。`WBP_Title` の操作説明を更新
- データ：`S_Skill` / `DT_Skills`（行名 `スロット_ID`、名前・説明・最大回数・価格）と `BFL_PR.SkillInfo(Slot, Id)`。`BP_PR_GameInstance.SkillSel`（保存はスロット `PR_Skills`、`SG_PR_Settings.SkillSel` を流用）、`SetSkillSel` / `LoadSkills` / `SaveSkills`。`BP_PR_GameMode.SkillCharges`（OpenLevel で作り直されるため試合開始時に 0）、`TryBuySkill(Slot)`、`SkillText(Slot)`（購入画面の表示文字列と購入可否）
- スタート画面：`WBP_MapIntro` にセットごとの選択ボタン（選択中は赤）、説明 1 行、「準備完了」。`PlayIntro` の `Delay 5` を「`bDone` を 0.2 秒ごとに確認」に置き換え。表示中はカーソルを出して UI のみ、決定後にゲーム入力へ戻す。20 秒で自動決定
- 購入画面：「スキル」見出しと 3 ボタン（`C フラッシュ　250　0/2` 形式、買えないときは無効）
- HUD：`SkillBar`（下中央）、`NoticeText`（位置 (0,150)、まだ何も表示しない）、`UpdateSkills`（0.1 秒ごとのタイマー）
- 構え：`BP_PR_Character.SkillMode`、`IA_Skill1/2/3`、`SkillKey(Slot)`（残り回数があれば 1 減らしてログ `[Skill] slot=N id=M used`）、`SkillActivate`（空）、`IA_Fire` の Started を `SkillMode>0` で分岐

仕様との差分：
- `SkillBar` は 3 枠ではなく 1 つの文字列（`C フラッシュ 1/2     E リコール 0/1 ...`）。●○ ではなく `n/最大`。構え中の黄色は未実装（`SkillMode` を使う段階で）
- 選択欄の説明は、各ボタンの下ではなく 1 行にまとめ、最後に押したボタンの説明を表示
- `SkillMode` を 0 に戻す処理は、死亡（キャラごと作り直し）では自動。同じキー再押し・1/2/3 の持ち替えでの解除は未実装（構えを持つスキルを作る 21-1 で入れる）
- 準備完了ボタンがスタート画面下部の `SideText` と重なる（見た目の調整が必要）

確認（PIE）：タイトル →「プレイ」→ スタート画面（選択・赤枠・説明・カウントダウン 20 秒・準備完了、時間切れでも進む）→ B で購入（クレジット 800→350、最大回数で止まる）→ HUD の回数表示 → C/E でログ `[Skill] slot=1 id=1 used` と回数減少。スクリーンショット：`docs/images/skills_intro.png`、`skills_buy.png`、`skills_hud.png`（購入画面のスクリーンショットは購入直後の状態で、ウィンドウ全体）。
未確認：設定画面のキー一覧での重複確認、リザルトからの「もう一度」「タイトルへ」、パロラント（難易度 4）でのスキル購入、`bSkipTitle` 起動時のスタート画面の流れ以外、Q の入力、IA_Fire の構え分岐の実動作（`SkillMode` が常に 0 のため）。

### 21-0 の手直し（2026-11-11）
- スタート画面：選択欄を `SkillBG`（Border、左中央・左余白 40px・700×390、背景 #1B2A32 相当・不透明度 0.85）にまとめ、`SkillPanel` をその中へ入れた。中央の「あなたは攻撃側…」「Aサイト／Bサイト…」や下の帯と重ならない（`docs/images/skills_intro.png` を撮り直し）
- HUD の `SkillBar`（文字 1 行）は非表示にし、`SkillRow`（下中央、(0.5,1)、位置 (0,-30)）に 3 枠（`SkillBox0..2` の Border と `SkillTxt0..2`）を作った。1 枠は「キー／名前／●○」の 3 行。● が残り、○ が最大までの空き（関数 `Dots`、`SkillLabel` の戻り値を改行区切りに変更）。構え中の枠（`SkillMode` = スロット番号 + 1）は背景を黄色にする。`UpdateSkills`（0.1 秒ごと）が文字・色・`AimText` を更新。体力・弾数表示とは重ならない（`docs/images/skills_hud.png`）
- 構えの解除：同じスキルキーの再押し、1/2/3 の持ち替えで `SkillMode` = 0（新関数 `SkillPress(Slot)`。IA_Skill1/2/3 は `SkillKey` ではなく `SkillPress` を呼ぶ）
- ピックアップ表示の文字を「[E]」から「[F]」に直した
- 確認（PIE）：設定画面のキー一覧にスキル1〜3・武器を拾う・ナイフを眺める・テスト用武器切替の行があり、`DT_KeyBinds` の 21 行の初期キーに重複はない（W S A D Space Shift Ctrl 左クリック R 1 2 3 4 F T B U Y C E Q）。Q でログ `[Skill] slot=3 id=0 used` と回数の減少。リザルトの「もう一度」（スタート画面に戻り回数は 0）と「タイトルへ」（タイトル画面）が通った（`EnemyScore` を 4 にして `Health` を 0 にし、試合を早く終わらせた）

### 21-1（2026-11-11）
作ったもの：
- ブリンク：`BP_PR_Character` の `BlinkStart`（`GetLastMovementInputVector` を水平にして正規化、無入力なら前方を `BlinkDir` に、`BlinkLeft` = 0.15）と `BlinkTick(DT)`（Tick の先頭。`min(DT, BlinkLeft) × 4666.667`（= 700cm ÷ 0.15 秒）を `AddActorWorldOffset`（Sweep）で進める）。上下は動かさない
- フラッシュ：`BP_PR_SkillFlash`（Actor。`Col`（球、BlockAll）、`Move`（ProjectileMovement、初速 1800、重力 1、跳ね返り 0.45）、`Light`（PointLight、強さ 0）、`Mesh`）。BeginPlay で 1.0 秒待ち、`Light` を強さ 80000 にして `SFX_Hit` を鳴らし、`GetAllActorsOfClass(BP_PR_Bot)` の各 Bot に関数 `BlindOne` を実行（生きている・目から距離 5000 未満・Bot の前方との内積 > 0.5・目からフラッシュへの Visibility トレースが遮られない（自分に当たるのは可）をすべて満たせば `BP_PR_AIController.BlindUntil` = 今 + 5、変数 `Count` を加算）。ログ `[Flash] blinded=N`。0.2 秒後に消える。プレイヤーには効かない
- リコン：`BP_PR_SkillRecon`（`Col`、`Move`（初速 2000、重力 1、跳ねない）、`Mesh`）。`OnProjectileStop` から 0.5 秒後、半径 2500 以内の生きている Bot に関数 `RevealOne` で `BP_PR_Bot.RevealUntil` = 今 + 4。ログ `[Recon] revealed=N`。4 秒後に消える。`BP_PR_HUD.DrawReveal`（`ReceiveDrawHUD` の `DrawKillFeed` の後）が各 Bot で関数 `RevealOne` を実行し、`RevealUntil` が有効で生きていれば、頭付近（+60cm）を `Project` し、画面の前方なら赤い菱形（`DrawLine` 4 本）と距離（m）を描く。壁越しでも描く
- 発動：`SkillPress(Slot)`。同じキー再押しなら構え解除、そうでなければ構えを解いて、回数 > 0 のとき `PlantProgress` を 0 に戻し、ブリンク・フラッシュは `SkillKey` で回数を減らしてから `BlinkStart`／`ThrowFlash`、リコンは `SkillMode` = 1（回数は減らさない）。`SkillActivate`（構え中の `IA_Fire`）は `PlantProgress` = 0、`ThrowRecon`、`SkillKey(0)`、`SkillMode` = 0 の順。投げる位置はカメラの前 80cm、向きはカメラの向き
- HUD：構え中に `AimText`「左クリック：投げる」（`SkillRow` の上、(0,-140)）。構え中の枠は黄色
- Bot（§5）：`BP_PR_AIController` に `BlindUntil`（0）と `LostFireTime`（0.5）、関数 `CanShoot`（`Now >= BlindUntil` かつ `Now - VisibleTime < LostFireTime`）。`CanSeeTarget` の先頭で `Now < BlindUntil` なら false。`BurstTick` と `StrafeTick` の `WFire` の手前に `CanShoot` の分岐。`DuelTick` の `DuelAim` の条件に `Now >= BlindUntil` を追加（`IsSmokeBlocked` は 21-3）。`BP_PR_Bot` に `RevealUntil`

仕様との差分：
- 構え中の枠は「黄色の枠線」ではなく、枠の背景色を黄色にした
- `DuelAim` は、元から「見えている間（`Now - VisibleTime < 0.25`）」だけ呼ばれるため、その条件に `Now >= BlindUntil` を足した
- フラッシュの方向は、Bot の位置からフラッシュの位置へのベクトルで判定した（炸裂時の位置を使う）
- `SkillActivate` にあった動作確認用の `PrintString` はつながりを外した

確認（PIE。値は `inspect set_property` で `SkillSel` / `SkillCharges` などを直接入れて試した）：
- ブリンク：開けた場所で前方に 700cm（-3600 → -2900 → -2200）。壁（PIE に置いた幅 100 の直方体、面は X = -1150）に向けると壁の手前 -1206（カプセル半径の分）で止まった。WASD の方向は未確認（無入力の前方のみ）。Bot のカプセルは止めない（通り抜ける）
- フラッシュ：Bot の正面に投げて `[Flash] blinded=1`。Bot が背を向けていると `[Flash] blinded=0`
- リコン：C で構え（黄色の枠と「左クリック：投げる」）、左クリックで投げて `[Recon] revealed=2`。壁越しの Bot に菱形と距離が出た（`docs/images/skills_recon.png`。菱形を撮るために `RevealUntil` を長くして一時停止中に撮った）
- スクリーンショット：`skills_intro.png`、`skills_hud.png`（構え中の HUD）、`skills_recon.png` はゲーム画面（ビューポート）だけに切り抜いた

未確認：
- フラッシュを受けた Bot が 5 秒撃たないこと、見失って 0.5 秒で撃つのをやめること（撃ち合いの手応え）は、PIE の操作の待ち時間でラウンドが進んでしまい実測できなかった。`CanShoot` と `CanSeeTarget` の分岐はグラフとコンパイルのみ確認
- WASD を押しながらのブリンクの方向、スモーク・リコール・ヒール・アラームボット（後の段階）
- 試合中のブリンクが設置を中断すること（`PlantProgress` の 0 戻しはグラフのみ）


### 21-1 の追加確認（2026-11-11）
実測の方法：一時的な `PrintString` は入れず、MCP のログポイント（ノードを通った回の game time とピン値を、グラフを変えずに記録する機能）を `WFire`（`BurstTick`・`StrafeTick`）、`CanShoot` のリターン、`BP_PR_SkillFlash` の `Set BlindUntil` に付けて PIE で測り、終わったらログポイントを全部消した（グラフには何も残っていない）。

- フラッシュで Bot が 5 秒撃たない：Bot の正面に C で投げて、`BlindUntil` を設定した時刻 t=129.809（= 134.809 まで）。`WFire` の時刻は …128.512、129.297 のあと 135.768 まで 1 回も無い（6.5 秒の空き）。目くらまし前の最後の発砲は 129.297、復帰後の最初の発砲は目くらまし終了の 0.96 秒後
- 見失って 0.5 秒で撃つのをやめる：壁（PIE に置いた直方体）で視線を切った。`VisibleTime` = 164.348、最後の発砲は 163.895（見失う前）で、そのあと 169.46 まで発砲も `CanShoot` 呼び出しも無い（State は 2）。バーストの合間で見失ったため「バーストの途中で止まる」瞬間は捉えられなかった。そこで一時停止中に `CanShoot` を直接呼んで境界を確認：`Now - VisibleTime` = 5.1 で false（t=169.46）、`VisibleTime` を 0.3 秒前に書き換えると true
- ブリンクの方向：D を押しながら C（`simulate_input` の `key_down D` → `key_tap C` → `key_up D`）で、X は -3600 のまま Y が 0 → 1054（700cm のブリンク＋押している間の歩き分）。前方（+X）には動かず、右へ動いた
- 設置中のスキル使用：`PlantProgress` を 0.7 にして C を押すと 0。何もしなければ 0.7 のままなので、スキルがリセットしている
- ブリンクと Bot：Bot を目の前（400cm）に置いてブリンクすると、Bot の手前（中心間 90cm）で止まった。プレイヤーも Bot も `CollisionCylinder` が `Pawn` プリセットで、Sweep は Bot に当たる。21-1 で「通り抜ける」と書いたのは、Bot が動いていたか Sweep 範囲外だった測定だと思われ、今回は修正の必要がなかった（コードは変えていない）

### 21-2（2026-11-11）
作ったもの：
- `BP_PR_RecallBeacon`（Actor。`Mesh` = 円柱 30×30×50cm、不透明でない水色 `M_RecallBeacon`（Translucent・Unlit・エミッシブ水色・不透明度 0.45・両面）、`Light` = PointLight 強さ 800 の水色。衝突なし）
- `BP_PR_Character`：変数 `RecallBeacon`（参照）、`SkillHandled`（bool）。関数 `RecallPlace`（足元の 73cm 下＝床の高さにスポーン）、`ClearBeacon`（有効なら破棄して空に）、`HealUse`（`Health` = min(`Health` + `PlayerMaxHealth`, `PlayerMaxHealth`)）、`SkillSpecialPress(Slot)`（スロット 1 かつ `SkillSel[1]` = 0 で目印が有効ならリコールの帰還を始め、スロット 1 かつ `SkillSel[1]` = 1 でヒールが使えない（体力が最大、またはフェーズが 1・2 以外）ときは「処理済み」として何もしない。結果は `SkillHandled`）。カスタムイベント `RecallGoEvt`（0.4 秒待つ → 目印が有効で生きていれば目印の位置 + 73cm へ `SetActorLocation`（Teleport、向きはそのまま）→ `ClearBeacon`）
- `SkillPress`：「構えの解除」の直後に `SkillSpecialPress` を呼び、`SkillHandled` なら終了。回数チェックのあと、ブリンク・フラッシュの判定の else に「スロット 1・ID 0 → `RecallPlace`」「スロット 1・ID 1 → `HealUse`」を追加（回数の消費は共通の `SkillKey`）。`PlantProgress` の 0 戻しは、リコールの帰還は `SkillSpecialPress` 内、置く・ヒールは既存の共通処理で行う
- `StartDeathCam` の先頭で `ClearBeacon`。`BP_PR_GameMode.CleanupRound` の末尾で `BP_PR_RecallBeacon` を全部破棄（ラウンド開始時）
- `WBP_GameHUD.SkillLabel`：スロット 1 で目印が有効な間は名前を「戻る」にする

仕様との差分：
- 目印の置き場所は「足元の床の高さ」。帰還先は「目印の位置 + 73cm」（立っているときのカプセル半高さ 98 − 目印の中心高さ 25）。しゃがんでいるときに置くと少し高い位置に戻る
- 帰還中（0.4 秒）に回数は減らない（最初の 1 回目で消費済み）。帰還の途中で 2 回押しても、2 回目のイベントは目印が無くなっているので何もしない
- リコールの帰還は回数が 0 でも使える（目印があるとき）。ヒールの「使えない」ときも `PlantProgress` は 0 にしない

確認（PIE。値は `inspect set_property` で入れ、キーは `simulate_input` で押した）：
- リコール：E で目印（-3600, 0）、回数 1 → 0。プレイヤーを (-3600, 1500) へ移動（1500cm）して E → 0.4 秒後に (-3600, 0, 98.15) へ戻り、目印は消えた。目印がある間、HUD のテキスト一覧に「E / 戻る / ○」。死亡（`StartDeathCam` を直接呼んだ）で目印が消えた。`CleanupRound` を直接呼んでも消えた
- ヒール：`Health` = 100、フェーズ 0 で E → 変化なし（100、回数 1）。フェーズ 1 で E → 200（`PlayerMaxHealth` は 200）、回数 1 → 0。体力が最大のとき E → 回数は 1 のまま
- 目印の高さは、確認のあとで `Mesh` の相対位置を 0 に直した（確認時は 25cm 浮いていた。直したあとの見た目は未確認）

未確認：
- 目印の見た目（半透明水色の円柱）のスクリーンショット。PIE を `PlayIntro` の直接呼び出しで進めたためタイトル画面が残り、ゲーム画面を撮れなかった
- 実際の次ラウンド開始（`StartRound`）での目印の消去（`CleanupRound` の直接呼び出しのみ）と、実際の被弾死での消去（`StartDeathCam` の直接呼び出しのみ）
- 帰還中に死んだ場合（イベントの `bDead` ガード）

### 21-3（2026-11-11）
作ったもの：
- `BP_PR_SmokeAnchor`（Actor。`Col` 球 半径 8・BlockAll、`Move`（初速 1500、重力 1、跳ねない）、`Mesh` 小さな立方体）、`BP_PR_SmokeField`（`Mesh` = 球 ×9 = 半径 450cm、`M_PR_Smoke`（Translucent・Unlit・両面・灰色・不透明度 0.93）。BeginPlay で `GameMode.ActiveSmokes` に自分を足し、15 秒後に破棄。EndPlay で配列から外す）
- `BP_PR_Character`：`ThrowSmoke`（カメラの前 80cm にアンカーを生成）、`SmokeFire`（戻り値 `Used`。カメラ前方との角度が 6° 以内の未発動アンカーがあればその位置に煙を出してアンカーを破棄。なければ `SkillCharges[2]` > 0 のとき `ThrowSmoke` と `SkillKey(2)`）、`SkillActivate` に `SkillMode`==3 の分岐（`PlantProgress`=0、`SmokeFire`、`Used` なら `SkillMode`=0）、`SkillPress` に「スロット 2・ID 0 なら（回数 0 でも）`SkillMode`=3」の分岐と「スロット 2・ID 1 なら `AlarmPlace`」、`AlarmPlace`（足元の前 150cm から下向き 400cm のトレースの命中点 +6cm に `BP_PR_AlarmBot` を生成）
- `BFL_PR.IsSmokeBlocked(Ctx, Start, End)`：`ActiveSmokes` の各煙で、線分 Start–End 上の最近点と煙の中心の距離 < 450 なら true。`CanSeeTarget`（視線のトレースの後）と `BP_PR_SkillFlash.BlindOne`（トレースの後）から呼ぶ。射撃のトレースは変えていない
- `BP_PR_HUD.DrawAnchors`（`SkillMode`==3 の間、未発動のアンカーを `Project` して白い四角を描く）
- `BP_PR_AlarmBot`（`Mesh` 箱 25×25×12 + 赤 `M_PR_Alarm`、`Light` 赤い PointLight。`Scan` イベントが 0.2 秒ごとに `CheckBot` を全 Bot に実行して `Light` の表示を切り替え（点滅））。`CheckBot`：生きている・距離 < 700・`BP_PR_Bot.AlarmCool` <= 今・Visibility のトレースが通る（当たったのが Bot 自身でも可）・`IsSmokeBlocked` でない、なら `AlarmCool` = 今 + 10、`RevealUntil` = 今 + 2、`GameMode.NoticeUntil` = 今 + 2.5、ログ `[Alarm] detected`
- `WBP_GameHUD.UpdateSkills`：`SkillMode`==3 の `AimText` を「左クリック：投げる／アンカーを狙って発動」に、`NoticeText` を `NoticeUntil` の間「アラームボットが敵を検知」（橙色）に
- `GameMode.CleanupRound` の末尾で `BP_PR_SmokeAnchor` / `BP_PR_SmokeField` / `BP_PR_AlarmBot` を全部破棄

仕様との差分：
- `IsSmokeBlocked` の引数は Start・End のほかに `Ctx`（Object。`GetGameMode` のワールドコンテキスト用で、呼び出し側は self を渡す）。実行ピンがある（pure ではない）
- アンカーは発動で消える（煙が消えるまでは残さない）。ミニマップ用の「煙の円」は Step 22 で `ActiveSmokes` から描く
- 通知の表示は `GameMode.NoticeUntil`（新変数）を `UpdateSkills`（0.1 秒ごと）が読む方式
- 煙の不透明度は 0.8 では背景が透けたため 0.93 にした
- 構え中に煙を持っていなくても、置いたアンカーを発動できるよう、スモークの構えは回数 0 でも入れる（回数の消費は投げるときだけ）

確認（PIE）：
- スモーク：Q で構え（`SkillMode`=3、`AimText`、アンカー位置に白い四角）、アンカー 2 個（X=-2709 と別方向 Y=384）を投げて回数 2→0。画面中央に捉えた方だけ発動し、もう一方は残った（`docs/images/skills_smoke.png`。外から見た煙）。ラウンドが替わると残っていたアンカーと煙は消えた
- 煙越しの Bot（ログポイント。`CanSeeTarget` の戻り値、`BurstTick` の `WFire`）：煙の発動の約 0.1 秒後に `bVisible` が True→False（t=247.209 → 247.31）、`WFire` は 247.44 が最後で、以後 252.1 まで（煙が消える 262 ごろまで）`WFire` は増えず（189 回のまま）。煙が消えた後 `bVisible` は True に戻り、`WFire` も再開（t=270 台）
- 煙越しのフラッシュ：煙なしで `[Flash] blinded=1`、Bot の手前に煙を置くと `blinded=0`
- アラームボット：Q で (-3450, 0, 6) に置かれ、700cm 以内に Bot を置くと `[Alarm] detected`、橙色の通知と赤い菱形（`docs/images/skills_alarm.png`）。範囲に居続けた Bot の通知は約 10.1 秒間隔（t=74.5, 84.6, 94.8, 104.9, 115.1）。ラウンドが替わるとアラームボットは消えた
- リコール：目印は床に接している（中心 z=25、高さ 50）。スクリーンショット `docs/images/skills_recall.png`
- 不具合を 1 件直した：`SkillPress` の構えの判定で、まだ実行されていないキャストの出力（`SkillSel` の読み出し）を使っていて ID が常に 0 になり、アラームボットを選んでも Q がスモークの構えになっていた。判定用に自前のキャストを足した

未確認・限界：
- リコールの帰還中に死亡した場合：`bDead` を true にして E を押したが、死亡処理でキャラが作り直されて位置も戻るため、ガードの効果と切り分けられなかった
- 煙の中の自分から外の Bot が見えない見た目（中から）は未撮影。`WFire` の時刻の測定は、Bot をプレイヤーの前に移動して行った
- アラームボットの設置で下向きトレースが外れた（足元の前が穴など）場合は、回数だけ減って置かれない
- 実際のプレイでの手応え（煙の大きさ 450cm、アラームの範囲 700cm）は未調整

### 21 の手直し（2026-11-11、Step 22 の前）
- デバッグ文字：スキルまわりの `PrintString`（`[Alarm] detected`、`[Skill] slot=… used`、`[Flash] …`、`[Recon] …`）の `Print to Screen` を false にした（ログには残る）。未使用の `SkillActivate` 内の `PrintString` はつながっていないのでそのまま
- 煙：`M_PR_Smoke` を Translucent から **Opaque**（Unlit・両面のまま、色は灰色）に変えた。外から見て向こうが一切透けない（`docs/images/skills_smoke.png` を撮り直し）。ただし、煙の球の中に立つと、通路の壁と床が球の半径より手前にあるため一部見える。そこで `BP_PR_HUD.DrawSmokeCover`（`ReceiveDrawHUD` の最初に呼ぶ）を足し、カメラが `ActiveSmokes` の煙の中心から 450cm 以内なら画面全体を灰色の矩形で塗る。HUD の文字・ミニマップ・UMG はその上に出る（`docs/images/skills_smoke_inside.png`）
- スキル枠：`WBP_GameHUD.SkillRow` の幅を 480 から 690 にして「アラームボット」が枠に収まるようにした

### 22 ミニマップ（2026-11-11）
作ったもの：
- 画像 `/Game/PARORANT/UI/T_PR_Minimap_Pind`（1024×1024）。エディタで正投影の SceneCapture2D（位置 (0,0,2000)、真下向き、OrthoWidth 8000、Final Color LDR）を一時的に置いて RenderTarget に写し、`convert_render_target_to_texture2d_editor_only` で静的テクスチャにした（Python）。上が +X（北）、右が +Y（東）で合っており、A サイトが左上、B サイトが右上、攻撃スポーンが下。クレートの位置（`CoverMid_1` (200,500) など）が画像の座標どおりに写っていることも確認した。一時アクター（`SceneCapture2D`）は破棄し、RenderTarget は保存していないため、レベルにも Content にも残していない。Bot・見えない当たり判定は写っていない。圧縮は UserInterface2D（`TC_EDITOR_ICON`）、ミップなし、ストリーミングなし
- `BP_PR_HUD`：`ReceiveDrawHUD` の `DrawAnchors` の後に `DrawMinimap`。変数 `MapTex`（画像）、`MapX` / `MapY` / `MapS`（左上の位置と一辺。`MapS` = 画面の高さ × 300/1080、`MapX` = `MapY` = 画面の高さ × 24/1080）、`VisBots`（見えている Bot の配列）
- 描画順：画像（不透明度 0.85）→ A／B の文字 → 見えている Bot（赤い点）→ `RevealUntil` が有効な Bot（赤い点。リコン・アラームボット）→ スモークのアンカー（白い点）→ アラームボット（桃色の点）→ 発動中の煙（`ActiveSmokes` の灰色の円。半径 450cm を縮尺どおり、24 本の線分）→ スパイク（橙の点）→ リコールの目印（水色の点）→ プレイヤー（向き付きの緑の三角。位置と向きは `GetPlayerViewPoint` のカメラ）
- 関数：`MapDot(Loc, Col, R)`、`MapCircle(Loc, RadiusCm, Col)`、`MapTri(Loc, Yaw, Col, Size)`、`MapDotActor`、`MapCircleActor`、`MapReveal`。座標変換は `MathExpression` で u = (Y+4000)/8000、v = (4000−X)/8000
- Bot の可視判定：`BeginPlay` で 0.1 秒ごとのタイマーに `MapScan`（`VisBots` を空にして全 Bot に `ScanOne`）。`ScanOne` は、生きている Bot の頭（+60cm）について、カメラから頭への Visibility トレース（プレイヤーは無視）が通る（当たりが無いか、当たったのがその Bot）、`BFL_PR.IsSmokeBlocked` でない、`PlayerController.ProjectWorldLocationToScreen` の結果が画面内、をすべて満たすときだけ `VisBots` に足す
- 表示条件：`GameMode.Phase` < 4 かつ `PlayerController.GetViewTarget` が `PRChar`（スタート画面の鳥瞰では別の視点なので出ない）。タイトル・リザルトは元から `bShowHUD` が false。死亡中は視点がプレイヤーの死亡カメラのままなので表示される場合があるが、確認したのは試合中のみ（下記）
- `WBP_GameHUD.CheatText` を (32, 28) から (32, 336) へ（ミニマップの下）。もとは非表示（Collapsed）の文字で、無敵チートが有効なときだけ出る

仕様との差分：
- ミニマップの縮尺は画面の高さ基準。UMG の `CheatText` は DPI スケール基準で、1080p では合うが他の解像度ではずれることがある
- 表示するスキルの設置物の色はこちらで決めた（アンカー=白、アラームボット=桃、リコールの目印=水色、スパイク=橙、煙=灰色の円）
- `DSL（write_graph_from_code）` はこの日本語エディタで算術ノードが引けず、グラフはすべて `edit_graph` の batch と `MathExpression` で組んだ
- ミニマップのための `HUD.Project`（Canvas が描画中にしか有効でない）は使えず、`PlayerController.ProjectWorldLocationToScreen` に差し替えた（最初の版は Bot が一度も出なかった不具合を直した）

確認（PIE。ビューポートの小さい状態、1178×498 のエディタ内。`control_actor set_transform` でプレイヤーと Bot を動かし、`simulate_input` でキーを押した）：
- 位置と向き：攻撃スポーン (-3600,0)・A サイト (2300,-2700)・B サイト (2300,2700)・ミッド (0,0) で、三角が正しい場所に出て、向き（yaw 0=北／90=東／180=南／270=西）が合った（`docs/images/minimap.png`、4 枚のミニマップを拡大した合成画像）
- Bot：正面の通路にいる Bot だけが赤い点で出て、壁の向こうの Bot（A レーンの箱の上、ミッドの脇）は出なかった。リコンを投げると、壁の向こうにいた Bot の赤い点が追加で出た（`docs/images/minimap_recon.png` の左が投げる前、右が投げた後。`docs/images/minimap_view.png` は通常の画面）
- 設置物：リコールの目印（水色）、アラームボット（桃色。プレイヤーの後ろに離れて確認）、スモークのアンカー（白）、発動中の煙の灰色の円が出た
- 煙：外から見て向こうが透けない（`docs/images/skills_smoke.png`、ミニマップに円も出ている）。中に入ると画面全体が灰色になる（`docs/images/skills_smoke_inside.png`）
- スタート画面（鳥瞰）ではミニマップが出ない
- スクリーンショットは、エディタ全体の画像からゲーム画面（ビューポート）だけを切り抜いた

未確認：
- 設置したスパイクの橙の点（スパイクを設置する流れを PIE で通していない。`SpikeRef` の有効判定のみグラフ）
- 死亡中・ラウンド終了（Phase 3）・リザルト・タイトルでの表示。最初の版は表示条件が Phase < 3 で、`ROUND LOSS` の間は出なかったため、Phase < 4 に直した。直したあとの Phase 3 の表示は撮っていない
- 1080p 以外のウィンドウ（ウルトラワイド等）での見た目。縮尺は画面の高さ基準なので比例して変わる
- `MapScan` の負荷（0.1 秒ごとに Bot の数だけトレースと投影。Bot は最大 5 体程度）は測っていない

### 23（2026-11-11）
作ったもの：
- §6.1 設置の中断：`BP_PR_Character` に `bPlantNeedRelease` と関数 `PlantInterrupt`（`PlantProgress > 0` なら 0 にして `bPlantNeedRelease` = true）。`IA_Fire` の Started の構え中でない側（`StartFire` の手前）と、`SkillPress` / `SkillActivate` の `PlantProgress` = 0 の位置（4 か所）で呼ぶ。`PlantTick` の先頭で `bPlantNeedRelease` が true の間は何もせず（4 キーがしゃがみ操作でなければ `UnCrouch`）、`IA_Plant` の Completed で false に戻す。`PlantProgress` が 0 のときに撃っても true にはならない（押していないのに次の設置が止まらないように）
- §6.2 死亡時の武器ドロップ：Tick の死亡検知（`StartDeathCam` の後）で、`PrimaryWeapon` が有効なら `Drop`、無ければ `SecondaryWeapon` を `Drop`。落とした方の参照と `PrimaryId` / `SecondaryId` を空にしてから `AddDeath` へ進む
- §6.3 攻め先の重み：Director に `RoundThreatA` / `RoundThreatB`（`ApplyEvent` で、A（`Area` 0）と B（`Area` 2）の `Pts` を足す。ラウンドごとに Director を作り直すので 0 から）。`BP_PR_GameMode` に `LastAttackSite` / `AttackStreak` / `AdaptSite`、関数 `DecideAttack`（`EndRound` の最後に呼ぶ。Difficulty >= 1。設置済みなら `SpikeRef.Site` の末尾 A/B、無ければ `RoundThreatA/B` の大きい方（A >= B で A、両方 0 ならなし）。同じサイトなら `AttackStreak` + 1、変われば 1、なしなら 0）と関数 `SetupMult(RowName)`（既定 2、行名の末尾が A／B でそれが `LastAttackSite` と一致すれば 3、`AttackStreak >= 2` なら 4。Difficulty 0 では常に 2）。`PickSetup` の `ForLoop` の `LastIndex` を `Weight × SetupMult(行名)` にした（`PickDifferentSetup` は `PickSetup` を呼ぶので同じ重み）。ログ `[Adapt] site=A streak=2`
- §6.5 予測移動：Director に `LastRepY`（100000）・`PredictCount`・`LastPredictTime`（-100）・`PredArea`、関数 `Predict(Loc)` と `PredPick(C, Area, Dest)`。`ApplyEvent` の `SetLastInfoTime` の直後で `Predict(Loc)` を呼ぶ。条件は Difficulty >= 2、`Phase` = 1、`PredictCount` < 2、前回から 20 秒以上、予測できた（`PredArea` >= 0）。予測は仕様どおり（A 通路 → 0、B 通路 → 2、ミッドは `LastRepY` との差 ±300）。`PredPick` は生きていて、`State` が 1 と 6 でなく、予測サイトの外にいる Bot のうち、`SiteDest` に一番近いものを `TmpNear` に残す。1 体を `Reinforce(SiteDest(PredArea))` し、ログ `[Predict] site=A`。最後に `LastRepY` を今回の Y にする
- §6.6 `BP_FlankPoint`（`/Game/PARORANT/Blueprints/World`）：Actor、`Marker`（球、0.4 倍、ゲーム中は非表示、当たり判定なし）、変数 `Side`（float、`FlankSide` と同じ値）、`Order`（int）。L_Pind に 8 個（`FlankPoints` フォルダ、Z = 20）：`Side` = 1 は (-1900,0)、(-3400,-3400)、(-2000,-3400)、(300,-3400)、`Side` = -1 は (-1900,0)、(-3400,3400)、(-2000,3400)、(300,3400)。`BP_PR_AIController` に `FlankPath`（Vector 配列）。`StartFlank` が `Order` 0〜3 の順に `Side` 一致のものを `FlankPath` へ集め（`ForLoop` 0〜3 の中で `GetAllActorsOfClass` の結果を回す）、1 個も無ければ従来の値を 4 点入れる。`FlankThink` は `FlankPath[FlankIdx]` へ向かい、終了は `FlankIdx >= Length(FlankPath)`（または 45 秒）。座標がアクターの Z = 20 になったほかは従来と同じ
- この L_Pind では `__ExternalActors__` を使っていないため、8 個のアクターは `L_Pind.umap` に入っている

仕様との差分：
- `[Adapt]` のログは `EndRound` の最後に出すだけで、`PickSetup` 側では出していない（プールの中身は `SetupMult` の戻り値で確認した）
- `RoundThreatA/B` はスパイクの `Report`（キュー）ではなく、1.5 秒後に処理する `ApplyEvent` で加点した（ラウンド終了の 1.5 秒前までの報告が数えられる）
- 設置の中断の「しゃがみも解く」は、`PlantTick` 内で 4 キー（`bCrouchKey` が false）のときに `UnCrouch` を毎フレーム呼ぶ形にした
- 予測移動の「交戦していない」は `State` が 1（交戦）・6（裏取り）でないこと。ミッドの判定の最初の報告は `LastRepY` が無いので予測しない

確認（PIE。ハード。体力は `inspect set_property` で 99999 に、プレイヤーは `set_transform` で移動し、入力は `simulate_input` で送った）：
- §6.1：4 を押し続けて `PlantProgress` が 0.33 まで進んだ状態で左クリック → `PlantProgress` = 0、`bPlantNeedRelease` = true（4 は押したまま。立った高さ z=98 に戻った）。左クリックを離しても 0 のまま。4 を離すと false、押し直すと 0.33 から再開した。スキルの使用経路での中断は未確認
- §6.2：セカンダリ（クラシック）だけを持った状態で `Health` を 0 にすると `Drop` が 1 回走り、武器が死んだ場所（-210, -3485, z=8）に `bDropped` = true で落ちた。次のラウンドで消えていた。プライマリがある場合の分岐、スクリーンショットは未確認
- §6.3：A に設置したラウンドの終了で `[Adapt] site=A streak=1`。次のラウンドの `SetupMult` は 8 行が [2,3,2,3,2,2,3,2]（A を厚くする行が 3）。設置せずに終わった次のラウンドでは Director の `RoundThreatA` から `[Adapt] site=A streak=2`、その次の抽選は [2,4,2,4,2,2,4,2]（A の行が 4）。B・難易度 0 の分岐は未確認
- §6.5：A 通路（-200,-3500）でプレイヤーが撃つと `[Predict] site=A` が出て、`AIController` 4 番が `Reinforce`（寄り先 (2760,-1936)）。同じラウンドの 2 回目の上限（2 回）、B 側、ミッドの Y の変化の分岐は未確認。条件が成り立っても候補の Bot が全員交戦中（State 1）だと何も起きない（ログは `PredArea` = 0 のみ）
- §6.6：`StartFlank(1)` を `call_actor_function` で呼ぶと `FlankPath` = [(-1900,0,20), (-3400,-3400,20), (-2000,-3400,20), (300,-3400,20)]（`BP_FlankPoint` の `Order` 順）になり、`FlankThink` の `MoveToLocation` が `RequestSuccessful`。その後その Bot が交戦に入ったため、経由点を順にたどって `FlankIdx` が進むところは未確認。`Side` = -1 と、`BP_FlankPoint` が無いときの従来値への戻りも未確認
- §6.4 引き返し：成立のログは取れていない。`LotOne` の `Reinforce`（引き返し）にログポイントを置き、State 4・`RProgress` < 0.5 になるよう `State` / `RDest` / `RTotal` を書き込んだ Bot を別サイトの出来事に当てようとしたが、書き込んだ Bot が見える位置にいてプレイヤーと交戦（State 1）に入る、または State が 0 に戻るなどで条件に届かなかった。コードは変えていない。自然に State 4 の Bot を作り、遅れて別サイトで撃つ形で、何回か試す必要がある
