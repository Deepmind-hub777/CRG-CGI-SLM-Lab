#!/usr/bin/env python3
"""Recompute a cloud eval artifact under rubric_v1 + frozen claim policy.

Read-only: no model load, no GPU. Produces a per-row audit for A5.
The cloud `claim_set_match` used `int(polarity)`, so string aliases collapse to
an empty set. This script keeps the alias-aware diagnostic separate from the
strict gate.
"""
import argparse
import json
import pathlib
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import claim_engine
import contract_eval


def load_jsonl(path):
    return [json.loads(line) for line in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if line.strip()]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", required=True)
    ap.add_argument("--holdout", default=str(ROOT / "data/holdout.jsonl"))
    ap.add_argument("--out", required=True)
    args = ap.parse_args()

    payload = json.loads(pathlib.Path(args.eval).read_text(encoding="utf-8"))
    rows = payload["rows"]
    holdout = load_jsonl(args.holdout)
    if len(rows) != len(holdout):
        raise SystemExit(f"row/holdout length mismatch: {len(rows)} vs {len(holdout)}")

    for row in rows:
        row["case_id"] = row.get("case") or row.get("case_id") or "E003"
    summary = contract_eval.summarize(rows)

    per_row = []
    gold_exact = 0
    policy_ok = 0
    consistency = 0
    for row, gold in zip(rows, holdout):
        adj = claim_engine.adjudicate_claims(row.get("model_claims", []), row["case_id"])
        pred = {
            (str(c.get("claim_id")), claim_engine._polarity_int(c.get("polarity")))
            for c in row.get("model_claims", [])
            if claim_engine._polarity_int(c.get("polarity")) in (1, -1)
        }
        frozen = {(str(c.get("claim_id")), int(c.get("polarity"))) for c in gold.get("gold_claims", [])}
        exact = pred == frozen
        gold_exact += exact
        policy_ok += adj["verdict"] == row.get("expected_verdict")
        consistency += adj["verdict"] == row.get("model_verdict")
        per_row.append({
            "id": row.get("id"),
            "expected_verdict": row.get("expected_verdict"),
            "model_verdict": row.get("model_verdict"),
            "claims_policy_verdict": adj["verdict"],
            "model_verdict_matches_own_policy": adj["verdict"] == row.get("model_verdict"),
            "gold_claim_set_exact": exact,
            "gold_claim_set": sorted(frozen),
            "model_claim_set_alias_aware": sorted(pred),
            "claim_count": len(row.get("model_claims", [])),
        })

    out = {
        "source_eval": str(pathlib.Path(args.eval)),
        "holdout": str(pathlib.Path(args.holdout)),
        "summary": {k: v for k, v in summary.items() if k != "rows"},
        "claims_policy_accuracy": round(policy_ok / len(rows), 4),
        "model_verdict_equals_own_policy": f"{consistency}/{len(rows)}",
        "gold_claim_set_exact_alias_aware": f"{gold_exact}/{len(rows)}",
        "claims_total": sum(len(r.get("model_claims", [])) for r in rows),
        "claim_id_counts": dict(Counter(str(c.get("claim_id")) for r in rows for c in r.get("model_claims", []))),
        "rows": per_row,
    }
    pathlib.Path(args.out).write_text(json.dumps(out, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(json.dumps({k: v for k, v in out.items() if k != "rows"}, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
