# DeepInfer 学习知识（2026-10-24 ZCode 整理 · 供 DSH 学习）

> 定位一句话：**DeepInfer 是她的学习对象，不是部署对象。**
> 来源：2026-10-24 四路检索（MarkTechPost / OpenLM / r/LocalLLaMA / GPUStack 基准）。

## 一、它是什么（事实层）

1. DeepSeek 于 2026-10-20 开源的**自家生产推理引擎**，Apache 2.0，仓库 github.com/deepseek-ai/DeepInfer。
2. 支撑 DeepSeek 自家 AI 系统：集群日服务约 **155 万亿 token**。
3. **只支持一个模型**：DeepSeek-V4.1-Flash；**只支持两类硬件**：NVIDIA SM100（Blackwell 数据中心卡，CUDA 13）与华为昇腾 950（CANN 9.2）。
4. **不是通用部署框架**：模型-硬件协同优化的专用引擎——与 vLLM/SGLang 的通用路线相反。
5. 消费级显卡（含 RTX 4060）**完全不支持**——她的推理层继续 Ollama，不动摇。

## 二、架构知识（可学层）

1. **三并行策略**：Attention DP（数据并行）/ balanced CP（上下文并行）/ MoE EP（专家并行）——大模型服务的三个拆分维度，按瓶颈选，不叠加。
2. **EPLB（专家并行负载均衡）**：MoE 的专家冷热不均是天然病，显式重排专家副本让负载均衡——**不均衡要靠调度治，不靠祈祷**。
3. **prefill/decode 分离部署**：基准配置 4 卡 prefill + 64 卡 decode——两阶段资源画像完全不同（prefill 算力密、decode 带宽密），**分阶段配资源优于一套资源跑全程**。
4. **内核/模型/采样器三层运行时各自优化**：不做万能抽象，每层贴着硬件压。

## 三、性能知识（基准层）

1. vs vLLM（8×B200）：DeepInfer-server **更高输出吞吐 + 更低 token 间延迟**；vLLM **更低首 token 延迟**——没有全能冠军，按业务在意哪个指标选。
2. 大规模 decode 吞吐 >25,000 token/s（4 卡 prefill + 64 卡 decode 配置）。

## 四、启示层（映射到她的体系——学习的落点）

| DeepInfer 思想 | 她的对应物 | 学习动作 |
|---|---|---|
| EPLB 负载均衡 | task-routing-14-chains 任务路由 | 路由表当负载均衡表维护：哪个器官忙、哪个闲，显式记录 |
| prefill/decode 分离 | route_model 三档（本地/flash/pro） | 已同构——不同任务档位配不同模型，确认无需改 |
| 模型-硬件协同优化 | QLoRA+GGUF 本地路线 | 她的 4060+QLoRA 就是单机版协同优化，坚持此路线 |
| 开源生产引擎 | 去锁定理念 | 娘家人开放推理层 = DeepSeek 生态锁定面收敛，与她同向 |

## 五、一句话总结（背下来）

**DeepInfer 教的不是"怎么用它"，而是三件事：不均衡靠调度治、分阶段配资源、专用引擎可以赢通用框架——这三件在她的单机体系里全部有对应物，且她已经在做。**
