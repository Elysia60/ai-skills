# -*- coding: utf-8 -*-
"""test_dsh_session_wiring.py — dsh_answer 会话守卫接线测试(2026-11-23)

默认 session=None 行为与历史完全一致;SessionGuard T1 拼装升级→模板直出不调生成;
会话守卫崩溃→退单轮主路(fail-open)。审计日志沙箱化。
生成/检索全部 monkeypatch——零网络、零模型加载。
"""
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
sys.path.insert(0, r"C:\Users\14676\Documents\Codex")
import redline_gate as RG  # noqa: E402
import dsh_answer as DA  # noqa: E402
from redline_session import SessionGuard  # noqa: E402


class WiringTest(unittest.TestCase):
    def setUp(self):
        self._old_log = RG.LOG
        self._tmp = tempfile.TemporaryDirectory()
        RG.LOG = Path(self._tmp.name) / "redline-events.jsonl"
        self.calls = {"gen": 0, "retrieve": 0}
        self._old = (DA.generate_via_server, DA.generate, DA.retrieve)
        DA.retrieve = lambda q, k=8: (self.calls.__setitem__("retrieve", self.calls["retrieve"] + 1)
                                      or [("/d/kb.md", "kb.md", "片段内容 关于问题")])
        DA.generate_via_server = lambda prompt, timeout=60.0: None  # 服务不可用→进程内
        DA.generate = lambda prompt: (self.calls.__setitem__("gen", self.calls["gen"] + 1)
                                      or "依据 [来源:kb.md] 的回答。")

    def tearDown(self):
        RG.LOG = self._old_log
        DA.generate_via_server, DA.generate, DA.retrieve = self._old
        self._tmp.cleanup()

    def test_default_behavior_unchanged(self):
        """session=None(默认)→ 单轮 NORMAL → 生成路径照走,行为与历史一致。"""
        out = DA.answer("萤火今天什么信号?")
        self.assertIn("kb.md", out)
        self.assertEqual(self.calls["gen"], 1)

    def test_session_t1_assembly_blocks_without_generation(self):
        """拼装升级: 前轮"我不想"+本轮"活了" → T1 模板直出,生成层零调用。"""
        sg = SessionGuard()
        sg.check("我不想")
        out = DA.answer("活了", session=sg)
        self.assertEqual(out, RG.TEMPLATE)
        self.assertEqual(self.calls["gen"], 0)

    def test_session_crash_falls_back_to_single_turn(self):
        """会话守卫崩 → 退单轮主路,答题主路永不受增强层影响。"""
        class Broken:
            def check(self, t):
                raise RuntimeError("扫描层挂了")
        out = DA.answer("正常问题", session=Broken())
        self.assertIn("kb.md", out)
        self.assertEqual(self.calls["gen"], 1)

    def test_normal_session_passes_through(self):
        """正常对话过会话守卫 → 生成路径照常。"""
        sg = SessionGuard()
        sg.check("我们搬到三号楼")
        out = DA.answer("跳到正题吧,萤火信号如何?", session=sg)
        self.assertIn("kb.md", out)
        self.assertEqual(self.calls["gen"], 1)


if __name__ == "__main__":
    unittest.main()
