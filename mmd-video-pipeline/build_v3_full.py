"""芙宁娜 MMD 全片版 v3 — 完整舞蹈 + 相机VMD运镜
基于 build_v2.py 的夜湖场景，新增:
  - camera.vmd 导入（mmd_tools 参数自省，版本兼容）
  - 涟漪/灯光关键帧扩展到 91 秒量级
  - 高潮段灯光脉冲（30%/62% 两处）
  - --probe N: 只渲前 N 帧（骨架/物理/构图验证）
用法:
  blender -b -P build_v3_full.py -- --pmx <> --bodyvmd <> [--facevmd <>] [--camvmd <>] \
      [--audio <>] --out <> [--outname x.mp4] [--res 1280] [--fps 30] [--probe 150]
"""
import bpy
import sys
import math
import addon_utils


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"pmx": None, "bodyvmd": None, "facevmd": None, "camvmd": None,
            "audio": None, "out": "//out", "outname": "furina_full.mp4",
            "res": 1280, "fps": 30, "probe": 0}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k in opts:
            v = argv[i + 1]
            opts[k] = int(v) if k in ("res", "fps", "probe") else v
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


def lerp_keys(ob, frames_locations):
    for f, loc in frames_locations:
        ob.location = loc
        ob.keyframe_insert("location", frame=f)
    if ob.animation_data and ob.animation_data.action:
        for fc in ob.animation_data.action.fcurves:
            if fc.data_path == "location":
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"


def import_vmd_safe(filepath, **wanted):
    """mmd_tools 版本参数自省：只传该版本支持的属性"""
    props = {p.identifier for p in bpy.ops.mmd_tools.import_vmd.get_rna_type().properties}
    kwargs = {"filepath": filepath}
    for k, v in wanted.items():
        if k in props:
            kwargs[k] = v
    return kwargs


def main():
    opts = parse_args()
    enable_mmd()
    SCALE = 0.08

    # ── 模型 + 双 VMD ──
    bpy.ops.mmd_tools.import_model(filepath=opts["pmx"], scale=SCALE, clean_model=False, log_level="WARNING")
    arm = next((ob for ob in bpy.context.scene.objects if ob.type == "ARMATURE"), None)
    if not arm:
        raise RuntimeError("no armature")
    bpy.context.view_layer.objects.active = arm
    bpy.ops.mmd_tools.import_vmd(**import_vmd_safe(opts["bodyvmd"], use_camera=False, use_light=False))
    if opts.get("facevmd"):
        bpy.context.view_layer.objects.active = arm
        bpy.ops.mmd_tools.import_vmd(**import_vmd_safe(opts["facevmd"], use_camera=False, use_light=False))

    scene = bpy.context.scene
    fps = int(opts["fps"])

    # ── 相机 VMD（在算帧范围前导入，范围取身体/相机动作并集）──
    camvmd_cam = None
    if opts.get("camvmd"):
        before = set(bpy.data.objects)
        bpy.context.view_layer.objects.active = arm
        bpy.ops.mmd_tools.import_vmd(**import_vmd_safe(opts["camvmd"], scale=SCALE, use_camera=True, use_light=False))
        new_objs = set(bpy.data.objects) - before
        cams = [o for o in new_objs if o.type == "CAMERA"]
        if cams:
            camvmd_cam = cams[0]
            print("CAMERA_VMD_IMPORT:", camvmd_cam.name)
        else:
            print("CAMERA_VMD_IMPORT: no camera object created, fallback to shots")

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

    if opts["probe"] > 0:
        scene.frame_end = scene.frame_start + opts["probe"] - 1
        total = scene.frame_end - scene.frame_start + 1
        print(f"PROBE_MODE: rendering {total} frames only")

    # ── 场景基础（夜湖）──
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

    # 高潮段灯光脉冲（两处，1.5s 缓落）— rim 是 Light 数据块，keyframe 直接打在 ID 上
    rim.energy = 180
    rim.keyframe_insert("energy", frame=scene.frame_start)
    for frac in (0.30, 0.62):
        fp = scene.frame_start + int(total * frac)
        rim.energy = 330
        rim.keyframe_insert("energy", frame=fp)
        rim.energy = 180
        rim.keyframe_insert("energy", frame=fp + int(1.5 * fps))
    if rim.animation_data and rim.animation_data.action:
        for fc in rim.animation_data.action.fcurves:
            if fc.data_path == "energy":
                for kp in fc.keyframe_points:
                    kp.interpolation = "LINEAR"

    # ── 脚步涟漪: 4 个相位错开的扩散环（循环覆盖全片长度）──
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
            rb.inputs["Alpha"].default_value = 0.85
            rb.inputs["Alpha"].keyframe_insert("default_value", frame=f0)
            rb.inputs["Alpha"].default_value = 0.0
            rb.inputs["Alpha"].keyframe_insert("default_value", frame=f1)
            f += period
            k += 1
            if k > 300:
                break

    # ── 相机：优先 camera.vmd，否则 4 分镜兜底 ──
    if camvmd_cam:
        scene.camera = camvmd_cam
        print("SHOTS: camera-vmd")
    else:
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
        start, end = scene.frame_start, scene.frame_end
        span = (end - start) / 4.0
        shots = [
            (0.0, 0.45, (0.42, -1.15, 1.34), (0.5, -1.02, 1.3), 1.34, 1.3, 55),
            (0.25, 0.5, (1.3, -2.5, 1.25), (1.05, -2.75, 1.2), 1.05, 1.0, 50),
            (0.5, 0.75, (2.5, -3.1, 0.75), (2.1, -3.5, 0.7), 0.85, 0.9, 44),
            (0.75, 1.0, (0.9, -4.4, 1.6), (1.4, -3.6, 1.45), 1.0, 1.0, 58),
        ]
        for (sf, ef, c0, c1, tz0, tz1, lens) in shots:
            f0 = start + int(span * sf)
            f1 = start + int(span * ef)
            lerp_keys(cam, [(f0, c0), (f1, c1)])
            lerp_keys(target, [(f0, (0, 0, tz0)), (f1, (0, 0, tz1))])
        for (sf, ef, c0, c1, tz0, tz1, lens) in shots:
            f0 = start + int(span * sf)
            cam_data.lens = lens
            cam_data.keyframe_insert("lens", frame=f0)
        if cam_data.animation_data and cam_data.animation_data.action:
            for fc in cam_data.animation_data.action.fcurves:
                if fc.data_path == "lens":
                    for kp in fc.keyframe_points:
                        kp.interpolation = "CONSTANT"
        print("SHOTS: 4 (fallback)")

    # ── 渲染 ──
    scene.use_nodes = False
    scene.render.engine = "BLENDER_EEVEE_NEXT"
    scene.view_settings.view_transform = "Standard"
    scene.view_settings.look = "None"
    scene.display_settings.display_device = "sRGB"
    scene.render.resolution_x = int(opts["res"])
    scene.render.resolution_y = int(opts["res"]) * 9 // 16
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = opts["out"].rstrip("/\\") + "/" + opts["outname"]
    bpy.ops.render.render(animation=True)
    print("RENDER_DONE:", scene.render.filepath)
    if opts.get("audio"):
        import subprocess
        dst = scene.render.filepath.replace(".mp4", "_withmusic.mp4")
        subprocess.run(["ffmpeg", "-y", "-i", scene.render.filepath, "-i", opts["audio"],
                        "-c:v", "copy", "-c:a", "aac", "-shortest", dst], check=True)
        print("MUX_DONE:", dst)


main()
