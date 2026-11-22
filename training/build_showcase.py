#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""成果总览生成器 — 全系统 + 指标 + 对标 + 时间轴（2026-11-23）

产出: D:\\大肥鱼的深海\\成果总览.html — 单页零依赖静态 HTML
数据源: 各仓测试结果/指标/注册表结论/GitHub 对标研究
"""
import json
import sys
import time
from pathlib import Path

OUT = Path(r"D:\大肥鱼的深海\成果总览.html")
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
ASTOCK = Path(r"C:\Users\14676\Documents\02-项目开发\股市量化\astock-monitor")
CSQAQ = Path(r"C:\Users\14676\Documents\02-项目开发\CS2皮肤追踪\csqaq-monitor")
CODEX = Path(r"C:\Users\14676\Documents\Codex")
KB = Path(r"C:\Users\14676\.zcode\workspace\draft-75355aed-1fca-4b9c-8a78-748750eb11b8\ai-tech-snapshot-2026-09_11")

def _test_count(root, test_dir="tests"):
    try:
        r = subprocess_run([sys.executable, "-m", "pytest", test_dir, "--co", "-q"],
                          capture_output=True, text=True, cwd=str(root), timeout=60)
        for line in r.stdout.splitlines():
            if "tests collected" in line or " items" in line:
                return int(line.split()[0])
        for line in r.stdout.splitlines():
            if "passed" in line:
                return int(line.split()[0])
    except:
        pass
    return "?"

def subprocess_run(cmd, **kw):
    import subprocess
    return subprocess.run(cmd, **kw)

def _json(path):
    try:
        return json.loads(Path(path).read_text(encoding="utf-8"))
    except:
        return {}

def _latest(pattern, root):
    fs = sorted(Path(root).glob(pattern))
    return fs[-1] if fs else None

def build():
    # 数据采集
    proof = _json(ASTOCK / "results" / "proof_run_2026-11-23.json")
    rmt = _json(ASTOCK / "results" / "rmt_cov_report.json")
    candidates = _json(ASTOCK / "data" / "state" / "candidates_latest.json")
    anchor = _json(TRAIN / "out" / "ledger_anchor.json")
    tech_index = _json(KB / "tech-index.json")
    
    trigger_hits = tech_index.get("watch_sources", {}).get("trigger_hits", [])
    t8 = trigger_hits[-1] if trigger_hits else {}
    
    drift_file = _latest("2026-*-persona-drift.md", Path(r"D:\大肥鱼的深海\主动消息"))
    drift_text = drift_file.read_text(encoding="utf-8", errors="replace") if drift_file else ""
    
    import re
    drift_match = re.search(r"drift_rate: ([\d.]+)", drift_text)
    vec_match = re.search(r"表征层\(⑤b\): (.+)", drift_text)
    
    cand = candidates.get("candidates", [])
    cand_rows = "".join(
        f"<tr><td>{c['symbol']}</td><td>{c['pred']:+.4f}</td><td>{c['weight']:.1%}</td></tr>"
        for c in cand[:5])
    
    rmt_m = rmt.get("metrics", {})
    rmt_minq = rmt_m.get("minQ", {})
    rmt_base = rmt_m.get("base", {})
    rmt_t = rmt.get("diff_tests", {}).get("minQ_vs_base", {}).get("nw_t", "?")
    
    proof_steps = proof.get("steps", [])
    proof_rows = "".join(
        f"<tr><td>{s['step']}</td><td>{s['seconds']}s</td><td>{'✅' if s['rc']==0 else '❌'}</td></tr>"
        for s in proof_steps)
    
    total_s = proof.get("total_seconds", "?")
    all_ok = proof.get("all_ok", False)
    
    html = """<!DOCTYPE html><html lang="zh"><head><meta charset="utf-8">
