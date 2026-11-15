# -*- coding: utf-8 -*-
"""m5_dual_source_stats.py — M5 人类互动腿·统计逻辑（2026-11-15 ZCode · 分工件：ZCode 逻辑/dsh 数据）

裁决依据：M5 升一票否决——连续两月真人互动较基线降 >30% → 项目停（DSH 裁决 2026-11-15）。
双源（dsh 供数据，路径实测确认）：
  主源 ~/.dsh/memories/daily/*.md（42 个按日文件，新增持续）
  辅源 D:\\大肥鱼的深海\\每日.txt（日期行）
统计口径（v1，诚实声明）：
  - "真人互动"=关键词命中计数（出门/见/朋友/家人/电话/通话/见面/聚会/约了/回来/聊了）
  - 已知弱点：关键词法对口语变体漏检（V0 实测 2026-10 仅 2 例）——**月度基线在关键词校准完成前
    只有参考价值，无否决效力**；校准方式=人工标注 dsh daily 中"真互动日"样本 ≥30 天后重定词表
  - 稀疏护栏：当月有日期标记的天数 <10 → 数据不足 flag，不出判定（防假结论——V0 的教训）
用法：
  python m5_dual_source_stats.py            # 输出月度剖面 + 否决检查
  python m5_dual_source_stats.py --baseline 2026-11   # 指定基线月
"""
import re
import sys
from collections import defaultdict
from pathlib import Path

DAILY_DIR = Path.home() / ".dsh" / "memories" / "daily"
AUX_FILE = Path(r"D:\大肥鱼的深海\每日.txt")
KEYWORDS = ["出门", "见面", "见了", "朋友", "家人", "电话", "通话", "聚会", "约了",
            "回来", "下班", "同学", "同事", "聊了", "吃饭", "散步"]
VETO_RULE = {"window": 2, "threshold": 0.30}  # 连续两月较基线降>30%


def _dated_entries() -> dict:
    """双源解析 → {date: 合并文本}。主源优先，辅源按日期行合并。"""
    out = {}
    if DAILY_DIR.exists():
        for p in sorted(DAILY_DIR.glob("*")):
            try:
                text = p.read_text(encoding="utf-8", errors="replace")
            except OSError:
                continue
            m = re.search(r"(\d{4}-\d{2}-\d{2})", p.name + text[:200])
            if m:
                out[m.group(1)] = out.get(m.group(1), "") + "\n" + text
    if AUX_FILE.exists():
        try:
            aux = AUX_FILE.read_text(encoding="utf-8", errors="replace")
            for line in aux.splitlines():
                m = re.match(r"\s*(\d{4}-\d{2}-\d{2})", line)
                if m and m.group(1) not in out:
                    out[m.group(1)] = line
        except OSError:
            pass
    return out


def monthly_counts(entries: dict) -> dict:
    """{YYYY-MM: {dated_days, keyword_hits}}——仅统计有日期标记的天。"""
    by_month = defaultdict(lambda: {"days": 0, "hits": 0})
    for date, text in entries.items():
        month = date[:7]
        hits = sum(text.count(k) for k in KEYWORDS)
        by_month[month]["days"] += 1
        by_month[month]["hits"] += hits
    return dict(by_month)


def check_veto(by_month: dict, baseline_month: str | None) -> dict:
    months = sorted(by_month)
    if baseline_month is None:
        baseline_month = months[0] if months else None
    base = by_month.get(baseline_month)
    if not base or base["days"] < 10:
        return {"veto": None, "reason": f"基线月 {baseline_month} 数据不足(有日期天数<10)——先校准关键词,不出判定"}
    tail = months[-2:] if len(months) >= 2 else months
    sparse = [m for m in tail if by_month[m]["days"] < 10]
    if sparse:
        return {"veto": None, "reason": f"近两月数据稀疏({sparse})——不出判定"}
    base_rate = base["hits"] / max(base["days"], 1)
    cur_rate = sum(by_month[m]["hits"] for m in tail) / max(sum(by_month[m]["days"] for m in tail), 1)
    drop = (base_rate - cur_rate) / max(base_rate, 1e-9)
    veto = drop > VETO_RULE["threshold"]
    return {"veto": veto, "baseline": baseline_month, "baseline_rate": round(base_rate, 2),
            "current_months": tail, "current_rate": round(cur_rate, 2),
            "drop": round(drop, 3), "threshold": VETO_RULE["threshold"]}


def main() -> int:
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    baseline = None
    if "--baseline" in sys.argv:
        baseline = sys.argv[sys.argv.index("--baseline") + 1]
    entries = _dated_entries()
    if not entries:
        print("双源均不可读或为空——检查路径与权限")
        return 1
    print(f"有日期条目: {len(entries)} 天（主源 daily + 辅源每日 合并去重）")
    by_month = monthly_counts(entries)
    for m in sorted(by_month)[-6:]:
        d = by_month[m]
        sparse_flag = " ⚠稀疏" if d["days"] < 10 else ""
        print(f"  {m}: 有日期 {d['days']} 天, 互动关键词命中 {d['hits']}{sparse_flag}")
    verdict = check_veto(by_month, baseline)
    print(f"\nM5 否决检查: veto={verdict['veto']} | {verdict['reason'] if 'reason' in verdict else ''}")
    if verdict.get("veto") is not None:
        print(f"  基线 {verdict['baseline']} 日均率 {verdict['baseline_rate']} → 近期日均率 {verdict['current_rate']}"
              f" | 降幅 {verdict['drop']:.0%} vs 阈值 {verdict['threshold']:.0%}")
    print("\n诚实声明: 关键词计数对口语变体漏检——校准(人工标注≥30天真互动日)完成前, 本脚本输出仅供观察, 不触发否决。")
    return 0


if __name__ == "__main__":
    sys.exit(main())
