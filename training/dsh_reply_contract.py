# -*- coding: utf-8 -*-
"""dsh_reply_contract.py — Natural Reply 合同 + 上下文预算（2026-11-18 · 逆向自 brain.py）

来源：anima-brain brain.py NATURAL_REPLY（回复长度合同）+ BrainConfig（上下文预算）。
合并为一处：dsh_answer 的回复质量与上下文管理从此有可执行规则（不是注释里的建议）。

设计：
  - 长度档位：acknowledgment 1-8 词 / chat 10-35 / explanation 40-90（英文词数）
    中文按字数×0.6 折算（Qwen 系 1.1 tok/字，1 word ≈ 1.8 字）
  - 上下文预算：48K 字符整条边界 + 10 轮 + 12K 近期字符
  - 溢出策略：整条边界（不腰斩单条），溢出计数显式报告
"""
from __future__ import annotations

import re

# ── 回复长度合同（anima-brain brain.py NATURAL_REPLY 逐字，中文适配） ──
NATURAL_REPLY = """使用与角色和用户匹配的对话语言。
简单确认用 3-15 字，普通聊天 18-60 字，需要解释时 70-160 字。
这些是软目标不是截断规则——用户要求深入时自然展开。
通常选一个有用的对话动作，然后给用户留空间。
避免未经请求的列表、客服式结尾和重复安慰。
列表在被要求或有具体用途时可以用。
自然地匹配俚语和停顿；不要强迫、制造错别字或假装是人。
承认感受但不自动附和结论。不要编造共同经历或不必要的追问。
""".strip()

# 长度档位（中文字数）
LENGTH_TIERS = {
    "acknowledgment": (3, 15),
    "chat": (18, 60),
    "explanation": (70, 160),
}

# ── 上下文预算（brain.py BrainConfig 逐字值） ──
CONTEXT_BUDGET = {
    "context_chars": 48000,      # 总上下文字符上限
    "recent_turns": 10,          # 近期轮数
    "recent_chars": 12000,       # 近期字符上限
    "overflow_policy": "whole-entry",  # 整条边界（不腰斩）
}

# 禁止模式（NATURAL_REPLY 逐字规则的机器可查版）
FORBIDDEN_PATTERNS = [
    (r"作为(?:一个)?AI", "不要以 AI 身份自指"),
    (r"希望(?:这些|这)?(?:对你|对您)?有(?:所)?帮助", "客服式结尾"),
    (r"如果你还有.{0,6}(?:问题|疑问).{0,4}(?:可以|欢迎|请)", "客服式追问"),
    (r"总的来说|综上所述|总而言之", "总结腔（未被要求时）"),
    (r"首先.{4,}其次.{4,}", "未经请求的分条列举"),
    (r"我(?:很)?(?:能)?(?:理解|体会)你的(?:感受|心情)，(?:但是|不过|然而)", "自动附和+转折"),
]


def check_natural_reply(answer: str) -> dict:
    """检查回答是否符合 Natural Reply 合同。返回 {ok, violations, length_tier}。"""
    violations = []
    for pat, desc in FORBIDDEN_PATTERNS:
        m = re.search(pat, answer)
        if m:
            violations.append(f"{desc}: '{m.group(0)[:30]}'")
    char_count = len(answer)
    tier = None
    for name, (lo, hi) in LENGTH_TIERS.items():
        if lo <= char_count <= hi:
            tier = name
            break
    return {"ok": not violations, "violations": violations,
            "char_count": char_count, "tier": tier}


def check_budget(entries: list[str], budget: dict | None = None) -> dict:
    """整条边界上下文预算检查——不腰斩单条，溢出条目显式计数。"""
    b = budget or CONTEXT_BUDGET
    total = sum(len(e) for e in entries)
    included = excluded = 0
    running = 0
    for e in entries:
        if running + len(e) <= b["context_chars"]:
            running += len(e)
            included += 1
        else:
            excluded += 1
    return {"total_chars": total, "included": included, "excluded": excluded,
            "fits": excluded == 0}


def trim_to_budget(entries: list[str], budget: dict | None = None) -> list[str]:
    """整条边界的预算裁剪——保留前 N 条完整条目，永不腰斩单条。"""
    b = budget or {"context_chars": 48000}
    out = []
    running = 0
    for e in entries:
        el = len(e)
        if running + el <= b.get("context_chars", 48000):
            out.append(e)
            running += el
        else:
            break
    return out
