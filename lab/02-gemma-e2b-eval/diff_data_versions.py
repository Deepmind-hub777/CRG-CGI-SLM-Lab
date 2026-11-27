#!/usr/bin/env python3
"""Field-level diff for two JSONL dataset versions.

Use it to answer whether two runs saw the same task. It does not edit either
file; output is a JSON/Markdown audit record.
"""
import argparse
import hashlib
import json
import pathlib
from collections import Counter


def load(path):
    return [json.loads(l) for l in pathlib.Path(path).read_text(encoding="utf-8").splitlines() if l.strip()]


def empty_counts(rows, claim_fields):
    out = Counter()
    for r in rows:
        for c in r.get("claims", []) or []:
            for f in claim_fields:
                if not str(c.get(f, "")).strip():
                    out[f] += 1
    return dict(out)


def diff(old, new, label):
    same_ids = [r.get("id") for r in old] == [r.get("id") for r in new]
    changed = Counter()
    examples = []
    for o, n in zip(old, new):
        for k in sorted(set(o) | set(n)):
            if k in ("claims", "gold_claims"):
                continue
            if o.get(k) != n.get(k):
                changed[k] += 1
        for key in ("claims", "gold_claims"):
            oc, nc = o.get(key), n.get(key)
            if oc is None and nc is None:
                continue
            if oc is None or nc is None:
                changed[key + "_presence"] += 1
                if len(examples) < 10:
                    examples.append({"id": o.get("id"), "field": key, "old": "absent" if oc is None else "present", "new": "absent" if nc is None else "present"})
                continue
            if len(oc) != len(nc):
                changed[key + "_count"] += 1
                if len(examples) < 10:
                    examples.append({"id": o.get("id"), "field": key, "old_count": len(oc), "new_count": len(nc)})
                continue
            for i, (a, b) in enumerate(zip(oc, nc)):
                for f in sorted(set(a) | set(b)):
                    if a.get(f) != b.get(f):
                        changed[f"{key}.{f}"] += 1
                        if len(examples) < 10:
                            examples.append({"id": o.get("id"), "claim_index": i, "field": f"{key}.{f}", "old": a.get(f), "new": b.get(f)})
    return {
        "label": label,
        "old_sha256": hashlib.sha256(pathlib.Path(old[0]["_path"]).read_bytes()).hexdigest() if old and "_path" in old[0] else None,
        "new_sha256": None,
        "records_old": len(old),
        "records_new": len(new),
        "same_ids_and_order": same_ids,
        "changed_fields": dict(changed),
        "examples": examples,
        "empty_claims_old": empty_counts(old, ["subject", "predicate", "object", "evidence"]),
        "empty_claims_new": empty_counts(new, ["subject", "predicate", "object", "evidence"]),
    }


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--old", required=True)
    ap.add_argument("--new", required=True)
    ap.add_argument("--label", default="dataset")
    ap.add_argument("--out", required=True)
    ap.add_argument("--md", default="")
    args = ap.parse_args()
    old, new = load(args.old), load(args.new)
    rec = diff(old, new, args.label)
    rec["old_sha256"] = hashlib.sha256(pathlib.Path(args.old).read_bytes()).hexdigest()
    rec["new_sha256"] = hashlib.sha256(pathlib.Path(args.new).read_bytes()).hexdigest()
    pathlib.Path(args.out).write_text(json.dumps(rec, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    if args.md:
        lines = [f"# 数据差异：{args.label}", "",
                 f"- 旧：`{rec['old_sha256']}`，{rec['records_old']} 条",
                 f"- 新：`{rec['new_sha256']}`，{rec['records_new']} 条",
                 f"- ID/顺序一致：`{rec['same_ids_and_order']}`",
                 f"- 字段级变更：`{json.dumps(rec['changed_fields'], ensure_ascii=False)}`",
                 f"- 空字段（旧）：`{json.dumps(rec['empty_claims_old'], ensure_ascii=False)}`",
                 f"- 空字段（新）：`{json.dumps(rec['empty_claims_new'], ensure_ascii=False)}`",
                 "", "## 示例（最多 10 条）", ""]
        for e in rec["examples"]:
            lines.append(f"- `{json.dumps(e, ensure_ascii=False)}`")
        lines.append("")
        pathlib.Path(args.md).write_text("\n".join(lines), encoding="utf-8")
    print(json.dumps(rec, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
