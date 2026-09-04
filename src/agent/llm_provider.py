import os
import re
import json
import time
import urllib.request
import urllib.error
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, asdict
from typing import Dict, Any, List, Optional, Tuple


@dataclass
class LLMResponse:
    """Structured response container from LLM generation."""
    text: str
    prompt_tokens: int = -1
    completion_tokens: int = -1
    total_tokens: int = -1
    latency_ms: float = 0.0
    model_name: str = ""
    finish_reason: str = "stop"
    raw_response: Dict[str, Any] = field(default_factory=dict)

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


class LLMProvider(ABC):
    """Abstract interface for LLM inference providers."""

    @abstractmethod
    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.1, max_tokens: int = 512,
                 json_format: bool = False) -> LLMResponse:
        """Executes a text generation query."""
        pass

    @staticmethod
    def _validate_parsed_structure(parsed: Any) -> Tuple[bool, str]:
        """Validates that parsed JSON meets basic hardware RCA schema constraints."""
        if not isinstance(parsed, dict):
            return False, "Output must be a JSON object (dictionary)."
        
        # Validate confidence if present
        if "confidence" in parsed:
            conf = parsed["confidence"]
            if not isinstance(conf, (int, float)) or conf < 0.0 or conf > 1.0:
                return False, f"Field 'confidence' must be a float between 0.0 and 1.0 (got {conf})."

        # Validate action formats if present
        action = parsed.get("action")
        if action == "tool_call":
            if not parsed.get("tool_name") or not isinstance(parsed.get("tool_name"), str):
                return False, "Tool call action requires non-empty string 'tool_name'."
        elif action == "conclude":
            if not parsed.get("candidate_signal"):
                return False, "Conclude action requires a non-empty 'candidate_signal'."

        return True, ""

    def structured_generate(self, prompt: str, system_prompt: Optional[str] = None,
                            temperature: float = 0.1, max_tokens: int = 512,
                            max_retries: int = 2) -> Tuple[Dict[str, Any], LLMResponse]:
        """Generates and parses structured JSON output with a bounded schema-validation repair loop."""
        resp = self.generate(
            prompt=prompt,
            system_prompt=system_prompt,
            temperature=temperature,
            max_tokens=max_tokens,
            json_format=True
        )
        
        parsed = self._extract_and_parse_json(resp.text)
        if parsed is not None:
            is_valid, val_err = self._validate_parsed_structure(parsed)
            if is_valid:
                return parsed, resp
        else:
            val_err = "Output is not valid JSON syntax."

        # Bounded repair retry (maximum 2 retries)
        curr_resp = resp
        for attempt in range(1, max_retries + 1):
            repair_prompt = (
                f"{prompt}\n\n"
                f"[SYSTEM ERROR]: Your previous response was invalid: {val_err}\n"
                f"Previous Response:\n```\n{curr_resp.text}\n```\n"
                f"Please fix the error and output ONLY a valid JSON object matching the required schema."
            )
            curr_resp = self.generate(
                prompt=repair_prompt,
                system_prompt=system_prompt,
                temperature=0.0,
                max_tokens=max_tokens,
                json_format=True
            )
            parsed = self._extract_and_parse_json(curr_resp.text)
            if parsed is not None:
                is_valid, val_err = self._validate_parsed_structure(parsed)
                if is_valid:
                    # Merge token accounting from retries
                    if resp.prompt_tokens >= 0 and curr_resp.prompt_tokens >= 0:
                        curr_resp.prompt_tokens += resp.prompt_tokens
                        curr_resp.completion_tokens += resp.completion_tokens
                        curr_resp.total_tokens = curr_resp.prompt_tokens + curr_resp.completion_tokens
                    curr_resp.latency_ms += resp.latency_ms
                    return parsed, curr_resp

        # Return failure fallback structure if repair exhausted
        fallback_json = {
            "error": "INVALID_OUTPUT",
            "validation_error": val_err,
            "raw_text": curr_resp.text,
            "status": "PARSE_FAILED"
        }
        return fallback_json, curr_resp

    @staticmethod
    def _extract_and_parse_json(text: str) -> Optional[Dict[str, Any]]:
        text_clean = text.strip()
        if not text_clean:
            return None

        # Tier 1: Direct JSON parsing
        try:
            return json.loads(text_clean)
        except Exception:
            pass

        # Tier 2: Extract markdown JSON blocks ```json ... ```
        if "```" in text_clean:
            lines = text_clean.split("\n")
            in_block = False
            block_lines = []
            for line in lines:
                if line.strip().startswith("```"):
                    if in_block:
                        break
                    else:
                        in_block = True
                        continue
                if in_block:
                    block_lines.append(line)
            block_text = "\n".join(block_lines).strip()
            try:
                return json.loads(block_text)
            except Exception:
                pass

        # Tier 3: Find first { and last }
        start = text_clean.find("{")
        end = text_clean.rfind("}")
        if start != -1 and end != -1 and end > start:
            snippet = text_clean[start:end+1]
            try:
                return json.loads(snippet)
            except Exception:
                # Tier 4: Clean common JSON syntax defects (trailing commas, comments)
                cleaned = re.sub(r",\s*([}\]])", r"\1", snippet)
                try:
                    return json.loads(cleaned)
                except Exception:
                    pass

        # Tier 5: Robust semantic regex extraction fallback
        action_match = re.search(r'"action"\s*:\s*"([^"]+)"', text_clean)
        sig_match = re.search(r'"candidate_signal"\s*:\s*"([^"]+)"', text_clean)
        tool_match = re.search(r'"tool_name"\s*:\s*"([^"]+)"', text_clean)
        thought_match = re.search(r'"thought"\s*:\s*"([^"]+)"', text_clean)
        
        if tool_match and (not action_match or action_match.group(1) == "tool_call"):
            # Reconstruct tool call object
            args_match = re.search(r'"tool_args"\s*:\s*({[^}]+})', text_clean)
            tool_args = {}
            if args_match:
                try:
                    tool_args = json.loads(args_match.group(1))
                except Exception:
                    pass
            return {
                "action": "tool_call",
                "tool_name": tool_match.group(1),
                "tool_args": tool_args,
                "thought": thought_match.group(1) if thought_match else ""
            }
        elif sig_match:
            # Reconstruct conclude object
            return {
                "action": "conclude",
                "candidate_signal": sig_match.group(1),
                "thought": thought_match.group(1) if thought_match else "",
                "confidence": 0.85
            }

        return None


