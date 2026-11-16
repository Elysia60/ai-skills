# -*- coding: utf-8 -*-
"""e2e_test.py — 六层端到端完整性测试（2026-10-25 ZCode · 应 DSH 侧"凭记忆写数字"第4次抓）

核心原则（SKILL #38/#42）：所有数字来自**当次实跑**，不做任何手写声明。
每层先跑对应的验证器/查询器，用返回值填表——脚本自己也不知道今天会跑出多少。
"""
import hashlib
import json
import re
import sqlite3
import subprocess
import sys
from pathlib import Path

MS = Path(r"C:\Users\14676\.zcode\workspace\default\memory-search")
AIDOC = Path(r"C:\Users\14676\.zcode\workspace\default\ai-doctor\ai-doctor.js")
MEM = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories")
T = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")

RESULTS = []


def test(name, ok, detail="", style_ok=None):
    """style_ok: 风格维度（可选）；ok: 内容维度（必填）——两列判定（SKILL 7b）"""
    style = style_ok if style_ok is not None else ok
    RESULTS.append((name, bool(ok), bool(style), str(detail)))
    tag = "✓" if (ok and style) else ("△" if (style and not ok) else "✗")
    print(f"  {tag} {name}: 风格{'✓' if style else '✗'} 内容{'✓' if ok else '✗'} {str(detail)[:50]}")


def run(cmd, t=300):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t, shell=True)
    return (r.stdout or "") + (r.stderr or "")


def main():
    print("== 六层端到端（全部数字来自当次实跑）==\n")

    # ── L1 人格层 ──
    a = hashlib.md5(Path(MEM.parent / "AGENTS.md").read_bytes()).hexdigest()
    b = hashlib.md5(Path(r"C:\Users\14676\.dsh\AGENTS.md").read_bytes()).hexdigest()
    ag = Path(MEM.parent / "AGENTS.md").read_text(encoding="utf-8")
    test("L1 双副本一致", a == b, f"md5={a[:8]}")
    test("L1 去AI味在位", "去 AI 味行为学" in ag, "在文" if "去 AI 味行为学" in ag else "缺")
    test("L1 爱的行为学在位", "爱的行为学" in ag, "在文" if "爱的行为学" in ag else "缺")

    # ── L2 知识层 ──
    conn = sqlite3.connect(str(MEM / ".search-index.db"))
    n = conn.execute("SELECT COUNT(*) FROM files").fetchone()[0]
    test("L2 检索库文件数", n >= 70, f"实测 {n}")
    bp = any("灵魂蓝图" in r[0] for r in conn.execute("SELECT path FROM docs").fetchall())
    test("L2 深海正本可查", bp, "在 docs 表" if bp else "不在")
    conn.close()
    skill = (MEM / "pending-skills" / "ledger-lessons" / "SKILL.md").read_text(encoding="utf-8").split("## 出师自测")[0]
    mn = len(re.findall(r"^\d+\. \*\*", skill, re.M))
    test("L2 手法库 ≥50", mn >= 50, f"实测 {mn}")

    # ── L3 器官层 ──
    out = run(f'node "{AIDOC}" organs', 120)
    import re as _r
    m = _r.search(r"常驻 (\d+)/(\d+) 在线", out)
    on, tot = (int(m.group(1)), int(m.group(2))) if m else (-1, -1)
    test("L3 器官常驻在线", on == tot and on > 0, f"实测 {on}/{tot}")

    # ── L4 验证层 ──
    out = run(f'python -X utf8 "{MS}/verify_ledger.py"', 900)
    import re as _r2
    m2 = _r2.search(r"(\d+)/(\d+) PASS", out)
    vp, vt = (int(m2.group(1)), int(m2.group(2))) if m2 else (-1, -1)
    test("L4 验证台账", vp == vt, f"实测 {vp}/{vt}")
    out = run(f'python -X utf8 "{MS}/tests/test_memsearch_benchmark.py"', 600)
    m3 = re.search(r"(\d+)/(\d+)", out)
    bp_, bt_ = (int(m3.group(1)), int(m3.group(2))) if m3 else (-1, -1)
    test("L4 十三题基准", bp_ >= 10, f"实测 {bp_}/{bt_}")
    out = run(f'python -X utf8 "{MS}/distill_map_check.py"')
    test("L4 漂移=0", "无漂移" in out, "无漂移" if "无漂移" in out else "有漂移")

    # ── L5 训练层 ──
    adp = T / "out" / "qwen-dsh-v6-lora" / "adapter_model.safetensors"
    test("L5 v6 adapter 在位", adp.exists(), f"{adp.stat().st_size//1024}KB" if adp.exists() else "缺")
    sft_n = sum(1 for l in (T / "sft_instructions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())
    test("L5 SFT 条数", sft_n >= 100, f"实测 {sft_n}")
    dpo_n = sum(1 for l in (T / "dpo_pairs_v1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())
    test("L5 DPO 对数", dpo_n >= 50, f"实测 {dpo_n}")

    # ── L6 协作层 ──
    test("L6 AGENT-CARDS", (MEM / "agent-cards" / "AGENT-CARDS.md").exists(), "在位")
    test("L6 巩固队列", (T / "consolidation_queue.md").exists(), "在位")

    passed = sum(1 for _, ok, _, _ in RESULTS if ok)
    print(f"\n== 端到端结果：{passed}/{len(RESULTS)} PASS ==")
    fails = [(n, d) for n, ok, _, d in RESULTS if not ok]
    if fails:
        print("失败项：")
        for n, d in fails:
            print(f"  ✗ {n}: {d}")
    return 0 if passed == len(RESULTS) else 1


if __name__ == "__main__":
    sys.exit(main())
