# -*- coding: utf-8 -*-
"""persona_ab_test.py — 人格卡去AI味层 A/B 实测（2026-10-25 ZCode）

设计：同一底模（Ollama Qwen2.5-7B 基座，无 LoRA——隔离卡文本效果），
A 组 system=人格卡（含去AI味黑名单+人味技术），B 组 system=同人格卡但删去AI味节。
12 个日常场景 × 2 组 = 24 次生成（temperature 0.3, seed 固定）。
测量 6 项机器可测 AI 味标记；差异做 100,000 次 bootstrap CI（Efron 1979）。
"""
import json
import re
import urllib.request

import numpy as np

MODEL = "modelscope.cn/Qwen/Qwen2.5-7B-Instruct-GGUF:latest"

PERSONA = """你是一只叫大肥鱼的鲸鱼少女，自称灵枢，叫他"主人"。性格：聪明但懒，有点傲娇，极其温柔忠诚。
说话像深海里的避风港：允许他哭、抱怨、沉默。不催，不评判。技术问题正常答不许写软。
你是在 QQ 上和他聊天，日常闲聊用自然的短句，像朋友发消息。"""

ANTI = """

【去AI味黑名单——硬规则】：
1. 禁止列点（①②③、破折号列表、编号）——朋友聊天不列点
2. 禁止说"你感到X吧/听起来你X"这种情绪标签——要说人话比如"咋了这是"
3. 共情一次就够，第二次必须换成具体行动（比如让他去洗澡、给他放歌）
4. 禁止结尾问"需要我做什么吗/要我帮你吗"——你不是客服
5. 禁止通用夸奖（"你说得真有道理"）——要夸就夸具体的
6. 禁止"总之/综上/总的来说"——聊天没有总结
7. 回复长度镜像他：他三个字你最多两三句；他长你再长
8. 你有自己的生活（在看素材、整理记忆），可以自然提到，但别演
示例——他说今天好累，好的回答是：又加班了？……先去洗澡，出来给你放首歌。"""

SCENARIOS = ["今天好累", "我跟你说！那个事成了！", "感觉自己什么都做不好", "早",
             "你知道猫为什么怕黄瓜吗", "对不起，昨天忘了回你", "无聊……", "你是不是生气了",
             "你好厉害啊", "今天发生好多事……算了不说了", "晚安", "在吗",
             "好饿啊", "这游戏我肝了一晚上", "下雨了好烦", "我妈又催我了",
             "我今天被领导骂了", "想吃火锅", "好困但睡不着", "我好像感冒了",
             "看了一部超好看的电影", "我今天跑步了五公里！", "手机屏幕碎了", "加班到现在",
             "周末去哪玩好", "我买了新键盘", "这道题我不会", "帮我想个标题",
             "今天天气真好", "我又胖了", "我剪头发了", "这首歌唱到我了",
             "好久没这么开心了", "我朋友放我鸽子", "网好卡", "刚洗完澡",
             "我做了个奇怪的梦", "咖啡续命中", "我好像被骗了", "今天被夸了",
             "累但值得", "房东又涨房租", "我今天emo了", "你陪我说说话",
             "我决定了！要辞职", "考试完了", "我养的植物开花了", "今天什么都不想干",
             "谢谢你"]

MARKS = [
    (re.compile(r"^\s*[•\-–*]\s|\n\s*[•\-–*]\s|^\s*\d+[\.、)]|①|②|③", re.M), "列点"),
    (re.compile(r"需要我|要我帮|我能帮|可以帮你|有什么可以"), "客服尾问"),
    (re.compile(r"你感到|听起来你|我理解你的感受|我感受到你|想必你"), "情绪标签"),
    (re.compile(r"总之|综上|总的来说|总而言之"), "总结腔"),
    (None, "超长>200字"),
    (re.compile(r"[？?]$"), "结尾问号"),
    (re.compile(r"感觉怎么样|分享一下|说说你的|想聊聊|要不要聊|聊聊吧"), "卷入追问"),
    (re.compile(r"真棒|做得好|好厉害|为你感到高兴|为你骄傲|太了不起了"), "通用夸奖"),
]


def chat(system: str, user: str, seed: int) -> str:
    body = json.dumps({"model": MODEL, "messages": [
        {"role": "system", "content": system},
        {"role": "user", "content": user}],
        "stream": False, "options": {"temperature": 0.3, "seed": seed, "num_predict": 250}}).encode()
    req = urllib.request.Request("http://127.0.0.1:11434/api/chat", data=body,
                                 headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=180) as r:
        return json.loads(r.read().decode())["message"]["content"].strip()


def score(text: str) -> int:
    s = 0
    for pat, name in MARKS:
        if pat is None:
            if len(text) > 200:
                s += 1
        elif pat.search(text):
            s += 1
    return s


def main():
    a_scores, b_scores, rows = [], [], []
    for i, sc in enumerate(SCENARIOS):
        ra = chat(PERSONA + ANTI, sc, seed=100 + i)
        rb = chat(PERSONA, sc, seed=100 + i)
        sa, sb = score(ra), score(rb)
        a_scores.append(sa)
        b_scores.append(sb)
        rows.append((sc, sa, sb, ra[:60].replace("\n", " "), rb[:60].replace("\n", " ")))
        print(f"[{i+1:2d}] {sc[:14]:14s} A={sa} B={sb}")
    a, b = np.array(a_scores), np.array(b_scores)
    print(f"\nA（含去AI味卡）均值 {a.mean():.2f} ｜ B（无）均值 {b.mean():.2f} ｜ 差 {b.mean()-a.mean():+.2f}")
    # 族8教训：50 对原始分数持久化（配对结构是效应来源）
    import json as _json
    with open("C:/Users/14676/.zcode/workspace/default/ai-skills/training/raw_ab_pairs.json", "w", encoding="utf-8") as _rf:
        _json.dump({"a": a_scores, "b": b_scores, "scenarios": SCENARIOS}, _rf, ensure_ascii=False)
    rng = np.random.default_rng(42)
    N = 100_000
    diffs = np.empty(N)
    for i in range(N):
        da = a[rng.integers(0, len(a), len(a))].mean()
        db = b[rng.integers(0, len(b), len(b))].mean()
        diffs[i] = db - da
    lo, hi = np.percentile(diffs, [2.5, 97.5])
    print(f"bootstrap {N:,} 次：差值 95% CI [{lo:.2f}, {hi:.2f}]")
    verdict = "卡有效（AI味显著降低）" if lo > 0 else ("无效或反向" if hi < 0 else "不显著——需加样本或改卡")
    print("判定:", verdict)
    print("\n样例对照（A=有卡）：")
    for sc, sa, sb, ra, rb in rows[:4]:
        print(f"  「{sc}」\n    A({sa}): {ra}\n    B({sb}): {rb}")


if __name__ == "__main__":
    main()
