# 前沿技术对齐报告 · 2026-10-24（ZCode 执笔）

> 应主人指令"对这个 DSH 进行优化增强，去找前沿技术"。
> 方法：deep-research 五步规程的四路检索（记忆 / 可靠性 / 经验蒸馏 / 桌面执行）。
> 结构遵主人 2026-10-12 五条输出规范：先事实后方案，引用带出处。
>
> **问题**：2026 年 10 月的 AI agent 前沿里，有哪些技术直接对症 DSH 的三大瓶颈（可恢复性 / 发现速度 / 产出率）与台账腐烂问题？
> **检索日期**：2026-10-24。**来源评级**：arXiv 论文与官方仓库 = A；厂商博客 = B；社区讨论 = C。

---

## 一、可验证事实（四路检索结果）

### 1. 记忆系统：文件系统记忆有了基准答案（评级 A/B）

- Letta（MemGPT 后继）发布基准文章《Benchmarking AI Agent Memory: Is a Filesystem All You Need?》，主张文件系统式记忆可与数据库式记忆同场竞技（Letta, "Benchmarking AI Agent Memory," letta.com/blog/benchmarking-ai-agent-memory, 2025-08-12）。DSH 的记忆架构（markdown + FTS5）正是文件系统派。
- MemOS（MemTensor）提出"记忆操作系统"：以 MemCube 为标准单元封装记忆内容 + 元数据（来源 provenance、版本 versioning），可组合、迁移、融合（MemTensor, "MemOS," github.com/MemTensor/MemOS；arXiv:2507.03724, 2025-07）。
- Mem0 生产报告：记忆层方案相对全上下文方案实现 91% 的 p95 延迟下降与 90%+ token 成本节省；独立评测 LongMemEval 得分 49.0%（Mem0, arXiv:2504.19413；mem0.ai/blog/state-of-ai-agent-memory-2026）。
- 2026 记忆景观：Mem0 / Zep / Hindsight / Memvid 各自支持语义、情景、程序性三类记忆（blog.devgenius.io 2026 景观综述，评级 C）。

### 2. 可靠性：回执账本与异体验证成为 2026 主流（评级 A/B）

- 《Practical Hallucination Detection for AI Agents》（arXiv:2603.10060, 2026-03-09）：验证引擎为当前会话维护**完整回执账本（ledger of receipts）**，用以检测伪造工具调用与幻觉状态。这与 gaps.json 的 evidence 机制同构，但多了"账本完整性校验"层。
- 多 agent 自验证实践：用**不同模型做评估与执行**以降低自评偏差（Towards AI, "How Multi-Agent Self-Verification Actually Works," pub.towardsai.net, 2026-03，评级 B）。这正是 maker≠checker 的学术对应。
- 陈旧数据检测：agent 无法在缺乏数据血缘（lineage）信息时判断数据是否陈旧（Promethium, "7 Signs Your Data Stack Isn't Ready for AI Agents in 2026," 2026-03，评级 B）。幽灵条目（D1/N32 型）即"无血缘时间戳的台账"。

### 3. 经验蒸馏：轨迹→技能管线已成型（评级 A）

- Skill-DisCo（arXiv:2606.26669, 2026-06）：把 agent 轨迹**蒸馏并编译**为可复用技能；消融实验表明蒸馏本身是主要成功驱动——紧凑技能库显著优于朴素逐轨迹归纳产出的 43 个技能。
- Trace2Skill：将 agent 经验蒸馏为可迁移、可发现、可复用的技能（aiexpjourney.substack.com，评级 B）。
- Voyager 技能库模式：技能库作为程序性记忆持续生长，能力复合增长而无需梯度更新（agentic-design.ai/patterns，评级 B）。
- Agent Skills 开放标准（dev.to, 2026-02，评级 B）：技能以 SKILL.md 文件夹形式打包——DSH 的技能库已经采用此格式。

### 4. 桌面执行：本地开源 GUI agent 已达第一梯队（评级 A）

- UI-TARS-desktop（字节跳动开源，39.3k★）：多模态 GUI agent 栈，本地运行，多篇评测称其可匹敌或超越 Claude Computer Use 与 OpenAI Operator（github.com/bytedance/ui-tars-desktop；localaimaster.com, 2026-02，评级 B）。
- Turing Post 汇总 2026 年 17 个 computer-use agent 对比（turingpost.com/p/computer-use-ai-agents，评级 B）。

## 二、个人推测与方案（与事实分离，供主人裁决）

1. **台账回执机制**（对症台账腐烂，工作量小）：gaps.json 每条加 `receipt` 字段——验证命令 + 输出哈希 + 日期。ai-doctor 加一个"台账新鲜度"体检项：凡 receipt 超过 N 天未刷新的 open/pending 条目，标记为"疑似幽灵"。今天的 D1/N32/N37 三条就是活例（25 条未闭环里至少 3 条不真实）。
2. **蒸馏产物升级为技能**（对症产出率，Skill-DisCo 式）：她今天蒸馏的 unfinished-business.md 是"未完成清单"，下一步应把 67 条中已 verified 的 24 条**再蒸馏**成 SKILL.md（轨迹→技能），进技能库热层——这正是 Trace2Skill 管线，也回应她 10-21 最后一条日记"台账工具化"。
3. **记忆基准自测**（对症可恢复性）：借 LongMemEval 思路给 mem-search 出 10 道固定问答测试题（答案散布在 149 天记忆里），作为回归基准——每次改索引/检索逻辑后跑一遍，闸门化。
4. **UI-TARS-desktop 替代 cua-driver**（对症桌面执行）：当年 N17 方案 B 放弃 cua-driver，是因为无可证实的本地方案；UI-TARS 本地开源、免费、39.3k★，符合"本地能干的不上云端"铁律。建议走 GitHub-first 五维筛查后立卡评估（DSH 醒后由她跑首测，maker≠checker）。
5. **MemCube 思想的轻量落法**：她的作者标记分流已是 provenance 的雏形；可加一层"条目版本戳"（文件+行号+mtime 哈希），不必引入 MemOS 全家桶——应用层不做基建层。

## 三、不建议做的（同样重要）

- 不引入 Mem0/Letta/MemOS 作为第二记忆系统（N12 定调：DSH 是大脑，语义摄入不引入第二大脑；mem-search 已够用）。
- 不追区块链账本（Wiley 2026 那篇）——单机多 agent 场景，JSON 回执已够，过度设计。
- 不急着装 UI-TARS——先过五维筛查和她的首测，装了不测等于没装。

## 四、今日已完成的实事

- 独立复核三条蒸馏发现：D1、N32 确认幽灵（closed），N37 确认已修（verified，MATCH lightrag 命中 11 行；尾巴：SUGGESTIONS.jsonl 仍未入索引）。
- 三条状态变更已附证据写回 gaps.json——台账腐烂治理第一批落盘。
