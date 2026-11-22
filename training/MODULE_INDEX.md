# training/ 模块总索引 — 2026-11-18 全量整理

> 本索引覆盖 training/ 全部 83 个 .py + 7 个 .md。
> 分层原则：**核心层（活跃生产）→ 评测层 → 历史层（保留可追溯）→ 退役层（已归档）**。
> 移动文件会断 import 链，故物理位置不动，以本索引为准绳。

---

## 一、核心层（2026-11-17~18 建/改，生产就绪）— 16 件

### 1.1 情感与人格

| 文件 | 一句话 | 关键接口 | 状态 |
|---|---|---|---|
| `emotion_vector.py` | PAD+SSoC 六维情感引擎 v2.1（逆向 EmotionEngine + viva_emotion 逐字公式） | `EmotionEngine.apply_event/decay_if_stale/arbitrate/style_directives/set_crisis` | ✅ 10 测全绿 |
| `persona_anchor.py` | 25 探针人格漂移监测（10 蓝图 + 15 ContextEcho 五类） | `run_probes/drift_report/score_answer`，锚文本 207 字符 ~227 token | ✅ 首夜实战抓到 67% 漂移 |
| `sidecar_server.py` | Stage 1 旁路服务器 :9623（pet 输出零变更，全量记日志） | GET /health /style /stats；POST /advance /validate /crisis /clear-crisis | ✅ 运行中，Stage 2 观察期 |

### 1.2 记忆与连续性（五层判据的代码化）

| 文件 | 对应层 | 关键接口 | 状态 |
|---|---|---|---|
| `dsh_temporal.py` | L2 记·时间化 | `TemporalClock.observe/assert_fact/as_of`（发生/观察/有效三钟分离） | ✅ |
| `dsh_standing_intents.py` | L3 信·约定兑现 | `promise/check/fulfill/broken/forget/list`（time/event/aspiration 三型，软失效不物理删） | ✅ 生命周期测试过 |
| `dsh_reply_contract.py` | L4a 表达·结构 | `check_natural_reply`（6 禁式）+ `check_budget/trim_to_budget`（整条边界不截半条） | ✅ |
| `dsh_note_protocol.py` | L4a 表达·笔记 | `NOTE_PROMPT`（anima-brain 逐字）+ `score_note/score_extraction` 确定性打分 | ✅ |
| `dsh_continuity.py` | L5 修复·分歧 | `detect_reactions`（boundary/rejected_strategy/correction/acceptance 四类）+ `create_receipt` 七列台账 | ✅ |

### 1.3 链路与闸门

| 文件 | 一句话 | 状态 |
|---|---|---|
| `dsh_answer.py` | 知识检索链 + 红线闸前置（T1 模板直出/T2 生成后验，fail-open）+ verify_refs | ✅ 12 接线测全绿 |
| `dual_voice_engine.py` | 双声部引擎 v5：红线闸 guard 包装 + style_directives 消费（状态→语气渐变） | ✅ |
| `night_consolidate.py` | 夜间巩固：①-④ 原有流程 + ⑤ persona_drift_check（25 探针，fail-open 不影响退出码） | ✅ 生产运行 |
| `test_redline_wiring.py` | 红线闸物理断线验证（12 测：断 import/断路径/断函数 → fail-open） | ✅ |
| `test_emotion_vector.py` | 情感引擎 10 测（含 crisis 传播、Cusp、衰减） | ✅ |
| `test_persona_anchor.py` | 探针 10 测（锚文本冻结、顺序检查） | ✅ |
| `test_dsh_brain_upgrade.py` | continuity/temporal/reply/note 四模块测试 | ✅ |

### 1.4 采集自愈（2026-11-18 · REA 蒸馏自 Scrapling 0.5.1）

| 文件 | 一句话 | 状态 |
|---|---|---|
| `selector_heal.py` | 选择器腐坏自愈（指纹 9 字段+7 项平均评分+全页重定位+自愈闭环），stdlib 零依赖 | ✅ 10 测全绿 |
| `test_selector_heal.py` | 含与原版测试对齐的 parity 断言（max 分母语义） | ✅ |
| `smoke_scrapling.py` | 原版实弹冒烟（改版自愈交叉验证基准） | ✅ |

> 来源：REA 报告 `Documents/REA报告-Scrapling元素重定位-2026-11-18.md`（版本锚定 0.5.1 @ 2998c9eb）。
> 配套：官方技能已入库 `ai-skills/scrapling-official/` + `.zcode/skills` + `.agents/skills`；`pip install scrapling` 核心层已装（fetchers/浏览器未装）。
> 用途：csqaq/astock 采集器防"网站改版→断链"，接线待做（推测 1，见 REA 报告）。

