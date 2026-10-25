# -*- coding: utf-8 -*-
"""vision_chat.py — 本地看图器官（2026-10-25 ZCode · qwen2.5vl:3b via Ollama）

突破：看图不再依赖 ModLens 安装门与云端 key——Qwen2.5-VL-3B 量化 3.2GB 走现有 Ollama 器官。
实测（vs BLIP）：蓝发✓+发饰✓（BLIP 漏）+连衣裙细节（领/袖口/蝴蝶结=女仆裙元素）——元素级 3/3 vs BLIP 1/3。
用法：python vision_chat.py <图片路径> "问题（默认：详细描述这张图）"
"""
import base64
import json
import sys
import urllib.request

MODEL = "qwen2.5vl:3b"


def look(image_path: str, question: str = "详细描述这张图") -> str:
    img = base64.b64encode(open(image_path, "rb").read()).decode()
    body = json.dumps({"model": MODEL, "messages": [
        {"role": "user", "content": question, "images": [img]}],
        "stream": False, "options": {"temperature": 0.2, "num_predict": 300}}).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=300) as r:
        return json.loads(r.read().decode())["message"]["content"]


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("用法: python vision_chat.py <图片> [问题]")
        sys.exit(2)
    print(look(sys.argv[1], sys.argv[2] if len(sys.argv) > 2 else "详细描述这张图"))
