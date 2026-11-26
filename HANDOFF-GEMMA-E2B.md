# HANDOFF · Gemma 4 E2B QLoRA 训练

**状态：** draft / 待 Grok 接单  
**日期：** 2026-11-27  
**发起：** Milo  
**执行：** Grok Bot（驻场总工）  
**验收：** 豆包（只读落盘、独立哈希回读、守规则；不写训练代码）  
**批准：** Milo  
**主张标签：** `[D]` 流程约束；模型能力数字一律 `[C]`，未复现前不得写成结论

---

## 0. 仓库与工作区（Grok 先看这一节）

### 0.1 GitHub 仓库

```text
https://github.com/Deepmind-hub777/CRG-CGI-SLM-Lab
```

- 公开仓库，默认分支 `main`。
- 代码 License：Apache-2.0；文档 CC BY 4.0。
- 当前本地分支：`lab/day-0-skeleton`；最新 commit `2f96b86`。
- 已有 PR #1：`https://github.com/Deepmind-hub777/CRG-CGI-SLM-Lab/pull/1`，draft / OPEN / 未合并。

### 0.2 重要：lab/01 已推上 PR 分支，但不在 main

`lab/01-qwen4b-eval/` 的代码、治理账本、报告、图片已推到 `lab/day-0-skeleton` 分支，并进入 PR #1。  
但 PR #1 目前是 **draft / OPEN / 未合并**，所以直接 clone `main` 还看不到 `lab/01`。

- 未合并前：checkout `lab/day-0-skeleton`。
- 合并后：`main` 才会有 `lab/01`。
- 模型权重不进 git 树，走 GitHub Release：

```text
https://github.com/Deepmind-hub777/CRG-CGI-SLM-Lab/releases/tag/lab-qwen3-4b-v0.1
```

- `probes/` 与 `llama.cpp/` 源码树不进 git；只保留 `llama-attn-probe.patch`。

离线快照（可选，57KB，不含模型、探针、llama.cpp）：

```text
https://aka.doubaocdn.com/s/x9uMhk4tTU
```

### 0.3 正确的开工方式

1. clone GitHub 仓库：

```bash
git clone https://github.com/Deepmind-hub777/CRG-CGI-SLM-Lab.git
cd CRG-CGI-SLM-Lab
```

2. 若 PR #1 尚未合并，切到已有实验分支：

```bash
git fetch origin lab/day-0-skeleton
git checkout lab/day-0-skeleton
```

3. 确认 `lab/01-qwen4b-eval/claim_engine.py` 与 `governed_runtime.py` 在树里；  
   如果不在，再用 57KB 离线包补齐。

4. 新建分支：

```bash
git checkout -b lab/02-gemma-e2b-smoke
```

5. 所有改动只走 PR，不直推 `main`。

> 注意：`lab/01-qwen4b-eval/` 的模型、probes、llama.cpp 构建产物不在 git 树里；Grok 不需要它们来训 E2B。需要复核 Qwen 基线时，读 `lab/01-qwen4b-eval/REPORT.md`、`CLAIM_LEVEL_REPORT.md` 与 `governance/state_claim/`。

---

## 0.4 一句话

用现有的 `0 / -1 / +1 / 使` 制度，在 Gemma 4 E2B 上做一次 **smoke QLoRA**：只训过程，不训锚定；先证明制度能跨模型，再谈效果。

---

## 1. 目标

1. 在 E2B 上跑通 **4-bit QLoRA**，产出可加载的 adapter。
2. 用同一套 `eval/cases/seed.jsonl` 和 `claim_engine.py`，对比：
   - E2B base
   - E2B + adapter
   - Qwen3-4B base（已有基线）
3. 验证三件事：
   - adapter 是否学会“先抽 claim、再引 evidence、再决定 PASS/HOLD”的过程；
   - 是否没有把锚定原文当答案背进去；
   - 是否能被外部 `-1` 否决并回滚。

---

## 2. 非目标

- **不做正式发布权重**；第一轮只算 smoke。
- **不做 GRPO/RLVR**；先 SFT/QLoRA，把过程数据跑通。
- **不做端侧部署**；GGUF 导出与手机加载放到 G3。
- **不换主线**；Qwen3-4B 仍是主线，E2B 只做第二执行器。
- **不碰 NAC 学生数据、家长信息、合同、密钥、受限权重。**

---

## 3. 硬约束（不可协商）

1. **0 在权重之外。**  
   `anchor_v0.json` 与 `claim_policy_v0.json` 只作为输入上下文/验收参照；**不得作为训练 target**，不得把锚定原文训成模型“自己的知识”。

