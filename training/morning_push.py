# -*- coding: utf-8 -*-
"""morning_push.py — 每日晨屏自动推送（2026-11-23）

把决策简报摘要推到主动消息目录（dsh 同通道），主人打开深海就能看到。
不新增依赖，不新增常驻进程——每天 09:00 定时任务触发一次。

推送内容:
  1. 萤火今日动作(一句话)
  2. cs 今日动作(一句话)
  3. 跨市场共振判断
  4. 候选名单前 3(如有)
  5. 看门狗状态(一行)

用法:
  python morning_push.py               # 推送今日摘要
  schtasks 安装后每日 09:00 自动跑
"""
import json
import re
import sys
from datetime import date, timedelta
from pathlib import Path

PROACTIVE = Path(r"D:\大肥鱼的深海\主动消息")
ASTOCK = Path(r"C:\Users\14676\Documents\02-项目开发\股市量化\astock-monitor")
CSQAQ = Path(r"C:\Users\14676\Documents\02-项目开发\CS2皮肤追踪\csqaq-monitor")
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")


def _latest(pattern, root):
    fs = sorted(Path(root).glob(pattern))
    return fs[-1] if fs else None


def _read(p):
    if p and Path(p).exists():
        return Path(p).read_text(encoding="utf-8", errors="replace")
    return ""


def extract_action(md, label):
    """从简报 md 提取今日动作一句话。"""
    m = re.search(r"## 今日动作\n\*\*(.+?)\*\*", md)
    if m:
        return f"{label}: {m.group(1)}"
    return f"{label}: 未产出"


def extract_regime(md):
    m = re.search(r"regime 三票二: \*\*(\w+)\*\*", md)
    return m.group(1) if m else "?"


def build_push(day):
    lines = [f"🔥 萤火晨报 {day}", ""]

    # 萤火简报(取最新)
    af = _latest("results/decision_brief/*.md", ASTOCK)
    afire = _read(af)
    if afire:
        lines.append(extract_action(afire, "🔥 A股"))
        m = re.search(r"regime 三票二: \*\*(\w+)\*\*", afire)
        if m:
            lines.append(f"   regime: {m.group(1)}")
        m2 = re.search(r"建议仓位: (\d+%)", afire)
        if m2:
            lines.append(f"   仓位: {m2.group(1)}")
        # vol 警示
        if "⚠ 波动危险区" in afire:
            lines.append("   ⚠ 波动危险区(50日分位>90%)")
    else:
        lines.append("🔥 A股: 简报未产出")

    lines.append("")

    # cs 简报(取最新)
    cf = _latest("data/reports/*-brief.md", CSQAQ)
    acs = _read(cf)
    if acs:
        m = re.search(r"## 今日动作\n\*\*(.+?)\*\*", acs)
        if m:
            lines.append(f"🦈 CS2: {m.group(1)}")
        m2 = re.search(r"综合分 (\d+\.?\d*)", acs)
        if m2:
            lines.append(f"   综合分: {m2.group(1)}")
        m3 = re.search(r"热度分位: (\d+%)", acs)
        if m3:
            lines.append(f"   热度: {m3.group(1)}")
    else:
        lines.append("🦈 CS2: 简报未产出")

    lines.append("")

    # 跨市场共振
    fire_risk = "观望" in afire or "规避" in afire or "avoid" in afire
    cs_risk = "等待" in acs or "回避" in acs
    fire_buy = "买入" in afire and "建仓" in afire
    cs_buy = "买入" in acs and "窗口" in acs
    if fire_risk and cs_risk:
        lines.append("🌐 共振: ⚠ RISK-OFF——不接刀")
    elif fire_buy and cs_buy:
        lines.append("🌐 共振: ✅ BULLISH——可部署")
    else:
        lines.append("🌐 共振: 分歧——观察")

    lines.append("")

    # 候选名单(如有且新鲜)
    cj = ASTOCK / "data" / "state" / "candidates_latest.json"
    if cj.exists():
        try:
            cand = json.loads(cj.read_text(encoding="utf-8"))
            cands = cand.get("candidates", [])
            as_of = cand.get("as_of", "")
            age = (date.today() - date.fromisoformat(as_of)).days if as_of else 99
            if cands and age <= 7:
                lines.append(f"📋 候选前3({as_of}):")
                for c in cands[:3]:
                    lines.append(f"   {c['symbol']} 权重{c['weight']:.1%}")
        except (json.JSONDecodeError, KeyError):
            pass

    lines.append("")

    # 看门狗
    hb = _read(Path(r"C:\Users\14676\.dsh\watchdog-last-run.txt")).strip()
    wd = _latest("2026-*-watchdog.md", PROACTIVE)
    wd_text = _read(wd)
    wd_line = wd_text.strip().splitlines()[0][:60] if wd_text.strip() else "今日未见"
    lines.append(f"🐕 看门狗: {wd_line}")
    if hb:
        lines.append(f"   心跳: {hb[:19]}")

    lines.append("")
    lines.append("💡 详细: 晨屏.html | 注册表.html | 使用证明.html")
    lines.append("⏰ 下次更新: 15:40 (run_daily) 或 23:30 (夜间巩固)")

    return "\n".join(lines)


def main():
    day = date.today().isoformat()
    content = build_push(day)
    out = PROACTIVE / f"{day}-晨报.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(content + "\n", encoding="utf-8")
    print(f"晨报已推送: {out}")
    print(content)
    return 0


if __name__ == "__main__":
    sys.exit(main())
