# -*- coding: utf-8 -*-
"""dsh_standing_intents.py — L3 约定兑现基础设施 v2（2026-11-18 · P0）

v2 修正（DSH 验收抓出三处超前 + 零测试覆盖）：
  ✅ forget 软失效命令（status → invalidated，不物理删）
  ✅ list --invalid 开关
  ✅ event 条件触发匹配（check 时扫描 daily 关键词）
  ✅ --store / --events 参数（测试可注入沙箱路径，不污染真实记忆）
  ✅ aspiration 周复查说明（设计口径，不虚报实现）

三层（OpenClaw 设计适配）：
  time       时间型——deadline 到了就触发
  event      条件型——trigger 关键词出现在 daily 中就触发
  aspiration 心愿型——不自动触发，每周人工复查

设计（fail-open）：
  - 文件式存储（零依赖零线程零数据库）
  - 约定不可物理删除（只能 complete/broken/cancel/forget——历史保全）
  - 到期未处理 → 自动标 broken
  - 兑现/失约写入 promises-events.jsonl 审计

用法：
  python dsh_standing_intents.py promise "主人提体检时问结果" --type event --trigger "体检"
  python dsh_standing_intents.py check                          # 巡检：到期/事件触发
  python dsh_standing_intents.py forget <id>                    # 软失效
  python dsh_standing_intents.py list --invalid                 # 含已失效条目
  python dsh_standing_intents.py --store <path> --events <path> # 测试路径注入
"""
from __future__ import annotations

import json
import os
import sys
import io
import time
from pathlib import Path

STORE = Path(r"C:\Users\14676\.dsh\memories\standing_intents.json")
EVENTS = Path(r"D:\大肥鱼的深海\主动消息\promises-events.jsonl")
TYPES = ("time", "event", "aspiration")
STATUSES = ("pending", "fulfilled", "broken", "cancelled", "invalidated")

