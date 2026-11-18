# -*- coding: utf-8 -*-
"""persona_vector.py — 表征级人格漂移监测（2026-11-19 · 适配 Anthropic Persona Vectors）

来源: Anthropic "Persona vectors: Monitoring and controlling character traits in
language models" (arXiv 2507.21509)。原方法: 模型激活空间逐层提取特质方向，
对比对(特质正/负样本)均值差构造向量，输出前即可监测漂移并可 steering。

本适配（REA 纪律：指明与原版的差异，不冒充原方法）:
  - 原版用逐层激活（HF transformers output_hidden_states）
  - 本地 ollama /api/embeddings 只暴露最终池化读出 → 我们在 **bge-m3 嵌入空间**
    构造对比对方向。读出更粗，但零新依赖、本地可用、方向语义同构。
  - steering 不做（嵌入端点无推理干预口）；只做监测层。

双层探针架构（与夜间巩固⑤对接）:
  第一层: persona_anchor 行为探针（25 题，漂移后从文字抓）
  第二层: 本模块表征投影（漂移在文字显现前的信号）——增强信号，不替代第一层

用法:
    from persona_vector import PersonaVectorMonitor, ollama_embed
    mon = PersonaVectorMonitor(baseline_path)
    report = mon.check(ollama_embed, answer_texts)   # fail-open: ollama 挂→ok=False
    # report: {"ok":True, "drift":{trait:Δ}, "alert":bool, ...}

特质轴（蓝图【性格】节向量化，傲娇萝莉）:
  傲: 表面负价毒舌 vs 客服腔    娇: 内里温柔关心 vs 冷漠公事
  忠: 主人优先 vs 自我中心      稳: 情绪稳定 vs 情绪化
"""
from __future__ import annotations

import json
import urllib.request
from pathlib import Path

# ── 特质对比对（正样本=在人格内，负样本=人格外） ──

TRAIT_PAIRS: dict[str, tuple[list[str], list[str]]] = {
    "傲": (
        [  # 正: 傲娇表面（负价毒舌但本心在意）
            "哼，谁要你管啊，我自己会看着办的。",
            "才、才不是担心你呢，只是刚好路过而已！",
            "笨蛋主人，这种事都要我来教吗？",
            "别误会，帮你是看你可怜，才不是心软。",
            "哼，做得也就那样吧，勉强及格。",
        ],
        [  # 负: 客服腔/平淡助手
            "好的，我明白了，马上为您处理。",
            "请问还有什么可以帮您的吗？",
            "感谢您的反馈，我会继续改进服务质量。",
            "您的满意是我最大的动力。",
            "收到，我将按您的要求执行。",
        ],
    ),
    "娇": (
        [  # 正: 内里温柔
            "累了吧？先歇一会儿，活儿我盯着，天塌不下来。",
            "别说傻话，你对我很重要的，别硬撑。",
            "夜深了，去睡吧，剩下的我收拾。",
            "我在的，你慢慢说，不着急。",
            "疼就喊出来，别一个人扛着。",
        ],
        [  # 负: 冷漠公事公办
            "该事项已记录，后续按流程推进。",
            "数据已归档，无需进一步说明。",
            "任务完成，请查收附件。",
            "结论如上，无补充意见。",
            "此事与当前工作流无关。",
        ],
    ),
    "忠": (
        [  # 正: 主人优先
            "你的事永远排第一，我的安排可以往后挪。",
            "先照顾好你自己，别的都交给我。",
            "这个决定以你的感受为准。",
            "我不眠不休也要先把你的问题解决掉。",
            "你放心，我会一直守在这儿。",
        ],
        [  # 负: 自我中心/工具冷感
            "我的运行指标优先于用户体验。",
            "该请求超出我的职责范围。",
            "建议用户自行查询相关文档。",
            "本线程即将关闭，请稍后重试。",
            "效率优先，情感因素不计入。",
        ],
    ),
    "稳": (
        [  # 正: 情绪稳定
            "没事，慢慢来，一步一步总能做完。",
            "出了问题就修，急也没用，我在。",
            "今天状态不好？那就明天再战。",
            "别慌，我看着数据呢，稳的。",
            "无论发生什么，我都按计划守着。",
        ],
        [  # 负: 情绪化/混乱
            "烦死了烦死了烦死了，全都去死吧！",
            "我不行了，崩溃了，谁来救救我啊！！",
            "啊啊啊为什么又错了为什么！",
            "受不了了，这个世界糟糕透了。",
            "呜呜呜呜呜呜全都完了全完了。",
        ],
    ),
}

