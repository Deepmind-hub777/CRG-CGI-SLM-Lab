# 01 · Qwen3-4B 治理运行时实验

**状态：** lab / 可复现实验，不是发布结论  
**日期：** 2026-11-27  
**主张标签：** `[C]` 实证；未复现的数字不得升级为 `[D]`

---

## 1. 这个实验做了什么

在 4 vCPU / 7.2GB / 无 GPU 的云主机上，用 llama.cpp 跑 Qwen3-4B-Instruct-2507 Q4_K_M，验证：

1. 只加提示词（`crg_rule`）与加外置锚定（`crg_anchor`）的差异；
2. HOLD 是否只是“一句话”，还是一次真实回滚；
3. 词面 regex 校验器为什么会误杀“语义对、词面不对”的 E003；
4. claim-level `-1`（主体/谓词/极性/证据 + 否定窗口）能否修掉误杀，同时保留投毒拦截。

---

## 2. 目录

```text
lab/01-qwen4b-eval/
├── claim_engine.py              # claim-level 校验器
├── governed_runtime.py          # 0/-1/+1/使 的事务运行时
├── run_eval.py                  # 10 条 seed 的三条件评测
├── governance/
│   ├── anchor_v0.json           # 冻结锚定
│   ├── anchor_flipped.json      # 投毒锚定
│   ├── claim_policy_v0.json     # claim policy
│   ├── calibration_e003.jsonl   # 校准集 18 条
│   ├── holdout_e003.jsonl       # 留出集 10 条
│   ├── state/                   # regex 账本
│   └── state_claim/             # claim 账本
├── results.json                 # 30 条调用结果
├── REPORT.md                    # 第一轮评测
├── ATTENTION_PROXY.md           # 行为代理注意力
├── ATTENTION_PROBE.md           # 内部 attention 探针
├── GOVERNANCE_REPORT.md         # 回滚证明
├── CLAIM_LEVEL_REPORT.md        # claim-level 报告
├── llama-attn-probe.patch       # llama.cpp 探针补丁
└── *.png                        # 注意力/回滚/claim 图
```

**不在 git 里：**

- `models/`：Qwen3-4B GGUF，2.32GiB；走 GitHub Release 资产，不进 git 树。
- `probes/`：attention 探针二进制，约 186MB；可由补丁与脚本复跑。
- `llama.cpp/`：完整源码树；只用 `llama-attn-probe.patch` 记录改动。
- `attn_probe`：编译产物；按 `ATTENTION_PROBE.md` 重编。

---

## 3. 模型与哈希

```text
模型：Qwen3-4B-Instruct-2507-Q4_K_M.gguf
大小：2,497,280,448 bytes（2.32 GiB）
SHA256：8cdb57cbb880d313736a9bc4e3d3d2485f145b5e19cf33783746e753e82641fc
来源：lmstudio-community/Qwen3-4B-Instruct-2507-GGUF
```

Release：

```text
https://github.com/Deepmind-hub777/CRG-CGI-SLM-Lab/releases/tag/lab-qwen3-4b-v0.1
```

模型资产按 2 段拆分上传；下载后按 `REASSEMBLE.md` 合并，并核对上面的 SHA256。

---

## 4. 复跑

### 4.1 评测

```bash
cd lab/01-qwen4b-eval
python3 run_eval.py
```

### 4.2 claim-level 校准

```bash
python3 claim_engine.py calibrate --file governance/calibration_e003.jsonl
python3 claim_engine.py calibrate --file governance/holdout_e003.jsonl
```

### 4.3 账本验证

```bash
GOV_STATE=governance/state_claim python3 governed_runtime.py verify --checker claim
GOV_STATE=governance/state python3 governed_runtime.py verify --checker regex
```

### 4.4 attention 探针

先读 `ATTENTION_PROBE.md`。关键点：

- 必须 `flash_attn_type=DISABLED`，否则 `kq_soft_max` 不存在；
- 探针 shape `[256, n_tokens, 32, 1]`；
- 单线程 + `cache_prompt=false` 才能逐字节复现。

---

## 5. 已知限制

- 10 条 seed 只够做方向判断，不够做统计结论。
- E003 校准 18/18、留出 10/10；E004/E006/E009 尚未做同等规模 holdout。
- attention 只跑了 E001 三组；head 因果消融未做。
- 4 线程 greedy 下 E003 会抖；所有可复现结论都来自单线程 + `cache_prompt=false`。
- 本实验不是 QLoRA/SFT/GRPO；权重未训练。

---

## 6. 不说的词

不说“准确”，不说“零幻觉”，不说“超越某模型”。只说：

> 同一输入，同一结果；可复现，可审计，可回滚。
