# Step 38c: 紹介画面の間だけ隠す物にタグ IntroHide を付ける（L_Canal）。再実行しても同じ結果。
# - アクタ：A_Roof（A サイトの元からある屋根）
# - ArtHost のコンポーネント：ISM_roof（マップの中の建物の屋根）
# GameMode の SetIntroHide(bHide) が、タグ IntroHide のアクタとコンポーネントの表示を切り替える。
import unreal

TAG = unreal.Name("IntroHide")
HIDE_ISM = ("ISM_roof",)
HIDE_ACTORS = ("A_Roof",)

actors = unreal.EditorLevelLibrary.get_all_level_actors()
for a in actors:
    lab = a.get_actor_label()
    if lab in HIDE_ACTORS:
        tags = list(a.tags)
        if TAG not in tags:
            tags.append(TAG)
            a.tags = tags
        print("actor tagged", lab)
    if lab == "ArtHost":
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            print("ArtHost ISM", c.get_name(), c.get_instance_count())
            if c.get_name() in HIDE_ISM:
                ct = list(c.component_tags)
                if TAG not in ct:
                    ct.append(TAG)
                    c.component_tags = ct
                print("component tagged", c.get_name())
unreal.EditorLoadingAndSavingUtils.save_dirty_packages(True, True)