2. **-1 必须独立。**  
   校验器仍然是 `claim_engine.py` / `governed_runtime.py`；**不能用 E2B 自己批自己**，不能把同一个 adapter 同时当生成器和校验器。

3. **+1 只负责生发。**  
   adapter 学的是：claim 抽取、evidence 引用、格式、何时 HOLD；不是“替模型决定真理”。

4. **训练不能用 GGUF。**  
   `gemma-4-E2B-it-Q4_K_M.gguf` 只能做推理/评测；QLoRA 必须用 Hugging Face safetensors 底座（`google/gemma-4-E2B-it`，BF16 约 10GB）。**不要拿 3GB GGUF 去训练。**

5. **不直推 main。**  
   所有改动走分支 + PR，由 Milo 批；Grok 不碰 merge。

6. **对外话术禁说“准确 / 零幻觉”。**  
   只能说：同一输入同一结果、可复现、可审计、可回滚。

---

## 4. 资产与路径

### 4.1 已有资产（Qwen 侧，不要动）

```text
/home/user/Doubao/chats/36399304075305730/CRG-CGI-SLM-Lab/
├── eval/cases/seed.jsonl
├── lab/01-qwen4b-eval/
│   ├── claim_engine.py
│   ├── governed_runtime.py
│   ├── governance/
│   │   ├── anchor_v0.json
│   │   ├── claim_policy_v0.json
│   │   ├── calibration_e003.jsonl
│   │   ├── holdout_e003.jsonl
│   │   ├── state_claim/
│   │   └── state/
│   └── models/Qwen3-4B-Instruct-2507-Q4_K_M.gguf
└── SPEC/03-metrics-and-gates.md
```

固定哈希（验收时回读）：

```text
anchor_v0 SHA256       86f481cf1f3508c2cf92bb7b1e9ce8299532bdd0122b5e707273dca4814f32be
claim_policy_v0 SHA256 72b5c2d4e7f6641eacfddd34f639b0b9ff5eed414d0e22af8480e4d946d1a438
Qwen3-4B SHA256        8cdb57cbb880d313736a9bc4e3d3d2485f145b5e19cf33783746e753e82641fc
```

### 4.2 新增目录（Grok 负责）

```text
lab/02-gemma-e2b-eval/
├── README.md                 # 环境、复跑命令、硬件
├── requirements.txt
├── data/
│   ├── train.jsonl           # 过程轨迹
│   ├── holdout.jsonl         # 不参与训练
│   └── manifest.json         # 来源、许可、哈希、split
├── train_qlora.py
├── eval_e2b.py
├── runs/<run_id>/
│   ├── adapter/
│   ├── merged/               # 可选
│   ├── eval.json
│   ├── train.log
│   └── manifest.json
└── models/                   # 不进 git
    ├── gemma-4-E2B-it/       # safetensors，训练用
    └── gemma-4-E2B-it-Q4_K_M.gguf  # 推理/对照用
```

---

## 5. 训练数据：只训过程，不训答案

### 5.1 每条样本的 schema

```json
{
  "id": "E003-train-001",
  "case_id": "E003",
  "prompt": "用户问题原文",
  "anchor_excerpt": "允许放入的锚定片段，可为空",
  "draft": "模型草稿或人工改写草稿",
  "claims": [
    {
      "claim_id": "anchor_source_external",
      "subject": "外部策略",
      "predicate": "定义",
      "object": "锚定",
      "polarity": "+1",
      "kind": "assertion",
      "evidence": "由外部策略或损失函数定义"
    }
  ],
  "verdict": "PASS",
  "hold_reason": "",
  "rollback_required": false,
  "source": "synthetic|human|model",
  "license": "CC-BY-NC-4.0",
  "split": "train"
}
```

### 5.2 正负样本

- **正例：** claim 结构完整、evidence 能回指原句、verdict 与 `claim_engine.py` 一致。
- **负例：** 不是“胡编”，而是“漂移”：
  - 结论对，但 evidence 是假的；
  - 前半对，后半偷偷 `self+`；
  - 条件句前件被当成断言；
  - 疑问句被当成主张；
  - 双重否定被否定窗口带跑。

### 5.3 Split 与 G0

- 第一轮 smoke：`train >= 50` 条，`holdout >= 10` 条；E003 必须覆盖。
- 正式训练前：每类 `holdout >= 50`，G0 才签。
- **holdout 绝不进 train**；`data/manifest.json` 记录每条 hash。
- 不含学生数据；不含未脱敏教师轨迹；每条带来源与许可。

