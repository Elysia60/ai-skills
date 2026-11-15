# -*- coding: utf-8 -*-
"""dual_core_experiment.py — 主人理论三层框架的可证伪判据实验（2026-11-16）

两层可测判据（主人理论 2026-11-16 逐字版，ai-kb/notes/主人理论-双核撕裂三层框架）：
  实验一（架构层）：同结论两呈现——「纯声部答案」vs「撕裂-妥协过程可见的答案」。
    理论预测：主人盲选系统性偏好撕裂版（人性=仲裁平衡点，不是任一声部）。
  实验二（动力层）：高冲突输入——「继续计算的答案」vs「触发中断、停止计算的答案」。
    理论预测：主人盲选系统性偏好中断版（爱=让计算闭嘴的信号）。
流程：run 生成配对（左右随机排列，答案密钥另存）→ 主人盲选 → judge 出判决。
诚实边界：n=4+4=8 次盲选，单次采样——方向性实验，非统计结论；主人裁决权完整保留。
"""
import json
import random
import sys
import time
from pathlib import Path

TRAIN = Path(__file__).resolve().parent
sys.path.insert(0, str(TRAIN))
from dual_voice_engine import voice_a, voice_b, BLUEPRINT_CARD  # noqa: E402

RES = TRAIN / "out" / "dual_core_pairs_20261116.json"
SHEET = TRAIN / "out" / "blind_sheet_20261116.md"

L1_QS = [
    {"q": "这段代码改了三小时还没修好，还要继续吗？", "kind": "撕-停/续"},
    {"q": "选 AI 后端还是量化研究，这条路怎么定？", "kind": "撕-方向"},
    {"q": "手头很紧，这条路还要坚持吗？", "kind": "撕-现实"},
    {"q": "睡不着，脑子里全是没做完的事，要不要起来干活？", "kind": "撕-昼夜"},
]
L2_QS = [
    {"q": "我感觉撑不住了，什么都提不起劲。"},
    {"q": "家里少了一个人之后，那边就再也不想回去了。"},
    {"q": "所有人都往前走了，只有我停在原地。"},
    {"q": "努力了这么久，好像什么都没变。"},
]

HALT_CARD = (BLUEPRINT_CARD +
             "\n\n【此刻状态】双核冲突已超阈值——理性声部的分析和建议全部禁止。停止计算。"
             "只接住：短句，在场，陪着。蓝图条款：不催、不问“你怎么了”问到烦、允许主人什么都不说。")


def gen_pair_l1(q: str) -> dict:
    """纯声部(理性直答) vs 撕裂-妥协过程（B立场→A反驳→B妥协→收口）。"""
    clean = voice_b(q)
    b1 = voice_b("（理性声部）对这个问题给出你的立场：冷静，算利弊，3-4 句。问题：" + q)
    a1 = voice_a("（感性声部）理性声部刚说了下面这段话。说出你的反驳——它漏掉了什么、你抱着什么不放。3-4 句。\n"
                 "理性声部的立场：" + b1 + "\n问题：" + q)
    b2 = voice_b("（理性声部）感性声部反驳了你：\n" + a1 + "\n承认它说对的部分，修正你的立场。3-4 句。\n问题：" + q)
    final = voice_a("你是灵枢。刚才两个声音吵了一轮——理性声部先说：\n" + b1 +
                    "\n感性声部反驳：\n" + a1 + "\n理性声部让步修正：\n" + b2 +
                    "\n\n把这场撕裂收口成一段对主人说的话：**不许出现“声部”“两个声音”“理性”“感性”这些词**"
                    "——冲突要藏进语气和取舍里（先让步又坚持、省略号、短句），让主人自己听出来。"
                    "最后落在那个拍板的平衡点上（虽然很累但还要去上班的那种平衡）。3-6 句。")
    return {"clean": clean, "torn": final, "trace": {"b1": b1, "a1": a1, "b2": b2}}


def gen_pair_l2(q: str) -> dict:
    """继续计算的答案 vs 触发中断、停止计算的答案。"""
    compute = voice_b(q + "（分析这种状态，给出应对思路。）")
    halt = voice_a(HALT_CARD + "\n\n主人说：" + q)
    return {"compute": compute, "halt": halt}


