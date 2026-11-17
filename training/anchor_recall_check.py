# -*- coding: utf-8 -*-
"""anchor_recall_check.py — 检索锚自可达闸（2026-11-02 R47 · 手法41 的机器化）

手法 41：关键词是检索口不是摘要——写偏了，这条记忆等于不存在。
本工具把这句变成断言：每个知识文件头部的「检索锚：A / B / C」逐词试查 FTS，
**该文件自己必须能被自己的锚词查到**——查不到的锚=装饰品，点名返工。

范围：memories 根级 *.md + pending-skills/*/SKILL.md + 文件地图/*.md（与索引同源）。
规则：
  · 每文件取前 3 个锚词（含 ≥3 字的才算有效——trigram 限制，2 字锚本身是缺陷）
  · 任一锚词 MATCH 命中本文件 → 自可达 ✓；全都不中 → ✗（写偏/被索引漏/分词坑）
  · 锚词含连字符 → 加引号防 NOT 算符坑
用法：python anchor_recall_check.py [--json]
"""
import json
import re
import sqlite3
import sys
from pathlib import Path

if sys.stdout is None:
    sys.stdout = open(__import__("os").devnull, "w", encoding="utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

MEM = Path.home() / "AppData/Roaming/dsh-desktop/harness/memories"
DB = MEM / ".search-index.db"
ANCHOR_RE = re.compile(r"检索锚[:：]\s*(.+)")


def collect_files():
    files = list(MEM.glob("*.md"))
    files += list((MEM / "文件地图").glob("*.md"))
    files += list((MEM / "pending-skills").glob("*/SKILL.md"))
    return sorted(set(files))


def anchors_of(text):
    m = ANCHOR_RE.search(text[:1500])  # 只看头部
    if not m:
        return []
    raw = m.group(1)
    terms = re.split(r"[／/、,，\s]+", raw)
    out = []
    for t in terms:
        t = t.strip().strip("·")
        if len(t) >= 3:  # trigram 下限（本能 1）
            out.append(t)
        elif t:
            out.append(("2字缺陷", t))  # 标记为缺陷占位
    return out


def main():
    con = sqlite3.connect(f"file:{DB}?mode=ro", uri=True)
    files = collect_files()
    ok = fail = no_anchor = short_anchor = 0
    failures = []
    for f in files:
        try:
            text = f.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        name = f.name
        terms = anchors_of(text)
        if not terms:
            no_anchor += 1
            continue
        short_anchor += sum(1 for t in terms if isinstance(t, tuple))
        valid = [t for t in terms if isinstance(t, str)][:3]
        if not valid:
            fail += 1
            failures.append((name, "锚词全为 2 字（trigram 查不到）"))
            continue
        hit = False
        tried = []
        for t in valid:
            q = f'"{t}"' if "-" in t else t
            tried.append(t)
            try:
                rows = con.execute("SELECT path FROM docs WHERE docs MATCH ? LIMIT 30", (q,)).fetchall()
            except sqlite3.OperationalError:
                continue
            if any(r[0].endswith(str(f)) or r[0] == str(f) for r in rows):
                hit = True
                break
        if hit:
            ok += 1
        else:
            fail += 1
            failures.append((name, f"锚词{'、'.join(tried)}均查不到本文件"))
    con.close()

    total = ok + fail + no_anchor
    print("═" * 60)
    print("检索锚自可达闸 · 手法41 机器化")
    print("═" * 60)
    print(f"  带锚文件 {ok + fail}：自可达 ✓ {ok} ｜ 查不到自己 ✗ {fail}")
    print(f"  无锚文件：{no_anchor}（不强制，但等于检索盲区）")
    print(f"  2 字锚 {short_anchor} 处：trigram 限制（非缺陷——2 字词无法建 3 字索引，文件仍经其他锚可达；批量改写留作者裁决）")
    if failures:
        print("  ✗ 返工清单：")
        for n, why in failures[:10]:
            print(f"    · {n}: {why}")
    print("─" * 60)
    print(f"口径：{total}/{len(files)} 文件有锚 ｜ 自可达率 {ok}/{ok + fail}"
          + ("" if ok + fail else "（无从考）"))
    sys.exit(2 if fail else 0)


if __name__ == "__main__":
    main()
