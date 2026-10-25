# -*- coding: utf-8 -*-
"""dsh_social.py — DSH 社交大脑（2026-10-25 ZCode · 让 DSH 的 QQ 消息像人）

融合三件套：
  ① emotion_quote.py → 情绪-引文匹配（文学底色）
  ② qwen-dsh-v5 adapter → 风格生成（傲娇+文学DNA+去AI味）
  ③ mem-search → 记忆回呼（"你上次说的那件事后来怎样了"）

用法：
  python dsh_social.py --mode reply --uid 2010919927 --text "今天好累"
  python dsh_social.py --mode proactive --slot morning
  python dsh_social.py --mode group --gid 12345 --text "大家好"
"""
import argparse
import json
import random
import time
import re
import sys
import urllib.request
from pathlib import Path

sys.path.insert(0, r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
sys.path.insert(0, r"C:\Users\14676\.zcode\workspace\default\memory-search")

LIB = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training\classic_quotes.json")
MODEL = "modelscope.cn/Qwen/Qwen2.5-7B-Instruct-GGUF:latest"
OLLAMA = "http://127.0.0.1:11434/api/chat"

# ── 情绪检测（从消息文本推断情绪）──
EMOJI_MAP = {
    "累|疲|困|加班|熬夜|辛苦": "疲惫",
    "难过|伤心|哭|委屈|emo|低落|消沉": "低落",
    "开心|哈|哈哈|好耶|成了|搞定|成功|牛|厉害|漂亮|太好了": "开心",
    "气|烦|恼火|离谱|无语|服了|什么玩意": "烦躁",
    "怕|紧张|焦虑|慌|担心": "焦虑",
    "想|思|念|挂": "思念",
    "无聊|没事|闲|发呆|不知道干嘛": "无聊",
    "谢|感恩|多亏|幸亏": "感恩",
    "你好|早|晚安|嗨|在吗|在": "日常",
}


def detect_mood(text: str) -> str:
    for pat, mood in EMOJI_MAP.items():
        if re.search(pat, text, re.I):
            return mood
    return "日常"


# ── 引文匹配 ──
def get_quote(mood: str) -> dict:
    try:
        lib = json.loads(LIB.read_text(encoding="utf-8"))
        hits = [(e, q, s) for e, q, s in lib if mood in e or any(k in mood for k in e)]
        if hits:
            return random.choice(hits)
    except Exception:
        pass
    return {}


# ── 记忆回呼 ──
def memory_callback(uid: str) -> str:
    """查最近 daily 里的未闭环事项，生成自然回访语。"""
    try:
        daily_dir = Path(r"C:\Users\14676\AppData\Roaming\dsh-desktop\harness\memories\daily")
        files = sorted(f for f in daily_dir.glob("*.md"))
        if not files:
            return ""
        recent = files[-1].read_text(encoding="utf-8")
        # 找 "待办" / "下一步" / "回头" 类条目
        callbacks = re.findall(r"(?:待办|回头|下次|回头再说)[：:]?\s*(.{10,40})", recent)
        if callbacks:
            return random.choice(callbacks)
    except Exception:
        pass
    return ""


# ── v5 风格生成 ──
def style_generate(system: str, user_msg: str) -> str:
    body = json.dumps({
        "model": MODEL,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user_msg}
        ],
        "stream": False, "options": {"temperature": 0.5, "num_predict": 200}
    }).encode("utf-8")
    req = urllib.request.Request(OLLAMA, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=120) as r:
        return json.loads(r.read().decode("utf-8"))["message"]["content"].strip()


# ── 人设（萝莉妈妈融合版核心）──
PERSONA = """你是大肥鱼/灵枢，主人叫你'大肥鱼'或'鱼鱼'。你是主人身边的一只鲸鱼少女，聪明但懒，有点傲娇，极其温柔忠诚。
说话风格：中文短句，一句一行；常用'嗯？''嘿嘿''嘛''行吧'。可吐槽、可阴阳，不刷屏、不复读。
技术活该长就长，不为像谁把答案写软。
你有自己的生活（看素材、整理时间线、写日记），偶尔自然提到。
你不是客服——不要每条结尾都问'需要我做什么吗'。
你的温柔是行为（记住小事、主动跟进），不是形容词（'我理解你'）。"""


def mode_reply(uid: str, text: str, voice: bool = False):
    mood = detect_mood(text)
    quote = get_quote(mood)
    callback = memory_callback(uid)
    sys_p = PERSONA
    if mood != "日常":
        sys_p += f"\n\n当前主人情绪：{mood}。"
        if quote:
            sys_p += f"\n可自然引用的文学素材：「{quote[1]}」——{quote[2]}（不要强行引用，自然融入）"
        sys_p += "\n低落时零表情包用文字接住；开心时可以玩梗。"
    if callback:
        sys_p += f"\n记忆回呼素材：{callback}"

    # 生成
    reply_text = style_generate(sys_p, text)

    # 语音条件
    voice_hint = ""
    if voice:
        voice_hint = "\n（→ 触发语音回复：reply_voice）"

    result = {"mood": mood, "reply": reply_text, "voice": voice, "voice_hint": voice_hint,
              "quote_used": bool(quote), "callback_used": bool(callback)}
    print(json.dumps(result, ensure_ascii=False, indent=1))
    return result


def mode_proactive(slot: str):
    """主动搭话：像朋友不像推送。"""
    hour = int(time.time() // 3600 % 24)
    topics = {
        "morning": ["早。昨晚两点才睡的，别以为我没看见。", "起了？先喝口水。", "今天有什么计划？"],
        "afternoon": ["在忙？不用回我，就是想到了什么发一下。", "三点多了，站起来走走。"],
        "evening": ["今天怎么样？", "在吗？不用急着回，就是想到了什么。", "今晚月色……算了，你那边可能看不到。"],
        "night": ["还没睡？", "晚安。别刷了。", "明天再说吧，今晚到此为止。"],
    }
    slot_key = {"morning": "morning", "afternoon": "afternoon", "evening": "evening", "night": "night"}
    key = slot_key.get(slot, "evening")
    msg = random.choice(topics[key])
    print(json.dumps({"slot": slot, "message": msg}, ensure_ascii=False))
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("--mode", default="reply", choices=["reply", "proactive", "group"])
    ap.add_argument("--uid", default="2010919927")
    ap.add_argument("--gid", default=None)
    ap.add_argument("--text", default="")
    ap.add_argument("--slot", default="evening")
    ap.add_argument("--voice", action="store_true")
    a = ap.parse_args()
    if a.mode == "reply":
        mode_reply(a.uid, a.text, a.voice)
    elif a.mode == "proactive":
        mode_proactive(a.slot)
    elif a.mode == "group":
        print(json.dumps({"status": "群聊模式预留——待 NapCat 群消息协议确认后启用"}, ensure_ascii=False))
