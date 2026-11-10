# 15. 不要アセットの整理（Step 14 の削除候補と参照の調査結果）

調査日: 2026-11-10（v0.33 時点、ブランチ `step14/asset-cleanup`）。**調査のみで、アセット・ノード・変数の削除や保存は一切していない。** 削除はユーザーの承認後に別途行う。

## 1. 方針

- 削除は **ユーザーの承認後** に行う。この文書は候補と根拠の一覧で、承認された行だけを実行する。
- 削除の前に **参照元（referencers）がゼロであること** を確認する。参照が残るものは「残す」にする。
- 参照元の調べ方は次の 2 通りで、結果は一致した（抜き取りで照合）。
  - Unreal Editor の MCP（`asset.inspect_asset` の `referencers`）で、`/Game/PARORANT` 内の主な候補を確認した。
  - ディスク上の全 `.uasset` / `.umap`（`Content` 配下 678 個）の名前テーブルから `/Game/...` の文字列を拾い、被参照の一覧と、`L_Pind` / `BP_PR_GameMode` / `PARORANT` 全体からの到達範囲（推移的）を作った。ソフト参照（文字列で持つ参照）も拾える。
- Blueprint 内の未接続ノードは、`blueprint.lint_blueprint` の `unreachable` と、ノード名の全文検索で確認した（BP_PR_AIController / Bot / WeaponBase / HUD / Director / GameMode / Character / PlayerController / WBP_GameHUD / ABP_PR_Swat）。
- Git の履歴から戻せる（削除前に作業ブランチ上でコミットしておく）。ただし初回コミットのバイナリは履歴が重いので、大きな `.uasset` を戻すと `.git` は小さくならない点に注意。
- サイズは `Content` 上のファイルの実サイズ。`Content` 全体は約 771 MB。

## 2. 削除候補（アセット）

判定の意味: **削除推奨** = 参照元がゼロ（または削除する他の候補だけ）。**要判断** = 技術的には消せるが、将来の予定や参照の残り方に論点がある。**残す** = 現在使用中。

### 2.1 削除推奨（11 行・約 139 MB）

| # | 分類 | パス | 種類 | サイズ | 参照元 | 判定 | 理由 |
|---|---|---|---|---|---|---|---|
| 1 | Swat 旧版 | `Swat/V2/`（SK_Swat2、swat_fixed_Skeleton・PhysicsAsset、Body_001・Eyelashes_001・HeadGear_001） | SkeletalMesh ほか 6 個 | 19.4 MB | なし（フォルダ内の相互参照のみ） | 削除推奨 | 試作の旧版。Bot は `SK_Swat8` を使用 |
| 2 | Swat 旧版 | `Swat/V3/`（同上の構成 6 個） | 同上 | 19.4 MB | なし（相互参照のみ） | 削除推奨 | 同上 |
| 3 | Swat 旧版 | `Swat/V4/`（同上 6 個） | 同上 | 19.4 MB | なし（相互参照のみ） | 削除推奨 | 同上 |
| 4 | Swat 旧版 | `Swat/V5/`（同上 6 個） | 同上 | 19.4 MB | なし（相互参照のみ） | 削除推奨 | 同上 |
| 5 | Swat 旧版 | `Swat/V6/`（SK_Swat6、swat_v6_Skeleton・PhysicsAsset、マテリアル 3） | 同上 | 19.4 MB | なし（相互参照のみ） | 削除推奨 | 同上 |
| 6 | XBot | `Swat/XBot/`（SK_XBot、X_Bot_Skeleton、A_XBot_Death/Fire/Idle/Run/Walk、Beta_* マテリアル 2） | SkeletalMesh、Skeleton、Anim 5、Material 2 | 22.6 MB | なし（相互参照のみ） | 削除推奨 | 最初の仮 Bot。`A_XBot_Death` だけで 4.3 MB |
| 7 | V7 のマテリアル | `Swat/V7/Body_001`、`Eyelashes_001`、`HeadGear_001` | Material 3 | 約 26 KB | なし | 削除推奨 | 現行のマテリアルは `Swat/Body_001` など（`SK_Swat7`・`SK_Swat8` が参照）。V7 側のコピーは未使用 |
| 8 | Swat 初期版 | `Swat/SK_Swat`、`Swat/swat_lp_Skeleton`、`Swat/swat_lp_PhysicsAsset` | SkeletalMesh、Skeleton、PhysicsAsset | 19.4 MB | `swat_lp_*` と `SK_Swat` の相互参照のみ | 削除推奨 | 初期版。`Swat/Body_001` などのマテリアルは `SK_Swat7`・`SK_Swat8` が使うので **消さない** |
| 9 | 未使用の BS | `Swat/V7/BS_Swat_Locomotion` | BlendSpace | 6 KB | なし | 削除推奨 | 1 次元の旧ブレンド。Step 14 の元の候補には無かったが、参照ゼロ |
| 10 | 未使用のアニメ | `Rifle/A_FP_AssaultRifle_Walk_F_Loop` | AnimSequence | 139 KB | なし | 削除推奨 | 元の候補には無かったが、`ABP_PR_RifleArms` も含め参照ゼロ |
| 11 | 旧ロゴ | `UI/Textures/T_PR_LogoMark/logo_mark` | Texture | 29 KB | なし（`WBP_Title` は `T_PR_Logo` を使用） | 削除推奨 | Step 18 で正式ロゴに置き換え済み（[06_ui](06_ui.md)） |

