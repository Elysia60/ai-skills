# -*- coding: utf-8 -*-
"""memory_evolve.py — 记忆演化层(A-MEM 蒸馏,2026-11-23)

出处: A-MEM(agentic memory,笔记链接+演化)思想蒸馏为零依赖模块——
新事实进入记忆体系时,不是无脑追加,而是先与既有记忆语料(结论注册表+皇冠jewels+手法)比对:

  ① sim < 关联阈值        → NEW        新话题,放行入册
  ② 关联阈值 ≤ sim        → LINK       关联记忆,标注链回 id(A-MEM 的 note linking)
  ③ sim ≥ 矛盾阈值 且 立场相反 → CONTRADICTION 矛盾警报(黄)——新事实与在册结论打架,
                              推主动消息,由主人裁决谁对(maker≠checker)
  ④ sim ≥ 矛盾阈值 且 立场一致 → REINFORCE  重复确认,无需动作

红线: fail-open——嵌入不可用/任何异常 → 报告 ok=False,绝不阻塞夜间巩固;
      本模块只产生警报,不修改账本/注册表(裁决权在主人)。

嵌入: 复用 persona_vector.ollama_embed(bge-m3, 1024维, 自带重试)。

用法:
  python memory_evolve.py build-corpus --md METHODS.md -o out/memory_corpus.json
  python memory_evolve.py run --new 今日新事实.txt --corpus out/memory_corpus.json
"""
from __future__ import annotations

import json
import re
import sys
import time
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from persona_vector import ollama_embed  # noqa: E402

PROACTIVE = Path(r"D:\大肥鱼的深海\主动消息")

# 预注册阈值(写死): bge-m3 余弦在中文长短文本上普遍偏高,0.55 才算同话题,0.72 以上同话题且窄
SIM_LINK = 0.55
SIM_CONTRA = 0.72
TOP_K = 3

# 立场反对词对(可注入自定义;检查时先剥长词再查短词,防"不显著"误触"显著")
STANCE_PAIRS = [
    ("有效", "无效"), ("买入", "卖出"), ("加仓", "减仓"), ("提升", "下降"),
    ("正面", "负面"), ("可行", "不可行"), ("支持", "反对"), ("通过", "否决"),
    ("启用", "停用"), ("允许", "禁止"), ("候选", "负面入册"), ("显著", "不显著"),
    ("只降不升", "允许回升"), ("真实", "虚高"),
]


def _cos(a: list[float], b: list[float]) -> float:
    num = sum(x * y for x, y in zip(a, b))
    na = sum(x * x for x in a) ** 0.5
    nb = sum(x * x for x in b) ** 0.5
    if na == 0 or nb == 0:
        return 0.0
    return num / (na * nb)


def _has(word: str, text: str, shield: str) -> bool:
    """word 在 text 中出现,但先把 shield(长词)剥掉——防子串误触。"""
    return word in text.replace(shield, "") if shield else word in text


def stance(new_text: str, old_text: str,
           pairs: list[tuple[str, str]]) -> tuple[str, tuple[str, str] | None]:
    """比较两条文本的立场: oppose(相反) / same(一致) / none(无立场信号)。"""
    for a, b in sorted(pairs, key=lambda p: -max(len(p[0]), len(p[1]))):
        a_new = _has(a, new_text, b if len(b) > len(a) else "")
        b_new = _has(b, new_text, a if len(a) > len(b) else "")
        a_old = _has(a, old_text, b if len(b) > len(a) else "")
        b_old = _has(b, old_text, a if len(a) > len(b) else "")
        if (a_new and b_old) or (b_new and a_old):
            return "oppose", (a, b)
        if (a_new and a_old) or (b_new and b_old):
            return "same", (a, b)
    return "none", None


def classify(new_text: str, old_text: str, sim: float,
             sim_link: float = SIM_LINK, sim_contra: float = SIM_CONTRA,
             pairs: list[tuple[str, str]] = STANCE_PAIRS) -> dict:
    """单条比对 → 演化判定。"""
    st, hit = stance(new_text, old_text, pairs)
    if sim >= sim_contra and st == "oppose":
        return {"verdict": "CONTRADICTION", "sim": round(sim, 4), "pair": hit}
    if sim >= sim_contra and st == "same":
        return {"verdict": "REINFORCE", "sim": round(sim, 4), "pair": hit}
    if sim >= sim_link:
        return {"verdict": "LINK", "sim": round(sim, 4), "pair": hit}
    return {"verdict": "NEW", "sim": round(sim, 4), "pair": None}


