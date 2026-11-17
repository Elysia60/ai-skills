# -*- coding: utf-8 -*-
"""dsh_continuity.py — L5 分歧自动检测（2026-11-18 · 逆向自 anima-brain continuity.py）

来源：anima-brain continuity.py（主人 Anima Lab 生产代码确定性移植）。
四类用户反应模式 + 七列台账自动追加。

设计原则（anima-brain 注释逐字）：
  "Feedback challenges an interpretation, never rewrites a person's feelings
   or silently rewards intimacy. Host reasoning stays with the host."

用法：
  from dsh_continuity import detect_reactions, create_receipt
  reactions = detect_reactions("你理解错了，不是这个意思")  # → [{"type":"correction",...}]
  entry = create_receipt("D-20261118-01", reactions, context="...")
"""
import re
from datetime import datetime

# ── 四类反应模式（逐字源自 anima-brain continuity.py REACTIONS + 中文变体扩展） ──
REACTIONS = [
    ("boundary",
     r"别再提|不要再问|别这么叫我|别叫我这个名字|leave me alone|don't call me|"
     r"stop calling me|这个话题到此为止|不许再"),
    ("rejected_strategy",
     r"别给我建议|不要给我建议|别分析我|别老问|don't give me advice|"
     r"stop asking questions|stop analyzing me|你不用管我|别操心"),
    ("correction",
     r"不是这个意思|你理解错了|你误会了|你记错了|我没说过|你搞错了|"
     r"you misunderstood|that's not what i meant|you got that wrong|不对。这条不算数"),
    ("acceptance",
     r"这次懂我了|这正是我想要的|谢谢你听我说|that helped|"
     r"that's exactly what i needed|thanks for listening|谢谢你|这就是我要的"),
]

# ── 七列台账格式（DSH 裁决 2026-11-17） ──
LEDGER_COLUMNS = ("日期", "分歧(可验证描述)", "谁坚持了", "修复动作",
                  "修复后状态", "证据(可重放)", "交叉引用id")


def detect_reactions(text: str) -> list[dict]:
    """检测用户回复中的反应类型。返回 [{"type","pattern","position"}]（可能多个）。"""
    low = text.lower()
    out = []
    for rtype, pattern in REACTIONS:
        m = re.search(pattern, low, re.I)
        if m:
            out.append({"type": rtype, "pattern": m.group(0), "position": m.start()})
    return sorted(out, key=lambda x: x["position"])


def create_receipt(entry_id: str, reactions: list[dict],
                   context: str, evidence: str, cross_ref: str = "") -> dict:
    """生成七列台账条目（只填可验证列——修复动作和状态由后续交互填充，不造数）。"""
    types = [r["type"] for r in reactions]
    return {
        "日期": datetime.now().strftime("%Y-%m-%d"),
        "分歧(可验证描述)": context[:200],
        "谁坚持了": "AI" if "correction" in types or "boundary" in types else "主人",
        "修复动作": "",  # 待真实交互填充
        "修复后状态": "",  # 待真实交互填充
        "证据(可重放)": evidence[:300],
        "交叉引用id": cross_ref or entry_id,
        "detected_types": types,
        "reactions": reactions,
    }


def is_repair_signal(text: str) -> bool:
    """检测修复信号（acceptance 类 = 关系修复的正面证据）。"""
    return any(r["type"] == "acceptance" for r in detect_reactions(text))
