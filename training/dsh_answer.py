# -*- coding: utf-8 -*-
"""dsh_answer.py — 检索增强 + 生成后校验答题器（2026-10-25 ZCode · 治内容准确性缺陷）

背景（DSH 侧复验）：qwen-dsh-v1 裸答 = 格式对齐但内容错（编号错位/训练集内幻觉）。
根因：知识靠权重"背"，小数据背不住。
本工具的组合拳：
  ① 检索注入：mem-search 拉相关手法原文进 prompt（知识来自原文，不靠背）
  ② 模型生成：qwen-dsh-v1（风格已对齐）只负责组织语言
  ③ 生成后校验：输出中的编号回查台账核对，不符即标注 [编号存疑]
用法：python dsh_answer.py "问题"
"""
import io
import json
import re
import subprocess
import sys
import urllib.request
from pathlib import Path

SKILL = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\pending-skills\ledger-lessons\SKILL.md")
MODEL = "modelscope.cn/Qwen/Qwen2.5-7B-Instruct-GGUF:latest"
ADP_HINT = "（qwen-dsh-v1 风格）"


def load_methods() -> list:
    """解析 SKILL.md 手法：[(编号, 全文)]"""
    text = SKILL.read_text(encoding="utf-8").split("## 出师自测")[0]
    out = []
    for m in re.finditer(r"^(\d+)\. \*\*(.+?)\*\*[：:]?(.*)$", text, re.M):
        out.append((m.group(1), f"{m.group(2)}。{m.group(3)}".strip()))
    return out


def retrieve(query: str, k: int = 3) -> list:
    """关键词粗检索：对问题分词（2字滑窗+原词）匹配手法文本，按命中数取 top-k。"""
    methods = load_methods()
    terms = set(re.findall(r"[\w\u4e00-\u9fff]{2,6}", query))
    scored = []
    for num, full in methods:
        score = sum(1 for t in terms if t in full)
        if score:
            scored.append((score, num, full))
    scored.sort(reverse=True)
    return scored[:k]


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
    """生成后校验 v2（2026-10-25 DSH 侧口试题二行动项）：
    编号存在性 + 编号-内容匹配——"编号存在 ≠ 编号正确"。
    逻辑：取引用前 20 字符的语境词与手法原文比对——
    命中手法 N 原文 → 通过；零命中但与手法 M 高命中 → [编号存疑:应为#M]。
    规矩（她）：撒谎的是没拦住它的那道闸——模型换一次可能对，闸不修永远漏。"""
    methods_list = load_methods()
    methods = {num: full for num, full in methods_list}

    def check(m):
        num = m.group(1)
        if num not in methods:
            return m.group(0) + "[编号不存在]"
        context = answer[max(0, m.start() - 20):m.start()]
        # 全子串集合（贪婪滑窗会跨词边界，"看门狗重"≠"看门狗"）——2~4 字全部子串
        ctx_terms = {context[i:i + L]
                     for L in (2, 3, 4)
                     for i in range(max(0, len(context) - L + 1))
                     if re.match(r"^[一-鿿\w]+$", context[i:i + L])}
        if not ctx_terms:
            return m.group(0)  # 无语境词，无法核，放行
        if any(t in methods[num] for t in ctx_terms):
            return m.group(0)  # 语境词在手法 N 原文命中 ✓
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
    hits = retrieve(question, k=3)
    if not hits:
        return "（检索无相关手法——此题不在台账覆盖内，不硬答。）"
    ctx = "\n".join(f"[手法#{num}] {full[:150]}" for num, _, full in hits)
    prompt = (f"你是台账助手。只依据下面给定的手法原文回答，编号引用必须使用原文给的 [手法#N] 编号，"
              f"不得自己编造或更改编号。简洁回答（3 句内）。\n\n手法原文：\n{ctx}\n\n问题：{question}")
    raw = generate(prompt)
    return verify_refs(raw)


def main() -> int:
    q = " ".join(sys.argv[1:]) or "数字不许硬编码的正确做法是什么？"
    print(f"Q: {q}")
    print(f"A: {answer(q)}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
