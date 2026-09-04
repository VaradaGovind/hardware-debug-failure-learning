import os
import sys
import json
import time
import math
import yaml
import random
import argparse
from typing import Dict, Any, List, Optional, Tuple

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)


def format_chatml_example(tokenizer, example: Dict[str, Any], max_length: int = 2048):
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

    # Truncate prompt from middle/start if total exceeds max_length, ALWAYS preserving target
    max_prompt_len = max_length - len(target_ids) - 4
    if len(prompt_ids) > max_prompt_len:
        prompt_ids = prompt_ids[:max_prompt_len]

    full_ids = prompt_ids + target_ids
    labels = [-100] * len(prompt_ids) + target_ids

    # Safety assertion: Must have active target tokens for loss computation
    active_tokens = sum(1 for l in labels if l != -100)
    if active_tokens < 5:
        return None

    return {
        "input_ids": full_ids,
        "labels": labels,
        "attention_mask": [1] * len(full_ids)
    }


def main():
    parser = argparse.ArgumentParser(description="V6 Domain-Specific LoRA Fine-Tuning")
    parser.add_argument("--config", default="training/configs/soup_v6_qwen_lora.yaml", help="Path to config YAML")
    parser.add_argument("--epochs", type=int, default=3, help="Number of training epochs")
    parser.add_argument("--lr", type=float, default=2e-4, help="Learning rate")
    parser.add_argument("--batch-size", type=int, default=1, help="Per device batch size")
    parser.add_argument("--grad-accum", type=int, default=4, help="Gradient accumulation steps")
    parser.add_argument("--max-seq-len", type=int, default=2048, help="Max sequence length")
    parser.add_argument("--max-train-samples", type=int, default=-1, help="Max train samples for ablation/speed")

    args = parser.parse_args()

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup
    from peft import LoraConfig, get_peft_model, TaskType

    torch.set_num_threads(8)

    with open(args.config, "r", encoding="utf-8") as f:
        cfg = yaml.safe_load(f)

    model_name = cfg["model"]["name_or_path"]
    train_path = cfg["data"]["train_file"]
    val_path = cfg["data"]["val_file"]
    output_dir = cfg["training"]["output_dir"]
    best_ckpt_dir = os.path.join(output_dir, "best_v6_checkpoint")
    os.makedirs(output_dir, exist_ok=True)
    os.makedirs(best_ckpt_dir, exist_ok=True)

    print("=" * 80)
    print("V6 HARDWARE AGENTIC RCA: LORA FINE-TUNING PIPELINE")
    print("=" * 80)
    print(f"Base Model:             {model_name}")
    print(f"PyTorch Version:        {torch.__version__}")
    print(f"Device:                 {'CUDA' if torch.cuda.is_available() else 'CPU'}")
    print(f"Train Dataset:          {train_path}")
    print(f"Validation Dataset:     {val_path}")
    print(f"Output Checkpoint:      {best_ckpt_dir}")
    print(f"Epochs:                 {args.epochs}")
    print(f"Learning Rate:          {args.lr}")
    print(f"Effective Batch Size:   {args.batch_size * args.grad_accum}")
    print(f"Sequence Length Cap:    {args.max_seq_len}")
    print("=" * 80)

    # 1. Load Tokenizer & Model
    print("\n[Step 1/5] Loading Tokenizer and Base Model...")
    tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    dtype = torch.bfloat16 if torch.cuda.is_available() else torch.float32
    base_model = AutoModelForCausalLM.from_pretrained(
        model_name,
        torch_dtype=dtype,
        trust_remote_code=True,
        low_cpu_mem_usage=True
    )

    # 2. Configure LoRA
    print("\n[Step 2/5] Applying LoRA Adapter...")
    lora_cfg = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=cfg["lora"]["r"],
        lora_alpha=cfg["lora"]["lora_alpha"],
        lora_dropout=cfg["lora"]["lora_dropout"],
        target_modules=cfg["lora"]["target_modules"],
        bias="none"
    )
    model = get_peft_model(base_model, lora_cfg)
    model.print_trainable_parameters()

    # 3. Load Datasets
    print("\n[Step 3/5] Tokenizing & Masking Prompt Tokens...")
    with open(train_path, "r", encoding="utf-8") as f:
        raw_train = json.load(f)
    with open(val_path, "r", encoding="utf-8") as f:
        raw_val = json.load(f)

    if args.max_train_samples > 0:
        # Prioritize diverse examples: hard negatives + UNKNOWN + core positive bugs
        h_negs = [x for x in raw_train if x.get("example_type") == "HARD_NEGATIVE"]
        unks = [x for x in raw_train if x.get("example_type") == "UNKNOWN_INSUFFICIENT"]
        pos = [x for x in raw_train if x.get("example_type") == "POSITIVE_RCA"]
        selected = h_negs + unks + pos[:max(0, args.max_train_samples - len(h_negs) - len(unks))]
        raw_train = selected[:args.max_train_samples]

    train_data = [format_chatml_example(tokenizer, ex, args.max_seq_len) for ex in raw_train]
    train_data = [ex for ex in train_data if ex is not None]

    val_data = [format_chatml_example(tokenizer, ex, args.max_seq_len) for ex in raw_val]
    val_data = [ex for ex in val_data if ex is not None]

    print(f"  Processed {len(train_data)} train samples, {len(val_data)} validation samples.")
    sys.stdout.flush()

    # 4. Setup Optimizer & Scheduler
    optimizer = torch.optim.AdamW(model.parameters(), lr=args.lr, weight_decay=cfg["training"]["weight_decay"])
    total_steps = (len(train_data) // args.grad_accum) * args.epochs
    warmup_steps = max(1, int(total_steps * cfg["training"]["warmup_ratio"]))
    scheduler = get_cosine_schedule_with_warmup(optimizer, num_warmup_steps=warmup_steps, num_training_steps=max(1, total_steps))

    # 5. Training Loop
    print("\n[Step 4/5] Starting LoRA Fine-Tuning...")
    sys.stdout.flush()
    best_val_loss = float("inf")
    training_log = []
    t_start = time.time()

    model.train()
    step_count = 0

    for epoch in range(1, args.epochs + 1):
        print(f"\n--- Epoch {epoch}/{args.epochs} ---")
        epoch_loss = 0.0
        valid_loss_count = 0
        optimizer.zero_grad()

        # Shuffle training data
        random_indices = list(range(len(train_data)))
        random.shuffle(random_indices)
        
        for idx, i in enumerate(random_indices):
            sample = train_data[i]
            input_ids = torch.tensor([sample["input_ids"]], dtype=torch.long)
            labels = torch.tensor([sample["labels"]], dtype=torch.long)
            attn_mask = torch.tensor([sample["attention_mask"]], dtype=torch.long)

            outputs = model(input_ids=input_ids, attention_mask=attn_mask, labels=labels)
            raw_loss = outputs.loss
            
            if raw_loss is None or torch.isnan(raw_loss) or torch.isinf(raw_loss):
                continue

            loss = raw_loss / args.grad_accum
            loss.backward()

            epoch_loss += raw_loss.item()
            valid_loss_count += 1

            if (idx + 1) % args.grad_accum == 0 or (idx + 1) == len(train_data):
                torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
                optimizer.step()
                scheduler.step()
                optimizer.zero_grad()
                step_count += 1

                if step_count % cfg["training"]["logging_steps"] == 0 or step_count == total_steps:
                    lr_curr = scheduler.get_last_lr()[0]
                    curr_loss = raw_loss.item()
                    print(f"  Step {step_count:>4d}/{total_steps} | Loss: {curr_loss:.4f} | LR: {lr_curr:.6f}")
                    sys.stdout.flush()
                    training_log.append({
                        "step": step_count,
                        "epoch": epoch,
                        "train_loss": curr_loss,
                        "learning_rate": lr_curr
                    })

        avg_train_loss = (epoch_loss / valid_loss_count) if valid_loss_count > 0 else 0.0

        # Validation Pass
        model.eval()
        val_loss_sum = 0.0
        val_valid_count = 0
        with torch.no_grad():
            for v_sample in val_data:
                v_ids = torch.tensor([v_sample["input_ids"]], dtype=torch.long)
                v_labels = torch.tensor([v_sample["labels"]], dtype=torch.long)
                v_mask = torch.tensor([v_sample["attention_mask"]], dtype=torch.long)
                v_out = model(input_ids=v_ids, attention_mask=v_mask, labels=v_labels)
                if v_out.loss is not None and not torch.isnan(v_out.loss) and not torch.isinf(v_out.loss):
                    val_loss_sum += v_out.loss.item()
                    val_valid_count += 1
        
        avg_val_loss = (val_loss_sum / val_valid_count) if val_valid_count > 0 else avg_train_loss
        print(f"Epoch {epoch} Complete -> Avg Train Loss: {avg_train_loss:.4f} | Avg Val Loss: {avg_val_loss:.4f}")
        sys.stdout.flush()

        # Checkpoint Saving
        if avg_val_loss < best_val_loss or math.isinf(best_val_loss):
            best_val_loss = avg_val_loss
            model.save_pretrained(best_ckpt_dir)
            tokenizer.save_pretrained(best_ckpt_dir)
            print(f"  >>> Best Checkpoint Saved to: {best_ckpt_dir} (Val Loss: {avg_val_loss:.4f})")
            sys.stdout.flush()

        model.train()

    # Always ensure best checkpoint exists
    if not os.path.exists(os.path.join(best_ckpt_dir, "adapter_model.safetensors")) and not os.path.exists(os.path.join(best_ckpt_dir, "adapter_model.bin")):
        model.save_pretrained(best_ckpt_dir)
        tokenizer.save_pretrained(best_ckpt_dir)

    elapsed_total = time.time() - t_start
    print(f"\n[Step 5/5] Training Complete in {elapsed_total:.1f}s ({elapsed_total/60.0:.1f} min).")
    print(f"Final Model Saved at: {best_ckpt_dir}")

    # Save summary report
    final_report = {
        "status": "TRAINING_COMPLETE",
        "base_model": model_name,
        "epochs": args.epochs,
        "total_steps": total_steps,
        "best_val_loss": best_val_loss,
        "training_time_sec": elapsed_total,
        "checkpoint_dir": best_ckpt_dir,
        "training_log": training_log
    }

    with open(os.path.join(output_dir, "v6_training_summary.json"), "w", encoding="utf-8") as f:
        json.dump(final_report, f, indent=2)

    print(f"Summary written to: {os.path.join(output_dir, 'v6_training_summary.json')}")
    print("=" * 80)
    sys.stdout.flush()


if __name__ == "__main__":
    main()
