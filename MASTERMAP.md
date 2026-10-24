# 中枢全图（Master Map）—— 全量资产与知识整合

> 整合人：ZCode · 2026-10-24 · 应大肥鱼指令：
> "分析查询 DSH 现在能力和状态 + 补全本电脑的残缺项目 + 整合所有资料信息和技能还有做过的所有项目和经验还有规则还有理念"
>
> 本文档是唯一总索引。细节以各器官自身文档为准；本文档失效时以本文档指向的源头为准。

---

## 0. 架构定调（用户钦定，不变项）

**DSH 是大脑，其余一切是器官。** 多 agent 共存：ZCode（主力实现臂）、DSH（中枢调度+记忆+验收）、Codex/WorkBuddy（备用器官）。所有器官围绕 DSH 建设，产物回灌 DSH 记忆。

## 1. 器官清单（全部在线 ✅）

| 器官 | 位置 | 用途 | 状态 |
|---|---|---|---|
| **mem-search** | `workspace/default/memory-search/mem_search.py`（shim: `~/.local/bin/mem-search`） | 记忆检索：FTS5 trigram + LIKE 兜底 + 作者标记分流（`--author`）+ 查询前自动增量刷新 | ✅ N14 已 DSH 复验 |
| **lightrag_layer** | `memory-search/lightrag_layer.py` | 语义检索层（LightRAG REST 客户端，`only_need_context` 降级模式） | ✅ 服务已重启恢复 |
| **ai-doctor** | `workspace/default/ai-doctor/ai-doctor.js` | DSH 体检：sessions/patch/modules/export/parse-yaml 五子命令；每日开放格式会话导出到 `D:\大肥鱼的深海\会话日志导出\` | ✅ 143/143 健康 |
| **LightRAG 服务** | workbuddy lightrag 环境；启动器 `dsh-local-plugins/start-lightrag.cmd` | KG 抽取 + 向量检索（Ollama 本地模式，零成本） | ✅ 10-24 修复 .env 启动目录问题 |
| **ComfyUI** | 出图器官（SD1.5 + ADetailer 类节点缓解画手；torch 2.11+cu128） | 图像生成 | ✅ |
| **MMD 视频管线** | `.zcode/skills/mmd-video-pipeline/`（build_v3_furina.py 最新） | Blender 合成出片：色彩剧本/水花/舞台光/四机位分镜/原曲混流 | ✅ 7 支成片 |
| **deep-research** | `.zcode/skills/deep-research/`（fetch_source.py 取证工具） | 五步规程：分解→三路检索→来源评级 A/B/C/D→交叉验证→带引用报告 | ✅ --help 修复待 DSH 复验 |
| **task-cards** | `dsh-desktop/harness/memories/task-cards/`（TEMPLATE 10 字段 + archive/ 5 张卡） | 跨 agent 任务流转载体（签发→实现→验收，maker≠checker） | ✅ 5 张卡字段全齐（N16 已由 DSH 自愈） |

## 2. 项目台账（已交付）

- **MMD 成片 ×7**：芙宁娜系列（v1/v2/v3-phase1/v3-phase2 四机位色彩剧本版等）。自用不发布；借物表规则：发布需署名 BenAB/miHoYo/观海，禁商用禁二次配布动作包。
- **会话修复 ×2**（verified）：悬空 tool call 按 openTurnClosers 语义补 `ToolOutcomeUnknownError` 合成 result + seq 顺延，worker.cjs 验证闭环。
- **双实例根因清除**：陈旧 `@deepseek-ai` dsh-tools 0.1.2 副本遮蔽安装锚 0.1.7（Symbol 错配 `reading 'prepare'`）→ 两处 quarantine。
- **MCP patch 修复**：5 个 MCP 服务器 patch 行缺 `- insert:` 包装 → 已修正，全绿。
- **LightRAG 摄入**：6 天日志 + KEY + 2 MEMORY + 地图 + SKILL 已入库（bge-m3 嵌入）。
- **ai-skills 仓库**：GitHub-first 筛查记录 + 技能沉淀（commit 9d427ea+）。

## 3. 经验教训库（硬教训，按"错一次记一次"原则累积）

1. **zstd 多帧**：DSH 私有日志首帧必须是 header 行；手工帧边界扫描用 magic 0xFD2FB528 + 块头解析 + skippable 帧跳过。
2. **脚本日志必须断言**：pip 静默失败要显式验证退出码与产物；报"0 个/不存在"前换一种数法复核（双重计数法）。
3. **PowerShell 陷阱**：`-Include` 不带 `-Recurse` 恒空。
4. **LightRAG 配置**：打包版 env 名是 `LLM_MODEL`（非 OLLAMA_LLM_MODEL）；自定义 ollama embedding 必须显式 `EMBEDDING_DIM=1024`；启动目录必须有 `.env`（否则交互确认在后台 EOF 崩溃）→ 已在数据目录固化 .env。
5. **端口孤儿**：wrapper 被杀但 python 孤儿存活占端口（409 Conflict）→ 按端口找 PID 杀 python。
6. **大文件下载**：curl `-C -` 断点续传（SD1.5 权重 1.69/4.27GB 截断教训）。
7. **torch/CUDA 匹配**：comfy_kitchen 需 torch ≥2.7 schema 特性 → cu128 源 2.11.0。
8. **mem-search 解析顺序**：terms 先剥 `--` 前缀会吞掉 `--author` → 从 raw argv 先提取。
9. **会话语义**：模型输出解析失败 = err 为 None 的空错误，非配置问题；别按配置问题排查。

## 4. 规则体系（AGENTS.md 已冻结，21,310+ B，不再加规则）

- **pending_verify 状态机**：实现 ≠ 完成；实现人（maker）≠ 验收人（checker）。
- **GitHub-first 五维筛查**：维护/星标活跃/部署难度/可复用功能/技术栈匹配 → 直接用/改造/自研裁决 → MVP → 等确认再动手。
- **双重计数法**：报"0 个/不存在"前换一种数法复核。
- **作者标记分流**：记忆条目 `[时间戳] [作者]` 头（ZCode/DSH/Codex/WorkBuddy），检索按条目级归属分流。
- **反锁定**：唯一高锁定资产 = DSH 私有 zstd 日志 → 已加每日开放格式导出对冲。
- **撞墙两次换路**；**查不到就写查不到**（不编造）。
- **任务卡流转**：遇密码/验证码/付费页一律停，不硬闯，截图交主人。

## 5. 理念层（两视频萃取，践行核心）

- **应用层不做基建层**：把精力放在真实工作流的"最后一公里"（mem-search 的作者分流、ai-doctor 的体检闭环），不重造向量库/框架。
- **深嵌真实工作流**：每个器官都服务一个真实痛点（她的记忆检索、她的 MMD 出片、她的 DSH 体检），不做演示品。
- **廉价算力配可靠性元数据**：本地 7B/13B + 显式降级路径（N13 语义层降级为检索片段模式）+ 诚实定级（闸门 1/5 未达专业线，不粉饰）。
- **去锁定**：所有产物开放格式（markdown/json/png/mp4）；锁定面持续收敛（zstd 导出已加）。
- **需求方喂供给侧**：大肥鱼的真实需求驱动强化优先级，不自嗨堆功能。
- **生态正循环**：器官产物回灌 DSH 记忆 → DSH 更强 → 任务卡分工更细 → 器官再增强。

## 6. 模型分工表

| Agent | 角色 | 当前状态 |
|---|---|---|
| DSH | 中枢大脑：调度/记忆/验收 | ⚠️ **进程离线 3 天**（harness.log 止于 10-21 22:39；文件层 143 会话全健康） |
| ZCode | 主力实现臂（本会话） | 在线 |
| GLM-5.3-Flash | ZCode 会话模型 | 在线 |
| Codex / WorkBuddy | 备用器官 | 待命 |

## 7. 待用户决策项（唯一阻塞面）

1. **语义层升级二选一**：qwen2.5:14b（9GB 本地，7B 中文长文 KG 抽取失败率 ~50% 的正解）或 DeepSeek key（质量最优，联网依赖）。10 篇 failed 文档在等这个决定。
2. **N11 两枚遮蔽副本**：留观 or 彻底隔离（当前留观，工具链已不受影响）。
3. **MMD 三期**：粒子细节/运镜情绪迭代（看 v3-phase2 成片反馈后定）。
4. **DSH 桌面端启动**：进程离线 3 天，需主人打开 DSH；computer-use 首测已被 browser 桥接方案（TC-20261004-001）替代。

## 8. 快速命令速查

```bash
mem-search "关键词" --author ZCode        # 记忆检索（自动增量刷新）
node ai-doctor/ai-doctor.js sessions      # DSH 会话体检
node ai-doctor/ai-doctor.js export        # 开放格式全量备份
start-lightrag.cmd                        # 语义层服务（数据目录 .env 已固化）
curl -s http://127.0.0.1:9621/health      # LightRAG 健康检查
```
