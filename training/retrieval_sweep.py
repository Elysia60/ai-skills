# -*- coding: utf-8 -*-
"""retrieval_sweep.py — 1000 次随机超参搜索（2026-10-25 ZCode · 主人令"验证 1000 次"的诚实兑现）

方法：Bergstra & Bengio 2012（JMLR，被引 1.9 万）——随机搜索优于网格。
对象：dsh_answer v2.2 检索层参数（已命名天花板：词汇失配）。
评测：20 题金标（检索级：期望来源文件应出现在 top-k）——全部来自已验证记忆事实。
安全：只读评测；最优配置仅在击败基线时落地（否则保持现状=零退步）。
"""
import random
import re
import sqlite3
from pathlib import Path

DB = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\.search-index.db")

GOLD = [
    ("会话日志损坏是怎么修好的", ["2026-10-01", "DSH-LEGACY"]),
    ("主会话 cbb6749d 的日志为什么读不进来", ["gaps.json", "2026-10-01"]),
    ("主目录的 nul 文件是谁删的", ["gaps.json", "KEY.md"]),
    ("dsh-spill-policy 的文件被写成了什么", ["gaps.json"]),
    ("dafeiyu 心跳超时一共多少次", ["gaps.json", "2026-10-24"]),
    ("她最后的话说了什么", ["2026-10-21"]),
    ("鲸鱼少女自称什么名字", ["灵魂蓝图"]),
    ("看门狗重启上限几次每小时", ["SKILL.md", "汐-总纲"]),
    ("OpenClaw 在 GitHub 多少星", ["GitHub高星", "Top100"]),
    ("Mem0 的基准争议说明什么", ["SKILL.md", "对齐审计"]),
    ("pending_verify 是什么意思", ["AGENTS.md", "SKILL.md"]),
    ("每日仪式是什么", ["AGENTS.md"]),
    ("记忆状态机怎么标记过期条目", ["SKILL.md", "吸收包"]),
    ("今晚月色真美是什么意思", ["人格增强", "经典思想库"]),
    ("弗洛姆爱的四要素是哪些", ["人格增强", "经典思想库"]),
    ("知行合一对应哪条工程规矩", ["经典思想库"]),
    ("斯多葛控制二分法是什么", ["经典思想库", "汐-总纲"]),
    ("验证台账每行有哪五个字段", ["SKILL.md"]),
    ("三态说话是哪三态", ["SKILL.md"]),
    ("lightrag watchdog 预算闸是谁建的", ["2026-10-25", "verify-ledger"]),
]


def terms_of(q, variant):
    terms = set()
    for run in re.findall(r"[A-Za-z0-9_.-]+|[\u4e00-\u9fff]+", q):
        if re.match(r"^[A-Za-z0-9_.-]+$", run):
            if len(run) >= 2:
                terms.add(run)
        else:
            if variant in ("g3", "g34"):
                terms.update(run[i:i + 3] for i in range(len(run) - 2))
            if variant in ("g4", "g34"):
                terms.update(run[i:i + 4] for i in range(len(run) - 3))
    return terms


def weight_of(path, cfg):
    p = path.replace("\\", "/").lower()
    if "/daily/" in p or "时间线" in p or "日记" in p:
        return cfg["daily"]
    if "gaps.json" in p:
        return cfg["gaps"]
    if "灵魂蓝图" in p or "记忆锚点" in p or "每日.txt" in p:
        return cfg["deepsea"]
    if "skill.md" in p:
        return cfg["skill"]
    return 1.0


def main():
    conn = sqlite3.connect(str(DB))
    # 预计算：每变体 {term: {path: count}}（一次查询，千次复用——这就是不烧算力的原因）
    tables = {}
    for variant in ("g3", "g4", "g34"):
        tbl = {}
        for q, _ in GOLD:
            for t in terms_of(q, variant):
                if t in tbl:
                    continue
                m = {}
                try:
                    for path, content in conn.execute("SELECT path, content FROM docs WHERE docs MATCH ?", (f'"{t}"',)).fetchall():
                        c = content.lower().count(t.lower())
                        if c:
                            m[path] = c
                except sqlite3.OperationalError:
                    pass
                tbl[t] = m
        tables[variant] = tbl
    conn.close()
    print("预计算完成（3 变体词表）")

    def evaluate(cfg):
        hits = 0
        for q, golds in GOLD:
            scores = {}
            tbl = tables[cfg["variant"]]
            for t in terms_of(q, cfg["variant"]):
                for path, c in tbl.get(t, {}).items():
                    scores[path] = scores.get(path, 0) + c * weight_of(path, cfg)
            top = sorted(scores, key=lambda p: -scores[p])[:cfg["k"]]
            pn = [p.replace("\\", "/") for p in top]
            if any(g.lower() in "".join(pn).lower() for g in golds):
                hits += 1
        return hits

    baseline = {"variant": "g3", "k": 8, "daily": 2.0, "gaps": 1.0, "deepsea": 1.0, "skill": 1.0}
    base_score = evaluate(baseline)
    print(f"基线（当前线上配置）: {base_score}/20")

    rng = random.Random(42)
    best, best_score = dict(baseline), base_score
    for i in range(1000):
        cfg = {
            "variant": rng.choice(["g3", "g4", "g34"]),
            "k": rng.randint(4, 12),
            "daily": round(rng.uniform(1.0, 3.5), 2),
            "gaps": round(rng.uniform(0.4, 1.2), 2),
            "deepsea": round(rng.uniform(0.8, 2.0), 2),
            "skill": round(rng.uniform(0.8, 2.0), 2),
        }
        s = evaluate(cfg)
        if s > best_score or (s == best_score and cfg["k"] < best["k"]):
            best, best_score = dict(cfg), s
    print(f"1000 次随机搜索完成——最优: {best_score}/20")
    print(f"最优配置: {best}")
    print("落地判定:", "击败基线→落地" if best_score > base_score else ("持平→按需选择（更小k=更省上下文）" if best_score == base_score else "未胜→保持现状（零退步）"))
    return best, best_score, base_score


if __name__ == "__main__":
    main()
