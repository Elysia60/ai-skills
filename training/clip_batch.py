# -*- coding: utf-8 -*-
"""clip_batch.py — CLIP 批量打分（一次加载，N 图同 prompt，JSON 输出）
用法：python clip_batch.py "prompt" 图1 图2 ... → {"scores": [..], "best_index": n}
"""
import json
import sys
from pathlib import Path

CLIP_DIR = Path(r"D:\AI训练基座\clip-vit-base-patch32")


def main():
    prompt, images = sys.argv[1], sys.argv[2:]
    import torch
    from PIL import Image
    from transformers import CLIPProcessor, CLIPModel
    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32
    cp = CLIPProcessor.from_pretrained(str(CLIP_DIR))
    cm = CLIPModel.from_pretrained(str(CLIP_DIR), torch_dtype=dtype).to(device).eval()
    scores = []
    for img_path in images:
        img = Image.open(img_path).convert("RGB")
        with torch.no_grad():
            inputs = cp(text=[prompt], images=img, return_tensors="pt", padding=True)
            inputs = {k: (v.to(device, dtype) if hasattr(v, "to") and v.is_floating_point() else (v.to(device) if hasattr(v, "to") else v)) for k, v in inputs.items()}
            scores.append(round(cm(**inputs).logits_per_image[0][0].item(), 3))
    best = scores.index(max(scores)) if scores else -1
    print(json.dumps({"scores": scores, "best_index": best}))


if __name__ == "__main__":
    main()
