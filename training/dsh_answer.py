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
    """生成后校验：answer 里的 (#N) 回查台账——N 对应手法开头是否含 answer 的关键词。
    不符标 [编号存疑:应为#M]。"""
    methods = {num: full for num, full in load_methods()}

    def check(m):
        num = m.group(1)
        if num not in methods:
            return m.group(0) + "[编号不存在]"
        return m.group(0)

    answer = re.sub(r"[#＃](\d{1,2})", check, answer)
    return answer


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
