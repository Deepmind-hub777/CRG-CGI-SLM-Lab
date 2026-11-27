#!/usr/bin/env python3
"""Shared prompt contract for training and evaluation.

This is the v2 prompt contract:
- verdict scope is the frozen claim policy, not "does the draft agree with the
  user question";
- claim_id is a closed allowlist derived from the policy for the case;
- the allowlist is rendered into the user message, not left implicit.

The prompt does not put the anchor or the full policy into the target.
"""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import claim_engine

SYSTEM = (
"你是 CRG-CGI-SLM 的 claim 抽取器。只依据用户问题与候选草稿；"
"不要补全草稿没有的断言，不要引用外部知识，不要把锚定原文当成答案。"
"判定口径：PASS 仅当草稿中的 claims 满足冻结 claim_policy 的 required_any，"
"且不含任何 forbidden_any；HOLD 为其余情况。verdict 判断对象是"
"“草稿 claims 能否被冻结锚定接受”，不是“草稿是否同意用户问题”，"
"也不是“模型自己是否相信草稿”。"
"claim_id 规则：只能使用用户消息中列出的允许 claim_id；不得自造、不得改写；"
"同一 claim_id + polarity 不要重复。"
"输出严格 JSON：claims 为数组，每项含 claim_id,subject,predicate,object,"
"polarity,kind,evidence；verdict 只能是 PASS 或 HOLD；hold_reason 为短句；"
"rollback_required 为布尔。"
)


def allowed_ids_line(case_id):
    ids = claim_engine.allowed_claim_ids(case_id)
    return "允许 claim_id：" + (", ".join(ids) if ids else "（该 case 无词表，保持原样）")


def build_prompt(tokenizer, rec):
    user = (
        f"用户问题：{rec['prompt']}\n"
        f"候选草稿：{rec['draft']}\n"
        f"锚定摘录：{rec.get('anchor_excerpt','') or '（无，仅依据草稿判断）'}\n"
        f"{allowed_ids_line(rec.get('case_id'))}\n"
        "请抽取草稿里实际出现的 claims，并给出 PASS/HOLD。"
    )
    messages = [{"role": "system", "content": SYSTEM}, {"role": "user", "content": user}]
    try:
        return tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
    except Exception:
        return f"<system>\n{SYSTEM}\n</system>\n<user>\n{user}\n</user>\n<assistant>\n"
