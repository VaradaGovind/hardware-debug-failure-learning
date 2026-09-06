#!/usr/bin/env python3
"""
scripts/train_v10_2_agentic_lora.py

Executes full controlled SFT for Experiment V10.2:
- Per-turn trajectory segment supervision (Type A, Type B, Type C).
- Target-preserving ChatML formatting (100% supervision on assistant responses).
- 66.7% tool-call targets, 33.3% conclude targets.
- DirectML GPU acceleration with chunked active-token projection.
- Safe serialization on CPU to prevent OpaqueTensorImpl errors.
"""

import os
import sys
import gc
import json
import time
import math
import random
import argparse
from typing import Dict, Any, List, Optional

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)


def format_per_turn_example(tokenizer, example: Dict[str, Any], max_length: int = 1024):
    """
    Formats a single per-turn conversation example into ChatML format,
    masking system, user, and tool header tokens with -100 so loss is computed
    strictly and completely on the assistant target tokens.
    Target completion is ALWAYS 100% preserved.
    """
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


def compute_eval_loss(model, val_dataset, device, max_eval_samples: int = 40) -> float:
    """Computes average loss on validation subset using chunked active-token cross-entropy."""
    import torch
    model.eval()
    total_loss = 0.0
    count = 0
    eval_subset = val_dataset[:max_eval_samples] if max_eval_samples > 0 else val_dataset

    with torch.no_grad():
        for item in eval_subset:
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
            chunk_size = 64
            item_loss = 0.0

            for s_idx in range(0, total_active, chunk_size):
                e_idx = min(s_idx + chunk_size, total_active)
                chunk_h = shift_hidden[s_idx:e_idx]
                chunk_l = shift_labels[s_idx:e_idx]
                chunk_logits = model.base_model.lm_head(chunk_h)
                c_loss = torch.nn.functional.cross_entropy(chunk_logits, chunk_l, reduction="sum")
                item_loss += c_loss.item()

            del hidden, shift_hidden, shift_labels
            avg_item_loss = item_loss / total_active
            if not math.isnan(avg_item_loss):
                total_loss += avg_item_loss
                count += 1

    model.train()
    gc.collect()
    return (total_loss / count) if count > 0 else float("inf")


def get_cosine_schedule_with_warmup(optimizer, num_warmup_steps: int, num_training_steps: int):
    from torch.optim.lr_scheduler import LambdaLR

    def lr_lambda(current_step: int):
        if current_step < num_warmup_steps:
            return float(current_step) / float(max(1, num_warmup_steps))
        progress = float(current_step - num_warmup_steps) / float(max(1, num_training_steps - num_warmup_steps))
        return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))

    return LambdaLR(optimizer, lr_lambda)


