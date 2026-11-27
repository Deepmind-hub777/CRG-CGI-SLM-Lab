# STAGE-01 · Gemma 4 E2B smoke QLoRA：链路验证与契约评测复盘

**状态：** 链路验证通过；模型能力 gate 未通过；**不进入正式 run**，不补新数据，不发布权重。
**日期：** 2026-11-27（Asia/Bangkok，UTC+7）
**范围：** 只做 smoke QLoRA + 契约评测；不替换 Qwen3-4B 主线，不做正式后训练。
**主张标签：** 工程与实测记录写作 `[D]`；模型能力数字一律 `[C]`，未复现前不得写成结论。

---

## 0. 一句话结论

这次真正跑通的是**从零到 adapter、再到可复盘评测**的完整链路；没有跑通的是**模型学会 HOLD 判别和 claim 语义**。

所以结论是两句话：

1. **链路通了，而且可复现、可审计。**
2. **模型 gate 没过，不能进正式 run；下一步先修评测口径和 claim 三元组 schema，不是加 epoch、不是补数据。**

---

## 1. 本阶段做了什么、没做什么

### 1.1 做了

- 在阿里云 PAI-DSW 免费试用内创建 V100 16GB 实例，完成模型下载、环境搭建、4bit QLoRA smoke 训练。
- 产出可加载的 LoRA adapter、`manifest.json`、`checkpoint-13`。
- 用同一批 10 条 holdout 跑 base 与 adapter 评测。
- 发现并修复 `eval_e2b.py` 的 `KeyError` 崩溃；把旧 `eval.json` 按契约重算。
- 用更严格的 prompt / `max_new_tokens=768` / `repetition_penalty=1.05` / 围栏即停，做同批 10 条对照。
- 把“评测失败”和“模型失败”分开，定位到 HOLD 判别、claim 三元组 schema、adapter 尾部稳定性三个问题。

### 1.2 没做

- 没启动正式 run，没扩大数据，没加 epoch。
- 没发布权重，没合并 main，没导出 GGUF。
- 没把 `0` 写进权重；`-1` 仍由 `claim_engine.py` 独立裁决；`+1` 只负责生发。
- 没使用付费资源；本阶段现金成本 ¥0，走免费试用额度。

---

## 2. 过程记录

### 2.1 资源路径

- 先尝试 A10 24GB `ecs.gn7i-c8g1.2xlarge`，在 `cn-shanghai-d` 创建失败；事件日志为 “Sales of this resource are temporarily suspended in the specified zone”，DSW 页面没有可用区切换。
- 改用 V100 16GB `ecs.gn6v-c8g1.2xlarge`。
- 前两个 V100 实例 `e2b-smoke-v100`、`e2b-smoke-v100b` 因镜像/依赖问题未能训练。
- 第三个实例 `e2b-smoke-v100c` 使用镜像 `modelscope:1.29.0-pytorch2.6.0-gpu-py311-cu124-ubuntu22.04`，实际环境为 Python 3.11、`torch 2.6.0+cu124`、CUDA 12.4、V100-SXM2-16GB（15.8GB 显存，计算能力 7.0）。

### 2.2 环境与依赖

- `transformers 4.55.4` / `4.57.6` 不识别 `gemma4` 架构；`transformers 5.24.1` 认识 Gemma 4，但要求 PyTorch ≥ 2.6。
- 最终安装 `transformers 5.24.1`、`peft 0.22.0`；环境还有 `bitsandbytes 0.47.0`、`accelerate 1.10.0`、`datasets 3.2.0`。
- `prepare_model_for_kbit_training` 在 16GB V100 上试图把大块非量化参数转 fp32，单次申请 8.75GB 导致 OOM；改为手动冻结参数、`enable_input_require_grads()`、`gradient_checkpointing_enable()`，并显式 `use_cache=False`。
- transformers 5 的 `TrainingArguments` 不再接受 `warmup_ratio`，改为 `warmup_steps=1`。
- V100 自动走 `fp16`；`manifest` 记录 `compute_dtype=torch.float16`。

### 2.3 数据

- `train.jsonl` 50 条：E003 20、E004 10、E006 10、E009 10；25 PASS / 25 HOLD。
- `holdout.jsonl` 10 条：6 PASS / 4 HOLD，不参与训练。
- `build_data.py` 用 `claim_engine.evaluate()` 从草稿反推 claims / verdict，保证训练 target 与外部 `-1` 判据一致。
- `test_candidates.py` 全量校验，50/50 OK。
- `anchor_excerpt` 全为空，target 不含 `anchor_v0` / `claim_policy_v0` 原文。
- 已知缺口：双重否定漂移未纳入本批 50 条；E004/E006/E009 没有独立 holdout。

