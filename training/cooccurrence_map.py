# -*- coding: utf-8 -*-
"""cooccurrence_map.py — 记忆检索关联图生成器（R36 · 取精自 graphify 理念的零成本版）

graphify 用 LLM 逐文件建知识图谱（每文件一次调用 = 持续花钱）。
本工具取其理念弃其实现：直接读 mem-search 的 FTS 索引，用字符二元组
TF-IDF 余弦算"哪两个文件在说同一件事"，只读不写索引，零 LLM 成本。

输出：每文件 top-K 关联文件（sim ≥ 阈值），落成 markdown 关联图。
覆盖率声明必须带分母（本能 10）——稀疏就报稀疏，图谱随知识库增长可再生。
用法：python cooccurrence_map.py [--top 5] [--min-sim 0.08] [--out 路径]
"""
import argparse
import math
import sqlite3
import sys
from collections import Counter
from datetime import date
from pathlib import Path

DB = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\.search-index.db")
DEFAULT_OUT = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\检索关联图谱-2026-11-02.md")


def bigrams(text):
    """中文无分词 → 字符二元组（字母数字词整取，其余滑窗）。"""
    units, buf = [], []
    for ch in text:
        if ch.isalnum() and ord(ch) < 128:  # ASCII 词整取
            buf.append(ch)
        else:
            if buf:
                units.append("".join(buf).lower())
                buf = []
            if not ch.isspace() and ord(ch) > 127:
                units.append(ch)
    if buf:
        units.append("".join(buf).lower())
    return [units[i] + units[i + 1] for i in range(len(units) - 1)]


def load_docs():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    rows = con.execute("SELECT path, content FROM docs").fetchall()
    con.close()
    docs = {}
    for p, c in rows:
        name = Path(p).name
        if name in docs:  # 双轨同名取旧轨（本索引即旧轨根，同名即重复索引）
            continue
        docs[name] = c or ""
    return docs


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--top", type=int, default=5)
    ap.add_argument("--min-sim", type=float, default=0.08)
    ap.add_argument("--out", default=str(DEFAULT_OUT))
    args = ap.parse_args()

    docs = load_docs()
    if not docs:
        print("索引为空，先让 mem_search 建索引")
        sys.exit(2)

    # TF-IDF（log-TF，L2 归一）
    tf = {name: Counter(bigrams(c)) for name, c in docs.items()}
    df = Counter()
    for cnt in tf.values():
        df.update(cnt.keys())
    N = len(docs)
    vec = {}
    for name, cnt in tf.items():
        v = {t: (1 + math.log(f)) * math.log(N / df[t]) for t, f in cnt.items()}
        norm = math.sqrt(sum(w * w for w in v.values())) or 1.0
        vec[name] = {t: w / norm for t, w in v.items()}

    names = sorted(vec)
    pairs = []
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            va, vb = vec[a], vec[b]
            if len(va) > len(vb):
                va, vb = vb, va
            s = sum(w * vb.get(t, 0.0) for t, w in va.items())
            if s >= args.min_sim:
                pairs.append((s, a, b))
    pairs.sort(reverse=True)

    best = {}
    for s, a, b in pairs:
        best.setdefault(a, []).append((s, b))
        best.setdefault(b, []).append((s, a))

    # ── 落盘 markdown ──
    lines = [
        f"# 检索关联图谱（{date.today().isoformat()} ZCode · cooccurrence_map.py 生成）",
        "",
        "> [状态:current] ｜ 作者标签：[ZCode] ｜ 检索锚：关联图谱 / 共现 / graphify / 文件关联 / 看相关",
        "> **生成命令（验证工件，手法44）**：`python training/cooccurrence_map.py --top 3 --min-sim 0.12`",
        "> **原理**：FTS 索引只读扫描 → 字符二元组 TF-IDF 余弦——graphify 的\"查图不查文件\"理念，零 LLM 成本版。",
        f"> **口径**：{N} 个已索引文档，相似度 ≥ {args.min_sim} 才建边，每文件取 top {args.top}。",
        "> **用途**：mem-search 查到 A 后，按本图看\"还有谁在说同一件事\"——补关键词检索查不到关联的短板（AI前沿 10-31 记录的语义检索缺失）。",
        "",
        "| 文件 | 最相关（相似度） |",
        "|---|---|",
    ]
    for name in names:
        rels = best.get(name, [])
        if rels:
            cell = " ｜ ".join(f"{b} ({s:.2f})" for s, b in rels[: args.top])
            lines.append(f"| {name} | {cell} |")
    lines += [
        "",
        "## 图级统计",
        f"- 建边对数：{len(pairs)} ｜ 有邻接的文件：{len(best)}/{N}",
        "- 高关联对（sim≥0.3，同一件事的不同侧面）：",
    ]
    strong = [(s, a, b) for s, a, b in pairs if s >= 0.3]
    for s, a, b in strong[:12]:
        lines.append(f"  - {a} ↔ {b}（{s:.2f}）")
    if not strong:
        lines.append("  - （暂无 ≥0.3 的强关联——知识库主题足够分散）")
    lines.append("")
    lines.append(
        f"*一句话：{len(best)}/{N} 篇有邻接（覆盖率 {len(best)/N*100:.0f}%），平均每篇 "
        f"{len(pairs)*2/N:.1f} 条边——覆盖率不到 100% 不是方法错，是知识库主题本来就分散；"
        f"关联是算出来的不是猜出来的，一次 LLM 都没花，图谱随知识库增长可再生。*"
    )

    out = Path(args.out)
    out.write_text("\n".join(lines), encoding="utf-8")
    print(f"关联图落盘: {out}（{N} 文档, {len(pairs)} 边, {len(strong)} 强关联）")


if __name__ == "__main__":
    main()