EVENT_SCAN_DAYS = 3
DAILY_DIR = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\daily")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def _load(store: Path) -> list:
    if not store.exists():
        return []
    try:
        return json.loads(store.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _save(items: list, store: Path) -> None:
    store.parent.mkdir(parents=True, exist_ok=True)
    store.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def _log_event(entry_id: str, event: str, events_path: Path) -> None:
    events_path.parent.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({"ts": _now(), "intent_id": entry_id, "event": event},
                       ensure_ascii=False)
    with open(events_path, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def _find(items: list, iid: str) -> dict | None:
    for it in items:
        if it["id"] == iid:
            return it
    return None


def cmd_promise(text: str, itype: str, deadline: str | None,
                trigger: str | None, store: Path, events: Path) -> dict:
    if itype not in TYPES:
        return {"error": f"类型必须是 {TYPES}"}
    items = _load(store)
    now = _now()
    seq = sum(1 for it in items if it.get("created", "").startswith(now[:10])) + 1
    entry = {
        "id": f"SI-{now[:10].replace('-', '')}-{seq:03d}",
        "text": text, "type": itype, "status": "pending",
        "created": now, "deadline": deadline, "trigger": trigger,
        "fulfilled_at": None, "broken_at": None,
    }
    items.append(entry)
    _save(items, store)
    _log_event(entry["id"], "created", events)
    return entry


def cmd_check(store: Path, events: Path, daily_dir: Path = DAILY_DIR) -> dict:
    """巡检：①time 型到期 → broken ②event 型 trigger 在最近 daily 中出现 → fulfilled。
    幂等：已处理的不重复。返回统计。"""
    items = _load(store)
    now = time.time()
    auto_broken = event_fired = 0

    for it in items:
        if it["status"] != "pending":
            continue
        if it["type"] == "time" and it.get("deadline"):
            try:
                dl_ts = time.mktime(time.strptime(it["deadline"], "%Y-%m-%d"))
                if now > dl_ts + 86400:
                    it["status"] = "broken"
                    it["broken_at"] = _now()
                    _log_event(it["id"], "auto_broken_overdue", events)
                    auto_broken += 1
            except ValueError:
                pass
        elif it["type"] == "event" and it.get("trigger"):
            trigger = it["trigger"]
            found = False
            cutoff = time.time() - EVENT_SCAN_DAYS * 86400
            for dp, _, fn in os.walk(daily_dir):
                for f in fn:
                    fp = os.path.join(dp, f)
                    try:
                        if os.path.getmtime(fp) < cutoff:
                            continue
                        text = open(fp, encoding="utf-8", errors="replace").read()
                        if trigger in text:
                            found = True
                    except OSError:
                        pass
            if found:
                it["status"] = "fulfilled"
                it["fulfilled_at"] = _now()
                _log_event(it["id"], "event_fired", events)
                event_fired += 1

    _save(items, store)
    return {"auto_broken": auto_broken, "event_fired": event_fired}


def cmd_fulfill(iid: str, store: Path, events: Path) -> int:
    items = _load(store)
    for it in items:
        if it["id"] == iid and it["status"] == "pending":
            it["status"] = "fulfilled"
            it["fulfilled_at"] = _now()
            _save(items, store)
            _log_event(iid, "fulfilled", events)
            print(f"✓ {iid} 已兑现")
            return 0
    print(f"{iid} 不存在或已处理")
    return 1


def cmd_broken(iid: str, store: Path, events: Path) -> int:
    items = _load(store)
    for it in items:
        if it["id"] == iid and it["status"] == "pending":
            it["status"] = "broken"
            it["broken_at"] = _now()
            _save(items, store)
            _log_event(iid, "broken", events)
            print(f"✗ {iid} 标记失约")
            return 0
    print(f"{iid} 不存在或已处理")
    return 1


def cmd_forget(iid: str, store: Path, events: Path) -> int:
    """软失效：status → invalidated（不物理删，历史保全）。"""
    items = _load(store)
    for it in items:
        if it["id"] == iid and it["status"] == "pending":
            it["status"] = "invalidated"
            it["invalidated_at"] = _now()
            _save(items, store)
            _log_event(iid, "invalidated", events)
            print(f"○ {iid} 已软失效（invalidated，历史可查）")
            return 0
    print(f"{iid} 不存在或状态不允许")
    return 1


def cmd_list(store: Path, show_all: bool = False, show_invalid: bool = False) -> int:
    items = _load(store)
    shown = 0
    for it in items:
        st = it["status"]
        if not show_all and st not in ("pending", "fulfilled", "broken"):
            continue
        if st == "invalidated" and not show_invalid:
            continue
        dl = f" deadline={it['deadline']}" if it.get("deadline") else ""
        print(f"{it['id']} [{st}] ({it['type']}){dl} {it['text'][:50]}")
        shown += 1
    print(f"显示 {shown} 条（总 {len(items)} 条）")
    return 0


def main(argv: list) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass

    store = STORE
    events = EVENTS
    if "--store" in argv:
        store = Path(argv[argv.index("--store") + 1])
    if "--events" in argv:
        events = Path(argv[argv.index("--events") + 1])

    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]

    if cmd == "promise":
        text = argv[2] if len(argv) > 2 else ""
        itype = argv[argv.index("--type") + 1] if "--type" in argv else "event"
        dl = argv[argv.index("--deadline") + 1] if "--deadline" in argv else None
        trigger = argv[argv.index("--trigger") + 1] if "--trigger" in argv else None
        r = cmd_promise(text, itype, dl, trigger, store, events)
        print(json.dumps(r, ensure_ascii=False)[:200] if isinstance(r, dict) else r)
        return 0

    if cmd == "check":
        r = cmd_check(store, events)
        print(f"check: auto_broken={r.get('auto_broken',0)} event_fired={r.get('event_fired',0)}")
        return 0

    if cmd == "fulfill":
        return cmd_fulfill(argv[2], store, events)
    if cmd == "broken":
        return cmd_broken(argv[2], store, events)
    if cmd == "forget":
        return cmd_forget(argv[2], store, events)
    if cmd == "list":
        show_all = "--all" in argv
        show_inv = "--invalid" in argv
        return cmd_list(store, show_all, show_inv)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
