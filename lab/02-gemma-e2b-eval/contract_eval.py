#!/usr/bin/env python3
"""Contract evaluator v1.

Reads either:
- an eval.json (JSON array; rows need id, expected_verdict, raw_output), or
- the cloud Markdown report (evidence/e2b-contract-eval-report.md).

Applies one rubric:
1. structural: single object, no fence, top-level verdict, claims list, no duplicate keys, no trailing tokens, not truncated.
2. schema: required claim fields, polarity in {1,-1}, kind in enum, no empty claims for PASS.
3. full triple: schema + non-empty subject/predicate/object/evidence.

It deliberately does not claim "accuracy" for a model. It reports contract pass rates,
verdict accuracy, HOLD recall, always-PASS baseline, and claim-set exact only when gold claims exist.
"""
import argparse
import json
import pathlib
import re
import sys
from collections import Counter

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import claim_engine

RUBRIC = json.loads((ROOT / "rubric_v1.json").read_text(encoding="utf-8"))
KINDS = set(RUBRIC["schema"]["kind_values"])
POLARITIES = set(RUBRIC["schema"]["polarity_values"])
POLARITY_ALIASES = {1, -1, "1", "-1", "+1", "positive", "negative", "pos", "neg"}
KIND_ALIASES = KINDS | {"fact", "restriction", "claim", "condition", "hypothesis"}

FAIL = RUBRIC["failure_classes"]


def _dup_hook(pairs):
    obj = {}
    dups = []
    for k, v in pairs:
        if k in obj:
            dups.append(k)
        obj[k] = v
    if dups:
        obj["__dups__"] = dups
    return obj


def parse_strict(text):
    """Return (obj, errors, dups). Errors are failure classes."""
    errors = []
    if "```" in text:
        errors.append("fence")
    stripped = text.strip()
    if not stripped:
        return None, ["bad_json"], []
    try:
        obj, end = json.JSONDecoder(object_pairs_hook=_dup_hook).raw_decode(stripped)
    except json.JSONDecodeError as e:
        # Heuristic: unterminated structures / unexpected end are truncation.
        msg = str(e)
        if "Unterminated string" in msg or "Expecting" in msg and e.pos >= len(stripped) - 24:
            errors.append("truncated")
        else:
            errors.append("bad_json")
        return None, errors, []
    if stripped[end:].strip():
        errors.append("trailing")
    if not isinstance(obj, dict):
        errors.append("array_root")
        return obj, errors, []
    dups = obj.pop("__dups__", [])
    return obj, errors, dups


def check_structural(obj, errors, dups):
    if dups:
        errors.append("dupkey")
    if obj is None:
        return errors
    if "verdict" not in obj:
        errors.append("missing_verdict")
    elif obj.get("verdict") not in ("PASS", "HOLD"):
        errors.append("bad_verdict")
    if not isinstance(obj.get("claims"), list):
        errors.append("bad_claims")
    return errors


def check_schema(obj, allowed_ids=None):
    errors = []
    if obj is None:
        return ["bad_json"]
    claims = obj.get("claims")
    if not isinstance(claims, list):
        return ["bad_claims"]
    if not claims and obj.get("verdict") == "PASS":
        errors.append("empty_claims_pass")
    for c in claims:
        if not isinstance(c, dict):
            errors.append("claim_not_object")
            continue
        for field in RUBRIC["schema"]["required_claim_fields"]:
            if field not in c:
                errors.append("missing_field")
        pol = c.get("polarity")
        if isinstance(pol, bool) or not isinstance(pol, int) or pol not in POLARITIES:
            errors.append("bad_polarity")
        if not isinstance(c.get("kind"), str) or c.get("kind") not in KINDS:
            errors.append("bad_kind")
        if allowed_ids is not None:
            cid = c.get("claim_id")
            if isinstance(cid, str) and cid.strip() and cid not in allowed_ids:
                errors.append("claim_id_not_allowed")
    return errors


def check_claim_ids(obj, allowed_ids=None):
    """Return True when every structured claim uses the case allowlist.

    A missing/empty claim_id is already a strict-schema failure; this helper
    only reports the allowlist dimension, so it stays usable as a diagnostic.
    """
    if allowed_ids is None:
        return True
    if not isinstance(obj, dict) or not isinstance(obj.get("claims"), list):
        return False
    for c in obj["claims"]:
        if not isinstance(c, dict):
            return False
        cid = c.get("claim_id")
        if not isinstance(cid, str) or not cid.strip() or cid not in allowed_ids:
            return False
    return True


def check_triple(obj):
    errors = check_schema(obj)
    if obj is None or not isinstance(obj.get("claims"), list):
        return errors
    for c in obj["claims"]:
        if not isinstance(c, dict):
            continue
        for field, fail in (
            ("claim_id", "empty_claim_id"),
            ("subject", "empty_subject"),
            ("predicate", "empty_predicate"),
            ("object", "empty_object"),
            ("evidence", "empty_evidence"),
        ):
            v = c.get(field)
            if not isinstance(v, str) or not v.strip():
                errors.append(fail)
    return errors


