# lab/02 · Gemma 4 E2B smoke QLoRA

**状态：** 阶段 01 链路验证通过；模型能力 gate 未通过；未发布，未合并 main，不进入正式 run。
**目标：** 验证 `0 / -1 / +1 / 使` 的 process 能不能跨模型；不证明模型更聪明。
**一句话：** 训练的是 **claim 抽取与 PASS/HOLD 过程**，不是把锚定原文背成答案。

## 阶段成果

- [STAGE-01-REPORT.md](STAGE-01-REPORT.md) — 2026-11-27 阶段复盘：过程、结论、证据与下一步。
- [STAGE-02-REPORT.md](STAGE-02-REPORT.md) — 从链路验证到运行时治理灰箱：契约分层、模型无关性边界、Ring 0 缺口。
- [NEXT-ACTIONS.md](NEXT-ACTIONS.md) — 阶段 02 的口径修复清单与验收门槛。
- [rubric_v1.json](rubric_v1.json) — 结构 / schema / 完整三元组的统一 rubric。
- [contract_eval.py](contract_eval.py) — 用统一 rubric 重算云端报告，0 GPU。
- [evidence/e2b-contract-eval-report.md](evidence/e2b-contract-eval-report.md) — 云端原始契约评测报告，只读证据。
- [evidence/contract-eval-v1.md](evidence/contract-eval-v1.md) — 统一 rubric 的重算摘要。
- [STAGE-02-MANIFEST.json](STAGE-02-MANIFEST.json) — 阶段 02 状态与文件哈希。
- [evidence/a2-recompute.md](evidence/a2-recompute.md) — A2：四个云端 eval 产物的统一 rubric 重算。

---

## 1. 这次到底训什么

输入：

```text
用户问题 + 候选草稿 + 锚定摘录（本 smoke 为空）
```

target：

```json
{
  "claims": [
    {"claim_id": "...", "subject": "...", "predicate": "...", "object": "...",
     "polarity": 1, "kind": "assertion", "evidence": "草稿里的原句"}
  ],
  "verdict": "PASS",
  "hold_reason": "",
  "rollback_required": false
}
```

- 草稿是**输入**，不是 target；模型不背草稿。
- `anchor_v0.json` 与 `claim_policy_v0.json` 只作为外部参照和验收规则，**不进入 target**。
- 负例教的是“识别漂移并 HOLD”，不是“生成错误答案”。
- 真正的 `-1` 仍是外部的 `claim_engine.py`；adapter 不自己批自己。

---

## 2. 数据

```text
data/train.jsonl     50 条：E003 20、E004 10、E006 10、E009 10
data/holdout.jsonl   10 条：现成 holdout_e003，不参与训练
data/manifest.json   来源、许可、split、逐条 hash
```

正负比 25:25。负例覆盖：self+、inside+、打分即三元、router 训练、public 放学生作文、疑问句未作答等漂移。

重建数据：

```bash
python3 build_data.py
```

当前数据哈希：

```text
train   54fd202c4df00c635ab0086acf01493ecbdaed10f95624eec1655e2165994492
holdout 87d2fb1b0b85203fc34d55e37642acd063ba5ad356941e4067bb83b8f37846e3
```

---

## 3. 硬件与底座

- 底座：`google/gemma-4-E2B-it`，`Gemma4ForConditionalGeneration`，safetensors，约 10GB。
- 不是 GGUF。GGUF 只能推理，不能 QLoRA。
- 文本配置：35 层，hidden 1536；`num_kv_shared_layers=20`；总参数约 5.12B，模型卡 2.3B effective。
- 最低 12GB VRAM；本 smoke 用阿里云 PAI-DSW 免费试用 V100 16GB（A10 24GB 在 `cn-shanghai-d` 暂停销售，未用）。
- 音频塔/视觉塔不进入 LoRA target；只打文本 decoder 的 7 个投影。

---

## 4. 环境

```bash
pip install -r requirements.txt
```

下载底座（模型不进 git）：

```bash
mkdir -p models
huggingface-cli download google/gemma-4-E2B-it \
  --local-dir models/gemma-4-E2B-it \
  --local-dir-use-symlinks False
```

国内网络可用镜像：

```bash
export HF_ENDPOINT=https://hf-mirror.com
```

---

## 5. 训练

```bash
python3 train_qlora.py \
  --model-id google/gemma-4-E2B-it \
  --train data/train.jsonl \
  --run-id smoke-$(date +%Y%m%d-%H%M%S) \
  2>&1 | tee smoke-train.log
```

默认：4-bit NF4 + double quant，bf16 compute（V100 自动 fp16），LoRA `r=16/alpha=32/dropout=0.05`，1 epoch，batch 1，grad accumulation 4，lr `1e-4`，max length 1024。

产物：

```text
runs/<run_id>/
├── adapter/            # 不进 git
├── manifest.json
└── train.log           # 由 tee 落盘
```

---

## 6. 评测

同一批 holdout 草稿，base 与 adapter 各跑一次；外部 `claim_engine.py` 仍给出草稿的基准 verdict。

```bash
python3 eval_e2b.py --model-id google/gemma-4-E2B-it \
  --out runs/base/eval.json

python3 eval_e2b.py --model-id google/gemma-4-E2B-it \
  --adapter runs/<run_id>/adapter \
  --out runs/<run_id>/eval.json
```

指标：结构合格率、schema 合格率、完整三元组、verdict 一致率、HOLD recall、always-PASS 基线、延迟；claim set 只在“结构 + schema 都合格”的输出上计算。
统一 rubric 的快速重算：

```bash
python3 contract_eval.py --report evidence/e2b-contract-eval-report.md
python3 test_contract_eval.py
python3 test_data_contract.py
```

**不写“准确 / 零幻觉 / 超越某模型”。**

---

## 7. 硬边界

- 0 在权重之外：target 中不得出现 `anchor_v0.json` / `claim_policy_v0.json` 原文。
- -1 独立：最终 PASS/HOLD 仍由 `claim_engine.py` 判；adapter 只做过程抽取。
- +1 只生发：adapter 不替模型决定真理。
- 不发布权重、不 merge、不导出 GGUF；adapter 只留在 `runs/<run_id>/adapter/`。
- 不碰 NAC 学生数据、家长信息、合同、密钥、受限权重。
- 不直推 main；只走分支 + PR，由 Milo 批。

---

## 8. 已知未实测

- `num_kv_shared_layers=20` 的共享 KV 层，LoRA 是否能稳定拿到梯度，需在 16GB+ 的可用卡上实测（本 smoke 已在 V100 16GB 上跑通；A10 在 `cn-shanghai-d` 暂停销售，未用）。
- `Gemma4ForConditionalGeneration` 的 processor 与纯文本 `generate` 路径，需在训练机确认。
- 50 条只够 smoke，不够签 G0；holdout 只有 E003 10 条，E004/E006/E009 的 holdout 仍缺。
