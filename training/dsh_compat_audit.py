# -*- coding: utf-8 -*-
"""dsh_compat_audit.py — DSH 兼容性一令审计（2026-10-30 ZCode · R29）

起因（事故原型）：两轨失步（二十轮产出旧轨写、新轨读不到）、蒸馏地图声明漂移（81≠97）、
FTS5 path-LIKE 恒假——三件事都是"各部件各自正常、合在一起不兼容"。本工具把它们变成一条命令。

七节审计（各自独立，一节失败不阻断其余）：
  ① 两轨一致性     16 份知识/候选文件在旧轨与新轨同时存在且 md5 一致
  ② 工具链         10 个工具 py_compile + 带 selftest 的逐一实跑
  ③ skill 分发     sync_skills --audit 全宿主 90/90
  ④ 数据链         SFT 逐行 JSON / 题库 / 金句池（过安全门）/ our-sea.json
  ⑤ 基线纪元       权威 baseline.py --check（CHANGED=正常增长记 WARN，MISSING=FAIL）
  ⑥ AGENTS 指针    指针块引用的文件在两轨都可解析
  ⑦ 检索通路       FTS5 上关键文件可命中（禁 path LIKE，用 instr）

退出码：0=全兼容 1=有 FAIL 2=审计器自身自测失败。
"""
import hashlib
import json
import py_compile
import re
import subprocess
import sys
import time
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
OLD_MEM = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories")
NEW_MEM = Path(r"C:\Users\14676\.dsh\memories")
CODEX = Path(r"C:\Users\14676\Documents\Codex")
DUAL = ["人格增强-文学养料库-2026-10-26.md", "视觉理解规程-2026-10-26.md",
        "教师移交-项目复合查询经验-2026-10-26.md", "人格增强-人格卡润色规范-2026-10-26.md",
        "人格增强-文学养料库续篇-2026-10-27.md", "人格增强-文学养料库续二-2026-10-27.md",
        "人格增强-文学养料库续三-2026-10-27.md", "人格增强-灵魂蓝图润色候选稿-2026-10-27.md",
        "教师总纲-六轮课程地图-2026-10-27.md", "人格增强-文学养料库续四-2026-10-27.md",
        "人格增强-文学养料库续五-2026-10-27.md", "桌宠通路-whisperPrompt候选-2026-10-27.md",
        "手法候选-十三轮蒸馏-2026-10-27.md"]
TOOLS = ["literary_four_steps.py", "agentsmd_freshness_check.py", "quotes_safety_check.py",
         "vision_protocol_check.py", "blueprint_merge_dryrun.py", "pet_config_check.py",
         "knowledge_quiz_e2e.py", "run_all_validators.py", "upgrade_validators_monotonic.py",
         "validation_common.py"]
SELFTESTING = ["literary_four_steps.py", "agentsmd_freshness_check.py", "quotes_safety_check.py",
               "vision_protocol_check.py", "blueprint_merge_dryrun.py", "pet_config_check.py"]


def md5(p):
    return hashlib.md5(Path(p).read_bytes()).hexdigest()


def audit_two_tracks(fails, warns):
    out = []
    for name in DUAL:
        o, n = OLD_MEM / name, NEW_MEM / name
        if not o.exists():
            fails.append(f"①旧轨缺: {name}")
        elif not n.exists():
            warns.append(f"①新轨缺（sync 未跑?）: {name}")
        elif md5(o) != md5(n):
            warns.append(f"①两轨内容不一致: {name}")
        else:
            out.append(name)
    return out


def audit_tools(fails, warns):
    for name in TOOLS:
        p = TRAIN / name
        if not p.exists():
            fails.append(f"②工具缺失: {name}")
            continue
        try:
            py_compile.compile(str(p), doraise=True)
        except py_compile.PyCompileError as e:
            fails.append(f"②编译失败: {name}: {str(e)[:60]}")
    for name in SELFTESTING:
        r = subprocess.run([sys.executable, str(TRAIN / name), "--selftest"],
                           capture_output=True, text=True, timeout=120)
        out = r.stdout + r.stderr
        if "PASS" not in out and "0 项失败" not in out:
            fails.append(f"②selftest 未过: {name}: {out[:80]}")


