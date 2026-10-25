# -*- coding: utf-8 -*-
"""caption_clip_score.py — 画图自评（2026-10-25 ZCode）
⚠ 状态：superseded——正本为 DSH 侧 blip_selfcheck.py（--image/--prompt CLI + logit 直读已修）。
   保留原因：双实现对照样本（softmax 假绿灯 bug 的化石——DSH 侧抓的归一化假象实证）。

背景（DSH 侧复核）：BLIP 自评曾是 python -c 内联跑——"跑通了"没有可复现的东西 = 没验（SKILL #38）。
且 BLIP caption 做元素核对是假绿灯（1/3 命中率：漏小元素/自己加元素/类别词错）——
DSH 侧方案：判据换 **CLIP score**（图像-提示词语义距离，整体匹配不漏报）。

功能：
  ① BLIP caption：一句话描述（参考用，不做判据）
  ② CLIP score：prompt 与图像的语义相似度（判据）——阈值标定：SD1.5 出图对原 prompt
     的典型分值区间待多次采样后固化为闸门（首版观测值打印供标定）
用法：
  python caption_clip_score.py <图片路径> "prompt 原文"
输出：BLIP 描述 + CLIP score + 判定（阈值首版 0.25 观测，标定后收紧）。
模型：D:\AI训练基座\（blip + clip-vit-base-patch32，均本地落盘）。
"""
import sys
from pathlib import Path

BLIP_DIR = Path(r"D:\AI训练基座\blip-captioning-base")
CLIP_DIR = Path(r"D:\AI训练基座\clip-vit-base-patch32")
CLIP_REPO = "openai/clip-vit-base-patch32"


def main() -> int:
    if len(sys.argv) < 3:
        print("用法: python caption_clip_score.py <图片> \"prompt\"")
        return 2
    img_path, prompt = sys.argv[1], sys.argv[2]

    import torch
    from PIL import Image
    from transformers import BlipProcessor, BlipForConditionalGeneration, CLIPProcessor, CLIPModel

    device = "cuda" if torch.cuda.is_available() else "cpu"
    dtype = torch.float16 if device == "cuda" else torch.float32

    # ① BLIP caption（参考）
    bp = BlipProcessor.from_pretrained(str(BLIP_DIR))
    bm = BlipForConditionalGeneration.from_pretrained(str(BLIP_DIR), torch_dtype=dtype).to(device)
    img = Image.open(img_path).convert("RGB")
    inputs = bp(img, return_tensors="pt")
    # 只有浮点张量（pixel_values）转 fp16——input_ids/attention_mask 必须保持 Long
    inputs = {k: (v.to(device, dtype) if hasattr(v, "to") and v.is_floating_point() else (v.to(device) if hasattr(v, "to") else v)) for k, v in inputs.items()}
    cap = bp.decode(bm.generate(**inputs, max_new_tokens=60)[0], skip_special_tokens=True)
    del bm
    torch.cuda.empty_cache()

    # ② CLIP score（判据）——本地有则用本地，无则经镜像落盘一次
    if CLIP_DIR.exists():
        clip_src = str(CLIP_DIR)
    else:
        from huggingface_hub import snapshot_download
        import os
        os.environ.setdefault("HF_ENDPOINT", "https://hf-mirror.com")
        os.environ.setdefault("HF_HUB_DISABLE_XET", "1")
        clip_src = snapshot_download(CLIP_REPO, local_dir=str(CLIP_DIR))
    cp = CLIPProcessor.from_pretrained(clip_src)
    cm = CLIPModel.from_pretrained(clip_src, torch_dtype=dtype).to(device)
    inputs = cp(text=[prompt], images=img, return_tensors="pt", padding=True)
    # 只有浮点张量（pixel_values）转 fp16——input_ids/attention_mask 必须保持 Long
    inputs = {k: (v.to(device, dtype) if hasattr(v, "to") and v.is_floating_point() else (v.to(device) if hasattr(v, "to") else v)) for k, v in inputs.items()}
    with torch.no_grad():
        logits = cm(**inputs).logits_per_image
    torch.cuda.empty_cache()

    # 2026-10-25 修 DSH 侧抓的 bug：softmax(dim=1) 在单图单文本时分母只有自己 → 恒 1.0（归一化假象）。
    # 真信息是 logit 本身（CLIP 典型 -10~10；30+ = 超强匹配）。sigmoid 供 0-1 口径对照。
    logit = logits[0][0].item()
    sig = torch.sigmoid(logits[0][0]).item()

    print(f"图: {img_path}")
    print(f"prompt: {prompt}")
    print(f"BLIP 描述（参考）: {cap}")
    print(f"CLIP logit（判据）: {logit:.3f} ｜ sigmoid 对照: {sig:.4f}")
    # logit 口径阈值（首版观测：30.384=强匹配样本；标定待办多次采样）
    verdict = "PASS" if logit >= 20 else ("WARN" if logit >= 10 else "FAIL")
    print(f"判定: {verdict}（logit ≥20 PASS / 10-20 WARN / <10 FAIL——首版观测，标定待办）")
    return 0 if verdict == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
