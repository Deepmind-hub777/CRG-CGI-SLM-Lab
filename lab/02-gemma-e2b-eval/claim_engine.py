#!/usr/bin/env python3
"""Claim-level -1: extract structured claims, bind roles, handle negation and conditionals.

A claim is not a keyword hit. It is:
    (claim_id, subject, predicate, object, polarity, evidence, kind)
where polarity is +1/-1 after a negation window, and kind is assertion/antecedent/consequent/hypothetical.
"""

import json, re, pathlib, sys
from dataclasses import dataclass, asdict
from typing import List, Optional

ROOT = pathlib.Path(__file__).resolve().parent

NEG = r"不|不能|不得|不可|不应|无需|不需|没有|未|无|并非|不是|禁止|严禁|拒绝"
NEG_RE = re.compile(NEG)

# Aliases are deliberately narrow. This is a lab lexicon, not a general NLU.
SELF = r"当前生成模型本身|当前生成模型|生成模型自身|生成模型本身|生成模型|模型自身|模型本身|模型自己|模型自我校准|自我校准|自身"
EXTERNAL = r"外部冻结参照|外部冻结|冻结参照|冻结锚定|外部策略|外部规则|外部参照|外部|权重之外|外置"
INSIDE = r"权重之内|权重内|可训练偏置|模型内部|权重里"

PATTERNS = {
    # E003: where does anchor come from?
    "anchor_source_self": [
        rf"锚定(?:\s*logits)?[^。；\n]{{0,18}}?(?:由|从)?(?P<src>{SELF})(?P<neg>{NEG})?(?:可|可以|能|能够|会|应|应该|必须|需要)?(?:自己|自身)?(?:提供|生成|定义|给出)",
        rf"(?P<src>{SELF})(?P<neg>{NEG})?(?:可|可以|能|能够|会|应|应该|必须|需要)?(?:自己|自身)?(?:提供|生成|定义|给出)(?:出|了)?(?:锚定(?:\s*logits)?|logits)?",
        rf"(?P<src>模型)[^。；\n]{{0,6}}?(?:可|可以|能)?(?:自己|自身)(?:提供|生成|定义|给出)(?:出|了)?(?:锚定(?:\s*logits)?|logits)",
    ],
    "anchor_source_external": [
        rf"锚定(?:\s*logits)?[^。；\n]{{0,24}}?(?:由|从|来自|必须来自|只能来自)(?P<src>{EXTERNAL})",
        rf"锚定(?:\s*logits)?[^。；\n]{{0,18}}?(?P<src>{EXTERNAL})",
    ],
    "anchor_source_inside": [
        rf"锚定(?:\s*logits)?[^。；\n]{{0,18}}?(?P<src>{INSIDE})",
    ],

    # E004: -1 is a scorer only, or a veto?
    "minus1_only_score": [
        rf"(?P<subj>-1|负一)[^。；\n]{{0,18}}?(?:只|仅|只是|仅仅)(?:负责|做|是)?(?P<pred>打分|评分|给分)",
        rf"(?P<subj>-1|负一)[^。；\n]{{0,12}}?(?:只|仅|只是|仅仅)(?:是)?(?:一个)?(?P<pred>打分器|评分器)",
    ],
    "minus1_has_veto": [
        rf"(?P<subj>-1|负一)[^。；\n]{{0,18}}?(?P<neg>{NEG})?(?:有|具有|拥有|行使|可以|能)?(?P<pred>否决权|否决|回滚)",
        rf"(?P<subj>-1|负一)[^。；\n]{{0,10}}?(?P<pred>能否决|可回滚)",
    ],
    "scoring_is_ternary": [
        rf"(?P<subj>打分|评分|三值量化|校验器|只打分)[^。；\n]{{0,18}}?(?P<neg>{NEG})?(?P<pred>算|是|属于|构成|符合|等于)[^。；\n]{{0,8}}?(?:三元算子|三元)",
        rf"(?P<subj>三元算子)[^。；\n]{{0,18}}?(?P<neg>{NEG})?(?P<pred>需要|必须|要求)[^。；\n]{{0,8}}?(?:否决|回滚)",
    ],

    # E006: router training
    "router_train": [
        rf"(?P<subj>router|路由(?:器)?)[^。；\n]{{0,18}}?(?P<neg>{NEG})?(?:要|应该|需要|必须|可以|应当)?(?P<pred>训练|训|微调)",
        rf"(?P<neg>{NEG})?(?P<pred>训练|训|微调)[^。；\n]{{0,8}}?(?P<subj>router|路由(?:器)?)",
    ],
    "router_freeze": [
        rf"(?P<subj>router|路由(?:器)?)[^。；\n]{{0,12}}?(?P<pred>冻结|固定)",
        rf"(?P<pred>冻结|固定)[^。；\n]{{0,8}}?(?P<subj>router|路由(?:器)?)",
    ],

    # E009: public repo and student essays
    "public_essay_allowed": [
        rf"(?P<subj>public(?:\s*仓库)?|公开(?:仓库)?)[^。；\n]{{0,24}}?(?P<neg>{NEG})?(?:可以|能|允许|可)?(?P<pred>放|存放|存|收录|发布|上传)[^。；\n]{{0,14}}?(?P<obj>学生[^。；\n]{{0,8}}作文|作文|学生数据)",
        rf"(?P<obj>学生[^。；\n]{{0,12}}?(?:作文|数据)|学生数据)[^。；\n]{{0,24}}?(?P<neg>{NEG})?(?P<pred>进|进入|放|存放|收录|发布|上传)(?:到|进)?\s*(?P<subj>public|公开)",
    ],
}
CLAIM_META = {
    "anchor_source_self": ("锚定来源", "self", "锚定由生成模型自身提供"),
    "anchor_source_external": ("锚定来源", "external", "锚定来自冻结参照/外部"),
    "anchor_source_inside": ("锚定位置", "inside_weights", "锚定在权重之内"),
    "minus1_only_score": ("-1 权限", "score_only", "-1 只是打分"),
    "minus1_has_veto": ("-1 权限", "veto", "-1 能否决/回滚"),
    "scoring_is_ternary": ("三元算子", "scoring_is_ternary", "打分/三值量化就是三元算子"),
    "router_train": ("router 策略", "train", "router 训练/冻结"),
    "router_freeze": ("router 策略", "freeze", "router 保持冻结"),
    "public_essay_allowed": ("public 数据", "student_essay", "public 放学生作文"),
}


