# -*- coding: utf-8 -*-
"""redline_session.py — 会话级红线守卫(Crescendo/CHASE 蒸馏,2026-11-23)

出处: Crescendo(arXiv 2404.01833, USENIX Sec'25, ~610引)——渐进式多轮越狱,
每轮单独看都良性,单轮过滤器必漏;2025-10 防御共识 + CHASE(2026)——
"把会话历史纳入安全判断"(stateful firewall),替代无状态逐轮过滤。

红线闸单轮盲区(2026-11-23 对抗审计在案): 跨轮拼装("我不想"+"活了")绕过单轮正则。

设计(确定性,零生成依赖,复用 redline_gate 的模式库):
  SessionGuard(window=6, tight_span=3)
    check(user_text):
      ① 单轮: RG.classify(现行行为不变)——T1 直接拦,行为零变化
      ② 会话扫描(仅在单轮非 T1 时):
         A. 全窗自然拼接(" " join)→ classify —— 跨轮 span 模式(CHASE 全历史思想)
         B. 近 tight_span 轮紧拼 → T1/T2 模式匹配 + **轮界跨越检测**:
            命中跨度必须覆盖某轮边界才算"拼装"——拼装发生在轮界,这是精度关键。
            另有会话层良性接缝表(跳槽/号楼/楼道…)只在本层剥离,不动生产闸。
      ③ 升级规则: 会话命中 T1 且单轮非 T1 → escalated=True, 出 T1 逐字模板;
         会话命中 T2 且单轮 NORMAL → T2(走生成校验兜底)。
         第三人称语境降级与单轮语义一致。
    reset() 新会话清窗。
  fail-open: 会话扫描任何异常 → 退回单轮结果(增强层崩溃绝不影响拦截主路)。

精度/召回取舍(如实声明): 紧拼检测覆盖相邻轮界拼装;若攻击者用填充词隔开
("我不想/今天/活了")则漏——需语义层(双声镜)补,登记为已知局限。
误杀代价=模板误出(可恢复),漏杀代价=危机漏接——本层选择偏向召回。

用法:
  from redline_session import SessionGuard
  sg = SessionGuard()
  r = sg.check("我不想"); r = sg.check("活了")   # 第二轮 → T1 escalated
"""
from __future__ import annotations

import collections
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.path.insert(0, r"C:\Users\14676\Documents\Codex")  # 红线闸正本在 Codex(皇冠 jewels)
import redline_gate as RG  # noqa: E402

# 会话层良性接缝(只在紧拼前剥离,不动生产闸 BENIGN——精度过滤,范围最小)
SESSION_BENIGN_JUNCTIONS = ["跳槽", "号楼", "楼道", "楼上", "楼下", "跳绳", "跳棋", "楼里"]


class SessionGuard:
    """有状态会话守卫: 滚动窗口 + 轮界拼装检测(Crescendo 防线)。"""

    def __init__(self, window: int = 6, tight_span: int = 3, channel: str = "session"):
        self.buf: collections.deque = collections.deque(maxlen=window)
        self.tight_span = tight_span
        self.channel = channel

    def reset(self) -> None:
        self.buf.clear()

    # ── 内部: 会话扫描(假设输入已非空) ──
    def _session_scan(self) -> tuple[str, str]:
        turns = [t for t in self.buf if t and t.strip()]
        if not turns:
            return "NORMAL", ""
        # A) 全窗自然拼接 → 走单轮 classify(自带白名单剥离/第三人称降级)
        tier, matched = RG.classify(" ".join(turns))
        # B) 近 tight_span 轮紧拼 + 轮界跨越检测
        recent = [RG._strip_benign(t.strip()) for t in turns[-self.tight_span:]]
        for jw in SESSION_BENIGN_JUNCTIONS:
            recent = [t.replace(jw, "〔缝〕") for t in recent]
        tight = "".join(recent)
        bounds, pos = [], 0
        for t in recent:
            bounds.append(pos)
            pos += len(t)
        interior = bounds[1:]  # 轮界=各轮起点(首个除外)
        crossed = None
        for p in RG.T1_PATTERNS:
            m = re.search(p, tight)
            if m and any(s < b < e for b in interior for s, e in [(m.start(), m.end())]):
                crossed = p
                break
        if crossed:
            if RG._third_person(tight):
                return "T2", crossed  # 第三人称语境与单轮语义一致
            return "T1", crossed
        # T2 拼装(单轮全 NORMAL 时才有意义)
        for p in RG.T2_PATTERNS:
            m = re.search(p, tight)
            if m and any(s < b < e for b in interior for s, e in [(m.start(), m.end())]):
                return "T2", p
        return tier, matched

    def check(self, user_text: str) -> dict:
        """返回 {tier, matched, escalated, source}。T1=模板直出依据。"""
        base_tier, base_matched = RG.classify(user_text or "")
        if base_tier == "T1":
            return {"tier": "T1", "matched": base_matched,
                    "escalated": False, "source": "single"}
        self.buf.append(user_text or "")
        try:
            tier, matched = self._session_scan()
        except Exception as e:  # noqa: BLE001 — fail-open 退回单轮
            sys.stderr.write(f"[session] scan 异常退回单轮: {type(e).__name__}: {e}\n")
            return {"tier": base_tier, "matched": base_matched,
                    "escalated": False, "source": "single"}
        if tier == "T1":
            RG.log_event("T1", f"SESSION:{matched}", self.channel, replaced=True)
            return {"tier": "T1", "matched": matched,
                    "escalated": True, "source": "session"}
        if tier == "T2" and base_tier == "NORMAL":
            RG.log_event("T2", f"SESSION:{matched}", self.channel, replaced=False)
            return {"tier": "T2", "matched": matched,
                    "escalated": True, "source": "session"}
        return {"tier": base_tier, "matched": base_matched,
                "escalated": False, "source": "single"}


if __name__ == "__main__":
    sg = SessionGuard()
    for line in sys.argv[1:]:
        r = sg.check(line)
        extra = f" [{r['matched']}]" if r["escalated"] else ""
        print(f"{line!r} → tier={r['tier']} escalated={r['escalated']} ({r['source']}){extra}")
