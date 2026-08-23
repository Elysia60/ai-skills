# AI Skills

10 个单一职责的 agent skill,按三个能力域组织:能力域(用 AI 的内功)、交付域(从需求到上线的流程)、工程域(安全与多 Agent 基础设施)。

## 🧠 能力域 — 用 AI 的内功

| Skill | 一句话 |
|---|---|
| `prompt-crafting` | 提问力:背景+任务+要求+格式,把模糊想法变成可执行指令 |
| `ai-output-qa` | 判断力:三找不合理点 + 1-10 信任分,给 AI 输出做质检 |
| `ai-integration` | 整合力:选、改、嵌三步,把 AI 产出拼进真实业务 |
| `human-touch` | 共情力:最后一步加自己的故事,给 AI 内容去掉机器味 |

## 📦 交付域 — 从需求到上线

| Skill | 一句话 |
|---|---|
| `requirement-xray` | 需求穿透:五连问 + 一页纸方案,动工前的防返工闸门 |
| `ai-build-loop` | AI 协作交付:最小闭环→健壮性→测试→部署,四类工具检查清单 |
| `demo-303030` | 演示与反馈:30秒痛点+30秒演示+30秒价值,反馈三问 |
| `skill-compounding` | 沉淀复用:第三次出现即沉淀,下次交付从3天变3小时 |

## 🛠️ 工程域 — 基础设施

| Skill | 一句话 |
|---|---|
| `glm-security-audit` | Trail of Bits 方法论安全审计:心智模型→STRIDE→证据级发现→评分卡 |
| `agent-fleet-ops` | 多 Agent 舰队运维:连接 Claude/Codex/ZCode,内置体检与同步脚本 |

> 交付域四技能连起来就是一条完整的 AI-First 交付流水线:穿透需求 → 协作交付 → 演示反馈 → 沉淀复用。

## 安装

```bash
git clone https://github.com/Elysia60/ai-skills.git
cp -r ai-skills/*/ ~/.agents/skills/   # 复制全部;或只挑你需要的
```

每个 skill 单一职责、独立可用,也可以按域组合成流水线使用。

## License

MIT
