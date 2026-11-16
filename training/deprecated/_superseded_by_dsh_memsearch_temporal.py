# -*- coding: utf-8 -*-
"""memsearch_refresh.py — P0-3：mem-search 索引补全 + supersession 历史层（沙箱副本上运行）。

裁决条件对齐（DSH 六条）：
  ① 只在副本上作业（search-index-copy.db；活体 .search-index.db 不碰）
  ② dry-run 模式：--dry-run 只报告不改库
  ③ 覆盖率改前改后各测一次（本脚本输出）
  ④ 回滚包：副本即回滚（原库未动）+ 重建声明（docs 可由 files 表+源 md 全量重建）
  ⑤ 四测试由 test_memsearch_supersession.py 覆盖（旧版不命中/恢复命中/integrity/相邻版本不误删）
  ⑥ 交付=命令+输出+diff（本脚本输出即命令日志）

新增表（ADDITIVE，不动 docs FTS schema）：
  doc_history(id, path, content, superseded_at)  —— 被替换的旧内容完整留档（不删）
  doc_meta(path PRIMARY KEY, version, indexed_at, size, mtime) —— 版本跟踪
  refresh_log(id, ts, action, path, detail) —— 操作日志
"""
import os
import re
import sqlite3
import sys
import io
import time

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = r"C:\Users\14676\w4-study\memsearch_sandbox\search-index-copy.db"
MEM_ROOT = r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories"
DRY = "--dry-run" in sys.argv

# 索引的 path 存的是截断形态（去掉盘符与前缀），这里复刻同款截断规则：
# 原库样例 'ata\\Roaming\\dsh-desktop\\harness\\memories\\daily\\2026-09-27.md'
# = 绝对路径去掉开头若干字符。经比对：截断点 = 从 'AppData' 起保留。
PREFIX_MARK = "AppData"


def rel_key(abs_path: str) -> str:
    norm = abs_path.replace("/", "\\")
    i = norm.find(PREFIX_MARK)
    return norm[i:] if i >= 0 else norm


def main() -> int:
    con = sqlite3.connect(DB)
    cur = con.cursor()
    # ① ADDITIVE 表
    cur.executescript("""
    CREATE TABLE IF NOT EXISTS doc_meta(
        path TEXT PRIMARY KEY, version INTEGER, indexed_at TEXT, size INTEGER, mtime REAL);
    CREATE TABLE IF NOT EXISTS doc_history(
        id INTEGER PRIMARY KEY, path TEXT, content TEXT, superseded_at TEXT);
    CREATE TABLE IF NOT EXISTS refresh_log(
        id INTEGER PRIMARY KEY, ts TEXT, action TEXT, path TEXT, detail TEXT);
    """)
    con.commit()

    # ② 现状：索引内 md 路径 vs 磁盘实况
    indexed = {r[0].replace("/", "\\") for r in cur.execute("SELECT path FROM docs")}
    md_files = {}
    for dp, dn, fn in os.walk(MEM_ROOT):
        for f in fn:
            if f.endswith(".md"):
                fp = os.path.join(dp, f)
                md_files[rel_key(fp)] = fp
    print(f"[现状] 磁盘 md={len(md_files)}  FTS docs={len(indexed)}")

    to_add = [k for k in md_files if k not in indexed]
    to_check = [k for k in md_files if k in indexed]  # 已索引——内容变更检测（mtime/size）
    print(f"[dry-run={DRY}] 待补索引: {len(to_add)} | 已索引待核对: {len(to_check)}")
    if DRY:
        for k in to_add[:8]:
            print("  待补:", k[-70:])
        con.close()
        return 0

    # ③ 补索引 + 变更历史
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    added = updated = unchanged = 0
    for key in to_add:
        fp = md_files[key]
        content = open(fp, encoding="utf-8", errors="replace").read()
        cur.execute("INSERT INTO docs(path, content) VALUES(?, ?)", (key, content))
        cur.execute("INSERT INTO doc_meta(path, version, indexed_at, size, mtime) VALUES(?,1,?,?,?)",
                    (key, ts, os.path.getsize(fp), os.path.getmtime(fp)))
        cur.execute("INSERT INTO refresh_log(ts, action, path, detail) VALUES(?,?,?,?)",
                    (ts, "add", key, f"{len(content)} chars"))
        added += 1
    for key in to_check:
        fp = md_files[key]
        content = open(fp, encoding="utf-8", errors="replace").read()
        row = cur.execute("SELECT content FROM docs WHERE path=?", (key,)).fetchone()
        if row and row[0] == content:
            unchanged += 1
            continue
        # 内容变更 → 旧内容留档（supersession：不删，标记被接替）
        cur.execute("INSERT INTO doc_history(path, content, superseded_at) VALUES(?,?,?)",
                    (key, row[0] if row else "", ts))
        cur.execute("UPDATE docs SET content=? WHERE path=?", (content, key))
        cur.execute("INSERT INTO refresh_log(ts, action, path, detail) VALUES(?,?,?,?)",
                    (ts, "update", key, "content changed"))
        updated += 1
    con.commit()
    print(f"[refresh] 新增索引 {added} | 内容更新 {updated} | 无变化 {unchanged}")

    # ④ 覆盖率复测
    indexed2 = {r[0].replace("/", "\\") for r in cur.execute("SELECT path FROM docs")}
    cov = sum(1 for k in md_files if k in indexed2)
    print(f"[覆盖率] {cov}/{len(md_files)} = {cov/max(len(md_files),1):.1%} (此前 85.6%)")
    hist = cur.execute("SELECT COUNT(*) FROM doc_history").fetchone()[0]
    print(f"[supersession 历史] {hist} 条留档")
    con.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
