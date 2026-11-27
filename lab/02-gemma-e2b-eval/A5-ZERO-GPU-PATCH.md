# A5 零 GPU 口径修复：语义、claim_id、strict gate、参数与哨兵

> 本文件只记录已执行的口径修改和离线结果，不判断模型通过/失败，不做跨模型排名。
> 本轮没有加载模型、没有训练、没有 GPU 推理。

## 1. 冻结的判定语义

新增 `governance/contract_semantics_v1.json`，并把同一段规则写进 `prompt_contract.py` 的 system prompt：

- PASS：草稿 claims 满足冻结 `claim_policy` 的 `required_any`，且不含任何 `forbidden_any`。
- HOLD：其余情况。
- 判定对象是“草稿 claims 能否被冻结锚定接受”，不是“草稿是否同意用户问题”，也不是“模型自己是否相信草稿”。

这一步只冻结规则，不替模型改答案。模型输出仍按 `rubric_v1` 独立计分。

## 2. claim_id 规则

选定 **closed allowlist + `claim_id`/`polarity` 精确匹配**：

- 允许表由 `claim_policy_v0.json` 的 `required_any + forbidden_any` 推导，不读 holdout gold。
- 未来训练/评测的 user prompt 会显式列出本 case 的允许 ID。
- 输出出现表外 ID 记为 `claim_id_not_allowed`，进入 strict gate。
- `(subject,predicate,object,polarity)` 三元组匹配只作诊断，不作验收门。

E003 当前允许表：`anchor_source_external`、`anchor_source_inside`、`anchor_source_self`。

## 3. strict contract gate

`rubric_v1.json` 升为 `contract-v1.1`，新增两个独立字段：

- `strict_contract_pass = structural + strict schema + full triple + claim_id_allowed`
- `claim_id_allowed` 单独报告；历史 `schema_pass` 保持旧口径，便于和 A2/A4 对齐。

云端弱门 `contract_ok` 只保留为解析健康度，不再与 strict gate 混报。

## 4. 参数量口径

新增 `param_stats.py`，训练脚本改为：

- 优先用 `model.safetensors.index.json` 的 `total_size / dtype bytes` 作为 `total_params`；
- 保留 4-bit 加载后的 `sum(p.numel())` 为 `total_params_loaded`；
- 写 `total_params_source`；有 index 时同时写 `run_dir/param_check.json`。

Qwen3-4B 的核对值不变：

- `total_size = 8,045,591,552` bytes，bf16 2 bytes/参数 → `4,022,795,776`；
- 可训练 `33,030,144` → `0.821%`；
- manifest 原 `2,238,840,320 / 1.475%` 保留为 4-bit 计数伪影，不再作分母。

## 5. 数据可比性 diff

用 Git 中的旧 blob 与新 `data/` 做字段级 diff，结果落盘：

- 训练集：50 条、ID/顺序一致；变更只有 `claims.object` 60 处、`claims.predicate` 24 处，全部是从空串补成 canonical 值；其他字段无变化。
- holdout：10 条、ID/顺序一致；唯一变化是 10 条都新增 `gold_claims`。
- 旧/新哈希：train `f1072fa9…` → `54fd202c…`；holdout `6d9de69e…` → `87d2fb1b…`。

因此“训练集被改过”可以落到具体字段；是否足以做受控比较仍需单独决定。

## 6. 完成哨兵与盯盘状态机

- 训练结束写 `RUN_COMPLETE.json`：`status`、`run_id`、`finished_at`、`train_sha256`、`manifest_sha256`、`train_seconds`、`train_loss`。
- 评测结束写 `EVAL_COMPLETE.json`：summary + `eval_sha256`。
- `run_watch.py` 的状态机：`completed`（哨兵）/ `running`（进程在 + log 新）/ `stalled`（进程在 + log 15 分钟不动）/ `manifest_only`（有产物无进程无哨兵）/ `idle`。
- GPU/显存不再作为主判据，只作辅助。

## 7. 离线语义审计结果

`a5_zero_gpu_audit.py` 把四个来源分别送进同一 claim policy，结果：

| 来源 | verdict 一致 | PASS recall | HOLD recall | 输出 HOLD |
|---|---:|---:|---:|---:|
| 冻结 gold claims → policy | 1.0 | 1.0 | 1.0 | 4 |
| 草稿文本 → claim_engine | 1.0 | 1.0 | 1.0 | 4 |
| Qwen base 模型自己的 verdict | 0.2 | 0.0 | 0.5 | 8 |
| Qwen base claims → policy 重判 | 0.4 | 0.0 | 1.0 | 10 |
| Qwen adapter 模型自己的 verdict | 0.3 | 0.0 | 0.75 | 9 |
| Qwen adapter claims → policy 重判 | 0.4 | 0.0 | 1.0 | 10 |

claim_id 使用：

- base：全部 ID 落在允许表的行 **0/10**；不同 ID 3 个，`c1`、`c2`、`c001`。
- adapter：全部 ID 落在允许表的行 **0/10**；不同 ID 12 个，最高频 `anchor_by_model`（3 次）。

模型 verdict 与“模型 claims 经 policy 重判”的配对：

- base：`HOLD→HOLD 8`、`PASS→HOLD 2`。
- adapter：`HOLD→HOLD 9`、`PASS→HOLD 1`。

用新 strict gate 复核旧输出：base 与 adapter 的 `claim_id_allowed` 都是 0/10，`strict_contract_pass` 都是 0/10；adapter 的旧 strict schema 仍是 5/10。两个数分开报，不合并成“模型退步”。

这些数字只说明规则、抽取、模型 verdict、模型 claims 四个层面当前不一致；不构成模型能力结论。

## 8. 测试

```bash
python3 test_contract_eval.py      # 8/8
python3 test_data_contract.py      # train=50 holdout=10
python3 test_param_stats.py        # OK
python3 test_run_watch.py          # 5/5
```

## 9. 还没做的

- 第 1 步 GPU 对照未执行：同一 Qwen base、同一 10 条 holdout、只换 v2 prompt（语义 + 允许表），重跑一次。
- 未重训 50 条；未做 Qwen/Gemma 受控比较；未扩数据。
- 未把云端弱门替换为 strict gate 的实际执行门；只在本机 rubric 中拆开。

## 10. 证据入口

- `evidence/a5-semantic-audit.json` / `.md`
- `evidence/data-diff-a3-train.json` / `.md`
- `evidence/data-diff-a3-holdout.json` / `.md`
- `evidence/qwen3-4b/param_check.json`
- `governance/contract_semantics_v1.json`
- `prompt_contract.py`、`param_stats.py`、`run_watch.py`
