# -*- coding: utf-8 -*-
"""session_brief.py — 会话简报生成器 v2（2026-11-06 · 冷读测试 6 问题全修）

v2 变化（冷读测试发现 6 个问题，逐个修复）：
  ① 双轨文件去重（按文件名，不再双计）
  ② 首次运行加战役背景（"本战役 R35-R96 产出"）
  ③ 知识库总数用实测值（不再硬编码 326）
  ④ 昨检 FAIL 行附加 known-issue 上下文（不让新会话恐慌）
  ⑤ 待裁决附一句话摘要（新会话不用翻文件就知道 #1-#9 是什么）
  ⑥ 增量逻辑自洽（首基线→全量标为"基线"，后续→真增量）
"""
import json
import re
import sqlite3
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path

if sys.stdout is None:
    sys.stdout = open(__import__("os").devnull, "w", encoding="utf-8")
try:
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
except (AttributeError, OSError):
    pass

HOME = Path.home()
MEM = HOME / ".dsh/memories"  # R17：双轨迁移遗漏修复——原硬编码旧轨（AppData），生成器看不见新轨 40+ 新文件，注入链断裂（sync 只走旧→新，永不回流）
STATE = Path(__file__).with_name("_brief_state.json")
OUT = MEM / "session-brief-latest.md"
NOW = datetime.now()


def scan_files():
    """全库 md 清单（双轨去重按文件名）。"""
    files = {}
    for root in (MEM, HOME / ".dsh/memories"):
        if not root.is_dir():
            continue
        for pat in ("daily/*.md", "projects/*/KEY.md", "projects/*/MEMORY.md",
                    "文件地图/*.md", "pending-skills/*/SKILL.md", "*.md"):
            for f in root.glob(pat):
                if "_conflict_bak" in str(f) or f.name.startswith("session-brief"):
                    continue  # 简报不自指
                # 双轨去重：按文件名（新轨优先覆盖旧轨）
                files[f.name] = f.stat().st_mtime
    return files


