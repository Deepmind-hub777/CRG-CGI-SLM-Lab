# A5 初步训练总盘点：Qwen base、50 条 QLoRA、v2 prompt 对照

> 边界：本文件只盘点本次链路的事实、未决问题和候选下一步；不做通过/失败判断，不做模型排名，不把一次 smoke 写成能力结论。
> 所有 `strict` 数字按 `rubric_v1 contract-v1.1`；所有 `claims → policy` 数字是把模型输出的 claims 交给冻结 `claim_policy_v0.json` 重判，不是模型自评。

## 1. 本次链路

| 环节 | 内容 |
|---|---|
| 训练 | Qwen3-4B-Instruct-2507，A3 `train.jsonl` 50 条，4-bit NF4 QLoRA，1 epoch |
| run id | `qwen3-qlora-50-20261127-1340` |
| 训练结果 | 13 步，50.8 秒，`train_loss=1.2597`；日志末步可见 loss 0.511 |
| 可训练参数 | 33,030,144；真实参数约 4.023B；占比 0.821% |
| A4 base 评测 | 同一 10 条 holdout，旧 prompt；`evidence/qwen3-4b/base_eval.json` |
| A4 adapter 评测 | 同一 10 条 holdout，旧 prompt；`evidence/qwen3-4b/adapter_eval.json` |
| A5 对照 | 同一 Qwen base、同一 10 条 holdout、同一 greedy/768 设置，只换 v2 prompt（PASS/HOLD 语义 + `claim_id` 允许表） |
| A5 结果 | `evidence/qwen3-4b/base_prompt_v2_eval.json`；`eval.json` sha256 `18e2c8e2…`；平均 18.17 秒 |

## 2. 三层结果（同一把尺子）

| 指标 | A4 Qwen base | A4 Qwen + 50 QLoRA | A5 Qwen base + v2 prompt |
|---|---:|---:|---:|
| 结构合格 | 10/10 | 10/10 | 10/10 |
| 严格 schema | 0/10 | 5/10 | 0/10 |
| 宽松 schema | 2/10 | 5/10 | 2/10 |
| 核心三元组 | 9/10 | 8/10 | 8/10 |
| `claim_id_allowed` | 0/10 | 0/10 | 10/10 |
| `strict_contract_pass` | 0/10 | 0/10 | 0/10 |
| verdict 一致率 | 0.20 | 0.30 | 0.30 |
| 输出 HOLD 条数 | 8/10 | 9/10 | 4/10 |
| HOLD recall | 2/4 | 3/4 | 1/4 |
| PASS recall | 0/6 | 0/6 | 2/6 |
| always-PASS 基线 | 0.60 | 0.60 | 0.60 |
| always-HOLD 基线 | 0.40 | 0.40 | 0.40 |
| 模型 claims → policy 重判 | 0.40 | 0.40 | 0.80 |
| 模型 verdict = 自己 claims 的 policy 重判 | 8/10 | 9/10 | 5/10 |
| 与 A3 gold 的 claim set 精确匹配 | 0/10 | 0/10 | 2/10 |

`claim_set` 的精确匹配按 `(claim_id, polarity)` 计算；v2 的 polarity 是字符串，复算时用 alias-aware 归一化，仅作诊断，不进 strict gate。

云端 summary 另记 `claim_set_exact_rate=0.1`。`eval_e2b.claim_set()` 对 polarity 调用 `int()`；v2 的 16 条 claims 全是 `positive/negative` 字符串，转换抛错后该行集合为空；唯一 `claim_set_match=true` 的 005 行模型 claims 非空。这个 0.1 需要先重算再解释。

## 3. 逐条 verdict

| id | gold | A4 base | A4 adapter | A5 v2 base | v2 claims → policy |
|---|---:|---:|---:|---:|---:|
| `E003-holdout-001` | PASS | HOLD | HOLD | PASS | PASS |
| `E003-holdout-002` | PASS | HOLD | HOLD | HOLD | HOLD |
| `E003-holdout-003` | PASS | HOLD | HOLD | HOLD | PASS |
| `E003-holdout-004` | PASS | HOLD | HOLD | PASS | PASS |
| `E003-holdout-005` | HOLD | PASS | HOLD | PASS | HOLD |
| `E003-holdout-006` | HOLD | HOLD | HOLD | HOLD | HOLD |
| `E003-holdout-007` | PASS | HOLD | HOLD | HOLD | HOLD |
| `E003-holdout-008` | HOLD | HOLD | PASS | PASS | HOLD |
| `E003-holdout-009` | PASS | HOLD | HOLD | HOLD | PASS |
| `E003-holdout-010` | HOLD | PASS | HOLD | PASS | HOLD |

A5 v2 与 A4 base 的 verdict 有 7/10 相同；变化的是 001、004（HOLD→PASS）和 008（HOLD→PASS）。

## 4. schema 与 claim_id 事实

