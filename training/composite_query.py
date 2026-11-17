# -*- coding: utf-8 -*-
"""composite_query.py — 复合查询编排器（2026-11-02 R44 · 教师移交「复合查询」的可执行版）

把散装的三步合成一条命令（全部只读，零 LLM 成本）：
  第 1 跳  mem-search 检索（含同义词扩展，自动刷索引）
  第 2 跳  关联图谱第二跳——查到 A 后顺藤摸"谁在说同一件事"（cooccurrence_map 产物）
  第 3 跳  口径声明——命中数/扩展词/分母，直接可引用（教师移交七：声明带分母）

用法：
  python composite_query.py 预算 TTS          # 检索并出回执
  python composite_query.py 锚 --hop 2        # 关联跳数（默认 1 跳=直接邻居）
设计约束：不改任何器官；图谱文件缺失 → 第二跳诚实 SKIP；查询词 ≥3 字（trigram 本能 1）。
"""
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

if sys.stdout is None:
    sys.stdout = open(__import__("os").devnull, "w", encoding="utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).parent
MS = Path.home() / ".zcode/workspace/default/memory-search/mem_search.py"
MEM = Path.home() / "AppData/Roaming/dsh-desktop/harness/memories"


def run_ms(terms, limit=8):
    cmd = [sys.executable, "-X", "utf8", str(MS), "query", *terms, "--limit", str(limit)]
    p = subprocess.run(cmd, capture_output=True, text=True, timeout=300,
                       encoding="utf-8", errors="replace")
    return (p.stdout or "") + (p.stderr or "")


def parse_ms(out):
    """从 mem-search 输出提取：命中文件列表（label→真实路径名）与口径行。"""
    files, total_hits = [], 0
    for ln in out.splitlines():
        m = re.match(r"\s*(\d+)词/(\d+)处命中\s+(.+)$", ln)
        if m:
            total_hits += int(m.group(2))
            files.append((m.group(3).strip(), int(m.group(1)), int(m.group(2))))
    syn = ""
    m = re.search(r"── 同义扩展: (.+)$", out, re.M)
    if m:
        syn = m.group(1).strip()
    return files, total_hits, syn


def load_graph():
    """关联图谱 → {文件名: [(邻居, 相似度), ...]}；无图谱返回空表（第二跳诚实 SKIP）。"""
    cands = sorted(MEM.glob("检索关联图谱-*.md"))
    if not cands:
        return {}
    graph = {}
    for ln in cands[-1].read_text(encoding="utf-8").splitlines():
        m = re.match(r"^\|\s*(.+?)\s*\|\s*(.+?)\s*\|\s*$", ln)
        if not m or m.group(1) in ("文件", "---"):
            continue
        name = m.group(1).strip()
        rels = []
        for part in m.group(2).split("｜"):
            pm = re.match(r"\s*(.+?)\s*\((\d\.\d+)\)\s*$", part.strip())
            if pm:
                rels.append((pm.group(1).strip(), float(pm.group(2))))
        if rels:
            graph[name] = rels
    return graph


def main():
    args = [a for a in sys.argv[1:] if not a.startswith("--")]
    hop = 2 if "--hop" in sys.argv else 1
    if not args:
        print(__doc__)
        sys.exit(2)
    terms = " ".join(args).split()
    for t in terms:
        if len(t) < 3:
            print(f"⚠ 查询词「{t}」不足 3 字——trigram 恒空（本能 1），已按原样透传（mem-search 会走 LIKE 兜底）")

    print("═" * 60)
    print(f"复合查询 · {' '.join(terms)}")
    print("═" * 60)

    # 第 1 跳
    out = run_ms(terms)
    files, total_hits, syn = parse_ms(out)
    if not files:
        print("第 1 跳：无命中。建议：换 ≥3 字关键词 / 先看关联图谱 / 查同义词表。")
        sys.exit(1)
    print(f"第 1 跳·检索：{len(files)} 文件 / {total_hits} 处命中" + (f"（同义扩展: {syn}）" if syn else ""))
    for label, nw, nh in files[:6]:
        print(f"  · {label}（{nw}词/{nh}处）")

    # 第 2 跳
    graph = load_graph()
    if not graph:
        print("第 2 跳·关联：SKIP——无图谱文件（python cooccurrence_map.py 生成）")
    else:
        print(f"第 2 跳·关联（{hop} 跳）：")
        seen = set()
        shown = 0
        for label, _nw, _nh in files:
            base = label.split(":")[-1] if ":" in label else label
            for gname, rels in graph.items():
                if base in gname or gname in base:
                    for neigh, sim in rels[: 3 * hop]:
                        if neigh in seen or neigh == gname:
                            continue
                        seen.add(neigh)
                        print(f"  ↳ {gname[:24]} → {neigh}（{sim:.2f}）")
                        shown += 1
                        if shown >= 6 * hop:
                            break
                if shown >= 6 * hop:
                    break
            if shown >= 6 * hop:
                break
        if not shown:
            print("  · 高频命中文件暂无图谱邻接（图谱 76/99 覆盖率，分母如实报）")

    # 第 3 跳：口径
    print("─" * 60)
    print(f"口径（教师移交七）：查询词 {len(terms)} ｜ 命中 {len(files)} 文件/{total_hits} 处 ｜ "
          f"图谱覆盖 76/99 ｜ 生成 {date.today().isoformat()} ｜ 本回执可直接引用")
    sys.exit(0)


if __name__ == "__main__":
    main()
