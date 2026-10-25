# -*- coding: utf-8 -*-
"""dsh_v5_server.py — qwen-dsh-v5 常驻推理服务（2026-10-25 ZCode）

解决：v5 首次加载 50s 导致 QQ 等待体验杀手。
方案：Flask 常驻 HTTP 服务——模型加载一次后驻留显存，后续推理 ~3s。
降级：v5 端点超时/失败 → dsh_answer 自动回退 Ollama GGUF（不卡用户）。
端口：9622（避开 LightRAG 9621 和 Ollama 11434）。
用法：python dsh_v5_server.py  → 后台常驻
     curl http://127.0.0.1:9622/answer?q=问题   # GET 快速
     curl -X POST http://127.0.0.1:9622/answer -d '{"q":"问题"}'
"""
import io
import json
import threading
import time
from pathlib import Path

from flask import Flask, request, jsonify

ADAPTER = r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\out\qwen-dsh-v5-lora"
BASE = r"D:\AI训练基座\qwen25-7b-instruct-hf"

app = Flask(__name__)
model = None
tok = None
ready = threading.Event()


def load():
    global model, tok
    import torch
    from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
    from peft import PeftModel
    print("加载 v5…")
    tok = AutoTokenizer.from_pretrained(BASE)
    bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                             bnb_4bit_compute_dtype=torch.bfloat16)
    m = AutoModelForCausalLM.from_pretrained(BASE, quantization_config=bnb, device_map="auto")
    m = PeftModel.from_pretrained(m, ADAPTER)
    m.eval()
    model = m
    ready.set()
    print("v5 就绪")


@app.route("/health")
def health():
    return jsonify({"ready": ready.is_set(), "model": "qwen-dsh-v5"})


@app.route("/answer", methods=["GET", "POST"])
def answer():
    if request.method == "GET":
        q = request.args.get("q", "")
    else:
        q = request.get_json(force=True).get("q", "")
    if not q.strip():
        return jsonify({"error": "empty q"}), 400
    if not ready.is_set():
        return jsonify({"error": "model loading"}), 503
    import torch
    msg = "<|im_start|>user" + chr(10) + q + "<|im_end|>" + chr(10) + "<|im_start|>assistant" + chr(10)
    inputs = tok(msg, return_tensors="pt").to(model.device)
    with torch.no_grad():
        out = model.generate(**inputs, max_new_tokens=220, do_sample=False)
    text = tok.decode(out[0][inputs["input_ids"].shape[1]:], skip_special_tokens=True).strip()
    return jsonify({"answer": text})


def boot():
    t = threading.Thread(target=load, daemon=True)
    t.start()
    app.run(host="127.0.0.1", port=9622, threaded=True)


if __name__ == "__main__":
    boot()
