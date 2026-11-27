# NEXT-ACTIONS · Gemma 4 E2B 阶段 01 → 阶段 02

**状态：** 不启动正式 run，不补数据，先修口径。
**原则：** 先校准尺子，再量模型；现在补数据，等于把错误的 target 口径放大。

---

## A. 先做（0 GPU，云端执行，豆包验收）

- [x] **A1. 冻结 rubric**
  - 已产出 `rubric_v1.json` 与 `contract_eval.py`。
  - 结构：单对象根、无围栏、顶层 `verdict`、`claims` 数组、无重复键、未截断。
  - 语义：`polarity ∈ {±1}`、`kind` 枚举、三元组非空、`evidence` 完整、禁止 `kind:"PASS"`。
  - 输出失败分类：`fence / truncated / dupkey / missing_verdict / array_root / bad_polarity / bad_kind / missing_field`。
  - 云端报告重算结果：结构 8/10、核心三元组 8/10、宽松 schema 7/10（base）/0（adapter）、严格 schema 0/10、完整三元组 0/10。

- [ ] **A2. 重算四个 `eval.json`**
  - `runs/base/eval.json`（旧）
  - `runs/smoke-v100c-20261127-1011/eval.json`（旧）
  - 新 prompt 的 base / adapter 对照结果
  - 全部用同一份 rubric；输出结构合格率、语义合格率、HOLD recall、verdict 准确率、always-PASS 基线。

- [x] **A3. 修 claim 三元组 schema 与 gold 存储**
  - 训练 target 与 holdout gold 已经都走 `claim_engine` 同一套抽取；不要重复做“同源”改造。
  - 真正要修的是 `claim_engine` 对 `anchor_source_*` 的空 `predicate` / `obj`：已用 `CLAIM_META` 做 canonical schema 填充，补上 `router_freeze`；evidence 仍是草稿原句。
  - `holdout.jsonl` 已补 `gold_claims`，把现场抽取变成冻结 gold。
  - 重建后：`train` 70 条 claims 的空 `object` / `predicate` 均为 **0/70**；`holdout` 11 条 gold claims 的空字段为 **0/11**。
  - 新哈希：`train=54fd202c…`，`holdout=87d2fb1b…`，`data/manifest=82e23714…`。
  - `test_candidates.py` 0 FAIL；`test_data_contract.py` 通过；`contract_eval` 单测 4/4。模型分数尚未在新数据上重跑。

---

## B. 再做（10 条 GPU A/B，不正式 run）

- [ ] `temperature=0`
- [ ] `repetition_penalty=1.0` vs `1.05` 做 A/B
- [ ] `max_new_tokens=768`，围栏即停
- [ ] 记录 `finish_reason`
- [ ] 只判断尾部稳定性与 HOLD 是否开始出现

---

## C. 最后才补数据

- [ ] 200–300 条，优先补完整负例三元组
- [ ] 配比暂定：40% HOLD 负例、20% 双重否定/条件前件、20% 中文三元组与契约样板、10% 长 claim/截断、10% PASS 对照
- [ ] epoch 先保持 1
- [ ] 补数据前，A1–A3 必须完成

---

## D. 验收门槛

| 项目 | 门槛 |
|---|---|
| 结构合格 | base 与 adapter 都 ≥ 8/10 |
| 语义合格 | ≥ 9/10；无 `polarity:0`、`kind:"PASS"`、缺字段 |
| HOLD recall | ≥ 1/4 |
| verdict 准确率 | > 0.6 的 always-PASS 基线 |

达不到：查生成停止与 target 序列化，不补数据、不加 epoch、不进正式 run。

---

## E. 不要做

- 不要跨 rubric 比较 2/10、0/10、8/10。
- 不要把 8/10 结构合格当成模型能力通过。
- 不要在 claim 三元组 schema 未修好前补数据。
- 不要把“target/gold 不同源”当结论；审计已确认两边都调用同一个 `claim_engine.evaluate()`。
- 不要因为 adapter 延迟低就当成效率提升。
- 不要直推 main；所有改动走 draft PR，由 Milo 批。
