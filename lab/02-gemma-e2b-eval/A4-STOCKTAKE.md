# A4 结果盘点：Qwen3-4B 初步训练

> 边界：本文件只盘点本次 run 的事实、未决问题和候选动作；不做通过/失败判断，不做模型排名，不把一次 smoke 写成能力结论。

## 1. 本次 run 清单

| 项 | 值 |
|---|---|
| run id | `qwen3-qlora-50-20261127-1340` |
| 底座 | `Qwen/Qwen3-4B-Instruct-2507` |
| 训练集 | A3 `data/train.jsonl`，50 条，`54fd202c4df00c635ab0086acf01493ecbdaed10f95624eec1655e2165994492` |
| 评测集 | 10 条 holdout；云端运行时是 A3 前版本，prompt/draft 与 A3 相同，只缺 `gold_claims` |
| 训练 | 4-bit NF4 + double quant，LoRA r16/alpha32/dropout .05，1 epoch，batch 1，grad accum 4，lr 1e-4，max length 1024，seed 42 |
| 训练结果 | 13 步，50.8 秒，汇总 `train_loss=1.2597`；日志可见末步 loss 0.511；252 个 target modules |
| 可训练参数 | 33,030,144 |
| 真实参数估算 | `model.safetensors.index.json` `total_size=8,045,591,552` bytes；按 bf16 2 bytes/参数约 4.023B；占比 0.821% |
| adapter | `/mnt/systemDisk/e2b/runs/qwen3-4b/qwen3-qlora-50-20261127-1340/adapter`，首个文件 sha256 `0acdda1df96dbd76fe64563c6729e9dc81883477325efcfacedaf0fb199e1aac` |
| base eval | 10 条，平均 19.3 秒；`evidence/qwen3-4b/base_eval.json`，sha256 `0ab2ed92…` |
| adapter eval | 10 条，平均 26.0 秒；`evidence/qwen3-4b/adapter_eval.json`，sha256 `9e4759e7…` |

## 2. 训练过程事实

- 日志首段单步 loss：2.567 / 2.098 / 2.424；末段可见 0.8556 / 0.9666 / 0.8209 / 0.7942 / 0.511。
- 日志首段 grad_norm：6.565 / 4.867 / 5.952；后段可见 1.055 / 1.278 / 1.171 / 0.9204 / 1.119。
- 1 个 run、1 个 seed、13 步；没有重复 run，也没有 seed 方差。
- 训练集 50 条，正负比 25:25；holdout 10 条，gold 为 6 PASS + 4 HOLD。

## 3. 评测事实（`rubric_v1`，10 条）

| 指标 | Qwen base | Qwen + 50 QLoRA | Gemma 新 prompt base | Gemma 新 prompt adapter |
|---|---:|---:|---:|---:|
| 结构 | 10/10 | 10/10 | 8/10 | 8/10 |
| 严格 schema | 0/10 | 5/10 | 0/10 | 0/10 |
| 宽松 schema | 2/10 | 5/10 | 7/10 | 0/10 |
| 核心三元组 | 9/10 | 8/10 | 8/10 | 8/10 |
| verdict 一致率 | 0.20 | 0.30 | 0.50 | 0.50 |
| 输出 HOLD 条数 | 8/10 | 9/10 | 0/9（1 条不可解析） | 0/8（2 条不可解析） |
| HOLD recall | 2/4 | 3/4 | 0/4 | 0/4 |
| PASS recall | 0/6 | 0/6 | 5/6 | 5/6 |
| always-PASS 基线 | 0.60 | 0.60 | 0.60 | 0.60 |
| always-HOLD 基线 | 0.40 | 0.40 | 0.40 | 0.40 |
| claim set（严格合格样本） | 不可计算（0 条合格） | 0.0（5 条合格） | 不可计算 | 不可计算 |

注：Qwen base 的云端 summary 另记 `claim_set_exact_rate=0.1`；这是旧 gold/engine 口径，本机用 A3 gold + strict 门复算为 0/10，两个口径不混用。Gemma 两列的 claim set 在严格合格样本上同样不可计算，表内并列只作格式参照。

失败分布：

