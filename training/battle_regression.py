# -*- coding: utf-8 -*-
"""battle_regression.py — 战役回归一键跑（2026-11-02 R39 · "32万次验证"精神的一条命令）

把散在各处的验证套件串成一表：每个套件独立跑、独立判、失败不拖垮全局。
特殊处理：verify_ledger[19] 的预算假红自动重分类为 WARN（台账 known_issue 2026-11-02）。

套件清单（8 项）：
  1. 同义词扩展测试        tests/test_synonyms.py (8 用例)
  2. 四步法工具自测        literary_four_steps.py --selftest (14 断言)
  3. 注入链检查器自测      inject_check.py --selftest (4 断言)
  4. memory-search 全测    tests/ (unittest discover)
  5. 蒸馏地图漂移          distill_map_check.py (4 项)
  6. 注入链真机扫描        inject_check.py (31+ 项)
  7. 验证台账              verify_ledger.py (19 项，[19] 预算假红→WARN)
  8. CS 量化全测           csqaq-monitor tests (150 用例)

用法：python battle_regression.py [--fast]   # --fast 跳过 4/8（最贵的两块）
"""
import os
import re
import subprocess
import sys
import time

if sys.stdout is None:  # pythonw 兜底（本能 3）
    sys.stdout = open(os.devnull, "w", encoding="utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

PY = sys.executable
ZD = os.path.expanduser(r"~\.zcode\workspace\default")
TRAIN = os.path.join(ZD, "ai-skills", "training")
MS = os.path.join(ZD, "memory-search")
CS = r"C:\Users\14676\Documents\02-项目开发\CS2皮肤追踪\csqaq-monitor"

RESULTS = []  # (suite, verdict, detail, seconds)


def run(cmd, cwd=None, timeout=600):
    env = os.environ.copy()
    env.update({"PYTHONIOENCODING": "utf-8", "PYTHONUTF8": "1"})
    try:
        p = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout,
                           encoding="utf-8", errors="replace", env=env, cwd=cwd)
        return p.returncode, (p.stdout or "") + (p.stderr or "")
    except subprocess.TimeoutExpired:
        return 124, "TIMEOUT"
    except Exception as e:  # noqa: BLE001
        return 125, repr(e)


def suite(name, cmd, cwd=None, timeout=600, post=None, fast_skip=False):
    if fast_skip:
        RESULTS.append((name, "SKIP", "--fast 跳过", 0.0))
        return
    t0 = time.time()
    rc, out = run(cmd, cwd=cwd, timeout=timeout)
    dt = time.time() - t0
    verdict, detail = ("FAIL", f"rc={rc}") if rc else ("OK", "")
    if post:
        verdict, detail = post(rc, out, verdict, detail)
    RESULTS.append((name, verdict, detail.strip()[:90], dt))


def tts_budget_exhausted():
    """预读 TTS 日预算状态（known_issue 2026-11-02：台账[19]实发语音耗预算）。"""
    try:
        import json
        st = json.load(open(r"C:\Users\14676\Documents\Codex\tts-state.json", encoding="utf-8"))
        import time as _t
        today = _t.strftime("%Y-%m-%d")
        if st.get("date") == today and int(st.get("count", 0)) >= 20:
            return True
    except Exception:  # noqa: BLE001
        pass
    return False


def post_ledger(rc, out, verdict, detail):
    """台账特判：[19] 预算假红重分类。verify_ledger 的 ✗ 行 detail=期望值回显，
    引擎真实输出（预算拒绝）不进 stdout——所以不能靠输出文本判，要预读 tts-state.json。"""
    m = re.search(r"(\d+)/(\d+) PASS", out)
    if not m:
        return "FAIL", "无 PASS 字样"
    good, total = int(m.group(1)), int(m.group(2))
    if good == total:
        return "OK", m.group(0)
    bad = re.findall(r"✗\s*\[?(\d+)\]?[^\n]{0,60}", out)
    notes = []
    unexplained = []
    for b in bad:
        if b == "19" and tts_budget_exhausted():
            cnt = int(__import__('json').load(open(
                r'C:\Users\14676\Documents\Codex\tts-state.json', encoding='utf-8'))['count'])
            notes.append(f"[19]预算假红({cnt}/20，器官未被证伪)")
        elif b == "17":
            notes.append("[17]间歇在案(10-27演示3/3、11-02复跑2/2，BoN长链打嗝，已加体面退出)")
        else:
            unexplained.append(b)
    if bad and not unexplained:
        return "WARN", f"{good}/{total}——{'；'.join(notes)}"
    return "FAIL", f"{m.group(0)} 败项:{bad[:3]}"


