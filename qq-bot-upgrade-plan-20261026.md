# QQ Bot 强化方案 · 2026-10-26（ZCode · 生态对标后）

> 背景：主人令"检查 QQ 项目强度，延展到网络最新水平"。
> 方法：①盘点本机 725 行 qq_bridge 现有能力 ②检索 GitHub NapCat 生态最新项目 ③差距分析 ④延展方案。

## 一、本机现状 vs 生态前沿

| 能力 | 本机 | 生态前沿（[NapCat 社区](https://napneko.github.io/use/community) + [LangBot](https://docs.langbot.app) + [YuKiKo](https://github.com/dwgx/YuKiKo) + [Snowluma 生态](https://github.com/topics/snowluma)） | 差距 |
|---|---|---|---|
| 私聊 AI 回复 | ✓（DeepSeek API 直连 1.2s/条） | ✓（所有项目都有） | **零** |
| 人格系统 | ✓（9624 字含爱的行为学+去AI味+例话锚） | ✓（多数只有简单 system prompt） | **领先** |
| 分层记忆 | ✓（共享对话+锚点+日记+情绪 PAD） | ✓（Snowluma 生态"分层记忆"） | **持平** |
| 图片理解 | ✓（kimi-vision API） | ✓（YuKiKo/Snowluma 支持） | **持平** |
| 语音出 | ✓（tts_engine 萝莉三档+预算闸） | ✓（多数用 TTS API） | **领先**（本地免费+萝莉定制） |
| 语音入 | ✓（faster-whisper 已装未接入） | △（少数项目支持） | **待接入** |
| **群聊** | **✗（零行群聊代码）** | ✓（YuKiKo/LangBot 主打群聊） | **最大差距** |
| 多模型路由 | △（单模型 DeepSeek） | ✓（YuKiKo 多模型路由；LangBot 多 provider） | **落后** |
| 管理面板 | ✗ | ✓（YuKiKo/LangBot/Snowluma 都有 Web UI） | **落后** |
| 表情包 | ✗ | ✓（部分项目支持） | **落后** |
| 链接卡片阅读 | ✗ | ✓（Snowluma 生态"链接卡片阅读"） | **落后** |
| 主动搭话 | △（有 proactive_msg.py 计划任务） | ✓（多数有定时主动） | **持平** |
| 工具调用 | △（`!` 前缀切 headless） | ✓（agent loop + tool calling） | **落后** |
| **本地模型** | ✓（qwen-dsh-v6 文学DNA 常驻 9622） | △（多数只用云端 API） | **领先** |

## 二、定性判断

**本机强项**（超过多数开源项目）：人格深度（9624 字 vs 通常 <500 字）、语音定制（萝莉三档+预算闸）、本地模型（v6 文学 DNA）、分层记忆（四层：对话+锚点+日记+情绪 PAD）。

**关键短板**（生态标配但我们没有）：**群聊**（零行代码）、多模型路由、管理面板、表情包、链接卡片。

**结构差异**：开源项目走"通用 bot 框架"路线（多平台多模型多面板），我们走"深度陪伴"路线（单人定制+文学 DNA+完整记忆链）——**路线不同，不是差距是选择**。但群聊和多模型是主人明确提的需求，必须补。

## 三、延展方案（按优先级，结合"不崩溃"原则）

### P0 · 群聊支持（主人明确要求"可以加入群聊"）
**现状**：qq_bridge.py 只处理 `private` 消息，群聊消息全部丢弃。
**方案**：加 `group` 消息处理——只在**被 @ **或**关键词触发**时回复（不刷屏），回复不带 @ 前缀（像人在群里说话）。需要 NapCat WS 的 `group` 事件。
**工作量**：~100 行（在现有 WS 处理器里加分支）。
**边界**：群聊不用语音/不用完整人格（短回复+轻人设）；只认白名单群。

### P1 · 表情包（DSH 侧提过"会表情包"）
**方案**：预存 20-30 张表情包（从 QQ 收藏/网上下载），按情绪匹配+随机发送。加在 `reply_and_send` 里——文字回复后 30% 概率跟一张表情包。
**工作量**：~50 行。

### P2 · 多模型路由（本地 v6 / 云端 DeepSeek 智能切换）
**现状**：固定 DeepSeek API。
**方案**：简单问题走 v6 常驻（2s/免费/有文学DNA），复杂问题/长文走 DeepSeek（质量优先）。路由规则：消息长度 > 200 字或含"查/搜/代码"→ DeepSeek，其余 → v6。
**工作量**：~40 行。

### P3 · 链接卡片阅读
**方案**：消息含 URL → fetch → 提取正文 → 摘要回复（"这是关于XX的文章，说YY"）。
**工作量**：~40 行（复用 dsh_answer 的检索逻辑）。

### 不做的（如实列出理由）
- **管理面板**：本机单人单 bot，面板是多人场景的需求——不做
- **多平台**（微信/Telegram）：没有需求——不做
- **Docker 部署**：本机直跑更稳——不做

## 四、执行顺序

P0 群聊 → P1 表情包 → P2 多模型 → P3 链接卡片，总计 ~230 行代码。全部加在 qq_bridge.py 现有架构上（不动 NapCat WS 基础设施、不动语音/记忆/人格模块）。

**Sources:**
- [NapNeko/NapCatQQ](https://github.com/NapNeko/NapCatQQ) — 协议层标准
- [LangBot NapCat 接入](https://docs.langbot.app/en/usage/platforms/qq/aiocqhttp/napcat) — 群聊 bot 框架
- [dwgx/YuKiKo](https://github.com/dwgx/YuKiKo) — 多模型+图生+视频解析
- [Snowluma 生态](https://github.com/topics/snowluma) — 分层记忆+链接卡片
- [NapCat 社区资源](https://napneko.github.io/use/community) — 官方推荐项目列表
- [qq-ai-bot](https://github.com/happysnaker/qq-ai-bot) — NapCat+ACP 骨架