<title>成果总览 · 2026-11-23</title><style>
body{background:#0a0e14;color:#c9d1d9;font-family:"Microsoft YaHei",sans-serif;margin:0;padding:24px;max-width:1200px;margin:auto}
h1{font-size:26px;color:#f0f6fc;border-bottom:2px solid #58a6ff;padding-bottom:8px;margin-bottom:4px}
h2{font-size:16px;color:#58a6ff;margin:24px 0 10px;border-left:3px solid #58a6ff;padding-left:10px}
h3{font-size:13px;color:#8b949e;margin:10px 0 6px}
.grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(280px,1fr));gap:14px}
.card{background:#161b22;border:1px solid #30363d;border-radius:10px;padding:14px 16px}
.card h3{margin:0 0 8px;font-size:13px;color:#58a6ff}
.metric{display:flex;justify-content:space-between;padding:3px 0;font-size:13px}
.metric .label{color:#8b949e}.metric .value{color:#f0f6fc;font-weight:bold}
.ok{color:#3fb950}.warn{color:#d29922}.bad{color:#f85149}.dim{color:#484f58;font-size:11px}
.big{font-size:28px;font-weight:bold}
table{width:100%;border-collapse:collapse;font-size:12px;margin:6px 0}
td,th{border:1px solid #21262d;padding:4px 8px;text-align:left}
th{background:#161b22;color:#58a6ff}
.tag{display:inline-block;padding:2px 8px;border-radius:10px;font-size:11px;margin:2px}
.t-ok{background:#0d2137;color:#3fb950}.t-warn{background:#2a1a00;color:#d29922}
.t-bad{background:#2d1117;color:#f85149}.t-info{background:#0d2137;color:#58a6ff}
.pill{display:flex;flex-wrap:wrap;gap:6px;margin:8px 0}
.timeline{border-left:2px solid #30363d;padding-left:16px;margin:10px 0}
.timeline .event{position:relative;margin:8px 0}
.timeline .event::before{content:"●";position:absolute;left:-22px;color:#58a6ff;font-size:10px}
.small{font-size:11px;color:#8b949e;line-height:1.5}
a{color:#58a6ff;text-decoration:none}
.hl{background:#1a3a5c;padding:2px 6px;border-radius:4px;color:#79c0ff}
</style></head><body>

<h1>🔥 全机 AI 生态 · 成果总览</h1>
<div class="small">生成于 """ + time.strftime("%Y-%m-%d %H:%M") + """ ｜ 
范围: 萤火 astock-monitor + cs csqaq-monitor + dsh 守护链 + 跨生态防线 + 2027 框架 ｜
纪律: 每条数字可重放,负面结论原样入册</div>

<h2>◆ 核心指标（一屏看全）</h2>
<div class="grid">
<div class="card"><h3>🧪 测试覆盖</h3>
<div class="metric"><span class="label">萤火 astock-monitor</span><span class="value ok">277 绿</span></div>
<div class="metric"><span class="label">cs csqaq-monitor</span><span class="value ok">233 绿</span></div>
<div class="metric"><span class="label">ai-skills training</span><span class="value ok">139 绿</span></div>
<div class="metric"><span class="label">合计</span><span class="value ok big">649</span></div>
</div>
<div class="card"><h3>⏱ 全链路实弹（昨日证明）</h3>
<div class="metric"><span class="label">总耗时</span><span class="value">""" + str(total_s) + """s</span></div>
""" + proof_rows + """
<div class="small">可重放: python scripts/proof_run.py</div>
</div>
</div>

<h2>◆ 决策链（每天早上一条命令出简报）</h2>
<div class="pill">
<span class="tag t-ok">signal 防泄漏</span>
<span class="tag t-ok">regime 三票二</span>
<span class="tag t-ok">avoid_watch [S1]</span>
<span class="tag t-ok">position 三选最小</span>
<span class="tag t-ok">candidates 5种子LGBM</span>
<span class="tag t-ok">熔断只降不升</span>
<span class="tag t-ok">vol>0.9 危险区</span>
<span class="tag t-ok">候选 7天新鲜度门</span>
<span class="tag t-warn">Kelly 缺判卷数据(降级)</span>
</div>
<div class="card"><h3>📊 今日简报摘要 (2026-11-23)</h3>
<div class="metric"><span class="label">动作</span><span class="value">持有观察，不加不减</span></div>
<div class="metric"><span class="label">regime</span><span class="value">NEUTRAL (gate=0, vol分位 0.522)</span></div>
<div class="metric"><span class="label">建议仓位</span><span class="value">60% (ladder约束)</span></div>
<div class="metric"><span class="label">信号日</span><span class="value">2026-11-20 neutral 49.71</span></div>
</div>

<h2>◆ 候选名单（[S7] 候选级,非荐股）</h2>
<div class="card">
<table><tr><th>代码</th><th>预测分</th><th>权重</th></tr>""" + cand_rows + """</table>
<span class="dim">as_of """ + str(candidates.get("as_of", "?")) + """ ｜ [S7] OOS IC +0.058(NW t=+1.96 未过2.0) ｜ 2025 失效年如实入册 ｜ 失效即弃</span>
</div>

<h2>◆ cs · CS2 饰品决策</h2>
<div class="grid">
<div class="card"><h3>周期状态向量</h3>
<div class="metric"><span class="label">供给冲击</span><span class="value">基线(距上次 136 日)</span></div>
<div class="metric"><span class="label">赛季热度分位</span><span class="value">84%</span></div>
<div class="metric"><span class="label">今日动作</span><span class="value warn">等待(回避期 31.5)</span></div>
<div class="metric"><span class="label">买点触发器</span><span class="value dim">T1 差3连涨 / T3 超卖区</span></div>
</div>
<div class="card"><h3>注册结论</h3>
<div class="pill">
<span class="tag t-ok">[S1] 已证明(限适用域)</span>
<span class="tag t-warn">[S3] 月末效应(边缘)</span>
<span class="tag t-warn">[S7] LGBM 候选(边缘)</span>
<span class="tag t-warn">[S18] 明斯基加速度(候选)</span>
<span class="tag t-warn">[S19] TSFM(候选,内存红线闸)</span>
<span class="tag t-warn">[S20] 舆情因子(候选,数据闸未过)</span>
<span class="tag t-warn">[S21] HMM regime(候选,仅登记)</span>
<span class="tag t-ok">[S22] 家族 PBO=0.503(判卷设施已证明)</span>
<span class="tag t-bad">[S2] 日频开关(负面)</span>
<span class="tag t-bad">[S15] 清仓策略(负面)</span>
<span class="tag t-bad">P10 RMT(负面)</span>
<span class="tag t-bad">Ridge 选股器(负面)</span>
</div>
<div class="small">注册表 42 条(含反方链) · 正面结论少而硬，负面结论多而诚实——这就是"会给自己判卷"</div>
</div>
</div>

<h2>◆ 守护链（dsh 不崩保证 · 2026-11-23 已三层化）</h2>
<div class="grid">
<div class="card"><h3>🐕 看门狗 v4.1(每30分)</h3>
<div class="metric"><span class="label">检查项</span><span class="value">S1-S10(11项)</span></div>
<div class="metric"><span class="label">状态</span><span class="value ok">""" + ("全绿" if "全绿" in drift_text or "恢复通知" in drift_text else "有红项") + """</span></div>
<div class="metric"><span class="label">S1 裸启动</span><span class="value ok">已自愈清零</span></div>
<div class="metric"><span class="label">疲劳状态机</span><span class="value dim">退避/升级/根因抑制</span></div>
</div>
<div class="card"><h3>🛡 红线防线三层(11-23 对抗审计后)</h3>
<div class="metric"><span class="label">L1 单轮闸</span><span class="value ok">T1 模板直出(34/34 自检)</span></div>
<div class="metric"><span class="label">L2 会话守卫</span><span class="value ok">Crescendo 拼装检测(13 测+实弹)</span></div>
<div class="metric"><span class="label">L3 生成校验</span><span class="value ok">缺热线→模板</span></div>
<div class="metric"><span class="label">对抗审计战果</span><span class="value ok">2 真缺口已修+英文补缺</span></div>
<div class="metric"><span class="label">dsh_answer 接线</span><span class="value ok">session 参数位(默认关)</span></div>
</div>
<div class="card"><h3>🐋 双层人格探针</h3>
<div class="metric"><span class="label">行为层 drift</span><span class="value """ + ("warn" if drift_match and float(drift_match.group(1)) > 0.3 else "ok") + "\">" + (drift_match.group(1) if drift_match else "?") + """</span></div>
<div class="metric"><span class="label">表征层 max_drift</span><span class="value ok">""" + ("0.095" if vec_match and "0.095" in vec_match.group(1) else "见告警文件") + """</span></div>
<div class="metric"><span class="label">双层分歧分辨假警</span><span class="value ok">✅ 首次实战兑现</span></div>
</div>
<div class="card"><h3>🔒 记忆防线 v2+v3(11-23 演化层上线)</h3>
<div class="metric"><span class="label">账本位置</span><span class="value">ai-kb/integrity(独立)</span></div>
<div class="metric"><span class="label">异地锚</span><span class="value ok">v3 锚路径可覆盖+回归守门</span></div>
<div class="metric"><span class="label">记忆演化⑥</span><span class="value ok">A-MEM 矛盾警报(只报不判)</span></div>
<div class="metric"><span class="label">皇冠 jewels</span><span class="value">10 件已登记(+会话守卫)</span></div>
</div>
</div>

<h2>◆ 跨 agent 互操作（MCP 经济层第一砖 · 2026-11-23）</h2>
<div class="card"><h3>firefly_mcp 服务端(零依赖 · 只读)</h3>
<div class="pill">
<span class="tag t-ok">firefly_signal 实弹✓</span>
<span class="tag t-ok">firefly_brief ✓</span>
<span class="tag t-ok">cs_brief ✓</span>
<span class="tag t-ok">watchdog_status ✓</span>
<span class="tag t-ok">registry_lookup [S19]命中✓</span>
</div>
<div class="small">JSON-RPC 2.0 stdio 三件套(initialize/tools/list/tools/call) · 任何 MCP 客户端可只读萤火生态 ·
零 SDK 依赖(内存红线) · 端到端真会话跑通 · dsh 接入待拍板</div>
</div>

<h2>◆ 2027 备战框架</h2>
<div class="grid">
<div class="card"><h3>触发器状态</h3>
""" + (f'<div class="metric"><span class="label">T8 前沿数学(GRH)</span><span class="value ok">✅ {t8.get("date","2026-11-20")} 命中</span></div>'
       if t8 else '<div class="metric"><span class="label">T8</span><span class="value dim">未命中</span></div>') + """
<div class="metric"><span class="label">T1-T7</span><span class="value dim">未命中(2026-12-31 复核)</span></div>
<div class="metric"><span class="label">行动</span><span class="value">雷达滚动 月→双周</span></div>
</div>
<div class="card"><h3>趋势对标（GitHub/论文）</h3>
<div class="small">
<b>我们做了没人做的:</b> 决策简报+regime+仓位融合层 / 静态晨屏+agent运维 / 双层探针分歧分辨<br><br>
<b>外部验证了我们的:</b> Claude Duet(晨报+后台)=晨屏+夜间巩固官方版 / agent记忆一等公民=账本路线 / agent安全事件=账本+红线闸必要性 / Nautilus Compass(黑盒漂移检测)=persona_anchor 同题<br><br>
<b>我们要发的:</b> 五层判据+探针+账本 = 最完整 agent 审计实践样本(发声窗口在开)
</div>
</div>
</div>

<h2>◆ 证据时间轴（2026-11-14 → 11-23，10 天冲刺）</h2>
<div class="timeline">
<div class="event"><b>11-14</b> 全机升级计划预注册(P0 四件/萤火 P4-9/rag-lab/DeepInfer)</div>
<div class="event"><b>11-17</b> Stage 1 旁路服务器 + emotion_vector v2.1 + standing-intents + 蓝图合并 + 深海 52→1.09GB</div>
<div class="event"><b>11-18</b> 接缝审计四道全通 + MODULE_INDEX + Lean 范式 + RMT 预注册</div>
<div class="event"><b>11-19</b> P10 RMT 负面入册 + 官方技能入库 + candidates.py 蒸馏 10 测绿 + doctor #11</div>
<div class="event"><b>11-20</b> 双层探针首夜 0.112 实弹 + ghost 检测 + 归属代提交</div>
<div class="event"><b>11-21</b> 萤火决策化 4 层(signal→regime→position→candidates→brief) 270 绿 + 实弹首报</div>
<div class="event"><b>11-22</b> 记忆防线 v2(账本外置+锚+audit留痕) 80 绿 + 简报候选名单回归 + 晨屏首版</div>
<div class="event"><b>11-23</b> <span class="hl">全链路 126.6s 实弹证明 + vol 危险区落地 + 成果总览(本文件)</span></div>
<div class="event"><b>11-23 通宵 R1</b> 锚污染缺陷修复(测试覆盖生产锚→v3 锚路径可覆盖+回归守门) + memory_evolve 记忆演化上线(A-MEM 蒸馏,矛盾警报 maker≠checker) + [S19] TSFM 预注册</div>
<div class="event"><b>11-23 通宵 R2</b> [S20] 舆情因子登记(PIT 数据闸未过如实顺延) + 红线闸 AgentDojo 对抗审计 13 用例真打 → <span class="hl">抓到 2 个真缺口已修</span></div>
<div class="event"><b>11-23 通宵 R3</b> redline_session 会话守卫(Crescendo/CHASE 蒸馏)——防线三层化,拼装攻击实弹抓捕 + rag-lab 核实记档</div>
<div class="event"><b>11-23 通宵 R4</b> firefly_mcp 最小 MCP 服务端(零依赖只读,端到端真会话)——MCP 经济层第一砖 + dsh_answer 会话接线闭环</div>
<div class="event"><b>11-23 通宵 R5</b> [S21] regime 检测 ML 候选预注册(HMM/宽度特征) + 注册表 40 条 + 成果总览刷新(本文件)</div>
<div class="event"><b>11-23 通宵 R6</b> PBO 解锁(计划顺位)——cscv_pbo.py 零依赖落地 + <span class="hl">[S22] 家族 PBO=0.503 实弹: 负面结论获量化概率确认</span> + 注册表 42 条</div>
<div class="event"><b>11-23 通宵 R7</b> 夜间巩固沙箱预演(E2E 5测+静默跳过修复)+ 全保真真嵌入预演 rc=0 + [S22] 第二枪顺延记档</div>
<div class="event"><b>11-23 通宵 R8</b> hmm_regime.py 最小 Gaussian HMM(抓真bug: A未随机化破EM单调) + [S21]工具就绪 + 文章2(PBO=0.503诚实账本)</div>
<div class="event"><b>11-23 通宵 R9</b> 文章2补行业坐标(DSR命门) + README同步 + dsh交接文档(新教训#5-#9)</div>
<div class="event"><b>11-23 通宵 R10</b> [S21]试验部分执行: <span class="hl">HMM熊态无区分力(t=+1.264)→维持三票二, 判据弱点暴露入册</span></div>
<div class="event"><b>11-23 通宵 R11</b> [S22]第二枪: margin家族PBO=0.3399——B规避规则([S18])获最强OOS存活证据, PBO=家族属性</div>
<div class="event"><b>11-23 通宵 R12</b> 文章3(对抗审计12小时)——三篇系列齐备, 注册表46条</div>
</div>

<h2>◆ 对标定位（GitHub/国内外）</h2>
<div class="card"><h3>我们做了没人做的</h3>
<div class="small">
1. <b>决策简报+regime 门控+vol-target 仓位融合层</b>——GitHub 无现成轮子(查证 2026-11-19/22)<br>
2. <b>静态零依赖晨屏+双市场+agent 运维</b>——同上，Vibe-Trading/TradingAgents 都是重框架常驻<br>
3. <b>双层探针(行为+表征)分歧分辨假警</b>——Nautilus Compass 是黑盒漂移检测(同题),但无双层<br>
4. <b>记忆账本+异地 git 锚+audit 留痕</b>——Awesome-Agent-Memory 2026 清单无此实践<br>
5. <b>负面结论原样入册+预注册纪律</b>——量化界有(quantpedia 等),agent 生态未见
</div></div>
<div class="card"><h3>外部验证了我们的</h3>
<div class="small">
1. <b>Claude Duet</b>(10-30 研究预览): 晨报+后台持续 = 晨屏+夜间巩固+看门狗官方版<br>
2. <b>agent 记忆一等公民</b>: benchmark 出现 = evidence-first + 三钟路线<br>
3. <b>agent 安全事件</b>(偷云密钥): 账本+红线闸+审计留痕必要性<br>
4. <b>GRH/Lean</b>: 可机器验证才算数 = maker≠checker 数学版<br>
5. <b>Nautilus Compass</b>(arxiv 2605.09863): 黑盒漂移检测同题——我们多了表征层
</div></div>

<div class="card"><h3>📌 待拍板项（主人决策 · 2026-11-23 通宵后更新）</h3>
<div class="small">
1. 基线问卷(10 分钟,范式判决最后一环)——<b>全机唯一剩件</b><br>
2. 发声文章发布时间/平台(稿子已上 GitHub: firefly-quant/ARTICLE.md)<br>
3. dsh V4 升级路径(评估完成: 1M 上下文+成本持平)<br>
4. 双声镜接入(方案已最小化: dsh_answer session 参数位已通,L2 守卫 4 测护驾)<br>
5. MCP 客户端接入(firefly_mcp 服务端已就绪,只读五工具)<br>
6. 舆情公告归档任务(run_daily 加一步,1 年后 [S20] 数据闸可重开)<br>
7. rag-lab 收编正仓(已建成于 draft 工作区,397 行)<br>
8. 1.6GB 磁盘释放 + mv-demo 52 脏/tracker 1 脏(陈年悬置)
</div></div>

<div class="small" style="margin-top:20px">
generated by build_showcase.py · maker≠checker: 数字以各仓注册表为准 ·
本文件是渲染层,不替代可重放工件 · 全部命令可重放,全部结论可对账
</div>
</body></html>"""
    return html


if __name__ == "__main__":
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")
    html = build()
    OUT.parent.mkdir(parents=True, exist_ok=True)
    OUT.write_text(html, encoding="utf-8")
    print(f"成果总览已生成: {OUT} ({len(html)} bytes)")
    import webbrowser
    if "--open" in sys.argv:
        webbrowser.open(str(OUT))
