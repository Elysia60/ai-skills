# -*- coding: utf-8 -*-
"""dsh_answer.py — 检索增强 + 生成后校验答题器（2026-10-25 ZCode）

背景（DSH 侧复验）：qwen-dsh-v1 裸答 = 格式对齐但内容错（编号错位/训练集内幻觉）。
根因：知识靠权重"背"，小数据背不住。
组合拳：
  ① 检索注入 v2（评估轮升级）：mem-search FTS 全库（daily/gaps/深海/研究层），
     不再只扫 53 条手法——N13 闸门 4/5 诚实拒绝的根因是检索面太窄
  ② 模型生成：qwen-dsh-v1（风格已对齐）只负责组织语言
  ③ 生成后校验：输出中的编号回查台账核对，不符即标 [编号存疑]
用法：python dsh_answer.py "问题"
"""
import io
import json
import re
import sys
import urllib.request
from pathlib import Path

SKILL = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\pending-skills\ledger-lessons\SKILL.md")
DB = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\.search-index.db")
MODEL = "modelscope.cn/Qwen/Qwen2.5-7B-Instruct-GGUF:latest"


def load_methods() -> list:
    """解析 SKILL.md 手法：[(编号, 全文)]"""
    text = SKILL.read_text(encoding="utf-8").split("## 出师自测")[0]
    out = []
    for m in re.finditer(r"^(\d+)\. \*\*(.+?)\*\*[：:]?(.*)$", text, re.M):
        out.append((m.group(1), f"{m.group(2)}。{m.group(3)}".strip()))
    return out


def retrieve(query: str, k: int = 8) -> list:
    """检索 v2.1（评估轮修正）：中文连续串滑窗切块是垃圾块（"会话日志损坏是/怎么修好的"
    永不命中）——改为 ASCII 词整取 + 中文 2 字滑窗，命中数按唯一词计。"""
    import sqlite3
    conn = sqlite3.connect(str(DB))
    terms = set()
    for run in re.findall(r"[A-Za-z0-9_.-]+|[\u4e00-\u9fff]+", query):
        if re.match(r"^[A-Za-z0-9_.-]+$", run):
            if len(run) >= 2:
                terms.add(run)
        else:  # 中文串 → 3 字滑窗（trigram 索引最短 3 字，2 字永不命中——首跑教训）
            terms.update(run[i:i + 3] for i in range(len(run) - 2))
    hits = {}
    for t in terms:
        try:
            rows = conn.execute("SELECT path, content FROM docs WHERE docs MATCH ?", (f'"{t}"',)).fetchall()
        except sqlite3.OperationalError:
            continue
        for path, content in rows:
            pos = content.lower().find(t.lower())
            if pos < 0:
                continue
            excerpt = content[max(0, pos - 60):pos + 150].replace("\n", " ").strip()
            if path not in hits:
                hits[path] = [0, ""]
            hits[path][0] += 1
            if len(hits[path][1]) < 200:
                hits[path][1] = (hits[path][1] + " … " + excerpt)[:420]
    conn.close()
    # 来源类型加权（2026-10-25 治元内容污染）：gaps.json 的 evidence 会原文转述"错误答案"
    # （如 N13 描述 ICU 混淆），词频压过 daily 里的正解记录——模型忠实复述批评文而非正解。
    # 权重：daily/深海正本（事实记录）0 + 1.0 奖励；gaps.json 降权 0.5；其余 1.0。
    def src_weight(path: str) -> float:
        # 末轮修正：gaps.json 同时住着元批评（N13 evidence）与正解（T8 title），
        # 文件级降权误伤正解——恢复 1.0，污染交给提示词抗复述指令处理。
        p = path.replace("\\", "/").lower()
        if "/daily/" in p or "时间线" in p or "日记" in p:
            return 2.0
        return 1.0
    scored = sorted(hits.items(), key=lambda kv: (-kv[1][0] * src_weight(kv[0])))[:k]
    return [(score, path.replace("\\", "/").split("/")[-1], excerpt) for path, (score, excerpt) in scored]


def generate(prompt: str) -> str:
    body = json.dumps({
        "model": MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "stream": False, "options": {"temperature": 0.2, "num_predict": 220},
    }).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode("utf-8"))["message"]["content"].strip()


def verify_refs(answer: str) -> str:
    """生成后校验 v2（DSH 侧口试题二行动项）：编号存在性 + 编号-内容匹配——
    "编号存在 ≠ 编号正确"。撒谎的是没拦住它的那道闸。"""
    methods_list = load_methods()
    methods = {num: full for num, full in methods_list}

    def check(m):
        num = m.group(1)
        if num not in methods:
            return m.group(0) + "[编号不存在]"
        context = answer[max(0, m.start() - 20):m.start()]
        # 全子串集合（贪婪滑窗会跨词边界）——2~4 字全部子串
        ctx_terms = {context[i:i + L]
                     for L in (2, 3, 4)
                     for i in range(max(0, len(context) - L + 1))
                     if re.match(r"^[\u4e00-\u9fff\w]+$", context[i:i + L])}
        if not ctx_terms:
            return m.group(0)
        if any(t in methods[num] for t in ctx_terms):
            return m.group(0)
        best_m, best_score = None, 0
        for mn, full in methods_list:
            s = sum(1 for t in ctx_terms if t in full)
            if s > best_score:
                best_m, best_score = mn, s
        if best_m and best_m != num and best_score >= 2:
            return m.group(0) + f"[编号存疑:应为#{best_m}]"
        return m.group(0) + "[编号存疑:语境不匹配]"

    return re.sub(r"[#＃](\d{1,2})", check, answer)


def answer(question: str) -> str:
    hits = retrieve(question, k=8)
    if not hits:
        return "（检索无相关内容——此题不在知识库覆盖内，不硬答。）"
    ctx = "\n".join(f"[来源:{name}] {excerpt[:300]}" for _, name, excerpt in hits)
    prompt = (f"你是知识助手。只依据下面给定的检索片段回答；片段里有的才说，没有的不编。"
              f"引用时注明来源文件名。简洁回答（3 句内）。\n\n检索片段：\n{ctx}\n\n问题：{question}")
    raw = generate(prompt)
    return verify_refs(raw)


def main() -> int:
    q = " ".join(sys.argv[1:]) or "数字不许硬编码的正确做法是什么？"
    print(f"Q: {q}")
    print(f"A: {answer(q)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
