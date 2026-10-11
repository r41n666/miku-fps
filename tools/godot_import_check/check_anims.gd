# Godot 导入验证脚本 · miku-fps
# 用法: Godot_v4.7.2-stable_win64_console.exe --headless --path <proj> --script res://check_anims.gd
# 输出: 动画列表 / 骨骼数 / 世界包围盒（验证导入是否成功、动作是否齐全、朝向尺寸是否合理）
extends SceneTree


func _initialize() -> void:
	print("###GODOT_IMPORT_CHECK### start")
	for f in ["res://miku_anim6.glb", "res://miku_anim6.fbx"]:
		if not FileAccess.file_exists(f):
			print("###FILE_MISSING### ", f)
			continue
		var res = load(f)
		if res == null:
			print("###LOAD_FAIL### ", f)
			continue
		var inst = res.instantiate()
		# global_transform / 蒙皮求值需要节点在场景树内（否则报 !is_inside_tree）
		get_root().add_child(inst)
		print("###INSTANTIATED### ", f)
		_collect(inst, f)
		get_root().remove_child(inst)
		inst.free()
	quit(0)


func _collect(node: Node, tag: String) -> void:
	var aps := []
	_find(node, "AnimationPlayer", aps)
	if aps.is_empty():
		print("###NO_ANIMPLAYER### ", tag)
	for ap in aps:
		var anims: PackedStringArray = ap.get_animation_list()
		print("###ANIMS### ", tag, " count=", anims.size(), " => ", anims)
	var skels := []
	_find(node, "Skeleton3D", skels)
	for sk in skels:
		print("###SKELETON### ", tag, " bones=", sk.get_bone_count(),
			" name=", sk.name)
		# 骨骼 rest 位置 = 最可靠的「尺度 / 朝向 / 重心」证据
		for bn in ["head_49", "hips_106", "toes.L_96", "hand.L_66"]:
			var bi: int = sk.find_bone(bn)
			if bi >= 0:
				print("###BONE_REST### ", tag, " ", bn, " = ",
					sk.get_bone_global_rest(bi).origin)
	# 世界包围盒（网格 AABB 角点变换并集；对蒙皮网格偏保守，仅作参考）
	var mn := Vector3(1e9, 1e9, 1e9)
	var mx := Vector3(-1e9, -1e9, -1e9)
	var meshes := []
	_find(node, "MeshInstance3D", meshes)
	for mi in meshes:
		var aabb: AABB = mi.get_aabb()
		for i in range(8):
			var w: Vector3 = mi.global_transform * aabb.get_endpoint(i)
			mn = mn.min(w)
			mx = mx.max(w)
	if mn.x < 1e8:
		print("###WORLD_AABB### ", tag, " min=", mn, " max=", mx,
			" size=", mx - mn, " meshes=", meshes.size())
	# 动作回放抽样：walk 动作驱动骨骼的真实性验证
	if aps.size() > 0 and skels.size() > 0:
		var ap: AnimationPlayer = aps[0]
		var sk2: Skeleton3D = skels[0]
		var wn := ""
		for n in ap.get_animation_list():
			if n.ends_with("MKI_walk_n_rifle"):
				wn = n
		if wn != "":
			var anim: Animation = ap.get_animation(wn)
			_dump_anim(anim, tag)
			# 轨道路径解析检查：track path 相对 AnimationPlayer.root_node 解析
			var rn: Node = ap.get_node_or_null(ap.root_node)
			var pth := str(anim.track_get_path(0))
			var node_part := pth.split(":")[0]
			var resolved: Node = rn.get_node_or_null(node_part) if rn != null else null
			print("###AP_ROOT### ", tag, " player=", ap.get_path(),
				" root_node=", ap.root_node, " resolved_root=", rn != null,
				" track0_node=", node_part, " resolved=", resolved != null)
			var fi: int = sk2.find_bone("toes.L_96")
			var hi: int = sk2.find_bone("head_49")
			ap.play(wn)
			# seek(…, true) 立即生效，不依赖帧推进。
			# 判定标准用「多骨骼 pose 旋转变化」——global pose 在 headless
			# 下依赖 process 帧的缓存刷新，不作为判据。
			var probe := ["upper_leg.L_100", "lower_leg.L_99",
				"upper_arm.L_68", "hips_106", "toes.L_96"]
			var idxs := []
			for bn in probe:
				idxs.append(sk2.find_bone(bn))
			ap.seek(0.0, true)
			var rot0 := []
			for i in idxs:
				rot0.append(sk2.get_bone_pose_rotation(i) if i >= 0 else Quaternion.IDENTITY)
			ap.seek(0.35, true)
			var rot1 := []
			for i in idxs:
				rot1.append(sk2.get_bone_pose_rotation(i) if i >= 0 else Quaternion.IDENTITY)
			ap.seek(0.7, true)
			var rot2 := []
			for i in idxs:
				rot2.append(sk2.get_bone_pose_rotation(i) if i >= 0 else Quaternion.IDENTITY)
			var total := 0.0
			for k in range(probe.size()):
				var d1: float = rad_to_deg(rot0[k].angle_to(rot1[k]))
				var d2: float = rad_to_deg(rot1[k].angle_to(rot2[k]))
				total += d1 + d2
				print("###POSE_ROT### ", tag, " ", probe[k],
					" 0->0.35: %.2f°  0.35->0.7: %.2f°" % [d1, d2])
			print("###ANIM_DRIVEN### ", tag, " sum_rotation_delta=%.2f°" % total)
			var f0: Vector3 = sk2.get_bone_global_pose(idxs[4]).origin if idxs[4] >= 0 else Vector3.ZERO
			print("###ANIM_MOVED### ", tag, " (参考) foot0_origin=", f0)
			ap.stop()


func _dump_anim(anim: Animation, tag: String) -> void:
	print("###ANIM_INFO### ", tag, " tracks=", anim.get_track_count(),
		" length=", anim.length, " loops=", anim.loop_mode)
	var shown := 0
	for ti in range(anim.get_track_count()):
		var p := str(anim.track_get_path(ti))
		if ti < 4:
			print("###TRACK_PATH### ", tag, " [", ti, "] ", p,
				" type=", anim.track_get_type(ti))
		if p.contains("lower_leg") or p.contains("upper_arm") or p.contains("leg"):
			var kc := anim.track_get_key_count(ti)
			var extra := ""
			if kc >= 2 and anim.track_get_type(ti) == Animation.TYPE_ROTATION_3D:
				var q0 = anim.track_get_key_value(ti, 0)
				var q1 = anim.track_get_key_value(ti, kc / 2)
				extra = " ang0->mid=%.4f rad" % q0.angle_to(q1)
			print("###TRACK_SAMPLE### ", tag, " ", p, " keys=", kc, extra)
			shown += 1
			if shown >= 4:
				break


func _find(node: Node, cls: String, out: Array) -> void:
	if node.is_class(cls):
		out.append(node)
	for c in node.get_children():
		_find(c, cls, out)
