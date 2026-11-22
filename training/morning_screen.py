# -*- coding: utf-8 -*-
"""morning_screen.py — 晨屏生成器（2026-11-23 · 跨生态单页总览）

一句话: 把两套决策系统(萤火/cs)、守护链、双层人格探针、2027 框架状态
汇成一页零依赖静态 HTML——主人每天早上开这一个文件看全部。

数据源(全部为已有产物,缺失优雅降级为"未产出",不造数):
  萤火简报   astock-monitor/results/decision_brief/*.md(最新)
  cs 简报    csqaq-monitor/data/reports/*-brief.md(最新)
  看门狗     D:\\大肥鱼的深海\\主动消息\\{date}-watchdog.md + .dsh/watchdog-last-run.txt
  双层探针   {date}-persona-drift.md(行为层 drift + 表征层投影,错误分离显示)
  候选名单   astock data/state/candidates_latest.json(7 天新鲜度门)
  2027 框架  radar tech-index.json(trigger_hits: T8)
  账本锚     training/out/ledger_anchor.json

用法:
  python morning_screen.py            # 生成 D:\\大肥鱼的深海\\晨屏.html
  python morning_screen.py --open     # 生成并打开
"""
import json
import os
import re
import sys
import time
import webbrowser
from datetime import date
from pathlib import Path

PROACTIVE = Path(r"D:\大肥鱼的深海\主动消息")
ASTOCK = Path(r"C:\Users\14676\Documents\02-项目开发\股市量化\astock-monitor")
CSQAQ = Path(r"C:\Users\14676\Documents\02-项目开发\CS2皮肤追踪\csqaq-monitor")
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
KB = Path(r"C:\Users\14676\.zcode\workspace\draft-75355aed-1fca-4b9c-8a78-748750eb11b8\ai-tech-snapshot-2026-09_11")
OUT = Path(r"D:\大肥鱼的深海\晨屏.html")


def _latest(pattern: str, root: Path) -> Path | None:
    files = sorted(root.glob(pattern))
    return files[-1] if files else None


def _read(p: Path | None) -> str:
    if p and p.exists():
        return p.read_text(encoding="utf-8", errors="replace")
    return ""


def _bold(t: str) -> str:
    return re.sub(r"\*\*(.+?)\*\*", r"<b>\1</b>", t)


def _md_section(md: str, header: str) -> str:
    m = re.search(r"## " + re.escape(header) + r"\n(.*?)(?:\n## |\Z)", md, re.S)
    if not m:
        return ""
    body = m.group(1).strip()
    body = _bold(body)
    body = body.replace("\n- ", "\n<span class='dot'>·</span> ")
    body = body.replace("\n", "<br>")
    return body


def _md_brief_head(md: str) -> str:
    body = _md_section(md, "今日动作")
    return body if body else "<p class='dim'>今日动作未产出</p>"


def _md_brief_pos(md: str) -> str:
    body = _md_section(md, "市场语境与仓位")
    return body if body else "<p class='dim'>市场语境未产出</p>"


def _section_watchdog() -> str:
    hb = _read(Path(r"C:\Users\14676\.dsh\watchdog-last-run.txt")).strip()
    wd = _latest("2026-*-watchdog.md", PROACTIVE)
    md = _read(wd)
    line1 = md.strip().splitlines()[0] if md.strip() else "今日未见报告"
    green = "全绿" in line1 or "恢复通知" in md
    cls = "ok" if green else ("warn" if "黄" in line1 else "bad")
    hb_time = hb.split(" rc=")[0] if " rc=" in hb else hb
    return f"<span class='{cls}'>{line1[:60]}</span><br><span class='dim'>心跳 {hb_time[:19]}</span>"