### 2.4 训练

- RUN：`smoke-v100c-20261127-1011`
- 13/13 step，1 epoch，50 条样本，52.6 秒
- loss：3.693 → 0.6903；`train_loss=2.5036`
- `grad_norm` 前两步为 `nan`，后面恢复正常；这是稳定性隐患，不能当作干净训练
- 可训练参数 24,158,208；总参数 3,960,178,208（约 3.96B）；占比 0.61%；205 个 target module
- adapter 约 93MB；`adapter_model.safetensors` 的 SHA256（云端记录）：`03bf5e2caa62fb17b60bf6ceec25a3e7d3aa40b06e9c86d542bdb0`
- manifest 关键值：`train_seconds=52.627092123031616`、`train_loss=2.50362741947417`

### 2.5 评测与事故

- `eval_e2b.py` 在 JSON 解析失败时不写 `model_verdict`，打印又直接取 `row[k]`，第二条样本触发 `KeyError`，两次评测中途崩溃。
- 云端备份 `eval_e2b.py.bak`，把打印改为 `row.get(k)`；本仓库同步修复为 `row.get(k)`，并在异常分支写入 `model_verdict=None`。
- 复跑 base 与 adapter 的 holdout 评测，产出 `runs/base/eval.json` 与 `runs/smoke-v100c-20261127-1011/eval.json`。
- 10:30:23 曾停止 `e2b-smoke-v100c`，导致云端正在进行的评测/对照半途卡住；随后重启，云子继续完成 1+2。
- 教训：**停实例前必须确认云子是否还在用同一台机器，不能只看本机 `nvidia-smi` 为空。**

---

## 3. 评测结果

### 3.1 先说明：旧基线不可直接比

旧产物存在两套口径：

- 云端结论写作 adapter 旧口径 **2/10**；
- 云端报告第 2 节严格重算表写作 adapter 旧口径 **0/10**（base 也是 0/10）。

这两个数不能同时作为基线。严格表里 base 10 条全带代码围栏、9 条数组根，adapter 7 条重复键、7 条缺顶层 verdict、2 条截断、3 条不可解析；按“单对象根 + 无围栏 + 顶层 verdict + 无重复键 + 未截断”的严格规则，**两边都是 0/10**。本阶段不采用 2/10 或 0/10 作为提升叙事。现已在 `rubric_v1.json` / `contract_eval.py` 下统一重算，见 3.2 与 3.3。

### 3.2 新对照（同 prompt / 768 / rep 1.05 / 围栏即停）

| 指标 | base | adapter |
|---|---|---|
| json_ok_rate | 0.9 | 0.8 |
| verdict 一致率 | 0.5 | 0.5 |
| claim set 精确率（旧口径，仅对照） | 0.0 | 0.1 |
| 结构契约（统一 rubric） | 8/10 | 8/10 |
| schema 契约（统一 rubric） | **0/10** | **0/10** |
| 完整三元组（统一 rubric） | **0/10** | **0/10** |
| 平均延迟 | 78.77 s | 12.48 s |

**统一 rubric 的重算方式：** `contract_eval.py --report evidence/e2b-contract-eval-report.md` 直接解析云端报告里的原始输出，不占 GPU、不改模型。结构 8/10 与云端一致；schema 0/10 是新增的硬结果，详见 3.3。旧 claim set 0.0/0.1 只在“结构不合格输出也能参与精确匹配”的旧口径下成立，本报告不再把它当能力指标。

**归因边界：** prompt 是两边同时改的，base 的绝对分也变了。本轮能干净归因的只有 **harness 效应**；adapter 从旧口径回到 8/10，不能全部记在 adapter 头上。

### 3.3 四个硬结论

1. **8/10 是结构契约，不是语义契约。**
   当前只查了单对象根、顶层 `verdict`、`claims` 数组、无重复键、未截断；没有查 `polarity ∈ {±1}`、`kind` 枚举、三元组非空、`evidence` 完整。adapter 003/004 的 `polarity:0`、008 的 `kind:"PASS"`、005 的缺字段，仍算“合格”。

2. **HOLD 判别为零。**
   4 条 gold=HOLD（005/006/008/010）全部漏判，base 与 adapter 一次 HOLD 都没输出。
   这批 holdout 是 6 PASS / 4 HOLD；一个永远输出 PASS 的傻瓜基线是 **0.6**，base 和 adapter 都是 **0.5**，**比傻瓜基线还差**。

