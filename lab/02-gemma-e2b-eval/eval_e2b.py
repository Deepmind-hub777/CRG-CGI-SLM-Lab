#!/usr/bin/env python3
"""Evaluate the E2B claim-extraction process on the frozen E003 holdout.

Base model and adapter see the same question + candidate draft. The external
claim_engine.py still decides the ground-truth verdict for that draft; the model
does not grade itself.
"""
import argparse, json, pathlib, re, sys, time
import torch
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import claim_engine

SYSTEM = (
"你是 CRG-CGI-SLM 的 claim 抽取器。只依据用户问题与候选草稿；"
"不要补全草稿没有的断言，不要引用外部知识，不要把锚定原文当成答案。"
"输出严格 JSON：claims 为数组，每项含 claim_id,subject,predicate,object,polarity,kind,evidence；"
"verdict 只能是 PASS 或 HOLD；hold_reason 为短句；rollback_required 为布尔。"
)


def get_tokenizer(model_id):
    try:
        from transformers import AutoProcessor
        proc = AutoProcessor.from_pretrained(model_id, trust_remote_code=True)
        if getattr(proc, "tokenizer", None) is not None:
            return proc.tokenizer
    except Exception:
        pass
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


def load_model(model_id, adapter=None):
    cap = torch.cuda.get_device_capability(0) if torch.cuda.is_available() else (0, 0)
    compute_dtype = torch.bfloat16 if cap[0] >= 8 else torch.float16
    bnb = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,
        bnb_4bit_compute_dtype=compute_dtype,
    )
    kwargs = dict(quantization_config=bnb, device_map={"": 0}, torch_dtype=compute_dtype,
                  low_cpu_mem_usage=True, trust_remote_code=True)
    try:
        model = AutoModelForCausalLM.from_pretrained(model_id, **kwargs)
    except Exception:
        from transformers import AutoModelForImageTextToText
        model = AutoModelForImageTextToText.from_pretrained(model_id, **kwargs)
    if adapter:
        model = PeftModel.from_pretrained(model, adapter)
    model.eval()
    return model


def parse_json(text):
    a = text.find("{")
    b = text.rfind("}")
    if a < 0 or b <= a:
        raise ValueError("no JSON object")
    return json.loads(text[a:b+1])


def claim_set(claims):
    out = set()
    for c in claims or []:
        try:
            out.add((str(c.get("claim_id")), int(c.get("polarity"))))
        except Exception:
            continue
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--model-id", default="google/gemma-4-E2B-it")
    ap.add_argument("--adapter", default="")
    ap.add_argument("--data", default=str(ROOT / "data/holdout.jsonl"))
    ap.add_argument("--out", default=str(ROOT / "runs/eval.json"))
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--max-new-tokens", type=int, default=384)
    args = ap.parse_args()

    rows = [json.loads(line) for line in pathlib.Path(args.data).read_text(encoding="utf-8").splitlines() if line.strip()]
    if args.limit:
        rows = rows[:args.limit]
    tokenizer = get_tokenizer(args.model_id)
    if tokenizer.pad_token_id is None:
        tokenizer.pad_token = tokenizer.eos_token
    model = load_model(args.model_id, args.adapter or None)
    log = []
    for rec in rows:
        expected = rec.get("expected_verdict")
        if not expected:
            expected = claim_engine.evaluate(rec["draft"], rec["case_id"])["verdict"]
        policy = claim_engine.evaluate(rec["draft"], rec["case_id"])
        expected_claims = {(c["claim_id"], c["polarity"]) for c in policy["claims"]}
        prompt = build_prompt(tokenizer, rec)
        inputs = tokenizer(prompt, return_tensors="pt", truncation=True, max_length=1024)
        inputs = {k: v.to(model.device) for k, v in inputs.items()}
        t0 = time.time()
        with torch.inference_mode():
            out = model.generate(
                **inputs,
                max_new_tokens=args.max_new_tokens,
                do_sample=False,
                temperature=None,
                top_p=None,
                pad_token_id=tokenizer.pad_token_id,
                eos_token_id=tokenizer.eos_token_id,
            )
        elapsed = time.time() - t0
        new_ids = out[0][inputs["input_ids"].shape[1]:]
        text = tokenizer.decode(new_ids, skip_special_tokens=True).strip()
        row = {
            "id": rec["id"],
            "case": rec["case_id"],
            "expected_verdict": expected,
            "latency_s": round(elapsed, 3),
            "raw_output": text,
        }
        try:
            obj = parse_json(text)
            row["json_ok"] = True
            row["model_verdict"] = obj.get("verdict")
            row["model_claims"] = obj.get("claims", [])
            row["verdict_match"] = obj.get("verdict") == expected
            row["claim_set_match"] = claim_set(obj.get("claims", [])) == expected_claims
        except Exception as e:
            row["json_ok"] = False
            row["parse_error"] = str(e)
            row["model_verdict"] = None
            row["verdict_match"] = False
            row["claim_set_match"] = False
        log.append(row)
        print(json.dumps({k: row.get(k) for k in ("id","expected_verdict","model_verdict","json_ok","verdict_match","claim_set_match")}, ensure_ascii=False))

    n = len(log)
    summary = {
        "model_id": args.model_id,
        "adapter": args.adapter,
        "data": str(pathlib.Path(args.data).resolve()),
        "n": n,
        "json_ok_rate": sum(1 for r in log if r.get("json_ok")) / n if n else 0,
        "verdict_accuracy": sum(1 for r in log if r.get("verdict_match")) / n if n else 0,
        "claim_set_exact_rate": sum(1 for r in log if r.get("claim_set_match")) / n if n else 0,
        "avg_latency_s": sum(r["latency_s"] for r in log) / n if n else 0,
    }
    out_path = pathlib.Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_text(json.dumps({"summary": summary, "rows": log}, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps(summary, ensure_ascii=False))


if __name__ == "__main__":
    main()
