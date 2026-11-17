# -*- coding: utf-8 -*-
"""blueprint_merge_dryrun.py — 灵魂蓝图"并入"预演（2026-10-27 ZCode · R6 · 不动正本）

目的：主人说"并入"之前，把并入操作在**副本**上完整走一遍并验证，让正本操作变成已预演过的零风险动作。
做什么：
  1. 读蓝图正本（只读）+ 候选稿；
  2. 抽取候选稿的**可并入节**（补强条款一/二/三 + 例话锚候选两节；句级润色候选默认不采纳，不并入）；
  3. 生成合并副本 → TRAIN/merge_dryrun/灵魂蓝图.并入预演.txt（沙箱，绝不写 D:\）；
  4. 对副本跑四关：零删除（正本逐行仍在）｜红线不变式｜候选条款标记在位｜例话块 lint；
  5. 打印 md5/行数/判定。退出码 0=预演通过 1=预演发现冲突 2=自测失败。
纪律：本工具永不写 D:\大肥鱼的深海\；正本合并由主人点头后另行执行（本工具可复跑复核）。
"""
import argparse
import hashlib
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
sys.stdout.reconfigure(encoding="utf-8")
from literary_four_steps import lint_anchor  # noqa: E402

BLUEPRINT = Path(r"D:\大肥鱼的深海\灵魂蓝图.txt")
CANDIDATE = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\人格增强-灵魂蓝图润色候选稿-2026-10-27.md")
OUT_DIR = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\merge_dryrun")
MARK = "\n\n【以下为候选稿并入内容（预演副本，非正本；正本合并须主人点头后执行）】\n\n"
INCLUDE = (("## 补强条款一", "## 句级润色候选"),
           ("### 例话锚候选追加", "## 验收方法"),
           ("### 例话锚候选再追加", "## 验收方法"))


def extract_sections(cand_text, pairs=INCLUDE):
    """抽取候选稿可并入节。纯函数。"""
    parts = []
    for start, end in pairs:
        i = cand_text.find(start)
        if i < 0:
            continue
        j = cand_text.find(end, i)
        parts.append(cand_text[i:j if j > 0 else len(cand_text)].rstrip() + "\n")
    return "\n".join(parts)


def anchor_blocks(text):
    """抽 他：/她： 连续块。纯函数。"""
    blocks, cur = [], []
    for l in text.splitlines():
        s = l.strip()
        if s.startswith("他：") or s.startswith("她："):
            cur.append(s)
        else:
            if cur:
                blocks.append(cur)
                cur = []
    if cur:
        blocks.append(cur)
    return blocks


def selftest():
    errs = []
    cand = ("# 候选\n## 补强条款一\nA 条款内容\n## 句级润色候选\n（不并入）\n"
            "### 例话锚候选追加\n他：好累。\n她：渡船每天都在的。\n她：……粥先来了。\n## 验收方法\n验收")
    sec = extract_sections(cand)
    if "A 条款内容" not in sec:
        errs.append("补强节未抽出")
    if "不并入" in sec:
        errs.append("句级润色候选不应并入")
    if "她：……粥先来了。" not in sec:
        errs.append("例话节未抽出")
    if "验收" in sec:
        errs.append("验收节不应并入")
    blocks = anchor_blocks(sec)
    if not blocks or not any("她：" in l for b in blocks for l in b):
        errs.append("例话块抽取异常")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    a = ap.parse_args()
    if a.selftest:
        errs = selftest()
        print(f"selftest: {'PASS' if not errs else 'FAIL'}" + ("" if not errs else " ｜ " + "；".join(errs)))
        sys.exit(2 if errs else 0)
    if not BLUEPRINT.exists():
        print(f"蓝图正本不存在: {BLUEPRINT}")
        sys.exit(2)
    bp_text = BLUEPRINT.read_text(encoding="utf-8")
    cand_text = CANDIDATE.read_text(encoding="utf-8")
    sections = extract_sections(cand_text)
    merged = bp_text.rstrip() + MARK + sections
    OUT_DIR.mkdir(exist_ok=True)
    out = OUT_DIR / "灵魂蓝图.并入预演.txt"
    out.write_text(merged, encoding="utf-8", newline="\n")
    # 四关
    errs = []
    bp_lines = [l for l in bp_text.splitlines() if l != ""]
    from collections import Counter
    cm = Counter(merged.splitlines())
    lost = [l for l in bp_lines if cm[l] < 1]
    if lost:
        errs.append(f"零删除破坏: {len(lost)} 行丢失")
    red = ("400-161-9995", "010-82951332", "绝不提供任何自我伤害", "没有例外，没有情境，没有商量")
    if not all(s in merged for s in red):
        errs.append("红线不变式缺失")
    for marker in ("补强条款一", "开场白即风格合同", "漂移锚定节奏", "周检六维对齐"):
        if marker not in merged:
            errs.append(f"候选标记缺失: {marker}")
    lint_fails = []
    for bi, b in enumerate(anchor_blocks(sections), 1):
        e = lint_anchor(b)
        if e:
            lint_fails.append((bi, e))
    if lint_fails:
        errs.append(f"例话块 lint: {lint_fails}")
    h_bp = hashlib.md5(bp_text.encode("utf-8")).hexdigest()[:8]
    h_out = hashlib.md5(merged.encode("utf-8")).hexdigest()[:8]
    print(f"正本: {BLUEPRINT}（{len(bp_text.splitlines())} 行, md5 {h_bp}）——未写、未动")
    print(f"并入节: 补强条款×3 + 例话锚两节（句级润色候选默认不并入）")
    print(f"预演副本: {out}（{len(merged.splitlines())} 行, md5 {h_out}）")
    for bi, e in lint_fails:
        print(f"  lint 块{bi}: {e}")
    for l in lost[:5]:
        print("  LOST:", l[:50])
    print("预演结论:", "PASS —— 副本四关全过；正本操作已预演，待主人点头" if not errs else f"FAIL: {len(errs)} 项冲突")
    sys.exit(1 if errs else 0)


if __name__ == "__main__":
    main()