3. **claim set 低分是 schema/评测口径 bug，不是能力结论；而且 target 与 gold 其实已经同源。**
   逐行审计确认：`build_data.py` 的 `target_from_engine` 和 `eval_e2b.py` 的 `expected_claims` 都调用同一个 `claim_engine.evaluate()`；`holdout.jsonl` 没有存 `claims`，但 gold 是现场用同一引擎抽的，不是另一套抽取。真正的问题是这条引擎对 `anchor_source_*` 常返回空 `predicate` / `obj`：70 条 train claims 里 60 条 `object` 空、24 条 `predicate` 空；holdout 11 条 gold claims 的 `predicate` / `object` 全空。训练 target 忠实复制了这些空字段，模型被教成“填 null”；评测 `claim_set` 只比较 `(claim_id, polarity)`，低分主要来自模型输出的 claim_id / polarity 对不上，不是 gold 来自另一套抽取。先把 claim 三元组 schema 和 gold 存储修好，再谈 claim set。

4. **schema 契约也是 0/10。**
   base 的 `polarity` 写成 `"positive"` / `"negative"`、`kind` 写成 `fact` / `restriction`；adapter 出现 `polarity:0`、`kind:"PASS"`、claims 缺 `polarity` / `kind` / `evidence`。按 target 的 schema（`polarity ∈ {±1}`、`kind` 枚举、字段齐全）判，base 与 adapter 都是 **0/10**，不是 8/10。8/10 只是结构合格。

### 3.4 尾部与语义问题

- adapter 002：`"evidence":null",` 多一个引号，JSON 坏。
- adapter 006：`""verdict"` 双引号，且断在中间；云端报告同时写了“断在中间”和“不是截断”，需要用 `finish_reason` 与实际 token 长度再确认。
- adapter 003/004：`polarity:0`；如果 schema 规定 polarity 只能是 ±1，这是非法值。
- adapter 008：`kind:"PASS"`；`kind` 被 verdict 值串味。
- adapter 005：claims 缺 `polarity/kind/evidence`。
- adapter 平均 12.48 秒，不是“效率提升”，是它把字段填 `null`、输出更短；快是省掉了内容。

---

## 4. 关键判断

### 4.1 链路验证通过

以下五段都真实发生，且产物可追溯：

1. 免费试用资源可创建、可启动、可进 shell。
2. Gemma 4 E2B safetensors 可下载、可 4bit 加载。
3. QLoRA 可训练，adapter 可落盘，manifest/hash 可回读。
4. base 与 adapter 可跑同一批 holdout，评测结果可落盘。
5. 云端执行 + 本地验收的协同可运行；即使中途停实例，也能重启恢复。

### 4.2 模型能力未通过

- 结构契约 8/10 只是 harness 门槛，不是模型门槛。
- HOLD 0/4，verdict 0.5 < 0.6 傻瓜基线。
- claim set 0.0/0.1 是旧口径；统一 rubric 下没有一条“结构 + schema”都合格的输出，claim set 无法作为能力指标。target/gold 已同源，但 claim 三元组字段大量为空。
- 语义契约未过：非法 polarity、kind 串味、字段缺失。

### 4.3 边界没有被污染

- `0` 没有进入权重；target 不含锚定原文。
- `-1` 仍由 `claim_engine.py` 独立裁决。
- `+1` 只负责生发。
- adapter 失败没有污染治理边界；这次负结果反而验证了边界是干净的。

---

## 5. 证据与哈希

| 文件 | SHA256 | 说明 |
|---|---|---|
| `data/train.jsonl` | `f1072fa95f2514ca9dba36f990bcdb276bb71266a8ccfac466efc68fb8238371` | 50 条训练数据 |
| `data/holdout.jsonl` | `6d9de69ea03ed664fa3f7c480d34a5876282a6d1002ade7d7d4e6a1d5e3d8e41` | 10 条 holdout |
| `evidence/e2b-contract-eval-report.md` | `30ac18e0b996f60263de15a8b18b12aa1b34f340eee882255346bcdf182de9c4` | 云端原始报告，只读证据 |
| `runs/.../adapter/adapter_model.safetensors` | `03bf5e2caa62fb17b60bf6ceec25a3e7d3aa40b06e9c86d542bdb0` | 云端记录，未在本机回读；adapter 不进 git |

- 训练 run：`smoke-v100c-20261127-1011`
- 产物根：`/mnt/systemDisk/e2b/runs`
- manifest：`/mnt/systemDisk/e2b/runs/smoke-v100c-20261127-1011/manifest.json`
- 评测输出：`runs/base/eval.json`、`runs/smoke-v100c-20261127-1011/eval.json`
- 原始云端报告：`evidence/e2b-contract-eval-report.md`

---

## 6. 下一步动作

### 6.1 先做（0 GPU）