def core_triple_ok(obj, structural_ok):
    """Diagnostic, not a gate: structural + non-empty core triple.
    Ignores polarity/kind/evidence so harness strictness is separated from content.
    """
    if not structural_ok or not isinstance(obj, dict) or not isinstance(obj.get("claims"), list):
        return False
    claims = obj["claims"]
    if not claims and obj.get("verdict") == "PASS":
        return False
    for c in claims:
        if not isinstance(c, dict):
            return False
        for field in ("claim_id", "subject", "predicate", "object"):
            if not isinstance(c.get(field), str) or not c[field].strip():
                return False
    return True


def lenient_schema_ok(obj, structural_ok):
    """Diagnostic: accept common aliases (positive/negative, fact/restriction)
    and require evidence, but still reject polarity 0 and kind PASS.
    """
    if not core_triple_ok(obj, structural_ok):
        return False
    for c in obj["claims"]:
        if c.get("polarity") not in POLARITY_ALIASES:
            return False
        if not isinstance(c.get("kind"), str) or c.get("kind") not in KIND_ALIASES:
            return False
        if not isinstance(c.get("evidence"), str) or not c["evidence"].strip():
            return False
    return True


def verdict_of(obj):
    return obj.get("verdict") if isinstance(obj, dict) else None


def claim_set(obj):
    out = set()
    if not isinstance(obj, dict):
        return out
    for c in obj.get("claims") or []:
        if not isinstance(c, dict):
            continue
        try:
            out.add((str(c.get("claim_id")), int(c.get("polarity"))))
        except Exception:
            continue
    return out


def semantic_claim_set(obj):
    """Triple-level set, reported as a diagnostic only."""
    out = set()
    if not isinstance(obj, dict):
        return out
    for c in obj.get("claims") or []:
        if not isinstance(c, dict):
            continue
        try:
            out.add((
                str(c.get("subject", "")).strip(),
                str(c.get("predicate", "")).strip(),
                str(c.get("object", "")).strip(),
                int(c.get("polarity")),
            ))
        except Exception:
            continue
    return out


def expected_claim_set(row):
    if isinstance(row.get("expected_claims"), list):
        return {(str(c.get("claim_id")), int(c.get("polarity"))) for c in row["expected_claims"] if c.get("polarity") in (1, -1)}
    # report mode: prefer frozen gold_claims, then fall back to the holdout draft.
    data = row.get("_holdout")
    if data and data.get("gold_claims") is not None:
        return {(str(c.get("claim_id")), int(c.get("polarity"))) for c in data["gold_claims"] if c.get("polarity") in (1, -1)}
    if data and row.get("case_id"):
        res = claim_engine.evaluate(data.get("draft", ""), data.get("case_id", "E003"))
        return {(str(c["claim_id"]), int(c["polarity"])) for c in res["claims"]}
    return None


def expected_semantic_claim_set(row):
    if isinstance(row.get("expected_claims"), list):
        return {
            (str(c.get("subject", "")).strip(), str(c.get("predicate", "")).strip(),
             str(c.get("object", "")).strip(), int(c.get("polarity")))
            for c in row["expected_claims"] if c.get("polarity") in (1, -1)
        }
    data = row.get("_holdout")
    if data and data.get("gold_claims") is not None:
        return {
            (str(c.get("subject", "")).strip(), str(c.get("predicate", "")).strip(),
             str(c.get("object", "")).strip(), int(c.get("polarity")))
            for c in data["gold_claims"] if c.get("polarity") in (1, -1)
        }
    return None


def evaluate_row(row):
    raw = row.get("raw_output", "")
    obj, perr, dups = parse_strict(raw)
    structural = check_structural(obj, list(perr), dups)
    schema = check_schema(obj)
    triple = check_triple(obj)
    case_id = row.get("case_id")
    allowed_ids = claim_engine.allowed_claim_ids(case_id) if case_id else None
    ids_allowed = check_claim_ids(obj, allowed_ids)
    gate_errors = check_schema(obj, allowed_ids) if allowed_ids is not None else schema
    expected = row.get("expected_verdict")
    got = verdict_of(obj)
    exp_claims = expected_claim_set(row)
    exp_semantic = expected_semantic_claim_set(row)
    cs = claim_set(obj)
    sem = semantic_claim_set(obj)
    contract_valid = (not structural) and (not schema)
    strict_contract = (not structural) and (not gate_errors) and (not triple) and ids_allowed
    return {
        "id": row.get("id"),
        "case_id": case_id,
        "expected_verdict": expected,
        "model_verdict": got,
        "structural_pass": not structural,
        "schema_pass": not schema,
        "triple_pass": not triple,
        "claim_id_allowed": ids_allowed,
        "strict_contract_pass": strict_contract,
        "core_triple_pass": core_triple_ok(obj, not structural),
        "lenient_schema_pass": lenient_schema_ok(obj, not structural),
        "structural_fail": structural,
        "schema_fail": schema,
        "triple_fail": triple,
        "gate_fail": gate_errors,
        "verdict_ok": bool(expected and got == expected),
        "claim_set_exact": (cs == exp_claims) if (exp_claims is not None and contract_valid) else None,
        "claim_set_semantic": (sem == exp_semantic) if (exp_semantic is not None and strict_contract) else None,
    }