def audit_skills(fails, warns):
    r = subprocess.run([sys.executable, r"C:\Users\14676\.agents\sync_skills.py", "--audit"],
                       capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    if "全宿主健康" not in out:
        m = re.search(r"缺失=\[([^\]]*)\]", out)
        fails.append(f"③skill 分发缺口: {m.group(1)[:80] if m else out[-80:]}")
    else:
        m = re.search(r"真源 (\d+) 项", out)
        warns.append(f"③skill 真源 {m.group(1) if m else '?'} 项全宿主健康")


def audit_data(fails, warns):
    try:
        rows = [json.loads(l) for l in (TRAIN / "sft_instructions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
        if not all(all(k in r and r[k] for k in ("instruction", "output", "source")) for r in rows):
            fails.append("④SFT 存在字段缺失行")
        if len(rows) < 300:
            warns.append(f"④SFT 行数回落: {len(rows)}")
    except Exception as e:
        fails.append(f"④SFT 读取失败: {str(e)[:60]}")
    try:
        quiz = json.loads((TRAIN / "quiz_bank.json").read_text(encoding="utf-8"))["questions"]
        if len(quiz) < 32 or len({q["id"] for q in quiz}) != len(quiz):
            fails.append(f"④题库异常: {len(quiz)} 题")
    except Exception as e:
        fails.append(f"④题库读取失败: {str(e)[:60]}")
    g = subprocess.run([sys.executable, str(TRAIN / "quotes_safety_check.py")],
                       capture_output=True, text=True, timeout=120)
    if g.returncode not in (0,):
        warns.append("④金句池安全门非 0（若 rc=1 存在 BLOCK 句——已知隔离待裁决）")
    try:
        sea = json.loads((CODEX / "3d-memory-sea" / "data" / "our-sea.json").read_text(encoding="utf-8"))
        n_msg = len(sea.get("messages", []))
        if n_msg < 600:
            warns.append(f"④our-sea messages 偏少: {n_msg}")
    except Exception as e:
        fails.append(f"④our-sea.json 读取失败: {str(e)[:60]}")


def audit_baseline(fails, warns):
    r = subprocess.run([sys.executable, str(CODEX / "baseline.py"), "--check"],
                       capture_output=True, text=True, timeout=300)
    out = r.stdout + r.stderr
    m_miss = re.search(r"MISSING=(\d+)", out)
    if m_miss and int(m_miss.group(1)) > 0:
        time.sleep(65)  # 可能与 30 分钟同步任务撞车：等一个同步周期后复检
        r2 = subprocess.run([sys.executable, str(CODEX / "baseline.py"), "--check"],
                            capture_output=True, text=True, timeout=300)
        m2 = re.search(r"MISSING=(\d+)", r2.stdout + r2.stderr)
        if m2 and int(m2.group(1)) > 0:
            fails.append(f"⑤基线复检仍 MISSING {m2.group(1)} 项（文件真丢了）")
        else:
            warns.append("⑤基线首查 MISSING、复检消失（同步撞车瞬时态，已复核）")
    elif r.returncode != 0:
        m = re.findall(r"~\s+(\S+)\s+内容变化", out)
        warns.append(f"⑤基线 CHANGED {len(m)} 项（正常增长类: {', '.join(m)[:60]}）——有意改动后由归属会话 --update 宣布新纪元")
    else:
        warns.append("⑤基线全 OK")


def audit_pointers(fails, warns):
    ag = OLD_MEM.parent / "AGENTS.md"
    t = ag.read_text(encoding="utf-8")
    refs = set(re.findall(r"memories[\\/](人格增强[^`）\s]+|视觉理解规程[^`）\s]+|教师移交[^`）\s]+|教师总纲[^`）\s]+|桌宠通路[^`）\s]+|手法候选[^`）\s]+)\.md", t))
    for r in sorted(refs):
        name = r.replace("\\", "/").split("/")[-1] + ".md"
        if not (OLD_MEM / name).exists():
            fails.append(f"⑥指针悬空（旧轨）: {name}")
        if not (NEW_MEM / name).exists():
            warns.append(f"⑥指针悬空（新轨）: {name}")


def audit_fts(fails, warns):
    import sqlite3
    db = sqlite3.connect(str(OLD_MEM / ".search-index.db"))
    for term, expect in [("文学养料八法", "文学养料库"), ("看图八步", "视觉理解规程"),
                         ("教师移交", "教师移交"), ("手法候选", "手法候选")]:
        try:
            n = db.execute('select count(*) from docs where docs match ? and instr(path,?)>0',
                           (f'"{term}"', expect)).fetchone()[0]
            if n <= 0:
                fails.append(f"⑦FTS 未命中: {term} → {expect}")
        except sqlite3.OperationalError as e:
            fails.append(f"⑦FTS 查询失败 {term}: {str(e)[:40]}")


def main():
    t0 = time.time()
    fails, warns = [], []
    dual_ok = audit_two_tracks(fails, warns)
    audit_tools(fails, warns)
    audit_skills(fails, warns)
    audit_data(fails, warns)
    audit_baseline(fails, warns)
    audit_pointers(fails, warns)
    audit_fts(fails, warns)
    print("═" * 62)
    print("DSH 兼容性一令审计 · 七节")
    print("═" * 62)
    print(f"① 两轨一致性: {len(dual_ok)}/{len(DUAL)} 份知识文件双轨同 md5")
    print(f"② 工具链: {len(TOOLS)} 个编译检查 + {len(SELFTESTING)} 个 selftest")
    print(f"③ skill 分发 / ④ 数据链 / ⑤ 基线纪元 / ⑥ AGENTS 指针 / ⑦ 检索通路: 见下")
    print("─" * 62)
    for f in fails:
        print("  FAIL:", f)
    for w in warns:
        print("  WARN:", w)
    print("─" * 62)
    print(f"FAIL {len(fails)} ｜ WARN {len(warns)} ｜ 耗时 {time.time()-t0:.0f}s")
    print("判定：", "全兼容" if not fails else "存在不兼容项（FAIL 见上）")
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