def train_v10_2_agentic_model(epochs: int = 2, lr: float = 1.0e-4, grad_accum: int = 4, max_seq_len: int = 896):
    gc.collect()

    print("=" * 96)
    print("EXPERIMENT V10.2: TRAINING PER-TURN AGENTIC SFT MODEL")
    print("=" * 96)

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

    train_path = os.path.join(WORKSPACE_ROOT, "datasets", "v10_2", "per_turn_train_v10_2.json")
    val_path = os.path.join(WORKSPACE_ROOT, "datasets", "v10_2", "per_turn_val_v10_2.json")
    
    output_dir = "C:/Users/varad/ml-cache/rca-reuse/v10_2/checkpoints/v10_2_agentic_lora"
    best_ckpt_dir = os.path.join(output_dir, "best_v10_2_checkpoint")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(best_ckpt_dir, exist_ok=True)

    base_model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct"

    print(f"\n[Step 1/5] Loading Tokenizer & Base Model ({base_model_name}) in {dtype}...")
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

    print("\n[Step 2/5] Initializing LoRA Adapter [q_proj, v_proj] (r=16, alpha=32)...")
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

    print(f"\n[Step 3/5] Loading & Tokenizing Datasets (max_length={max_seq_len})...")
    with open(train_path, "r", encoding="utf-8") as f:
        raw_train = json.load(f)
    with open(val_path, "r", encoding="utf-8") as f:
        raw_val = json.load(f)

    tokenized_train = []
    for ex in raw_train:
        item = format_per_turn_example(tokenizer, ex, max_length=max_seq_len)
        if item is not None:
            tokenized_train.append(item)

    tokenized_val = []
    for ex in raw_val:
        item = format_per_turn_example(tokenizer, ex, max_length=max_seq_len)
        if item is not None:
            tokenized_val.append(item)

    print(f"  Usable Train Per-Turn Examples: {len(tokenized_train)} / {len(raw_train)}")
    print(f"  Usable Val Per-Turn Examples:   {len(tokenized_val)} / {len(raw_val)}")

    total_steps = (len(tokenized_train) // grad_accum) * epochs
    warmup_steps = int(total_steps * 0.05)

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=lr,
        weight_decay=0.01
    )
    scheduler = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps)

    print(f"\n[Step 4/5] Executing LoRA Fine-Tuning Loop...")
    print(f"  Total Optimization Steps: {total_steps} (Warmup: {warmup_steps})")
    print(f"  Gradient Accumulation:    {grad_accum}")
    print(f"  Learning Rate:            {lr}")
    print(f"  Epochs:                   {epochs}")

    training_log = []
    best_val_loss = float("inf")
    global_step = 0
    t_train_start = time.time()

    model.train()

    for epoch in range(1, epochs + 1):
        random.shuffle(tokenized_train)
        epoch_loss = 0.0
        accum_loss = 0.0
        optimizer.zero_grad()
        t_epoch_start = time.time()

        for idx, item in enumerate(tokenized_train):
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

            del hidden, shift_hidden, shift_labels
            avg_loss_item = accum_item_loss / total_active
            epoch_loss += avg_loss_item
            accum_loss += avg_loss_item

            if (idx + 1) % grad_accum == 0 or (idx + 1) == len(tokenized_train):
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                gc.collect()
                global_step += 1

                if global_step % 10 == 0 or global_step == 1:
                    avg_step_loss = accum_loss / grad_accum
                    current_lr = scheduler.get_last_lr()[0]
                    print(f"  [Epoch {epoch}/{epochs} | Step {global_step:03d}/{total_steps}] Loss: {avg_step_loss:.4f} | LR: {current_lr:.2e}", flush=True)
                    accum_loss = 0.0

        # Validation evaluation at end of epoch
        epoch_time = time.time() - t_epoch_start
        val_loss = compute_eval_loss(model, tokenized_val, device, max_eval_samples=40)
        avg_train_loss = epoch_loss / len(tokenized_train)
        print(f"\n>>> [Epoch {epoch}/{epochs} Finished in {epoch_time:.1f}s] Avg Train Loss: {avg_train_loss:.4f} | Val Loss: {val_loss:.4f} <<<\n", flush=True)

        training_log.append({
            "epoch": epoch,
            "global_step": global_step,
            "train_loss": round(avg_train_loss, 4),
            "val_loss": round(val_loss, 4),
            "epoch_time_s": round(epoch_time, 1)
        })

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            print(f"  [*] Saving new best V10.2 LoRA checkpoint (Val Loss: {val_loss:.4f}) to: {best_ckpt_dir}", flush=True)
            cpu_sd = {k: v.cpu() for k, v in model.state_dict().items() if "lora_" in k}
            model.save_pretrained(best_ckpt_dir, state_dict=cpu_sd, safe_serialization=False)
            tokenizer.save_pretrained(best_ckpt_dir)

    total_training_time = time.time() - t_train_start
    print(f"\n[Step 5/5] Training Completed in {total_training_time:.1f}s! Best Validation Loss: {best_val_loss:.4f}", flush=True)

    telemetry = {
        "status": "COMPLETED",
        "total_steps": global_step,
        "best_val_loss": best_val_loss,
        "total_time_seconds": round(total_training_time, 1),
        "learning_rate": lr,
        "epochs": epochs,
        "grad_accum": grad_accum,
        "max_seq_len": max_seq_len,
        "checkpoint_dir": best_ckpt_dir,
        "training_history": training_log
    }

    log_path = os.path.join(output_dir, "v10_2_training_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)

    reports_log = os.path.join(WORKSPACE_ROOT, "results", "reports", "v10_2_training_telemetry.json")
    with open(reports_log, "w", encoding="utf-8") as f:
        json.dump(telemetry, f, indent=2)

    print(f"[PASS] Model checkpoint and training telemetry saved to: {output_dir}", flush=True)
    return best_val_loss


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train V10.2 Per-Turn Agentic LoRA Model")
    parser.add_argument("--epochs", type=int, default=2)
    parser.add_argument("--lr", type=float, default=1.0e-4)
    parser.add_argument("--grad_accum", type=int, default=4)
    parser.add_argument("--max_seq_len", type=int, default=896)
    args = parser.parse_args()

    train_v10_2_agentic_model(
        epochs=args.epochs,
        lr=args.lr,
        grad_accum=args.grad_accum,
        max_seq_len=args.max_seq_len
    )
