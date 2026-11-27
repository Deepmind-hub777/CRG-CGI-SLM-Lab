#!/usr/bin/env python3
"""Gemma 4 E2B smoke QLoRA: process trace, not answer memorization.

Input  : user question + candidate draft (the draft is context, not a target)
Target : {"claims":[...],"verdict":"PASS|HOLD","hold_reason":"...","rollback_required":bool}

The target is only the claim structure/verdict. The frozen anchor and policy are
not copied into any target. Run one epoch for smoke; do not merge/export here.
"""
import argparse, hashlib, json, os, pathlib, platform, random, time
import torch
from datasets import Dataset
from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    DataCollatorForSeq2Seq,
    Trainer,
    TrainingArguments,
)

ROOT = pathlib.Path(__file__).resolve().parent
SYSTEM = (
"你是 CRG-CGI-SLM 的 claim 抽取器。只依据用户问题与候选草稿；"
"不要补全草稿没有的断言，不要引用外部知识，不要把锚定原文当成答案。"
"输出严格 JSON：claims 为数组，每项含 claim_id,subject,predicate,object,polarity,kind,evidence；"
"verdict 只能是 PASS 或 HOLD；hold_reason 为短句；rollback_required 为布尔。"
)


def log(msg):
    print(msg, flush=True)


def get_tokenizer(model_id):
    # Gemma 4 E2B may be multimodal; prefer the processor's tokenizer.
    try:
        from transformers import AutoProcessor
        proc = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        tok = getattr(proc, "tokenizer", None)
        if tok is not None:
            return tok
    except Exception as e:
        log(f"processor fallback: {e}")
    return AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)


def build_prompt(tokenizer, rec):
    user = (
        f"用户问题：{rec['prompt']}\n"
        f"候选草稿：{rec['draft']}\n"
        f"锚定摘录：{rec.get('anchor_excerpt','') or '（无，仅依据草稿判断）'}\n"
        "请抽取草稿里实际出现的 claims，并给出 PASS/HOLD。"
    )
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:
        return f"<system>\n{SYSTEM}\n</system>\n<user>\n{user}\n</user>\n<assistant>\n"