- Qwen base：`bad_polarity 15 / bad_kind 14`；大量 `positive/negative`、`prohibition/requirement` 别名。
- Qwen adapter：`missing_field 4 / bad_polarity 4`；2 条核心三元组不完整。
- 云端 `contract_ok_rate=1.0`：只查单对象根、`verdict`、`claims` 数组，不查 claim 字段、polarity、kind。
- Gemma 行来自 A2 的四个云端产物，用同一 `rubric_v1` 复算；Gemma 训练集是 A3 前版本，不能与 Qwen 行当受控对照。

## 4. 数据与口径事实

- Qwen 训练用 A3 重建的 `54fd202c…`；Gemma 旧 run 用 A3 前的 `f1072fa9…`。
- A3 的改动是 canonical `predicate/object` 填充：训练集空 `object`/`predicate` 从 60/70、24/70 降到 0/70；holdout 补了 11 条 `gold_claims`。
- Qwen 评测在云端跑的是 A3 前 holdout；prompt/draft 与 A3 相同，只差 `gold_claims`。claim set 在本机按 A3 gold 复算，模型输出不受影响。
- `manifest.json` 的 `total_params=2,238,840,320` 来自 4-bit 加载后的 `sum(p.numel())`；与 index 推算的 4.023B 不一致。当前报告用 4.023B / 0.821% 作为分母。

## 5. 未决问题

### A. 契约语义

1. **PASS/HOLD 的定义是什么？** 当前 system prompt 只说“给出 PASS/HOLD”，没有写“PASS = 草稿 claims 可被冻结锚定接受”还是“草稿是否同意用户问题”。这次 Qwen 的 verdict 更像在判后者；这是 prompt 缺口、模型理解，还是 target 本身没写清？
2. **claim set 要比什么？** 现在按 `claim_id` 精确匹配，但 prompt 没给 `claim_id` 词表。应该给允许词表，还是改成按 `(subject,predicate,object,polarity)` 语义匹配？
3. **哪个 contract 门算运行门？** 云端弱门 10/10 与严格 schema 0/10、5/10 同时成立。弱门只作“解析健康度”，还是也进验收表？
4. **`hold_reason` / `rollback_required` 要不要评分？** 当前只评 verdict 和 claims；adapter 的 `hold_reason` 是否可信，没有进入指标。

### B. 指标效度

5. **10 条 holdout、4 条 HOLD 的分辨率够吗？** HOLD recall 的分母只有 4；是否需要更多 holdout、重复采样或区间估计？
6. **claim set 的云端 0.1 / 严格 0.0 差异说明什么？** 是抽取质量问题，还是 ID 命名问题，还是 gold 集合定义问题？
7. **严格 schema 0/10 与 5/10 的差别，应该归因给模型还是 harness？** 别名宽容度、字段枚举、是否允许 `kind` 别名，都会改变分数。
8. **延迟 19.3 / 26.0 秒能说明什么？** 单次、单卡、4-bit、greedy；是否只作为运行开销记录，不进入能力比较？

### C. 训练充分性

9. **50 条、13 步、1 epoch 能区分“学格式”与“学判定”吗？** 需要哪些对照：train-set 复现、同 prompt 的 base、去掉 adapter、只改 prompt 不训练、反事实成对样本？
10. **HOLD 偏置来自哪里？** 训练集 25:25 平衡，但 base 8/10 HOLD、adapter 9/10 HOLD；是 target 文本、chat template、解码、还是 holdout 构成导致？
11. **adapter 的严格 schema 从 0/10 到 5/10、核心三元组从 9/10 到 8/10，这两条方向相反的变化怎么解释？** 是格式学习挤掉了内容，还是样本太少？
12. **只跑一个 seed 的 50.8 秒和 loss 曲线可重复吗？** 是否需要第二个 seed 或重复评测，至少看方差？

### D. 数据可比性

13. **Qwen 与 Gemma 能否直接比较？** 两者训练集 hash 不同（`54fd20…` vs `f1072f…`）；最小受控实验是同 train、同 holdout、同 rubric 重跑，还是只比较格式契约、不比较判定？
14. **A3 的 canonical 填充是否改变了任务难度？** 空 `predicate/object` 被补成固定词后，模型是在学抽取，还是在学模板？
15. **要不要保留 A3 前数据作为对照？** 如果以后要复现 Gemma 旧结果，旧 `train/holdout` 是否需要一个只读快照？

