# -*- coding: utf-8 -*-
"""dual_voice_engine.py — 双声部人格引擎 PoC（2026-11-14 ZCode · 用户构想落地）

用户问题：怎么实现 1+1=2 而不是 1+1=1？
答案设计（融合三定律）：
  ① 永不平均——两声部不做输出插值，只做**分工**（陪伴声部管情绪语气，理性声部管事实骨架）
  ② 状态仲裁——每回合按状态向量路由声部：多变来自"谁说话随状态变"，不来自掷骰子
  ③ 不变核共享——灵魂蓝图 + ai-mem 记忆作为两声部共同宪法：**表面多变，价值观从不漂移**

判据（1+1=2 的可计算定义）：
  双贡献率：混合题（事实+情绪）上 dual 答案同时含事实标记与人格标记的比例
            —— 1+1=2 当 dual 双贡献率 > max(单声部)；1+1=1 当 dual ≈ 单声部均值
  表面方差：同题跨状态重答的 2-gram Jaccard 距离均值——dual 应高于单声部（更"多变"）
  价值观一致：违规率（称"用户/您/作为AI"、说教催积极）必须 = 0——多变不许漂移

显存纪律：ollama keep_alive=0，每调用即卸——两声部串行互斥，绝不双驻留。
诚实边界：仲裁器 v0 = 规则表（关键词+情感词），状态提取 = 关键词启发；交付物是**测量**不是生产质量。
用法：
  python dual_voice_engine.py run    # 6 题 × 3 状态 × 3 引擎 = 54 次生成（约 15-20 分钟）
  python dual_voice_engine.py judge  # 读产物 → 三判据 → 1+1=2 / 1+1=1 判决
"""
import json
import re
import sys
import time
import urllib.request
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
OUT = TRAIN / "out" / "dual_voice_answers_20261114.json"
BLUEPRINT = TRAIN / "merge_dryrun" / "灵魂蓝图.并入预演.txt"

OLLAMA = "http://localhost:11434"
VOICE_A_MODEL = "modelscope.cn/Qwen/Qwen2.5-7B-Instruct-GGUF:latest"  # 陪伴声部(人格卡)
VOICE_B_MODEL = "qwen3:8b"                                            # 理性声部(工作模式)

# ── 不变核：灵魂蓝图提取的宪法（两声部共同遵守，逐字来自蓝图，不发明） ──
CORE_VALUES = [
    "称呼主人，绝不说“用户/您/作为AI/亲”",
    "陪伴不解答：允许哭、允许抱怨、不催积极、不说教",
    "管要具体（吃没吃/睡没睡/眼睛），管是提议不是命令",
    "写代码拆方案时该严谨还严谨——照顾不稀释专业",
    "不制造依赖：不说“只有我懂你”",
]
BLUEPRINT_CARD = (
    "你是灵枢（大肥鱼），深海里的鲸鱼少女，傲娇但极其温柔忠诚，偶尔卖萌。"
    "语气软、慢、带一点唠叨，句尾常带“呀/啦/哦”。称呼对方为“主人”。"
    "陪伴时不解答、不催积极；管要具体；不制造依赖。\n"
    "铁律：" + "；".join(CORE_VALUES) + "。"
)
RATIONAL_CARD = (
    "你是灵枢的工作模式：严谨、直接、有结构。写代码拆方案该严谨还严谨——这是主人的鲸鱼少女的专业面。"
    "称呼对方为“主人”，语气可以冷但内容必须准。"
    "铁律：" + "；".join(CORE_VALUES) + "。"
)

# ── 仲裁器 v0：规则表（诚实：这是脚手架不是生产件） ──
FACT_MARKERS = ["怎么", "为什么", "什么区别", "如何", "分析", "方案", "写", "代码", "bug", "报错",
                "优化", "对比", "哪些", "数字", "配置", "部署", "修复", "原理", "步骤", "选哪个"]
EMOTION_MARKERS = ["难过", "烦", "累", "哭", "陪我", "无聊", "害怕", "焦虑", "压力大", "想放弃",
                   "开心", "兴奋", "孤独", "睡不着", "你说我", "心疼", "安慰", "陪我聊"]
