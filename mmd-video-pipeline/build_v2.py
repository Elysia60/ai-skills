"""芙宁娜 MMD v2 — 对照参考片优化版
新增: 合成器后期链(泛光+夜蓝分级) / 景深 / 脚步涟漪 / 景内运镜 / 假光柱
用法: blender -b -P build_v2.py -- --pmx <> --bodyvmd <> --facevmd <> --audio <> --out <>
"""
import bpy
import sys
import math
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


def constant_keys(ob, frames_locations):
    for f, loc in frames_locations:
        ob.location = loc
        ob.keyframe_insert("location", frame=f)
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            if fc.data_path == "location":
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"


def lerp_keys(ob, frames_locations):
    """线性插值关键帧 — 景内运镜"""
    for f, loc in frames_locations:
        ob.location = loc
        ob.keyframe_insert("location", frame=f)
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            if fc.data_path == "location":
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"


def main():
    opts = parse_args()
    enable_mmd()

    # ── 模型 + 双 VMD ──
    bpy.ops.mmd_tools.import_model(filepath=opts["pmx"], scale=0.08, clean_model=False, log_level="WARNING")
    arm = next((ob for ob in bpy.context.scene.objects if ob.type == "ARMATURE"), None)
    if not arm:
        raise RuntimeError("no armature")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.mmd_tools.import_vmd(filepath=opts["bodyvmd"])
    if opts.get("facevmd"):
        bpy.context.view_layer.objects.active = arm
        bpy.ops.mmd_tools.import_vmd(filepath=opts["facevmd"])

    scene = bpy.context.scene
    fps = int(opts["fps"])
    fmin, fmax = 1, 2
    if arm.animation_data and arm.animation_data.action:
        for fc in arm.animation_data.action.fcurves:
            if fc.keyframe_points:
                fmin = min(fmin, int(fc.keyframe_points[0].co[0]))
                fmax = max(fmax, int(fc.keyframe_points[-1].co[0]))
    scene.frame_start, scene.frame_end = max(fmin, 1), max(fmax, 2)
    scene.render.fps = fps
    total = scene.frame_end - scene.frame_start + 1
    print(f"ANIM_RANGE: {fmin}-{fmax} ({total} frames)")

    # ── 场景基础 ──
    for name in ("Cube", "Light", "Camera"):
        ob = bpy.data.objects.get(name)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)
    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    world.node_tree.nodes["Background"].inputs[0].default_value = (0.008, 0.02, 0.06, 1.0)

    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    water = bpy.context.active_object
    wmat = bpy.data.materials.new("NightWater")
    wmat.use_nodes = True
    wb = wmat.node_tree.nodes["Principled BSDF"]
    wb.inputs["Base Color"].default_value = (0.005, 0.025, 0.08, 1.0)
    wb.inputs["Metallic"].default_value = 0.9
    wb.inputs["Roughness"].default_value = 0.035
    water.data.materials.append(wmat)

    key = bpy.data.lights.new("Key", type="SUN")
    key.energy = 1.3
    key.color = (0.78, 0.9, 1.0)
    ko = bpy.data.objects.new("KeyLight", key)
    ko.rotation_euler = (math.radians(52), 0, math.radians(30))
    scene.collection.objects.link(ko)
    fill = bpy.data.lights.new("Fill", type="AREA")
    fill.energy = 120
    fill.color = (0.4, 0.6, 1.0)
    fill.size = 6
    fo = bpy.data.objects.new("FillLight", fill)
    fo.location = (-3, -3, 3)
    fo.rotation_euler = (math.radians(45), 0, math.radians(45))
    scene.collection.objects.link(fo)
    rim = bpy.data.lights.new("Rim", type="AREA")
    rim.energy = 180
    rim.color = (0.55, 0.75, 1.0)
    rim.size = 3
    ro = bpy.data.objects.new("RimLight", rim)
    ro.location = (2.5, 3.2, 2.3)
    ro.rotation_euler = (math.radians(-55), 0, math.radians(-140))
    scene.collection.objects.link(ro)

    # ── 假光柱(斜置半透明长锥) ──
    shaft_mat = bpy.data.materials.new("LightShaft")
    shaft_mat.use_nodes = True
    nt = shaft_mat.node_tree
    nt.nodes.clear()
    outn = nt.nodes.new("ShaderNodeOutputMaterial")
    em = nt.nodes.new("ShaderNodeEmission")
    em.inputs[0].default_value = (0.55, 0.72, 1.0, 1.0)
    em.inputs[1].default_value = 1.6
    trans = nt.nodes.new("ShaderNodeBsdfTransparent")
    mix = nt.nodes.new("ShaderNodeMixShader")
    mix.inputs[0].default_value = 0.92  # 92% 透明
    nt.links.new(em.outputs[0], mix.inputs[1])
    nt.links.new(trans.outputs[0], mix.inputs[2])
    nt.links.new(mix.outputs[0], outn.inputs[0])
    shaft_mat.blend_method = "BLEND"
    for sx, sz, rot in ((-2.2, 1.2, 26), (1.8, 1.5, -18)):
        bpy.ops.mesh.primitive_cone_add(vertices=16, radius1=0.7, radius2=1.9, depth=9,
                                        location=(sx, 1.5, sz), rotation=(math.radians(rot + 68), 0, 0))
        shaft = bpy.context.active_object
        shaft.name = f"Shaft{sx}"
        shaft.data.materials.append(shaft_mat)
        shaft.visible_shadow = False

    # ── 脚步涟漪: 4 个相位错开的扩散环 ──
    for ri in range(4):
        bpy.ops.mesh.primitive_torus_add(major_radius=0.22, minor_radius=0.006,
                                         location=(0, 0, 0.015))
        ring = bpy.context.active_object
        ring.name = f"Ripple{ri}"
        rmat = bpy.data.materials.new(f"RippleM{ri}")
        rmat.use_nodes = True
        rnt = rmat.node_tree
        rb = rnt.nodes["Principled BSDF"]
        rb.inputs["Base Color"].default_value = (0.5, 0.8, 1.0, 1.0)
        rb.inputs["Emission Color"].default_value = (0.4, 0.75, 1.0, 1.0)
        rb.inputs["Emission Strength"].default_value = 2.2
        rb.inputs["Alpha"].default_value = 0.0
        rmat.blend_method = "BLEND"
        ring.data.materials.append(rmat)
        # 相位循环: 每 1.25s 一个周期, 环间隔 0.3s
        phase = scene.frame_start + int(ri * 0.3 * fps)
        period = int(1.25 * fps)
        f = phase
        k = 0
        while f < scene.frame_end + period:
            f0, f1 = f, f + int(0.7 * fps)
            ring.scale = (0.15, 0.15, 0.15)
            ring.keyframe_insert("scale", frame=f0)
            ring.scale = (2.1, 2.1, 2.1)
            ring.keyframe_insert("scale", frame=f1)
            # alpha 0.9 -> 0
            rb.inputs["Alpha"].default_value = 0.85
            rb.inputs["Alpha"].keyframe_insert("default_value", frame=f0)
            rb.inputs["Alpha"].default_value = 0.0
            rb.inputs["Alpha"].keyframe_insert("default_value", frame=f1)
            f += period
            k += 1
            if k > 40:
                break

    # ── 分镜相机: 每景内带缓动运镜, 硬切转场 ──
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 50
    cam_data.dof.use_dof = True
    cam_data.dof.focus_distance = 2.2
    cam_data.dof.aperture_fstop = 2.8  # 明显景深
    cam = bpy.data.objects.new("Camera", cam_data)
    scene.collection.objects.link(cam)
    target = bpy.data.objects.new("CamTarget", None)
    scene.collection.objects.link(target)
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    scene.camera = cam

    # 分镜: [起点帧, 机位起, 机位终, 目标z起, 目标z终, lens]
    start, end = scene.frame_start, scene.frame_end
    span = (end - start) / 4.0
    shots = [
        (0.0, 0.45, (0.42, -1.15, 1.34), (0.5, -1.02, 1.3), 1.34, 1.3, 55),   # 特写推进
        (0.25, 0.5, (1.3, -2.5, 1.25), (1.05, -2.75, 1.2), 1.05, 1.0, 50),    # 中景横移
        (0.5, 0.75, (2.5, -3.1, 0.75), (2.1, -3.5, 0.7), 0.85, 0.9, 44),      # 低角广角
        (0.75, 1.0, (0.9, -4.4, 1.6), (1.4, -3.6, 1.45), 1.0, 1.0, 58),       # 收尾缓拉
    ]
    for (sf, ef, c0, c1, tz0, tz1, lens) in shots:
        f0 = start + int(span * sf)
        f1 = start + int(span * ef)
        lerp_keys(cam, [(f0, c0), (f1, c1)])
        lerp_keys(target, [(f0, (0, 0, tz0)), (f1, (0, 0, tz1))])
    # 镜头切换时硬切焦距
    for (sf, ef, c0, c1, tz0, tz1, lens) in shots:
        f0 = start + int(span * sf)
        cam_data.lens = lens
        cam_data.keyframe_insert("lens", frame=f0)
    if cam_data.animation_data and cam_data.animation_data.action:
        for fc in cam_data.animation_data.action.fcurves:
            if fc.data_path == "lens":
                for kp in fc.keyframe_points:
                    kp.interpolation = "CONSTANT"
    print("SHOTS:", len(shots))

    # ── 合成器后期链: 泛光 + 夜蓝分级 ──
    scene.use_nodes = True
    scene.render.use_compositing = True
    nt = scene.node_tree
    nt.nodes.clear()
    rl = nt.nodes.new("CompositorNodeRLayers")
    glare = nt.nodes.new("CompositorNodeGlare")
    glare.glare_type = "BLOOM"
    glare.quality = "MEDIUM"
    glare.threshold = 1.0
    glare.size = 8
    cb = nt.nodes.new("CompositorNodeColorBalance")
    cb.correction_method = "LIFT_GAMMA_GAIN"
    # 夜蓝电影分级: 阴影偏蓝、高光微青
    cb.lift = (0.88, 0.95, 1.10)
    cb.gamma = (0.94, 1.0, 1.08)
    cb.gain = (0.92, 1.0, 1.10)
    con_node = nt.nodes.new("CompositorNodeBrightContrast")
    try:
        con_node.inputs[1].default_value = 0.12
    except Exception:
        pass
    comp = nt.nodes.new("CompositorNodeComposite")
    nt.links.new(rl.outputs[0], glare.inputs[0])
    nt.links.new(glare.outputs[0], cb.inputs[0])
    nt.links.new(cb.outputs[0], con_node.inputs[0])
    nt.links.new(con_node.outputs[0], comp.inputs[0])

    # ── 渲染 + 混流 ──
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.render.resolution_x = int(opts["res"])
    scene.render.resolution_y = int(opts["res"]) * 9 // 16
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = opts["out"].rstrip("/\\") + "/furina_v2.mp4"
    bpy.ops.render.render(animation=True)
    print("RENDER_DONE:", scene.render.filepath)
    if opts.get("audio"):
        import subprocess
        dst = scene.render.filepath.replace(".mp4", "_withmusic.mp4")
        subprocess.run(["ffmpeg", "-y", "-i", scene.render.filepath, "-i", opts["audio"],
                        "-c:v", "copy", "-c:a", "aac", "-shortest", dst], check=True)
        print("MUX_DONE:", dst)


main()