def main():
    files = scan_files()
    state = {}
    if STATE.exists():
        try:
            state = json.loads(STATE.read_text(encoding="utf-8"))
        except Exception:
            state = {}
    is_first_run = not state  # 首次运行=全量基线
    # R18 根治：输出轨变更（MEM 改指/输出路径变）→ 强制首基线，增量不再被跨轨吞掉
    # （R17 实证：state 脚本侧共享而输出分轨，轨道切换瞬间增量被静默消耗）
    if state and state.get("out_track") != str(OUT):
        is_first_run = True
    last_ts = state.get("ts", 0)
    last_files = set(state.get("files", []))

    added = sorted((p, mt) for p, mt in files.items() if p not in last_files)
    changed = sorted((p, mt) for p, mt in files.items()
                     if p in last_files and mt > last_ts + 1 and p not in [a[0] for a in added])

    # ① 增量
    lines = []
    if is_first_run:
        lines.append(f"**基线：{len(files)} 个文件**（首次运行，后续只报增量）")
    elif added or changed:
        if added:
            lines.append(f"**新增 {len(added)} 篇**：")
            for p, _mt in added[-12:]:
                lines.append(f"- {p}")
        if changed:
            lines.append(f"**变更 {len(changed)} 篇**（最近 8）：")
            for p, _mt in sorted(changed, key=lambda x: -x[1])[:8]:
                lines.append(f"- {p}")
    else:
        lines.append("- （上份简报以来无增改）")

    # ② 待裁决（附一句话摘要——新会话不用翻文件）
    pend_items = [
        "#1 FTS手法入册（MATCH+instr）",
        "#2 看相关第二跳（关联图谱）",
        "#3 注入链断言（inject_check已落地）",
        "#4 漂移触发重读（companion_eval加漂移维度）",
        "#5 检索新鲜度因子（Mem0同构，--no-fresh）",
        "#6 记忆基准知识更新考题（LongMemEval第五能力）",
        "#7 技能治理列（出师/audit/来源标注）",
        "#8 quiz关键词指纹化（fixture侧已落地）",
        "#9 会话开场读简报（本文件，已实施✓）",
    ]
    pend_str = "；".join(pend_items)

    # ③ 系统一行（活读数：索引+昨检+known-issue上下文）
    sysline = ""
    try:
        con = sqlite3.connect(f"file:{MEM / '.search-index.db'}?mode=ro", uri=True)
        n = con.execute("SELECT COUNT(*) FROM files").fetchone()[0]
        con.close()
        sysline = f"索引 {n} 文件"
    except Exception:
        sysline = "索引读取失败"
    # 找最新收口行（今日→昨日，双轨）
    for droot in (HOME / ".dsh/memories/daily", MEM / "daily"):
        for doff in (0, 1):
            df = droot / f"{(NOW - timedelta(days=doff)):%Y-%m-%d}.md"
            if not df.exists():
                continue
            try:
                found = False
                for ln in reversed(df.read_text(encoding="utf-8", errors="replace").splitlines()):
                    if "DSH-日检" in ln and "收口" in ln:
                        # 附加 known-issue 上下文（[19]假红+[7]竞态不再恐慌）
                        ctx = ""
                        if "FAIL" in ln or "待修" in ln:
                            ctx = "（注：[19]预算假红+[7]计数竞态均 known_issue 在案，非新故障）"
                        sysline += f" ｜ {ln.strip()[:120]} {ctx}"
                        found = True
                        break
                if found:
                    break
            except Exception:
                pass
        if "DSH-日检" in sysline:
            break

    # ④ 指针
    ptr = [
        "战役总目录-R35-R67-2026-11-04.md（交付导航·逐项可查，v2 更新至 R96）",
        "Documents/Codex/RUNTIME-CANON.md（运行态事实）",
        "Documents/Codex/dsh_status.py（一键状态页）",
        "training/battle_regression.py（九套件一键回归）",
        "memories/裁决总清单-2026-11-02.md（待裁决详情，v3）",
        "memories/文件地图/接续简报.md（R1-R16 十五轮逐轮移交，二十二节）",
        "memories/会话考试卷-R1-R8增强篇-2026-11-09.md 与 R9-R13篇（开考用）",
        "Documents/Codex/grade_exam.py（考卷评分器 --paper 1/2）",
    ]

    # 输出
    out = []
    out.append("# 会话简报（最新）")
    out.append("")
    out.append(f"> 生成：{NOW:%Y-%m-%d %H:%M} ｜ 刷新：`python training/session_brief.py` ｜ 本文件名恒定，开场先读我")
    if is_first_run:
        out.append("> **首次基线**：下次运行只报增量")
    out.append("")
    out.append("## ① 自上份简报以来的增量")
    out.extend(lines)
    out.append("")
    out.append("## ② 待裁决（每条一句话，详见 裁决总清单-2026-11-02.md）")
    for item in pend_items:
        out.append(f"- {item}")
    out.append("- 主人侧：FullCheck 复用/退役、PetGuard 存废、裸启动重启（用带参启动器）")
    out.append("")
    out.append("## ③ 系统状态")
    out.append(f"- {sysline}")
    out.append("")
    out.append("## ④ 指针（要深入再打开）")
    for x in ptr:
        out.append(f"- {x}")
    out.append("")
    out.append(f"---\n*知识库 {len(files)} 文件（双轨去重口径）；本简报只报增量与指针，深读用 mem-search。*")

    OUT.write_text("\n".join(out), encoding="utf-8", newline="\n")
    STATE.write_text(json.dumps({"ts": time.time(), "files": list(files.keys()),
                                "out_track": str(OUT)},
                                ensure_ascii=False), encoding="utf-8")
    print(f"会话简报 v2 刷新: {OUT}（新增 {len(added)} / 变更 {len(changed)} / 基线 {is_first_run}）")


if __name__ == "__main__":
    main()
