#!/usr/bin/env python3
"""A4: recompute Qwen3-4B base and 50-record QLoRA adapter with rubric_v1.

The cloud eval ran on the pre-A3 holdout (same prompt/draft, only gold_claims
absent). This script attaches the frozen A3 holdout and recomputes claim sets
against A3 gold, plus trivial baselines and pass/hold recalls.
"""
import hashlib
import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import contract_eval

CASES = {
    "qwen_base": "evidence/qwen3-4b/base_eval.json",
    "qwen_adapter_50": "evidence/qwen3-4b/adapter_eval.json",
}
MODEL = "Qwen3-4B-Instruct-2507"
PROMPT = "same contract prompt; 768 tokens; greedy; qwen chat template"


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
    for label, rel in CASES.items():
        path = ROOT / rel
        rows = load_rows(path)
        for i, row in enumerate(rows):
            row["case_id"] = "E003"
            row["_holdout"] = holdout[i]
            row["draft"] = holdout[i].get("draft", "")
        summary = contract_eval.summarize(rows)
        ev = summary["rows"]
        pass_rows = [e for e in ev if e["expected_verdict"] == "PASS"]
        hold_rows = [e for e in ev if e["expected_verdict"] == "HOLD"]
        raw_claim_exact = sum(1 for e in ev if e["claim_set_exact"] is True)
        summary["pass_recall"] = round(sum(e["verdict_ok"] for e in pass_rows) / len(pass_rows), 4) if pass_rows else None
        summary["hold_recall"] = round(sum(e["verdict_ok"] for e in hold_rows) / len(hold_rows), 4) if hold_rows else None
        summary["always_hold_baseline"] = round(len(hold_rows) / len(ev), 4) if ev else None
        summary["raw_claim_set_exact"] = round(raw_claim_exact / len(ev), 4) if ev else None
        summary["cloud_contract_ok_rate"] = 1.0
        out[label] = {
            "source": rel,
            "sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
            "model": MODEL,
            "prompt": PROMPT,
            "summary": {k: v for k, v in summary.items() if k != "rows"},
            "rows": summary["rows"],
        }
    text = json.dumps(out, ensure_ascii=False, indent=2)
    (ROOT / "evidence/a4-recompute.json").write_text(text + "\n", encoding="utf-8")

    lines = ["# A4: Qwen3-4B 契约基线 + 50 条 QLoRA（离线复算）", "",
             "统一 `rubric_v1`；模型输出未重跑，只按 A3 冻结 gold 重算。", "",
             "| 产物 | 结构 | 严格 schema | 宽松 schema | 核心三元组 | verdict | always-PASS | always-HOLD | HOLD recall | PASS recall | claim set |",
             "|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|"]
    for label, item in out.items():
        s = item["summary"]
        lines.append(
            f"| {label} | {s['structural_pass']}/10 | {s['schema_pass']}/10 | "
            f"{s['lenient_schema_pass']}/10 | {s['core_triple_pass']}/10 | "
            f"{s['verdict_accuracy']} | {s['always_pass_baseline']} | {s['always_hold_baseline']} | "
            f"{s['hold_recall']} | {s['pass_recall']} | {s.get('claim_set_exact')} |"
        )
    lines += ["", "## 失败分布", ""]
    for label, item in out.items():
        lines.append(f"- **{label}**：{json.dumps(item['summary']['fail_counts'], ensure_ascii=False)}")
    lines += ["", "## 读法", "",
              "- `contract_ok_rate=1.0` 是云端弱门：只查单对象根、`verdict` 与 `claims` 列表，不查 claim 字段、polarity、kind。",
              "- 严格 schema 下 base 0/10、adapter 5/10；宽松 schema base 2/10、adapter 5/10。",
              "- base 与 adapter 都低于 always-PASS 0.60；adapter 0.30 也低于 always-HOLD 0.40。",
              "- adapter 在 6 条 PASS 上全部输出 HOLD；HOLD recall 0.75 不能当总体能力。",
              "- claim set 在严格合格样本上：base 不可计算（0 条合格），adapter 0.0；本机 raw 计数 base 0.0、adapter 0.0。",
              "- 云端 summary 的 `claim_set_exact_rate` 是旧 gold/engine 口径：base 0.1、adapter 0.0；不与本机 strict 复算混用。",
              "- 主要缺口不是 JSON 语法，而是 (a) PASS/HOLD 语义未在 prompt 定义；(b) claim_id 词表未给模型；(c) 云端 contract gate 过弱。",
              "",
              "## 参数量核对",
              "",
              "- `model.safetensors.index.json` 的 `total_size=8,045,591,552` bytes；按 bf16 每参数 2 bytes 估算约 **4.023B** 参数。",
              "- `trainable=33,030,144`，真实占比 **0.821%**；manifest 里的 `2.238B / 1.475%` 是 4-bit 加载后的 `numel()` 伪影，不用作分母。",
              "- 细表：`evidence/qwen3-4b/param_check.json`。",
              ""]
    (ROOT / "evidence/a4-recompute.md").write_text("\n".join(lines), encoding="utf-8")
    print("\n".join(lines))


if __name__ == "__main__":
    main()
