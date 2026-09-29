---
name: mmd-video-pipeline
description: MMD出片力——不手K一帧,自动产出MMD风格角色舞蹈视频:Blender+mmd_tools导入PMX模型/VMD舞蹈动作,自动搭夜湖水面场景,EEVEE渲染直接出MP4。当用户想要"做一个MMD舞蹈视频/让角色跳舞/复刻MMD风格动画"时使用。
---

# MMD 出片力:模型+动作+渲染全自动

MMD 视频的本质是三样资产:**模型(PMX) + 舞蹈动作(VMD) + 场景**。动画不用手 K——社区现成的 VMD 动作套上去,渲染交给 EEVEE。本目录的 `build_scene.py` 已验证可一键跑通(含夜景水面灯光相机)。

## 资产清单(缺一不可)

1. **模型 .pmx**:角色 MMD 模型。渠道:模之屋 aplaybox.com(搜角色名)/BowlRoll(搜日文名)。⚠️ 多数配布有**下载密钥**,藏在发布视频简介/评论里(常见"密码见视频")
2. **舞蹈 .vmd**:标准 MMD 骨架舞蹈数据。同上渠道,搜"曲名+モーション";注意选与模型骨架匹配的动作(标准 MMD 骨架 vs 游戏改骨架)
3. **音乐 .mp3/.wav**:VMD 对应曲目的音频(合成时混入)

## 一条命令出片

```bash
blender -b -P build_scene.py -- --pmx 模型.pmx --vmd 舞蹈.vmd --out 输出目录 --fps 30
```

参数:`--seconds`(取动作前N秒) `--res`(宽度,默认1280) `--water false`(关水面) `--fps`(输出帧率)

首次使用先装 mmd_tools:从 [MMD-Blender/blender_mmd_tools](https://github.com/MMD-Blender/blender_mmd_tools/releases) 下载对应 Blender 版本的 zip,`blender --command extension install-file -r user_default xxx.zip` 安装。

## v2 优化层(对照参考片的分镜+后期)

`build_v2.py` 在基础管线上叠加五层电影感(2026-09-30 对照参考视频迭代):

1. **合成器后期链**: Glare泛光 → 夜蓝 Lift/Gamma/Gain 分级 → 对比度, EEVEE 直出电影感
2. **景深**: 相机 DOF 锁焦模型(光圈 f/2.8), 背景虚化
3. **分镜运镜**: 4 景(特写推进/中景横移/低角广角/缓拉收尾), 景内线性缓动机位 + 硬切转场 + 镜头切换变焦
4. **脚步涟漪**: 4 个相位错开的水环, 缩放扩散+透明渐隐循环
5. **假光柱**: 斜置半透明锥体 mesh, 零体积开销出舞台氛围

用法同 build_scene.py, 额外参数: `--facevmd`(表情动作) `--audio`(原曲自动混流)

## 执行规则

1. 资产下载遇密码门 → 去发布视频(B站/YouTube)简介找提取码;视频里也没有就让用户登录模之屋账号取
2. 动作套上去模型歪了/悬浮 → 先查骨架匹配:游戏改骨架模型要配"游戏骨架转MMD"的对应动作,不能拿标准骨架动作硬套
3. 渲染黑屏/报 `hide` 属性错 → 确认删除了默认场景的 Cube/Light/Camera(build_scene.py 已内置清理)
4. 想要参考视频的运镜 → 用姿态估计提取原视频骨架序列做相机轨迹,别凭空猜机位
5. 出片后对照参考视频逐秒检查:模型穿模/悬空/比例,再迭代灯光与特效(泡沫波纹→粒子系统,第二期)
