# 30. 開発者用のマップ選択（Step 43）

2026-11-16、ユーザーの指示「開発者モードとして、タイトル画面で M ボタンを押すとマップが選べる選択肢が出てくるようにして」。

## 1. 仕様

### 1.1 操作

- タイトル画面で **M キー**を押すと、マップ選択のパネルが開く。もう一度 M を押すと閉じる。
- パネルの選択肢は「ランダム」と、`BP_PR_GameInstance.MapList` にあるマップ（今は CANAL、PIND）。マップを足したら選択肢も増えるように、`MapList` から作る。
- 選択肢を押すと、その内容に決まり、パネルが閉じる。
  - マップを選ぶ：`BP_PR_GameInstance.DebugMap` にそのマップを入れる（固定）。
  - 「ランダム」：`DebugMap` を空にする（抽選に戻る）。
- パネルには、今の選択（ランダム／固定中のマップ名）が分かる表示を出す。
- 固定中は、タイトル画面の隅に小さく「DEV マップ固定：PIND」のように出す。ランダムのときは何も出さない。

### 1.2 範囲と決めごと

- 開発者用なので、タイトル画面に M キーの案内は出さない。README にも書かない。
- exe（Shipping）でも使える。
- 固定は保存しない。アプリを起動し直すとランダムに戻る（`DebugMap` の既定値は空のまま）。セーブデータには触らない。
- 固定中は「プレイ」も「もう一度」も固定したマップを開く（`PickMap` が `DebugMap` を見る今の動きのまま）。「タイトルへ」で戻っても固定は続く。
- 設定画面、キー設定の画面などタイトル以外の画面が開いている間は、M キーに反応しない（キーの割り当てで M を押したときに開かないこと）。
- 抽選の履歴（`LastMap`、`SameMapCount`）の扱いは今の `PickMap` のまま変えない。

### 1.3 実装の方針

- `WBP_Title` に、パネルを開閉する関数 `ToggleDevMap` と、選択を反映する関数 `SetDevMap(Map)`、表示を更新する関数 `UpdateDevMapLabel` を作る。キーを使わずに関数を直接呼んで確かめられるようにする。
- M キーの受け取り方は、タイトル画面の入力モードに合った方法を選ぶ（キー設定画面でのキーの受け取り方が先例）。ボタンを押したあとでも効くこと。
- 見た目は既存のタイトル・設定画面の部品と色に合わせる。

## 2. 確認

- `ToggleDevMap` で開閉、`SetDevMap` で `DebugMap` が変わる、表示が変わる。
- 固定して `PickMap` を 20 回 → すべて固定したマップ。ランダムに戻して 200 回 → 両方出て、同じマップは 3 回続かない。
- PIE で固定 → 試合開始 → 固定したマップが開く。
- Blueprint のコンパイル失敗 0。終了時に `DebugMap` の既定値は空、`bSkipTitle` は false、セーブデータは変わっていない。

## 3. 結果

### 3.1 実装した内容（Step 43、Sonnet、2026-11-16、ブランチ `step43/dev-map-select`）

**追加・変更した資産**

| 資産 | 内容 |
|---|---|
| `WBP_DevMapItem`（新規、`UI/`） | 選択肢 1 個ぶん（ルートは SizeBox 300×40、中に Button `Btn` と文字 `Lbl`）。変数 `ItemMap`（Name）・`ItemLabel`（Text）は「スポーン時に公開」。`Construct` で `Lbl` に `ItemLabel` を入れる。クリックでイベントディスパッチャー `OnPicked(Map)` を呼ぶ |
| `WBP_Title` | ウィジェット `DevPanel`（Border、最初は Collapsed。中に `DevHeader`・`DevNow`・`DevList`）と、隅の `DevBadge`（最初は Collapsed）。変数 `LabelKey`。関数 `ToggleDevMap`、`UpdateDevMapLabel`、`DevMapLabel`（→ Label）、`CanUseDevKey`（→ Allowed）、`OnKeyDown`（上書き）。カスタムイベント `SetDevMap(Map)`、`AddDevItem(Map)`、`OnDevPick(Map)`。`Construct` の最後で `AddDevItem(None)`（= ランダム）→ `MapList` の各要素ごとに `AddDevItem` → `UpdateDevMapLabel`。クラスの `bIsFocusable` を true に。`Tick` に、フォーカスを戻す処理 |
| `BP_PR_GameInstance` | 変数 `MapNames`（Map<Name, String>、既定 L_Canal → CANAL、L_Pind → PIND）を追加。それ以外は変えていない（`DebugMap` の既定は空、`bSkipTitle` は false のまま） |

**M キーの受け取り方**：タイトルは `ShowTitle` が `Set Input Mode UI Only`（フォーカスは `WBP_Title`）で出している。UI Only ではプレイヤーコントローラーのキー入力は届かないので、`WBP_Title` 自身の `OnKeyDown`（`UserWidget` の上書き）で受ける。ボタンをクリックしてフォーカスがボタンに移っても、ボタンが処理しないキーはキーイベントの経路を上がって `WBP_Title` の `OnKeyDown` に来る。`OnKeyDown` は「キーが M、かつ押しっぱなしの繰り返しではない、かつ `CanUseDevKey` が true」のときだけ `ToggleDevMap` を呼んで Handled を返し、それ以外は Unhandled。`bIsFocusable` が false だと起動直後のフォーカスが空振りするため true にした（作業前は false で、ログに「Non-Focusable widget」のエラーが出ていた）。

