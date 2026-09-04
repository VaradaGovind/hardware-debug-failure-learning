import os
import sys
import time
import json
import argparse
from typing import Dict, Any

WORKSPACE_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if WORKSPACE_ROOT not in sys.path:
    sys.path.insert(0, WORKSPACE_ROOT)


def run_gpu_smoke_test(device_index: int = 0, num_steps: int = 5) -> Dict[str, Any]:
    print("=" * 80)
    print("V7 GPU FINE-TUNING FEASIBILITY SMOKE TEST")
    print("=" * 80)

    t_start = time.time()
    report = {
        "status": "FAILED",
        "backend": "UNKNOWN",
        "device_name": "UNKNOWN",
        "device_type": "UNKNOWN",
        "pytorch_version": "",
        "directml_available": False,
        "cuda_available": False,
        "rocm_available": False,
        "device_count": 0,
        "selected_device": "",
        "tensor_devices": {},
        "training_steps": [],
        "avg_step_latency_ms": 0.0,
        "vram_allocated_mb": 0.0,
        "gradient_verification": False,
        "error": None
    }

    try:
        import torch
        report["pytorch_version"] = torch.__version__
        report["cuda_available"] = torch.cuda.is_available()
        report["rocm_available"] = getattr(torch.version, "hip", None) is not None

        # 1. Detect Acceleration Backend
        backend_name = "CPU"
        device = torch.device("cpu")

        try:
            import torch_directml
            dml_count = torch_directml.device_count()
            report["directml_available"] = True
            report["device_count"] = dml_count
            print(f"[Backend Check] torch_directml is available with {dml_count} device(s).")
            
            if dml_count > 0:
                selected_idx = min(device_index, dml_count - 1)
                device = torch_directml.device(selected_idx)
                backend_name = "DirectML"
                report["device_name"] = torch_directml.device_name(selected_idx) if hasattr(torch_directml, "device_name") else f"DirectML_Device_{selected_idx}"
                report["selected_device"] = str(device)
        except ImportError:
            print("[Backend Check] torch_directml is not installed.")

        if backend_name == "CPU" and torch.cuda.is_available():
            backend_name = "CUDA/ROCm"
            device = torch.device(f"cuda:{device_index}")
            report["device_name"] = torch.cuda.get_device_name(device_index)
            report["selected_device"] = str(device)

        report["backend"] = backend_name
        report["device_type"] = device.type if hasattr(device, "type") else str(device)

        print(f"[Device Selected] Backend: {backend_name} | Device: {device} | Name: {report['device_name']}")

        # 2. Load Model & Tokenizer
        from transformers import AutoModelForCausalLM, AutoTokenizer
        from peft import LoraConfig, get_peft_model, TaskType

        model_name = "Qwen/Qwen2.5-Coder-1.5B-Instruct"
        print(f"\n[Step 1/5] Loading Tokenizer & Model: {model_name}...")
        t0 = time.time()
        tokenizer = AutoTokenizer.from_pretrained(model_name, trust_remote_code=True)
        if tokenizer.pad_token is None:
            tokenizer.pad_token = tokenizer.eos_token

        # Load in float16 to conserve VRAM (3.12 GB weights vs 6.24 GB in fp32)
        dtype = torch.float16
        base_model = AutoModelForCausalLM.from_pretrained(
            model_name,
            torch_dtype=dtype,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )
        print(f"  Base model loaded in {time.time() - t0:.2f}s.")

        # 3. Apply PEFT / LoRA
        print("\n[Step 2/5] Creating LoRA Adapter...")
        lora_config = LoraConfig(
            task_type=TaskType.CAUSAL_LM,
            r=16,
            lora_alpha=32,
            lora_dropout=0.05,
            target_modules=["q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj"],
            bias="none"
        )
        model = get_peft_model(base_model, lora_config)
        trainable_params, all_params = model.get_nb_trainable_parameters()
        print(f"  Trainable Parameters: {trainable_params:,} / {all_params:,} ({100 * trainable_params / all_params:.2f}%)")

        # 4. Move Model to Target Device
        print(f"\n[Step 3/5] Transferring Model to Target Device: {device}...")
        t_transfer = time.time()
        model.to(device)
        print(f"  Model successfully transferred to {device} in {time.time() - t_transfer:.2f}s.")

        # Check parameter device placements
        base_param_device = next(model.base_model.parameters()).device
        lora_param_device = next(p for n, p in model.named_parameters() if "lora_" in n and p.requires_grad).device
        report["tensor_devices"]["base_param_device"] = str(base_param_device)
        report["tensor_devices"]["lora_param_device"] = str(lora_param_device)
        print(f"  Base Parameter Device: {base_param_device}")
        print(f"  LoRA Parameter Device: {lora_param_device}")

        # 5. Optimizer Setup
        optimizer = torch.optim.AdamW(model.parameters(), lr=1e-4)

        # 6. Execute Forward & Backward Steps
        print(f"\n[Step 4/5] Executing {num_steps} Forward & Backward Training Steps on {device}...")
        dummy_prompt = "Module: fifo. Failure: assertion violation on empty signal. Candidate signals: [count, read_ptr, write_ptr]."
        dummy_target = '{"suspected_root_cause": "count", "candidate_signal": "count", "confidence": 0.95}'
        
        # Tokenize
        prompt_ids = tokenizer.encode(dummy_prompt, add_special_tokens=True)
        target_ids = tokenizer.encode(dummy_target, add_special_tokens=False) + [tokenizer.eos_token_id]
        full_ids = prompt_ids + target_ids
        labels = [-100] * len(prompt_ids) + target_ids

        input_ids_tensor = torch.tensor([full_ids], dtype=torch.long, device=device)
        labels_tensor = torch.tensor([labels], dtype=torch.long, device=device)
        attn_mask = torch.tensor([[1] * len(full_ids)], dtype=torch.long, device=device)

        report["tensor_devices"]["input_ids_device"] = str(input_ids_tensor.device)
        report["tensor_devices"]["labels_device"] = str(labels_tensor.device)

        step_latencies = []
        model.train()

        for step in range(1, num_steps + 1):
            t_s = time.time()
            optimizer.zero_grad()

            outputs = model(input_ids=input_ids_tensor, attention_mask=attn_mask, labels=labels_tensor)
            loss = outputs.loss

            if step == 1:
                report["tensor_devices"]["loss_device"] = str(loss.device)
                print(f"  Step 1 Loss Device: {loss.device} | Loss Value: {loss.item():.4f}")

            loss.backward()

            if step == 1:
                # Inspect gradients
                first_grad = next(p.grad for n, p in model.named_parameters() if "lora_" in n and p.requires_grad and p.grad is not None)
                report["tensor_devices"]["gradient_device"] = str(first_grad.device)
                grad_norm = first_grad.norm().item()
                report["gradient_verification"] = (first_grad.device == device and not torch.isnan(first_grad).any().item())
                print(f"  Step 1 Gradient Device: {first_grad.device} | First LoRA Grad Norm: {grad_norm:.6f}")

            optimizer.step()
            step_ms = (time.time() - t_s) * 1000.0
            step_latencies.append(step_ms)
            print(f"  Step {step:>2d}/{num_steps} Completed | Loss: {loss.item():.4f} | Latency: {step_ms:.1f} ms")
            report["training_steps"].append({
                "step": step,
                "loss": loss.item(),
                "latency_ms": step_ms
            })

        avg_latency = sum(step_latencies) / len(step_latencies)
        report["avg_step_latency_ms"] = avg_latency
        print(f"\n[Step 5/5] Smoke Test Finished! Average Step Latency: {avg_latency:.1f} ms")

        # 7. Confirm True GPU Execution
        is_gpu_training = (
            backend_name in ["DirectML", "CUDA/ROCm"] and
            str(device) != "cpu" and
            report["tensor_devices"]["lora_param_device"] != "cpu" and
            report["tensor_devices"]["gradient_device"] != "cpu" and
            report["gradient_verification"] is True
        )

        if is_gpu_training:
            report["status"] = "SUCCESS_GPU_TRAINING_CONFIRMED"
            print("\n" + "=" * 80)
            print(">>> RESULT: TRUE GPU TRAINING CONFIRMED! <<<")
            print(f"    Backend:         {backend_name}")
            print(f"    Target Device:   {report['device_name']} ({device})")
            print(f"    Model Device:    {report['tensor_devices']['base_param_device']}")
            print(f"    LoRA Device:     {report['tensor_devices']['lora_param_device']}")
            print(f"    Gradient Device: {report['tensor_devices']['gradient_device']}")
            print(f"    Step Latency:    {avg_latency:.1f} ms / forward+backward step")
            print("=" * 80)
        else:
            report["status"] = "FALLBACK_CPU_ONLY"
            print("\n" + "=" * 80)
            print(">>> RESULT: FALLBACK CPU TRAINING (GPU NOT ACTIVE) <<<")
            print("=" * 80)

    except Exception as e:
        import traceback
        report["status"] = "FAILED"
        report["error"] = str(e)
        report["traceback"] = traceback.format_exc()
        print(f"\n[ERROR] GPU Smoke Test Failed with exception:\n{traceback.format_exc()}")

    cache_root = os.environ.get("RCA_REUSE_CACHE_DIR", os.path.expanduser("~/.cache/rca-reuse"))
    out_dir = os.path.join(cache_root, "v7", "reports")
    os.makedirs(out_dir, exist_ok=True)
    out_file = os.path.join(out_dir, "gpu_smoke_test_report.json")
    with open(out_file, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=2)
    print(f"\nSmoke test report saved to: {out_file}")

    return report


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="V7 GPU Training Smoke Test")
    parser.add_argument("--device-index", type=int, default=0, help="DirectML / GPU Device Index")
    parser.add_argument("--steps", type=int, default=5, help="Number of training steps")
    args = parser.parse_args()

    run_gpu_smoke_test(device_index=args.device_index, num_steps=args.steps)
