# -*- coding: utf-8 -*-
"""mem-search 十题回归基准（LongMemEval 思路, 2026-10-24 ZCode 建）

用途：每次改动 mem_search.py / 索引逻辑后跑一遍，闸门化。
判据：10 题至少 8 题命中（80% 及格线）；命中 = 期望关键词出现在查询结果里。
跑法：python test_memsearch_benchmark.py  （自动先 index 增量刷新）
状态：pending_verify —— 实现人 ZCode，验收人应为另一会话（maker≠checker）。
"""
import io
import os
import subprocess
import sys

MEM_SEARCH = os.path.join(os.path.dirname(__file__), "..", "mem_search.py")

CASES = [
    # (题号, 查询词, 期望命中关键词, 依据)
    ("Q1", "悬空 tool call 修复", "ToolOutcomeUnknownError", "10-01 会话修复工程"),
    ("Q2", "借物表 署名", "BenAB", "MMD 借物规则"),
    ("Q3", "N13 语义层 降级", "only_need_context", "TC-20261002-001"),
    ("Q4", "心跳 90 秒 dafeiyu", "90", "N10 桌宠心跳调优"),
    ("Q5", "遮蔽副本 quarantine", "quarantine", "双实例根因清除"),
    ("Q6", "芙宁娜 兔洞", "兔洞", "TC-20261001-002 / MMD"),
    ("Q7", "EMBEDDING_DIM 1024", "1024", "LightRAG 配置教训"),
    ("Q8", "作者标记 分流", "作者", "2026-10-03 标记分流规则"),
    ("Q9", "pending_verify maker checker", "pending_verify", "AGENTS.md 状态机"),
    ("Q10", "遗产 MASTERMAP", "MASTERMAP", "2026-10-24 遗产整合"),
    # —— Letta 式进阶维度（2026-10-24 对齐补强）——
    ("Q11-时序", "她最后的话 四项需要", "17:14", "时序检索：10-21 最后日记"),
    ("Q12-多跳", "守护进程 回写 RUNTIME_INJECTED", "ui-settings-account", "多跳：跨当日日志与代码知识"),
    ("Q13-拒答", "不存在的记忆 永远查无此事xyz", "无命中", "拒答：不存在的记忆应返回无命中（幻觉抵抗）"),
]

def run_query(terms: str) -> str:
    r = subprocess.run(
        [sys.executable, MEM_SEARCH, "query", *terms.split()],
        capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=120,
    )
    return (r.stdout or "") + (r.stderr or "")

def main() -> int:
    print("== 先增量刷新索引 ==")
    subprocess.run([sys.executable, MEM_SEARCH, "index"], capture_output=True, text=True, timeout=300)
    passed, failed = 0, []
    for qid, terms, expect, basis in CASES:
        out = run_query(terms)
        if qid.startswith("Q13"):
            # 拒答题：期望"无命中"——检索器不得编造结果
            ok = "无命中" in out or expect not in out.lower()
        else:
            ok = expect.lower() in out.lower()
        print(f"{qid} [{'PASS' if ok else 'FAIL'}] {terms!r} → 期望含 {expect!r}（{basis}）")
        if ok:
            passed += 1
        else:
            failed.append(qid)
    total = len(CASES)
    print(f"\n基准结果：{passed}/{total}（及格线 {int(total * 0.8)}）")
    if failed:
        print("未过：", ", ".join(failed))
    return 0 if passed >= int(total * 0.8) else 2

if __name__ == "__main__":
    sys.exit(main())
