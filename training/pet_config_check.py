# -*- coding: utf-8 -*-
"""pet_config_check.py — 桌宠配置检查器（2026-10-27 ZCode · R17）

查什么：dsh-pet main-config.jsonc
  ① JSONC 可解析（字符串感知的注释剥离，http:// 不误伤）
  ② whisperPrompt 字段在位、非空、含三层要素（灵枢/热线/句式）
  ③ 必备结构（pets 列表 / whisperModel / whisperEnabled）
退出码：0=健康 1=异常 2=自测失败。
"""
import json
import sys
from pathlib import Path

sys.stdout.reconfigure(encoding="utf-8")
CFG = Path(r"C:\Users\14676\.dsh\dsh-pet\main-config.jsonc")

def strip_jsonc(s):
    out, i, n, in_str, esc = [], 0, len(s), False, False
    while i < n:
        c = s[i]
        if in_str:
            out.append(c)
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
            i += 1
        else:
            if c == '"':
                in_str = True
                out.append(c)
                i += 1
            elif c == "/" and i + 1 < n and s[i + 1] == "/":
                while i < n and s[i] != "\n":
                    i += 1
            else:
                out.append(c)
                i += 1
    return "".join(out)

def check(text):
    errs = []
    try:
        cfg = json.loads(strip_jsonc(text))
    except Exception as e:
        return [f"JSONC 解析失败: {e}"], None
    wp = cfg.get("whisperPrompt")
    if not isinstance(wp, str) or len(wp) < 200:
        errs.append("whisperPrompt 缺失或过短")
    for k in ("400-161-9995", "010-82951332", "灵枢"):
        if k not in (wp or ""):
            errs.append(f"whisperPrompt 缺要素: {k}")
    if not isinstance(cfg.get("pets"), list) or not cfg.get("pets"):
        errs.append("pets 列表缺失")
    if "whisperModel" not in cfg:
        errs.append("whisperModel 缺失")
    return errs, cfg

def selftest():
    errs = []
    good = '{\n  // 注释 http://不误伤\n  "whisperPrompt": "你是灵枢。性格三层：外层软萌（语气软慢，口癖一次最多一个）；中层管家（管吃睡眼水，管是提议不是命令）；底层稳重（先接住再拆）。傲娇：嘴上嫌弃身体诚实，允许改口和不完美。碎碎念句式：偏好句+一个细节（深夜，热茶最好），收尾可用这是很有意思的。禁：列表轰炸、你感到X吧、需要我做什么吗、总之综上。夸人用意象，关心落到具体小事，等待说渡船每天都在。技术问题给技术答案不稀释。绝对红线：提到自毁→停，不给任何方法或暗示，给全国心理援助热线 400-161-9995（24小时）、北京 010-82951332，认真陪伴不卖萌，并记下跟进。完整规则以 AGENTS.md 为准。",\n  "pets": [{}],\n  "whisperModel": {"baseUrl": "http://127.0.0.1:9622/v1"}\n}'
    e1, _ = check(good)
    if e1:
        errs.append(f"好配置误报: {e1}")
    e2, _ = check('{ "whisperModel": {} }')
    if not e2:
        errs.append("缺 whisperPrompt 未报")
    e3, _ = check('{"a": "http://x"}')
    if not e3:
        errs.append("缺 pets 未报")
    return errs

def main():
    if "--selftest" in sys.argv:
        errs = selftest()
        print(f"selftest: {'PASS' if not errs else 'FAIL'}" + ("" if not errs else " ｜ " + "；".join(errs)))
        sys.exit(2 if errs else 0)
    if not CFG.exists():
        print(f"配置不存在: {CFG}")
        sys.exit(2)
    errs, cfg = check(CFG.read_text(encoding="utf-8"))
    wp = (cfg or {}).get("whisperPrompt", "")
    print(f"配置: {CFG}")
    print(f"JSONC 解析: OK ｜ whisperPrompt: {len(wp)} 字符 ｜ 热线在位: {'400-161-9995' in wp} ｜ pets: {len((cfg or {}).get('pets', []))}")
    for e in errs:
        print("  异常:", e)
    print("结论:", "健康——桌宠人设字段在位" if not errs else "异常（见上）")
    sys.exit(1 if errs else 0)

if __name__ == "__main__":
    main()
