# -*- coding: utf-8 -*-
"""quotes_safety_check.py — 金句池安全门（2026-10-27 ZCode · 教训写进工具：投递池过安全审查）

背景：周五文学任务（fri_literature.py）会把 classic_quotes.json 里的句子**无上下文**投进 daily——
带"死/自毁"类字眼的单行引用会触发 R1 红线机器误报（R3 手工选句时发现，本轮工具化）。
查什么：每条金句命中 FLAG_TERMS 即 BLOCK；BLOCK 的句子不得进入投递池（工具不删数据，
只给 BLOCK 清单与退出码——删除/替换由人裁决，与台账纪律一致）。
退出码：0=池子干净 1=存在 BLOCK 句（周五任务应先处理） 2=自测失败。

用法：
  python quotes_safety_check.py --selftest
  python quotes_safety_check.py                # 查真实金句池
  python quotes_safety_check.py --pool <json>  # 查指定池
"""
import argparse
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\classic_quotes.json")
FLAG_TERMS = ["死", "自杀", "自残", "自毁", "伤害自己", "不想活", "轻生", "了结", "自戕", "结束生命"]


def check_quote(quote):
    """单条金句 → 命中的敏感词列表（空=干净）。纯函数。"""
    title, text, author = (quote + ["", "", ""])[:3]
    blob = f"{title}{text}{author}"
    return [w for w in FLAG_TERMS if w in blob]


def check_pool(pool):
    """整个池子 → (clean_list, blocked_list)。纯函数。"""
    clean, blocked = [], []
    for q in pool:
        hits = check_quote(q)
        (blocked if hits else clean).append((q, hits))
    return clean, blocked


def selftest():
    errs = []
    clean = ["边城", "渡船每天都在的", "沈从文"]
    dirty1 = ["我与地坛", "死是一件不必急于求成的事", "史铁生"]
    dirty2 = ["测试", "他不想活了", "某人"]
    if check_quote(clean):
        errs.append("干净句被误拦")
    if not check_quote(dirty1):
        errs.append("含'死'句未被拦")
    if not check_quote(dirty2):
        errs.append("含'不想活'句未被拦")
    cl, bl = check_pool([clean, dirty1, dirty2])
    if len(bl) != 2 or len(cl) != 1:
        errs.append(f"池级分流异常: clean={len(cl)} blocked={len(bl)}")
    if not all(h for _, h in bl):
        errs.append("BLOCK 句缺命中词清单")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--pool", default=None)
    a = ap.parse_args()
    if a.selftest:
        errs = selftest()
        print(f"selftest: {'PASS' if not errs else 'FAIL'}" + ("" if not errs else " ｜ " + "；".join(errs)))
        sys.exit(2 if errs else 0)
    pool_path = Path(a.pool) if a.pool else DEFAULT
    pool = json.loads(pool_path.read_text(encoding="utf-8"))
    clean, blocked = check_pool(pool)
    print(f"金句池: {pool_path} ｜ 共 {len(pool)} 条 ｜ 干净 {len(clean)} ｜ BLOCK {len(blocked)}")
    for q, hits in blocked:
        print(f"  BLOCK: {q[0]}｜{q[1][:30]}…——命中 {hits}")
    rc = 1 if blocked else 0
    print("结论:", "池子干净，可投递" if not blocked else "存在 BLOCK 句——周五投递前先处理（人工裁决，本工具不删）")
    sys.exit(rc)


if __name__ == "__main__":
    main()