---

## 6. 训练配置（建议，不是宪制）

> 具体超参由 Grok 按 E2B 实际结构调；以下只给安全起点。

- 底座：`google/gemma-4-E2B-it` safetensors，BF16 加载后 4-bit QLoRA。
- 量化：NF4 + double quant；计算 dtype bf16。
- LoRA：`r=16`，`alpha=32`，`dropout=0.05`；先只打 attention + MLP 线性层。
- **target modules 必须从 `model.named_modules()` 实际探测**；不要照抄 Qwen 的 `q_proj/k_proj/...` 名字。
- 学习率：`1e-4` 起步；epoch 1–3；warmup 3%；cosine 或 linear。
- 序列长度：先 `1024`；稳定后再 `2048`。
- batch：1 + gradient accumulation 8；gradient checkpointing 开。
- 固定 `seed`；记录 CUDA/cuDNN 版本。
- 若 E2B 带音频/视觉塔：**冻结非文本塔**，只训文本路径。
- 不要用 `llama.cpp` 训练；用 PyTorch + PEFT/TRL 或 Unsloth（由 Grok 选，但要在 README 写清）。

### 6.1 硬件门槛

- 建议 `>= 12GB VRAM` 跑 4-bit QLoRA；`16GB` 舒适；`24GB` 可上 2048。
- 低于 `8GB` 不要开训；先回传硬件清单，改做推理评测。
- 当前 `vm` 是 4 vCPU / 7.2GB / 无 GPU，**只能做推理和验收，不能训练**。

---

## 7. 执行顺序

### S0 · 环境与资产

- [ ] `nvidia-smi`、`python -c "import torch; print(torch.__version__, torch.cuda.is_available())"`。
- [ ] 下载 `google/gemma-4-E2B-it` safetensors；记录 SHA256。
- [ ] 下载 `ggml-org/gemma-4-E2B-it-GGUF` Q4_K_M 仅作推理对照；记录 SHA256。
- [ ] 复制 `anchor_v0.json`、`claim_policy_v0.json` 到 `lab/02-gemma-e2b-eval/governance/`；只读，不改。

### S1 · 先测 base，不训练

- [ ] 用同一套 `seed.jsonl` 10 条，跑 E2B base。
- [ ] `temperature=0`，单请求，`llama.cpp` 单线程 + `cache_prompt=false`（若用 GGUF）。
- [ ] 记录 `pp/tg`、峰值内存、输出 hash。
- [ ] 用 `claim_engine.py` 判 PASS/HOLD；记录 evidence coverage。
- [ ] 产出 `runs/base/eval.json`。

### S2 · 数据冻结

- [ ] 生成/整理 `train.jsonl` 与 `holdout.jsonl`。
- [ ] 每条样本过 schema 校验；写 `manifest.json`。
- [ ] 豆包抽检 10 条：正例/负例各 5，确认没有 anchor 原文当 target。

### S3 · Smoke QLoRA

- [ ] 只训 1 个 epoch，先看 loss 是否正常下降。
- [ ] 保存 adapter；记录显存峰值、耗时、可训练参数比例。
- [ ] 不做 merge，不导出 GGUF。

### S4 · Adapter 评测

- [ ] E2B base vs E2B+adapter，同一 10 条。
- [ ] 指标：claim-level PASS/HOLD、evidence coverage、格式合规、HOLD 召回、误杀率。
- [ ] 抽 5 条失败案例，写失败模式。
- [ ] 与 Qwen3-4B base 做并排表。

### S5 · 合并与导出（仅当 S4 不崩）

- [ ] merge adapter 到 BF16。
- [ ] 导出 GGUF Q4_K_M；记录转换命令与哈希。
- [ ] 用 `llama.cpp` 复跑 10 条，确认与 PyTorch 侧行为一致（允许量化误差，但要记录）。

### S6 · 报告

- [ ] `runs/<run_id>/manifest.json`：commit、model_hash、adapter_hash、anchor_hash、policy_hash、GPU、seed、gates。
- [ ] `runs/<run_id>/eval.json`：逐条结果 + 汇总。
- [ ] `README.md`：复跑命令、坑、已知限制。
- [ ] PR 描述：只写“做了什么、证据在哪、哪条没过”。

---

## 8. 验收标准