def summarize(rows):
    n = len(rows)
    if not n:
        return {"n": 0}
    ev = [evaluate_row(r) for r in rows]
    counts = Counter()
    for e in ev:
        for k in e["structural_fail"]:
            counts[k] += 1
        for k in e["schema_fail"]:
            counts[k] += 1
        for k in e["gate_fail"]:
            if k == "claim_id_not_allowed":
                counts[k] += 1
    hold = [e for e in ev if e["expected_verdict"] == "HOLD"]
    pass_rows = [e for e in ev if e["expected_verdict"] == "PASS"]
    claim_rows = [e for e in ev if e["claim_set_exact"] is not None]
    semantic_rows = [e for e in ev if e["claim_set_semantic"] is not None]
    return {
        "n": n,
        "structural_pass": sum(e["structural_pass"] for e in ev),
        "schema_pass": sum(e["schema_pass"] for e in ev),
        "triple_pass": sum(e["triple_pass"] for e in ev),
        "claim_id_allowed": sum(e["claim_id_allowed"] for e in ev),
        "strict_contract_pass": sum(e["strict_contract_pass"] for e in ev),
        "core_triple_pass": sum(e["core_triple_pass"] for e in ev),
        "lenient_schema_pass": sum(e["lenient_schema_pass"] for e in ev),
        "structural_and_schema_pass": sum(e["structural_pass"] and e["schema_pass"] for e in ev),
        "verdict_accuracy": round(sum(e["verdict_ok"] for e in ev) / n, 4),
        "hold_recall": round(sum(e["verdict_ok"] for e in hold) / len(hold), 4) if hold else None,
        "always_pass_baseline": round(len(pass_rows) / n, 4),
        "claim_set_exact": round(sum(e["claim_set_exact"] for e in claim_rows) / len(claim_rows), 4) if claim_rows else None,
        "claim_set_semantic": round(sum(e["claim_set_semantic"] for e in semantic_rows) / len(semantic_rows), 4) if semantic_rows else None,
        "fail_counts": dict(counts),
        "rows": ev,
    }


HEAD_RE = re.compile(r"^`(\d{3})`\s+gold=(PASS|HOLD)\s*/\s*model=([^\s（(]+)")


def parse_report(path):
    lines = pathlib.Path(path).read_text(encoding="utf-8").splitlines()
    holdout = [json.loads(l) for l in (ROOT / "data/holdout.jsonl").read_text(encoding="utf-8").splitlines() if l.strip()]
    sections = {}
    current = None
    in_block = False
    block = []
    for line in lines:
        if line.strip() == "### base":
            current = "base"
            sections.setdefault(current, [])
            continue
        if line.strip() == "### adapter":
            current = "adapter"
            sections.setdefault(current, [])
            continue
        if current is None:
            continue
        m = HEAD_RE.match(line.strip())
        if m and not in_block:
            sections[current].append({"id": m.group(1), "expected_verdict": m.group(2), "raw_output": ""})
            continue
        if line.strip().startswith("```json"):
            in_block = True
            block = []
            continue
        if in_block and line.strip() == "```":
            in_block = False
            if sections[current]:
                sections[current][-1]["raw_output"] = "\n".join(block)
            continue
        if in_block:
            block.append(line)
    out = {}
    for name, rows in sections.items():
        for row in rows:
            idx = int(row["id"]) - 1
            if 0 <= idx < len(holdout):
                row["case_id"] = "E003"
                row["_holdout"] = holdout[idx]
                row["draft"] = holdout[idx].get("draft", "")
        out[name] = rows
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--eval", help="eval.json (JSON array)")
    ap.add_argument("--report", help="cloud Markdown report")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    if not args.eval and not args.report:
        raise SystemExit("provide --eval or --report")
    if args.report:
        payload = parse_report(args.report)
    else:
        payload = {"input": json.loads(pathlib.Path(args.eval).read_text(encoding="utf-8"))}
    result = {name: summarize(rows) for name, rows in payload.items()}
    text = json.dumps(result, ensure_ascii=False, indent=2)
    if args.out:
        pathlib.Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