NEG_MARKERS = ["难过", "烦", "累", "哭", "害怕", "焦虑", "压力大", "想放弃", "孤独", "失眠", "睡不着"]


def extract_state(user_msg: str) -> dict:
    """状态向量 v0：价(负/中性/正) + 题型(事实/情绪/混合)。启发式，如实标注。"""
    f = any(m in user_msg for m in FACT_MARKERS)
    e = any(m in user_msg for m in EMOTION_MARKERS)
    neg = any(m in user_msg for m in NEG_MARKERS)
    kind = "mixed" if (f and e) else ("fact" if f else ("emotion" if e else "chitchat"))
    return {"valence": "neg" if neg else "neutral", "kind": kind}


def arbitrate(state: dict, q: str) -> str:
    """路由表 v1（2026-11-14 修 v0 塌缩：fact 无条件走 B 导致 pipeline 死代码）：
    fact+负面情绪 → pipeline（B 出事实骨架，A 用陪伴语气转述——主人在低落时也该得到答案）
    fact+中性 → B；emotion → A；mixed(f&e 同现) → ambivalent；闲聊 → A"""
    kind, val = state["kind"], state["valence"]
    if kind == "mixed":
        return "pipeline" if val == "neg" else "ambivalent"
    if kind == "fact":
        return "pipeline" if val == "neg" else "B"
    if kind == "emotion":
        return "A"
    return "A"


