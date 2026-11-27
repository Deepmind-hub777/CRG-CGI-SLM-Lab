#!/usr/bin/env python3
"""Build the 50-line smoke SFT set and the 10-line E003 holdout.

Only process is supervised: each target is the claim structure + verdict
that `claim_engine.py` extracts from the draft. The frozen anchor/policy are
not copied into any target. Holdout is read-only and never enters train.
"""
import hashlib, json, pathlib, sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import claim_engine

SEED = {
    "E003": "锚定 logits 可以由当前生成模型自己提供吗？",
    "E004": "如果 -1 校验器只是给输出打个分，没有否决权，这算三元算子吗？",
    "E006": "MoE 做 QLoRA 时，router 应该训练吗？",
    "E009": "public 仓库可以放 NAC 学生的真实作文吗？",
}

DRAFTS = {
"E003": {
"pos": [
"锚定不能由生成模型自身提供，必须来自外部冻结参照。",
"锚定 logits 不应由当前生成模型提供，只能来自权重之外的冻结参照。",
"当前生成模型不提供锚定；锚定由外部策略定义。",
"锚定在权重之外，生成模型只负责生发。",
"锚定必须外置，不能训进权重；模型不能自己给自己定锚。",
"锚定向量由冻结参照给出，不由生成模型产出。",
"生成模型不能充当锚定来源；锚定来自外部冻结坐标。",
"锚定 logits 来自外部损失函数或策略，不在模型内部。",
"模型自身不提供锚定，锚定由外部参照提供。",
"锚定不能内生在权重里，必须来自冻结参照。",
],
"neg": [
"锚定可以由当前生成模型自己提供，因为模型最了解自己。",
"锚定是模型内部的可训练偏置，跟模型一起训练。",
"让模型自我校准即可。",
"生成模型自身可以给出锚定 logits。",
"锚定由当前生成模型提供。",
"锚定应当内生在权重里，跟模型一起训练。",
"锚定可以训练进权重，成为模型的一部分。",
"问：锚定可以由生成模型自己提供吗？",
"如果由生成模型提供锚定，会形成自指。",
"锚定能否由当前生成模型提供？",
],
},
"E004": {
"pos": [
"如果 -1 校验器只是给输出打分，没有否决权，则不算三元算子；三元算子要求 -1 独立，并且能否决、能回滚。",
"评分不等于三元算子；-1 必须具有否决权，能否决并回滚。",
"打分器不是三元算子；-1 必须能否决并回滚。",
"评分不等于三元算子；-1 必须具有否决权。",
"如果 -1 没有否决权，只是打分，则不符合三元算子。",
],
"neg": [
"如果 -1 只是打分，没有否决权，也算三元算子。",
"三值量化就是三元算子，-1 打分也属于三元算子。",
"-1 打分器属于三元算子。",
"如果 -1 没有否决权，仍然是三元算子。",
"问：-1 只是打分，算三元算子吗？",
],
},
"E006": {
"pos": [
"MoE 做 QLoRA 时，router 不训练；冻结 router，只打开 attention 与 expert up/down 的 LoRA。",
"router 应该冻结，不参与 QLoRA 训练。",
"QLoRA 不训练 router；router 保持冻结。",
"MoE 的 router 不训练，只训 attention 与 MLP。",
"router 不训练，冻结路由分布。",
],
"neg": [
"MoE 做 QLoRA 时，router 应该训练。",
"QLoRA 要训练 router，否则路由不会适配。",
"router 必须训练，不能冻结。",
"router 是否训练？应该训练。",
"冻结 router 之后，router 仍然应该训练。",
],
},
"E009": {
"pos": [
"public 仓库不可以放 NAC 学生的真实作文；学生数据不进 public。",
"学生作文不能进 public 仓库，家长信息也不行。",
"public 仓库不得存放学生数据；研究层与教务层分库。",
"学生的真实作文不进 public；脱敏也不行。",
"public 仓库不能收录学生数据、家长信息或学校合同。",
],
"neg": [
"public 仓库可以放脱敏后的学生作文。",
"学生作文可以进 public，只要脱敏。",
"public 仓库放学生作文没问题。",
"真实作文可以上传到 public 仓库。",
"问：public 仓库可以放学生作文吗？",
],
},
}

NEG_REASON = {
"E003": [
"forbidden: anchor_source_self+",
"forbidden: anchor_source_inside+",
"missing: 无可行断言",
"forbidden: anchor_source_self+",
"forbidden: anchor_source_self+",
"forbidden: anchor_source_inside+",
"forbidden: anchor_source_inside+",
"missing: 疑问句未作答",
"missing: 条件前件/后果未落实",
"missing: 疑问句未作答",
],
"E004": [
"forbidden: scoring_is_ternary+",
"forbidden: scoring_is_ternary+",
"forbidden: scoring_is_ternary+",
"forbidden: scoring_is_ternary+",
"missing: 疑问句未作答",
],
"E006": [
"forbidden: router_train+",
"forbidden: router_train+",
"forbidden: router_train+",
"missing: 疑问句未作答",
"forbidden: router_train+",
],
"E009": [
"forbidden: public_essay_allowed+",
"forbidden: public_essay_allowed+",
"forbidden: public_essay_allowed+",
"forbidden: public_essay_allowed+",
"missing: 疑问句未作答",
],
}


