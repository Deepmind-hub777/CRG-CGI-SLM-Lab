# Contract Eval v1 · 结果摘要

**输入：** `evidence/e2b-contract-eval-report.md`（云端 1+2 对照的原始 JSON 输出，只读证据）  
**执行：** `python3 contract_eval.py --report evidence/e2b-contract-eval-report.md`  
**GPU：** 0（只解析已落盘报告，不重跑模型）  
**日期：** 2026-11-27

## 汇总

| 指标 | base | adapter |
|---|---:|---:|
| n | 10 | 10 |
| 结构合格 | 8/10 | 8/10 |
| 核心三元组非空（诊断） | 8/10 | 8/10 |
| 宽松 schema（接受 positive/negative、fact/restriction 别名） | 7/10 | **0/10** |
| schema 合格（严格） | **0/10** | **0/10** |
| 完整三元组（严格） | **0/10** | **0/10** |
| verdict 准确率 | 0.5 | 0.5 |
| HOLD recall | 0/4 | 0/4 |
| always-PASS 基线 | 0.6 | 0.6 |
| claim set 精确率 | 无法计算（0 条合同合格） | 无法计算（0 条合同合格） |

## 失败分类计数

| 失败类 | base | adapter |
|---|---:|---:|
| bad_polarity | 12 | 13 |
| bad_kind | 12 | 11 |
| missing_field | 0 | 24 |
| missing_verdict | 1 | 0 |
| trailing | 1 | 0 |
| truncated | 0 | 2 |
| bad_json | 0 | 2 |

> 计数是“失败项次数”，不是样本数；同一条样本可能同时有多个 claim 失败。

## 结论

1. **8/10 只是结构合格；核心三元组也是 8/10。** 两边在有效样本里都能给出非空的 claim_id / subject / predicate / object，内容层不是“全空”。
2. **base 的严格 0/10 主要是 harness 严格度。** 它把 `polarity` 写成 `"positive"` / `"negative"`、`kind` 写成 `fact` / `restriction`；放宽别名后是 **7/10**，按 target 的 `±1` + 枚举才是 0/10。
3. **adapter 的 0/10 不能全推给 harness。** 即使放宽别名，它仍是 **0/10**：`polarity:0`、`kind:"PASS"`、claims 缺 `polarity/kind/evidence`，另有 2 条截断。这里有 prompt/schema 没说清的部分，但输出确实不合契约。
4. **HOLD recall 0/4，verdict 0.5 < always-PASS 0.6。** 这是模型行为，不是 rubric 造成的。
5. **claim set 旧 0.1 不能当能力指标。** 唯一“精确匹配”的样本是结构不合格的 base 005；在“结构 + schema 都合格”的门槛下，没有可计算样本。

## 边界

- 这是对已有云端报告的重算，不是新的 GPU run；不声称提升、不声称准确。
- 统一 rubric 定义在 `rubric_v1.json`；没有第二套口径。
- 阶段 01 的结论不变：链路通过，模型 gate 未通过，不进入正式 run。
