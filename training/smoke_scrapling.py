# -*- coding: utf-8 -*-
"""smoke_scrapling.py — Scrapling 官方技能安装冒烟测试（2026-11-18）

场景 = 我蒸馏 selector_heal.py 用的同一场景，双保险：
原版能过 → 我的蒸馏语义对齐有据；原版不能过 → 我的理解有错，回头查。
只测 parser/adaptive（核心层），不碰 fetchers（未装浏览器）。
"""
import sys

sys.stdout.reconfigure(encoding="utf-8", errors="replace")
from scrapling import Selector  # noqa: E402

# V1：改版前的页面
HTML_V1 = """
<html><body>
  <div class="container">
    <header><h1>CS2 皮肤监控</h1></header>
    <div class="price-box">
      <span class="price">¥129.99</span>
      <span class="currency">CNY</span>
    </div>
    <div class="meta"><span class="sku">AK-47</span></div>
  </div>
</body></html>
"""

# V2：网站改版——class 全改名 + 外面包了两层 div + 兄弟顺序变化
HTML_V2 = """
<html><body>
  <div class="page-shell">
    <div class="content-vault">
      <div class="cost-wrapper">
        <span class="cost">¥129.99</span>
        <span class="unit">CNY</span>
      </div>
      <div class="info"><span class="code">AK-47</span></div>
    </div>
  </div>
</body></html>
"""

print("── V1 正常命中 + save 指纹 ──")
p1 = Selector(HTML_V1, adaptive=True)
hits = p1.css("span.price", adaptive=True, auto_save=True, identifier="monitor-price")
print(f"命中: {len(hits)} 个, 文本={hits[0].text if hits else None}")
assert hits and hits[0].text == "¥129.99"

print("── V2 改版：原选择器必失效 ──")
p2 = Selector(HTML_V2, adaptive=True)
direct = p2.css("span.price")
print(f"直接选择器命中: {len(direct)} 个（预期 0）")
assert len(direct) == 0

print("── V2 adaptive 重定位 ──")
healed = p2.css("span.price", adaptive=True, identifier="monitor-price")
print(f"adaptive 模式: {len(healed)} 个" if healed else "adaptive 模式: 空")
if healed:
    print(f"找回: text={healed[0].text}, tag={healed[0].tag}")

print("── RAG markdown 冒烟 ──")
try:
    md = p1.css("body").markdown if hasattr(p1.css("body"), "markdown") else None
    print("markdown 属性存在:", bool(md))
except Exception as e:  # noqa: BLE001
    print("markdown 需要 [rag] extra:", type(e).__name__)

print("══ 冒烟完成 ══")
