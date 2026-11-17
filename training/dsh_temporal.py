# -*- coding: utf-8 -*-
"""dsh_temporal.py — 三层时钟（2026-11-18 · 逆向自 anima-brain temporal.py）

三层分离（anima-brain temporal.py 注释逐字）：
  "Occurrence dates, observation dates and state validity are separate clocks."

对 dsh 的映射：
  发生日期 = 事件实际发生（dateparse.py 已管）
  观察日期 = AI 学习到它（本模块管）
  状态有效期 = 事实为真的时间窗（本模块管）

用法：
  from dsh_temporal import TemporalClock
  tc = TemporalClock()
  tc.observe("主人说要去体检", observed_at=now)     # AI 学习到
  tc.assert_valid("主人在体检", valid_until="2026-12-01")  # 事实有效期
  tc.as_of("2026-11-15")                             # 查那天已知什么
"""
from __future__ import annotations

from datetime import datetime, timezone
from zoneinfo import ZoneInfo

DEFAULT_TZ = ZoneInfo("Asia/Shanghai")


class TemporalClock:
    """三层时钟：发生/观察/有效期分离。零依赖零线程。"""

    def __init__(self, timezone_name: str = "Asia/Shanghai"):
        self.tz = ZoneInfo(timezone_name)
        self._observations: list[dict] = []   # [{text, observed_at}]
        self._facts: list[dict] = []          # [{text, valid_from, valid_until, superseded_at}]

    def observe(self, text: str, observed_at: float | None = None) -> None:
        """记录一个观察（AI 在此刻学到了这件事）。"""
        ts = observed_at if observed_at is not None else datetime.now(self.tz).timestamp()
        self._observations.append({"text": text, "observed_at": ts})

    def assert_fact(self, text: str, valid_from: float, valid_until: float | None = None) -> None:
        """登记一个时间事实（有效期可设 None = 无限）。"""
        self._facts.append({"text": text, "valid_from": valid_from, "valid_until": valid_until})

    def as_of(self, query_time: float) -> list[str]:
        """查 query_time 时刻已知的观察 + 仍有效的事实。"""
        known = [o["text"] for o in self._observations if o["observed_at"] <= query_time]
        valid = []
        now_dt = datetime.fromtimestamp(query_time, self.tz)
        for f in self._facts:
            vf = datetime.fromtimestamp(f["valid_from"], self.tz)
            vu = datetime.fromtimestamp(f["valid_until"], self.tz) if f["valid_until"] else None
            if vf <= now_dt and (vu is None or vu >= now_dt):
                valid.append(f["text"])
        return known + valid

    def stats(self) -> dict:
        return {"observations": len(self._observations), "facts": len(self._facts)}