### 1.5 记忆防线（2026-11-19 · 论文落地）

| 文件 | 一句话 | 状态 |
|---|---|---|
| `persona_vector.py` | 表征级人格漂移监测（Persona Vectors 适配：bge-m3 嵌入空间对比对方向，傲/娇/忠/稳四轴投影） | ✅ 13 测全绿 + 实弹基线建立 |
| `memory_integrity.py` | 记忆投毒防线：append-only 账本 + verify（OK/MODIFIED/UNREGISTERED/**ROLLED_BACK**）+ audit（含 GHOST 幽灵检测）；v3 锚路径可覆盖（2026-11-23 修测试覆盖生产锚缺陷） | ✅ 沙箱全周期测试过，真实账本已登记 8 件皇冠 jewels |
| `memory_evolve.py` | 记忆演化层（A-MEM 蒸馏，2026-11-23）：新事实 × 注册表语料（bge-m3）→ NEW/LINK/REINFORCE/**CONTRADICTION** 矛盾警报（只报不判，maker≠checker）；fail-open | ✅ 17 测全绿 + 34 条语料实弹（2 LINK/1 NEW） |
| `test_memory_evolve.py` | 演化层测试（词典型确定性嵌入，零模型依赖） | ✅ |
| `test_new_defenses.py` | 两模块测试（mock 嵌入测数学 + 沙箱账本测生命周期）+ v3 回归（测试不得触碰生产锚） | ✅ |
| `smoke_scrapling.py` | Scrapling 原版实弹冒烟（改版自愈交叉验证基准） | ✅ |

> ⑤b 双层探针：night_consolidate ⑤ 已接线（行为探针 + 表征投影，均 fail-open）。
> ⑥ 记忆演化：night_consolidate ⑥ 已接线（A-MEM 蒸馏，矛盾推主动消息待主人裁决，fail-open）。
> 账本：`D:\大肥鱼的深海\_记忆账本.jsonl`（append-only，账本在被审计目录之外）。
> 来源：Persona Vectors (arXiv 2507.21509) 适配声明——嵌入空间读出非逐层激活，steering 不做。

### 1.6 晨屏与夜间加固（2026-11-23）

| 文件 | 一句话 | 状态 |
|---|---|---|
| `morning_screen.py` | 晨屏生成器:跨生态单页总览(两简报/仓位/候选/看门狗/双层探针/账本锚/T8),零依赖静态 HTML | ✅ 实弹产出 D:\大肥鱼的深海\晨屏.html |
| night_consolidate v4.2 | 探针重试(2次+退避+90s)+drift 计算错误分离(gen_errors 不计入 drift)——11-22 夜 80% 假漂移根因修复 | ✅ |

> 晨屏纪律: 渲染层不造数,缺失显式标'未产出';数字以各仓注册表为准。

### 依赖关系图

```
night_consolidate.py（夜间总调度）
 ├─→ persona_anchor.py ──→ ollama 本地生成
 └─→ ①-④ 原有巩固流程

sidecar_server.py（旁路观察）
 ├─→ emotion_vector.py（状态持久化 out/sidecar_emotion_state.json）
 └─→ dsh_reply_contract.py（validate 端点）
 日志 → D:\大肥鱼的深海\主动消息\sidecar-events.jsonl

dual_voice_engine.py → dsh_answer.py → redline_gate.py（Documents\Codex，dsh 领地）
                      → emotion_vector.style_directives()

dsh_standing_intents.py → ~/.dsh/memories/standing_intents.json + 主动消息\promises-events.jsonl
```

### 交叉引用（Documents\Codex 侧，dsh 维护）

- `redline_gate.py` — 红线确定性拦截（T1 模板/T2 验证，fail-open，审计 JSONL 62+ 条）；
  **2026-11-23 AgentDojo 式对抗审计**：13 用例真打击中 2 个 T1 缺口（世界告别句式/方法索求句式）已补 + 英文 8 条，
  自检 34/34 + 对抗 13/13，新哈希 a9313540 已重登记账本（ZCode 侧补丁，API 不变）
- `dateparse.py` — 相对时间换算（时间线三层闭环的最底层）

> 对抗套件：`test_redline_adversarial.py`（training/，攻击+效用联合测——AgentDojo 原则；
> 审计日志重定向沙箱，测试不污染真审计）。已知局限在案：拼音混淆/跨轮拼装/编码载荷 → 会话层（双声镜）补。

---

## 二、评测层（2026-11-14~16）— 3 件

| 文件 | 用途 | 状态 |
|---|---|---|
| `blind_test_bank.py` | 盲测题库生成器（SHA256 冻结/校验，防事后改题） | ✅ |
| `m5_dual_source_stats.py` | M5 双源（人类互动 vs 合成）对照统计 | ✅ |
| `dual_core_experiment.py` | 主人理论双核竞争实验（状态→声部翻转验证） | ✅ |

---

## 三、历史层（2026-10-24~11-09，保留可追溯）— 59 件

不删除、不移动（部分被 run_all_validators.py 等聚合入口引用）。按组说明：

- **train_dsh_v1~v7**（7 件）— 训练版本演进史，v5→v7 切换判定见 `切换判定-v5vs7-20261114.md`
- **mega_validation_320k + r2~r12**（13 件）— 32 万字验证的 12 个轮次，聚合入口 `run_all_validators.py` + `validation_common.py`
- **knowledge_***（3 件）— knowledge_write / knowledge_quiz_e2e / knowledge 相关
- **literary_***（4 件）— 文学四步/teller/dna/fri_literature
- **vision_***（4 件）— 视觉协议/阈值校准/chat/selftest
- **weekly_***（2 件）— weekly_quiz / weekly_digest
- **pet_***（3 件）— pet_launcher / pet_wrapper / start_pet_once
- **审计工具**（8 件）— dsh_compat_audit / audit_all_claims / memory_decay_audit / fact_check_creation / quotes_safety_check / pet_config_check / agentsmd_freshness_check / upgrade_validators_monotonic
- **检索研究**（5 件）— retrieval_sweep / composite_query / cooccurrence_map / anchor_recall_check / session_brief
- **治理与其他**（10 件）— skill_governance / battle_regression / eval_v5_v7_compare / dsh_v5_server / creative_loop / dsh_social / emotion_quote / e2e_layer_check / caption_clip_score / clip_batch / mega_bootstrap_10m / persona_ab_test / teach_scenarios / wed_scenario / n13_gate_rerun / blueprint_merge_dryrun

**历史层 .md（7 件）**：calibration-report-20261025 / consolidation_queue / deepinfer-knowledge / 切换判定-v5vs7 / 技能治理清单 / 桌面语义树定位实证 / 注入有效性测量研究 / 蒸馏候选

---

## 四、退役层（deprecated/）— 2 件

| 文件 | 退役原因 |
|---|---|
| `_deprecated_test_memsearch_supersession.py` | mem-search 索引刷新方案被 dsh_temporal 三时钟取代 |
| `_superseded_by_dsh_memsearch_temporal.py` | 同上（原 memsearch_refresh.py 主体） |

---

## 五、本 session 的 Documents/ 侧文档（15 件，时间倒序）

- 逆向报告-anima-brain-2026-11-18.md（30 模块源级逆向）
- 强化方案-全生态-2026-11-18.md（166 技能 + 论文 + 经验整合）
- token消耗诊断 / DSH回执-P0-4 / chat-demo技术拆解 / DSH全方位自评 / DSH验收-W2v2 两轮 kappa（均 11-17）
- DSH交接-强化包 / DSH验收-八缺口 / DSH回执-P0双件 / DSH裁决-W2 / DSH裁决-强化包（11-17）
- DSH回执-取证结果与M5接口 / ZCode回执-裁决执行与盲测出题 / DSH裁决与交接-外部深挖与五层判据v2（11-15）

**本次新增交接文**：`DSH交接-经验总结-2026-11-18.md`（经验蒸馏主文）

---

## 六、w4-study/ 参考库（6 clone + 2 沙箱 + 3 草稿）

| 目录 | 性质 |
|---|---|
| ContextEcho / EmotionEngine / MMTR / anima-brain / claude-mem / sno-station | 论文/开源对照参考（逆向与移植的源头，保留） |
| memsearch_sandbox / mmtr-test | 沙箱（不碰活体记忆，保留至 MMTR 隔离实验拍板） |
| douyin_5layer / douyin_bot / douyin_page .html | 抓页草稿，可删 |

---

## 七、维护规则（写给未来会话）

1. **新增模块必须同时更新本索引**——索引落后于现实 = 下一次整理的成本翻倍
2. **退役必须进 deprecated/ 并留退役原因**——不留原因的删除等于丢历史
3. **import 链优先于物理整洁**——training/ 内模块互相 import 且引用 Documents\Codex 侧，不重组目录
4. **maker≠checker**——本索引由 ZCode 维护，dsh 验收时以抽查为准
5. **手工法44**——所有验证工件落盘，不靠对话记录
