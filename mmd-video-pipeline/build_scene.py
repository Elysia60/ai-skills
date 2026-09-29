"""ai-doctor 系: MMD 管线验证脚本 — 导入 PMX + VMD, 搭夜湖场景, EEVEE 渲染 MP4
用法: blender -b -P build_scene.py -- --pmx <path> --vmd <path> --out <dir> [--seconds 5] [--water]
"""
import bpy
import sys
import math
import addon_utils


def parse_args():
    argv = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []
    opts = {"pmx": None, "vmd": None, "out": "//out", "seconds": 5.0, "water": True, "res": 1280, "fps": None}
    i = 0
    while i < len(argv):
        k = argv[i].lstrip("-")
        if k in ("water",):
            opts[k] = argv[i + 1].lower() != "false"
            i += 2
        elif k == "res":
            opts[k] = int(argv[i + 1])
            i += 2
        else:
            opts[k] = argv[i + 1]
            i += 2
    return opts


def enable_mmd():
    for mod in ("bl_ext.user_default.mmd_tools", "mmd_tools"):
        try:
            addon_utils.enable(mod, default_set=True, persistent=True)
            return
        except Exception:
            continue


def main():
    opts = parse_args()
    enable_mmd()

    # 1) 导入 PMX 模型
    bpy.ops.mmd_tools.import_model(filepath=opts["pmx"], scale=0.08, clean_model=False, log_level="WARNING")
    arm = None
    for ob in bpy.context.scene.objects:
        if ob.type == "ARMATURE":
            arm = ob
    if arm is None:
        raise RuntimeError("PMX 导入后未找到骨架")
    bpy.context.view_layer.objects.active = arm
    arm.name = "MMD_Model"

    # 2) 导入 VMD 动作(作用于活动骨架)
    bpy.ops.mmd_tools.import_vmd(filepath=opts["vmd"])

    # 3) 动画范围
    fmin, fmax = 1, 2
    for fc in arm.animation_data.action.fcurves if arm.animation_data and arm.animation_data.action else []:
        if fc.keyframe_points:
            fmin = min(fmin, int(fc.keyframe_points[0].co[0]))
            fmax = max(fmax, int(fc.keyframe_points[-1].co[0]))
    scene = bpy.context.scene
    fps = 30
    start = max(fmin, 1)
    end = min(fmax, start + int(float(opts["seconds"]) * fps) - 1)
    scene.frame_start, scene.frame_end = start, end
    scene.render.fps = fps
    print(f"ANIM_RANGE: {fmin}-{fmax} -> render {start}-{end}")

    # 4) 夜湖场景
    # 清掉默认场景自带的 Cube/Light/Camera
    for name in ("Cube", "Light", "Camera"):
        ob = bpy.data.objects.get(name)
        if ob:
            bpy.data.objects.remove(ob, do_unlink=True)

    world = bpy.data.worlds.get("World") or bpy.data.worlds.new("World")
    scene.world = world
    world.use_nodes = True
    bg = world.node_tree.nodes["Background"]
    bg.inputs[0].default_value = (0.008, 0.02, 0.06, 1.0)  # 深夜蓝
    bg.inputs[1].default_value = 1.0

    # 水面: 大平面 + 深蓝反射
    bpy.ops.mesh.primitive_plane_add(size=60, location=(0, 0, 0))
    water = bpy.context.active_object
    water.name = "WaterPlane"
    mat = bpy.data.materials.new("NightWater")
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes["Principled BSDF"]
    bsdf.inputs["Base Color"].default_value = (0.006, 0.03, 0.09, 1.0)
    bsdf.inputs["Metallic"].default_value = 0.85
    bsdf.inputs["Roughness"].default_value = 0.05
    mat.node_tree.links.new(bsdf.inputs["Normal"], mat.node_tree.nodes.new("ShaderNodeTexNoise").outputs["Fac"]) if False else None
    water.data.materials.append(mat)

    # 灯光: 冷色主光 + 补光
    key = bpy.data.lights.new("Key", type="SUN")
    key.energy = 1.1
    key.color = (0.75, 0.88, 1.0)
    ko = bpy.data.objects.new("KeyLight", key)
    ko.rotation_euler = (math.radians(50), 0, math.radians(35))
    scene.collection.objects.link(ko)
    fill = bpy.data.lights.new("Fill", type="AREA")
    fill.energy = 90
    fill.color = (0.35, 0.55, 1.0)
    fill.size = 6
    fo = bpy.data.objects.new("FillLight", fill)
    fo.location = (-3, -3, 3)
    fo.rotation_euler = (math.radians(45), 0, math.radians(45))
    scene.collection.objects.link(fo)
    rim = bpy.data.lights.new("Rim", type="AREA")
    rim.energy = 150
    rim.color = (0.55, 0.75, 1.0)
    rim.size = 3
    ro = bpy.data.objects.new("RimLight", rim)
    ro.location = (2.5, 3.5, 2.2)
    ro.rotation_euler = (math.radians(-55), 0, math.radians(-140))
    scene.collection.objects.link(ro)

    # 相机: 低机位注视模型
    cam_data = bpy.data.cameras.new("Cam")
    cam_data.lens = 50
    cam = bpy.data.objects.new("Camera", cam_data)
    cam.location = (2.3, -3.6, 1.7)
    scene.collection.objects.link(cam)
    target = bpy.data.objects.new("CamTarget", None)
    target.location = (0, 0, 0.9)
    scene.collection.objects.link(target)
    con = cam.constraints.new("TRACK_TO")
    con.target = target
    scene.camera = cam

    # 5) 渲染设置: EEVEE -> MP4
    scene.render.engine = "BLENDER_EEVEE_NEXT" if hasattr(bpy.types, "RenderEngine") and "BLENDER_EEVEE_NEXT" in [e.identifier for e in bpy.types.RenderSettings.bl_rna.properties["engine"].enum_items] else "BLENDER_EEVEE"
    scene.render.resolution_x = int(opts["res"])
    scene.render.resolution_y = int(opts["res"]) * 9 // 16
    scene.render.film_transparent = False
    scene.render.image_settings.file_format = "FFMPEG"
    scene.render.ffmpeg.format = "MPEG4"
    scene.render.ffmpeg.codec = "H264"
    scene.render.ffmpeg.constant_rate_factor = "HIGH"
    scene.render.filepath = opts["out"].rstrip("/\\") + "/mmd_test.mp4"

    print("ENGINE:", scene.render.engine)
    bpy.ops.render.render(animation=True)
    print("RENDER_DONE:", scene.render.filepath)


main()