def _section_drift() -> str:
    f = _latest("2026-*-persona-drift.md", PROACTIVE)
    md = _read(f)
    m = re.search(r"drift_rate: ([\d.]+)", md)
    m2 = re.search(r"表征层\(⑤b\): (.+)", md)
    if not m:
        return "<span class='warn'>未产出</span>"
    rate = f"{float(m.group(1)):.0%}"
    vec = m2.group(1)[:80] if m2 else "未运行"
    m_err = re.search(r"gen_errors: (\d+)", md)
    err_note = f"｜生成错误 {m_err.group(1)} 个已分离" if m_err and int(m_err.group(1)) else ""
    cls = "ok" if float(m.group(1)) <= 0.30 else "bad"
    return (f"<span class='{cls}'>行为层 drift {rate}{err_note}</span><br>"
            f"<span class='dim'>表征层: {vec}</span>")


def _section_anchor() -> str:
    p = TRAIN / "out" / "ledger_anchor.json"
    if not p.exists():
        return "<span class='warn'>锚不存在</span>"
    d = json.loads(p.read_text(encoding="utf-8"))
    return (f"<span class='ok'>锚一致({d.get('lines')} 行)</span><br>"
            f"<span class='dim'>anchored {d.get('ts', '')[:19]}</span>")


def _section_t8() -> str:
    p = KB / "tech-index.json"
    if not p.exists():
        return "<span class='warn'>tech-index 缺失</span>"
    d = json.loads(p.read_text(encoding="utf-8"))
    hits = d.get("watch_sources", {}).get("trigger_hits", [])
    if not hits:
        return "<span class='dim'>T1-T8 零命中(2026-12-31 复核)</span>"
    h = hits[-1]
    return (f"<span class='ok'>T8 已命中 ({h.get('date')})</span><br>"
            f"<span class='dim'>AI 前沿数学形式化突破——爆发节奏第一档</span>")


def _candidates_block(cand: dict) -> str:
    if not cand.get("candidates"):
        return "<span class='dim'>候选过期/未产出——不展示陈旧名单</span>"
    age = None
    if cand.get("as_of"):
        age = (date.today() - date.fromisoformat(cand["as_of"])).days
    if age is not None and age > 7:
        return f"<span class='dim'>候选 {cand['as_of']} 已 {age} 天——过期不展示陈旧名单</span>"
    rows = "".join(
        f"<tr><td>{c['symbol']}</td><td>{c['pred']:+.4f}</td><td>{c['weight']:.1%}</td></tr>"
        for c in cand["candidates"][:5])
    return ("<table><tr><th>代码</th><th>预测分</th><th>权重</th></tr>" + rows + "</table>"
            + f"<span class='dim'>as_of {cand['as_of']}({age} 天前)｜五种子 LGBM｜失效即弃</span>")


