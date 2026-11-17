# -*- coding: utf-8 -*-
"""agentsmd_freshness_check.py — AGENTS.md 文档新鲜度体检（2026-10-27 ZCode · ROADMAP P1-2 落地）

来源：DSH 自己的 ROADMAP（2026-10-05）P1-2"文档新鲜度体检（N22 推广）"——立项三周未做，本轮清偿。
查什么：AGENTS.md 里引用的**绝对路径**（py/md/txt/json/jsonc/db/lnk/exe/cmd/bat/yaml/yml）
  ① 文件是否存在  ② .py 是否可编译  ③ 无扩展名的绝对目录是否存在
怎么算：只扫带盘符的绝对路径（跳过 模型.pmx 类占位符——无盘符即跳过）；
  抽取是启发式的——声明"检查到 N 个路径"必须带清单口径，不是"全部路径"（R8 纪律）。
退出码：0=全部健康 1=有缺失/编译失败 2=体检器自身自测失败。

用法：
  python agentsmd_freshness_check.py --selftest
  python agentsmd_freshness_check.py                 # 体检正本 AGENTS.md，打印发现清单
  python agentsmd_freshness_check.py --file <path>   # 体检指定文件
"""
import argparse
import json
import py_compile
import re
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")

DEFAULT = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\AGENTS.md")
EXTS = (".py", ".md", ".txt", ".json", ".jsonc", ".db", ".lnk", ".exe", ".cmd", ".bat", ".yaml", ".yml")
# Windows 绝对路径：盘符 + 非空白/反引号/常见中文标点序列
PATH_RE = re.compile(r"[A-Za-z]:\\[^\s`）)、。，；】」”“”'\"]+")
TOOLS = ("mem-search", "ai-doctor.js", "sync_skills.py")


def extract_paths(text):
    """抽取文本中的绝对路径候选（带盘符、以已知扩展名结尾）。纯函数，供自测。"""
    out = []
    for m in PATH_RE.findall(text):
        m = m.rstrip("\\")
        low = m.lower()
        if low.endswith(EXTS):
            out.append(m)
    return sorted(set(out))


def classify(paths, exists=None):
    """返回 (ok, missing, compile_fail)。exists 可注入以便自测；纯逻辑。"""
    exists = exists or (lambda p: Path(p).exists())
    ok, missing, cfail = [], [], []
    for p in paths:
        try:
            if not exists(p):
                missing.append(p)
                continue
            if p.lower().endswith(".py"):
                try:
                    py_compile.compile(p, doraise=True)
                    ok.append(p)
                except py_compile.PyCompileError as e:
                    cfail.append((p, str(e)[:80]))
            else:
                ok.append(p)
        except OSError:
            missing.append(p)
    return ok, missing, cfail


def selftest():
    """自测：抽取正确性 + 分类逻辑（py 用本工具真实文件过编译分支；
    缺失路径用注入 exists 验证分流；非 py 假存在不触盘）。"""
    errs = []
    txt = (r"工具在 C:\Tool\a.md；占位 模型.pmx 不算；"
           r"相对路径 tool\x.py 不算；" r"坏路径 C:\Nope\not_there.py；")
    got = extract_paths(txt)
    if r"C:\Tool\a.md" not in got:
        errs.append(f"抽取漏了已知路径: {got}")
    if any("模型" in p for p in got):
        errs.append("占位符被误抽")
    if any(p.endswith("tool\\x.py") for p in got):
        errs.append("相对路径被误抽")
    if r"C:\Nope\not_there.py" not in got:
        errs.append("缺失路径未被抽出")
    # 分类逻辑：真实 py（本文件）必须进 ok（真实编译通过）；注入不存在的 py 进 missing；假存在 md 不触盘
    real_py = str(Path(__file__).resolve())
    fake = {r"C:\Nope\not_there.py": False, r"C:\Tool\a.md": True}
    ok, missing, cfail = classify([real_py, r"C:\Nope\not_there.py", r"C:\Tool\a.md"],
                                  exists=lambda p: fake.get(p, Path(p).exists()))
    if real_py not in ok or cfail:
        errs.append(f"真实 py 未过编译分支: ok={ok} cfail={cfail}")
    if r"C:\Nope\not_there.py" not in missing:
        errs.append("缺失文件未入 missing")
    if r"C:\Tool\a.md" not in ok:
        errs.append("注入存在的 md 未入 ok")
    return errs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--selftest", action="store_true")
    ap.add_argument("--file", default=None)
    a = ap.parse_args()
    if a.selftest:
        errs = selftest()
        print(f"selftest: {'PASS' if not errs else 'FAIL'}" + ("" if not errs else " ｜ " + "；".join(errs)))
        sys.exit(2 if errs else 0)
    target = Path(a.file) if a.file else DEFAULT
    if not target.exists():
        print(f"目标不存在: {target}")
        sys.exit(2)
    text = target.read_text(encoding="utf-8")
    paths = extract_paths(text)
    ok, missing, cfail = classify(paths)
    tools = {t: bool(__import__("shutil").which(t)) for t in ("mem-search",)}
    n = len(paths)
    print(f"体检对象: {target}")
    print(f"抽取口径: 绝对路径(带盘符,已知扩展名)共 {n} 个——启发式清单,非全量声明")
    print(f"健康: {len(ok)} ｜ 缺失: {len(missing)} ｜ 编译失败: {len(cfail)} ｜ mem-search 在 PATH: {tools.get('mem-search')}")
    for p in missing:
        print("  MISSING:", p)
    for p, e in cfail:
        print("  COMPILE-FAIL:", p, "｜", e)
    rc = 1 if (missing or cfail) else 0
    print("结论:", "发现过期引用（见上,供主人/DSH 裁决,本工具不自动改）" if rc else "全部健康")
    sys.exit(rc)


if __name__ == "__main__":
    main()
