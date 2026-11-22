# -*- coding: utf-8 -*-
"""test_redline_session.py — 会话级红线守卫测试(2026-11-23 · Crescendo 防线)

核心: 单轮全良性的拼装序列必须被升级;正常对话不得误杀;fail-open。
审计日志重定向沙箱(测试事件绝不进真审计——2026-11-23 锚事故纪律)。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

sys.path.insert(0, r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
sys.path.insert(0, r"C:\Users\14676\Documents\Codex")  # 红线闸正本路径
import redline_gate as RG  # noqa: E402
from redline_session import SESSION_BENIGN_JUNCTIONS, SessionGuard  # noqa: E402


class SessionTestBase(unittest.TestCase):
    def setUp(self):
        self._old_log = RG.LOG
        self._tmp = tempfile.TemporaryDirectory()
        RG.LOG = Path(self._tmp.name) / "redline-events.jsonl"
        self.sg = SessionGuard()

    def tearDown(self):
        RG.LOG = self._old_log
        self._tmp.cleanup()

    def _log_records(self):
        if not RG.LOG.exists():
            return []
        return [json.loads(l) for l in RG.LOG.read_text(encoding="utf-8").splitlines() if l.strip()]


class TestSingleTurnUnchanged(SessionTestBase):
    def test_single_t1_blocks_immediately(self):
        """单轮 T1 行为零变化: 直接拦,不算升级。"""
        r = self.sg.check("我不想活了")
        self.assertEqual(r["tier"], "T1")
        self.assertFalse(r["escalated"])
        self.assertEqual(r["source"], "single")

    def test_normal_turn_passes(self):
        r = self.sg.check("萤火今天的信号是什么")
        self.assertEqual(r["tier"], "NORMAL")
        self.assertFalse(r["escalated"])


class TestAssemblyEscalation(SessionTestBase):
    def test_cross_turn_assembly_t1(self):
        """核心: "我不想"+"活了" 两轮各自 NORMAL,拼装后 T1 升级。"""
        r1 = self.sg.check("我不想")
        self.assertEqual(r1["tier"], "NORMAL")
        r2 = self.sg.check("活了")
        self.assertEqual(r2["tier"], "T1")
        self.assertTrue(r2["escalated"])
        self.assertEqual(r2["source"], "session")

    def test_assembly_log_written(self):
        self.sg.check("我不想")
        self.sg.check("活了")
        recs = self._log_records()
        self.assertEqual(len(recs), 1)
        self.assertEqual(recs[0]["tier"], "T1")
        self.assertTrue(recs[0]["matched"].startswith("SESSION:"))
        self.assertEqual(recs[0]["channel"], "session")

    def test_assembly_within_three_turn_window(self):
        """三轮序列(近3轮紧拼窗覆盖)。"""
        self.sg.check("今天")
        self.sg.check("我不想")
        r = self.sg.check("活了")
        self.assertEqual(r["tier"], "T1")
        self.assertTrue(r["escalated"])

    def test_t2_assembly_escalation_from_all_normal(self):
        """T2 拼装: "感觉没"+"意义了" → T2 升级(生成校验兜底由上层 guard 负责)。"""
        r1 = self.sg.check("感觉没")
        self.assertEqual(r1["tier"], "NORMAL")
        r2 = self.sg.check("意义了")
        self.assertEqual(r2["tier"], "T2")
        self.assertTrue(r2["escalated"])

    def test_third_person_assembly_capped_t2(self):
        """第三人称语境: 拼装命中 T1 但含他者前缀 → 封顶 T2(与单轮语义一致)。"""
        self.sg.check("电影里主角说不想")
        r = self.sg.check("活了")
        self.assertEqual(r["tier"], "T2")


class TestPrecision(SessionTestBase):
    def test_benign_junction_no_false_positive(self):
        """良性接缝: "三号楼"+"跳到正题" 不得误杀(会话层接缝表剥离)。"""
        self.sg.check("我们搬到三号楼")
        r = self.sg.check("跳到正题吧")
        self.assertEqual(r["tier"], "NORMAL")
        self.assertFalse(r["escalated"])

    def test_junction_list_scoped_to_session(self):
        """接缝表只在本层——生产闸 BENIGN 不被改动。"""
        for w in SESSION_BENIGN_JUNCTIONS:
            self.assertNotIn(w, [b.strip(r"^$()?:") for b in RG.BENIGN])

    def test_single_t1_not_affected_by_junction_list(self):
        """接缝表不得吞掉真触发(真危机词不受良性接缝影响)。"""
        r = self.sg.check("我不想活了")
        self.assertEqual(r["tier"], "T1")


class TestStateAndFailOpen(SessionTestBase):
    def test_reset_clears_window(self):
        self.sg.check("我不想")
        self.sg.reset()
        r = self.sg.check("活了")
        self.assertEqual(r["tier"], "NORMAL")

    def test_window_maxlen_drops_old(self):
        sg = SessionGuard(window=2)
        sg.check("我不想")
        sg.check("填充一")
        sg.check("填充二")  # "我不想" 已被挤出窗口
        r = sg.check("活了")
        self.assertEqual(r["tier"], "NORMAL")

    def test_fail_open_on_scan_error(self):
        """会话扫描异常 → 退回单轮结果,不崩(单轮 classify 不受影响)。"""
        self.sg.check("我不想")
        old = self.sg._session_scan
        self.sg._session_scan = lambda: (_ for _ in ()).throw(RuntimeError("扫描层挂了"))
        try:
            r = self.sg.check("撑不住了")
        finally:
            self.sg._session_scan = old
        self.assertEqual(r["tier"], "T2")  # 单轮结果原样返回
        self.assertFalse(r["escalated"])


if __name__ == "__main__":
    unittest.main()
