# -*- coding: utf-8 -*-
"""test_night_consolidate_e2e.py — 夜间巩固全链沙箱预演(2026-11-23)

今晚 21:00 ⑥记忆演化首跑前的去风险:E2E 走 ①读 daily → ②-③抽教训行入队列 →
⑤人格漂移(mock) → ⑥记忆演化(mock 演化引擎,验证接线与告警推送) → 幂等标记落盘。
绝不碰 dsh 真 memories 目录(--daily-dir 沙箱口 + QUEUE/PROACTIVE 全沙箱化)。
"""
import json
import sys
import tempfile
import unittest
from pathlib import Path

TRAIN = r"C:\Users\14676\.zcode\workspace\default\ai-skills\training"
sys.path.insert(0, TRAIN)
import night_consolidate as NC  # noqa: E402
import memory_evolve as ME  # noqa: E402

DAILY_MD = """# daily 2026-11-23
[诊断] 修正了熔断状态机的边界 bug——教训: 只降不升逻辑要靠测试锁住。
[事故] 抓到收集任务静默失败,根因是限流。踩过的坑要记。
无关行不该被抽取。
"""


class E2EBase(unittest.TestCase):
    def setUp(self):
        self._old = (NC.DAILY, NC.QUEUE, NC.ALERT_DIR, NC.persona_drift_check)
        self.td = tempfile.TemporaryDirectory()
        self.daily_dir = Path(self.td.name) / "daily"
        self.daily_dir.mkdir()
        (self.daily_dir / "2026-11-23.md").write_text(DAILY_MD, encoding="utf-8")
        NC.QUEUE = Path(self.td.name) / "queue.md"
        NC.persona_drift_check = lambda: {"drift_rate": 0.04, "failed_probes": [],
                                          "verdict": "OK"}
        self.old_proactive = ME.PROACTIVE
        ME.PROACTIVE = Path(self.td.name) / "proactive"

    def tearDown(self):
        NC.DAILY, NC.QUEUE, NC.ALERT_DIR, NC.persona_drift_check = self._old
        ME.PROACTIVE = self.old_proactive
        self.td.cleanup()


class TestE2E(E2EBase):
    def _run(self, extra=()):
        return NC.main(["night_consolidate.py", "--date", "2026-11-23",
                        "--daily-dir", str(self.daily_dir), *extra])

    def test_full_pipeline_with_contradiction_alert(self):
        """⑥演化报矛盾 → 告警推沙箱主动消息,daily 三行齐全,队列入教训行。"""
        old_evolve = ME.evolve
        ME.evolve = lambda texts, corpus, **kw: {
            "ok": True, "n_new": len(texts), "n_contradictions": 1,
            "n_reinforce": 0, "n_links": 1, "n_new_topics": 0,
            "details": [{"new": texts[0][:40], "verdict": "CONTRADICTION",
                         "sim": 0.91, "related_id": "[S1]", "related": "熔断只降不升",
                         "pair": ("允许回升", "只降不升")}]}
        try:
            rc = self._run()
        finally:
            ME.evolve = old_evolve
        self.assertEqual(rc, 0)
        q = NC.QUEUE.read_text(encoding="utf-8")
        self.assertIn("熔断状态机", q)
        daily = (self.daily_dir / "2026-11-23.md").read_text(encoding="utf-8")
        self.assertIn(NC.MARK, daily)
        self.assertIn("[人格漂移] drift=4%", daily)
        self.assertIn("[记忆演化] 矛盾=1", daily)
        alerts = list(ME.PROACTIVE.glob("2026-11-23-记忆演化.md"))
        self.assertEqual(len(alerts), 1)
        self.assertIn("[S1]", alerts[0].read_text(encoding="utf-8"))

    def test_evolve_crash_fails_open(self):
        """⑥崩 → daily 记跳过行,退出码 0,①-④成果不受影响(fail-open 纪律)。"""
        old_evolve = ME.evolve
        ME.evolve = lambda *a, **kw: (_ for _ in ()).throw(RuntimeError("ollama 挂了"))
        try:
            rc = self._run()
        finally:
            ME.evolve = old_evolve
        self.assertEqual(rc, 0)
        daily = (self.daily_dir / "2026-11-23.md").read_text(encoding="utf-8")
        self.assertIn("[记忆演化] 跳过", daily)
        self.assertNotIn("矛盾=1", daily)

    def test_idempotent_second_run(self):
        """当日已巩固 → 第二次跳过,队列不再追加。"""
        self._run()
        rc2 = self._run()
        self.assertEqual(rc2, 0)
        self.assertEqual(NC.QUEUE.read_text(encoding="utf-8").count("## 2026-11-23"), 1)

    def test_no_lesson_lines_still_green(self):
        """无教训行 → 抽取 0,⑤⑥ 照跑,退出码 0。"""
        (self.daily_dir / "2026-11-23.md").write_text("# 平安无事的一天\n今天没有教训。\n",
                                                      encoding="utf-8")
        rc = self._run()
        self.assertEqual(rc, 0)
        daily = (self.daily_dir / "2026-11-23.md").read_text(encoding="utf-8")
        self.assertIn("巩固队列 +0 行", daily)

    def test_missing_daily_returns_2(self):
        rc = NC.main(["night_consolidate.py", "--date", "1999-01-01",
                      "--daily-dir", str(self.daily_dir)])
        self.assertEqual(rc, 2)


if __name__ == "__main__":
    unittest.main()
