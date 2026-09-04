import os
import sys
import json
import time
import math
import yaml
import random
import psutil
import argparse
from typing import Dict, Any, List, Optional, Tuple

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)


def format_chatml_example(tokenizer, example: Dict[str, Any], max_length: int = 768):
    """
    Formats a single conversation example using Qwen2.5 ChatML format
    and builds input_ids and labels, ensuring assistant target tokens are ALWAYS preserved.
    """
    convs = example.get("conversations", [])
    if len(convs) < 3:
        return None

    system_text = convs[0]["value"]
    human_text = convs[1]["value"]
    target_text = convs[2]["value"]

    # Target tokenization
    target_ids = tokenizer.encode(target_text, add_special_tokens=False)
    if not target_text.endswith(tokenizer.eos_token):
        target_ids.append(tokenizer.eos_token_id)

    # Prompt tokenization (System + User)
    prompt_messages = [
        {"role": "system", "content": system_text},
        {"role": "user", "content": human_text}
    ]
    prompt_text = tokenizer.apply_chat_template(prompt_messages, tokenize=False, add_generation_prompt=True)
    prompt_ids = tokenizer.encode(prompt_text, add_special_tokens=False)

    # Truncate prompt from start/middle if total exceeds max_length, ALWAYS preserving target
    max_prompt_len = max_length - len(target_ids) - 4
    if len(prompt_ids) > max_prompt_len:
        # Keep first 200 tokens (system instructions) and tail tokens (candidate list and question)
        head_len = min(180, max_prompt_len // 3)
        tail_len = max_prompt_len - head_len
        prompt_ids = prompt_ids[:head_len] + prompt_ids[-tail_len:]

    full_ids = prompt_ids + target_ids
    labels = [-100] * len(prompt_ids) + target_ids

    prompt_len = len(prompt_ids)
    target_len = len(target_ids)

    # Safety assertion: Must have active target tokens for loss computation
    active_tokens = sum(1 for l in labels if l != -100)
    if active_tokens < 5:
        return None

    return {
        "input_ids": full_ids,
        "labels": labels,
        "attention_mask": [1] * len(full_ids),
        "prompt_len": prompt_len,
        "target_len": target_len
    }


def compute_eval_loss(model, val_dataset, device, max_eval_samples: int = 50) -> float:
    """Computes average loss on validation subset using active-token loss."""
    import torch
    model.eval()
    total_loss = 0.0
    count = 0
    eval_subset = val_dataset[:max_eval_samples] if max_eval_samples > 0 else val_dataset

    with torch.no_grad():
        for item in eval_subset:
            p_len = item["prompt_len"]
            t_len = item["target_len"]
            inp = torch.tensor([item["input_ids"]], dtype=torch.long, device=device)
            att = torch.tensor([item["attention_mask"]], dtype=torch.long, device=device)
            lbl = torch.tensor([item["labels"]], dtype=torch.long, device=device)

            hidden_states = model.base_model.model.model(input_ids=inp, attention_mask=att).last_hidden_state
            active_hidden = hidden_states[:, (p_len - 1) : (p_len + t_len - 1), :]
            active_labels = lbl[:, p_len:]
            active_logits = model.base_model.lm_head(active_hidden)

            loss = torch.nn.functional.cross_entropy(
                active_logits.view(-1, active_logits.size(-1)),
                active_labels.view(-1)
            )
            if not torch.isnan(loss):
                total_loss += loss.item()
                count += 1

    model.train()
    return (total_loss / count) if count > 0 else 0.0


def main():
    parser = argparse.ArgumentParser(description="V7 Domain-Specific LoRA Fine-Tuning on DirectML GPU")
    parser.add_argument("--config", default="training/configs/soup_v7_qwen_lora.yaml", help="Path to config YAML")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=2.5e-4, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=1, help="Per device batch size")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--max-seq-len", type=int, default=768, help="Max sequence length")
    parser.add_argument("--max-train-samples", type=int, default=-1, help="Max train samples for ablation/speed")
    parser.add_argument("--device-idx", type=int, default=0, help="DirectML device index")
    parser.add_argument("--ablation", default=None, choices=[None, "no_hard_negatives", "no_unknown"], help="Ablation mode")
    parser.add_argument("--output-suffix", default="", help="Suffix for checkpoint dir")

    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup
    from peft import LoraConfig, get_peft_model, TaskType

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    model_name = cfg["model"]["name_or_path"]
    train_path = cfg["data"]["train_file"]
    val_path = cfg["data"]["val_file"]
    base_out_dir = cfg["training"]["output_dir"]
    if args.output_suffix:
        base_out_dir = f"{base_out_dir}_{args.output_suffix}"
    best_ckpt_dir = os.path.join(base_out_dir, "best_v7_checkpoint")
    os.makedirs(base_out_dir, exist_ok=True)
    os.makedirs(best_ckpt_dir, exist_ok=True)

    # 1. Device Selection
    device = torch.device("cpu")
    backend_name = "CPU"
    device_name = "CPU"

    try:
        import torch_directml
        if torch_directml.device_count() > 0:
            device = torch_directml.device(args.device_idx)
            backend_name = "DirectML"
            device_name = torch_directml.device_name(args.device_idx) if hasattr(torch_directml, "device_name") else f"DirectML_{args.device_idx}"
    except Exception:
        pass

    if backend_name == "CPU" and torch.cuda.is_available():
        device = torch.device(f"cuda:{args.device_idx}")
        backend_name = "CUDA"
        device_name = torch.cuda.get_device_name(args.device_idx)

    print("=" * 96)
    print("V7 HARDWARE AGENTIC RCA: LORA FINE-TUNING PIPELINE (DirectML GPU Accelerated)")
    print("=" * 96)
    print(f"Base Model:             {model_name}")
    print(f"PyTorch Version:        {torch.__version__}")
    print(f"Compute Backend:        {backend_name} ({device_name})")
    print(f"Target Device:          {device}")
    print(f"Train Dataset:          {train_path}")
    print(f"Validation Dataset:     {val_path}")
    print(f"Ablation Mode:          {args.ablation or 'FULL_V7'}")
    print(f"Output Checkpoint:      {best_ckpt_dir}")
    print(f"Epochs:                 {args.epochs}")
    print(f"Learning Rate:          {args.lr}")
    print(f"Effective Batch Size:   {args.batch_size * args.grad_accum}")
    print(f"Sequence Length Cap:    {args.max_seq_len}")
    print("=" * 96)

    # 2. Load Tokenizer & Base Model
    print("\n[Step 1/5] Loading Tokenizer and Base Model in FP16...")
    t0 = time.time()
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.float16 if backend_name in ["DirectML", "CUDA"] else torch.float32
    base_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=dtype,
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )
    print(f"  Base model loaded in {time.time() - t0:.2f}s.")

    # 3. Configure LoRA (Targeting attention projections q_proj, v_proj for optimal GPU activation fit)
    print("\n[Step 2/5] Creating LoRA Adapter...")
    lora_config = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=16,
        lora_alpha=32,
        lora_dropout=0.05,
        target_modules=["q_proj", "v_proj"],
        bias="none"
    )
    model = get_peft_model(base_model, lora_config)
    trainable_params, all_params = model.get_nb_trainable_parameters()
    print(f"  Trainable Parameters: {trainable_params:,} / {all_params:,} ({100 * trainable_params / all_params:.2f}%)")

    # 4. Move Model to Target Device
    print(f"\n[Step 3/5] Transferring Model to Target Device ({device})...")
    t_transfer = time.time()
    model.to(device)
    print(f"  Model transferred to {device} in {time.time() - t_transfer:.2f}s.")

    # 5. Prepare Tokenized Datasets
    print("\n[Step 4/5] Tokenizing & Formatting Datasets...")
    with open(train_path, "r", encoding="utf-8") as f:
        raw_train = json.load(f)
    with open(val_path, "r", encoding="utf-8") as f:
        raw_val = json.load(f)

    # Handle Ablations if specified
    if args.ablation == "no_hard_negatives":
        raw_train = [e for e in raw_train if e.get("example_type") != "HARD_NEGATIVE"]
    elif args.ablation == "no_unknown":
        raw_train = [e for e in raw_train if e.get("example_type") != "UNKNOWN_INSUFFICIENT"]

    if args.max_train_samples > 0:
        raw_train = raw_train[:args.max_train_samples]

    tokenized_train = []
    for ex in raw_train:
        item = format_chatml_example(tokenizer, ex, max_length=args.max_seq_len)
        if item is not None:
            tokenized_train.append(item)

    tokenized_val = []
    for ex in raw_val:
        item = format_chatml_example(tokenizer, ex, max_length=args.max_seq_len)
        if item is not None:
            tokenized_val.append(item)

    print(f"  Usable Tokenized Train Samples: {len(tokenized_train)} / {len(raw_train)}")
    print(f"  Usable Tokenized Val Samples:   {len(tokenized_val)} / {len(raw_val)}")

    # 6. Training Setup
    num_epochs = args.epochs
    grad_accum = args.grad_accum
    total_steps = (len(tokenized_train) // grad_accum) * num_epochs
    warmup_steps = int(total_steps * 0.05)

    optimizer = torch.optim.AdamW(
        [p for p in model.parameters() if p.requires_grad],
        lr=args.lr,
        weight_decay=0.01
    )
    scheduler = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=total_steps)

    print("\n[Step 5/5] Executing LoRA Fine-Tuning Training Loop...")
    print(f"  Total Optimizer Steps: {total_steps} (Warmup: {warmup_steps})")
    print(f"  Gradient Accumulation: {grad_accum}")

    training_log = []
    step_latencies = []
    best_val_loss = float("inf")
    global_step = 0
    t_train_start = time.time()

    model.train()

    for epoch in range(1, num_epochs + 1):
        random.shuffle(tokenized_train)
        epoch_loss = 0.0
        accum_loss = 0.0
        optimizer.zero_grad()
        t_epoch_start = time.time()

        for idx, item in enumerate(tokenized_train):
            t_step_start = time.time()

            p_len = item["prompt_len"]
            t_len = item["target_len"]
            inp = torch.tensor([item["input_ids"]], dtype=torch.long, device=device)
            att = torch.tensor([item["attention_mask"]], dtype=torch.long, device=device)
            lbl = torch.tensor([item["labels"]], dtype=torch.long, device=device)

            # Forward base model
            hidden_states = model.base_model.model.model(input_ids=inp, attention_mask=att).last_hidden_state
            active_hidden = hidden_states[:, (p_len - 1) : (p_len + t_len - 1), :]
            active_labels = lbl[:, p_len:]
            active_logits = model.base_model.lm_head(active_hidden)

            loss = torch.nn.functional.cross_entropy(
                active_logits.view(-1, active_logits.size(-1)),
                active_labels.view(-1)
            ) / grad_accum

            loss.backward()

            step_latency_ms = (time.time() - t_step_start) * 1000.0
            step_latencies.append(step_latency_ms)
            accum_loss += loss.item() * grad_accum
            epoch_loss += loss.item() * grad_accum

            if (idx + 1) % grad_accum == 0 or (idx + 1) == len(tokenized_train):
                torch.nn.utils.clip_grad_norm_([p for p in model.parameters() if p.requires_grad], max_norm=1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                global_step += 1

                if global_step % 25 == 0 or global_step == 1:
                    avg_step_ms = sum(step_latencies[-25:]) / len(step_latencies[-25:])
                    cur_lr = scheduler.get_last_lr()[0]
                    cpu_pct = psutil.cpu_percent()
                    ram_gb = psutil.virtual_memory().used / (1024 ** 3)

                    print(
                        f"  [Epoch {epoch}/{num_epochs} | Step {global_step:>4d}/{total_steps}] "
                        f"Loss: {accum_loss / grad_accum:.4f} | LR: {cur_lr:.2e} | "
                        f"Step: {avg_step_ms:.1f}ms | CPU: {cpu_pct:.1f}% | RAM: {ram_gb:.2f}GB"
                    )
                    training_log.append({
                        "epoch": epoch,
                        "global_step": global_step,
                        "train_loss": accum_loss / grad_accum,
                        "learning_rate": cur_lr,
                        "avg_step_latency_ms": avg_step_ms,
                        "cpu_pct": cpu_pct,
                        "ram_gb": ram_gb
                    })

                accum_loss = 0.0

        # End of Epoch Validation
        avg_train_loss = epoch_loss / len(tokenized_train)
        val_loss = compute_eval_loss(model, tokenized_val, device, max_eval_samples=60)
        epoch_sec = time.time() - t_epoch_start

        print(
            f"\n>>> [Epoch {epoch} Completed in {epoch_sec:.1f}s] "
            f"Avg Train Loss: {avg_train_loss:.4f} | Validation Loss: {val_loss:.4f} <<<\n"
        )

        if val_loss < best_val_loss:
            best_val_loss = val_loss
            print(f"  [*] Saving new best V7 LoRA checkpoint (Val Loss: {val_loss:.4f}) to: {best_ckpt_dir}")
            cpu_sd = {k: v.cpu() for k, v in model.state_dict().items() if "lora_" in k}
            model.save_pretrained(best_ckpt_dir, state_dict=cpu_sd)
            tokenizer.save_pretrained(best_ckpt_dir)

    total_training_sec = time.time() - t_train_start
    overall_avg_step_ms = sum(step_latencies) / len(step_latencies) if step_latencies else 0.0

    print("=" * 96)
    print("V7 LORA TRAINING FINISHED SUCCESSFULLY!")
    print("=" * 96)
    print(f"Total Training Time:    {total_training_sec:.1f}s ({total_training_sec / 60:.2f} min)")
    print(f"Average Step Latency:   {overall_avg_step_ms:.1f} ms / step")
    print(f"Best Validation Loss:   {best_val_loss:.4f}")
    print(f"Final Checkpoint Path:  {best_ckpt_dir}")
    print("=" * 96)

    # Save summary report
    summary = {
        "status": "COMPLETED",
        "model_name": model_name,
        "ablation_mode": args.ablation or "FULL_V7",
        "backend": backend_name,
        "device_name": device_name,
        "total_train_samples": len(tokenized_train),
        "total_val_samples": len(tokenized_val),
        "num_epochs": num_epochs,
        "effective_batch_size": args.batch_size * grad_accum,
        "total_optimizer_steps": total_steps,
        "total_training_sec": total_training_sec,
        "avg_step_latency_ms": overall_avg_step_ms,
        "best_val_loss": best_val_loss,
        "checkpoint_dir": best_ckpt_dir,
        "training_log": training_log
    }

    report_name = f"v7_training_summary_{args.ablation}.json" if args.ablation else "v7_training_summary.json"
    cache_root = os.environ.get("RCA_REUSE_CACHE_DIR", os.path.expanduser("~/.cache/rca-reuse"))
    reports_dir = os.path.join(cache_root, "v7", "reports")
    os.makedirs(reports_dir, exist_ok=True)
    report_out = os.path.join(reports_dir, report_name)
    with open(report_out, "w", encoding="utf-8") as f:
        json.dump(summary, f, indent=2)
    print(f"Training summary saved to: {report_out}")


if __name__ == "__main__":
    main()
