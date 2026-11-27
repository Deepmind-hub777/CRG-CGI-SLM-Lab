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

- [x] **A2. 重算四个 `eval.json`**
  - 已取回并重算：旧 base、旧 adapter、新 prompt base、新 prompt adapter。
  - 同一份 `rubric_v1` 下：旧两份结构 **0/10**；新 prompt 两份结构 **8/10**，严格 schema 仍 **0/10**。
  - HOLD recall 四个产物全是 **0/4**；always-PASS 基线 **0.6**；new prompt verdict 0.5 低于基线。
  - 产物：`evidence/a2-cloud/*.json`、`evidence/a2-recompute.json`、`evidence/a2-recompute.md`。
  - 旧 base 的 0.4 是文件记录值，不是本次 raw 重算值；两者已分开列。

- [x] **A3. 修 claim 三元组 schema 与 gold 存储**
  - 训练 target 与 holdout gold 已经都走 `claim_engine` 同一套抽取；不要重复做“同源”改造。
  - 真正要修的是 `claim_engine` 对 `anchor_source_*` 的空 `predicate` / `obj`：已用 `CLAIM_META` 做 canonical schema 填充，补上 `router_freeze`；evidence 仍是草稿原句。
  - `holdout.jsonl` 已补 `gold_claims`，把现场抽取变成冻结 gold。
  - 重建后：`train` 70 条 claims 的空 `object` / `predicate` 均为 **0/70**；`holdout` 11 条 gold claims 的空字段为 **0/11**。
  - 新哈希：`train=54fd202c…`，`holdout=87d2fb1b…`，`data/manifest=82e23714…`。
  - `test_candidates.py` 0 FAIL；`test_data_contract.py` 通过；`contract_eval` 单测 4/4。模型分数尚未在新数据上重跑。

- [x] **A4. Qwen3-4B 基线 + 50 条 QLoRA**
  - 底座 `Qwen3-4B-Instruct-2507`，A3 train 50 条，4-bit QLoRA，1 epoch，13 步，50.8 秒，train loss 1.2597。
  - base：结构 10/10，严格 schema 0/10，核心三元组 9/10，verdict 0.20；adapter：结构 10/10，严格 schema 5/10，核心三元组 8/10，verdict 0.30。
  - 两者都低于 always-PASS 0.60；adapter 也低于 always-HOLD 0.40。6 条 PASS 被 adapter 全判 HOLD；HOLD recall 0.75 是 HOLD 偏置的副作用。
  - 云端 `contract_ok=1.0` 只是弱门，不校验 claim 字段、polarity、kind；与严格 schema 0/10 不矛盾。
  - 产物：`evidence/qwen3-4b/*.json`、`evidence/a4-recompute.json`、`evidence/a4-recompute.md`。

- [x] **A5. 修 PASS/HOLD 语义与 claim_id 契约（零 GPU，先于扩数据）**
  - 已冻结 `governance/contract_semantics_v1.json`：PASS = 草稿 claims 满足 `required_any` 且不含 `forbidden_any`；HOLD 为其余情况；判的是“能否被冻结锚定接受”，不是“草稿是否同意用户问题”。
  - 已选定 closed allowlist + `claim_id`/`polarity` 精确匹配；允许表由 `claim_policy_v0.json` 的 `required_any + forbidden_any` 推导，不读 holdout gold；三元组匹配只作诊断。
  - 已加 `strict_contract_pass = structural + schema + full_triple + claim_id_allowed`；云端弱门只保留为解析健康度。
  - 已加 `param_stats.py`，参数量改从 safetensors index 计算；已加 `RUN_COMPLETE.json` / `EVAL_COMPLETE.json` 与 `run_watch.py` 状态机。
  - 已做 `f1072fa9` → `54fd202c` 的字段级 diff：训练集只补 60 处 `object`、24 处 `predicate`；holdout 只新增 10 条 `gold_claims`。
  - 离线语义审计：gold claims 与草稿抽取都 10/10 复现 gold；Qwen base/adapter 自己的 verdict 0.2/0.3，模型 claims 经 policy 重判都是 0.4，允许 ID 命中都是 0/10。
  - 产物：`A5-ZERO-GPU-PATCH.md`、`evidence/a5-semantic-audit.*`、`evidence/data-diff-a3-*.json`。
  - 下一步：同一 Qwen base、同一 10 条 holdout、只换 v2 prompt，跑一次不训练的 GPU 对照。

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
- [ ] 补数据前，A1–A5 必须完成

---

## D. 验收门槛

| 项目 | 门槛 |
|---|---|
| 结构合格 | base 与 adapter 都 ≥ 8/10 |
| 语义合格 | ≥ 9/10；无 `polarity:0`、`kind:"PASS"`、缺字段 |
| HOLD recall | ≥ 1/4 |
| verdict 准确率 | > 0.6 的 always-PASS 基线 |
| 退化检查 | adapter 不得低于 always-HOLD 0.4；PASS recall 不得为 0 |

达不到：查生成停止与 target 序列化，不补数据、不加 epoch、不进正式 run。

---

## E. 不要做

- 不要跨 rubric 比较 2/10、0/10、8/10。
- 不要把 8/10 结构合格当成模型能力通过。
- 不要在 claim 三元组 schema 未修好前补数据。
- 不要把“target/gold 不同源”当结论；审计已确认两边都调用同一个 `claim_engine.evaluate()`。
- 不要因为 adapter 延迟低就当成效率提升。
- 不要直推 main；所有改动走 draft PR，由 Milo 批。
