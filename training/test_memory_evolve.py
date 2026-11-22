# -*- coding: utf-8 -*-
"""test_memory_evolve.py — 记忆演化层测试(2026-11-23 · 零模型依赖,注入确定性嵌入)"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
import memory_evolve as ME  # noqa: E402


class DictEmbedder:
    """词典型确定性嵌入: 未知文本 → md5 派生的伪向量(跨次运行稳定)。"""

    def __init__(self, table: dict[str, list[float]], dim: int = 8):
        self.table = table
        self.dim = dim

    def __call__(self, text: str) -> list[float]:
        if text in self.table:
            return self.table[text]
        import hashlib
        h = hashlib.md5(text.encode("utf-8")).digest()
        v = [(b % 17) - 8 for b in h[:self.dim]]
        n = sum(x * x for x in v) ** 0.5 or 1.0
        return [x / n for x in v]


class TestCosAndStance(unittest.TestCase):
    def test_cos_orthogonal_zero(self):
        self.assertAlmostEqual(ME._cos([1, 0], [0, 1]), 0.0)

    def test_cos_identical_one(self):
        self.assertAlmostEqual(ME._cos([2, 1], [2, 1]), 1.0)

    def test_stance_oppose(self):
        st, pair = ME.stance("该因子无效", "该因子有效", [("有效", "无效")])
        self.assertEqual(st, "oppose")
        self.assertEqual(pair, ("有效", "无效"))

    def test_stance_same(self):
        st, _ = ME.stance("回测证明有效", "样本外仍有效", [("有效", "无效")])
        self.assertEqual(st, "same")

    def test_stance_none(self):
        st, pair = ME.stance("今天天气不错", "中午吃了饭", [("有效", "无效")])
        self.assertEqual(st, "none")
        self.assertIsNone(pair)

    def test_stance_long_word_shielded(self):
        """'不显著'必须先剥掉再查'显著',否则假 same/oppose。"""
        st, _ = ME.stance("OOS 结果不显著", "训练集内显著", [("显著", "不显著")])
        self.assertEqual(st, "oppose")


class TestClassify(unittest.TestCase):
    def test_contradiction_high_sim_opposed(self):
        d = ME.classify("熔断允许回升", "熔断只降不升", 0.90,
                        pairs=[("只降不升", "允许回升")])
        self.assertEqual(d["verdict"], "CONTRADICTION")

    def test_reinforce_high_sim_same(self):
        d = ME.classify("该因子有效(新样本)", "该因子有效", 0.90,
                        pairs=[("有效", "无效")])
        self.assertEqual(d["verdict"], "REINFORCE")

    def test_link_mid_sim(self):
        d = ME.classify("两融斜率新批次更新", "两融 30 日斜率是前导指标", 0.60)
        self.assertEqual(d["verdict"], "LINK")

    def test_new_low_sim(self):
        d = ME.classify("CS2 赛季热度上升", "熔断阈值只降不升", 0.10)
        self.assertEqual(d["verdict"], "NEW")


CORPUS = [
    {"id": "[S1]", "text": "熔断只降不升,高水位持久化"},
    {"id": "[S2]", "text": "avoid 信号提前 23~30 天前导 regime 转 bear"},
    {"id": "[S3]", "text": "Ridge 选股器负面入册,效果不显著"},
]


class TestEvolve(unittest.TestCase):
    def _embedder(self):
        # 相关组: 同方向高相似向量;无关组: 正交
        hot = [1.0, 0.9, 0.1, 0, 0, 0, 0, 0]
        ridge = [0, 0, 0, 1.0, 0.9, 0.1, 0, 0]
        return DictEmbedder({
            CORPUS[0]["text"]: hot,
            CORPUS[1]["text"]: [0, 0, 0, 0, 0, 0, 1.0, 0.9],
            CORPUS[2]["text"]: ridge,
            "熔断新规: 允许回升": [1.0, 0.95, 0.12, 0, 0, 0, 0, 0],
            "Ridge 换特征集后仍不显著": [0, 0, 0, 1.0, 0.95, 0.12, 0, 0],
            "cs 热度分位更新": [0.1, 0.1, 1.0, 0.1, 0, 0, 0, 0],
        })

    def test_contradiction_detected_and_counted(self):
        rep = ME.evolve(["熔断新规: 允许回升"], CORPUS, embed_fn=self._embedder(),
                        pairs=[("只降不升", "允许回升"), ("显著", "不显著")])
        self.assertTrue(rep["ok"])
        self.assertEqual(rep["n_contradictions"], 1)
        self.assertEqual(rep["details"][0]["related_id"], "[S1]")

    def test_reinforce_no_alert(self):
        rep = ME.evolve(["Ridge 换特征集后仍不显著"], CORPUS, embed_fn=self._embedder(),
                        pairs=[("显著", "不显著")])
        self.assertEqual(rep["n_reinforce"], 1)
        self.assertEqual(rep["n_contradictions"], 0)

    def test_unrelated_is_new_topic(self):
        rep = ME.evolve(["cs 热度分位更新"], CORPUS, embed_fn=self._embedder())
        self.assertEqual(rep["n_new_topics"], 1)

    def test_embed_fail_fail_open(self):
        def broken(text):
            raise ConnectionError("ollama down")
        rep = ME.evolve(["任意"], CORPUS, embed_fn=broken)
        self.assertFalse(rep["ok"])
        self.assertIn("fail-open", rep["detail"])

    def test_alert_pushed_on_contradiction(self):
        with tempfile.TemporaryDirectory() as td:
            old = ME.PROACTIVE
            ME.PROACTIVE = Path(td)
            try:
                rep = ME.evolve(["熔断新规: 允许回升"], CORPUS,
                                embed_fn=self._embedder(),
                                pairs=[("只降不升", "允许回升")])
                out = ME.push_alert("2026-11-23", rep)
                self.assertTrue(out.exists())
                self.assertIn("只降不升", out.read_text(encoding="utf-8"))
                self.assertIn("maker≠checker", out.read_text(encoding="utf-8"))
            finally:
                ME.PROACTIVE = old


class TestCorpusBuilder(unittest.TestCase):
    def test_parse_registry_md(self):
        with tempfile.TemporaryDirectory() as td:
            md = Path(td) / "m.md"
            md.write_text(
                "## 3d. 结论注册表\n"
                "| --- | --- | --- | --- |\n"
                "| [S1] | 熔断只降不升 | 回测 | 已证明 |\n"
                "| [S2]-反方 | 5 次事件不排除巧合 | 观测 | 反方 |\n",
                encoding="utf-8")
            corpus = ME.parse_registry_md(md)
            self.assertEqual(len(corpus), 2)
            self.assertEqual(corpus[0]["id"], "[S1]")
            self.assertIn("熔断", corpus[0]["text"])

    def test_build_corpus_cli(self):
        with tempfile.TemporaryDirectory() as td:
            md = Path(td) / "m.md"
            md.write_text("| [S9] | 两融斜率前导 | 数据 | 已证明 |\n", encoding="utf-8")
            out = Path(td) / "c.json"
            rc = ME.main(["memory_evolve.py", "build-corpus", "--md", str(md),
                          "-o", str(out)])
            self.assertEqual(rc, 0)
            data = json.loads(out.read_text(encoding="utf-8"))
            self.assertEqual(data[0]["id"], "[S9]")


if __name__ == "__main__":
    unittest.main()
