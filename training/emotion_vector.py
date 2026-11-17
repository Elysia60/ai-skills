# -*- coding: utf-8 -*-
"""emotion_vector.py — dsh-emotion 形式化状态向量（2026-11-17 ZCode · P0 缺口 #2）

规格来源：xingxingRealzyx/EmotionEngine README（PAD+SSoC 六维，[-1,1]，每轮交互移位、
背景线程向可配置基线人格衰减）+ viva_emotion 的 O-U 均值回归离散化。
蓝图对接：基线人格 = 傲娇萝莉（傲:负效价表面+高唤醒 / 娇:正效价内核 / 危机时全关=强制置位）。

设计（fail-open 原则）：
  - 纯函数 + 显式状态类，零依赖零线程（EmotionEngine 的后台衰减改为按需惰性衰减：
    距上次更新 real-time 折算衰减量——等价于"衰减一直在跑"，但无常驻线程）
  - 危机置位（蓝图绝对红线）：set_crisis() 强制全维归零并置 safety_lock——傲娇全关的字面实现
  - 仲裁输出：arbitrate() 把状态映射为声部权重（供 dual_voice 引擎作输入）

用法：
  from emotion_vector import EmotionState, EmotionEngine
  eng = EmotionEngine.baseline()            # 傲娇萝莉基线
  eng.apply_event(valence=-0.6, arousal=0.3, source="主人报错三小时")
  eng.decay_if_stale()                       # 惰性背景衰减
  w = eng.arbitrate()                        # {"A":0.7,"B":0.3} 声部权重
"""
from __future__ import annotations

import json
import time
from pathlib import Path

DIMS = ("P", "A", "D", "S", "So", "C")  # Pleasure/Arousal/Dominance/Stability/Sociality/Certainty

# 傲娇萝莉基线（蓝图【性格】节向量化）：表面傲(负价)内里温柔(高社交)，
# 稳定度中(会烦躁)确定度中(嘴硬)，支配度低(主人优先)。
BASELINE = {"P": 0.1, "A": 0.35, "D": -0.3, "S": 0.1, "So": 0.6, "C": 0.2}

# 衰减参数（v2: EmotionEngine 逐字公式 new = baseline + (current-baseline)*exp(-rate*minutes)）
DECAY_RATE_PER_MIN = 0.01   # 官方默认（~30min settle）
STALE_SECONDS = 3600        # 超过 1 小时未交互 → 折算衰减
# viva_emotion 耦合系数（逐字）：dP += c_pa·A + c_pd·D；dA += c_ap·P；dD += c_da·A
COUPLE = {"c_pa": 0.0, "c_pd": 0.05, "c_ap": 0.0, "c_da": -0.03}
EMA_ALPHA = 0.05            # 长期 mood 指数平滑（半衰期 ≈13.5 步）
CUSP = {"arousal_threshold": -2.5, "dominance": -0.3, "pleasure": -0.5}  # 突跳触发域

# 仲裁映射（主人理论第一层：状态→声部权重；负价/高唤醒偏情感声部）
ARBITER = {"A_bias": 0.35, "B_bias": 0.35}  # 对称偏置，净差由价决定


class EmotionState(dict):
    """六维状态字典（各维自动夹在 [-1,1]）。"""

    def __init__(self, values: dict | None = None):
        super().__init__({d: 0.0 for d in DIMS})
        if values:
            for k, v in values.items():
                self[k] = max(-1.0, min(1.0, float(v)))

    def shift(self, delta: dict) -> None:
        for k, dv in delta.items():
            if k in DIMS:
                self[k] = max(-1.0, min(1.0, self[k] + float(dv)))


