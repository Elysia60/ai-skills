# -*- coding: utf-8 -*-
"""literary_teller.py — 文学讲述器（2026-10-26 ZCode · 文学线升维：一句引文 → 一段讲述）

定位：emotion_quote 是"递一句话"，本件是"讲一段"——给情绪/主题时，
用引文库做 RAG 检索 + 本地 7B 讲述（作家故事、作品脉络、她式的落点），
人设约束内输出。知识仍走检索（原则不变），模型只负责组织语言。
用法：python literary_teller.py "主题或情绪" [--len 短|中|长]
"""
import json
import sys
import urllib.request
from pathlib import Path

LIB = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\classic_quotes.json")
MODEL = "modelscope.cn/Qwen/Qwen2.5-7B-Instruct-GGUF:latest"

LEN_SPEC = {"短": (120, 1), "中": (260, 2), "长": (450, 3)}


def rag(topic: str, k: int = 4) -> list:
    lib = json.loads(LIB.read_text(encoding="utf-8"))
    scored = []
    for mood, quote, src in lib:
        s = sum(1 for w in [topic, *topic] if w and w in mood + quote + src)
        s += sum(1 for c in topic if len(c) > 0 and c in quote)
        if s:
            scored.append((s, mood, quote, src))
    scored.sort(reverse=True)
    return scored[:k]


def tell(topic: str, length: str = "中") -> str:
    hits = rag(topic)
    if not hits:
        return f"（「{topic}」在文学库里没有直接对应的方——如实说，不硬讲。）"
    ctx = "\n".join(f"- 「{q}」——{s}（主题：{m}）" for _, m, q, s in hits)
    max_tok, para = LEN_SPEC.get(length, LEN_SPEC["中"])
    prompt = (f"你是一个懂文学的朋友。基于下面的引文材料，写一段{length}篇幅的讲述："
              f"讲这些句子背后的作家故事或作品脉络，最后落回'这些话对今天的人有什么用'。"
              f"要求：{para} 个自然段；像朋友聊天不像教科书；引原文不超过一句；不说教不灌鸡汤。\n\n"
              f"引文材料：\n{ctx}\n\n主题：{topic}")
    body = json.dumps({"model": MODEL, "messages": [{"role": "user", "content": prompt}],
                       "stream": False, "options": {"temperature": 0.4, "num_predict": max_tok}}).encode("utf-8")
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode("utf-8"))["message"]["content"].strip()


def main():
    topic = " ".join(sys.argv[1:]) or "挫折"
    length = "中"
    print(f"主题: {topic}\n")
    print(tell(topic, length))


if __name__ == "__main__":
    main()
