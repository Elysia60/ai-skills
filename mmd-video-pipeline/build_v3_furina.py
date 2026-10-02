"""芙宁娜×萝莉神レクイエム MMD 二期 — 色彩剧本 + 水花爆发 + 舞台光 + 分镜
用法: blender -b -P build_v3_furina.py -- --pmx <> --bodyvmd <> --facevmd <> --audio <> --out <>
色彩剧本(12.4s, 371帧@30fps):
  0-60f   深夜蓝(安静)      60-105f 亮起过渡(灯能量脉冲)
  105-210 舞台白光(光柱在位) 210-270 水花爆发+高潮
  270-330 粉紫梦境转场       330-371 深蓝收尾
"""
import bpy
import sys
import math
import random
import addon_utils


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"pmx": None, "bodyvmd": None, "facevmd": None, "audio": None,
            "out": "//out", "res": 1280, "fps": 30}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k in opts:
            opts[k] = argv[i + 1]
            i += 2
        else:
            i += 1
    return opts


def enable_mmd():
    for mod in ("bl_ext.user_default.mmd_tools", "mmd_tools"):
        try:
            addon_utils.enable(mod, default_set=True, persistent=True)
            return
        except Exception:
            continue


def data_keys(db, prop, values_frames):
    for f, v in values_frames:
        setattr(db, prop, v)
        db.keyframe_insert(prop, frame=f)


def kframe(node_socket, values_frames, linear=True):
    for f, v in values_frames:
        node_socket.default_value = v
        node_socket.keyframe_insert("default_value", frame=f)
    if not linear and node_socket.id_data.animation_data:
        for fc in node_socket.id_data.animation_data.action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "CONSTANT"


def obj_loc_keys(ob, frames_locations, interp="CONSTANT"):
    for f, loc in frames_locations:
        ob.location = loc
        ob.keyframe_insert("location", frame=f)
    if interp == "CONSTANT" and ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            if fc.data_path == "location":
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"


