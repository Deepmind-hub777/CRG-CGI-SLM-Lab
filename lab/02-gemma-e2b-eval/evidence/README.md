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

使用说明：

- `e2b-contract-eval-report.md` 作为阶段 01 的云端原始证据，未改动正文；不代表本仓库重新跑过模型。
- `contract-eval-v1.*` 是本仓库对同一批原始输出的离线重算，**不是新的 GPU run**，不能写成模型提升。
- 报告内存在两处口径不一致，已在 `../STAGE-01-REPORT.md` 第 3.1 与第 7 节标注：
  - 结论写 adapter 旧口径 2/10，第 2 节严格表写 0/10；
  - 006 同时被描述为“断在中间”和“不是截断”。
- 任何后续重算，以冻结后的单一 rubric 为准；不要跨口径比较。