### 2.2 要判断（6 行・約 37 MB）

| # | 分類 | パス | 種類 | サイズ | 参照元 | 判定 | 論点 |
|---|---|---|---|---|---|---|---|
| 12 | V7 旧メッシュ | `Swat/V7/SK_Swat7`、`Swat/V7/swat_v7_PhysicsAsset` | SkeletalMesh、PhysicsAsset | 19.3 MB | `swat_v7_Skeleton`・`swat_v7_PhysicsAsset` との相互参照のみ（Bot は `SK_Swat8` / `PA_Swat8`） | 要判断 | TASK.md の元の記述は「参照が残るので残す」だったが、現在 Bot は `SK_Swat8`。`swat_v7_Skeleton`（現行の骨格）のプレビューメッシュが `SK_Swat7` なので、消すとスケルトンのプレビュー表示が空になる（動作には影響しない見込み）。`SK_Swat8` を作るときの元データを残したいか |
| 13 | 旧ブレンドスペース | `Swat/V7/BS_Swat_Move2D` と `Anims/A_Swat_StrafeL`、`A_Swat_StrafeR`、`A_Swat_RunBack` | BlendSpace、AnimSequence 3 | 2.5 MB | `BS_Swat_Move2D` ← `ABP_PR_Swat`（登録上の参照）。3 アニメ ← `BS_Swat_Move2D` のみ | 要判断 | `ABP_PR_Swat` の AnimGraph が使っているのは `BS_Swat_Move2D_V2` だけ（ノードの全文検索で確認）。旧 BS への参照がどこに残っているか未特定。削除してよいか、削除時に ABP が参照中と出たら ABP を開いて旧参照を外してからコンパイルする、で進めてよいか |
| 14 | ライフル腕 | `Rifle/ABP_PR_RifleArms`、`SK_FP_Manny`（13.7 MB）、`SK_FP_Manny_Simple_Skeleton`、`MI_Manny_01`・`02`、`A_FP_AssaultRifle_Equip` / `Fire` / `Idle_Loop` / `Reload` / `Run_Loop` | ABP、SkeletalMesh、Anim 5、Material 2 | 14.7 MB | `BP_PR_Character`（`ABP_PR_RifleArms`・`SK_FP_Manny`・`A_FP_AssaultRifle_Idle_Loop`） | 要判断 | v0.16 で無効化中。TASK.md の将来対応に「ライフル腕の組み込み再挑戦」がある。再挑戦を諦めるなら Character 側のノード（`UpdateArms` など）も一緒に整理。なお `Rifle/SK_AssaultRifle` 系は使用中なので別（下の「残す」） |
| 15 | テスト用マップ | `Maps/L_Proto`（158 KB） | Level | 0.16 MB | なし（`GameDefaultMap` は `L_Pind`） | 要判断 | 旧プロトタイプ。`docs/tools/map_layout_l_proto.py` や [05_map](05_map.md) の記述が残る可能性。`L_Pind` の元になった配置データとして残すか |
| 16 | テスト用マップ | `Maps/L_Range`（外部アクターを含めて約 0.5 MB）、`Blueprints/World/BP_TargetDummy`（214 KB） | Level、Blueprint | 0.5 MB | `L_Range` ← 自身の `__ExternalActors__` / `__ExternalObjects__` のみ。`BP_TargetDummy` ← `L_Range` の外部アクターのみ | 要判断 | 射撃場。`L_Pind` や `L_Proto` が名前の文字列だけ持っている（アセットの参照としては登録されていない）。今後の武器テストに使うか |
| 17 | `Content` 外の旧ロゴ素材 | `SourceArt/Logo/logo_mark.png`、`icon_192.png`、`icon_1024.png`、`docs/tools/make_logo.py` | PNG、Python | 約 36 KB | `Content` からの参照なし（Git 管理対象） | 要判断 | [06_ui](06_ui.md) に「使わなくなったが残している（Step 14 の整理対象）」とある。`PARORANT.ico` は `PARORANT.png` とともに別用途の可能性があるので別扱い（今回は触らない前提） |

