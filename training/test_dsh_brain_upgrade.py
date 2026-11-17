# -*- coding: utf-8 -*-
"""dsh_continuity / dsh_temporal / dsh_reply_contract / dsh_note_protocol 四模块测试。"""

import unittest

from dsh_continuity import detect_reactions, create_receipt, is_repair_signal
from dsh_temporal import TemporalClock
from dsh_reply_contract import check_natural_reply, check_budget, trim_to_budget
from dsh_note_protocol import score_note, score_extraction


class ContinuityTest(unittest.TestCase):
    def test_correction_detected(self):
        r = detect_reactions("你理解错了，不是这个意思")
        self.assertTrue(any(x["type"] == "correction" for x in r))

    def test_boundary_detected(self):
        r = detect_reactions("别再提这件事了")
        self.assertTrue(any(x["type"] == "boundary" for x in r))

    def test_acceptance_detected(self):
        r = detect_reactions("谢谢你听我说，这正是我想要的")
        self.assertTrue(any(x["type"] == "acceptance" for x in r))

    def test_rejected_strategy_detected(self):
        r = detect_reactions("别给我建议了行不行")
        self.assertTrue(any(x["type"] == "rejected_strategy" for x in r))

    def test_no_reaction(self):
        self.assertEqual(detect_reactions("今天天气不错"), [])

    def test_receipt_seven_columns(self):
        r = detect_reactions("你理解错了")
        e = create_receipt("D-20261118-01", r, context="测试分歧", evidence="测试证据")
        for col in ("日期", "分歧(可验证描述)", "谁坚持了", "修复动作",
                    "修复后状态", "证据(可重放)", "交叉引用id"):
            self.assertIn(col, e)

    def test_repair_signal(self):
        self.assertTrue(is_repair_signal("谢谢你听我说，这正是我想要的"))
        self.assertFalse(is_repair_signal("你理解错了"))


class TemporalTest(unittest.TestCase):
    def test_observe_and_stats(self):
        tc = TemporalClock()
        tc.observe("测试观察")
        self.assertEqual(tc.stats()["observations"], 1)

    def test_fact_validity(self):
        import time
        tc = TemporalClock()
        now = time.time()
        tc.assert_fact("测试事实", valid_from=now - 100, valid_until=None)
        known = tc.as_of(now)
        self.assertIn("测试事实", known)

    def test_fact_expiry(self):
        import time
        tc = TemporalClock()
        tc.assert_fact("过期事实", valid_from=1, valid_until=2)  # epoch 早期 = 已过期
        known = tc.as_of(time.time())
        self.assertNotIn("过期事实", known)


class ReplyContractTest(unittest.TestCase):
    def test_natural_reply_pass(self):
        r = check_natural_reply("粥在锅里，凉了自己热。")
        self.assertTrue(r["ok"])

    def test_customer_service_detected(self):
        r = check_natural_reply("希望这些对你有帮助！如果你还有问题可以随时问我。")
        self.assertFalse(r["ok"])
        self.assertTrue(any("客服" in v for v in r["violations"]))

    def test_ai_self_reference_detected(self):
        r = check_natural_reply("作为一个AI，我认为...")
        self.assertFalse(r["ok"])

    def test_list_detected(self):
        r = check_natural_reply("首先你要检查配置，其次要重启服务，最后验证结果。")
        self.assertFalse(r["ok"])

    def test_budget_whole_entry(self):
        entries = ["a" * 100, "b" * 200, "c" * 50]
        r = check_budget(entries, {"context_chars": 300})
        self.assertEqual(r["included"], 2)  # 前 2 条放进（300 字），第 3 条溢出
        self.assertEqual(r["excluded"], 1)

    def test_trim_preserves_order(self):
        entries = ["short", "medium" * 5, "tiny"]
        r = trim_to_budget(entries, {"context_chars": 200})
        self.assertLessEqual(len(r), len(entries))
        self.assertTrue(all(isinstance(x, str) for x in r))


class NoteProtocolTest(unittest.TestCase):
    def test_good_note_passes(self):
        r = score_note(
            "主人今天改了 mem_search.py 的 superseded_at 逻辑，旧版本进 doc_history 不删。",
            ["mem_search", "superseded_at", "doc_history"])
        self.assertTrue(r["ok"])

    def test_note_too_long_rejected(self):
        r = score_note("长" * 700, ["tag"])
        self.assertFalse(r["ok"])

    def test_note_too_many_keywords_rejected(self):
        r = score_note("描述", [f"kw{i}" for i in range(12)])
        self.assertFalse(r["ok"])

    def test_summary_tone_detected(self):
        r = score_note("总的来说今天的修改是成功的", ["tag"])
        self.assertFalse(r["ok"])

    def test_extraction_link_needs_quotes(self):
        r = score_extraction({
            "note_text": "描述", "keywords": ["a"],
            "links": [{"relation": "clarifies", "source_quote": "", "target_quote": ""}]})
        self.assertFalse(r["ok"])
        self.assertTrue(any("缺引用" in v for v in r["violations"]))


if __name__ == "__main__":
    unittest.main()
