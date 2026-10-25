# -*- coding: utf-8 -*-
"""vision_threshold_calibration.py — CLIP 阈值标定 + 十万次 Bootstrap（2026-10-25 ZCode）

方法：Fong 2019（bootstrap 阈值 CI，PMC6713448）+ CLIP 校准文献（arXiv 2503.08723）。
数据：8 图（6 新生成 + 2 既有）× 10 文（8 真 prompt + 3 泛用干扰…实为 8×(8+3) 对，去对角=配对错）。
产出：最优点估计阈值 + 100000 次重采样的 95% CI——十万次是真的十万次（Efron 1979）。
"""
import random
from pathlib import Path

import numpy as np
import torch
from PIL import Image
from transformers import CLIPProcessor, CLIPModel

CLIP_DIR = Path(r"D:\AI训练基座\clip-vit-base-patch32")
OUT = Path(r"C:\Users\14676\简历\outputs")
IMGS = [
    (OUT / "img_1792891214.png", "a cute anime girl with blue hair, whale hairpin, maid dress, soft lighting, masterpiece, best quality"),
    (OUT / "img_1792891483.png", "a cute anime girl with blue hair, whale hairpin, maid dress, soft lighting, masterpiece, best quality"),
    (OUT / "img_1792904170.png", "a mountain lake at sunrise, mist, pine forest, landscape photo"),
    (OUT / "img_1792904195.png", "a bowl of ramen with egg and nori, food photography"),
    (OUT / "img_1792904214.png", "a fluffy orange cat sleeping on a windowsill"),
    (OUT / "img_1792904231.png", "a red sports car on a coastal road at sunset"),
    (OUT / "img_1792904248.png", "an abandoned spaceship interior, sci-fi concept art"),
    (OUT / "img_1792904267.png", "a bouquet of sunflowers in a glass vase, oil painting"),
]
GENERIC = ["a photo of a dog", "a city skyline at night", "a plate of sushi"]


def main():
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    cp = CLIPProcessor.from_pretrained(str(CLIP_DIR))
    cm = CLIPModel.from_pretrained(str(CLIP_DIR), torch_dtype=dtype).to(device).eval()

    prompts = [p for _, p in IMGS] + GENERIC
    matched, mismatched = [], []
    for i, (img_path, own) in enumerate(IMGS):
        img = Image.open(img_path).convert("RGB")
        with torch.no_grad():
            inputs = cp(text=prompts, images=img, return_tensors="pt", padding=True)
            inputs = {k: (v.to(device, dtype) if hasattr(v, "to") and v.is_floating_point() else (v.to(device) if hasattr(v, "to") else v)) for k, v in inputs.items()}
            logits = cm(**inputs).logits_per_image[0]
        for j, p in enumerate(prompts):
            v = logits[j].item()
            if p == own:
                matched.append(v)
            else:
                mismatched.append(v)
    m, x = np.array(matched), np.array(mismatched)
    # 2026-10-25 族8教训：原始数据必须持久化（重建分布重采样=造新数据，不构成复验）
    import json
    with open("C:/Users/14676/.zcode/workspace/default/ai-skills/training/raw_clip_logits.json", "w", encoding="utf-8") as _rf:
        json.dump({"matched": matched, "mismatched": mismatched}, _rf)
    print(f"配对数：匹配 {len(m)} / 错配 {len(x)}")
    print(f"匹配 logit：min {m.min():.2f} max {m.max():.2f} 均值 {m.mean():.2f}")
    print(f"错配 logit：min {x.min():.2f} max {x.max():.2f} 均值 {x.mean():.2f}")

    grid = np.arange(5.0, 35.1, 0.5)

    def best_thr(a, b):
        acc = [( (a >= t).mean() * len(a) + (b < t).mean() * len(b) ) / (len(a) + len(b)) for t in grid]
        return grid[int(np.argmax(acc))]

    point = best_thr(m, x)
    rng = np.random.default_rng(42)
    N = 100_000
    boot = np.empty(N)
    for i in range(N):
        ma = m[rng.integers(0, len(m), len(m))]
        xb = x[rng.integers(0, len(x), len(x))]
        boot[i] = best_thr(ma, xb)
    lo, hi = np.percentile(boot, [2.5, 97.5])
    print(f"\n== CLIP 阈值标定（{N:,} 次 bootstrap，seed=42）==")
    print(f"点估计: {point:.1f} ｜ 95% CI: [{lo:.1f}, {hi:.1f}]")
    print(f"当前线上阈值 20 → {'在 CI 内（保守侧）' if lo <= 20 <= hi else ('偏高' if 20 > hi else '偏低')}")
    # 推荐值：CI 中点
    rec = (lo + hi) / 2
    print(f"推荐: PASS ≥ {rec:.0f}（CI 中点）；WARN 带 [{rec-5:.0f}, {rec:.0f}）")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