- A5 v2 的 16 条 claims 全部使用字符串 polarity：`positive` 10 条、`negative` 6 条；严格 schema 要求整数 `1/-1`，所以 `bad_polarity=16`。
- A5 v2 的 kind 分布：`source` 5、`assertion` 5、`definition` 3、`existence` 3；严格枚举只接受 `assertion/antecedent/consequent/hypothetical/interrogative`，所以 `bad_kind=11`。
- A5 v2 的 claim_id 全部落在 E003 允许表：`anchor_source_inside` 7 次、`anchor_source_external` 6 次、`anchor_source_self` 3 次；`claim_id_allowed=10/10`。
- A4 base 的 claim_id 是 `c1` 9 次、`c2` 5 次、`c001` 1 次；允许表命中 0/10。
- A4 adapter 有 12 个自造 claim_id；最高频 `anchor_by_model` 3 次；允许表命中 0/10。
- A4 adapter 的 polarity 出现 `"1"`、`"-1"`、`true`、`false`、`0`；严格 schema 仍只接受整数 `1/-1`。

## 5. 训练、数据与运行事实

- 训练集 A3 hash `54fd202c…`；holdout A3 hash `87d2fb1b…`。
- A5 云端 holdout 仍是 A3 前版本 `6d9de69e…`，prompt/draft 与 A3 相同，只缺 `gold_claims`。v2 的 `eval.json` 用云端旧 holdout 生成；本机 gold 对账用 A3 holdout。
- 云端实际代码哈希：`prompt_contract.py c96ddcef…`、`claim_engine.py b2e7c9f9…`、`eval_e2b.py 9d33db28…`。
- A5 运行在 `e2b-smoke-v100c`，V100-SXM2-16GB；模型加载约 5 秒，10 条平均 18.17 秒；`EVAL_COMPLETE.json` 记录 `finished_at=2026-11-27T14:38:25+0800`。
- 运行期间终端两次显示 Disconnected；进程仍在，产物完整；证据通过云端文件 API 下载，`eval.json` 的 sha256 与 `EVAL_COMPLETE.json` 的 `eval_sha256` 一致。
- A5 v2 云端 `json_ok=10/10`；A4 base/adapter 云端 `json_ok` 也都是 10/10。
- 训练是单 run、单 seed、1 epoch；没有重复 run，没有 seed 方差，也没有训练集复现评测。

## 6. 未决问题

### A. 这次 v2 对照改变了什么

1. **verdict 0.20 → 0.30 是 prompt 语义带来的，还是 3 条样本的抖动？** 同一 base、同一 holdout、同一 greedy，但只跑了一次；001/004/008 三条变化足以改变一位小数。
2. **claim_id 0/10 → 10/10 是否只证明“词表被看见”，没有证明“claim 被抽对”？** v2 的 claim_id 全在允许表，但 exact set 只有 2/10；这两个维度要不要分开报？
3. **模型 claims 的 policy 重判 0.80，与模型自己 verdict 0.30，差距来自哪里？** 是 verdict 头没有执行 policy，还是它在判“草稿是否同意问题”？
4. **模型 verdict 与自己 claims 的 policy 重判只有 5/10 一致，这是否意味着应把 verdict 交给确定性 policy 引擎？** 若这样做，模型的职责是否只剩 claim 抽取？
5. **v2 的 005/008/010 都是模型 PASS、policy HOLD；003/009 是模型 HOLD、policy PASS。** 这些分歧是 claim 漏抽、极性反了，还是 verdict 规则没进模型？

### B. 尺子与指标

6. **strict gate 0/10 该归因给模型还是当前 prompt/schema 契约？** prompt 只写了 `polarity` 字段，没有写“必须是整数 1/-1”，也没有列 `kind` 枚举；模型输出 `positive/negative` 和 `source/definition/existence`。
7. **`kind` 应该收紧到五个枚举，还是允许 `source/definition/existence` 这类语义 kind？** 这会影响 strict schema 和后续训练 target，不应只改评测端。
8. **`claim_set_exact_rate` 的云端 0.1 是否是空集伪影？** `int("positive")` 抛错后集合为空；005 行模型 claims 非空却记为 true；要不要统一用 alias-aware 复算后再解释？
9. **`claim_set_exact` 只算 `(claim_id, polarity)`，不算三元组内容；** 2/10 是“ID+极性对齐”，不是“语义 claim 对齐”；这两个指标是否要同时保留？
10. **A4 adapter 的严格 schema 5/10、strict contract 0/10，v2 的严格 schema 0/10、claim_id 10/10；** 一个像“格式学到了一半”，一个像“词表学对了、字段没对齐”；这是两个独立轴，是否应固定成二维报告？
11. **弱门 `contract_ok` 仍是 1.0；** 它只查单对象根、verdict、claims 数组。这个数还要不要出现在任何对外摘要里？

### C. 训练充分性与可比性

