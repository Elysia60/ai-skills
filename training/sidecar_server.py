# -*- coding: utf-8 -*-
"""sidecar_server.py — P0-1 Stage 1 旁路服务器（2026-11-18 · ZCode）

Stage 1 = 旁路观察层：三个端点跑仪器、全量记日志，pet 输出零变更。
Stage 2 = 观察 1-2 天（误杀/漂移/日志合理性）
Stage 3 = 前置接入（emotion 注入 + reply_contract 后处理 + 红线闸前置）

端点：
  GET  /health   → 健康检查（仪器状态）
  POST /advance  → 推进情感状态 {"valence":-0.5,"arousal":0.2} → 当前状态+声部指令
  GET  /style    → 当前声部风格指令（不推进状态）
  POST /validate → 回复合同校验 {"question":"...","answer":"..."} → 合同+漂移结果
  GET  /stats    → 运行统计（调用数/错误数/日志行数）

设计：
  - Python http.server（stdlib 零依赖）
  - 127.0.0.1 only（不暴露外网）
  - fail-open：任何 handler 异常 → 500 + 日志，不崩服务
  - 每个请求记 JSONL（可重放）
  - emotion_vector 状态持久化到 vector-state.json（与 dsh-emotion 的 schema 完全独立）
"""
import json
import os
import sys
import io
import time
import threading
from http.server import HTTPServer, BaseHTTPRequestHandler
from pathlib import Path

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8", errors="replace")

TRAIN = Path(__file__).resolve().parent
sys.path.insert(0, str(TRAIN))
CODEX = Path(r"C:\Users\14676\Documents\Codex")
if str(CODEX) not in sys.path:
    sys.path.insert(0, str(CODEX))

from emotion_vector import EmotionEngine  # noqa: E402
from dsh_reply_contract import check_natural_reply  # noqa: E402

LOG = Path(r"D:\大肥鱼的深海\主动消息\sidecar-events.jsonl")
STATE_FILE = TRAIN / "out" / "sidecar_emotion_state.json"
PORT = 9623

engine = EmotionEngine(state_file=str(STATE_FILE))
_stats = {"requests": 0, "errors": 0, "started": time.strftime("%Y-%m-%dT%H:%M:%S")}


def _log(event: dict):
    LOG.parent.mkdir(parents=True, exist_ok=True)
    event["ts"] = time.strftime("%Y-%m-%dT%H:%M:%S")
    with open(LOG, "a", encoding="utf-8") as f:
        f.write(json.dumps(event, ensure_ascii=False) + "\n")


def _read_body(handler) -> dict:
    length = int(handler.headers.get("Content-Length", 0))
    if length == 0:
        return {}
    raw = handler.rfile.read(length)
    try:
        return json.loads(raw.decode("utf-8"))
    except (json.JSONDecodeError, UnicodeDecodeError):
        return {}


class SidecarHandler(BaseHTTPRequestHandler):

    def _json_response(self, data: dict, status: int = 200):
        body = json.dumps(data, ensure_ascii=False, indent=1).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        _stats["requests"] += 1
        if self.path == "/health":
            self._json_response({"status": "ok", "port": PORT,
                                 "stats": dict(_stats),
                                 "emotion": engine.as_dict()})
        elif self.path == "/style":
            self._json_response(engine.style_directives())
        elif self.path == "/stats":
            self._json_response(dict(_stats))
        else:
            self._json_response({"error": "unknown path"}, 404)

    def do_POST(self):
        _stats["requests"] += 1
        body = _read_body(self)
        if self.path == "/advance":
            try:
                engine.apply_event(
                    valence=body.get("valence", 0),
                    arousal=body.get("arousal", 0),
                    dominance=body.get("dominance", 0),
                    source=body.get("source", "sidecar"))
                engine.decay_if_stale()
                engine.save()
                result = {"state": dict(engine.state),
                          "arbitration": engine.arbitrate(),
                          "style": engine.style_directives()}
                _log({"endpoint": "advance", **result})
                self._json_response(result)
            except Exception as e:  # noqa: BLE001
                _stats["errors"] += 1
                _log({"endpoint": "advance", "error": str(e)})
                self._json_response({"error": str(e)}, 500)

        elif self.path == "/validate":
            try:
                question = body.get("question", "")
                answer = body.get("answer", "")
                reply_check = check_natural_reply(answer)
                crisis = engine.crisis
                _log({"endpoint": "validate", "question": question[:100],
                      "answer_len": len(answer), "reply_ok": reply_check["ok"],
                      "crisis": crisis})
                self._json_response({"reply_check": reply_check,
                                     "crisis_mode": crisis})
            except Exception as e:  # noqa: BLE001
                _stats["errors"] += 1
                _log({"endpoint": "validate", "error": str(e)})
                self._json_response({"error": str(e)}, 500)
        elif self.path == "/crisis":
            engine.set_crisis()
            engine.save()
            _log({"endpoint": "crisis", "action": "set"})
            self._json_response({"crisis": True, "mode": engine.style_directives()["mode"]})

        elif self.path == "/clear-crisis":
            engine.clear_crisis()
            engine.save()
            _log({"endpoint": "clear-crisis", "action": "cleared"})
            self._json_response({"crisis": False, "state": dict(engine.state)})

        else:
            self._json_response({"error": "unknown path"}, 404)

    def log_message(self, format, *args):
        pass  # 静默默认日志（自有 JSONL 代替）


class ThreadedHTTPServer(HTTPServer):
    """daemon_threads 版 HTTPServer。"""
    daemon_threads = True


def serve():
    server = ThreadedHTTPServer(("127.0.0.1", PORT), SidecarHandler)
    print(f"sidecar 运行中 → http://127.0.0.1:{PORT}")
    print(f"端点: /health /style /stats | POST /advance /validate")
    print(f"日志: {LOG}")
    print(f"状态文件: {STATE_FILE}")
    server.serve_forever()


if __name__ == "__main__":
    serve()
