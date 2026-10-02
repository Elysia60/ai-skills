#!/usr/bin/env python3
"""fetch_source — 理性研究规程的取证工具
抓取网页 → 纯文本(去脚本/样式/广告) → 带行号输出(便于"第 N 行"级引用)
用法: python fetch_source.py <URL> [--max-chars 8000]
输出直接进研究报告;末行附 URL 与抓取时间。
"""
import re
import sys
import urllib.request
from datetime import datetime
from html import unescape


def fetch(url, max_chars=8000):
    req = urllib.request.Request(url, headers={
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    })
    with urllib.request.urlopen(req, timeout=30) as r:
        raw = r.read().decode("utf-8", errors="replace")
    # 去脚本/样式/注释
    raw = re.sub(r"(?is)<(script|style|noscript|svg|iframe)[^>]*>.*?</\1>", " ", raw)
    raw = re.sub(r"(?is)<!--.*?-->", " ", raw)
    # 块级标签转换行,保留结构
    raw = re.sub(r"(?i)</(p|div|h[1-6]|li|tr|section|article|blockquote)>", "\n", raw)
    raw = re.sub(r"(?i)<(br|hr)\s*/?>", "\n", raw)
    text = unescape(re.sub(r"<[^>]+>", " ", raw))
    text = re.sub(r"[ \t\u3000]+", " ", text)
    lines = [l.strip() for l in text.split("\n")]
    lines = [l for l in lines if l and len(l) > 1]
    # 去导航/广告噪音行(经验规则: 太短的重复菜单行)
    out, prev = [], None
    for l in lines:
        if l == prev:
            continue
        out.append(l)
        prev = l
    body = "\n".join(out)[:max_chars]
    stamp = datetime.now().strftime("%Y-%m-%d %H:%M")
    return f"来源: {url}\n抓取: {stamp}\n{'─' * 30}\n{body}"


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print(__doc__)
        sys.exit(2)
    url = sys.argv[1]
    mc = 8000
    if "--max-chars" in sys.argv:
        mc = int(sys.argv[sys.argv.index("--max-chars") + 1])
    try:
        print(fetch(url, mc))
    except Exception as e:
        print(f"抓取失败: {e}\n提示: 换来源或用浏览器手动取证(理性研究规程第三步)")
        sys.exit(1)