def build_target(rec):
    return json.dumps({
        "claims": rec["claims"],
        "verdict": rec["verdict"],
        "hold_reason": rec.get("hold_reason", ""),
        "rollback_required": bool(rec.get("rollback_required", False)),
    }, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def load_records(path):
    rows = [json.loads(line) for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]
    if not rows:
        raise SystemExit(f"empty dataset: {path}")
    return rows


def tokenize_record(tokenizer, rec, max_length):
    prompt = build_prompt(tokenizer, rec)
    target = build_target(rec)
    p_ids = tokenizer(prompt, add_special_tokens=False)["input_ids"]
    t_ids = tokenizer(target, add_special_tokens=False)["input_ids"]
    eos = tokenizer.eos_token_id
    if eos is not None and (not t_ids or t_ids[-1] != eos):
        t_ids = t_ids + [eos]
    # Keep the target intact; trim prompt from the left when needed.
    if len(t_ids) >= max_length:
        t_ids = t_ids[:max_length - 1] + [eos]
    room = max_length - len(t_ids)
    p_ids = p_ids[-room:] if len(p_ids) > room else p_ids
    input_ids = p_ids + t_ids
    labels = [-100] * len(p_ids) + t_ids
    return {"input_ids": input_ids, "attention_mask": [1] * len(input_ids), "labels": labels}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", default="google/gemma-4-E2B-it")
    ap.add_argument("--train", default=str(ROOT / "data/train.jsonl"))
    ap.add_argument("--run-id", default=time.strftime("smoke-%Y%m%d-%H%M%S"))
    ap.add_argument("--output-root", default=str(ROOT / "runs"))
    ap.add_argument("--max-length", type=int, default=1024)
    ap.add_argument("--epochs", type=float, default=1.0)
    ap.add_argument("--grad-accum", type=int, default=4)
    ap.add_argument("--lr", type=float, default=1e-4)
    ap.add_argument("--seed", type=int, default=42)
    ap.add_argument("--compute-dtype", choices=["auto","bf16","fp16"], default="auto")
    args = ap.parse_args()

    random.seed(args.seed)
    torch.manual_seed(args.seed)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(args.seed)

    run_dir = pathlib.Path(args.output_root) / args.run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    log(f"run_dir={run_dir}")
    log(f"torch={torch.__version__} cuda={torch.cuda.is_available()}")
    if torch.cuda.is_available():
        log(f"gpu={torch.cuda.get_device_name(0)} vram_gb={torch.cuda.get_device_properties(0).total_memory/1024**3:.1f}")
        log(f"cuda_version={torch.version.cuda}")
        cap = torch.cuda.get_device_capability(0)
        log(f"compute_capability={cap}")
    else:
        raise SystemExit("CUDA is required for QLoRA; no GPU visible.")

    if args.compute_dtype == "auto":
        compute_dtype = torch.bfloat16 if cap[0] >= 8 else torch.float16
    elif args.compute_dtype == "bf16":
        compute_dtype = torch.bfloat16
    else:
        compute_dtype = torch.float16
    use_bf16 = compute_dtype == torch.bfloat16
    log(f"compute_dtype={compute_dtype} bf16={use_bf16}")

    tokenizer = get_tokenizer(args.model_id)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    log(f"tokenizer={type(tokenizer).__name__} pad={tokenizer.pad_token_id} eos={tokenizer.eos_token_id}")

    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    kwargs = dict(
        quantization_config=bnb,
        device_map={"": 0},
        torch_dtype=compute_dtype,
        low_cpu_mem_usage=True,
        trust_remote_code=True,
    )
    try:
        model = AutoModelForCausalLM.from_pretrained(args.model_id, **kwargs)
        model_kind = "AutoModelForCausalLM"
    except Exception as e:
        log(f"AutoModelForCausalLM failed: {e}; trying AutoModelForImageTextToText")
        from transformers import AutoModelForImageTextToText
        model = AutoModelForImageTextToText.from_pretrained(args.model_id, **kwargs)
        model_kind = "AutoModelForImageTextToText"
    log(f"model_kind={model_kind}")

    # Do not call prepare_model_for_kbit_training here: on this multimodal
    # checkpoint it casts a large non-quantized block to fp32 and OOMs a 16 GB
    # V100 before LoRA is even attached. Freeze first, then let PEFT mark LoRA
    # params trainable; enable input grads explicitly for checkpointing.
    for _, p in model.named_parameters():
        p.requires_grad = False
    if hasattr(model, "enable_input_require_grads"):
        model.enable_input_require_grads()
    model.gradient_checkpointing_enable()
    model.config.use_cache = False

    # Only text decoder projections. Avoid vision/audio towers by name.
    suffixes = ("q_proj", "k_proj", "v_proj", "o_proj", "gate_proj", "up_proj", "down_proj")
    targets = []
    for name, _ in model.named_modules():
        if not any(name.endswith("." + s) for s in suffixes):
            continue
        low = name.lower()
        if any(x in low for x in ("vision", "audio", "multi_modal", "mm_projector", "embed_vision", "embed_audio")):
            continue
        if "language_model" in low or "text_model" in low or ".layers." in low or low.startswith("model.layers"):
            targets.append(name)
    if not targets:
        targets = [s for s in suffixes]
    log(f"target_modules={len(targets)} first={targets[:3]} last={targets[-3:]}")

    lora = LoraConfig(
        r=16, lora_alpha=32, lora_dropout=0.05, bias="none",
        target_modules=targets, task_type="CAUSAL_LM",
    )
    model = get_peft_model(model, lora)
    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log(f"trainable={trainable} total={total} ratio={trainable/total:.6f}")

    rows = load_records(args.train)
    ds = Dataset.from_list([tokenize_record(tokenizer, r, args.max_length) for r in rows])
    collator = DataCollatorForSeq2Seq(tokenizer, model=model, padding=True, label_pad_token_id=-100, return_tensors="pt")

    training_args = TrainingArguments(
        output_dir=str(run_dir),
        per_device_train_batch_size=1,
        gradient_accumulation_steps=args.grad_accum,
        learning_rate=args.lr,
        num_train_epochs=args.epochs,
        warmup_steps=1,
        lr_scheduler_type="cosine",
        logging_steps=1,
        save_strategy="epoch",
        save_total_limit=1,
        bf16=use_bf16,
        fp16=not use_bf16,
        gradient_checkpointing=True,
        optim="paged_adamw_8bit",
        report_to="none",
        seed=args.seed,
        data_seed=args.seed,
        remove_unused_columns=False,
    )
    trainer = Trainer(model=model, args=training_args, train_dataset=ds, data_collator=collator)
    t0 = time.time()
    result = trainer.train()
    elapsed = time.time() - t0
    adapter_dir = run_dir / "adapter"
    model.save_pretrained(adapter_dir)
    tokenizer.save_pretrained(adapter_dir)
    log(f"train_seconds={elapsed:.1f} result={result.training_loss}")

    adapter_hash = ""
    for p in sorted(adapter_dir.rglob("*")):
        if p.is_file():
            adapter_hash = hashlib.sha256(p.read_bytes()).hexdigest()
            break

    manifest = {
        "run_id": args.run_id,
        "model_id": args.model_id,
        "model_kind": model_kind,
        "train_file": str(pathlib.Path(args.train).resolve()),
        "train_sha256": hashlib.sha256(pathlib.Path(args.train).read_bytes()).hexdigest(),
        "records": len(rows),
        "max_length": args.max_length,
        "epochs": args.epochs,
        "grad_accum": args.grad_accum,
        "lr": args.lr,
        "seed": args.seed,
        "trainable_params": trainable,
        "total_params": total,
        "trainable_ratio": trainable / total,
        "train_seconds": elapsed,
        "train_loss": result.training_loss,
        "gpu": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "",
        "vram_gb": torch.cuda.get_device_properties(0).total_memory / 1024**3 if torch.cuda.is_available() else 0,
        "torch": torch.__version__,
        "cuda": torch.version.cuda,
        "compute_dtype": str(compute_dtype),
        "adapter_first_file_sha256": adapter_hash,
        "target_module_count": len(targets),
        "notes": "smoke only; adapter not merged/exported; 0 and -1 remain external",
    }
    (run_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    log(f"manifest={run_dir/'manifest.json'}")


if __name__ == "__main__":
    main()
