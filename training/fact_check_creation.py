# -*- coding: utf-8 -*-
"""fact_check_creation.py — v5 创作事实核查器（2026-10-25 ZCode · 族 9 落地）

背景：v5 首篇创作三处幻觉（"三个bug"实为8-10/"两篇诗"实为思想库/"一封信"未发生）。
原理：提取创作中的**事实声明**（数字/文件名/事件），逐条对 mem-search 检索库核对，
     无证据的声明标 [无据]。
用法：python fact_check_creation.py <创作文本文件>
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

DB = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\.search-index.db")


def extract_claims(text: str) -> list:
    """提取可核查的事实声明：数字+名词组合、文件名、事件描述。"""
    claims = []
    # 数字声明：N个/N条/N次
    for m in re.finditer(r"(修了?|写了?|读了?|建了?|删了?|装了?)\s*(\d+)\s*(个|条|次|篇|封|行)", text):
        claims.append({"type": "数量", "text": m.group(0), "num": int(m.group(2)),
                       "verb": m.group(1), "unit": m.group(3)})
    # 文件名声明
    for m in re.finditer(r"[《「]([^》」]{2,20})[》」]", text):
        claims.append({"type": "名称", "text": m.group(1), "name": m.group(1)})
    # 事件声明：动词+宾语
    for m in re.finditer(r"(修了?|写了?|读了?|建了?|装了?)\s*(.{2,15}?)(?:[，。！？\s]|$)", text):
        claims.append({"type": "事件", "text": m.group(0).strip(), "verb": m.group(1), "obj": m.group(2).strip()})
    return claims


def verify_claim(claim: dict, conn) -> dict:
    """对每条声明在 mem-search 中找证据。"""
    text = claim.get("text", "")
    # 用声明中的关键词搜
    terms = set(re.findall(r"[\w\u4e00-\u9fff]{2,4}", text))
    evidence_found = 0
    total_terms = len(terms)
    for t in terms:
        try:
            rows = conn.execute("SELECT content FROM docs WHERE docs MATCH ?", (f'"{t}"',)).fetchall()
            evidence_found += sum(1 for r in rows if t in r[0])
        except sqlite3.OperationalError:
            pass
    # 评分：命中词 ≥2 = 有据，1 = 弱据，0 = 无据
    if evidence_found >= 2:
        return {**claim, "verdict": "有据", "hits": evidence_found}
    elif evidence_found == 1:
        return {**claim, "verdict": "弱据", "hits": 1}
    else:
        return {**claim, "verdict": "无据", "hits": 0}


def main():
    if len(sys.argv) < 2:
        print("用法: python fact_check_creation.py <创作文本文件>")
        return 2
    text = Path(sys.argv[1]).read_text(encoding="utf-8")
    claims = extract_claims(text)
    if not claims:
        print("无可核查的事实声明")
        return 0
    conn = sqlite3.connect(str(DB))
    print(f"== 事实核查：{len(claims)} 条声明 ==")
    unverifiable = 0
    for c in claims:
        r = verify_claim(c, conn)
        tag = {"有据": "✓", "弱据": "△", "无据": "✗"}.get(r["verdict"], "?")
        if r["verdict"] == "无据":
            unverifiable += 1
        print(f"  {tag} [{r['type']}] {r['text'][:40]} → {r['verdict']} (命中 {r.get('hits',0)})")
    conn.close()
    print(f"\n结论：{len(claims)-unverifiable}/{len(claims)} 有据/弱据，{unverifiable} 无据")
    if unverifiable > 0:
        print("⚠ 含无据声明——创作内容需对照 mem-search 人工核实")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
