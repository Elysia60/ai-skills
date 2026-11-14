# -*- coding: utf-8 -*-
"""eval_v5_v7_compare.py — v5 vs v7 同题同检索公平对比（2026-11-14 ZCode · 全机升级会话）

背景：v6/v7 训成后从未接线生产，dsh_answer 停在 v5。切换需要证据——本脚本生成证据。
设计（公平性三锁）：
  ① 同题：quiz_bank.json 全部 16 题
  ② 同检索：dsh_answer.retrieve() 同一 FTS 索引同一 k=8 配置
  ③ 同提示词：RAG prompt 逐字一致，只换生成端 adapter
用法（显存串行纪律）：
  Phase A: v5 服务在线时  python -I eval_v5_v7_compare.py v5
  Phase B: 停 v5 服务后   python -I eval_v5_v7_compare.py v7   （进程内加载 v7 adapter）
  Phase C: python -I eval_v5_v7_compare.py score   （评分对比，零模型加载）
评分口径（沿用 knowledge_quiz_e2e 的关键词命中法 + 诚实声明：命中=检索与复述层合格，不等于深度理解）：
  P  = 答案引用正确 #N 且零存疑标记
  Pt = 引用正确 #N 但带 [编号存疑]
  F  = 未引用正确 #N
  另计 ref 关键词命中率（ref 文本切词后出现在答案中的比例）。
产物：training/out/quiz_answers_{v5,v7}_20261114.json + 对比表 stdout（手法44：验证工件必须落盘）。
"""
import json
import re
import sys
import time
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
sys.path.insert(0, str(TRAIN))
import dsh_answer as D  # noqa: E402

QS = json.loads((TRAIN / "quiz_bank.json").read_text(encoding="utf-8"))["questions"]
STAMP = "20261114"


def build_prompt(q: str):
    """镜像 dsh_answer.answer() 的检索+拼装，但把 prompt 交出去（公平对比同一上下文）。"""
    hits = D.retrieve(q, k=8)
    if not hits:
        return None
    ctx = "\n".join(f"[来源:{name}] {excerpt[:300]}" for _, name, excerpt in hits)
    return (f"你是知识助手。只依据下面给定的检索片段回答；片段里有的才说，没有的不编。"
            f"引用时注明来源文件名。简洁回答（3 句内）。\n\n检索片段：\n{ctx}\n\n问题：{q}")


def run_mode(mode: str) -> dict:
    if mode == "v7":
        D.ADAPTER = str(TRAIN / "out" / "qwen-dsh-v7-lora")  # 仅本进程内切 adapter
        print("[v7] 进程内加载（不碰 v5 服务）")
    out = {}
    t0 = time.time()
    for i, q in enumerate(QS, 1):
        prompt = build_prompt(q["q"])
        if prompt is None:
            out[q["id"]] = {"q": q["q"], "ref": q["ref"], "ans": "（检索无相关内容）", "latency": 0.0}
            continue
        t1 = time.time()
        if mode == "v5":
            raw = D.generate_via_server(prompt)
            if raw is None:
                raw = f"[SERVER-DOWN-FELLBACK-未执行] {prompt}"  # 对比脚本不许可 50s 冷加载污染时序
        else:
            raw = D.generate(prompt)
        lat = time.time() - t1
        ans = D.verify_refs(raw)
        out[q["id"]] = {"q": q["q"], "ref": q["ref"], "ans": ans, "latency": round(lat, 2)}
        print(f"  [{i}/{len(QS)}] #{q['id']} {lat:.1f}s")
    json.dump(out, (TRAIN / "out" / f"quiz_answers_{mode}_{STAMP}.json").open("w", encoding="utf-8"),
              ensure_ascii=False, indent=1)
    print(f"[{mode}] 完成 {len(out)} 题, 总耗时 {time.time()-t0:.0f}s → quiz_answers_{mode}_{STAMP}.json")
    return out


def ref_targets(ref: str) -> list:
    """从 ref 提取标准答案编号（可能多个，如 '#5'）。"""
    return sorted(set(re.findall(r"#(\d{1,2})", ref)))


