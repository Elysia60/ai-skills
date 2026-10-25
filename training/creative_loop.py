# -*- coding: utf-8 -*-
"""creative_loop.py — 创作闭环（2026-10-25 ZCode · 生成→看图核对→自动重画 + BoN 选优）

体系位置：ADetailer 思想的全链版（承诺于画图强化轮，今日建成）。
学术根基：Best-of-N + verifier（RLHF Book ch.9；此前已引）——N 张选优，元素核对做 verifier。
流程：
  ① BoN：同 prompt 生成 N 张（不同 seed）→ CLIP logit 选优
  ② 元素核对：prompt 拆元素 → qwen2.5vl 逐元素问答（在/不在）
  ③ 自动重画：不合格元素 → 强化 prompt 重生成一轮（元素词加权）→ 复核
用法：python creative_loop.py "prompt" [--n 4] [--elements 元素1,元素2,...]（不给则自动拆英文逗号/中文逗号）
"""
import argparse
import json
import re
import subprocess
import sys
import time
from pathlib import Path

VENV = r"C:\Users\14676\简历\.venv\Scripts\python.exe"
GEN = r"C:\Users\14676\简历\gen_image.py"
OUT = Path(r"C:\Users\14676\简历\outputs")


def run(cmd, t=300):
    r = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=t, shell=True)
    return (r.stdout or "") + (r.stderr or "")


def gen(prompt, seed):
    out_path = str(OUT / f"cl_{int(time.time()*1000)}_{seed}.png")
    o = run(f'"{VENV}" -X utf8 "{GEN}" "{prompt}" --seed {seed} --out "{out_path}"', t=300)
    m = re.search(r"出图: (\S+\.png)", o)
    return m.group(1).replace(chr(92), "/") if m else None


def clip_best(images, prompt):
    """CLIP logit 选优——clip_batch.py 一次加载批量判，JSON 输出无匹配歧义。"""
    o = run(f'"{VENV}" -X utf8 "C:/Users/14676/.zcode/workspace/default/ai-skills/training/clip_batch.py" "{prompt}" ' + " ".join(f'"{i}"' for i in images), t=300)
    try:
        d = json.loads(o[o.index("{"): o.rindex("}") + 1])
        bi = d["best_index"]
        return images[bi], d["scores"][bi]
    except (ValueError, KeyError, IndexError):
        print(f"    [选优失败] 输出头: {o.strip()[:120]!r}")
        return images[0] if images else None, -99


def vlm_check(img, element):
    o = run(f'python -X utf8 "C:/Users/14676/.zcode/workspace/default/ai-skills/training/vision_chat.py" "{img}" "图里有{element}吗？只答有或没有，然后一句话说明"', t=300)
    a = o.strip().splitlines()[-1] if o.strip() else ""
    hit = ("有" in a[:6]) or a.startswith("有") or (element in a)
    return hit, a[:80]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("prompt")
    ap.add_argument("--n", type=int, default=4)
    ap.add_argument("--elements", default=None)
    a = ap.parse_args()
    elements = [e.strip() for e in re.split(r"[,，]", a.elements or "") if e.strip()] or \
               [e.strip() for e in re.split(r"[,，]", a.prompt) if len(e.strip()) >= 2][:4]

    print(f"BoN 生成 {a.n} 张…")
    imgs = [p for p in (gen(a.prompt, s) for s in range(100, 100 + a.n)) if p]
    print(f"  生成 {len(imgs)}/{a.n}")
    best, bl = clip_best(imgs, a.prompt)
    print(f"CLIP 选优: logit={bl:.1f} → {Path(best).name}")

    print("\n元素核对（qwen2.5vl）：")
    hits = 0
    miss = []
    for e in elements:
        ok, ans = vlm_check(best, e)
        hits += ok
        print(f"  {'✓' if ok else '✗'} {e}: {ans}")
        if not ok:
            miss.append(e)

    if miss:
        print(f"\n重画：强化缺失元素 {miss}")
        strong = a.prompt + ", " + ", ".join(f"({m} emphasized, clearly visible)" for m in miss)
        img2 = gen(strong, 999)
        if img2:
            hits2, ok2_list = 0, []
            for e in elements:
                ok, ans = vlm_check(img2, e)
                hits2 += ok
                ok2_list.append(ok)
            print(f"  重画命中 {hits2}/{len(elements)}（首图 {hits}/{len(elements)}）")
            if hits2 > hits:
                best = img2
                hits = hits2
                print("  → 采用重画稿")

    print(f"\n== 闭环结果：{Path(best).name} ｜ 元素命中 {hits}/{len(elements)} ==")
    return 0


if __name__ == "__main__":
    sys.exit(main())
