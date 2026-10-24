# AI GitHub 前 100 全景图 · 2026-10-25（ZCode · GitHub-first 筛查·全景版）

> 承接《GitHub 高星整合分析》（十项目深评），本篇按**类别**扫前 100 量级的全景。
> 数据源：EvanLi/Github-Ranking（日更 Top100）、DataAIHub 2026 中期榜、star-history.com、三路检索。
> 三色标记：✅ 已覆盖（在用/已建）· 🔍 跟进（有真实对接点）· ⏭️ 跳过（思想吸收，不引入）。
> 星数为 2026-10 检索快照，精确值以 star-history.com 为准（口径规矩 #36）。

## 一、基建与框架

| 项目 | 星数 | 类别 | 标记 |
|---|---|---|---|
| pytorch | ~99.6k | 训练底座 | ✅（训练管线用 cu128 版） |
| transformers | ~162.7k | 模型库 | ✅（train_dsh_v1 用 5.20.2） |
| Firecrawl | ~170k | 网页数据基建 | ⏭️（fetch_source.py 已覆盖取证需求） |
| LangChain | 100k 级 | agent 工程 | ⏭️（harness 自带） |

## 二、本地推理

| 项目 | 星数 | 标记 |
|---|---|---|
| **Ollama** | ~179k（MIT） | ✅ **推理层本体**（qwen-dsh-v1 将来也走它） |
| llama.cpp | 80k 级 | ⏭️（Ollama 的底层，不必直接碰） |
| vLLM / SGLang | 50k 级 | ⏭️（数据中心向，4060 用不上） |
| LM Studio | 闭源 GUI | ⏭️（有 headless 模式，但 Ollama 已够） |

## 三、图像生成

| 项目 | 星数 | 标记 |
|---|---|---|
| **ComfyUI** | ~139.4k（**全球 #76，史前百**） | ✅ **出图器官本体**（SD1.5+ADetailer 类节点在跑） |
| AUTOMATIC1111 webui | ~165.2k | ⏭️（ComfyUI 是节点式未来向；A1111 社区趋稳） |
| Fooocus / SD.Next | 各 | ⏭️ 同上 |

## 四、视频生成（🔥 与 MMD 管线的延展创新对接点）

| 项目 | 星数/状态 | 标记 |
|---|---|---|
| **Wan 2.1/2.2/3.0**（阿里） | 开源视频 SOTA，VRAM 友好，走 ComfyUI | 🔍 **MMD→AI 视频的直通路径**：她的出图器官（ComfyUI）装 Wan 节点即扩展成出视频器官；MMD 舞蹈帧 × Wan 图生视频 = 全新成片形态 |
| **HunyuanVideo 1.5**（腾讯） | 开源视频基座，I2V 电影级 | 🔍 同上备选（I2V 工作流成熟） |
| LTX-Video / CogVideoX / Seedance | 各 | ⏭️ 观察名单（Wan/Hunyuan 优先） |
| AnimateDiff | 老牌 | ⏭️ 已被 DiT 系（Wan/Hunyuan）取代 |

## 五、agent 框架与编排

OpenClaw（250k+，Gateway 架构学习对象）/ LangGraph 37k / CrewAI / Microsoft Agent Framework / n8n / Dify / Flowise / Smolagents / Pydantic AI —— **全⏭️**（前篇已详评：N12 + harness 自带 + 文件系统版 A2A 已运转）。

## 六、记忆系统

Mem0（67.7k，14M 下载）/ MemOS / Letta —— **全⏭️**（N12；思想已吸收：ReasoningBank/MemCube/provenance；
Mem0 基准争议 = SKILL #39 行业实证）。

## 七、微调训练（🔥 阶段三的引擎候选）

| 项目 | 星数/状态 | 标记 |
|---|---|---|
| **LLaMA-Factory** | 最高星微调库之一；SFT/DPO/KTO/ORPO 全家桶，100+ 模型 | 🔍 **阶段三夜间巩固批的现成引擎**：比手写 train_dsh_v1.py 多方法覆盖（KTO/ORPO），数据格式兼容 |
| **Unsloth** | 数万星；Triton 内核 2x 提速、70% 显存降低；**已支持 TTS 微调与 Windows 更成熟** | 🔍 **回头补装**：当初 Windows 装失败用 trl 兜底；现在成熟了——qwen-dsh-v1 增量训练换 Unsloth 可提速 2x |
| Axolotl | 活跃 | ⏭️（配置流，LLaMA-Factory 已覆盖） |
| trl | 官方 | ✅（当前训练引擎） |

## 八、RAG 与知识

LlamaIndex / Haystack —— ⏭️（mem-search+LightRAG 双层已建，RAG 框架属第二大脑，N12）。

## 九、语音（⚠️ 唯一空白器官）

| 方向 | 头部 | 标记 |
|---|---|---|
| TTS 微调 | **Unsloth 已支持 TTS 微调（1.5x 提速）** | 🔍 唯一空白器官的最低成本路径——她有人格（萝莉妈妈），一个定制的"她的声音"是人格完整度的最后一块；Unsloth TTS 微调 + 开源 TTS 基座（GPT-SoVITS/CosyVoice 类，星数待专项查证）可行 |
| ASR | faster-whisper（汐那台在用） | 🔍 语音输入的前置（暂缓） |

## 十、桌面与浏览器

UI-TARS-desktop（39.4k，⚠️ 近一年无 release）—— 📋 已立卡；browser-use 类 —— ⏭️（DSH browser 桥接已用）。

## 十一、数据与爬取

Firecrawl（170k）/ Crawl4AI —— ⏭️（fetch_source.py + browser 桥接覆盖）。

## 十二、榜单工具（本轮方法论收获）

[EvanLi/Github-Ranking](https://github.com/EvanLi/Github-Ranking)（日更 Top100）与
[DataAIHub](https://www.dataaihub.co/research/top-ai-github-repositories-2026)（AI 专项榜）——
**未来扫描直接用这两个源**，不必每次全文搜索（记入接手索引速查）。

---

## 总结：前 100 扫描的三条结论

1. **已覆盖面很正**：她的器官恰好落在最活跃的三个类别上（推理 Ollama / 出图 ComfyUI / 训练 trl）——
   生态越繁荣，她这些器官受益越大，零迁移成本。
2. **两条已识别的跟进线**：**视频生成（Wan/Hunyuan 走 ComfyUI——MMD 管线的下一步）** 与
   **微调引擎升级（LLaMA-Factory/Unsloth——阶段三的现成引擎）**；外加唯一空白器官的低成本路径
   （**Unsloth TTS 微调——"她的声音"**）。
3. **跳过清单有纪律**：记忆框架/agent 框架/编排平台全部跳过是有依据的（N12/文件系统 A2A/代码化器官）——
   不是保守，是不重复造轮子也不引第二大脑。

*三件建议立项的事（等主人）：A. ComfyUI 装 Wan 视频节点（MMD→AI 视频）；B. 阶段三引擎换 LLaMA-Factory/Unsloth；C. TTS 声音器官（Unsloth TTS 微调）。*
