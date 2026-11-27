#!/usr/bin/env python3
"""A5 zero-GPU semantic audit.

No model is loaded. It compares four verdict sources against the frozen holdout:
1. gold_claims -> claim policy (does the rule reproduce gold?);
2. draft text -> claim_engine.evaluate (does extraction reproduce gold?);
3. model raw verdict (what the model said);
4. model claims -> claim policy (what the frozen rule says about the model's claims).

The point is to separate rule consistency from model behavior before any GPU
rerun. It does not label a model as pass/fail.
"""
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import claim_engine
import contract_eval

CASES = {
    "qwen_base": "evidence/qwen3-4b/base_eval.json",
    "qwen_adapter_50": "evidence/qwen3-4b/adapter_eval.json",
}


def load_rows(path):
    payload = json.loads(path.read_text(encoding="utf-8"))
    return payload["rows"] if isinstance(payload, dict) else payload


def main():
    holdout = [json.loads(l) for l in (ROOT / "data/holdout.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    allow = claim_engine.allowed_claim_ids("E003")
    out = {"contract": "contract-semantics-v1", "case": "E003", "allowlist": allow, "n": len(holdout), "sources": {}}

    gold_policy = []
    draft_engine = []
    for rec in holdout:
        gold_policy.append(claim_engine.adjudicate_claims(rec.get("gold_claims", []), rec["case_id"])["verdict"])
        draft_engine.append(claim_engine.evaluate(rec["draft"], rec["case_id"])["verdict"])

    def basic(verdicts):
        exp = [r["expected_verdict"] for r in holdout]
        return {
            "verdict_accuracy": round(sum(v == e for v, e in zip(verdicts, exp)) / len(exp), 4),
            "pass_recall": round(sum(v == "PASS" for v, e in zip(verdicts, exp) if e == "PASS") / sum(e == "PASS" for e in exp), 4),
            "hold_recall": round(sum(v == "HOLD" for v, e in zip(verdicts, exp) if e == "HOLD") / sum(e == "HOLD" for e in exp), 4),
            "output_hold": sum(v == "HOLD" for v in verdicts),
            "distribution": dict(Counter(verdicts)),
        }

    out["sources"]["gold_claims_policy"] = basic(gold_policy)
    out["sources"]["draft_engine"] = basic(draft_engine)

    for label, rel in CASES.items():
        rows = load_rows(ROOT / rel)
        model_verdicts = []
        claim_verdicts = []
        ids_allowed = 0
        claim_ids = Counter()
        for row, rec in zip(rows, holdout):
            raw = row.get("raw_output", "")
            obj, _, _ = contract_eval.parse_strict(raw)
            mv = obj.get("verdict") if isinstance(obj, dict) else None
            model_verdicts.append(mv)
            claims = obj.get("claims", []) if isinstance(obj, dict) and isinstance(obj.get("claims"), list) else []
            claim_verdicts.append(claim_engine.adjudicate_claims(claims, rec["case_id"])["verdict"])
            ids = [str(c.get("claim_id")) for c in claims if isinstance(c, dict)]
            claim_ids.update(ids)
            if ids and all(x in allow for x in ids):
                ids_allowed += 1
        out["sources"][label + "_model_verdict"] = basic(model_verdicts)
        out["sources"][label + "_claims_policy"] = basic(claim_verdicts)
        out["sources"][label + "_claim_ids"] = {
            "rows_with_all_ids_allowed": ids_allowed,
            "distinct_ids": len(claim_ids),
            "top_ids": claim_ids.most_common(8),
        }

    # Confusion between the model's own verdict and the policy verdict on its claims.
    for label in CASES:
        rows = load_rows(ROOT / CASES[label])
        pairs = []
        for row, rec in zip(rows, holdout):
            obj, _, _ = contract_eval.parse_strict(row.get("raw_output", ""))
            if not isinstance(obj, dict):
                continue
            pairs.append((obj.get("verdict"), claim_engine.adjudicate_claims(obj.get("claims", []), rec["case_id"])["verdict"]))
        out["sources"][label + "_verdict_vs_claim_policy"] = {
            "pairs": dict(Counter(f"{a}->{b}" for a, b in pairs))
        }

    text = json.dumps(out, ensure_ascii=False, indent=2)
    (ROOT / "evidence/a5-semantic-audit.json").write_text(text + "\n", encoding="utf-8")

    lines = ["# A5 零 GPU 语义审计", "",
             "未加载模型；只把冻结 gold、草稿抽取、模型输出和模型 claims 分别送进同一套 claim policy。", "",
             "允许 claim_id：" + ", ".join(allow), "",
             "| 来源 | verdict 一致 | PASS recall | HOLD recall | 输出 HOLD | 分布 |",
             "|---|---:|---:|---:|---:|---|"]
    for name, s in out["sources"].items():
        if "distribution" in s:
            lines.append(f"| {name} | {s['verdict_accuracy']} | {s['pass_recall']} | {s['hold_recall']} | {s['output_hold']} | {s['distribution']} |")
    lines += ["", "## claim_id 使用", ""]
    for name in CASES:
        s = out["sources"][name + "_claim_ids"]
        lines.append(f"- **{name}**：全部 ID 落在允许表的行 {s['rows_with_all_ids_allowed']}/10；不同 ID {s['distinct_ids']} 个；高频 {s['top_ids']}。")
    lines += ["", "## 模型 verdict 与“模型 claims 经 policy 重判”的配对", ""]
    for name in CASES:
        s = out["sources"][name + "_verdict_vs_claim_policy"]
        lines.append(f"- **{name}**：{s['pairs']}")
    lines += ["", "读法：`gold_claims_policy` 与 `draft_engine` 检验规则/抽取是否复现 gold；`*_model_verdict` 是模型自己说的；`*_claims_policy` 是同一规则对模型 claims 的重判。四者不混成一个分数。", ""]
    (ROOT / "evidence/a5-semantic-audit.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