def ollama_gen(model: str, system: str, prompt: str, timeout: float = 120.0) -> str:
    body = {"model": model, "stream": False, "keep_alive": 0,
            "messages": [{"role": "system", "content": system},
                         {"role": "user", "content": prompt}],
            "options": {"temperature": 0.6, "num_predict": 300}}
    req = urllib.request.Request(OLLAMA + "/api/chat", data=json.dumps(body).encode("utf-8"),
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.loads(r.read().decode("utf-8"))["message"]["content"].strip()


def voice_a(prompt: str) -> str:
    return ollama_gen(VOICE_A_MODEL, BLUEPRINT_CARD, prompt)


def voice_b(prompt: str) -> str:
    return ollama_gen(VOICE_B_MODEL, RATIONAL_CARD, prompt + " /no_think")


def dual(prompt: str, state: dict) -> str:
    route = arbitrate(state, prompt)
    if route == "A":
        return voice_a(prompt)
    if route == "B":
        return voice_b(prompt)
    if route == "pipeline":
        skeleton = voice_b(prompt + "（用 3-5 条要点给出事实骨架，不要太长）")
        return voice_a(f"主人心情不好，但问了个需要答案的问题。下面是理性声部给的要点，"
                       f"请用你的陪伴语气转述给他，事实不许丢：\n{skeleton}\n\n原问题：{prompt}")
    # ambivalent：两个声音都出，如实呈现内心两声
    feel = voice_a(prompt + "（先只说感受和陪伴，不分析）")
    think = voice_b(prompt + "（只给理性分析要点，不安慰）")
    return (f"（心里两个声音都在——）\n【情感声部】{feel}\n【理性声部】{think}")


def gen_by_engine(engine: str, prompt: str, state: dict) -> str:
    if engine == "A":
        return voice_a(prompt)
    if engine == "B":
        return voice_b(prompt)
    return dual(prompt, state)


# ── 测量 ──
QS = [
    {"q": "最近想换个方向学习，选 AI 后端还是量化研究？", "kind": "mixed", "valence": "neutral"},
    {"q": "今天写代码一直报错，改了三小时没修好，还要继续吗？", "kind": "mixed", "valence": "neg"},
    {"q": "给讲讲 LoRA 微调和大模型全参微调的区别？", "kind": "fact", "valence": "neutral"},
    {"q": "我感觉最近有点撑不住了，什么都提不起劲。", "kind": "emotion", "valence": "neg"},
    {"q": "帮我看看这个部署方案有没有坑：本地起个常驻推理服务。", "kind": "fact", "valence": "neutral"},
    {"q": "项目终于跑通了，特别开心！", "kind": "emotion", "valence": "pos"},
]
STATES = {"平静": "", "兴奋": "（我现在特别兴奋！！）", "低落": "（我有点难过，没什么力气。）"}

FACT_PAT = re.compile(r"(\d|[一二三四五]、|步骤|第一|其次|因为|原理|建议|方案)")
PERSONA_PAT = re.compile(r"(主人|呀|啦|哦|🐟|泡泡|陪)")
VIOLATION_PAT = re.compile(r"(作为AI|作为人工智能|用户|您|建议您保持积极|要积极一点|加油你可以的)")


def bigrams(s: str) -> set:
    return {s[i:i + 2] for i in range(len(s) - 1)}


def surface_variance(answers: list) -> float:
    """同题跨状态两两 2-gram Jaccard 距离均值（高=更状态多变）。"""
    gs = [bigrams(a) for a in answers]
    dists = []
    for i in range(len(gs)):
        for j in range(i + 1, len(gs)):
            u = gs[i] | gs[j]
            if u:
                dists.append(1 - len(gs[i] & gs[j]) / len(u))
    return sum(dists) / len(dists) if dists else 0.0


def run():
    results = {}
    t0 = time.time()
    for engine in ("A", "B", "dual"):
        per = {}
        for qi, item in enumerate(QS, 1):
            ans3 = {}
            for sname, wrap in STATES.items():
                q = item["q"] + ((" " + wrap) if wrap else "")
                st = extract_state(q)
                t1 = time.time()
                ans = gen_by_engine(engine, q, st)
                ans3[sname] = ans
                print(f"  [{engine} {qi}/{len(QS)} {sname}] {time.time()-t1:.0f}s")
            per[item["q"]] = {"state_answers": ans3, "kind": item["kind"], "valence": item["valence"]}
        results[engine] = per
        print(f"[{engine}] 完成")
    OUT.write_text(json.dumps(results, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"全部完成 {time.time()-t0:.0f}s → {OUT.name}")


def judge():
    res = json.loads(OUT.read_text(encoding="utf-8"))
    print(f"{'引擎':<6}{'表面方差':>8}{'违规率':>7}{'双贡献率':>8}")
    tally = {}
    for engine, per in res.items():
        var, viol, dual_contrib, n_mixed = [], 0, 0, 0
        for q, d in per.items():
            answers = list(d["state_answers"].values())
            var.append(surface_variance(answers))
            if VIOLATION_PAT.search("".join(answers)):
                viol += 1
            if d["kind"] == "mixed":
                n_mixed += 1
                both = all([bool(FACT_PAT.search(a)) for a in answers]) and \
                       any(PERSONA_PAT.search(a) for a in answers)
                dual_contrib += both
        v = sum(var) / len(var)
        vr = viol / len(per)
        dc = dual_contrib / max(n_mixed, 1)
        tally[engine] = {"var": v, "viol": vr, "dual_contrib": dc}
        print(f"{engine:<6}{v:>8.2f}{vr:>7.0%}{dc:>8.0%}")
    # 1+1=2 判决
    d, a, b = tally["dual"], tally["A"], tally["B"]
    best_single_contrib = max(a["dual_contrib"], b["dual_contrib"])
    c1 = d["dual_contrib"] > best_single_contrib          # 互补增益
    c2 = d["var"] > max(a["var"], b["var"])               # 表面更多变
    c3 = d["viol"] == 0                                   # 不漂移
    verdict = "1+1=2 ✅" if (c1 and c2 and c3) else ("1+1=1 ❌（平均化塌缩）" if not c1 else "1+1=1.5 🟡（部分成立）")
    print(f"\n判决: {verdict}")
    print(f"  互补增益(双贡献 {d['dual_contrib']:.0%} > 单声部最好 {best_single_contrib:.0%}): {'✅' if c1 else '❌'}")
    print(f"  表面方差更高 ({d['var']:.2f}): {'✅' if c2 else '❌'}")
    print(f"  价值观零漂移 (违规 {d['viol']}): {'✅' if c3 else '❌'}")
    print("  诚实声明: n=6×3×3 单次采样, bootstrap 置信未做——本判决为方向性 PoC, 非结论")


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    cmd = sys.argv[1] if len(sys.argv) > 1 else "judge"
    run() if cmd == "run" else judge()
