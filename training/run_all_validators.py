# -*- coding: utf-8 -*-
"""run_all_validators.py — 战役级全量回归运行器（2026-10-27 ZCode · R13）

串行执行 R1-R12 全部验证器（快照断言已升级为单调不变式，可无限重跑），
汇总：每轮 rc / 断言数 / 失败数，战役级总断言与判定。
退出码：0=全绿 1=有轮失败。用法：python run_all_validators.py [--quick R后缀,R后缀]
"""
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
ALL = ["mega_validation_320k.py"] + [f"mega_validation_320k_r{i}.py" for i in range(2, 13)]

def main():
    quick = None
    if "--quick" in sys.argv:
        quick = [f"mega_validation_320k{'' if s == '' else '_r' + s}.py" for s in
                 sys.argv[sys.argv.index("--quick") + 1].split(",")]
    files = quick or ALL
    rows, total_asserts, total_fails, t0 = [], 0, 0, time.time()
    for name in files:
        p = TRAIN / name
        if not p.exists():
            rows.append((name, "MISSING", 0, 0))
            continue
        r = subprocess.run([sys.executable, str(p)], capture_output=True, text=True, timeout=900)
        out = r.stdout + r.stderr
        m_a = re.search(r"总断言 ([\d,]+) 次", out)
        m_f = re.search(r"失败 (\d+) 条", out)
        asserts = int(m_a.group(1).replace(",", "")) if m_a else 0
        fails = int(m_f.group(1)) if m_f else (0 if r.returncode == 0 else -1)
        total_asserts += max(asserts, 0)
        total_fails += max(fails, 0)
        rows.append((name, "PASS" if r.returncode == 0 else "FAIL", asserts, fails))
    dt = time.time() - t0
    print("═" * 60)
    print("战役级全量回归 · 汇总")
    print("═" * 60)
    for name, verdict, asserts, fails in rows:
        print(f"  {verdict}  {name:36s} 断言 {asserts:>9,}  失败 {fails}")
    print("─" * 60)
    print(f"总断言 {total_asserts:,} 次 ｜ 总失败 {total_fails} ｜ 耗时 {dt/60:.1f} 分钟 ｜ 轮数 {len(rows)}")
    ok = all(v == "PASS" for _, v, _, _ in rows)
    print("战役判定：", "全绿 —— 十二轮不变式同时成立" if ok else "有失败轮（见上）")
    sys.exit(0 if ok else 1)

if __name__ == "__main__":
    main()
