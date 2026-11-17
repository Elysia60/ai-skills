# -*- coding: utf-8 -*-
"""dsh_standing_intents.py — L3 约定兑现基础设施（2026-11-18 · P0 · 缺口 #5）

来源：OpenClaw standing-intents 三层设计（cron/aspiration/event-conditional）
      + anima-brain continuity.py 的修复语义 + dsh 裁决七列格式。

三层：
  time       时间型——deadline 到了就触发（"周五提醒我"）
  event      条件型——事件出现就触发（"主人提体检时问结果"）
  aspiration 心愿型——不触发，但每周复查（"这个季度改善排片"）

设计（fail-open 原则）：
  - 文件式存储（零依赖零线程零数据库）
  - 约定一经创建不可删除（只能 complete/broken/cancel——历史保全）
  - 到期未处理 → 自动标 broken（不是"消失"）
  - 兑现/失约写入 promises-events.jsonl 审计

用法：
  python dsh_standing_intents.py promise "周五提醒我确认回滚负责人" --type time --deadline "2026-11-22"
  python dsh_standing_intents.py promise "主人提体检时问结果" --type event --trigger "体检"
  python dsh_standing_intents.py promise "这个季度改善排片流程" --type aspiration
  python dsh_standing_intents.py check              # 巡检：到期/触发/过期
  python dsh_standing_intents.py fulfill <id>       # 标记兑现
  python dsh_standing_intents.py broken <id>        # 标记失约
  python dsh_standing_intents.py list [--all]       # 列出（默认只出 pending）
"""
import json
import os
import sys
import io
import time
from pathlib import Path

# stdout reconfigure 延迟到 main() —— import 时无副作用（带电 import 教训）

STORE = Path(r"C:\Users\14676\.dsh\memories\standing_intents.json")
EVENTS = Path(r"D:\大肥鱼的深海\主动消息\promises-events.jsonl")
TYPES = ("time", "event", "aspiration")


def _load() -> list:
    if not STORE.exists():
        return []
    try:
        return json.loads(STORE.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return []


def _save(items: list) -> None:
    STORE.parent.mkdir(parents=True, exist_ok=True)
    STORE.write_text(json.dumps(items, ensure_ascii=False, indent=1), encoding="utf-8")


def _log_event(entry_id: str, event: str) -> None:
    EVENTS.parent.mkdir(parents=True, exist_ok=True)
    entry = json.dumps({"ts": time.strftime("%Y-%m-%dT%H:%M:%S"),
                        "intent_id": entry_id, "event": event},
                       ensure_ascii=False)
    with open(EVENTS, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def cmd_promise(text: str, itype: str, deadline: str | None,
                trigger: str | None) -> int:
    if itype not in TYPES:
        print(f"类型必须是 {TYPES}")
        return 1
    items = _load()
    now = time.strftime("%Y-%m-%dT%H:%M:%S")
    seq = sum(1 for it in items if it.get("created", "").startswith(now[:10])) + 1
    entry = {
        "id": f"SI-{now[:10].replace('-','')}-{seq:03d}",
        "text": text, "type": itype, "status": "pending",
        "created": now, "deadline": deadline, "trigger": trigger,
        "fulfilled_at": None, "broken_at": None,
    }
    items.append(entry)
    _save(items)
    _log_event(entry["id"], "created")
    print(f"已登记约定 {entry['id']} ({itype}): {text[:50]}")
    return 0


def cmd_check() -> int:
    """巡检：到期未兑现 → 标 broken + 告警。幂等：已处理的不重复。"""
    items = _load()
    now = time.time()
    alerted = 0
    for it in items:
        if it["status"] != "pending" or it["type"] != "time":
            continue
        dl = it.get("deadline")
        if not dl:
            continue
        try:
            dl_ts = time.mktime(time.strptime(dl, "%Y-%m-%d"))
        except ValueError:
            continue
        if now > dl_ts + 86400:  # 过期超 1 天 → broken
            it["status"] = "broken"
            it["broken_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            _log_event(it["id"], "auto_broken_overdue")
            alerted += 1
    if alerted:
        _save(items)
        print(f"⚠ {alerted} 条约定过期未兑现 → 标 broken")
    else:
        print("巡检：无过期约定")
    return 0


def cmd_fulfill(iid: str) -> int:
    items = _load()
    for it in items:
        if it["id"] == iid and it["status"] == "pending":
            it["status"] = "fulfilled"
            it["fulfilled_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            _save(items)
            _log_event(iid, "fulfilled")
            print(f"✓ {iid} 已兑现")
            return 0
    print(f"{iid} 不存在或已处理")
    return 1


def cmd_broken(iid: str) -> int:
    items = _load()
    for it in items:
        if it["id"] == iid and it["status"] == "pending":
            it["status"] = "broken"
            it["broken_at"] = time.strftime("%Y-%m-%dT%H:%M:%S")
            _save(items)
            _log_event(iid, "broken")
            print(f"✗ {iid} 标记失约")
            return 0
    print(f"{iid} 不存在或已处理")
    return 1


def cmd_list(show_all: bool) -> int:
    items = _load()
    for it in items:
        if not show_all and it["status"] != "pending":
            continue
        dl = f" deadline={it['deadline']}" if it.get("deadline") else ""
        print(f"{it['id']} [{it['status']}] ({it['type']}){dl} {it['text'][:50]}")
    print(f"共 {len(items)} 条")
    return 0


def main(argv: list) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    if len(argv) < 2:
        print(__doc__)
        return 1
    cmd = argv[1]
    if cmd == "promise":
        text = argv[2] if len(argv) > 2 else ""
        itype = argv[argv.index("--type") + 1] if "--type" in argv else "event"
        dl = argv[argv.index("--deadline") + 1] if "--deadline" in argv else None
        trigger = argv[argv.index("--trigger") + 1] if "--trigger" in argv else None
        return cmd_promise(text, itype, dl, trigger)
    if cmd == "check":
        return cmd_check()
    if cmd == "fulfill":
        return cmd_fulfill(argv[2]) if len(argv) > 2 else 1
    if cmd == "broken":
        return cmd_broken(argv[2]) if len(argv) > 2 else 1
    if cmd == "list":
        return cmd_list("--all" in argv)
    print(__doc__)
    return 1


if __name__ == "__main__":
    sys.exit(main(sys.argv))
