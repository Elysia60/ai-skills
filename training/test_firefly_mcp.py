# -*- coding: utf-8 -*-
"""test_firefly_mcp.py — 最小 MCP 服务端测试(2026-11-23 · 零依赖)

纯函数 handle() 逐协议项测试 + 全部 5 工具真跑(本机实数据) + 通知不回/未知方法报错/工具异常不崩。
"""
import sys
import unittest

sys.path.insert(0, r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
import firefly_mcp as FM  # noqa: E402


def rpc(method, params=None, mid=1):
    msg = {"jsonrpc": "2.0", "id": mid, "method": method}
    if params is not None:
        msg["params"] = params
    return FM.handle(msg)


class TestProtocol(unittest.TestCase):
    def test_initialize_handshake(self):
        r = rpc("initialize", {})
        self.assertEqual(r["result"]["protocolVersion"], FM.PROTOCOL_VERSION)
        self.assertEqual(r["result"]["serverInfo"]["name"], "firefly-mcp")
        self.assertIn("tools", r["result"]["capabilities"])

    def test_tools_list_has_five(self):
        r = rpc("tools/list")
        names = [t["name"] for t in r["result"]["tools"]]
        self.assertEqual(len(names), 5)
        for t in r["result"]["tools"]:
            self.assertIn("inputSchema", t)

    def test_notification_returns_none(self):
        self.assertIsNone(FM.handle({"jsonrpc": "2.0", "method": "notifications/initialized"}))

    def test_unknown_method_error(self):
        r = rpc("resources/list")
        self.assertEqual(r["error"]["code"], -32601)

    def test_unknown_tool_error(self):
        r = rpc("tools/call", {"name": "不存在的工具"})
        self.assertEqual(r["error"]["code"], -32602)

    def test_tool_crash_becomes_error_content(self):
        """单工具异常 → 错误内容返回,服务端不崩(fail-open)。"""
        old = FM.HANDLERS["firefly_signal"]
        FM.HANDLERS["firefly_signal"] = lambda a: (_ for _ in ()).throw(RuntimeError("db 锁死"))
        try:
            r = rpc("tools/call", {"name": "firefly_signal"})
        finally:
            FM.HANDLERS["firefly_signal"] = old
        self.assertIn("RuntimeError", r["result"]["content"][0]["text"])


class TestToolsLive(unittest.TestCase):
    """真跑本机数据(只读)。"""
    def test_signal(self):
        r = rpc("tools/call", {"name": "firefly_signal"})
        t = r["result"]["content"][0]["text"]
        self.assertTrue("最新信号" in t or "不存在" in t or "为空" in t)

    def test_brief(self):
        r = rpc("tools/call", {"name": "firefly_brief", "arguments": {"lines": 5}})
        self.assertIn("content", r["result"])

    def test_cs_brief(self):
        r = rpc("tools/call", {"name": "cs_brief"})
        self.assertIn("content", r["result"])

    def test_watchdog(self):
        r = rpc("tools/call", {"name": "watchdog_status"})
        t = r["result"]["content"][0]["text"]
        self.assertTrue("心跳" in t)

    def test_registry_lookup(self):
        r = rpc("tools/call", {"name": "registry_lookup", "arguments": {"query": "负面"}})
        t = r["result"]["content"][0]["text"]
        self.assertIn("[S", t)
        r2 = rpc("tools/call", {"name": "registry_lookup", "arguments": {"query": "不存在的词组xyz"}})
        self.assertIn("无匹配", r2["result"]["content"][0]["text"])


if __name__ == "__main__":
    unittest.main()
