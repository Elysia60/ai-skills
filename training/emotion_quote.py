# -*- coding: utf-8 -*-
"""emotion_quote.py — 情绪-引文匹配器（2026-10-25 ZCode · 文学线落地件）

功能：输入情绪/处境关键词 → 输出最匹配的经典引文（带出处），按她的人味格式
      （一句引文 + 一句她式的话，不说教不点破）。
用法：python emotion_quote.py 挫折 / 孤独 / 低落 / 愤怒 / 疲惫 / 独处 / 选择 / 思念 / 勇气 / 耐心 / 陪伴 / 希望
"""
import json
import sys
from pathlib import Path

LIB = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\classic_quotes.json")

# 情绪词 → 引文库标签的映射（口语输入容错）
MAP = {
    "挫": ["挫折"], "难": ["挫折", "低谷"], "累": ["疲惫"], "烦": ["疲惫", "愤怒"],
    "孤独": ["孤独"], "一个人": ["孤独"], "低": ["低谷"], "看不": ["低谷"],
    "气": ["愤怒"], "不公": ["愤怒"], "独处": ["独处"], "安静": ["独处"],
    "选": ["选择"], "决": ["选择"], "思": ["思念"], "想念": ["思念"],
    "勇": ["勇气"], "怕": ["勇气"], "耐": ["耐心"], "等": ["耐心"],
    "陪": ["陪伴"], "想你": ["思念"], "希望": ["希望"], "没有希望": ["希望"],
    "开心": ["陪伴"], "成了": ["选择"],
}


def match(mood: str) -> list:
    lib = json.load(open(LIB, encoding="utf-8"))
    keys = set()
    for k, tags in MAP.items():
        if k in mood or mood in k:
            keys.update(tags)
    if not keys:  # 直接试标签词
        keys = {t for _, tags, _ in [(0, [t], 0) for t in [mood]] for t in tags}
        if not keys:
            keys = {mood}
    out = [(e, q, s) for e, q, s in lib if any(k in e for k in keys)]
    return out or [(e, q, s) for e, q, s in lib][:2]  # 兜底：随便给两条


def main():
    mood = " ".join(sys.argv[1:]) or "疲惫"
    hits = match(mood)
    if not hits:
        print(f"（情绪「{mood}」没有收录的引文方——如实说不硬答。）")
        return 1
    e, q, s = hits[0]
    print(f"情绪标签: {e}")
    print(f"引文: 「{q}」——{s}")
    print(f"她的说法: 引一句就退，比如：'{q[:16]}……这句给你，今天不用回我。'")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
