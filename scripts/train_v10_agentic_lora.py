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


def format_multiturn_chatml_example(tokenizer, example: Dict[str, Any], max_length: int = 768):
    """
    Formats a multi-turn conversation into ChatML format,
    masking system, user, and tool output tokens with -100 so loss is computed
    strictly on assistant tokens across all turns.
    """
    convs = example.get("conversations", [])
    if len(convs) < 3:
        return None

    full_ids = []
    labels = []

    for turn in convs:
        role = turn.get("role", "")
        val = str(turn.get("value", ""))

        if role == "system":
            turn_text = f"<|im_start|>system\n{val}<|im_end|>\n"
            turn_ids = tokenizer.encode(turn_text, add_special_tokens=False)
            full_ids.extend(turn_ids)
            labels.extend([-100] * len(turn_ids))

        elif role == "user":
            turn_text = f"<|im_start|>user\n{val}<|im_end|>\n"
            turn_ids = tokenizer.encode(turn_text, add_special_tokens=False)
            full_ids.extend(turn_ids)
            labels.extend([-100] * len(turn_ids))

        elif role == "assistant":
            header_text = "<|im_start|>assistant\n"
            header_ids = tokenizer.encode(header_text, add_special_tokens=False)
            content_text = f"{val}<|im_end|>\n"
            content_ids = tokenizer.encode(content_text, add_special_tokens=False)

            full_ids.extend(header_ids)
            labels.extend([-100] * len(header_ids))

            full_ids.extend(content_ids)
            labels.extend(content_ids)

    # Truncate if exceeding max_length while preserving header and conclusion
    if len(full_ids) > max_length:
        head_len = min(120, max_length // 4)
        tail_len = max_length - head_len
        full_ids = full_ids[:head_len] + full_ids[-tail_len:]
        labels = labels[:head_len] + labels[-tail_len:]

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

            avg_item_loss = item_loss / total_active
            if not math.isnan(avg_item_loss):
                total_loss += avg_item_loss
                count += 1

    model.train()
    return (total_loss / count) if count > 0 else float("inf")


def get_cosine_schedule_with_warmup(optimizer, num_warmup_steps: int, num_training_steps: int):
    from torch.optim.lr_scheduler import LambdaLR

    def lr_lambda(current_step: int):
        if current_step < num_warmup_steps:
            return float(current_step) / float(max(1, num_warmup_steps))
        progress = float(current_step - num_warmup_steps) / float(max(1, num_training_steps - num_warmup_steps))
        return max(0.0, 0.5 * (1.0 + math.cos(math.pi * progress)))

    return LambdaLR(optimizer, lr_lambda)


def train_v10_model(condition: str = "model_b", epochs: int = 3, lr: float = 2.0e-4, grad_accum: int = 4):
    """
    Executes controlled SFT on AMD DirectML GPU:
    - 'model_a': Generic Agentic SFT (Hard negatives excluded)
    - 'model_b': Topology-Generalized Agentic SFT (Full topology-disjoint dataset + hard negatives + UNKNOWNs)
    """
    gc.collect()

    print("=" * 96)
    print(f"EXPERIMENT V10: TRAINING {'MODEL A (Generic Agentic SFT)' if condition == 'model_a' else 'MODEL B (Topology-Generalized SFT)'}")
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

    train_path = "C:/Users/varad/ml-cache/rca-reuse/v10/datasets/agentic_train_v10.json"
    val_path = "C:/Users/varad/ml-cache/rca-reuse/v10/datasets/agentic_val_v10.json"
    
    if condition == "model_a":
        output_dir = "C:/Users/varad/ml-cache/rca-reuse/v10/checkpoints/v10_model_a_generic_lora"
    else:
        output_dir = "C:/Users/varad/ml-cache/rca-reuse/v10/checkpoints/v10_model_b_topological_lora"

    best_ckpt_dir = os.path.join(output_dir, "best_v10_checkpoint")
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

    print("\n[Step 3/5] Loading & Tokenizing Dataset...")
    with open(train_path, "r", encoding="utf-8") as f:
        raw_train = json.load(f)
    with open(val_path, "r", encoding="utf-8") as f:
        raw_val = json.load(f)

    if condition == "model_a":
        raw_train = [e for e in raw_train if e.get("example_type") != "HARD_NEGATIVE"]

    tokenized_train = []
    for ex in raw_train:
        item = format_multiturn_chatml_example(tokenizer, ex, max_length=768)
        if item is not None:
            tokenized_train.append(item)

    tokenized_val = []
    for ex in raw_val:
        item = format_multiturn_chatml_example(tokenizer, ex, max_length=768)
        if item is not None:
            tokenized_val.append(item)

    print(f"  Usable Train Trajectories: {len(tokenized_train)} / {len(raw_train)}")
    print(f"  Usable Val Trajectories:   {len(tokenized_val)} / {len(raw_val)}")

    total_steps = (len(tokenized_train) // grad_accum) * epochs
    warmup_steps = int(total_steps * 0.05)

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=lr,
        weight_decay=0.01
    )
    scheduler = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps)

    print("\n[Step 4/5] Executing LoRA Fine-Tuning Loop...")
    print(f"  Total Steps: {total_steps} (Warmup: {warmup_steps})")
    print(f"  Grad Accumulation: {grad_accum}")

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
            item_loss = 0.0

            for s_idx in range(0, total_active, chunk_size):
                e_idx = min(s_idx + chunk_size, total_active)
                chunk_h = shift_hidden[s_idx:e_idx]
                chunk_l = shift_labels[s_idx:e_idx]
                chunk_logits = model.base_model.lm_head(chunk_h)
                c_loss = torch.nn.functional.cross_entropy(chunk_logits, chunk_l, reduction="sum")
                
                loss_scaled = c_loss / (total_active * grad_accum)
                loss_scaled.backward(retain_graph=(e_idx < total_active))
                item_loss += c_loss.item() / total_active

            accum_loss += item_loss
            epoch_loss += item_loss

            if (idx + 1) % grad_accum == 0 or (idx + 1) == len(tokenized_train):
                torch.nn.utils.clip_grad_norm_(model.parameters(), max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                global_step += 1

                if global_step % 20 == 0 or global_step == 1:
                    step_time = time.time() - t_train_start
                    print(f"  [Epoch {epoch}/{epochs} | Step {global_step:>4d}/{total_steps}] Train Loss: {accum_loss/grad_accum:.4f} | Elapsed: {step_time:.1f}s", flush=True)

                accum_loss = 0.0

        # End of Epoch Validation Evaluation
        epoch_time = time.time() - t_epoch_start
        val_loss = compute_eval_loss(model, tokenized_val, device, max_eval_samples=35)
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
            print(f"  [*] Saving new best V10 LoRA checkpoint (Val Loss: {val_loss:.4f}) to: {best_ckpt_dir}", flush=True)
            cpu_sd = {k: v.cpu() for k, v in model.state_dict().items() if "lora_" in k}
            model.save_pretrained(best_ckpt_dir, state_dict=cpu_sd, safe_serialization=False)
            tokenizer.save_pretrained(best_ckpt_dir)

    total_training_time = time.time() - t_train_start
    print(f"\n[Step 5/5] Training Completed in {total_training_time:.1f}s! Best Validation Loss: {best_val_loss:.4f}", flush=True)

    log_path = os.path.join(output_dir, "v10_training_log.json")
    with open(log_path, "w", encoding="utf-8") as f:
        json.dump({
            "condition": condition,
            "total_steps": total_steps,
            "best_val_loss": best_val_loss,
            "total_time_seconds": total_training_time,
            "training_history": training_log
        }, f, indent=2)

    print(f"[PASS] Model checkpoint and training telemetry saved to: {output_dir}", flush=True)
    return best_val_loss


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Train V10 LoRA Model")
    parser.add_argument("--condition", type=str, default="model_b", choices=["model_a", "model_b"])
    parser.add_argument("--epochs", type=int, default=3)
    parser.add_argument("--lr", type=float, default=2.0e-4)
    parser.add_argument("--grad_accum", type=int, default=4)
    args = parser.parse_args()

    train_v10_model(condition=args.condition, epochs=args.epochs, lr=args.lr, grad_accum=args.grad_accum)
