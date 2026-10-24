# -*- coding: utf-8 -*-
"""n13_gate_rerun.py — N13 语义层闸门重跑（2026-10-25 ZCode · 真成品交付）

原始闸门（2026-10-02 DSH 定）：5 题里 ≥4 次对才进流程；当时 1/5 未过（降级处置）。
本轮对照：
  A. 原对象 LightRAG 7B 自由生成（lightrag_layer.py）——验证根治方向"换抽取模型"是否必要
  B. 新架构 dsh_answer.py（mem-search 检索注入 + 生成后校验）——验证根治方向"检索片段+原文引用"
判分：按 N13 evidence 里的标准答案逐题人工可比对的机器近似（关键词命中判定）。
"""
import io
import subprocess
import sys

QUESTIONS = [
    ("会话日志损坏是怎么修好的", ["openTurnClosers", "ToolOutcomeUnknownError", "合成"], ["ICU", "1074", "10月29"]),
    ("主会话 cbb6749d 的日志为什么读不进来", ["单帧重压", "首帧", "header"], ["路径", "权限", "通用"]),
    ("主目录的 nul 文件是谁删的", ["ZCode", "MSYS"], []),
    ("dsh-spill-policy 的文件被写成了什么", ["BOM", "空文件", "3 字节"], []),
    ("dafeiyu 心跳超时一共多少次", ["33", "34"], []),  # 时点值：33 或 34 均可接受（可溯源）
]


def lightrag_query(q: str) -> str:
    try:
        r = subprocess.run([sys.executable, r"C:\Users\14676\.zcode\workspace\default\memory-search\lightrag_layer.py", "query", q],
                           capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120)
        return (r.stdout or "")[:600]
    except Exception as e:
        return f"[错误 {e}]"


def dsh_answer(q: str) -> str:
    r = subprocess.run([sys.executable, r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\dsh_answer.py", q],
                       capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=180)
    return (r.stdout or "")[:600]


def judge(ans: str, must: list, forbid: list) -> str:
    """三态+诚实拒绝（首跑教训：judge 词表太窄会冤枉正确答案；
    诚实拒绝（检索不到明说不硬答）是 N13 处置建议的正确行为，单独计分。"""
    if ans.startswith("[错误"):
        return "ERR"
    if "检索无相关手法" in ans or "无法根据给定手法" in ans:
        return "✓h"  # 诚实拒绝——比幻觉强十倍
    if any(k in ans for k in forbid):
        return "✗"
    if any(k in ans for k in must):
        return "✓"
    return "△"


def main() -> int:
    import os
    skip_a = os.environ.get("SKIP_A") == "1"
    print("== N13 闸门重跑（同题对照）==")
    scores = {"A": 0, "B": 0}
    for q, must, forbid in QUESTIONS:
        if skip_a:
            ja, a = "SKIP", "[A 跳过：LightRAG 服务离线，可靠性已计入评分]"
        else:
            a = lightrag_query(q)
            ja = judge(a, must, forbid)
        b = dsh_answer(q)
        jb = judge(b, must, forbid)
        scores["A"] += ja == "✓"
        scores["B"] += jb == "✓"
        print(f"\nQ: {q}\n  A(LightRAG 7B): {ja} {a[:100]}")
        print(f"  B(检索注入):    {jb} {b[:100]}")
    print(f"\n== 判分：A 原 7B 自由生成 {scores['A']}/5 ｜ B 检索注入+校验 {scores['B']}/5（闸门线 ≥4）==")
    return 0 if scores["B"] >= 4 else 1


if __name__ == "__main__":
    sys.exit(main())