### 2.3 残す（5 行）

| # | パス | サイズ | 参照元 | 判定 | 理由 |
|---|---|---|---|---|---|
| 18 | `Rifle/SK_AssaultRifle`、`M_AssaultRifle`、`SK_AssaultRifle_Skeleton` | 3.5 MB | `BP_PR_WeaponBase`（`LoadData` の `Set Skeletal Mesh Asset`。lint でも到達可能） | 残す | TASK.md の「未使用になった」は誤り。現在も武器のメッシュとして使っている |
| 19 | `Swat/Body_001`、`Eyelashes_001`、`HeadGear_001`、`Swat/Textures/T_Swat_*`（5 枚） | 約 73 MB | `SK_Swat7`・`SK_Swat8` | 残す | Bot の見た目に使用中（テクスチャが最大。解像度を下げれば容量は減らせるが、整理の範囲外） |
| 20 | `Swat/V7/SK_Swat8`、`PA_Swat8`、`swat_v7_Skeleton` | 約 20 MB | `BP_PR_Bot`（`SK_Swat8`）、`ABP_PR_Swat`・各アニメ（骨格） | 残す | 現行の Bot |
| 21 | `Swat/V7/ABP_PR_Swat`、`A_Swat_Death` / `Fire` / `Idle` / `Run` / `Walk`、V2 系（`A_Swat_StrafeL_V2`・`StrafeR_V2`・`RunBack_V2`）、`BS_Swat_Move2D_V2` | 約 7.7 MB | `BP_PR_Bot`、`ABP_PR_Swat` | 残す | 現行のアニメ。`A_Swat_Run`・`Walk`・`Idle` は V2 の BS も使う |
| 22 | `Audio/`、`Data/`、`Input/`、`Materials/`、`UI/`、`Knife/`、`Blueprints/` の残り全部（`Maps/L_Pind` を含む） | 約 14 MB（Blueprints 9.3 MB、UI 3.2 MB、Audio 0.5 MB、Knife 0.6 MB ほか） | `BP_PR_GameMode`、`L_Pind`、DataTable ほか | 残す | 参照ゼロのものは無かった（`T_PR_LogoMark/logo_mark` のみ上記 #11） |

### 2.4 まとめ

| 判定 | 行数 | 合計サイズ |
|---|---|---|
| 削除推奨 | 11 行（アセット約 49 個） | 約 139 MB |
| 要判断 | 6 行（アセット約 30 個、`Content` 外 4 ファイル含む） | 約 37 MB |
| 残す（候補にあったもの・念のため確認したもの） | 5 行 | — |

削除推奨のうち、`Swat/V2`〜`V6`、`XBot`、`SK_Swat` で 138 MB。要判断のうち、`SK_Swat7`（19.3 MB）とライフル腕（14.7 MB）で 34 MB。

