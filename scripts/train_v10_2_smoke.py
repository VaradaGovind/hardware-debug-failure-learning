#!/usr/bin/env python3
"""
scripts/train_v10_2_smoke.py

Trains a lightweight smoke LoRA adapter on 75 per-turn examples for 30 steps.
Purpose: Verify that per-turn supervision successfully conditions the model to
generate tool calls on Step 1 instead of immediately concluding.
"""

import os
import sys
import gc
import json
import time
import math
import random
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)


def format_per_turn_example(tokenizer, example: Dict[str, Any], max_length: int = 896):
    convs = example.get("conversations", [])
    if len(convs) < 3:
        return None

    system_text = str(convs[0].get("value", ""))
    human_text = str(convs[1].get("value", ""))
    target_text = str(convs[2].get("value", ""))

    sys_turn = f"<|im_start|>system\n{system_text}<|im_end|>\n"
    sys_ids = tokenizer.encode(sys_turn, add_special_tokens=False)

    target_turn = f"<|im_start|>assistant\n{target_text}<|im_end|>\n"
    target_ids = tokenizer.encode(target_turn, add_special_tokens=False)

    user_hdr = "<|im_start|>user\n"
    user_ftr = "<|im_end|>\n"
    user_hdr_ids = tokenizer.encode(user_hdr, add_special_tokens=False)
    user_ftr_ids = tokenizer.encode(user_ftr, add_special_tokens=False)
    raw_user_ids = tokenizer.encode(human_text, add_special_tokens=False)

    avail_user_body = max_length - len(sys_ids) - len(target_ids) - len(user_hdr_ids) - len(user_ftr_ids)
    if avail_user_body < 50:
        return None

    if len(raw_user_ids) > avail_user_body:
        u_head = min(120, avail_user_body // 3)
        u_tail = avail_user_body - u_head
        raw_user_ids = raw_user_ids[:u_head] + raw_user_ids[-u_tail:]

    user_ids = user_hdr_ids + raw_user_ids + user_ftr_ids

    prompt_ids = sys_ids + user_ids
    full_ids = prompt_ids + target_ids
    labels = [-100] * len(prompt_ids) + target_ids

    active_tokens = sum(1 for l in labels if l != -100)
    if active_tokens < 5:
        return None

    return {
        "input_ids": full_ids,
        "labels": labels,
        "attention_mask": [1] * len(full_ids),
        "active_tokens": active_tokens
    }


def train_v10_2_smoke(max_steps: int = 30, lr: float = 1.0e-4, grad_accum: int = 2):
    gc.collect()

    print("=" * 80)
    print("EXPERIMENT V10.2: TRAINING BEHAVIORAL SMOKE ADAPTER")
    print("=" * 80)

    import torch
    import torch_directml
    from transformers import AutoTokenizer, AutoModelForCausalLM
    from peft import LoraConfig, get_peft_model, TaskType

    if torch_directml.device_count() > 0:
        device = torch_directml.device(0)
        gpu_name = torch_directml.device_name(0)
        dtype = torch.float16
        print(f"[*] DirectML Acceleration Active: {gpu_name} (Device: {device})")
    else:
        device = torch.device("cpu")
        dtype = torch.float32
        print("[!] Running on CPU.")

    smoke_data_path = os.path.join(WORKSPACE_ROOT, "datasets", "v10_2", "per_turn_smoke_v10_2.json")
    output_dir = "C:/Users/varad/ml-cache/rca-reuse/v10_2/checkpoints/v10_2_smoke_adapter"
    best_ckpt_dir = os.path.join(output_dir, "best_smoke_checkpoint")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(best_ckpt_dir, exist_ok=True)

    base_model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct"

    print(f"\n[Step 1/4] Loading Tokenizer & Base Model ({base_model_name}) in {dtype}...")
    tokenizer = AutoTokenizer.from_pretrained(base_model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    model = AutoModelForCausalLM.from_pretrained(
        base_model_name,
        torch_dtype=dtype,
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    model.config.use_cache = False

    print("\n[Step 2/4] Initializing LoRA Adapter [q_proj, v_proj] (r=16, alpha=32)...")
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        bias="none",
        task_type=TaskType.CAUSAL_LM,
        target_modules=["q_proj", "v_proj"]
    )
    model = get_peft_model(model, lora_config)
    trainable_params, all_params = model.get_nb_trainable_parameters()
    print(f"  Trainable Parameters: {trainable_params:,} / {all_params:,} ({100 * trainable_params / all_params:.2f}%)")

    model.to(device)

    print(f"\n[Step 3/4] Loading & Tokenizing Smoke Dataset from {smoke_data_path}...")
    with open(smoke_data_path, "r", encoding="utf-8") as f:
        raw_smoke = json.load(f)

    tokenized_smoke = []
    for ex in raw_smoke:
        item = format_per_turn_example(tokenizer, ex, max_length=896)
        if item is not None:
            tokenized_smoke.append(item)

    print(f"  Tokenized Smoke Examples: {len(tokenized_smoke)} / {len(raw_smoke)}")

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=lr,
        weight_decay=0.01
    )

    print(f"\n[Step 4/4] Executing Smoke Training Loop ({max_steps} Optimization Steps)...")
    model.train()
    global_step = 0
    step_loss = 0.0
    accum_count = 0
    t0 = time.time()

    data_idx = 0
    n_examples = len(tokenized_smoke)
    indices = list(range(n_examples))
    random.shuffle(indices)

    optimizer.zero_grad()

    while global_step < max_steps:
        ex_idx = indices[data_idx % n_examples]
        data_idx += 1
        item = tokenized_smoke[ex_idx]

        inp = torch.tensor([item["input_ids"]], dtype=torch.long, device=device)
        att = torch.tensor([item["attention_mask"]], dtype=torch.long, device=device)
        lbl = torch.tensor([item["labels"]], dtype=torch.long, device=device)

        hidden = model.base_model.model.model(input_ids=inp, attention_mask=att).last_hidden_state

        active_mask = (lbl[:, 1:] != -100)
        active_indices = torch.nonzero(active_mask.view(-1), as_tuple=True)[0]
        if len(active_indices) == 0:
            continue

        shift_hidden = hidden[:, :-1, :].contiguous().view(-1, hidden.size(-1))[active_indices]
        shift_labels = lbl[:, 1:].contiguous().view(-1)[active_indices]

        total_active = len(active_indices)
        chunk_size = 48
        accum_item_loss = 0.0

        for s_idx in range(0, total_active, chunk_size):
            e_idx = min(s_idx + chunk_size, total_active)
            chunk_h = shift_hidden[s_idx:e_idx]
            chunk_l = shift_labels[s_idx:e_idx]
            chunk_logits = model.base_model.lm_head(chunk_h)
            c_loss = torch.nn.functional.cross_entropy(chunk_logits, chunk_l, reduction="sum")
            loss_chunk = c_loss / total_active
            (loss_chunk / grad_accum).backward(retain_graph=(e_idx < total_active))
            accum_item_loss += c_loss.item()

        item_loss = accum_item_loss / total_active
        step_loss += item_loss
        accum_count += 1

        del hidden, shift_hidden, shift_labels

        if accum_count % grad_accum == 0:
            optimizer.step()
            optimizer.zero_grad()
            gc.collect()
            global_step += 1
            avg_loss = step_loss / grad_accum
            print(f"  [Smoke Step {global_step:02d}/{max_steps}] Loss: {avg_loss:.4f} (Active Tokens: {total_active})", flush=True)
            step_loss = 0.0

    total_time = time.time() - t0
    print(f"\n[*] Smoke Training Finished in {total_time:.1f}s!")

    print(f"[*] Saving Smoke LoRA checkpoint to: {best_ckpt_dir}...")
    cpu_sd = {k: v.cpu() for k, v in model.state_dict().items() if "lora_" in k}
    model.save_pretrained(best_ckpt_dir, state_dict=cpu_sd, safe_serialization=False)
    tokenizer.save_pretrained(best_ckpt_dir)

    log_path = os.path.join(output_dir, "smoke_training_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "status": "COMPLETED",
            "global_steps": global_step,
            "training_time_s": round(total_time, 1),
            "final_loss": round(avg_loss, 4),
            "checkpoint_dir": best_ckpt_dir
        }, f, indent=2)

    print(f"[PASS] Smoke adapter ready for behavioral testing at: {best_ckpt_dir}")


if __name__ == "__main__":
    train_v10_2_smoke(max_steps=40, lr=1.5e-4, grad_accum=2)
