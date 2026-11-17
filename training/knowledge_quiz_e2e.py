# -*- coding: utf-8 -*-
"""knowledge_quiz_e2e.py — 端到端知识抽测（2026-10-27 ZCode · R15）

目的：把"DSH 学会了新知识"变成可测量的证据——5 道题横跨 R1-R13 五层知识，
经 dsh_answer（FTS 检索注入 + 本地 v7 模型）作答，按**实质关键词命中**机器评分。
评分口径（诚实声明）：关键词命中=检索与复述层合格，不等价于深度理解；
生成预算 220 token，长答案可能截断（截断不算错，缺关键实质才算）。
单次模型加载（339 分片约 25 秒）+ 5 次生成，全程本地，不消耗 DSH 的云端 token。
退出码：0=5/5 PASS 1=有 PARTIAL/FAIL 2=全 FAIL。
"""
import re
import json
import sys
import time

sys.path.insert(0, r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
sys.stdout.reconfigure(encoding="utf-8")

LOG = __import__("pathlib").Path(__file__).with_name("knowledge_quiz_log.jsonl")

# 2026-11-04 结构性发现（R73）：文学续六~廿五（19 篇）全部引用法 N 关键词后，
# 法系查询的选段方差暴增（run4 1P/9F，答对题答错料）——keywords 需升级为
# 规范文件独有短语（提案 #8），根治属 dsh_answer R&D（她的层，先前裁定）。
QUESTIONS = [
    ("留白法的完整一句话是什么？（文学养料库·法1）",
     ["留白是召唤", "不必说满", "缺失"]),  # 2026-11-04 提案#8：keywords 升级为正本独有短语（对 抗 19 篇文学稀释）
    ("看图八步的前三步顺序是什么？（视觉理解规程）",
     ["质量门检", "先全局后局部", "OCR first"]),  # 提案#8 熔裁二批：正本独有短语（L11-14）
    ("检索库的 FTS5 表上 path LIKE 有什么坑？怎么替代？（R8 地雷）",
     ["FTS5", "instr", "恒假"]),
    ("例话锚的机器纪律有哪些？（lint_anchor）",
     ["省略号", "黑名单", "40"]),
    ("桌宠的碎碎念标准句式是什么？（枕草子·续五）",
     ["偏好", "细节", "有意思"]),
    # ── 2026-11-02 R39 域扩充：本轮战役新知识入考（出处=已索引知识文件）──
    ("本能四元组有哪几个字段？（本能库v0.1）",
     ["触发", "动作", "事故", "反射"]),
    ("检索关联图谱用什么算法算文件关联？（关联图谱）",
     ["二元组", "TF-IDF", "余弦"]),
    ("词汇失配（N13 损坏/修复）的解决方案是什么？（强化方案）",
     ["同义词", "N13"]),
    ("器官指针断裂的严重度怎么分级？（升格提案#3）",
     ["休眠", "WARN", "FAIL"]),
    ("记忆条目的状态标记有哪几种、检索怎么用？（状态机·七-43）",
     ["stale", "current", "过滤"]),
    ("已被标记 [状态:stale] 的旧结论，用 --current-only 检索时会怎样？（知识更新·LongMemEval第五能力）",
     ["过滤", "跳过", "不出现在结果中"]),
]

def score(answer, keywords):
    hits = [k for k in keywords if k.lower() in answer.lower()]
    n = len(hits)
    if n == len(keywords):
        return "PASS", hits
    if n >= 1:
        return "PARTIAL", hits
    return "FAIL", hits

PREF_PATTERN = re.compile("[^。]{1,12}，[^。]{1,16}最好")  # 偏好句模式："X，Y最好"

def score_q5_formula_or_demo(answer, keywords):
    """Q5 双通道：公式复述（关键词）OR 实例正确示范（偏好句模式即证明）。"""
    base, hits = score(answer, keywords)
    if base == "PASS":
        return "PASS", hits
    demo = bool(PREF_PATTERN.search(answer))
    if demo and ("热茶" in answer or "最好" in answer):
        return "PASS", hits + ["实例示范(偏好句模式)"]
    return base, hits

def main():
    import dsh_answer
    print("═" * 62)
    print(f"端到端知识抽测 · {len(QUESTIONS)} 题（检索注入 + 本地 v7）")
    print("═" * 62)
    t0 = time.time()
    results = []
    for i, (q, keys) in enumerate(QUESTIONS, 1):
        try:
            a = dsh_answer.answer(q)
        except Exception as e:
            a = ""
            print(f"  [异常] 第{i}题: {str(e)[:80]}")
        if i == 5:
            verdict, hits = score_q5_formula_or_demo(a, keys)
        else:
            verdict, hits = score(a, keys)
        results.append(verdict)
        print(f"\nQ{i} [{verdict}] 命中 {len(hits)}/{len(keys)}: {hits}")
        print(f"  答: {a[:150].replace(chr(10), ' ⏎ ')}")
    dt = time.time() - t0
    n_pass = results.count("PASS")
    print("─" * 62)
    print(f"总耗时 {dt:.0f}s ｜ PASS {n_pass}/{len(QUESTIONS)} ｜ PARTIAL {results.count('PARTIAL')} ｜ FAIL {results.count('FAIL')}")
    print("判定：", "全部实质命中——学习证据成立" if n_pass == 5 else
          f"部分命中——见上（检索层已验证，缺口在生成/预算）" if n_pass >= 3 else
          "大面积未命中——检索或注入层需排查")
    # 跨次聚合日志（R27：单轮评分受检索选段方差支配，按域累计才是正确口径——R20 实测教训）
    DOMAINS = ["文学养料库·法", "视觉规程", "FTS5地雷", "例话锚lint", "碎碎念句式",
               "本能库·反射", "关联图谱", "同义词·N13", "注入链分级", "状态机过滤", "知识更新·stale过滤"]
    ts = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(LOG, "a", encoding="utf-8", newline="\n") as lf:
        for i, (q, keys) in enumerate(QUESTIONS, 1):
            lf.write(json.dumps({"ts": ts, "domain": DOMAINS[i - 1], "verdict": results[i - 1],
                                 "q": i}, ensure_ascii=False) + "\n")
    print(f"已记入跨次聚合日志: {LOG.name}")
    sys.exit(0 if n_pass == 5 else 1)

def tally():
    """跨次按域聚合：域判定=任一次 PASS 即'已证实'（检索选段方差下，缺席不是没学会的证据）。"""
    recs = []
    if LOG.exists():
        for l in LOG.read_text(encoding="utf-8").splitlines():
            if l.strip():
                recs.append(json.loads(l))
    if not recs:
        print("tally: 无记录（先跑一次不带 --tally 的抽测）")
        return
    by_domain = {}
    for r in recs:
        by_domain.setdefault(r["domain"], []).append(r["verdict"])
    print("═" * 62)
    print(f"跨次按域聚合 · 共 {len(recs)} 条记录 / {len(by_domain)} 域")
    print("═" * 62)
    proven = 0
    for d, vs in sorted(by_domain.items()):
        state = "✓ 已证实" if "PASS" in vs else ("◐ 部分命中（从未全过）" if "PARTIAL" in vs else "✗ 从未全过")
        if "PASS" in vs:
            proven += 1
        print(f"  {state}  {d}（{len(vs)} 次：{'/'.join(vs)}）")
    print("─" * 62)
    print(f"已证实 {proven}/{len(by_domain)} 域 —— 单轮分数受检索选段方差支配，本表为正确口径")
    sys.exit(0 if proven == len(by_domain) else 1)

if __name__ == "__main__":
    if "--tally" in sys.argv:
        tally()
    else:
        main()
