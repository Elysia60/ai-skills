# -*- coding: utf-8 -*-
"""firefly_mcp.py — 萤火信号 MCP 服务端(2026-11-23 · 零依赖 · 只读)

出处: MCP(Model Context Protocol, Anthropic)生态 2026(约 97M 下载)与 A2A(Google)
互补而非替代;最小服务端只需 JSON-RPC 2.0 over stdio 的三件事:
initialize + tools/list + tools/call(arXiv 2505.02279 协议综述核实)。
本文件是 2027 框架"MCP 经济层"的第一块砖: 任何 MCP 客户端(ZCode/其他 agent)
都能直接读取萤火生态的只读信号,跨 agent 判断不再靠人肉搬运。

红线:
  - 只读——不写湖/不碰交易/不改任何状态(经济层探索期零副作用)
  - 零依赖——纯标准库,不装 mcp SDK(本机内存红线)
  - fail-open——单工具异常→错误内容返回,服务端不崩

工具(5 个只读):
  firefly_signal   最新信号(verdict/score,forecast_log)
  firefly_brief    最新决策简报(头部)
  cs_brief         CS2 最新简报(头部)
  watchdog_status  看门狗心跳
  registry_lookup  结论注册表按关键词检索(38 条)

用法:
  echo '{"jsonrpc":"2.0","id":1,"method":"initialize","params":{}}' | python firefly_mcp.py
  (MCP 客户端以 stdio 长驻方式接入;每行一个 JSON-RPC 消息)
"""
from __future__ import annotations

import json
import sqlite3
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8", errors="replace")

ASTOCK = Path(r"C:\Users\14676\Documents\02-项目开发\股市量化\astock-monitor")
CSQAQ = Path(r"C:\Users\14676\Documents\02-项目开发\CS2皮肤追踪\csqaq-monitor")
DEEPSEA = Path(r"D:\大肥鱼的深海")
METHODS = ASTOCK / "METHODS.md"
PROTOCOL_VERSION = "2024-11-05"

TOOLS = [
    {"name": "firefly_signal", "description": "萤火最新信号: verdict+score(forecast_log 最新一行)",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "firefly_brief", "description": "最新 A 股决策简报头部(今日动作/依据/失效条件)",
     "inputSchema": {"type": "object", "properties": {"lines": {"type": "integer", "description": "取头部行数,默认 25"}}}},
    {"name": "cs_brief", "description": "CS2 最新决策简报头部",
     "inputSchema": {"type": "object", "properties": {"lines": {"type": "integer", "description": "默认 20"}}}},
    {"name": "watchdog_status", "description": "看门狗心跳与最近状态行",
     "inputSchema": {"type": "object", "properties": {}}},
    {"name": "registry_lookup", "description": "结论注册表(38 条)按关键词检索,含反方陈述",
     "inputSchema": {"type": "object", "properties": {"query": {"type": "string", "description": "关键词,如 熔断/负面/TSFM"},
                                                     "limit": {"type": "integer", "description": "默认 5"}}}},
]


def _latest(pattern: str, root: Path):
    fs = sorted(root.glob(pattern))
    return fs[-1] if fs else None


def tool_firefly_signal(_args: dict) -> str:
    db = ASTOCK / "data" / "monitor.db"
    if not db.exists():
        return "monitor.db 不存在——萤火数据层未初始化"
    row = sqlite3.connect(str(db)).execute(
        "SELECT signal_date, verdict, score FROM forecast_log ORDER BY signal_date DESC LIMIT 1").fetchone()
    if not row:
        return "forecast_log 为空"
    return f"最新信号 {row[0]}: verdict={row[1]} score={row[2]:.1f}(只读快照,非投资建议)"


def tool_firefly_brief(args: dict) -> str:
    f = _latest("results/decision_brief/*.md", ASTOCK)
    if not f:
        return "简报未产出"
    lines = int(args.get("lines") or 25)
    return "\n".join(f.read_text(encoding="utf-8", errors="replace").splitlines()[:lines])


def tool_cs_brief(args: dict) -> str:
    f = _latest("data/reports/*-brief.md", CSQAQ)
    if not f:
        return "cs 简报未产出"
    lines = int(args.get("lines") or 20)
    return "\n".join(f.read_text(encoding="utf-8", errors="replace").splitlines()[:lines])


def tool_watchdog_status(_args: dict) -> str:
    hb = Path(r"C:\Users\14676\.dsh\watchdog-last-run.txt")
    out = f"心跳: {hb.read_text(encoding='utf-8', errors='replace').strip()}" if hb.exists() else "心跳文件缺失"
    wd = _latest("2026-*-watchdog.md", DEEPSEA / "主动消息")
    if wd:
        out += "\n" + wd.read_text(encoding="utf-8", errors="replace").strip().splitlines()[0][:80]
    return out


def tool_registry_lookup(args: dict) -> str:
    q = (args.get("query") or "").strip()
    limit = int(args.get("limit") or 5)
    rows = []
    for line in METHODS.read_text(encoding="utf-8", errors="replace").splitlines():
        line = line.strip()
        if line.startswith("| [") and "---" not in line:
            if not q or q in line:
                rows.append(line[:240])
    if not rows:
        return f"注册表无匹配: {q}"
    return f"共 {len(rows)} 条命中,前 {min(limit, len(rows))} 条:\n" + "\n".join(rows[:limit])


HANDLERS = {"firefly_signal": tool_firefly_signal, "firefly_brief": tool_firefly_brief,
            "cs_brief": tool_cs_brief, "watchdog_status": tool_watchdog_status,
            "registry_lookup": tool_registry_lookup}


def handle(msg: dict) -> dict | None:
    """纯函数分发(可测核心): 一条 JSON-RPC → 响应或 None(通知不回)。"""
    method = msg.get("method", "")
    mid = msg.get("id")
    if method.startswith("notifications/"):
        return None
    if method == "initialize":
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "protocolVersion": PROTOCOL_VERSION, "capabilities": {"tools": {}},
            "serverInfo": {"name": "firefly-mcp", "version": "0.1"}}}
    if method == "tools/list":
        return {"jsonrpc": "2.0", "id": mid, "result": {"tools": TOOLS}}
    if method == "tools/call":
        name = (msg.get("params") or {}).get("name", "")
        args = (msg.get("params") or {}).get("arguments") or {}
        if name not in HANDLERS:
            return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32602,
                    "message": f"未知工具: {name}"}}
        try:
            text = HANDLERS[name](args)
        except Exception as e:  # noqa: BLE001 — 单工具异常→错误内容,服务端不崩
            text = f"工具 {name} 异常: {type(e).__name__}: {e}"
        return {"jsonrpc": "2.0", "id": mid, "result": {
            "content": [{"type": "text", "text": str(text)}]}}
    return {"jsonrpc": "2.0", "id": mid, "error": {"code": -32601,
            "message": f"方法不存在: {method}"}}


def serve() -> int:
    """stdio 主循环: 每行一条 JSON-RPC;解析失败回 -32700;EOF 退出。"""
    for line in sys.stdin:
        line = line.strip()
        if not line:
            continue
        try:
            msg = json.loads(line)
        except json.JSONDecodeError as e:
            resp = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700,
                    "message": f"解析失败: {e}"}}
        else:
            resp = handle(msg)
        if resp is not None:
            sys.stdout.write(json.dumps(resp, ensure_ascii=False) + "\n")
            sys.stdout.flush()
    return 0


if __name__ == "__main__":
    sys.exit(serve())