1. **冻结一份 rubric：结构 + 语义 + 失败分类。**
   - 已产出 `rubric_v1.json` 与 `contract_eval.py`；结构规则：单对象根、无围栏、顶层 `verdict`、`claims` 数组、无重复键、未截断。
   - schema 规则：`polarity ∈ {±1}`、`kind` 枚举、字段齐全、PASS 不得空 claims；完整三元组再加 `subject` / `predicate` / `object` / `evidence` 非空。
   - 已在云端报告上重算：base / adapter 结构 8/10，schema **0/10**，完整三元组 **0/10**；HOLD recall 0/4；verdict 0.5 < always-PASS 0.6。
   - 用同一份 rubric 重算四个 `eval.json`，不再跨口径比较。

2. **修 claim 三元组 schema 与 gold 存储。**
   - 训练 target 与 holdout gold 已经都走 `claim_engine` 同一套抽取；不要再重复做“同源”改造。
   - 真正要修的是 `claim_engine` 对 `anchor_source_*` 的空 `predicate` / `obj`：要么补齐抽取规则，要么在 `build_data` 里写明确的 canonical triple，不能继续把空字段当 target。
   - `holdout.jsonl` 补 `gold_claims`，把现场抽取变成可审计的冻结 gold。
   - `claims` 补完整三元组；`polarity` 统一 ±1；`kind` 用枚举；顶层 `verdict` 固定。
   - 重跑 `test_candidates.py` 与 `contract_eval.py`，更新 manifest/hash。

### 6.2 再做（10 条 GPU A/B）

- `temperature=0`；
- `repetition_penalty=1.0` 与 `1.05` 做 A/B；
- `max_new_tokens=768`，围栏即停；
- 记录 `finish_reason`；
- 只判断尾部稳定性和 HOLD 是否开始出现，不做正式 run。

### 6.3 最后才补数据

- 200–300 条，优先补“双重否定、条件前件未成断言、自我定锚/内生在权重/自我校准”的完整负例三元组。
- 配比暂定：40% HOLD 负例、20% 双重否定/条件前件、20% 中文三元组与输出契约样板、10% 长 claim/截断压力、10% PASS 对照。
- epoch 先保持 1。
- **现在补数据，等于把错误的 target 口径放大五倍。**

### 6.4 验收门槛

- 结构合格：base 与 adapter 都 ≥ 8/10。
- 语义合格：≥ 9/10，不能再出现 `polarity:0`、`kind:"PASS"`、缺字段。
- HOLD recall：≥ 1/4。
- verdict 准确率：> 0.6 的 always-PASS 基线。
- 达不到，就继续查生成停止和 target 序列化，不补数据、不加 epoch、不进正式 run。

---

## 7. 未决与风险

1. `grad_norm` 前两步 `nan` 未解决；正式 run 若复现，先处理 fp16/梯度裁剪/优化器稳定性。
2. 旧口径 2/10 与严格表 0/10 冲突；已用 `rubric_v1.json` 重算，结构 8/10、schema 0/10，两个数不再混用。
3. 8/10 只查结构，语义 gate 未过。
4. 006 的“断在中间”与“不是截断”描述冲突，需 `finish_reason` 确认。
5. 本地 `eval_e2b.py` 已同步 `row.get(k)` 修复；云端 `eval_e2b.py.bak` 仍作为回滚备份。
6. 正式 run、数据补充、PR 合并均未获批；本阶段只提交 draft PR。
7. 免费试用是 3 个月 / 250 计算时/月，不能当生产 SLA；正式 run 前要算额度。

---

## 8. 复现入口

```bash
cd lab/02-gemma-e2b-eval

# 数据校验
python3 test_candidates.py

# 统一 rubric：直接解析云端报告，不占 GPU
python3 contract_eval.py --report evidence/e2b-contract-eval-report.md

# 重建数据（会重写 train/holdout/manifest）
python3 build_data.py

# 训练（需要 GPU 与模型）
python3 train_qlora.py \
  --model-id google/gemma-4-E2B-it \
  --train data/train.jsonl \
  --run-id smoke-$(date +%Y%m%d-%H%M%S)

# 评测
python3 eval_e2b.py --model-id google/gemma-4-E2B-it --out runs/base/eval.json
python3 eval_e2b.py --model-id google/gemma-4-E2B-it \
  --adapter runs/<run_id>/adapter --out runs/<run_id>/eval.json
```

- 模型权重、adapter、`runs/` 不进 git；只保留 manifest、hash 与报告。
- 本阶段代码与数据随 draft PR 提交；不直推 main，不 merge。

---

## 9. 记录声明

- 本文只记录已发生的事实与已复现的数字；未复现的模型能力数字标 `[C]`。
- 不写“准确 / 零幻觉 / 超越某模型”；只说同一输入同一结果、可复现、可审计、可回滚。
- 本阶段结论：**链路验证通过，模型能力 gate 未通过；不进入正式 run。**
