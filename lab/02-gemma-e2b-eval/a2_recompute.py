#!/usr/bin/env python3
"""A2: recompute the four cloud eval artifacts with one frozen rubric.

Inputs (copied from DSW via the browser file API):
- base old (384 tokens)
- adapter old (384 tokens)
- base new prompt (768 / rep 1.05)
- adapter new prompt (768 / rep 1.05)

No GPU, no model load, no weights changed.
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import contract_eval

CASES = {
    "base_old_384": ("evidence/a2-cloud/base_eval.json", "base", "old: 384 tokens"),
    "adapter_old_384": ("evidence/a2-cloud/adapter_eval.json", "adapter", "old: 384 tokens"),
    "base_new_prompt": ("evidence/a2-cloud/base_eval_contract.json", "base", "new: 768 / rep 1.05 / fence-stop"),
    "adapter_new_prompt": ("evidence/a2-cloud/adapter_eval_contract.json", "adapter", "new: 768 / rep 1.05 / fence-stop"),
}


def load_rows(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    if isinstance(payload, list):
        return payload
    if isinstance(payload, dict) and isinstance(payload.get("rows"), list):
        return payload["rows"]
    raise SystemExit(f"{path}: no rows array")


def main():
    holdout = [json.loads(l) for l in (ROOT / "data/holdout.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    out = {}
    for label, (rel, model, prompt) in CASES.items():
        path = ROOT / rel
        rows = load_rows(path)
        for i, row in enumerate(rows):
            row["case_id"] = "E003"
            row["_holdout"] = holdout[i]
        summary = contract_eval.summarize(rows)
        recorded = [r.get("model_verdict") == r.get("expected_verdict") for r in rows]
        recorded_hold = [r.get("model_verdict") == r.get("expected_verdict") for r in rows if r.get("expected_verdict") == "HOLD"]
        summary["recorded_verdict_accuracy"] = round(sum(recorded) / len(rows), 4)
        summary["recorded_hold_recall"] = round(sum(recorded_hold) / len(recorded_hold), 4) if recorded_hold else None
        out[label] = {
            "source": rel,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "model": model,
            "prompt": prompt,
            "summary": {k: v for k, v in summary.items() if k != "rows"},
            "rows": summary["rows"],
        }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    (ROOT / "evidence/a2-recompute.json").write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
