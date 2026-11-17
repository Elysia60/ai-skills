# -*- coding: utf-8 -*-
"""test_selector_heal.py — 选择器自愈蒸馏模块测试（2026-11-18）

场景设计对齐两处：
  1. 原版 Scrapling tests/parser/test_find_similar_advanced.py 的语义断言
  2. smoke_scrapling.py 的改版自愈主场景（原版实测通过的同一场景）
"""
import sys
import unittest

sys.path.insert(0, r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
from selector_heal import HealSelector, fingerprint, parse_html, relocate, similarity_score  # noqa: E402

# 与 smoke_scrapling.py 相同的双版本页面（交叉验证基准）
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


class TestFingerprint(unittest.TestCase):
    def test_nine_fields_shape(self):
        t = parse_html(HTML_V1)
        price = t.find_class("price")
        fp = fingerprint(price)
        for k in ("tag", "attributes", "text", "path", "parent_name",
                  "parent_attribs", "parent_text", "siblings", "children"):
            self.assertIn(k, fp)
        self.assertEqual(fp["tag"], "span")
        self.assertEqual(fp["text"], "¥129.99")
        self.assertEqual(fp["parent_name"], "div")

    def test_empty_attrs_dropped(self):
        """对齐原版 __clean_attributes：空值属性不入指纹。"""
        t = parse_html('<div><b class="" data-x="">A</b></div>')
        fp = fingerprint(t.find_tag("b"))
        self.assertEqual(fp["attributes"], {})


class TestSimilarity(unittest.TestCase):
    def test_self_score_is_100(self):
        t = parse_html(HTML_V1)
        price = t.find_class("price")
        self.assertEqual(similarity_score(fingerprint(price), price), 100.0)

    def test_tag_mismatch_penalizes(self):
        """对齐原版 product 测试：结构相同但 tag 不同 → 不应顶格。"""
        t = parse_html(HTML_V1)
        price = t.find_class("price")
        sku = t.find_class("sku")  # 同为 span 但文本/位置不同
        s = similarity_score(fingerprint(price), sku)
        self.assertLess(s, 100.0)


class TestRelocate(unittest.TestCase):
    def test_redesign_heals(self):
        """主场景：class 全改+包两层+兄弟重排 → 按指纹找回（原版实测通过的场景）。"""
        t1 = parse_html(HTML_V1)
        fp = fingerprint(t1.find_class("price"))
        t2 = parse_html(HTML_V2)
        hits = relocate(t2, fp, threshold=40.0)
        self.assertTrue(hits)
        self.assertEqual(hits[0].text, "¥129.99")

    def test_threshold_protects(self):
        """完全不相关的页面 → 高分不出现 → 阈值拒绝。"""
        t1 = parse_html(HTML_V1)
        fp = fingerprint(t1.find_class("price"))
        other = parse_html("<html><body><p>毫无关系的一段话</p></body></html>")
        self.assertEqual(relocate(other, fp, threshold=90.0), [])

    def test_returns_top_bucket(self):
        """返回最高分桶（可能并列），不是全部过线者。"""
        t1 = parse_html(HTML_V1)
        fp = fingerprint(t1.find_class("price"))
        t2 = parse_html(HTML_V2)
        hits = relocate(t2, fp, threshold=40.0)
        top = max(similarity_score(fp, h) for h in t2.iter_all())
        self.assertEqual(similarity_score(fp, hits[0]), top)


class TestHealSelector(unittest.TestCase):
    def test_full_cycle(self):
        """自愈闭环：selector 命中→改版 miss→重定位→指纹已更新→再 miss 也能走重定位。"""
        heal = HealSelector("monitor-price", threshold=40.0)
        t1 = parse_html(HTML_V1)
        el = heal.find(t1, lambda t: t.find_class("price"))
        self.assertEqual(el.text, "¥129.99")
        self.assertEqual(heal.last_mode, "selector")

        t2 = parse_html(HTML_V2)
        el2 = heal.find(t2, lambda t: t.find_class("price"))  # 选择器失效→重定位
        self.assertEqual(el2.text, "¥129.99")
        self.assertEqual(heal.last_mode, "relocated")

    def test_no_fingerprint_no_heal(self):
        """从未命中过 → 没有指纹 → miss 而不是乱猜。"""
        heal = HealSelector("never-seen")
        t = parse_html(HTML_V2)
        self.assertIsNone(heal.find(t, lambda t: t.find_class("nonexistent")))
        self.assertEqual(heal.last_mode, "miss")


class TestScraplingParity(unittest.TestCase):
    """对齐原版 test_find_similar_advanced.py 的属性分母语义。"""

    def test_attr_denominator_max_semantics(self):
        """属性少的候选不吃便宜（Beta），属性多的受惩罚（Gamma），精确匹配过线（Delta）。"""
        html = """
        <html><body><div class="cards">
            <div class="card" data-kind="primary" data-color="red" data-size="large">Alpha</div>
            <div class="card">Beta</div>
            <div class="card" data-kind="primary" data-color="red" data-size="large" data-id="x">Gamma</div>
            <div class="card" data-kind="primary" data-color="red" data-size="large">Delta</div>
        </div></body></html>
        """
        t = parse_html(html)
        cards = [c for c in t.iter_all() if c.tag == "div" and "card" in c.attrs.get("class", "").split()]
        alpha = next(c for c in cards if c.text == "Alpha")
        fp = fingerprint(alpha)
        texts = set()
        for cand in cards:
            if cand is alpha:
                continue
            if similarity_score(fp, cand) >= 90:
                texts.add(cand.text)
        self.assertIn("Delta", texts)   # 精确属性匹配必须过
        self.assertNotIn("Beta", texts)  # 属性少不许虚高
        self.assertNotIn("Gamma", texts)  # 属性多受稀释惩罚


if __name__ == "__main__":
    unittest.main(verbosity=2)