**他の画面が開いている間は効かない仕組み**：`CanUseDevKey` が `BP_PR_PlayerController.MenuWidget`（設定・キー設定の画面）が有効かを見て、有効なら false を返す。さらに、設定画面は別のウィジェットがフォーカスを持つので、そもそも `WBP_Title` にキーが来ない（キー設定の `InputKeySelector` が M を受け取る間も開かない）。設定画面を閉じるとフォーカスが空になるため、`Tick` で「`CanUseDevKey` が true で、`WBP_Title` もその子もフォーカスを持たない」ときだけ `SetKeyboardFocus(self)` する（設定画面が開いている間は戻さない）。選択肢を押してパネルを閉じたときも同じ理由で `SetKeyboardFocus` する。

**表示名の元（1 か所）**：`BP_PR_GameInstance.MapNames`。タイトル画面ではレベルが開いていないので `MapInfo.MapName` は読めないため、「マップ → 表示名」の対応をここに 1 か所だけ持たせた。マップの表示名を変えるとき（CANAL → PACENT など）は、`MapInfo.MapName` と、この `MapNames` の値の 2 か所を直す（この Step では名前は変えていない）。`MapNames` に無いマップは、レベル名から `L_` を取って大文字にした名前で出す。`MapList` にマップを足すと、選択肢が自動で増える（`Construct` で `MapList` から作る）。

**作りの上の決めごと（外れたところ）**
- `SetDevMap` はカスタムイベント（関数ではない）。このツール経由で作った「入力ピンを持つ関数」は、ノードの更新（`refresh_blueprints` など）でピンが消えてコンパイルエラーになることが分かったため、入力を持つ関数は作らず、カスタムイベント（`SetDevMap`、`AddDevItem`）と、公開変数（スポーン時に公開）、変数 `LabelKey` を使う形にした。`DevMapLabel` は入力なし（`LabelKey` を読む）。呼び出しは名前でできる。
- 選択肢のボタンは `WBP_DevMapItem`（子のウィジェット）を `MapList` から実行時に作る（要望どおり）。

### 3.2 確認結果（PIE、エディタ。`docs/tools/dev_map_check_43.py`、ログは `Saved/art43/`）

| 項目 | 結果 |
|---|---|
| 起動直後 | `DebugMap` 空、パネルと隅の表示は非表示、`DevNow` は「現在：ランダム」、選択肢 3 個（ランダム・CANAL・PIND）、`WBP_Title` はキーボードフォーカスを持つ |
| `ToggleDevMap` | 開く（Visible）→ 閉じる（Collapsed）→ 開く、の順に切り替わる |
| `SetDevMap(L_Pind)` | `DebugMap` = L_Pind、パネルは閉じる、`DevNow` は「現在：PIND」、隅は「DEV マップ固定：PIND」（表示あり）、フォーカスは `WBP_Title` に残る |
| `PickMap` | 固定（L_Pind）20 回 → L_Pind 20。固定（L_Canal）20 回 → L_Canal 20。`SetDevMap(None)` で隅の表示が消え、200 回 → L_Canal 96・L_Pind 104（別の実行では 104・96）、同じマップの最長連続は 2 |
| 表示名の元 | PIE 中に `MapNames` の L_Canal を PACENT に変えて `SetDevMap(L_Canal)` すると、隅が「DEV マップ固定：PACENT」、`DevNow` が「現在：PACENT」。すぐ CANAL に戻した（保存していない）。レベル名からの直書きではないことの確認 |
| 他の画面 | `OpenMenu` の前 `CanUseDevKey` = true、開いている間 = false（このときタイトルはフォーカスを持たない）、`CloseMenu` の後 = true で、`Tick` が数フレームのうちにフォーカスを戻した（`has_keyboard_focus` = true） |
| `OnPlay` | 固定 L_Canal → `OnPlay` → 開いたマップは L_Canal（L_Pind のエディタ PIE から）。固定 L_Pind → `OnPlay` → L_Pind（**L_Pind の PIE から L_Pind を開き直しただけ**。別のマップから開いたものではない）。どちらも `DebugMap` は固定のまま、`bSkipTitle` は true になる（プレイ後の通常の動き） |
| 画像 | `docs/images/step43_title_panel.png`（パネルを開いたタイトル）、`step43_title_pinned.png`（PIND 固定中の隅の表示）。どちらもエディタの画面ごと（`Shot ShowUI`） |
| コンパイル | `Content/PARORANT` の Blueprint 40 個、失敗 0（新しい `WBP_DevMapItem` を含む） |
| 終了時の設定 | `DebugMap` の既定値は空、`bSkipTitle` は false（CDO を読んだ）。レベル（L_Canal、L_Pind）は編集していない |

### 3.3 未確認・注意

- **実際の M キーは未確認**（PIE にキー入力を送れないため）。`OnKeyDown` の中身と、フォーカスが `WBP_Title` に届いていること（`has_keyboard_focus`）は確認したが、キーを押して開く動きそのものは、ユーザーの確認待ち。ボタンをクリックした後（フォーカスがボタンにある状態）で M が効くかも、実際には試していない。
- 選択肢のボタンを実際にクリックして `DebugMap` が変わる動きも、PIE にクリックを送れないため未確認（`SetDevMap` の直接呼び出しと、選択肢が 3 個できていること、画像での見た目は確認）。
- パネルの見た目は控えめにしたが、タイトルの中央に重なる（Bot の強さの行の上）。色・位置はユーザーの確認待ち。
- exe（Shipping）では未確認（ビルドしていない）。
- `Saved/SaveGames/PR_Sens.sav` が、確認中に `OpenMenu`（設定画面の表示で感度などが保存される）で書き換わった。中身（難易度 0 など）は読み込めるが、作業前のバイト列は控えていないため、値が同じだったかは断定できない。他の 3 つのセーブは作業前後でハッシュが同じ。