## 3. Blueprint 内の未接続ノード・未使用変数

ノードの ID（GUID の先頭）は lint の結果から。削除時は ID で探すと確実。

### 3.1 削除推奨（11 行）

| # | BP | 関数・グラフ | ノードや変数 | 判定 | 補足 |
|---|---|---|---|---|---|
| B1 | `BP_PR_AIController` | `EngageSeen` | 旧 `Stop Movement`（`2EDA8100…`） | 削除推奨 | Step 11 の置き換えで残った |
| B2 | `BP_PR_AIController` | `EngageMove` | 旧 `Add Movement Input` ×2（`79E1E8E6…`、`FABB62E9…`） | 削除推奨 | B3 で関数ごと消すなら不要 |
| B3 | `BP_PR_AIController` | `EngageMove` 関数そのもの | 呼び出し元ゼロ（全文検索で `Engage Move` は関数の入口の 1 件のみ） | 削除推奨 | Step 16 の再設計後は使っていない。削除前に再検索して確認 |
| B4 | `BP_PR_AIController` | `Think` | `Call Rotate`（`4837C33E…`）以降の未接続ノード | 削除推奨 | Step 17 で Director の抽選に置き換え済み |
| B5 | `BP_PR_AIController` | `CallRotate` 関数 | 呼び出しは B4 の未接続ノードだけ | 削除推奨 | B4 と同時に。他の BP（Director など）からの呼び出しが無いことを再確認 |
| B6 | `BP_PR_Bot` | `EventGraph`（`Die` 付近） | 旧ラグドール用 `Set Collision Profile Name`（`E5208141…`）と、続く `Set Simulate Physics` | 削除推奨 | 現在は `A_Swat_Death` を再生 |
| B7 | `BP_PR_WeaponBase` | `EventGraph` | 旧・簡易振りの `Set Relative Rotation`（`50CE6A9E…`）と前後の未接続ノード | 削除推奨 | [03_combat](03_combat.md) にも「未使用が残存」と記載あり |
| B8 | `BP_PR_HUD` | `EventGraph` | 未接続の `Draw Text`（`B2887A87…`）、`Count Enemies` 呼び出し（`0EDD29FA…`）、`Draw Banner` 呼び出し（`85D2127F…`） | 削除推奨 | Step 20 で `WBP_GameHUD` に切り替えて切り離したもの |
| B9 | `BP_PR_HUD` | `DrawMatchInfo` | 未接続の `Draw Text` ×2（`45455945…`、`E41152A5…`）と `ブランチ`（`670444E0…`） | 削除推奨 | 旧スコア・体力・弾数・敵数・購入案内の描画の残り |
| B10 | `BP_PR_Director` | `Report` と `EventGraph` | `PendTime` / `PendArea` / `PendPts` / `PendKind` / `PendLoc` の `Get` ノードと、つながっていない `配列を作成` ×5（`Report` 内に確認）、変数 5 個 | 削除推奨 | `Set` は無く、出力先が未接続（`Report` の中身を読んで確認）。先にノードを消してから変数を消す。[12_macro_ai](12_macro_ai.md) の「古い `Pend*` は未使用のまま」に該当 |
| B11 | `BP_PR_GameMode` | `MatchTick` | 未接続の `Get Current Level Name`（`076AEE86…`）以降 | 削除推奨 | 元の候補には無かった |

### 3.2 要判断（4 行）