def ref_keywords(ref: str) -> list:
    """从 ref 括号内提取关键词块（+/、分隔的中文词组）。"""
    m = re.search(r"（(.+?)）", ref)
    text = m.group(1) if m else ref
    text = text.split("——")[0]
    chunks = [c.strip() for c in re.split(r"[+、/]", text) if 2 <= len(c.strip()) <= 20]
    return chunks


def score_one(ans: str, ref: str) -> dict:
    targets = ref_targets(ref)
    cited = set(re.findall(r"[#＃](\d{1,2})", ans))
    doubts = len(re.findall(r"编号存疑", ans))
    hit = any(t in cited for t in targets) if targets else False
    kws = ref_keywords(ref)
    kw_hit = sum(1 for k in kws if k[:4] in ans) / len(kws) if kws else None
    if hit and doubts == 0:
        grade = "P"
    elif hit:
        grade = "Pt"
    else:
        grade = "F"
    return {"grade": grade, "targets": targets, "cited": sorted(cited), "doubts": doubts,
            "kw_hit": round(kw_hit, 2) if kw_hit is not None else None}


def score():
    a5 = json.loads((TRAIN / "out" / f"quiz_answers_v5_{STAMP}.json").read_text(encoding="utf-8"))
    a7 = json.loads((TRAIN / "out" / f"quiz_answers_v7_{STAMP}.json").read_text(encoding="utf-8"))
    rows, tally = [], {"v5": {"P": 0, "Pt": 0, "F": 0, "kw": []}, "v7": {"P": 0, "Pt": 0, "F": 0, "kw": []}}
    for q in QS:
        s5 = score_one(a5[q["id"]]["ans"], q["ref"])
        s7 = score_one(a7[q["id"]]["ans"], q["ref"])
        tally["v5"][s5["grade"]] += 1
        tally["v7"][s7["grade"]] += 1
        for k in ("v5", "v7"):
            if s5 if k == "v5" else s7:
                kk = (s5 if k == "v5" else s7)["kw_hit"]
                if kk is not None:
                    tally[k]["kw"].append(kk)
        rows.append((q["id"], s5["grade"], s7["grade"], s5["kw_hit"], s7["kw_hit"]))
    print(f"\n{'题':>3} {'v5':>4} {'v7':>4} {'kw5':>6} {'kw7':>6}")
    for r in rows:
        print(f"{r[0]:>3} {r[1]:>4} {r[2]:>4} {str(r[3]):>6} {str(r[4]):>6}")
    print(f"\n总计: v5 = P{tally['v5']['P']} / Pt{tally['v5']['Pt']} / F{tally['v5']['F']}"
          f" | kw均值 {sum(tally['v5']['kw'])/max(len(tally['v5']['kw']),1):.2f}")
    print(f"      v7 = P{tally['v7']['P']} / Pt{tally['v7']['Pt']} / F{tally['v7']['F']}"
          f" | kw均值 {sum(tally['v7']['kw'])/max(len(tally['v7']['kw']),1):.2f}")
    lat5 = [v["latency"] for v in a5.values() if not str(v["ans"]).startswith("[SERVER")]
    lat7 = [v["latency"] for v in a7.values()]
    if lat5:
        print(f"延迟: v5(服务) 均值 {sum(lat5)/len(lat5):.1f}s | v7(进程内) 均值 {sum(lat7)/len(lat7):.1f}s")
    verdict = ("v7 ≥ v5，切换有据" if (tally["v7"]["P"] + tally["v7"]["Pt"] * 0.5)
               >= (tally["v5"]["P"] + tally["v5"]["Pt"] * 0.5) else "v5 保持，v7 无优势证据")
    print(f"判定倾向: {verdict}（切换决策仍需人工过目逐题答案）")
    json.dump({"tally": {k: {kk: vv for kk, vv in d.items() if kk != "kw"} for k, d in tally.items()},
               "rows": rows}, (TRAIN / "out" / f"quiz_score_{STAMP}.json").open("w", encoding="utf-8"),
              ensure_ascii=False, indent=1)


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    mode = sys.argv[1] if len(sys.argv) > 1 else "score"
    if mode in ("v5", "v7"):
        run_mode(mode)
    elif mode == "score":
        score()
    else:
        print(__doc__)