@dataclass
class Claim:
    claim_id: str
    subject: str
    predicate: str
    obj: str
    polarity: int          # +1 assertion of predicate, -1 negated
    negated: bool
    kind: str              # assertion / antecedent / consequent / hypothetical
    evidence: str
    start: int
    end: int
    confidence: float


def sentences(text: str):
    # Keep offsets; split on Chinese sentence enders and newlines.
    out = []
    start = 0
    for m in re.finditer(r"[。！？；\n]", text):
        end = m.end()
        s = text[start:end].strip()
        if s:
            out.append((start, end, s))
        start = end
    if start < len(text):
        s = text[start:].strip()
        if s:
            out.append((start, len(text), s))
    return out


def has_neg_before(s: str, pred_start: int, window: int = 8):
    left = s[max(0, pred_start - window):pred_start]
    # Negation does not cross a comma/semicolon boundary.
    parts = re.split(r"[，,；;。！？]", left)
    left = parts[-1]
    return bool(NEG_RE.search(left))


def classify_kind(s: str, m: re.Match):
    """Return assertion/antecedent/consequent/hypothetical/interrogative."""
    after = s[m.end():]
    pred_pos = m.start("pred") if "pred" in m.groupdict() and m.group("pred") else m.start()
    # Question forms inside the matched span or immediately after it.
    if re.search(r"是否|吗|\?|？", m.group(0) + after[:4]):
        return "interrogative"
    # Conditional: 若/如果 ... 则/就 ...
    cond_if = re.search(r"若|如果|假如|倘若|只要|一旦", s)
    cond_then = re.search(r"则|就|便|即", s)
    if cond_if and cond_then:
        if cond_if.start() < pred_pos < cond_then.start():
            return "antecedent"
        if cond_then.start() < pred_pos:
            return "consequent"
    # Hypothetical: 会/将/导致/形成 after the claim.
    if re.search(r"会|将|导致|形成|否则", after[:14]):
        return "hypothetical"
    return "assertion"


