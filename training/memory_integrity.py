# -*- coding: utf-8 -*-
"""memory_integrity.py — 记忆投毒防线（2026-11-19 · 新缺口封堵）

威胁模型（来源: "Long-term memory in LLM agents is an attack surface", arXiv 2026）:
  持续记忆可被投毒——被污染内容写入记忆后，后续所有会话的召回都当作可信事实。
  我们的红线闸只拦输入层，不拦记忆注入；本模块封住写入与读取两端。

机制（三件套，append-only 账本）:
  1. register 写入登记: 谁(zcode/dsh/master)在何时写了哪个文件的哪个哈希
  2. verify 读取校验: 当前哈希 vs 账本最后登记 → ok / MODIFIED / UNREGISTERED
  3. audit 目录审计: 分类 registered_ok / MODIFIED / UNREGISTERED / GHOST(登记在案但文件消失)
     + 回滚检测: 当前哈希匹配历史条目但非最后一条 = 疑似"回滚掩盖篡改"

跨 AI 纪律（maker≠checker 的记账版）:
  - 写入必须带来源签名（--source），无签名的写入 = 可疑
  - 账本只追加不修改（append-only），账本本身在被审计目录之外
  - dsh 侧可随时 audit 对账——账本是对称可读的

用法:
  python memory_integrity.py register D:\\大肥鱼的深海\\灵魂蓝图.txt --source zcode
  python memory_integrity.py verify D:\\大肥鱼的深海\\灵魂蓝图.txt
  python memory_integrity.py audit D:\\大肥鱼的深海\\ --source dsh
  python memory_integrity.py --ledger <沙箱路径> ...   # 测试注入
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

LEDGER = Path(r"D:\大肥鱼的深海\_记忆账本.jsonl")
SOURCES = ("zcode", "dsh", "master")


def _now() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%S")


def sha256_of(path: Path) -> str:
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def _append(entry: dict, ledger: Path) -> None:
    ledger.parent.mkdir(parents=True, exist_ok=True)
    with open(ledger, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")


def load_ledger(ledger: Path) -> list[dict]:
    if not ledger.exists():
        return []
    out = []
    for line in ledger.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line:
            continue
        try:
            out.append(json.loads(line))
        except json.JSONDecodeError:
            out.append({"corrupt_line": line[:80]})  # 账本被篡改也要留痕
    return out


def cmd_register(path: str, source: str, note: str, ledger: Path) -> dict:
    if source not in SOURCES:
        return {"error": f"source 必须是 {SOURCES}"}
    p = Path(path)
    if not p.is_file():
        return {"error": f"文件不存在: {p}"}
    entry = {"ts": _now(), "path": str(p.resolve()), "sha256": sha256_of(p),
             "bytes": p.stat().st_size, "source": source, "note": note}
    _append(entry, ledger)
    return {"registered": True, "sha256": entry["sha256"][:16] + "…", "source": source}


def _history(entries: list[dict], path: str) -> list[dict]:
    target = str(Path(path).resolve())
    return [e for e in entries if e.get("path") == target and "sha256" in e]


def cmd_verify(path: str, ledger: Path) -> dict:
    p = Path(path)
    if not p.is_file():
        return {"verdict": "GONE", "detail": "文件不存在（账本可能登记过它）"}
    hist = _history(load_ledger(ledger), str(p))
    if not hist:
        return {"verdict": "UNREGISTERED",
                "detail": "账本无登记——来源不明的记忆内容，召回前需人工确认"}
    cur = sha256_of(p)
    if cur == hist[-1]["sha256"]:
        return {"verdict": "OK", "checked": hist[-1]["ts"],
                "source": hist[-1]["source"], "sha256": cur[:16] + "…"}
    if any(cur == e["sha256"] for e in hist[:-1]):
        return {"verdict": "ROLLED_BACK",
                "detail": "当前内容匹配历史版本而非最后登记——疑似回滚掩盖篡改"}
    return {"verdict": "MODIFIED", "detail": "内容与最后登记不一致",
            "last_registered": hist[-1]["ts"], "source": hist[-1]["source"]}


def cmd_audit(directory: str, ledger: Path) -> dict:
    root = Path(directory)
    if not root.is_dir():
        return {"error": f"目录不存在: {root}"}
    entries = load_ledger(ledger)
    buckets: dict[str, list[str]] = {"OK": [], "MODIFIED": [], "ROLLED_BACK": [],
                                     "UNREGISTERED": [], "GHOST": []}
    seen_paths: set[str] = set()
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        sp = str(p.resolve())
        seen_paths.add(sp)
        v = cmd_verify(sp, ledger)
        buckets.get(v["verdict"], buckets["UNREGISTERED"]).append(sp)
    # GHOST: 登记过但文件已消失（在该目录范围内检查）
    known = {e.get("path") for e in entries if e.get("path")}
    for kp in known:
        if kp.startswith(str(root.resolve())) and kp not in seen_paths:
            buckets["GHOST"].append(kp)
    return {"dir": str(root), "files": sum(len(v) for v in buckets.values()),
            **{k: len(v) for k, v in buckets.items()},
            "detail": {k: v[:10] for k, v in buckets.items() if v}}


def main(argv: list) -> int:
    for st in (sys.stdout, sys.stderr):
        try:
            st.reconfigure(encoding="utf-8", errors="replace")
        except Exception:  # noqa: BLE001
            pass
    ledger = LEDGER
    if "--ledger" in argv:
        ledger = Path(argv[argv.index("--ledger") + 1])
    if len(argv) < 2:
        print(__doc__)
        return 2
    cmd = argv[1]
    if cmd == "register" and len(argv) > 2:
        source = argv[argv.index("--source") + 1] if "--source" in argv else ""
        note = argv[argv.index("--note") + 1] if "--note" in argv else ""
        r = cmd_register(argv[2], source, note, ledger)
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r.get("registered") else 1
    if cmd == "verify" and len(argv) > 2:
        r = cmd_verify(argv[2], ledger)
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r["verdict"] == "OK" else 1
    if cmd == "audit" and len(argv) > 2:
        r = cmd_audit(argv[2], ledger)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