def evolve(new_texts: list[str], corpus: list[dict], embed_fn=ollama_embed,
           sim_link: float = SIM_LINK, sim_contra: float = SIM_CONTRA,
           pairs: list[tuple[str, str]] = STANCE_PAIRS, top_k: int = TOP_K) -> dict:
    """主入口: 新事实列表 × 记忆语料 → 演化报告。fail-open。"""
    t0 = time.time()
    try:
        corpus_vecs = [(c, embed_fn(c["text"])) for c in corpus]
        new_vecs = [(t, embed_fn(t)) for t in new_texts]
    except Exception as e:  # noqa: BLE001
        return {"ok": False, "error": f"{type(e).__name__}: {e}",
                "detail": "嵌入不可用——记忆演化跳过(fail-open,不阻塞巩固)"}
    details, contra = [], 0
    for text, vec in new_vecs:
        ranked = sorted((( _cos(vec, cv), c) for c, cv in corpus_vecs),
                        key=lambda x: -x[0])[:top_k]
        if not ranked:
            continue
        top_sim, top_c = ranked[0]
        d = classify(text, top_c["text"], top_sim, sim_link, sim_contra, pairs)
        entry = {"new": text[:80], "verdict": d["verdict"], "sim": d["sim"],
                 "related_id": top_c["id"], "related": top_c["text"][:60]}
        if d["verdict"] == "CONTRADICTION":
            entry["pair"] = d["pair"]
            contra += 1
        details.append(entry)
    return {"ok": True, "n_new": len(new_texts), "n_contradictions": contra,
            "n_reinforce": sum(1 for x in details if x["verdict"] == "REINFORCE"),
            "n_links": sum(1 for x in details if x["verdict"] == "LINK"),
            "n_new_topics": sum(1 for x in details if x["verdict"] == "NEW"),
            "details": details, "elapsed_s": round(time.time() - t0, 1)}


def push_alert(day: str, rep: dict) -> Path:
    """矛盾警报 → 主动消息(黄,待主人裁决)。maker≠checker: 本模块只报不判。"""
    lines = [f"⚠ 记忆演化警报 {day}", ""]
    for d in rep["details"]:
        if d["verdict"] == "CONTRADICTION":
            lines.append(f"⛔ 新事实: {d['new']}")
            lines.append(f"   与在册 {d['related_id']} 相似度 {d['sim']:.2f} 立场相反")
            lines.append(f"   在册结论: {d['related']}")
            if d.get("pair"):
                lines.append(f"   冲突词对: {d['pair'][0]} ↔ {d['pair'][1]}")
            lines.append("")
    lines.append("裁决规则(maker≠checker): 主人定谁对 → 对方按审计纪律修正(账本留痕)。本模块只报不判。")
    out = PROACTIVE / f"{day}-记忆演化.md"
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return out


def parse_registry_md(path: Path) -> list[dict]:
    """从 METHODS.md 式表格提取语料: | [S1] | 结论 | 证据 | 状态 |。"""
    out = []
    for line in path.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if not line.startswith("| ["):
            continue
        cols = [c.strip() for c in line.split("|")]
        if len(cols) >= 3 and "---" not in cols[1]:
            out.append({"id": cols[1], "text": f"{cols[1]} {cols[2]}"})
    return out


def main(argv: list) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "build-corpus":
        mds = [Path(argv[i + 1]) for i, a in enumerate(argv) if a == "--md"]
        out = Path(argv[argv.index("-o") + 1]) if "-o" in argv else Path("out/memory_corpus.json")
        corpus = []
        for md in mds:
            corpus.extend(parse_registry_md(md))
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(json.dumps(corpus, ensure_ascii=False, indent=1), encoding="utf-8")
        print(json.dumps({"corpus": str(out), "entries": len(corpus)}, ensure_ascii=False))
        return 0
    if cmd == "run":
        new_f = Path(argv[argv.index("--new") + 1])
        corpus_f = Path(argv[argv.index("--corpus") + 1])
        texts = [l.strip() for l in new_f.read_text(encoding="utf-8").splitlines()
                 if l.strip() and not l.startswith("#")]
        corpus = json.loads(corpus_f.read_text(encoding="utf-8"))
        rep = evolve(texts, corpus)
        print(json.dumps({k: v for k, v in rep.items() if k != "details"},
                         ensure_ascii=False, indent=1))
        if rep.get("ok") and rep["n_contradictions"]:
            day = (argv[argv.index("--date") + 1] if "--date" in argv
                   else date.today().isoformat())
            print("警报:", push_alert(day, rep))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