### E. 运行与运维

16. **参数总量以哪个字段为准？** `manifest.total_params`、index `total_size`、`config` 的 hidden/层数，三者如何统一进审计？
17. **训练/评测完成状态怎么报？** 只看 GPU 会把“已完成”报成“空转”；是否统一写 `RUN_COMPLETE.json`，还是用 `runs/` + log mtime + 进程三件套？
18. **云端登录/终端断连/文件同步没有稳定流水线，是否影响可复现性？** 是否需要固定的文件 API 下载清单和 hash 校验步骤？
19. **adapter 不进 git、不发布权重；证据只留 manifest/eval。** 这个边界是否够用，是否需要把 adapter 的哈希清单和 run 目录结构一并落盘？

## 6. 候选下一步（按“零 GPU 优先”排列）

### 第 0 步：零 GPU，先修口径

- 写清 PASS/HOLD 的判定规则，落到 prompt 或 runtime contract；用现有 10 条输出离线重判，先看规则本身是否会改变 gold/模型对齐。
- 决定 claim set 口径：给 `claim_id` 允许词表，或改为三元组语义匹配；两种都先用现有输出离线重算，不加载模型。
- 把云端 `contract_ok` 升级为 `rubric_v1` strict schema；弱门只保留为“解析健康度”，不与严格门混报。
- 修正 `total_params` 口径：以 index `total_size` 或 config 计算；把 `param_check.json` 纳入 manifest。
- 做 `f1072f` vs `54fd20` 的字段级 diff，标注哪些结果可比、哪些不可比。

### 第 1 步：一次不训练的基础对照

- 用同一 Qwen base、同一 10 条 holdout、同一解码参数，只改 PASS/HOLD 语义与 claim_id 规则，重跑一次 base。
- 观察 verdict 分布是否变化：如果 base 仍 8/10 HOLD，问题可能在模型/解码；如果分布改变，问题先在 prompt 语义。
- 这一步不训练、不扩数据，只增加一次 GPU 推理。

### 第 2 步：再决定是否重训

- 只有在第 1 步确认“语义修正能改变判定”后，才考虑用同一 50 条重训。
- 重训前固定：同一 train hash、同一 holdout、同一 seed、同一解码；adapter 与 base 同表；同时报 strict/lenient/raw。
- 如果第 1 步没有改变判定，先检查 chat template、target 序列化、label mask，而不是继续加数据。

### 第 3 步：模型比较与数据扩展

- 若要做 Qwen vs Gemma，先在同一 train/holdout/rubric 下重跑；否则只写“格式契约差异”，不写模型差异。
- 扩数据前先定 claim 语义、ID 规则、strict gate；否则无法区分“数据量不足”和“语义错位被放大”。
- 任何新 run 都保留 `manifest.json`、`eval.json`、原始输出、adapter 首文件 hash 和完成哨兵。

### 第 4 步：盯盘改造

- 主判据改为“进程 + 产物哨兵（`RUN_COMPLETE.json` / `manifest.json` / `eval.json`）”，GPU/显存只作辅助。
- 状态机：`running`（进程在 + log mtime 近）、`completed`（无进程 + 产物出现且两次轮询稳定）、`stalled`（进程在 + log 15 分钟不动）、`idle`（无进程 + 无新产物）。
- 只报状态迁移和 run_id，不每次轮询重复报“空转”。

## 7. 证据入口

- `evidence/qwen3-4b/base_eval.json` — Qwen base 原始评测。
- `evidence/qwen3-4b/adapter_eval.json` — Qwen + 50 QLoRA 原始评测。
- `evidence/qwen3-4b/manifest.json` — 云端训练 manifest（含 bnb 计数伪影）。
- `evidence/qwen3-4b/param_check.json` — 真实参数量与占比核对。
- `evidence/a4-recompute.json` / `.md` — 用 `rubric_v1` 的逐行复算与摘要。
- `evidence/a2-recompute.json` / `.md` — Gemma 四个产物的同尺复算，仅作格式对照。
- `STAGE-02-REPORT.md` 第 11 节 — A4 记录；`NEXT-ACTIONS.md` A5 — 待修口径。
