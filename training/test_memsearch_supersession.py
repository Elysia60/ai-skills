# -*- coding: utf-8 -*-
"""P0-3 四条件测试 v3（净化基线 + FTS5 引号修正 + 干净四阶段）。"""
import os
import sqlite3
import subprocess
import sys
import io

sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding="utf-8", errors="replace")

DB = r"C:\Users\14676\w4-study\memsearch_sandbox\search-index-copy.db"
DAILY_DIR = r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\daily"

TEST_MD = None
for f in sorted(os.listdir(DAILY_DIR)):
    if "2026-11-14" in f:
        TEST_MD = os.path.join(DAILY_DIR, f)
assert TEST_MD, "测试文件未找到"

# ① 净化：去掉此前测试注入的标记行，还原真基线
lines = open(TEST_MD, encoding="utf-8", errors="replace").read().splitlines()
true_orig = "\n".join(l for l in lines if "ZZOLDMARK77" not in l and "ZZNEWMARK42" not in l)
open(TEST_MD, "w", encoding="utf-8").write(true_orig + "\n")
print("① 基线净化完成（去除历史测试标记）")


def fresh_con():
    return sqlite3.connect(DB)


def fts_match(phrase: str) -> int:
    con = fresh_con()
    try:
        quoted = '"' + phrase.replace('"', '""') + '"'
        return con.execute(
            "SELECT COUNT(*) FROM docs WHERE docs MATCH ?", (quoted,)).fetchone()[0]
    except Exception as e:
        print("  MATCH 异常:", str(e)[:80])
        return -1
    finally:
        con.close()


def refresh() -> int:
    con = fresh_con()
    con.close()  # 先关测试连接，避免库锁
    r = subprocess.run([sys.executable, "memsearch_refresh.py"],
                       capture_output=True, text=True, encoding="utf-8", errors="replace")
    if r.returncode != 0:
        print("  ⚠ refresh rc=", r.returncode, "| stderr:", r.stderr[-200:])
    return r.returncode


def find_key():
    con = fresh_con()
    key = None
    for pid, pth in con.execute("SELECT rowid, path FROM docs"):
        norm = pth.replace("/", "\\")
        if norm.endswith("daily\\2026-11-14.md"):
            key = (pid, pth)
            break
    con.close()
    return key


# ② Phase A：加标记 → refresh → 新标记可检
open(TEST_MD, "a", encoding="utf-8").write("\nZZADDMARK42\n")
rc_a = refresh()
a_add = fts_match("ZZADDMARK42")
print(f"② Phase A: rc={rc_a} 新标记命中={a_add} (期望 1)")

# ③ Phase B：移除标记 → refresh → 旧标记失效 + 历史留档
open(TEST_MD, "w", encoding="utf-8").write(true_orig + "\n")
rc_b = refresh()
b_gone = fts_match("ZZADDMARK42")
con = fresh_con()
hist = con.execute("SELECT COUNT(*) FROM doc_history WHERE path LIKE '%daily%2026-11-14%' OR path LIKE '%daily%'").fetchone()[0]
meta = con.execute("SELECT COUNT(*) FROM doc_meta").fetchone()[0]
con.close()
print(f"③ Phase B: rc={rc_b} 旧标记残留={b_gone} (期望 0) | 历史留档={hist} | doc_meta={meta}")

# ④ Phase C：integrity + 相邻不误删
con = fresh_con()
ic = con.execute("PRAGMA integrity_check").fetchone()[0]
con.execute("INSERT INTO docs(docs) VALUES('integrity-check')")
probe = con.execute('SELECT COUNT(*) FROM docs WHERE docs MATCH \'"integrity-check"\'').fetchone()[0]
neighbor = con.execute('SELECT COUNT(*) FROM docs WHERE docs MATCH \'\"2026-09-27\"\'').fetchone()[0]
con.commit()
con.close()
print(f"④ Phase C: integrity_check={ic} FTS探针={probe} 相邻(2026-09-27)={neighbor}")

# ⑤ 还原真基线
open(TEST_MD, "w", encoding="utf-8").write(true_orig + "\n")
print("⑤ 测试文件已还原真基线")