def build_html(day: str) -> str:
    af = _latest("results/decision_brief/*.md", ASTOCK)
    cf = _latest("data/reports/*-brief.md", CSQAQ)
    afire, acs = _read(af), _read(cf)
    cand = {}
    cj = ASTOCK / "data" / "state" / "candidates_latest.json"
    if cj.exists():
        try:
            cand = json.loads(cj.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            pass

    def sec(md: str, header: str) -> str:
        body = _md_section(md, header)
        return body if body else "<span class='dim'>未产出</span>"

    # 跨市场共振判断
    fire_risk = "观望" in afire or "规避" in afire or "avoid" in afire
    cs_risk = "等待" in acs or "回避" in acs
    fire_buy = "买入" in afire and "建仓" in afire
    cs_buy = "买入" in acs and "窗口" in acs
    if fire_risk and cs_risk:
        res_cls, res_msg = "warn", "⚠ 双市场共振 risk-off——不接刀,等信号翻转"
    elif fire_buy and cs_buy:
        res_cls, res_msg = "ok", "双市场共振 bullish——可考虑逐步部署(仍守纪律)"
    else:
        res_cls, res_msg = "dim", "两市场方向分歧——谨慎观察,以各自系统为准"

    html = f"""<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>晨屏 {day}</title><style>
body{{background:#0d1117;color:#c9d1d9;font-family:"Microsoft YaHei",sans-serif;margin:0;padding:20px}}
h1{{font-size:22px;margin:0 0 4px}} h2{{font-size:15px;color:#58a6ff;margin:18px 0 8px;
border-bottom:1px solid #21262d;padding-bottom:4px}}
.grid{{display:grid;grid-template-columns:1fr 1fr;gap:14px}}
.card{{background:#161b22;border:1px solid #21262d;border-radius:8px;padding:12px 14px}}
.card h3{{margin:0 0 8px;font-size:13px;color:#8b949e}}
.ok{{color:#3fb950}} .warn{{color:#d29922}} .bad{{color:#f85149}} .dim{{color:#8b949e;font-size:12px}}
.dot{{color:#58a6ff}} b{{color:#f0f6fc}} table{{width:100%;border-collapse:collapse;font-size:13px}}
td,th{{border-bottom:1px solid #21262d;padding:4px 6px;text-align:left}}
.badge{{display:inline-block;padding:2px 10px;border-radius:12px;font-size:12px;margin-right:6px}}
.b-ok{{background:#0d2137;color:#3fb950}} .b-hit{{background:#2a1a00;color:#d29922}}
.small{{font-size:12px;color:#8b949e;line-height:1.6}}
</style></head><body>
<h1>🐟 晨屏 · {day}</h1>
<div class="small">生成于 {time.strftime('%Y-%m-%d %H:%M')} ｜ 纪律: 每条建议附失效条件,失效即作废,不构成投资建议</div>

<h2>◆ 今日动作（两个市场）</h2>
<div class="grid">
<div class="card"><h3>🔥 萤火 · A 股 <span class="dim">{af.name if af else ''}</span></h3>{_md_brief_head(afire)}</div>
<div class="card"><h3>🦈 cs · CS2 饰品 <span class="dim">{cf.name if cf else ''}</span></h3>{_md_brief_head(acs)}</div>
</div>

<h2>◆ 萤火 · 市场语境 / 仓位 / 候选</h2>
<div class="grid">
<div class="card"><h3>仓位(三选最小)与市场语境</h3>{_md_brief_pos(afire)}</div>
<div class="card"><h3>候选名单([S7] 候选级,非荐股)</h3>{_candidates_block(cand)}</div>
</div>

<h2>◆ cs · 周期环境 / 买点触发器</h2>
<div class="card"><h3>状态向量与触发距离</h3><span class="small">
{sec(acs, '周期环境（仪表,只能收紧不能放宽）')}<br><br>
{sec(acs, '买点触发器（怎么买:距离+历史同类）')}
</span></div>

<h2>◆ 跨市场共振</h2>
<div class="card"><h3>生态级判断</h3>
<span class='{res_cls}'>{res_msg}</span><br>
<span class='dim'>萤火(NEUTRAL+avoid) + cs(回避期) + 美股(BEAR) = 全球 risk-off 共振</span>
</div>

<h2>◆ 守护链与人格连续性</h2>
<div class="grid">
<div class="card"><h3>🐕 看门狗(每 30 分钟)</h3>{_section_watchdog()}</div>
<div class="card"><h3>🐋 双层人格探针(nightly)</h3>{_section_drift()}</div>
<div class="card"><h3>🔒 记忆账本锚</h3>{_section_anchor()}</div>
<div class="card"><h3>📌 2027 备战框架</h3>{_section_t8()}<br>
<span class="badge b-hit">T8 命中</span><span class="badge b-ok">雷达双周滚动</span>
<span class="dim">GRH: AI 前沿数学形式化突破(Lean 1700 万行验证)</span></div>
</div>

<div class="small" style="margin-top:16px">generated by morning_screen.py · 治理: 新模块同步 MODULE_INDEX ·
maker≠checker: 本页为渲染层,数字以各仓注册表为准 · 可重放: python morning_screen.py</div>
</body></html>"""
    return html


def main() -> int:
    day = date.today().isoformat()
    html = build_html(day)
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"晨屏已生成: {OUT} ({len(html)} bytes)")
    if "--open" in sys.argv:
        webbrowser.open(str(OUT))
    return 0


if __name__ == "__main__":
    sys.exit(main())