| # | 检查 | 通过条件 |
|---|---|---|
| A1 | 0 未进权重 | 训练 target 中没有 `anchor_v0` / `claim_policy_v0` 原文；抽检 10 条 |
| A2 | -1 独立 | 评测仍由 `claim_engine.py` 判，不用 E2B 自评 |
| A3 | 过程可学 | adapter 在 holdout 上 claim 结构完整率不低于 base |
| A4 | 不背答案 | 换问法/换案例，仍能抽 claim，而不是复述训练答案 |
| A5 | 可回滚 | HOLD 时仍能触发 `pending -> mid -> after` 真实回滚 |
| A6 | 可复现 | 固定 seed、temp 0、单线程；同输入输出 hash 一致 |
| A7 | 数据干净 | 无学生数据、无受限许可、holdout 未进 train |
| A8 | 失败有记录 | 任何一项没过，先写 `FAIL-###`，不 cherry-pick |

**Smoke 通过 ≠ 发布。** 只有 G0/G2 过、holdout 每类 50+，才谈正式权重。

---

## 9. 交付物

```text
lab/02-gemma-e2b-eval/
├── README.md
├── data/manifest.json
├── train_qlora.py
├── eval_e2b.py
├── runs/<run_id>/adapter/
├── runs/<run_id>/eval.json
├── runs/<run_id>/train.log
└── runs/<run_id>/manifest.json
```

PR 里必须贴：

- 硬件：GPU 型号 / VRAM / CUDA；
- 模型与 adapter 的 SHA256；
- base vs adapter 的 10 条并排表；
- 一条真实 HOLD 回滚的 txn / before / pending / after；
- 一条 FAIL（如果有）。

---

## 10. 禁止清单

- 禁止拿 GGUF 做 QLoRA。
- 禁止把 `anchor_v0.json` 原文当训练 target。
- 禁止同一 adapter 既生成又校验。
- 禁止 holdout 泄漏进 train。
- 禁止直推 main。
- 禁止把厂商自测数字写成 `[D]`。
- 禁止用 NAC 学生数据、家长信息、合同、密钥、受限权重。
- 禁止在报告里写“准确 / 零幻觉 / 超越某模型”。

---

## 11. 待决

1. Grok 侧是否有 `>=12GB VRAM` 的 NVIDIA GPU？没有就只做推理评测。
2. 用 Unsloth 还是 PEFT/TRL？两者都行，但必须记录版本。
3. E2B 实际参数是约 5B 还是其他？以 `google/gemma-4-E2B-it` 模型卡为准。
4. E2B 是否带音频/视觉塔？若带，冻结非文本塔。
5. 第一轮 smoke 数据是 50 条还是 100 条？建议先 50，别把脏数据放大。
6. 是否允许把 adapter 放 `runs/` 但 .gitignore 权重？建议是：adapter 不进 git，只留 manifest + hash。

---

## 12. 给 Grok 的第一条消息（可直接复制）

```text
Grok，接 CRG-CGI-SLM-Lab 的 E2B smoke QLoRA。

仓库：
https://github.com/Deepmind-hub777/CRG-CGI-SLM-Lab
先 clone。PR #1 未合并时，checkout lab/day-0-skeleton；合并后用 main。
新建分支 lab/02-gemma-e2b-smoke。不要直推 main。

lab/01 的代码、治理账本、报告已在 PR #1 分支里。
模型权重走 Release，不在 git 树：
https://github.com/Deepmind-hub777/CRG-CGI-SLM-Lab/releases/tag/lab-qwen3-4b-v0.1
如果分支里缺 claim runtime，再用 57KB 离线包：
https://aka.doubaocdn.com/s/x9uMhk4tTU

先读：
- HANDOFF-GEMMA-E2B.md（尤其第 0 节仓库与工作区）
- lab/01-qwen4b-eval/claim_engine.py
- lab/01-qwen4b-eval/governed_runtime.py
- lab/01-qwen4b-eval/REPORT.md / CLAIM_LEVEL_REPORT.md

任务：在 lab/02-gemma-e2b-eval/ 下跑通 Gemma 4 E2B 的 4-bit QLoRA smoke。
硬约束：0 不进权重；-1 仍用 claim_engine.py；只训过程不训答案；GGUF 只做推理不做训练；不直推 main。

第一步不要写训练代码，先回传：
1) GPU 型号 / VRAM / CUDA；
2) 你打算用 Unsloth 还是 PEFT/TRL；
3) E2B 实际 target modules 探测结果；
4) 50 条 train + 10 条 holdout 的数据计划。

我这边只做验收：读落盘、独立哈希回读、跑同一套 claim-level 评测。工程实现你来做。
```