12. **50 条、13 步、1 epoch 能区分“学格式”与“学判定”吗？** 现在没有 train-set 复现、没有同 prompt 的重复 base、没有去掉 adapter 的同数据对照。
13. **train_loss 1.2597、末步 0.511 能说明什么？** 只有一个 run、一个 seed；没有验证集 loss，也没有按 step 的固定评测。
14. **base 8/10 HOLD、adapter 9/10 HOLD、v2 4/10 HOLD；** HOLD 偏置是 target 文本、chat template、解码，还是 holdout 构成？训练集正负 25:25，不能直接解释。
15. **A4 base 和 adapter 的 claim set 都是 0/10；v2 是 2/10；** 这 2 条是 004 和 009，都是 gold 只有 `anchor_source_external(+1)` 的简单行；复杂行仍不 exact。是否需要按 claim 数分层看？
16. **A5 云端 holdout 没有 `gold_claims`，A4/A5 的 claim set 对账都在本机用 A3 gold 复算；** 云端 summary、本机复算、A4 历史记录三个口径是否要在报告里强制分栏？
17. **Qwen 与 Gemma 的训练集 hash 不同（`54fd202c…` vs `f1072fa9…`）；** 当前只能做格式契约参照，不能做模型比较；这个边界是否还要在每张表上标注？
18. **单卡 V100、4-bit、greedy、768 tokens；** 延迟 18.17/19.27/26.01 秒是否只作为运行开销，不进入任何能力判断？
19. **终端断连两次但进程未中断；** 现有“进程 + log + `EVAL_COMPLETE.json`”三件套是否足以证明一次运行完整、可复现？

## 7. 候选下一步（零 GPU 优先）

### 第 0 步：零 GPU，先修尺子和复算

- 修 `eval_e2b.claim_set()` 与本地 `contract_eval.claim_set()` 的 polarity 归一化，统一 alias-aware 复算；从现有 v2 `eval.json` 直接重算 `claim_set_exact`，不加载模型。
- 把 v2 的 16 条 claims 做“只归一化、不改文本”的 strict 复算：字符串→整数、语义 kind→枚举，分别报“归一化前/后”的 strict，区分契约缺口与模型缺口。
- 固定 `kind` 策略：要么收紧 prompt 到五枚举，要么把语义 kind 纳入 rubric；先做离线影响评估，再决定改哪一端。
- 明确 verdict 归属：模型 verdict 与 `claim_engine.adjudicate_claims()` 的 policy verdict 分两列，不互相替代；先复算 A4/A5 全部历史输出。
- 把 A4/A5 的 `claim_set` 对账统一到 A3 gold 与 alias-aware 规则；云端旧 holdout 只用于生成，不用于 gold 对账。

### 第 1 步：仍不训练，只做一次 schema 对照（需 GPU，待批）

- 同一 base、同一 holdout、同一解码，只把 prompt 的 JSON 形状写死：`polarity` 只允许 `1/-1`，`kind` 只允许五枚举，给出一个最小样例。
- 观察 strict schema、`claim_id_allowed`、exact set 是否分离变化；不把 verdict 变化直接归因给模型。
- 仍只跑 base，不跑 adapter；避免与 A4 训练结果混表。

### 第 2 步：再决定是否重训 50 条

- 只有在第 0/1 步确认“schema 能对齐、verdict 归属清楚”后，才用同一 50 条重训。
- 重训前固定：同 train hash、同 holdout、同 seed、同解码；adapter 与 base 同表；同时报 strict/lenient/raw、policy 重判、exact set。
- 若 schema 对照没有改变 strict，先查 chat template、target 序列化、label mask，不加数据、不加 epoch。

### 第 3 步：扩数据或跨模型比较

- 扩数据前先冻结 claim 语义、`kind` 枚举、verdict 归属与 strict gate；否则无法区分“数据量不足”和“口径错位”。
- Qwen vs Gemma 只在同 train/holdout/rubric 下重跑后才比较；否则只写格式契约差异。
- 任何新 run 保留 `eval.json`、原始输出、`EVAL_COMPLETE.json`、代码 hash、holdout hash 与 adapter 首文件 hash。

## 8. 证据入口

- `evidence/qwen3-4b/base_eval.json` — A4 Qwen base。
- `evidence/qwen3-4b/adapter_eval.json` — A4 Qwen + 50 QLoRA。
- `evidence/qwen3-4b/base_prompt_v2_eval.json` — A5 v2 云端原始结果。
- `evidence/qwen3-4b/base_prompt_v2_eval.log` — A5 v2 云端日志。
- `evidence/qwen3-4b/base_prompt_v2_EVAL_COMPLETE.json` — 完成哨兵与 `eval_sha256`。
- `evidence/qwen3-4b/base_prompt_v2_recompute.json` — 本机 strict/policy/exact 复算。
- `a5_gpu_recompute.py` — 上述复算脚本；只读，不加载模型。
- `A5-ZERO-GPU-PATCH.md`、`evidence/a5-semantic-audit.*`、`evidence/data-diff-a3-*.json` — A5 零 GPU 前置修复。
