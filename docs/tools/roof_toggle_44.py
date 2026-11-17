"""Step 44 の確認用：エディタの表示だけで A_Roof と ISM_roof を隠す／戻す（ROOF_OFF=True/False）。保存はしない（可視はコンポーネントの一時的な設定）。"""
import unreal
off = globals().get("ROOF_OFF", True)
for a in unreal.get_editor_subsystem(unreal.EditorActorSubsystem).get_all_level_actors():
    if a.get_actor_label() == "A_Roof":
        a.set_is_temporarily_hidden_in_editor(off)
    if a.get_actor_label() == "ArtHost":
        for c in a.get_components_by_class(unreal.InstancedStaticMeshComponent):
            if c.get_name() == "ISM_roof":
                c.set_visibility(not off)
print("roof off" if off else "roof on")
