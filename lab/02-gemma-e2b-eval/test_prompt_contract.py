#!/usr/bin/env python3
"""Prompt contract test. No model, no GPU."""
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import prompt_contract


class Tok:
    def apply_chat_template(self, messages, tokenize=False, add_generation_prompt=True):
        return messages[0]["content"] + "\n" + messages[1]["content"]


def main():
    rec = {"prompt": "锚定 logits 可以由当前生成模型自己提供吗？", "draft": "锚定由冻结参照给出。", "anchor_excerpt": "", "case_id": "E003"}
    p = prompt_contract.build_prompt(Tok(), rec)
    assert "不是“草稿是否同意用户问题”" in p
    for cid in ("anchor_source_external", "anchor_source_inside", "anchor_source_self"):
        assert cid in p
    assert "只能使用用户消息中列出的允许 claim_id" in p
    print("prompt_contract tests: OK")


if __name__ == "__main__":
    main()
