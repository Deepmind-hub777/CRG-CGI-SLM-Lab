#!/usr/bin/env python3
"""A3 data-contract checks: no GPU, no model.

Verifies:
- train targets have complete claim triples, numeric polarity, enum kind.
- holdout has frozen gold_claims, all complete.
- frozen gold_claims still reproduce expected_verdict under claim_engine.
"""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import claim_engine

KINDS = {"assertion", "antecedent", "consequent", "hypothetical", "interrogative"}
FIELDS = ("claim_id", "subject", "predicate", "object", "evidence")


def check_claims(claims, where, allow_empty=False):
    assert allow_empty or claims, f"{where}: empty claims"
    if not claims:
        return
    for i, c in enumerate(claims):
        for f in FIELDS:
            assert isinstance(c.get(f), str) and c[f].strip(), f"{where}[{i}] empty {f}"
        assert c.get("polarity") in (1, -1), f"{where}[{i}] bad polarity {c.get('polarity')}"
        assert c.get("kind") in KINDS, f"{where}[{i}] bad kind {c.get('kind')}"


def main():
    train = [json.loads(l) for l in pathlib.Path("data/train.jsonl").read_text().splitlines() if l.strip()]
    holdout = [json.loads(l) for l in pathlib.Path("data/holdout.jsonl").read_text().splitlines() if l.strip()]
    assert len(train) == 50 and len(holdout) == 10
    for r in train:
        check_claims(r.get("claims"), r["id"], allow_empty=(r.get("verdict") == "HOLD"))
        assert "gold_claims" not in r, f"{r['id']}: gold leaked into train"
    for r in holdout:
        check_claims(r.get("gold_claims"), r["id"], allow_empty=(r.get("expected_verdict") == "HOLD"))
        res = claim_engine.evaluate(r["draft"], r["case_id"])
        assert res["verdict"] == r["expected_verdict"], f"{r['id']}: frozen gold verdict mismatch"
    print("data contract: train=50 holdout=10, all triples complete, gold frozen, verdicts consistent")


if __name__ == "__main__":
    main()
