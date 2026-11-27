# Evidence · 云端原始契约评测报告

本目录保存云端执行方回传的原始证据，**未改动正文**。

| 文件 | 来源 | SHA256 |
|---|---|---|
| `e2b-contract-eval-report.md` | 用户上传附件 `https://aka.doubaocdn.com/s/vP6h5Oz2Es`；本地接收 2026-11-27 | `30ac18e0b996f60263de15a8b18b12aa1b34f340eee882255346bcdf182de9c4` |
| `contract-eval-v1.md` | 用 `rubric_v1.json` 对云端报告的重算摘要，非云端原始 | 见 `STAGE-01-MANIFEST.json` |
| `contract-eval-v1.json` | 同一重算的逐行结果，非云端原始 | 见 `STAGE-01-MANIFEST.json` |
| `a5-semantic-audit.json` / `.md` | A5 零 GPU 语义审计：gold/草稿/模型 verdict/模型 claims 分源对照 | 见 `STAGE-02-MANIFEST.json` |
| `data-diff-a3-train.json` / `.md` | A3 前后训练集字段级差异 | 见 `STAGE-02-MANIFEST.json` |
| `data-diff-a3-holdout.json` / `.md` | A3 前后 holdout 字段级差异 | 见 `STAGE-02-MANIFEST.json` |
| `qwen3-4b/base_prompt_v2_eval.json` | A5 云端原始 v2 prompt 评测；`eval_sha256=18e2c8e2…` | `18e2c8e279b901b763af77e2f23446f4c72cd0ed006b341e00b00871eadfdae9` |
| `qwen3-4b/base_prompt_v2_eval.log` | A5 云端运行日志 | `268236b7427c1f14479910717bce9b4d5a22339ee58df084d4fd5cefcca6b8c1` |
| `qwen3-4b/base_prompt_v2_EVAL_COMPLETE.json` | A5 完成哨兵与 eval hash | `54548d8b31e33a7caaae5d4aa8033cfac9ad98eb3425792da607ac15d8e5084c` |
| `qwen3-4b/base_prompt_v2_recompute.json` | 本机 strict/policy/exact 复算，非云端原始 | `6eaaf3863134a779bcb0733178539dc12422b991b5356827ed85a0f13f49aea9` |

使用说明：

- `e2b-contract-eval-report.md` 作为阶段 01 的云端原始证据，未改动正文；不代表本仓库重新跑过模型。
- `contract-eval-v1.*` 是本仓库对同一批原始输出的离线重算，**不是新的 GPU run**，不能写成模型提升。
- 报告内存在两处口径不一致，已在 `../STAGE-01-REPORT.md` 第 3.1 与第 7 节标注：
  - 结论写 adapter 旧口径 2/10，第 2 节严格表写 0/10；
  - 006 同时被描述为“断在中间”和“不是截断”。
- 任何后续重算，以冻结后的单一 rubric 为准；不要跨口径比较。