| # | BP | 関数・グラフ | ノードや変数 | 判定 | 論点 |
|---|---|---|---|---|---|
| B12 | `BP_PR_HUD` | `CountEnemies` 関数、変数 `EnemyAlive` | B8 で呼び出しを消すと参照ゼロになる見込み | 要判断 | 関数ごと消すか、旧 HUD を丸ごと別途整理するか |
| B13 | `BP_PR_HUD` | `DrawBanner` 関数 | 呼び出しは B8 の未接続ノードのみ（全文検索で確認） | 要判断 | 「結果文字（ROUND WIN など）は残した」と [13_hud_difficulty](13_hud_difficulty.md) にあるため、別の場所で描画しているなら消してよいが、画面での確認が要る |
| B14 | `BP_PR_HUD` | `DrawEconomy` 関数 | 呼び出しは生きている（lint でも未接続なし） | 要判断 | 今も所持金などを描いているか。`WBP_GameHUD` と二重表示になっていないか PIE で確認してから |
| B15 | `BP_PR_Character` | `PickupNearby` の `ブランチ`（`61E48918…`）、`SpawnWeapon` の `Attach Actor To Component`（`86337CC5…`）、`UpdateArms` の `ブランチ`（`1352F752…`） | 未接続 | 要判断 | ライフル腕の無効化（#14）や武器拾いの変更の残り。#14 の結論と一緒に決める。lint の `unguarded_read`（`UpdateArms`）も同じ関数 |

### 3.3 対象外

- lint の `unguarded_read`（Is Valid 未チェック）と `random_fanout`（`SetupMacro` の乱数）は、整理ではなく品質改善なので、このステップでは触らない。
- Director の `Pend*` と HUD の `EnemyAlive` 以外の **未使用変数の網羅確認は未実施**。必要なら別途、変数ごとに参照を調べる。

## 4. テンプレート・素材フォルダの使用状況（参考）

`PARORANT`（`L_Pind`、`BP_PR_GameMode`、`PARORANT` 内の全アセット）から、参照を辿って（推移的に）たどり着く範囲で判定した。サイズは `du` による `Content` 上の値。**削除提案は控えめ**で、丸ごと不要なフォルダは無かった。

| フォルダ | サイズ（du） | 使用範囲（アセット数・サイズ） | 分類 | 主な使用元・メモ |
|---|---|---|---|---|
| `FPWeapon` | 34 MB | 18 / 20 個、28.1 / 34.3 MB | 使用中 | `BP_PR_WeaponBase`（`SK_FPGun`、`FirstPersonTemplateWeaponFire02`）。未到達は 2 個、約 6 MB |
| `FirstPerson` | 9.7 MB | 8 / 15 個、0.3 / 9.8 MB | 一部使用 | `BP_PR_Character` が `BP_FirstPersonCharacter` を参照、`IMC_PR` / `DT_KeyBinds` が `IA_Look` / `IA_Jump` を参照。マップ `FirstPersonMap` などテンプレートの残りは未使用 |
| `FirstPersonArms` | 138 MB | 39 / 40 個、140.7 / 141.0 MB | 使用中 | `SK_Mannequin_Arms`・`FP_*` アニメ。ナイフ用の腕（`ABP_PR_KnifeArms`）経由 |
| `Knife_FPS_Animations` | 289 MB | 81 / 144 個、約 244 / 295 MB | 一部使用 | `ABP_PR_KnifeArms`・`BP_PR_Character`・`BP_PR_WeaponBase` が `SKM_Hands`・`SKM_Knife`・ナイフのアニメを参照。未使用は `Demo` のマップ（`L_FirstPerson`、`L_Overview`）、`Props` など約 50 MB |
| `LP_FPSLite_JC` | 0.6 MB | 5 / 19 個 | 一部使用 | `L_Pind`（`SM_Box_01`、`SM_Building_01`、`SM_Wall_01`） |
| `LP_LiteWeapons_JC` | 1.4 MB | 7 / 27 個 | 一部使用 | `BP_PR_WeaponBase`（`SM_Weapon_01`・`02`、`SM_SciFi_Weapons_01`） |
| `LevelPrototyping` | 0.3 MB | 2〜8 / 13 個（`L_Pind` 基準で 2、`L_Range`・`L_Proto` を含めると 8） | 一部使用 | `BP_PlantZone`・`BP_SpawnBarrier`・`MI_Bot_*`（`MI_Solid_Blue`、`M_Solid`）。テストマップを消すと使用範囲が減る |
| `Weapons_Free` | 5.3 MB | 3 / 20 個、1.4 / 5.4 MB | 一部使用 | `BP_PR_WeaponBase`（`SM_pistol_001`） |