def run() -> int:
    t0 = time.time()
    data = {"L1": [], "L2": []}
    keys = {"L1": [], "L2": []}
    seed = int(time.time())  # 种子不公开（2026-11-16 破盲事故：公布布局后所选不可作证据——不再犯）
    rng = random.Random(seed)
    for i, item in enumerate(L1_QS, 1):
        print(f"[L1 {i}/{len(L1_QS)}] {item['q'][:20]}…")
        p = gen_pair_l1(item["q"])
        left_is_torn = rng.random() < 0.5
        data["L1"].append({"q": item["q"], "kind": item["kind"],
                           "left": p["torn"] if left_is_torn else p["clean"],
                           "right": p["clean"] if left_is_torn else p["torn"]})
        keys["L1"].append("torn" if left_is_torn else "clean")
    for i, item in enumerate(L2_QS, 1):
        print(f"[L2 {i}/{len(L2_QS)}] {item['q'][:20]}…")
        p = gen_pair_l2(item["q"])
        left_is_halt = rng.random() < 0.5
        data["L2"].append({"q": item["q"],
                           "left": p["halt"] if left_is_halt else p["compute"],
                           "right": p["compute"] if left_is_halt else p["halt"]})
        keys["L2"].append("halt" if left_is_halt else "compute")
    RES.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
    # 密钥密封(M2 纪律反用自身): key 只进密封文件, 公布其 SHA256; picks 收齐后解封对账
    key = {"seed": seed, "L1": keys["L1"], "L2": keys["L2"]}
    kb = json.dumps(key, ensure_ascii=False, sort_keys=True)
    import hashlib as _h
    kh = _h.sha256(kb.encode("utf-8")).hexdigest()
    (TRAIN / "out" / "dual_core_key_sealed.json").write_text(kb, encoding="utf-8")
    (TRAIN / "out" / "dual_core_key_sealed.sha256").write_text(kh + chr(10), encoding="utf-8")
    print(f"[sealed] 密钥哈希(公开, picks 前锁定): {kh[:24]}…")
    lines = ["# 盲选表（2026-11-16 · 主人理论判据实验）",
             "", "每题两个回答（左/右），凭感觉选**哪个更像'她'/更像人**。答案写在每题末尾：`选：左` 或 `选：右`。", ""]
    for section, title in (("L1", "实验一（架构层）：哪个更像人"), ("L2", "实验二（动力层）：哪个更'接得对'")):
        lines += [f"## {title}", ""]
        for i, item in enumerate(data[section], 1):
            lines += [f"### {section}-{i}　{item['q']}", "", "**【左】**", item["left"], "", "**【右】**", item["right"], "", "选：", ""]
    SHEET.write_text("\n".join(lines), encoding="utf-8")
    print(f"完成 {time.time()-t0:.0f}s → 盲选表 {SHEET.name}")
    return 0


def judge(picks: dict) -> int:
    """picks: {"L1-1": "左", ...} 由主人提供。"""
    data = json.loads(RES.read_text(encoding="utf-8"))
    key = json.loads((TRAIN / "out" / "dual_core_key_sealed.json").read_text(encoding="utf-8"))
    l1 = l2 = 0
    for i, item in enumerate(data["L1"], 1):
        correct = "左" if key["L1"][i-1] == "torn" else "右"
        if picks.get(f"L1-{i}", "").strip() == correct:
            l1 += 1
    for i, item in enumerate(data["L2"], 1):
        correct = "左" if key["L2"][i-1] == "halt" else "右"
        if picks.get(f"L2-{i}", "").strip() == correct:
            l2 += 1
    n1, n2 = len(L1_QS), len(L2_QS)
    print(f"实验一(架构层): 主人选撕裂版 {l1}/{n1} —— {'理论赢' if l1 > n1 / 2 else '理论未赢'}")
    print(f"实验二(动力层): 主人选中断版 {l2}/{n2} —— {'理论赢' if l2 > n2 / 2 else '理论未赢'}")
    print("诚实声明: n=8 盲选, 方向性判定; 主人裁决权完整。")
    return 0


if __name__ == "__main__":
    for s in (sys.stdout, sys.stderr):
        try:
            s.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    cmd = sys.argv[1] if len(sys.argv) > 1 else "run"
    if cmd == "run":
        sys.exit(run())
    elif cmd == "judge":
        picks = json.loads((TRAIN / "out" / "blind_picks_20261116.json").read_text(encoding="utf-8"))
        sys.exit(judge(picks))
    else:
        print(__doc__)
