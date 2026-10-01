---
name: mmd-video-pipeline
description: MMD出片力——Blender+mmd_tools自动产出角色舞蹈视频：PMX模型+VMD动作+夜湖场景+分镜运镜+EEVEE渲染出MP4。含参考片逐段拆解法、VMD真实性校验、踩坑实录。当用户想要"做MMD舞蹈视频/让角色跳舞/复刻MMD风格动画"时使用。
---

# MMD 出片力：从参考片到成片的完整工艺

## 〇、先定性：两种作品，两条路线

拿到参考视频**先看片尾字幕**，定性决定路线：

| 类型 | 特征 | 路线 |
|---|---|---|
| **VMD 翻跳型** | 使用现成舞蹈动作数据配布，字幕常写"Motion: 某配布者" | 本管线主战场：模型+VMD+场景自动渲染 |
| **手作动画型** | 字幕写 "Animation: 作者本人"（如参考片灶天cartoooo） | 动作层是手工 K 帧的，自动管线不碰；但场景/灯光/FX/后期/色彩剧本层完全可复刻 |

**定性案例**：芙宁娜《Wild Hearts Never Die》片（84.5s, 1280x640@24fps）——字幕 Model: Mihoyo / Rigging: 小风 / Animation+FX: 灶天cartoooo / Music: Sayonara Wild Hearts OST。手作型。

## 一、参考片逐段拆解（拆片是学制作的第一步）

**参考片母本**：`C:\Users\14676\Desktop\素材视频\d1e8d36d9d02bbbb7a36ac563705429a.mp4`（芙宁娜《Wild Hearts Never Die》，84.5s, 1280x640@24fps）。学制作用 ffmpeg 抽帧逐张看：

用 `ffmpeg -ss T -i 参考.mp4 -frames:v 1 抽帧.jpg` 每隔 8-12 秒抽帧逐张看，按"时间段/画面/技法"记表：

| 时间 | 画面 | 技法 |
|---|---|---|
| 0-8s | 戴手套的手捧发光水珠 | 开场道具特写，发光物=全场唯一光源，浅景深 |
| 8-18s | 帽子/服装细节插入镜 | 细节特写攒期待，不先露全身 |
| 18s | 脚踏上木栈桥，桥下水光 | 引入舞台，涟漪环预告"水面舞台" |
| 20-40s | 夜湖水面独舞全景 | 深夜蓝环境光，脚步发光涟漪+水花，水面倒影 |
| ~42s | 水花大爆发 | 白色 FX burst 卡音乐节点 |
| 45-60s | 光柱舞台高潮 | 体积光束+舞台圆环+水珠粒子+雾 |
| 60-70s | 侧脸特写 | 色板切换：粉紫梦境+bokeh 气泡 |
| 70-80s | 俯瞰"水族箱" | 水上发光水灵环绕，水焦散 |
| 80s+ | 黑屏字幕 | 署名 Model/Rigging/Animation/FX/合成/Music |

**核心心得——色彩剧本**：全片色板"暗夜蓝→爆白→亮舞台→粉紫→深蓝→黑"跟音乐结构走。特效不是堆的，是叙事节拍。复刻时先抄这张表再动手。

## 二、制作流程（十条，按序执行）

1. **资产三件套**：模型 .pmx / 舞蹈 .vmd / 音乐。渠道：模之屋 aplaybox.com、BowlRoll（bowlroll.net，仅社交账号登录）。⚠️ 配布大多带**下载密钥**，藏在发布视频简介/评论；B 站"密码见视频"就得看视频
2. **验 VMD 真实时长**（见坑 1 代码），顺手验 camera.vmd 是否为空（见坑 2）
3. **骨架匹配探针**：`--probe 150` 先渲 150 帧看骨架/裙摆物理/构图，再全量
4. **场景**：夜湖 = 世界背景 (0.008,0.02,0.06) + 水面 Metallic 0.9/Roughness 0.035/深蓝 + 三灯（Sun 主光冷白 1.3 + 两盏蓝 Area 补/轮廓）
5. **相机**：camera.vmd 有货就用（mmd_tools import_vmd 自省参数导入，找 type==CAMERA 的新对象设 scene.camera）；空则 4 分镜兜底（特写推进/中景横移/低角广角/缓拉，TRACK_TO + 线性缓动 + 镜头切换硬切焦距）
6. **FX 三件套**：脚步涟漪 = 发光 torus 环（Emission 2.2 + Alpha 0.85→0 动画，4 环相位错开 0.3s 循环扩散）；水花爆发/粒子/体积光 = 二期（粒子系统 + volumetric）
7. **渲染**：EEVEE_NEXT + view_transform Standard + H264 CRF HIGH，1280x720@30
8. **后期**：ffmpeg 泛光/分级/暗角要克制（有过曝白帧事故，见坑 10）
9. **混音**：`--audio` 自动 mux（`-c:v copy -c:a aac -shortest`）
10. **对照检查**：抽帧和参考片并排看，穿模/悬空/比例逐项过

## 三、踩坑实录（每条都真炸过，必读）