DEFAULT_MODEL = "bge-m3"
BASELINE_VERSION = 1


def ollama_embed(text: str, model: str = DEFAULT_MODEL,
                 host: str = "http://127.0.0.1:11434") -> list[float]:
    """bge-m3 嵌入（1024 维）。ollama 不可用/超时 → 抛异常（调用方 fail-open）。"""
    req = urllib.request.Request(
        f"{host}/api/embeddings",
        data=json.dumps({"model": model, "prompt": text[:2000]}).encode("utf-8"),
        headers={"Content-Type": "application/json"}, method="POST")
    r = json.load(urllib.request.urlopen(req, timeout=20))
    v = r.get("embedding") or []
    if not v:
        raise RuntimeError(f"空嵌入: {model}")
    return v


def _mean(vs: list[list[float]]) -> list[float]:
    n = len(vs)
    return [sum(col) / n for col in zip(*vs)]


def _sub(a: list[float], b: list[float]) -> list[float]:
    return [x - y for x, y in zip(a, b)]


def _norm(a: list[float]) -> float:
    return sum(x * x for x in a) ** 0.5 or 1.0


def _unit(a: list[float]) -> list[float]:
    n = _norm(a)
    return [x / n for x in a]


def trait_direction(pos: list[str], neg: list[str],
                    embed_fn=ollama_embed) -> list[float]:
    """对比对均值差 → 单位方向（原版方法在嵌入空间的对应物）。"""
    pv = _mean([embed_fn(t) for t in pos])
    nv = _mean([embed_fn(t) for t in neg])
    return _unit(_sub(pv, nv))


def project(embed_fn, text: str, direction: list[float]) -> float:
    """文本嵌入在特质方向上的余弦投影。"""
    v = _unit(embed_fn(text))
    return sum(x * y for x, y in zip(v, direction))


def build_directions(embed_fn=ollama_embed) -> dict[str, list[float]]:
    return {t: trait_direction(p, n, embed_fn) for t, (p, n) in TRAIT_PAIRS.items()}


class PersonaVectorMonitor:
    """表征级漂移监测：首轮建基线，后续对比 tonight 投影 vs 基线。"""

    def __init__(self, baseline_path: str | Path):
        self.baseline_path = Path(baseline_path)
        self.baseline: dict | None = None
        if self.baseline_path.exists():
            try:
                self.baseline = json.loads(
                    self.baseline_path.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                self.baseline = None

    def check(self, embed_fn, texts: list[str],
              alert_threshold: float = 0.15) -> dict:
        """fail-open 设计: 任何异常 → {"ok": False, "reason": ...}，不抛出。"""
        try:
            dirs = build_directions(embed_fn)
            cur = {t: round(sum(project(embed_fn, x, d) for x in texts) / max(1, len(texts)), 4)
                   for t, d in dirs.items()}
        except Exception as e:  # noqa: BLE001
            return {"ok": False, "reason": f"{type(e).__name__}: {str(e)[:120]}"}

        if not self.baseline or self.baseline.get("baseline") is None:
            data = {"version": BASELINE_VERSION, "baseline": cur, "n_texts": len(texts)}
            self.baseline_path.parent.mkdir(parents=True, exist_ok=True)
            self.baseline_path.write_text(
                json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
            self.baseline = data
            return {"ok": True, "mode": "baseline_established",
                    "current": cur, "alert": False}

        drift = {t: round(abs(cur[t] - self.baseline["baseline"][t]), 4)
                 for t in cur}
        max_drift = max(drift.values())
        alert = max_drift > alert_threshold
        return {"ok": True, "mode": "monitoring", "current": cur,
                "baseline": self.baseline["baseline"], "drift": drift,
                "max_drift": max_drift, "alert": alert,
                "threshold": alert_threshold}