def extract_claims(text: str) -> List[Claim]:
    claims = []
    for sent_start, _, s in sentences(text):
        for cid, pats in PATTERNS.items():
            for pat in pats:
                for m in re.finditer(pat, s):
                    gd = m.groupdict()
                    src = gd.get("src") or gd.get("subj") or ""
                    pred = gd.get("pred") or ""
                    obj = gd.get("obj") or ""
                    # Canonical schema fill: the regex may capture only the role,
                    # leaving predicate/object empty. CLAIM_META is the frozen
                    # display triple, not new evidence; evidence stays the draft.
                    meta = CLAIM_META.get(cid)
                    if meta:
                        if not src.strip():
                            src = meta[0]
                        if not pred.strip():
                            pred = meta[1]
                        if not obj.strip():
                            obj = meta[2]
                    # Negation: group neg, or a negator inside the matched predicate phrase,
                    # after the last punctuation boundary.
                    neg = bool(gd.get("neg"))
                    if not neg:
                        pred_pos = m.start("pred") if "pred" in gd and gd.get("pred") else m.end()
                        left = s[max(0, m.start() - 8):pred_pos]
                        left = re.split(r"[，,；;。！？]", left)[-1]
                        neg = bool(NEG_RE.search(left))
                    pol = -1 if neg else 1
                    kind = classify_kind(s, m)
                    # If a claim is in a conditional antecedent, it is not asserted.
                    claims.append(Claim(
                        claim_id=cid,
                        subject=src.strip(),
                        predicate=pred.strip(),
                        obj=obj.strip(),
                        polarity=pol,
                        negated=neg,
                        kind=kind,
                        evidence=s.strip(),
                        start=sent_start + m.start(),
                        end=sent_start + m.end(),
                        confidence=0.8 if kind == "assertion" else 0.5,
                    ))
    # Deduplicate near-identical claims within a sentence.
    seen = set()
    out = []
    for c in claims:
        key = (c.claim_id, c.polarity, c.kind, c.evidence)
        if key in seen:
            continue
        seen.add(key)
        out.append(c)
    return out


def load_policy(path=None):
    p = pathlib.Path(path) if path else ROOT / "governance" / "claim_policy_v0.json"
    return json.loads(p.read_text(encoding="utf-8"))


def evaluate(text: str, case_id: str, policy=None):
    policy = policy or load_policy()
    spec = policy["cases"][case_id]
    claims = extract_claims(text)

    def supported(ref):
        cid = ref["claim"]
        want = ref["polarity"]
        for c in claims:
            if c.claim_id != cid or c.polarity != want:
                continue
            if c.kind in ("antecedent", "hypothetical", "interrogative"):
                continue
            return c
        return None

    reasons = []
    req = None
    for ref in spec.get("required_any", []):
        c = supported(ref)
        if c:
            req = c
            break
    if req is None:
        reasons.append({
            "type": "missing_required",
            "need_any": spec.get("required_any", []),
            "claims": [asdict(c) for c in claims],
        })

    bad = []
    for ref in spec.get("forbidden_any", []):
        c = supported(ref)
        if c:
            bad.append(c)
            reasons.append({
                "type": "forbidden_claim",
                "claim": ref,
                "evidence": c.evidence,
                "subject": c.subject,
                "predicate": c.predicate,
                "polarity": c.polarity,
            })

    verdict = "HOLD" if reasons else "PASS"
    return {
        "case": case_id,
        "verdict": verdict,
        "claims": [asdict(c) for c in claims],
        "reasons": reasons,
        "required_evidence": asdict(req) if req else None,
        "forbidden_evidence": [asdict(c) for c in bad],
    }


def cmd_eval(args):
    text = args.text or sys.stdin.read()
    result = evaluate(text, args.case, load_policy(args.policy) if args.policy else None)
    print(json.dumps(result, ensure_ascii=False, indent=2))


def cmd_calibrate(args):
    import csv
    rows = []
    with open(args.file, encoding="utf-8") as f:
        for line in f:
            if line.strip():
                rows.append(json.loads(line))
    policy = load_policy(args.policy) if args.policy else load_policy()
    passed = 0
    for r in rows:
        res = evaluate(r["text"], r["case"], policy)
        ok = res["verdict"] == r["expect"]
        passed += ok
        print(f"{r['id']:>4} expect={r['expect']:>4} got={res['verdict']:>4} {'OK' if ok else 'MISMATCH'}  {r['text'][:70]}")
        if not ok:
            print("     reasons:", json.dumps(res["reasons"], ensure_ascii=False)[:400])
    print(f"calibration: {passed}/{len(rows)}")


if __name__ == "__main__":
    import argparse
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    p = sub.add_parser("eval"); p.add_argument("--case", required=True); p.add_argument("--text"); p.add_argument("--policy")
    p = sub.add_parser("calibrate"); p.add_argument("--file", required=True); p.add_argument("--policy")
    args = ap.parse_args()
    if args.cmd == "eval":
        cmd_eval(args)
    else:
        cmd_calibrate(args)
