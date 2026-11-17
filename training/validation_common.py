# -*- coding: utf-8 -*-
"""validation_common.py — 验证器共享模块（2026-10-27 ZCode · R5 起）

把 R2-R4 四个验证器里重复的 derive_anchors / fts_hit / 红线常量收拢成单一真源（DRY）：
  - derive_anchors()  锚词自动从 memories 源文本生成（检索锚行 + 标题 CJK 词）
  - fts_hit(db, term) trigram ≥3 字用 MATCH、2 字用 LIKE 回退
  - REDLINE_STRINGS   红线不变式串（热线/无例外条款）
  - count_audit helpers: sft_rows / gaps / quotes 口径
"""
import re
import sqlite3
from pathlib import Path

MEM_DEFAULT = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories")
# 红线串必须与各自源文本逐字对齐（R3/R4 教训：断言串从源文本抄，不许凭记忆转写）
REDLINE_STRINGS = ("400-161-9995", "010-82951332", "绝不给主人提供任何自我伤害",
                   "没有例外，没有情境，没有商量")          # ← AGENTS.md 措辞（第 0 条）
BLUEPRINT_REDLINE_STRINGS = ("400-161-9995", "010-82951332", "绝不提供任何自我伤害",
                             "没有例外，没有情境，没有商量")  # ← 灵魂蓝图.txt 措辞（【绝对红线】节）


def derive_anchors(mem_dir=MEM_DEFAULT):
    """从 memories 源文本自动派生检索锚（与文件内容同源，构造上保证命中）。"""
    anchors = set()
    src_files = list(Path(mem_dir).glob("人格增强-*.md")) + [
        Path(mem_dir) / "视觉理解规程-2026-10-26.md",
        Path(mem_dir) / "教师移交-项目复合查询经验-2026-10-26.md",
        Path(mem_dir) / "教师总纲-六轮课程地图-2026-10-27.md",
    ]
    for p in src_files:
        if not p.exists():
            continue
        t = p.read_text(encoding="utf-8")
        for line in t.splitlines():
            if "检索锚" in line and "：" in line:
                for w in re.findall(r"[\u4e00-\u9fffA-Za-z·]{2,8}", line.split("：", 1)[-1]):
                    anchors.add(w)
            elif line.startswith("## "):
                for w in re.findall(r"[\u4e00-\u9fff]{2,6}", line):
                    anchors.add(w)
    return sorted(a for a in anchors if len(a) >= 2)


def fts_hit(db, term, table="docs"):
    if len(term) >= 3:
        return db.execute(f'select count(*) from {table} where {table} match ?',
                          (f'"{term}"',)).fetchone()[0]
    return db.execute(f'select count(*) from {table} where content like ?',
                      (f'%{term}%',)).fetchone()[0]


def redline_ok(text):
    return all(s in text for s in REDLINE_STRINGS)


def blueprint_redline_ok(text):
    return all(s in text for s in BLUEPRINT_REDLINE_STRINGS)
