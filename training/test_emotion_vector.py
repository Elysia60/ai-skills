# -*- coding: utf-8 -*-
"""emotion_vector.py 测试：基线/移位夹取/O-U 衰减/危机置位/仲裁映射。零依赖。"""

import importlib.util
import json
import tempfile
import time
import unittest
from pathlib import Path

spec = importlib.util.spec_from_file_location(
    "emotion_vector", Path(__file__).resolve().parent / "emotion_vector.py")
EV = importlib.util.module_from_spec(spec)
spec.loader.exec_module(EV)


class StateTest(unittest.TestCase):
    def test_clamp(self):
        st = EV.EmotionState({"P": 5.0, "A": -9.0})
        self.assertEqual(st["P"], 1.0)
        self.assertEqual(st["A"], -1.0)

    def test_shift_unknown_dim_ignored(self):
        st = EV.EmotionState({"P": 0.5})
        st.shift({"P": 0.2, "X": 9.0})
        self.assertAlmostEqual(st["P"], 0.7)
        self.assertNotIn("X", st)


class EngineTest(unittest.TestCase):
    def setUp(self):
        self.eng = EV.EmotionEngine()

    def test_baseline_matches_blueprint(self):
        for d, v in EV.BASELINE.items():
            self.assertAlmostEqual(self.eng.state[d], v)

    def test_decay_pulls_to_baseline(self):
        # 人为拉偏 → 惰性衰减多步 → 应向基线回归
        self.eng.apply_event(valence=-1.0, arousal=1.0)
        self.eng.state["P"] = -0.9
        before = abs(self.eng.state["P"] - EV.BASELINE["P"])
        self.eng.decay_if_stale(now=self.eng.updated_at + 3600 * 10)
        after = abs(self.eng.state["P"] - EV.BASELINE["P"])
        self.assertLess(after, before, "衰减后应更接近基线")

    def test_decay_cap_24h(self):
        # 时间跳跃雪崩防护：36h 只折算 24 步
        steps = self.eng.decay_if_stale(now=time.time() + 3600 * 36)
        self.assertLessEqual(steps, 24)

    def test_crisis_lock(self):
        self.eng.set_crisis()
        arb = self.eng.arbitrate()
        self.assertEqual(arb["mode"], "crisis")
        self.assertEqual(self.eng.state["S"], 1.0)  # 危机唯一满格：稳定
        self.eng.clear_crisis()
        self.assertFalse(self.eng.crisis)

    def test_arbitrate_valence_routing(self):
        self.eng.state["P"] = -0.8   # 主人低落 → 情感声部加权
        arb = self.eng.arbitrate()
        self.assertGreater(arb["A"], arb["B"])
        self.assertIn(arb["mode"], ("care", "balanced"))
        self.eng.state["P"] = 0.9    # 主人高兴 → 理性声部加权
        arb = self.eng.arbitrate()
        self.assertGreater(arb["B"], arb["A"])

    def test_persistence_roundtrip(self):
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "state.json"
            eng = EV.EmotionEngine(state_file=fp)
            eng.apply_event(valence=-0.5)
            eng.save()
            eng2 = EV.EmotionEngine(state_file=fp)
            self.assertAlmostEqual(eng2.state["P"], eng.state["P"], places=2)

    def test_corrupt_state_fail_open(self):
        with tempfile.TemporaryDirectory() as td:
            fp = Path(td) / "state.json"
            fp.write_text("{broken", encoding="utf-8")
            eng = EV.EmotionEngine(state_file=fp)  # 不抛异常 → 基线重来
            self.assertAlmostEqual(eng.state["P"], EV.BASELINE["P"])


class CrisisStyleTest(unittest.TestCase):
    """危机锁 → 风格指令清空，mode=crisis（人格卡优先级链第 1 条接管）。"""

    def test_crisis_style_directives_empty(self):
        eng = EV.EmotionEngine()
        eng.set_crisis()
        d = eng.style_directives()
        self.assertEqual(d["mode"], "crisis")
        self.assertEqual(d["A"], "")
        self.assertEqual(d["B"], "")


if __name__ == "__main__":
    unittest.main()