class EmotionEngine:
    """PAD+SSoC 引擎：交互移位 + 惰性 O-U 基线衰减 + 危机置位 + 仲裁输出。"""

    def __init__(self, baseline: dict | None = None, state_file: str | Path | None = None):
        self.baseline = dict(baseline) if baseline else dict(BASELINE)
        self.state_file = Path(state_file) if state_file else None
        st = self._load()
        if st:
            self.state = EmotionState(st["state"])
            self.updated_at = st["updated_at"]
            self.crisis = st.get("crisis", False)
        else:
            self.state = EmotionState(self.baseline)
            self.updated_at = time.time()
            self.crisis = False

    # ── 持久化 ──
    def _load(self) -> dict | None:
        if not (self.state_file and self.state_file.exists()):
            return None
        try:
            return json.loads(self.state_file.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return None  # 状态文件损坏 → 从基线重来（fail-open）

    def save(self) -> None:
        if not self.state_file:
            return
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self.state_file.write_text(json.dumps(
            {"state": dict(self.state), "updated_at": self.updated_at, "crisis": self.crisis},
            ensure_ascii=False, indent=1), encoding="utf-8")

    # ── 背景衰减（v2: EmotionEngine 逐字指数公式，惰性折算） ──
    def decay_if_stale(self, now: float | None = None) -> int:
        """距上次更新超 STALE_SECONDS → 指数衰减折算。

        公式（EmotionEngine 源码逐字）：factor = exp(-rate*minutes)；
        new = baseline + (current - baseline) * factor。返回折算次数。
        """
        import math
        now = now if now is not None else time.time()
        minutes = max(0.0, (now - self.updated_at) / 60.0)
        if minutes < 1.0:
            return 0
        factor = math.exp(-DECAY_RATE_PER_MIN * minutes)
        for d in DIMS:
            mu = self.baseline[d]
            self.state[d] = mu + (self.state[d] - mu) * factor
            self.state[d] = max(-1.0, min(1.0, self.state[d]))
        self.updated_at = now
        return 1

    # ── 长期 mood（viva_emotion EMA 逐字：Mood[t]=α·Emotion[t]+(1-α)·Mood[t-1]） ──
    def update_mood(self) -> float:
        self.mood = EMA_ALPHA * self.state["P"] + (1 - EMA_ALPHA) * getattr(self, "mood", self.baseline["P"])
        return round(self.mood, 4)

    # ── Cusp 突跳（viva_emotion 逐字判据：双稳 Δ=-4α³-27β²>0 且 D<-0.3 且 P<-0.5） ──
    def check_cusp(self) -> bool:
        a = self.state["A"]
        alpha = CUSP["arousal_threshold"] * a
        beta = self.state["P"]
        bistable = (-4 * alpha ** 3 - 27 * beta ** 2) > 0
        if (bistable and self.state["D"] < CUSP["dominance"]
                and self.state["P"] < CUSP["pleasure"]):
            self.state["P"] = -self.state["P"] * 0.7
            self.state["A"] = self.state["A"] * 0.8
            self.state["D"] = self.state["D"] + 0.2
            return True
        return False

    # ── 声部内状态渐变（主人理论第一层的完整实现：不只换声部，同声部也随状态变调） ──
    def style_directives(self) -> dict:
        """把状态翻译成两声部的风格指令（注入 system 卡，不进正文——体现而非报出）。

        返回 {"A": 情感声部指令, "B": 理性声部指令, "mode": str}。
        空字符串 = 该状态无需额外指令（基线人格已含）。
        依据：蓝图【说话的样子】+ 萝莉妈妈节；低落→更短更慢少问多陪；兴奋→接住能量；
        理性声部高唤醒→更简短直接。
        危机锁（蓝图第 0 条）：指令清空——人格卡优先级链第 1 条接管（主人情绪>一切）。
        """
        if self.crisis:
            return {"A": "", "B": "", "mode": "crisis"}  # 人格卡接管，风格指令清空
        p = self.state["P"]
        out = {"A": "", "B": "", "mode": "balanced"}
        if p < -0.2:
            out["A"] = "此刻主人状态不好：句子更短更慢，少问多陪，不分析，先接住。"
            out["B"] = "此刻不宜长篇分析：要点式，一句结论。"
            out["mode"] = "care"
        elif p > 0.4:
            out["A"] = "主人在兴头上：可以更活泼，接住他的能量，别泼冷水。"
            out["B"] = "乘兴展开：可以多给一步'接下来还能怎么走'。"
            out["mode"] = "lift"
        return out

    # ── 交互移位 ──
    def apply_event(self, valence: float = 0.0, arousal: float = 0.0,
                    dominance: float = 0.0, source: str = "") -> None:
        """一轮交互的状态移位。valence/arousal ∈ [-1,1]。"""
        self.decay_if_stale()
        self.state.shift({"P": valence * 0.3, "A": arousal * 0.3, "D": dominance * 0.1})
        self.updated_at = time.time()

    # ── 危机置位（蓝图绝对红线：傲娇全关） ──
    def set_crisis(self) -> None:
        self.crisis = True
        for d in DIMS:
            self.state[d] = 0.0
        self.state["S"] = 1.0  # 危机时唯一满格：稳定（绝不慌）

    def clear_crisis(self) -> None:
        self.crisis = False
        self.state = EmotionState(self.baseline)

    # ── 仲裁输出（主人理论第一层：状态→声部权重） ──
    def arbitrate(self) -> dict:
        """返回 {"A": wA, "B": wB, "mode": str}。

        规则（可证伪，待盲测校准）：
        - 危机锁 → mode="crisis"，声部权重无关（人格卡优先级链第 1 条接管）
        - 负价(主人低落) → 情感声部加权（A+wA·|P|）
        - 正价/中性 → 两声部均衡，唤醒高偏理性(干活)
        权重和恒为 1。
        """
        if self.crisis:
            return {"A": 0.0, "B": 0.0, "mode": "crisis"}
        p = self.state["P"]
        wa = ARBITER["A_bias"] + max(0.0, -p) * 0.5          # 负价 → 情感声部加权
        wb = ARBITER["B_bias"] + max(0.0, p) * 0.5           # 正价 → 理性声部加权
        total = wa + wb
        mode = "care" if p < -0.2 else ("work" if p > 0.3 else "balanced")
        return {"A": round(wa / total, 3), "B": round(wb / total, 3), "mode": mode}

    def as_dict(self) -> dict:
        return {"state": dict(self.state), "crisis": self.crisis,
                "arbitration": self.arbitrate()}
