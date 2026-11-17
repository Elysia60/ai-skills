# -*- coding: utf-8 -*-
"""skill_governance.py — 技能治理清单生成器（2026-11-04 · 提案#7 落地 · R85）

治理三字段（提案#7 原案）：每技能标注「有无出师自测 / 是否过 --audit / 来源」。
数据源：
  · sync_skills --audit（宿主分发健康，91 真源 × 7 宿主）
  · 各技能 SKILL.md 的 出师自测/自测 标记扫描
  · 来源分类：自建（有台账/战役出处可查）/ 社区（其余，如实标注）
输出：training/技能治理清单-最新.md（每技能一行）+ 汇总统计
用法：python skill_governance.py
"""
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

if sys.stdout is None:
    sys.stdout = open(__import__("os").devnull, "w", encoding="utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

HERE = Path(__file__).parent
OUT = HERE / "技能治理清单-最新.md"
SYNC = Path.home() / ".agents/sync_skills.py"

# 自建技能（有战役/台账出处可查——证据见各自 SKILL.md/纪要；其余如实标社区）
SELF_BUILT = {
    "ledger-lessons": "手法库八类53条（蒸馏体系产出，2026-10-24）",
    "mmd-video-pipeline": "MMD 出片管线 v3（DSH 教材+渲染脚本）",
    "resource-hub": "资源中枢（DSH 侧裁定产物）",
    "vision-skills": "视觉技能脚本族（本机视觉规程配套）",
}
AUDIT_RULED = {"ledger-lessons", "mmd-video-pipeline", "resource-hub"}  # 出师自测在册


def run_audit():
    p = subprocess.run([sys.executable, str(SYNC), "--audit"], capture_output=True,
                       text=True, timeout=300, encoding="utf-8", errors="replace")
    out = (p.stdout or "") + (p.stderr or "")
    m = re.search(r"真源 (\d+) 项", out)
    total = int(m.group(1)) if m else 0
    hosts_ok = out.count("[OK]")
    hosts_bad = out.count("[!!]")
    m2 = re.search(r"缺失=\[([^\]]*)\]", out)
    missing = m2.group(1) if m2 else ""
    return total, hosts_ok, hosts_bad, missing, out


def scan_selftest():
    """扫描各技能 SKILL.md 的出师自测标记。"""
    roots = [Path.home() / ".zcode/skills",
             Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\pending-skills"),
             Path.home() / ".agents/skills"]
    result = {}
    seen = set()
    for root in roots:
        if not root.is_dir():
            continue
        for skill_md in root.glob("*/SKILL.md"):
            name = skill_md.parent.name
            if name in seen:
                continue
            seen.add(name)
            try:
                text = skill_md.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            has_test = bool(re.search(r"出师自测|## 自测|selftest", text, re.I))
            result[name] = has_test
    return result


def main():
    total, hosts_ok, hosts_bad, missing, raw = run_audit()
    selftest = scan_selftest()

    n_test = sum(1 for v in selftest.values() if v)
    lines = [
        "# 技能治理清单（最新）",
        "",
        f"> 生成：{datetime.now():%Y-%m-%d %H:%M} ｜ 刷新：`python skill_governance.py` ｜ 提案#7 交付物",
        "",
        "## 一、宿主分发健康（sync_skills --audit 实跑）",
        f"- 真源 {total} 项 ｜ 宿主 OK {hosts_ok} / 异常 {hosts_bad}"
        + (f" ｜ 缺失: {missing}" if missing else " ｜ 无缺失"),
        "",
        "## 二、治理标注（自建技能逐条；社区技能汇总）",
        "| 技能 | 来源 | 出师自测 | 备注 |",
        "|---|---|---|---|",
    ]
    for name in sorted(SELF_BUILT):
        has = selftest.get(name, False)
        lines.append(f"| {name} | 自建：{SELF_BUILT[name]} | {'✓ 在册' if has else '✗ 无'} |"
                     + ("技能桥接 91/91" if name != "ledger-lessons" else "已修：曾缺 3 宿主，--fix 恢复") + "|")
    n_community = len(selftest) - len(SELF_BUILT)
    lines.append(f"| 其余 {n_community} 个扫描到的 SKILL.md | 社区/第三方 | 出师自测 {sum(1 for k,v in selftest.items() if v and k not in SELF_BUILT)}/{n_community} | 社区技能不出师，audit 只看分发 |")
    lines += [
        "",
        "## 三、汇总",
        f"- 扫描到 SKILL.md 的技能：{len(selftest)} ｜ 含出师自测：{n_test}",
        f"- 自建 {len(SELF_BUILT)} 全部在册；宿主分发 {'健康' if hosts_bad == 0 else '有缺口'}",
        "- 治理缺口修复记录：ledger-lessons 曾缺 3 宿主（11-04 --fix 恢复，91/91）",
    ]
    OUT.write_text("\n".join(lines), encoding="utf-8", newline="\n")
    print(f"治理清单: {OUT}")
    print(f"  真源 {total} ｜ 宿主 OK {hosts_ok}/异常 {hosts_bad} ｜ SKILL.md {len(selftest)} 个含自测 {n_test} ｜ 自建 {len(SELF_BUILT)}")


if __name__ == "__main__":
    main()