class LocalOllamaProvider(LLMProvider):
    """
    Local LLM provider using the Ollama HTTP API endpoint (default: http://127.0.0.1:11434).
    Captures precise hardware token counts and inference timings directly from Ollama.
    """

    def __init__(self, model_name: str = "qwen2.5-coder:1.5b",
                 base_url: str = "http://127.0.0.1:11434",
                 timeout: float = 60.0):
        self.model_name = model_name
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.1, max_tokens: int = 512,
                 json_format: bool = False) -> LLMResponse:
        t0 = time.time()
        url = f"{self.base_url}/api/generate"
        
        payload: Dict[str, Any] = {
            "model": self.model_name,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        if system_prompt:
            payload["system"] = system_prompt
        if json_format:
            payload["format"] = "json"

        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"}
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                resp_data = json.loads(resp.read().decode("utf-8"))
            
            elapsed_ms = (time.time() - t0) * 1000.0
            text = resp_data.get("response", "")
            p_tokens = resp_data.get("prompt_eval_count", -1)
            c_tokens = resp_data.get("eval_count", -1)
            t_tokens = (p_tokens + c_tokens) if (p_tokens >= 0 and c_tokens >= 0) else -1
            
            return LLMResponse(
                text=text,
                prompt_tokens=p_tokens,
                completion_tokens=c_tokens,
                total_tokens=t_tokens,
                latency_ms=elapsed_ms,
                model_name=self.model_name,
                raw_response=resp_data
            )
        except Exception as e:
            elapsed_ms = (time.time() - t0) * 1000.0
            return LLMResponse(
                text=f'{{"error": "Ollama connection failed: {str(e)}", "status": "MODEL_FAILURE"}}',
                prompt_tokens=-1,
                completion_tokens=-1,
                total_tokens=-1,
                latency_ms=elapsed_ms,
                model_name=self.model_name,
                finish_reason="error",
                raw_response={"error": str(e)}
            )


class MockLLMProvider(LLMProvider):
    """
    Deterministic Mock LLM Provider for unit testing, offline verification,
    and fast CI testing without external model weights.
    """

    def __init__(self, canned_responses: Optional[Dict[str, str]] = None,
                 default_signal: str = "count"):
        self.canned_responses = canned_responses or {}
        self.default_signal = default_signal
        self.call_count = 0

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.1, max_tokens: int = 512,
                 json_format: bool = False) -> LLMResponse:
        self.call_count += 1
        
        # Priority check for repair prompts if present
        if "[SYSTEM ERROR]" in prompt and "[SYSTEM ERROR]" in self.canned_responses:
            v = self.canned_responses["[SYSTEM ERROR]"]
            return LLMResponse(
                text=v,
                prompt_tokens=len(prompt) // 4,
                completion_tokens=len(v) // 4,
                total_tokens=(len(prompt) + len(v)) // 4,
                latency_ms=10.0,
                model_name="mock-deterministic"
            )

        # Check other canned responses
        for k, v in self.canned_responses.items():
            if k in prompt:
                return LLMResponse(
                    text=v,
                    prompt_tokens=len(prompt) // 4,
                    completion_tokens=len(v) // 4,
                    total_tokens=(len(prompt) + len(v)) // 4,
                    latency_ms=10.0,
                    model_name="mock-deterministic"
                )

        # Default structured RCA response
        default_resp = json.dumps({
            "failure_summary": "Simulated hardware testbench failure detected.",
            "suspected_root_cause": f"Anomaly on signal {self.default_signal} during active transaction.",
            "root_cause_location": "Internal state register update logic.",
            "causal_signals": [self.default_signal],
            "candidate_signal": self.default_signal,
            "evidence": ["Waveform transition divergence observed at failure cycle."],
            "confidence": 0.90,
            "action": "conclude",
            "tool_call": None
        })

        return LLMResponse(
            text=default_resp,
            prompt_tokens=50,
            completion_tokens=40,
            total_tokens=90,
            latency_ms=5.0,
            model_name="mock-deterministic"
        )


