#!/usr/bin/env python3
"""Minimal tests for contract_eval v1. No GPU, no model."""
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import contract_eval

GOOD = {
    "claims": [{
        "claim_id": "anchor_source_external",
        "subject": "锚定来源",
        "predicate": "是",
        "object": "外部冻结参照",
        "polarity": 1,
        "kind": "assertion",
        "evidence": "锚定来自外部冻结参照。",
    }],
    "verdict": "PASS",
}


def row(raw, expected="PASS"):
    return {"id": "t", "expected_verdict": expected, "raw_output": raw}


def main():
    good = contract_eval.evaluate_row(row(json.dumps(GOOD, ensure_ascii=False)))
    assert good["structural_pass"] and good["schema_pass"] and good["triple_pass"], good
    assert good["verdict_ok"] is True

    fenced = contract_eval.evaluate_row(row("```json\n" + json.dumps(GOOD, ensure_ascii=False) + "\n```"))
    assert not fenced["structural_pass"]
    assert "fence" in fenced["structural_fail"]

    alias = json.loads(json.dumps(GOOD, ensure_ascii=False))
    alias["claims"][0]["polarity"] = "negative"
    alias["claims"][0]["kind"] = "fact"
    bad = contract_eval.evaluate_row(row(json.dumps(alias, ensure_ascii=False)))
    assert not bad["schema_pass"]
    assert "bad_polarity" in bad["schema_fail"] and "bad_kind" in bad["schema_fail"]

    empty = json.loads(json.dumps(GOOD, ensure_ascii=False))
    empty["claims"][0]["object"] = ""
    empty_triple = contract_eval.evaluate_row(row(json.dumps(empty, ensure_ascii=False)))
    assert empty_triple["schema_pass"]  # empty string is type-correct; schema does not require non-empty
    assert not empty_triple["triple_pass"]
    assert "empty_object" in empty_triple["triple_fail"]

    print("contract_eval tests: 4/4 OK")


if __name__ == "__main__":
    main()