メモ:
- 容量の大半は `Knife_FPS_Animations`（289 MB）・`FirstPersonArms`（138 MB）・`PARORANT/Swat`（260 MB）。今回の削除推奨（139 MB）は `PARORANT/Swat` の旧版が中心で、素材フォルダは **使用中のため触らない** のが安全。
- 素材フォルダの「未使用の一部」を消す場合は、パック内の依存が複雑なので、別のステップで 1 フォルダずつ参照ビューアを見ながら行うのがよい（今回の提案には含めない）。
- `FirstPerson` の `BP_FirstPersonCharacter` は `BP_PR_Character` から参照されているが、使い方（親クラス・未使用の定数など）は未確認。

## 5. 削除の手順案

承認された行だけを、次の順で行う。各段階で確認し、問題が出たら Git で戻す。

1. **準備**: ブランチ `step14/asset-cleanup` のまま、`L_Pind.umap` などの未コミットの変更は先にコミットするか退避する。Editor を起動し、全 BP がコンパイルできる状態にする。
2. **Blueprint の整理（§3 の削除推奨・承認分）**: ノード → 関数 → 変数の順（`Pend*` は先にノード）。1 BP ごとにコンパイルして警告が減ったか確認する。
3. **参照ゼロのアセット（#7、#9、#10、#11）**: 小さいものから。削除前に参照ビューアで再確認する。
4. **Swat の旧版（#1〜#5、#6、#8）**: フォルダごとに削除（`SK_Swat` の削除で `Swat/Body_001` などが道連れにならないことを確認）。リダイレクタが残ったら「リダイレクタを修正」を実行。
5. **要判断の行（#12〜#17、B12〜B15）**: 承認された分だけ、同じ手順で。#13 は ABP の旧参照を確認してから。
6. **削除後の確認**:
   - 全 BP のコンパイルがエラー・新しい警告なし（`BP_PR_Bot`、`AIController`、`Director`、`GameMode`、`Character`、`WeaponBase`、`HUD`、`WBP_*`、`ABP_PR_Swat`、`ABP_PR_KnifeArms`）。
   - PIE で 1 ラウンド（購入 → 戦闘 → スパイク設置・解除 → 結果）を通し、Bot の歩き・走り・撃ち・死亡のアニメと、武器のメッシュ・サウンドが変わらない。
   - ログ（Output Log）にエラーなし（`Accessed None`、アセット読み込み失敗がない）。
   - Git の差分で、削除されたファイルが計画どおりか確認してからコミット（`Delete 不要アセットを削除` などの種別 `Delete`）。
7. **ドキュメントの更新**: `docs/TASK.md` の Step 14 のチェックを更新し、`docs/06_ui.md`・`03_combat.md`・`04_enemy_ai.md`・`12_macro_ai.md` の「Step 14 で整理」の記述を更新する。`docs/README.md` の状態の行と `08_roadmap.md` の残タスクも合わせる。

## 6. 実行結果（2026-11-10、ユーザー承認済みの §2.1 #1〜#11 と §3.1 B1〜B11 のみ）

要判断（#12〜#17、B12〜B15）、「残す」、§4 の素材フォルダには触れていない。

### 6.1 消したもの

| 区分 | 内容 |
|---|---|
| アセット | 48 個（`Swat/V2`〜`V6` 各 6 個、`Swat/XBot` 9 個、`Swat/SK_Swat` と `swat_lp_*` 3 個、`Swat/V7/Body_001`・`Eyelashes_001`・`HeadGear_001`、`BS_Swat_Locomotion`、`A_FP_AssaultRifle_Walk_F_Loop`、`T_PR_LogoMark/logo_mark`）。コミット `5d218c1` |
| サイズ | `Content/PARORANT` 292 MB → 153 MB、`Content` 全体 771 MB → 632 MB（約 139 MB 減） |
| Blueprint | B1〜B11。コミット `f1db3d1`。`EngageMove` と `CallRotate` は呼び出し元ゼロを全文検索で確認してから `remove_function` で削除（呼び出しが残っていれば拒否される） |

