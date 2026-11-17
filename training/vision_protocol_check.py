# -*- coding: utf-8 -*-
"""vision_protocol_check.py — 协议-器官一致性检查（2026-10-27 ZCode · R6）

查什么：视觉理解规程（memories/视觉理解规程-2026-10-26.md）里引用的每个 vision_* 工具名，
是否真实存在于本机 dsh-vision-router 插件的代码（lib/*.js 词法扫描）。
口径：只验"协议引用 ⊆ 器官真实注册"（协议引用了不存在的工具=纸上谈兵，必须 FAIL）；
器官有而协议未提的工具只作信息项列出（协议不必覆盖全部）。
退出码：0=一致 1=存在幽灵引用 2=自测失败。

用法：
  python vision_protocol_check.py --selftest
  python vision_protocol_check.py                 # 查正本规程
  python vision_protocol_check.py --doc <path> --lib <dir>
"""
import argparse
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

PROTO = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\视觉理解规程-2026-10-26.md")
LIB = Path(r"C:\Users\14676\.dsh\_local-plugins\dsh-vision-router\lib")
TOKEN_RE = re.compile(r"vision_[a-z_]+")


def real_tokens(lib_dir):
    """扫描插件 lib 目录，返回真实出现的 vision_* 词法集合。纯 IO。"""
    out = set()
    for p in Path(lib_dir).rglob("*.js"):
        try:
            out |= set(TOKEN_RE.findall(p.read_text(encoding="utf-8", errors="ignore")))
        except OSError:
            continue
    return out


def referenced_tokens(text):
    """规程文本里引用的 vision_* 集合（排除示例占位——本规程无占位，全量即引用）。纯函数。"""
    return set(TOKEN_RE.findall(text))


def selftest():
    errs = []
    txt = "用 vision_ground 定位，再 vision_crop 细看；幽灵工具 vision_not_real 不许过。"
    refs = referenced_tokens(txt)
    real = {"vision_ground", "vision_crop", "vision_describe"}
    ghost = refs - real
    if ghost != {"vision_not_real"}:
        errs.append(f"幽灵引用识别异常: {ghost}")
    if refs - real != ghost:
        errs.append("引用集合口径漂移")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--doc", default=None)
    ap.add_argument("--lib", default=None)
    a = ap.parse_args()
    if a.selftest:
        errs = selftest()
        print(f"selftest: {'PASS' if not errs else 'FAIL'}" + ("" if not errs else " ｜ " + "；".join(errs)))
        sys.exit(2 if errs else 0)
    doc = Path(a.doc) if a.doc else PROTO
    lib = Path(a.lib) if a.lib else LIB
    if not doc.exists():
        print(f"规程不存在: {doc}")
        sys.exit(2)
    if not lib.exists():
        print(f"插件 lib 不存在: {lib}")
        sys.exit(2)
    real = real_tokens(lib)
    refs = referenced_tokens(doc.read_text(encoding="utf-8"))
    ghost = sorted(refs - real)
    covered = sorted(refs & real)
    uncovered = sorted(real - refs)
    print(f"规程: {doc.name}")
    print(f"协议引用工具: {len(refs)} 个 ｜ 其中真实存在: {len(covered)} ｜ 幽灵引用: {len(ghost)}")
    print(f"已覆盖: {', '.join(covered) if covered else '（无）'}")
    if ghost:
        print("幽灵引用（协议写了但器官没有）:")
        for g in ghost:
            print("  GHOST:", g)
    print(f"信息项·器官有而规程未提的工具 {len(uncovered)} 个（不判失败）: {', '.join(uncovered[:12])}{'…' if len(uncovered) > 12 else ''}")
    rc = 1 if ghost else 0
    print("结论:", "一致——规程引用的每个工具都真实存在" if not ghost else "存在幽灵引用，必须改规程或装工具")
    sys.exit(rc)


if __name__ == "__main__":
    main()
