# -*- coding: utf-8 -*-
r"""memory_integrity.py — 记忆投毒防线 v2（2026-11-19 · DSH 验收后加固）

v2 修正（dsh 凌晨验收抓出两处威胁模型级问题）:
  ✅ 账本外置: D:\大肥鱼的深海\_记忆账本.jsonl 原本在审计树内——能改记忆的攻击者
     也能顺手改账本，防线可被连锅端。现移至独立目录 ai-kb/integrity/（跨 harness 中立地）。
  ✅ 异地哈希锚: anchor 子命令——账本整体 SHA256+条目数 写入 git 管辖的
     training/out/ledger_anchor.json；改账本则锚对不上，改锚则 git diff 可见。双保险。
  ✅ audit 留痕: 每次审计向账本追加审计事件（谁/何时/目录/结果摘要），
     maker≠checker 的"谁对过账"不再缺失。verify 保持只读。

威胁模型（来源: "Long-term memory in LLM agents is an attack surface", arXiv 2026）:
  持续记忆可被投毒——被污染内容写入记忆后，后续所有会话的召回都当作可信事实。
  我们的红线闸只拦输入层，不拦记忆注入；本模块封住写入与读取两端。

机制（三件套 + 锚）:
  1. register 写入登记: 谁(zcode/dsh/master)在何时写了哪个文件的哪个哈希
  2. verify 读取校验: 当前哈希 vs 账本最后登记 → OK / MODIFIED / UNREGISTERED /
     ROLLED_BACK（回滚掩盖篡改） / GONE
  3. audit 目录审计: OK / MODIFIED / ROLLED_BACK / UNREGISTERED / GHOST 分类，
     并把审计事件本身写进账本留痕
  4. anchor 异地锚: 账本哈希锚存 git 管辖文件——篡改账本会在锚校验和 git diff 双处显形

跨 AI 纪律（maker≠checker 的记账版）:
  - 写入必须带来源签名（--source），无签名 = 可疑
  - 账本只追加不修改；账本、锚、被审计记忆三者物理分离
  - dsh 侧可随时 audit 对账——账本是对称可读的，且"谁对过账"有据可查

用法:
  python memory_integrity.py register D:\\大肥鱼的深海\\灵魂蓝图.txt --source zcode
  python memory_integrity.py verify D:\\大肥鱼的深海\\灵魂蓝图.txt
  python memory_integrity.py audit D:\\大肥鱼的深海\\ --source dsh
  python memory_integrity.py anchor update|check
  python memory_integrity.py --ledger <沙箱路径> ...   # 测试注入
"""
from __future__ import annotations

import hashlib
import json
import os
import sys
import time
from pathlib import Path

LEDGER = Path(r"C:\Users\14676\ai-kb\integrity\ledger.jsonl")  # v2: 独立于一切被审计树
ANCHOR = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\out\ledger_anchor.json")
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


def cmd_audit(directory: str, ledger: Path, source: str = "unknown") -> dict:
    root = Path(directory)
    if not root.is_dir():
        return {"error": f"目录不存在: {root}"}
    entries = load_ledger(ledger)
    buckets: dict[str, list[str]] = {"OK": [], "MODIFIED": [], "ROLLED_BACK": [],
                                     "UNREGISTERED": [], "GHOST": []}
    seen_paths: set[str] = set()
    ledger_resolved = str(ledger.resolve())
    for p in root.rglob("*"):
        if not p.is_file():
            continue
        sp = str(p.resolve())
        if sp == ledger_resolved:
            continue  # 账本本身若意外落在审计树内，不参与分类（v2 防自指）
        seen_paths.add(sp)
        v = cmd_verify(sp, ledger)
        buckets.get(v["verdict"], buckets["UNREGISTERED"]).append(sp)
    # GHOST: 登记过但文件已消失（在该目录范围内检查）
    known = {e.get("path") for e in entries if e.get("path")}
    for kp in known:
        if kp.startswith(str(root.resolve())) and kp not in seen_paths:
            buckets["GHOST"].append(kp)
    summary = {"dir": str(root), "files": sum(len(v) for v in buckets.values()),
               **{k: len(v) for k, v in buckets.items()},
               "detail": {k: v[:10] for k, v in buckets.items() if v}}
    # v2: 审计事件留痕（谁/何时/目录/结果摘要）——maker≠checker 的"谁对过账"
    _append({"ts": _now(), "event": "audit", "source": source,
             "dir": str(root), "summary": {k: v for k, v in summary.items()
                                           if k != "detail"}}, ledger)
    summary["audit_event_logged"] = True
    summary["auditor"] = source
    return summary


def _ledger_fingerprint(ledger: Path) -> dict:
    """账本整体指纹：SHA256 + 有效条目数（含审计事件行）。"""
    if not ledger.exists():
        return {"sha256": "", "lines": 0}
    raw = ledger.read_bytes()
    return {"sha256": hashlib.sha256(raw).hexdigest(),
            "bytes": len(raw),
            "lines": sum(1 for l in raw.decode("utf-8", errors="replace").splitlines() if l.strip())}


def cmd_anchor(mode: str, ledger: Path) -> dict:
    fp = _ledger_fingerprint(ledger)
    if mode == "update":
        prev = {}
        if ANCHOR.exists():
            try:
                prev = json.loads(ANCHOR.read_text(encoding="utf-8"))
            except (OSError, json.JSONDecodeError):
                prev = {}
        data = {"ts": _now(), "ledger_sha256": fp["sha256"], "lines": fp["lines"],
                "bytes": fp["bytes"], "prev_sha256": prev.get("ledger_sha256", "")}
        ANCHOR.parent.mkdir(parents=True, exist_ok=True)
        ANCHOR.write_text(json.dumps(data, ensure_ascii=False, indent=1), encoding="utf-8")
        return {"anchored": True, **{k: v for k, v in data.items() if k != "prev_sha256"},
                "anchor_path": str(ANCHOR)}
    if mode == "check":
        if not ANCHOR.exists():
            return {"verdict": "NO_ANCHOR", "detail": "锚文件不存在，先 anchor update"}
        try:
            a = json.loads(ANCHOR.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return {"verdict": "ANCHOR_CORRUPT"}
        if a.get("ledger_sha256") == fp["sha256"]:
            return {"verdict": "OK", "anchored_at": a.get("ts"), "lines": fp["lines"]}
        return {"verdict": "MISMATCH",
                "detail": "账本与异地锚不一致——账本被改或锚过期，需人工核对 git diff",
                "anchor_ts": a.get("ts"), "anchor_sha256": a.get("ledger_sha256", "")[:16] + "…",
                "current_sha256": fp["sha256"][:16] + "…"}
    return {"error": "mode 必须是 update|check"}


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
        source = argv[argv.index("--source") + 1] if "--source" in argv else "unknown"
        r = cmd_audit(argv[2], ledger, source)
        print(json.dumps(r, ensure_ascii=False, indent=1))
        return 0
    if cmd == "anchor" and len(argv) > 2:
        r = cmd_anchor(argv[2], ledger)
        print(json.dumps(r, ensure_ascii=False))
        return 0 if r.get("verdict") in ("OK", None) or r.get("anchored") else 1
    print(__doc__)
    return 2


if __name__ == "__main__":
    sys.exit(main(sys.argv))
