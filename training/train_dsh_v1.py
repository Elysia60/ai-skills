# -*- coding: utf-8 -*-
"""train_dsh_v1.py — 阶段二：QLoRA 微调 Qwen2.5-7B → qwen-dsh-v1（2026-10-24）

数据：training/sft_instructions.jsonl（35 条 SFT）→ training/dpo_pairs_v1.jsonl（54 对 DPO）
流程：SFT 3 epochs → DPO 3 epochs（标准顺序：先对齐格式能力，再对齐偏好）
基座：D:\AI训练基座\qwen25-7b-instruct-hf（4-bit NF4）
输出：training/out/qwen-dsh-v1-lora（adapter）+ 合并 16-bit 可选
引擎：优先 Unsloth（快），无则 transformers+trl（稳）
红线：全程本地；训练前 GPU 显存检查；产物与原模型隔离。
"""
import json
import sys
from pathlib import Path

BASE = Path(r"D:\AI训练基座\qwen25-7b-instruct-hf")
TRAIN = Path(r"C:\Users\14676\.zcode\workspace\default\ai-skills\training")
OUT = TRAIN / "out" / "qwen-dsh-v1-lora"
MAX_SEQ = 1024


def check_env():
    import torch
    assert torch.cuda.is_available(), "无 CUDA——拒绝在 CPU 上跑"
    free, total = torch.cuda.mem_get_info()
    assert free / 1e9 > 5.0, f"显存空闲 {free/1e9:.1f}GB < 5GB——先关闭 Ollama 模型等占用"
    print(f"GPU 就绪：空闲 {free/1e9:.1f}GB")


def load_jsonl(p: Path):
    return [json.loads(l) for l in p.read_text(encoding="utf-8").splitlines() if l.strip()]


def main():
    check_env()
    try:
        from unsloth import FastLanguageModel
        USE_UNSIOTH = True
        print("引擎: Unsloth")
    except ImportError:
        from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig
        USE_UNSIOTH = False
        print("引擎: transformers+trl（Unsloth 不可用）")

    import torch
    from datasets import Dataset
    from trl import SFTTrainer, DPOTrainer, DPOConfig, SFTConfig

    kwargs = dict(model_name=str(BASE), max_seq_length=MAX_SEQ,
                  load_in_4bit=True)
    if USE_UNSIOTH:
        model, tokenizer = FastLanguageModel.from_pretrained(**kwargs)
        model = FastLanguageModel.get_peft_model(
            model, r=16, lora_alpha=32, lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            use_gradient_checkpointing="unsloth")
    else:
        from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
        bnb = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4",
                                 bnb_4bit_compute_dtype=torch.bfloat16, bnb_4bit_use_double_quant=True)
        tokenizer = AutoTokenizer.from_pretrained(str(BASE))
        model = AutoModelForCausalLM.from_pretrained(str(BASE), quantization_config=bnb, device_map="auto")
        model.enable_input_require_grads()
        model = get_peft_model(model, LoraConfig(
            r=16, lora_alpha=32, lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            task_type="CAUSAL_LM"))

    # —— 阶段 A：SFT ——
    sft_rows = [{"text": f"<|im_start|>user\n{r['instruction']}<|im_end|>\n<|im_start|>assistant\n{r['output']}<|im_end|>"}
                for r in load_jsonl(TRAIN / "sft_instructions.jsonl")]
    sft = Dataset.from_list(sft_rows)
    strainer = SFTTrainer(model=model, tokenizer=tokenizer, train_dataset=sft,
                          dataset_text_field="text",
                          args=SFTConfig(output_dir=str(OUT / "sft"), per_device_train_batch_size=2,
                                         gradient_accumulation_steps=4, num_train_epochs=3, logging_steps=5,
                                         learning_rate=2e-4, warmup_ratio=0.1, lr_scheduler_type="cosine",
                                         save_strategy="no", report_to="none", max_seq_length=MAX_SEQ))
    strainer.train()
    print("SFT 完成")

    # —— 阶段 B：DPO ——
    dpo_rows = [{"prompt": r["prompt"], "chosen": r["chosen_v1"], "rejected": r["rejected_v1"]}
                for r in load_jsonl(TRAIN / "dpo_pairs_v1.jsonl") if r.get("rewritten")]
    dpo = Dataset.from_list(dpo_rows)
    dtrainer = DPOTrainer(model=model, ref_model=None,  # PEFT 下 ref=base 自动
                          tokenizer=tokenizer, train_dataset=dpo,
                          args=DPOConfig(output_dir=str(OUT / "dpo"), per_device_train_batch_size=2,
                                         gradient_accumulation_steps=4, num_train_epochs=3, logging_steps=5,
                                         learning_rate=5e-5, beta=0.1, save_strategy="no", report_to="none",
                                         max_length=MAX_SEQ, max_prompt_length=256))
    dtrainer.train()
    print("DPO 完成")

    model.save_pretrained(str(OUT))
    tokenizer.save_pretrained(str(OUT))
    print(f"adapter 已存: {OUT}")


if __name__ == "__main__":
    sys.exit(main())