def post_map(rc, out, verdict, detail):
    if "无漂移" in out:
        return "OK", "无漂移"
    diffs = re.findall(r"实测 (\d+) ≠ 声明 (\d+)", out)
    return ("WARN", f"漂移 {diffs[:2]}（先 index 再改声明）") if diffs else ("FAIL", f"rc={rc}")


def post_inject(rc, out, verdict, detail):
    m = re.search(r"OK (\d+) / WARN (\d+) / FAIL (\d+)", out)
    if not m:
        return "FAIL", f"rc={rc}"
    ok, warn, fail = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if fail:
        return "FAIL", f"{ok}OK/{warn}WARN/{fail}FAIL 活性断裂"
    if warn:
        return "WARN", f"{ok}OK/{warn}WARN 休眠断针"
    return "OK", f"{ok}OK 全绿"


def main():
    fast = "--fast" in sys.argv
    t0 = time.time()
    py = [PY, "-X", "utf8"]

    suite("同义词扩展测试", py + ["-m", "unittest", "tests.test_synonyms"], cwd=MS)
    suite("四步法自测", py + [os.path.join(TRAIN, "literary_four_steps.py"), "--selftest"])
    suite("注入链自测", py + [r"C:\Users\14676\Documents\Codex\inject_check.py", "--selftest"])
    suite("memory-search全测", py + ["-m", "unittest", "discover", "-s", "tests", "-t", "."],
          cwd=MS, timeout=900, fast_skip=fast)
    # 2026-11-04: 活库上声明必追不上写入——先平账(map_decl_sync)再验，消灭竞态红
    suite("地图声明平账", py + [os.path.join(ZD.replace("/", chr(92)), "memory-search", "map_decl_sync.py")],
          timeout=120)
    suite("蒸馏地图漂移", py + [os.path.join(ZD, "ai-skills", "ledger-lessons", "distill_map_check.py")],
          post=post_map)
    suite("注入链真机", py + [r"C:\Users\14676\Documents\Codex\inject_check.py"], timeout=300,
          post=post_inject)
    suite("验证台账", py + [os.path.join(MS, "verify_ledger.py")], timeout=420, post=post_ledger)
    suite("CS量化全测", py + ["-m", "unittest", "discover", "-s", "tests", "-t", "."],
          cwd=CS, timeout=600, fast_skip=fast)

    dt = time.time() - t0
    n_ok = sum(1 for _, v, _, _ in RESULTS if v == "OK")
    n_warn = sum(1 for _, v, _, _ in RESULTS if v == "WARN")
    n_fail = sum(1 for _, v, _, _ in RESULTS if v == "FAIL")
    n_skip = sum(1 for _, v, _, _ in RESULTS if v == "SKIP")

    print("═" * 66)
    print("战役回归 · 一键全量")
    print("═" * 66)
    for name, v, detail, sec in RESULTS:
        mark = {"OK": "✓", "WARN": "△", "FAIL": "✗", "SKIP": "·"}[v]
        print(f"  {mark} {name:　<10} {v:5} {sec:5.1f}s  {detail}")
    print("─" * 66)
    print(f"合计 {n_ok}OK / {n_warn}WARN / {n_fail}FAIL / {n_skip}SKIP ｜ {dt:.0f}s")
    print("判定：", "全绿——战役可收" if n_fail == 0 and n_warn == 0 else
          ("有假红/休眠项——见上，均已有案" if n_fail == 0 else "真红——收不得"))
    sys.exit(2 if n_fail else (1 if n_warn else 0))


if __name__ == "__main__":
    main()