1. **VMD 记录数 ≠ 时长**！解析帧号跨度才算数：
```python
import struct
d = open("motion.vmd","rb").read()
n = struct.unpack_from("<I", d, 50)[0]          # 记录数（2728 条≠91秒！）
nums = [struct.unpack_from("<I", d, 54+15+i*111)[0] for i in range(n)]
print(min(nums), max(nums), (max(nums)-min(nums))/30, "s")  # 实测 0..412 = 13.7s DanceCut
```
2. **camera.vmd 可以是 0 记录空文件**——导入前解析 offset 50 的记录数，为 0 直接走分镜兜底
3. **Light 数据块没有 `.data` 属性**：`bpy.data.lights.new()` 返回的就是数据块，`rim.data.energy` 直接 AttributeError，写 `rim.energy`
4. **Blender 日志 stdout 有缓冲乱序**：重定向到文件时 print 和 Traceback 顺序会颠倒，grep 时序会骗人，以 Traceback 行号为真相
5. **默认 Cube 挡镜头**：删 Cube/Light/Camera 三件（脚本内置）
6. **mmd_tools 扩展两条安装路径**（blender_org / user_default）都要试；退出时 unregister 报错是无害噪音
7. **工厂设置重置会吞已装插件**，重置后重装 mmd_tools
8. **mmd_tools import_vmd 参数随版本变**：用 `bpy.ops.mmd_tools.import_vmd.get_rna_type().properties` 自省，只传支持的参数
9. **骨架匹配**：游戏改骨架模型（如某些原神模型）要配对应转换的动作；标准 MMD 骨架动作互套一般安全（芙宁娜×兔洞/萝莉摇均验证通过）
10. **后期 grade 别过**：v2 曾把整帧拉成白屏（v2e 事故），饱和度/对比度增量 ≤10%
11. **VMD 模型名字段是 Shift-JIS**，zip 内文件名常 cp437 双重编码，读取用 `zipfile` 后 `.encode('cp437').decode('shift_jis')`
12. 配乐是版权曲目（本例 DECO*27 / 游戏 OST）不要网上乱抓，让主人提供文件再 mux

## 四、参数速查（build_v3_full.py，已真机验证）

```bash
blender -b -P build_v3_full.py -- --pmx 模型.pmx --vmd 动作.vmd \
  [--facevmd 表情.vmd] [--camvmd 相机.vmd] [--audio 配乐.mp3] \
  --out 输出目录 [--outname x.mp4] [--res 1280] [--fps 30] [--probe 150]
```
- `--probe N` 只渲前 N 帧验证；全量渲 413 帧 ≈ 4 分钟（RTX 4060 EEVEE）
- 源码：`C:\Users\14676\.zcode\skills\mmd-video-pipeline\build_v3_full.py`

## 五、已验证样例（对照学习用）

| 成片 | 内容 | 位置 |
|---|---|---|
| furina-rabbithole-v3.mp4 | 芙宁娜×兔洞 13.8s 完整舞段，夜湖四分镜 | C:\Users\14676\Videos\MMD\ |
| furina-lolikami-dance.mp4 | 芙宁娜×萝莉摇 12.1s 含音乐 | 同上 |
| rabbithole-dance-full.mp4 | 初音×兔洞 13.5s | 同上 |
| pipeline-demo-miku.mp4 | 初音管线首验 0.8s | 同上 |

## 六、二期路线（向参考片质量的差距）

- 水花爆发：粒子系统 + 卡点触发（参考片 42s 那种 burst）
- 体积光柱舞台：volumetric scattering 或假光锥 mesh 阵列
- 色彩剧本：分场景关键帧化（粉紫梦境段、俯瞰段）
- 水焦散 + 发光水灵环绕
- 转场：硬切之外加闪白/涟漪转场

## 七、出师自测（学会的验收标准）

首次走本管线前先答这 6 道决策题，**6/6 全对才算学会**；答错的回看对应小节后再答一遍。不要跳过——每道题都对应一次真实事故。

1. VMD 二进制 offset 50 读出 **2728 条记录**，帧号范围 0..412（30fps）。这条舞蹈实际时长多少秒？（→ 坑 1）
2. `camera.vmd` 解析出来是 **0 条记录**，下一步怎么走？（→ 坑 2）
3. 灯脉冲动画要给灯打能量关键帧，代码写 `rim.data.energy` 还是 `rim.energy`？（→ 坑 3）
4. 主人说"做个 MMD 舞蹈视频"，在渲全量片之前**必须先完成哪两步**？（→ 流程 2/3）
5. 拿到一支参考视频，第一步看什么？由此分出哪两条制作路线？（→ 〇）
6. 全片渲完混音完，最后一步做什么？（→ 流程 10）

<details>
<summary>答案（先自己答完再看）</summary>

1. **13.7 秒**。帧号跨度 412/30 才是真实时长；2728/30≈91s 是记录数幻影。
2. **跳过相机导入，走 4 分镜兜底**（特写推进/中景横移/低角广角/缓拉），不要对着空文件 import。
3. **`rim.energy`**。`bpy.data.lights.new()` 返回的就是数据块，没有 `.data`，写错直接 AttributeError。
4. ① 解析 VMD 真实帧号跨度（顺便验 camera.vmd 是否为空）；② `--probe 150` 渲 150 帧验证骨架/裙摆物理/构图。
5. **看片尾字幕定性**：写"Motion: 配布者"= VMD 翻跳型（走自动管线）；写"Animation: 作者本人"= 手作动画型（动作层不碰，只复刻场景/灯光/FX/色彩剧本层）。
6. **抽帧和参考片并排对照**，穿模/悬空/比例逐项过；高级感复刻先抄"色彩剧本"表再动手。
</details>