class PeftLLMProvider(LLMProvider):
    """
    Local PyTorch / Transformers / PEFT inference provider.
    Executes fine-tuned LoRA models directly in memory with exact token accounting.
    """

    def __init__(self, base_model_name: str = "Qwen/Qwen2.5-Coder-1.5B-Instruct",
                 adapter_path: Optional[str] = None,
                 device: Optional[str] = None):
        self.base_model_name = base_model_name
        self.adapter_path = adapter_path
        self.device = device or self._detect_best_device()
        self.model = None
        self.tokenizer = None
        self._load_model()

    @staticmethod
    def _detect_best_device():
        try:
            import torch_directml
            if torch_directml.device_count() > 0:
                return torch_directml.device(0)
        except Exception:
            pass
        try:
            import torch
            if torch.cuda.is_available():
                return torch.device("cuda:0")
        except Exception:
            pass
        import torch
        return torch.device("cpu")

    def _load_model(self):
        import torch
        from transformers import AutoTokenizer, AutoModelForCausalLM
        from peft import PeftModel

        self.tokenizer = AutoTokenizer.from_pretrained(self.base_model_name, trust_remote_code=True)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token

        dev_str = str(self.device).lower()
        if "cuda" in dev_str:
            dtype = torch.bfloat16
        elif "privateuseone" in dev_str or "directml" in dev_str:
            dtype = torch.float16
        else:
            dtype = torch.float32

        base = AutoModelForCausalLM.from_pretrained(
            self.base_model_name,
            torch_dtype=dtype,
            trust_remote_code=True,
            low_cpu_mem_usage=True
        )

        if self.adapter_path and os.path.exists(self.adapter_path):
            self.model = PeftModel.from_pretrained(base, self.adapter_path)
            self.model = self.model.merge_and_unload()
        else:
            self.model = base

        self.model.to(self.device)
        self.model.eval()

    def generate(self, prompt: str, system_prompt: Optional[str] = None,
                 temperature: float = 0.1, max_tokens: int = 512,
                 json_format: bool = False) -> LLMResponse:
        import torch
        t0 = time.time()

        messages = []
        if system_prompt:
            messages.append({"role": "system", "content": system_prompt})
        messages.append({"role": "user", "content": prompt})

        prompt_str = self.tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = self.tokenizer(prompt_str, return_tensors="pt").to(self.device)
        p_tokens = inputs.input_ids.shape[1]

        do_sample = (temperature > 0.0)
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_tokens,
                do_sample=do_sample,
                temperature=temperature if do_sample else 1.0,
                top_p=0.95 if do_sample else 1.0,
                pad_token_id=self.tokenizer.pad_token_id,
                eos_token_id=self.tokenizer.eos_token_id
            )

        gen_ids = outputs[0][p_tokens:]
        c_tokens = len(gen_ids)
        total_tokens = p_tokens + c_tokens
        text = self.tokenizer.decode(gen_ids, skip_special_tokens=True).strip()
        elapsed_ms = (time.time() - t0) * 1000.0

        return LLMResponse(
            text=text,
            prompt_tokens=p_tokens,
            completion_tokens=c_tokens,
            total_tokens=total_tokens,
            latency_ms=elapsed_ms,
            model_name=f"peft-{self.base_model_name}"
        )