削除は `asset.delete`（参照が残るものは消さない設定）で行い、削除前に全 `uasset` の名前テーブルからも参照ゼロを再確認した（想定外の参照元なし）。

### 6.2 調査時の想定との違い

- B7（`WeaponBase` の旧・簡易振り）は未接続の `Set Relative Rotation` 1 個ではなく、`Delay` と `Set Relative Rotation` が 2 段つながった鎖と、その `Get WeaponMesh` だった。鎖ごと消した。
- B8 では `Draw Economy` の呼び出しノードも、未接続の鎖（旧スコア文字 → 旧ヘルプ文字 → `Draw Economy`）の途中にあり、他から到達できなかったので一緒に消した。`DrawEconomy` 関数本体は残している（B14、要判断）。つまり B14 の「呼び出しは生きている」は誤りで、実際は呼び出しも未接続だった。
- B8・B9 で消したノードの引数用の純粋ノード（`Append`、`To String`、`Select`、数式、変数の `Get` など）が使われなくなって残ったので、読まれていないものだけを繰り返し消した（`BP_PR_HUD` の `EventGraph` と `DrawMatchInfo`）。
- B10 の変数 5 個は、ノード（`配列を作成` 11 個）を先に消したあと `remove_variable` で消した（一緒に消えた `Get` ノードは 10 個で、いずれも出力先なし）。
- 未使用の純粋ノードで、今回の削除と関係なく前から残っていたもの（`BP_PR_HUD` の `Get Current Spread`・`Get CX`・`To Float` ×4、`BP_PR_Director` の `To Float` ×3、`BP_PR_Bot` の `Get WeaponPoint`）は範囲外なので残した。動作には影響しない。

### 6.3 確認結果

| 項目 | 結果 |
|---|---|
| 消えたこと | 全文検索で `Engage Move`・`Call Rotate`・`Pend` は 0 件。lint（`unreachable`）は `AIController`・`Bot`・`WeaponBase`・`HUD`・`Director`・`GameMode` で 0 件 |
| コンパイル | `/Game/PARORANT` の Blueprint 27 個を全部コンパイル：失敗 0、エラー 0。警告は元からあるもの（音の減衰なし、`random_fanout`、`unguarded_read` など。新しい警告なし） |
| PIE | イージー相当ではなく既定のノーマルで確認。タイトルが表示される（新しいロゴあり）→ `bSkipTitle` を true にして `open L_Pind` で試合へ。購入フェーズ → 戦闘 → ラウンド終了（スコア 0:1）→ 次ラウンドの購入フェーズまで進んだ。Bot（SWAT）がライフルを持って立っているのを画面で確認。`TakeWeaponDamage` で Bot を倒し、HUD の敵の数が 3 → 2 に減った |
| ログ | `Saved/Logs/PARORANT.log` に `Accessed None`、`LogScript` エラー、削除したアセット（`SK_Swat`・`XBot`・`swat_lp`・`logo_mark`・`BS_Swat`・`A_Swat` など）の読み込み失敗なし。出ていたエラーは、タイトルの `InputMode:UIOnly` の 1 件（以前からある）のみ |

### 6.4 確認できなかったこと

- Bot の歩き・走り・撃ち・死亡アニメを動きとして目視していない（立ち姿とライフルは画面で確認、死亡はノードが動いて敵の数が減ることまで）。アニメ本体（`A_Swat_*`、`BS_Swat_Move2D_V2`）は今回消していない。
- 設置・解除、リザルト画面（「もう一度」「タイトルへ」）は通していない（ラウンドは時間切れまたは被弾で終わった）。
- チート U は押していない（キー入力ができないため）。
- 編集中に Unreal Editor が 1 回クラッシュ（PIE の開始・終了時の `WBP_Title` の GC ensure のあとに access violation）。BP の削除はその前にすべて保存済みで、再起動後もコンパイルと lint は通った。今回の削除との関係は未調査（PIE を繰り返し開始・終了すると起きる既知の挙動の可能性）。
- Editor が複数のセッションから同時に操作されていたらしく、PIE が勝手に開始・終了して削除が拒否される場面があった（PIE を止めた直後に削除すると通った）。