def main():
    opts = parse_args()
    enable_mmd()
    scene = bpy.context.scene
    fps = int(opts["fps"])

    # 1) 模型 + 双 VMD
    bpy.ops.mmd_tools.import_model(filepath=opts["pmx"], scale=0.08, clean_model=False, log_level="WARNING")
    arm = next((ob for ob in scene.objects if ob.type == "ARMATURE"), None)
    if not arm:
        raise RuntimeError("no armature")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.mmd_tools.import_vmd(filepath=opts["bodyvmd"])
    if opts.get("facevmd"):
        bpy.context.view_layer.objects.active = arm
        bpy.ops.mmd_tools.import_vmd(filepath=opts["facevmd"])

    fmin, fmax = 1, 2
    if arm.animation_data and arm.animation_data.action:
        for fc in arm.animation_data.action.fcurves:
            if fc.keyframe_points:
                fmin = min(fmin, int(fc.keyframe_points[0].co[0]))
                fmax = max(fmax, int(fc.keyframe_points[-1].co[0]))
    scene.frame_start, scene.frame_end = max(fmin, 1), fmax
    scene.render.fps = fps
    F0, F1 = scene.frame_start, scene.frame_end
    total = F1 - F0 + 1
    print(f"ANIM_RANGE: {fmin}-{fmax} ({total} frames, {total/fps:.1f}s)")

    def T(sec):  # 秒 → 帧
        return F0 + int(sec * fps)

    # 2) 清默认 + 水面(颜色带剧本关键帧)
    for name in ("Cube", "Light", "Camera"):
        ob = bpy.data.objects.get(name)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    wbg = world.node_tree.nodes["Background"]

    bpy.ops.mesh.primitive_plane_add(size=70, location=(0, 0, 0))
    water = bpy.context.active_object
    wmat = bpy.data.materials.new("ScriptWater")
    wmat.use_nodes = True
    wb = wmat.node_tree.nodes["Principled BSDF"]
    wb.inputs["Metallic"].default_value = 0.85
    wb.inputs["Roughness"].default_value = 0.05
    # 色彩剧本: 水面颜色/亮度跟段走
    kframe(wb.inputs["Base Color"], [
        (F0, (0.004, 0.02, 0.07, 1)),          # 深夜蓝
        (T(2.0), (0.006, 0.03, 0.09, 1)),
        (T(3.2), (0.05, 0.12, 0.28, 1)),        # 亮起
        (T(4.2), (0.02, 0.08, 0.20, 1)),        # 舞台
        (T(8.8), (0.03, 0.10, 0.24, 1)),        # 高潮
        (T(10.4), (0.10, 0.10, 0.20, 1)),       # 粉紫梦境
        (F1, (0.02, 0.05, 0.12, 1)),            # 深蓝收尾
    ])
    water.data.materials.append(wmat)

    # 3) 灯组(能量带剧本)
    key = bpy.data.lights.new("Key", type="SUN")
    key.color = (0.78, 0.9, 1.0)
    ko = bpy.data.objects.new("KeyLight", key)
    ko.rotation_euler = (math.radians(52), 0, math.radians(30))
    scene.collection.objects.link(ko)
    data_keys(key, "energy", [  # 世界亮度剧本(深夜→爆亮→稳→暖收)
        (F0, 0.9), (T(2.0), 1.1), (T(3.0), 2.6), (T(3.6), 1.4),
        (T(7.0), 1.5), (T(10.4), 1.2), (F1, 0.8),
    ])
    fill = bpy.data.lights.new("Fill", type="AREA")
    fill.color = (0.4, 0.6, 1.0)
    fill.size = 6
    fo = bpy.data.objects.new("FillLight", fill)
    fo.location = (-3, -3, 3)
    fo.rotation_euler = (math.radians(45), 0, math.radians(45))
    scene.collection.objects.link(fo)
    data_keys(fill, "energy", [(F0, 90), (T(3.0), 260), (T(4.0), 120), (T(8.8), 150), (T(10.4), 200), (F1, 110)])
    rim = bpy.data.lights.new("Rim", type="AREA")
    rim.color = (0.55, 0.75, 1.0)
    rim.size = 3
    ro = bpy.data.objects.new("RimLight", rim)
    ro.location = (2.5, 3.2, 2.3)
    ro.rotation_euler = (math.radians(-55), 0, math.radians(-140))
    scene.collection.objects.link(ro)
    data_keys(rim, "energy", [(F0, 150), (T(3.0), 320), (T(4.2), 180), (T(10.4), 260), (F1, 160)])

    # 4) 舞台光柱(高处置+低强度, 3.2s 后淡入)
    shaft_mat = bpy.data.materials.new("StageShaft")
    shaft_mat.use_nodes = True
    snt = shaft_mat.node_tree
    snt.nodes.clear()
    sout = snt.nodes.new("ShaderNodeOutputMaterial")
    sem = snt.nodes.new("ShaderNodeEmission")
    sem.inputs[0].default_value = (0.6, 0.78, 1.0, 1.0)
    trans = snt.nodes.new("ShaderNodeBsdfTransparent")
    smix = snt.nodes.new("ShaderNodeMixShader")
    smix.inputs[0].default_value = 0.96
    snt.links.new(sem.outputs[0], smix.inputs[1])
    snt.links.new(trans.outputs[0], smix.inputs[2])
    snt.links.new(smix.outputs[0], sout.inputs[0])
    shaft_mat.blend_method = "BLEND"
    for sx, rot in ((-1.8, 24), (0.2, 2), (2.0, -20)):
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.45, radius2=1.6, depth=10,
                                        location=(sx, 2.2, 4.2),
                                        rotation=(math.radians(rot + 70), 0, 0))
        sh = bpy.context.active_object
        sh.name = f"Shaft{sx}"
        sh.data.materials.append(shaft_mat)
        sh.visible_shadow = False
        sh.scale = (1, 1, 1)
        sh.keyframe_insert("scale", frame=T(3.0))
        sh.scale = (0.01, 0.01, 0.01)
        sh.keyframe_insert("scale", frame=T(3.0) - 1)  # 出现前隐藏
        sh.scale = (1, 1, 1)
        sh.keyframe_insert("scale", frame=T(3.4))
        sh.keyframe_insert("scale", frame=F1)

    # 5) 水花爆发 @T(7.0): 36 水珠抛物线 + 冲击环
    burst_f = T(7.0)
    drop_mat = bpy.data.materials.new("SplashDrop")
    drop_mat.use_nodes = True
    db = drop_mat.node_tree.nodes["Principled BSDF"]
    db.inputs["Base Color"].default_value = (0.55, 0.85, 1.0, 1.0)
    db.inputs["Emission Color"].default_value = (0.5, 0.85, 1.0, 1.0)
    db.inputs["Emission Strength"].default_value = 3.0
    db.inputs["Roughness"].default_value = 0.1
    random.seed(42)
    g = 9.8
    dt = 0.12
    for di in range(36):
        ang = random.uniform(0, 2 * math.pi)
        spd = random.uniform(1.6, 3.2)
        vx, vy = math.cos(ang) * spd * 0.55, math.sin(ang) * spd * 0.35
        vz = random.uniform(1.8, 3.4)
        r = random.uniform(0.02, 0.05)
        bpy.ops.mesh.primitive_uv_sphere_add(segments=10, ring_count=8, radius=r,
                                             location=(0, 0, 0.06))
        drop = bpy.context.active_object
        drop.name = f"Drop{di}"
        drop.data.materials.append(drop_mat)
        frames, locs = [], []
        t = 0.0
        for step in range(7):
            f = burst_f + int(t * fps)
            x = vx * t
            y = -0.15 * t
            z = 0.06 + vz * t - 0.5 * g * t * t
            if z < 0.005:
                z = 0.005
            frames.append(f)
            locs.append((x, y, max(z, 0.005)))
            t += dt
        obj_loc_keys(drop, list(zip(frames, locs)), interp="LINEAR")
        drop.visible_shadow = False
    # 冲击环(爆发帧)
    bpy.ops.mesh.primitive_torus_add(major_radius=0.3, minor_radius=0.02, location=(0, 0, 0.05))
    ring = bpy.context.active_object
    ring.name = "BurstRing"
    rmat = bpy.data.materials.new("BurstRingM")
    rmat.use_nodes = True
    rb = rmat.node_tree.nodes["Principled BSDF"]
    rb.inputs["Emission Color"].default_value = (0.6, 0.9, 1.0, 1.0)
    rb.inputs["Emission Strength"].default_value = 4.0
    rb.inputs["Alpha"].default_value = 0.9
    rmat.blend_method = "BLEND"
    ring.data.materials.append(rmat)
    for f, s in ((burst_f, 0.3), (burst_f + 8, 1.1), (burst_f + 16, 2.2)):
        ring.scale = (s, s, s)
        ring.keyframe_insert("scale", frame=f)
    ring.visible_shadow = False

    # 6) 脚步涟漪(沿用 v2, 相位错开)
    for ri in range(4):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.22, minor_radius=0.006,
                                         location=(0, 0, 0.015))
        ripple = bpy.context.active_object
        ripple.name = f"Ripple{ri}"
        rip_mat = bpy.data.materials.new(f"RippleM{ri}")
        rip_mat.use_nodes = True
        rpb = rip_mat.node_tree.nodes["Principled BSDF"]
        rpb.inputs["Base Color"].default_value = (0.5, 0.8, 1.0, 1.0)
        rpb.inputs["Emission Color"].default_value = (0.4, 0.75, 1.0, 1.0)
        rpb.inputs["Emission Strength"].default_value = 2.2
        rpb.inputs["Alpha"].default_value = 0.0
        rip_mat.blend_method = "BLEND"
        ripple.data.materials.append(rip_mat)
        phase = F0 + int(ri * 0.3 * fps)
        period = int(1.25 * fps)
        f = phase
        guard = 0
        while f < F1 + period and guard < 30:
            f1 = f + int(0.7 * fps)
            ripple.scale = (0.15, 0.15, 0.15)
            ripple.keyframe_insert("scale", frame=f)
            ripple.scale = (2.1, 2.1, 2.1)
            ripple.keyframe_insert("scale", frame=f1)
            rpb.inputs["Alpha"].default_value = 0.85
            rpb.inputs["Alpha"].keyframe_insert("default_value", frame=f)
            rpb.inputs["Alpha"].default_value = 0.0
            rpb.inputs["Alpha"].keyframe_insert("default_value", frame=f1)
            f += period
            guard += 1
        ripple.visible_shadow = False

    # 7) 分镜相机(对齐色彩剧本段)
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 50
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = 2.2
    cam_data.dof.aperture_fstop = 2.8
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    target = bpy.data.objects.new("CamTarget", None)
    scene.collection.objects.link(target)
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    scene.camera = cam
    cam_shots = [
        (F0, T(2.0), (0.4, -1.1, 1.35), (0.45, -1.0, 1.32), 1.34, 1.3, 55),   # 特写(夜)
        (T(2.0), T(4.2), (1.3, -2.4, 1.3), (1.0, -2.7, 1.25), 1.1, 1.05, 50),  # 中景(亮起)
        (T(4.2), T(9.0), (2.6, -3.0, 0.85), (2.0, -3.4, 0.8), 0.9, 0.95, 46),  # 低角(舞台+爆发)
        (T(9.0), F1 + 1, (0.8, -4.3, 1.7), (1.5, -3.5, 1.55), 1.0, 1.0, 58),   # 缓拉(粉紫收)
    ]
    for (f0, f1, c0, c1, tz0, tz1, lens) in cam_shots:
        obj_loc_keys(cam, [(f0, c0), (f1, c1)], interp="LINEAR")
        obj_loc_keys(target, [(f0, (0, 0, tz0)), (f1, (0, 0, tz1))], interp="LINEAR")
        cam_data.lens = lens
        cam_data.keyframe_insert("lens", frame=f0)
    if cam_data.animation_data and cam_data.animation_data.action:
        for fc in cam_data.animation_data.action.fcurves:
            if fc.data_path == "lens":
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"

    # 8) 渲染 + 混流
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.render.resolution_x = int(opts["res"])
    scene.render.resolution_y = int(opts["res"]) * 9 // 16
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = opts["out"].rstrip("/\\") + "/furina_lolikami_v3.mp4"
    bpy.ops.render.render(animation=True)
    print("RENDER_DONE:", scene.render.filepath)
    if opts.get("audio"):
        import subprocess
        dst = scene.render.filepath.replace(".mp4", "_withmusic.mp4")
        subprocess.run(["ffmpeg", "-y", "-i", scene.render.filepath, "-i", opts["audio"],
                        "-c:v", "copy", "-c:a", "aac", "-shortest", dst], check=True)
        print("MUX_DONE:", dst)


main()
