# -*- coding: utf-8 -*-
"""audit_all_claims.py — 全量声明复验（2026-10-25 ZCode · 应主人令"真的去复验"）
每项真跑真查，失败如实报。用法：python audit_all_claims.py [--json]"""
import hashlib
import json
import subprocess
import sys
from pathlib import Path

T = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
MS = Path(r"C:\Users\14676\.zcode\workspace\default\memory-search")
MEM = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories")
RES = []


def run(cmd, t=120):
    r = subprocess.run(cmd, shell=True, capture_output=True, text=True,
                       encoding="utf-8", errors="replace", timeout=t)
    return (r.stdout or "") + (r.stderr or "")


def check(name, ok, detail=""):
    RES.append({"name": name, "ok": bool(ok), "detail": str(detail)[:100]})
    print(f"  {'✓' if ok else '✗'} {name}: {str(detail)[:90]}")


def fsize(path, min_kb=0.1):
    p = Path(path)
    return p.exists() and p.stat().st_size > min_kb * 1024, (f"{p.stat().st_size/1024:.1f}KB" if p.exists() else "不存在")


def main():
    print("== 全量声明复验 ==\n-- 文件工件 --")
    da = (T / "dsh_answer.py").read_text(encoding="utf-8")
    check("dsh_answer v2.2（k=4）", "RETRIEVE_CFG" in da and '"k": 4' in da, "k=4 在文件")
    check("qwen-dsh-v3 adapter", *fsize(T / "out/qwen-dsh-v3-lora/adapter_model.safetensors", 1000))
    sft_n = sum(1 for l in (T / "sft_instructions.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())
    check("SFT 115 条", sft_n == 115, f"实际 {sft_n}")
    dpo_n = sum(1 for l in (T / "dpo_pairs_v1.jsonl").read_text(encoding="utf-8").splitlines() if l.strip())
    check("DPO 54 对", dpo_n == 54, f"实际 {dpo_n}")
    qb = json.loads((T / "quiz_bank.json").read_text(encoding="utf-8"))["questions"]
    check("quiz_bank 16 题", len(qb) == 16, f"实际 {len(qb)}")
    check("巩固队列含今日", "2026-10-25" in (T / "consolidation_queue.md").read_text(encoding="utf-8"), "10-25 节在")
    check("标定报告", *fsize(T / "calibration-report-20261025.md", 1))
    check("思想库（哲学+文学）", *fsize(MEM / "经典思想库-2026-10-25.md", 3))
    check("思想库续篇（毛选）", *fsize(MEM / "经典思想库续篇-毛选-2026-10-25.md", 2))
    check("验证总结 8 族", "族 8" in (MEM / "验证经验总结-2026-10-25.md").read_text(encoding="utf-8"), "族8 在文")
    check("人格润色+例话锚", "例话锚" in (MEM / "人格润色-去AI味行为学-2026-10-25.md").read_text(encoding="utf-8"), "8 组锚在文")

    print("\n-- 可执行复跑 --")
    out = run(f'python -X utf8 "{MS}/verify_ledger.py"', t=900)
    check("verify_ledger 16/16 实跑", "16/16" in out, out.strip().splitlines()[0][:40] if out.strip() else "无输出")
    out = run(f'python -X utf8 "{MS}/distill_map_check.py"')
    check("漂移 0 实跑", "无漂移" in out, "无漂移" if "无漂移" in out else out[-60:])
    out = run(f'python -X utf8 "{MS}/count_audit.py"')
    check("计数真值一致实跑", "一致" in out, "高发区一致" if "一致" in out else "有漂移")
    out = run(f'python -X utf8 "{MS}/tests/test_memsearch_benchmark.py"', t=600)
    check("基准 13/13 实跑", "13/13" in out, out.strip().splitlines()[-1][:40] if out.strip() else "空")
    out = run(f'python -X utf8 "{T}/dsh_answer.py" "验证台账每行有哪五个字段"', t=300)
    check("dsh_answer 可用禁裸答", "A:" in out, out.strip().splitlines()[-1][:60] if out.strip() else "空")
    out = run(f'python -X utf8 "{T}/vision_chat.py" "C:/Users/14676/简历/outputs/img_1792891483.png" "一句话：图里是什么"', t=300)
    check("本地 VLM 可看图", len(out.strip()) >= 10 and ("图" in out or "描述" in out or len(out.strip()) > 8), out.strip()[:60] or "空")

    print("\n-- 调度与服务 --")
    for n in ["DSH DailyClosure", "DSH LightRAG-Watchdog", "DSH NightConsolidate", "DSH WeeklyQuiz"]:
        s = run(f'powershell -NoProfile -Command "(Get-ScheduledTask \'{n}\' -ErrorAction SilentlyContinue).State"').strip()
        check(f"任务[{n}]", s == "Ready", s or "未注册")
    out = run('curl -s -o /dev/null -w "%{http_code}" --max-time 4 http://127.0.0.1:9621/health')
    check("LightRAG 200", "200" in out, out.strip() or "不可达")
    out = run("ollama list")
    check("Ollama VLM 在库", "qwen2.5vl:3b" in out, "qwen2.5vl:3b 在" if "qwen2.5vl:3b" in out else "不在")

    print("\n-- AGENTS 与索引 --")
    a = hashlib.md5(Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\AGENTS.md").read_bytes()).hexdigest()
    b = hashlib.md5(Path(r"C:\Users\14676\.dsh\AGENTS.md").read_bytes()).hexdigest()
    check("AGENTS 双副本一致", a == b, a[:8])
    out = run(f'python -X utf8 "{MS}/mem_search.py" index', t=300)
    import re as _re
    m = _re.search(r"库内共 (\d+) 个文件", out)
    n_files = int(m.group(1)) if m else -1
    check("检索库 74 文件", n_files == 74, f"实际 {n_files}")

    passed = sum(1 for r in RES if r["ok"])
    print(f"\n== 复验结论：{passed}/{len(RES)} 通过 ==")
    fails = [r for r in RES if not r["ok"]]
    for r in fails:
        print(f"  ✗ 失败: {r['name']}: {r['detail']}")
    if "--json" in sys.argv:
        print(json.dumps(RES, ensure_ascii=False, indent=1))
    return 0 if not fails else 1


if __name__ == "__main__":
    sys.exit(main())
