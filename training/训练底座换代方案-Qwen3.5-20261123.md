# 训练底座换代方案 · Qwen2.5-7B → Qwen3.5（2026-11-23 ZCode）

> 出处：项目落后度审计（notes/行业审计-项目落后度-20261122.md）第 1 优先建议。
> 本方案只做"换代准备"，**不立即跑训练**——下次真实微调需求出现时按本方案执行。

## 一、为什么换

- Qwen2.5-7B 落后两代：Qwen3-4B 即匹敌 Qwen2.5-72B（MMLU 83.7%，2026-01）
- HF 实查（2026-11-23）：Qwen3.5 全系在架——**4B（4.1M 下载）/ 9B（6.3M）/ 2B / 0.8B**，另有 Qwen3.8-27B、Qwen3.6-35B-A3B
- 手搓 DPO/SFT 流水线 = 重造 unsloth（80k★）/LlamaFactory（76k★）已有件——**换流程不换数据**（见 §四，格式即 TRL 原生输入）

## 二、型号选型（约束：RTX 4060 Laptop 8GB）

| 档位 | 型号 | 方式 | 判定 |
|---|---|---|---|
| **主选** | Qwen3.5-4B | 全参 SFT 或 LoRA | 8GB 可跑，DPO 54 对/SFT ≥100 条量级合适 |
| 备选 | Qwen3.5-9B | QLoRA 4-bit（bitsandbytes 0.50.2 已装） | 显存紧但可行，质量上限更高 |
| 不选 | Qwen3.8-27B / Qwen3.6-35B-A3B | — | 8GB 不可行 |

## 三、工具链两条路（二选一，都不需大改）

- **路 A（零新增，推荐先走）**：TRL 1.16.0 已装——SFTTrainer（instruction/output）+ DPOTrainer（prompt/chosen/rejected）直接消费现有 jsonl；peft/accelerate/bitsandbytes 全在
- **路 B（可选加速）**：unsloth——训练时长基准 3.2h vs TRL 系 4.7-5.8h、省 VRAM ~70%；**Windows wheel 兼容性待核验**，装不上走路 A

## 四、数据兼容性（已验证）

- `dpo_pairs_v1.jsonl`（54 对）：字段 prompt/chosen/rejected → TRL DPOTrainer 直接消费 ✓
- `sft_instructions.jsonl`（≥100）：instruction/output → TRL SFTTrainer 直接消费 ✓
- source 字段保留溯源（ledger-lessons/排障方法等）——评测回归时按 source 分桶看分

## 五、换代步骤（下次微调时执行）

1. 冒烟：Qwen3.5-4B + SFT 冒烟 100 step（~15 分钟）→ loss 收敛 + 生成抽查
2. 全量：SFT ≥100 条 → DPO 54 对（TRL 两段式）
3. **回归评测用现成仪器**：persona_ab_test 8 标记 + bootstrap 判决（dual_voice 兼容性）+ 25 探针漂移对照（新底座人格贴基线才算过）
4. 通过后换装 dsh 本地人格底座；旧两代 qwen-dsh LoRA 归档保留（不删）

## 六、不做的事

- 不立即跑训练（无真实微调需求触发不烧卡）
- 不删旧 LoRA/数据
- 不在本方案内决定 dsh 主力模型（deepseek-flash 云端与本地方案是两条线）