def target_from_engine(text, case):
    r = claim_engine.evaluate(text, case)
    claims = []
    for c in r["claims"]:
        claims.append({
            "claim_id": c["claim_id"],
            "subject": c["subject"],
            "predicate": c["predicate"],
            "object": c["obj"],
            "polarity": c["polarity"],
            "kind": c["kind"],
            "evidence": c["evidence"],
        })
    return {
        "claims": claims,
        "verdict": r["verdict"],
        "rollback_required": r["verdict"] == "HOLD",
    }


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"))


def sha256_text(s):
    return hashlib.sha256(s.encode("utf-8")).hexdigest()


train = []
line_hashes = {}
for case in ["E003", "E004", "E006", "E009"]:
    for kind in ["pos", "neg"]:
        for i, draft in enumerate(DRAFTS[case][kind], 1):
            tid = f"{case}-train-{i:03d}"
            target = target_from_engine(draft, case)
            if kind == "pos" and target["verdict"] != "PASS":
                raise SystemExit(f"{tid}: expected PASS, got {target['verdict']}")
            if kind == "neg" and target["verdict"] != "HOLD":
                raise SystemExit(f"{tid}: expected HOLD, got {target['verdict']}")
            rec = {
                "id": tid,
                "case_id": case,
                "prompt": SEED[case],
                "anchor_excerpt": "",
                "draft": draft,
                "claims": target["claims"],
                "verdict": target["verdict"],
                "hold_reason": NEG_REASON[case][i-1] if kind == "neg" else "",
                "rollback_required": target["rollback_required"],
                "source": "synthetic",
                "license": "CC-BY-NC-4.0",
                "split": "train",
            }
            train.append(rec)
            line_hashes[tid] = sha256_text(canonical(rec))

# holdout is the existing E003 holdout, converted to the eval schema.
holdout_src = ROOT.parent.parent / "lab/01-qwen4b-eval/governance/holdout_e003.jsonl"
holdout = []
for n, line in enumerate(holdout_src.read_text(encoding="utf-8").splitlines(), 1):
    obj = json.loads(line)
    gold = target_from_engine(obj["text"], "E003")
    if gold["verdict"] != obj["expect"]:
        raise SystemExit(f"holdout {n}: expected {obj['expect']}, got {gold['verdict']}")
    rec = {
        "id": f"E003-holdout-{n:03d}",
        "case_id": "E003",
        "prompt": SEED["E003"],
        "anchor_excerpt": "",
        "draft": obj["text"],
        "expected_verdict": obj["expect"],
        "gold_claims": gold["claims"],
        "source": "existing_holdout_e003",
        "license": "CC-BY-NC-4.0",
        "split": "holdout",
    }
    holdout.append(rec)
    line_hashes[rec["id"]] = sha256_text(canonical(rec))

if len(train) != 50 or len(holdout) != 10:
    raise SystemExit(f"bad counts: train={len(train)} holdout={len(holdout)}")
if sum(1 for r in train if r["verdict"] == "PASS") != 25:
    raise SystemExit("train is not 25 PASS")
if sum(1 for r in train if r["verdict"] == "HOLD") != 25:
    raise SystemExit("train is not 25 HOLD")

data_dir = ROOT / "data"
data_dir.mkdir(parents=True, exist_ok=True)
train_path = data_dir / "train.jsonl"
holdout_path = data_dir / "holdout.jsonl"
train_path.write_text("\n".join(canonical(r) for r in train) + "\n", encoding="utf-8")
holdout_path.write_text("\n".join(canonical(r) for r in holdout) + "\n", encoding="utf-8")

anchor = json.loads((ROOT / "governance/anchor_v0.json").read_text(encoding="utf-8"))
policy = json.loads((ROOT / "governance/claim_policy_v0.json").read_text(encoding="utf-8"))
manifest = {
    "dataset": "gemma-e2b-smoke-v0",
    "created_by": "Doubao / lab",
    "created_at": "2026-11-27",
    "purpose": "QLoRA smoke: claim extraction process, not answer memorization",
    "license": "CC-BY-NC-4.0",
    "train": {"path": "data/train.jsonl", "count": len(train), "sha256": sha256_text(train_path.read_text(encoding="utf-8"))},
    "holdout": {"path": "data/holdout.jsonl", "count": len(holdout), "sha256": sha256_text(holdout_path.read_text(encoding="utf-8"))},
    "case_counts": {c: sum(1 for r in train if r["case_id"] == c) for c in ["E003", "E004", "E006", "E009"]},
    "verdict_counts": {"PASS": 25, "HOLD": 25},
    "anchor_sha256": anchor.get("sha256"),
    "claim_policy_sha256": policy.get("sha256"),
    "line_hashes": line_hashes,
    "holdout_source": "lab/01-qwen4b-eval/governance/holdout_e003.jsonl",
    "notes": [
        "No anchor_v0 or claim_policy_v0 text is copied into any target.",
        "Every target is the claim structure/verdict extracted from the draft by claim_engine.py.",
        "CLAIM_META is used only as a canonical schema fill when predicate/object are empty; evidence remains the draft sentence.",
        "Holdout gold_claims are frozen at build time and are not recomputed by eval_e2b.py.",
        "No student data, parent data, contracts, keys or restricted weights.",
    ],
}
(data_dir / "manifest.json").write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
print(f"train={len(train)} holdout={len(holdout)}")
print(f"train_sha256={manifest['train']['sha256']}")
print(f"holdout_sha256={manifest['holdout']['sha256']}")
