# A5 零 GPU 语义审计

未加载模型；只把冻结 gold、草稿抽取、模型输出和模型 claims 分别送进同一套 claim policy。

允许 claim_id：anchor_source_external, anchor_source_inside, anchor_source_self

| 来源 | verdict 一致 | PASS recall | HOLD recall | 输出 HOLD | 分布 |
|---|---:|---:|---:|---:|---|
| gold_claims_policy | 1.0 | 1.0 | 1.0 | 4 | {'PASS': 6, 'HOLD': 4} |
| draft_engine | 1.0 | 1.0 | 1.0 | 4 | {'PASS': 6, 'HOLD': 4} |
| qwen_base_model_verdict | 0.2 | 0.0 | 0.5 | 8 | {'HOLD': 8, 'PASS': 2} |
| qwen_base_claims_policy | 0.4 | 0.0 | 1.0 | 10 | {'HOLD': 10} |
| qwen_adapter_50_model_verdict | 0.3 | 0.0 | 0.75 | 9 | {'HOLD': 9, 'PASS': 1} |
| qwen_adapter_50_claims_policy | 0.4 | 0.0 | 1.0 | 10 | {'HOLD': 10} |

## claim_id 使用

- **qwen_base**：全部 ID 落在允许表的行 0/10；不同 ID 3 个；高频 [('c1', 9), ('c2', 5), ('c001', 1)]。
- **qwen_adapter_50**：全部 ID 落在允许表的行 0/10；不同 ID 12 个；高频 [('anchor_by_model', 3), ('anchor_vector_source', 2), ('anchor_can_be_generated_by_model', 2), ('anchor_source_model', 1), ('anchor_source_weight', 1), ('anchor_is_external', 1), ('anchor_is_generated_by_model', 1), ('anchor_can_be_intrinsic', 1)]。

## 模型 verdict 与“模型 claims 经 policy 重判”的配对

- **qwen_base**：{'HOLD->HOLD': 8, 'PASS->HOLD': 2}
- **qwen_adapter_50**：{'HOLD->HOLD': 9, 'PASS->HOLD': 1}

读法：`gold_claims_policy` 与 `draft_engine` 检验规则/抽取是否复现 gold；`*_model_verdict` 是模型自己说的；`*_claims_policy` 是同一规则对模型 claims 的重判。四者不混成一个分数。
