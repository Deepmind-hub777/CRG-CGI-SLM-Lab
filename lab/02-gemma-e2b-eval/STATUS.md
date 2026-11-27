# STATUS · Gemma 4 E2B smoke QLoRA · 第一步探测

> **归档说明（2026-11-27 10:55 UTC+7）：** 本文件是 01:50 的第一步探测记录，保留原始判断（当时未建分支、未 commit/push/PR）。阶段 01 的最终结果与下一步见 [`STAGE-01-REPORT.md`](STAGE-01-REPORT.md) 与 [`NEXT-ACTIONS.md`](NEXT-ACTIONS.md)。不要用本文件里的“未 commit/未 push”描述当前状态。

| 字段 | 值 |
|---|---|
| 写入时间 | 2026-11-27 01:50（Asia/Bangkok，UTC+7） |
| 执行方 | CGI/CRG 治理（工程） |
| 验收方 | 豆包（只读落盘、独立哈希回读） |
| 批准 | Milo |
| 本步范围 | 交接单第 12 节「第一步」：只回传 4 项探测结果。没写训练代码，没下载权重，没装训练栈，没租用或付费，没申请 token，没建分支，没 commit/push/PR |
| 主张标签 | 流程与实测记录写作 `[D]`；厂商或第三方给的模型能力、显存、价格数字一律标 `[C]`；没有加载权重实测的结构判断标【推演】 |

## 0. 输入文件与哈希（本机 `sha256sum` 独立复算）

| 文件 | sha256 | 说明 |
|---|---|---|
| `/workspace/handoffs/gemma-e2b/HANDOFF-GEMMA-E2B.md`（v1，保留不动） | `1f55ebf593347a83cb1aeb522b5af03203f32db9def8668ec203cd09ae8bd950` | 与幕僚长助手给的值一致。注意：这个文件每一行前都带有 `     N|` 行号前缀（像是从阅读工具里粘出来的），v2 没有这个前缀 |
| `/workspace/handoffs/gemma-e2b/v2/HANDOFF-GEMMA-E2B.md`（v2，**本步按 v2 执行**） | `cc55633563caac9d970e046877ba25ad1ccb4305576b746632d53e18849cf6b5` | 一致。去掉 v1 的行号前缀后做 diff：v2 只多了第 0 节（仓库、runtime 包、开工顺序），并改了第 12 节的「先读」清单；第 1–11 节正文相同 |
| `/workspace/handoffs/gemma-e2b/小模型方法梳理-背景.md` | `727a840ca3ee0218268a9da3bd04b2a4723cc824fc6516e51db7ca67745c73d8` | 一致，只作参考 |
| runtime 包 zip（Milo 附件） | `bea9ac1f068b35b07f79e584ced3d703bc4bf3b978a1a1fdf5df16e41ae42390` | 共 39 项，其中 34 个文件、5 个目录。解包目录 `/workspace/handoffs/gemma-e2b/runtime-pkg/` 下的 34 个文件与 zip 内文件逐个比对 sha256，0 个不一致。包内文件我一个都没改 |
| `/workspace/governance/CRG-GATE-001.md` | （只读参照） | 付费、账号、凭证类动作 → HOLD，交 Milo 本人决定 |

**待核（小差异）：** Milo 消息里给的包链接是 `aka.doubaocdn.com/s/XCzWwH2UJK`，v2 交接单 §0.2 和 §12 写的是 `/s/x9uMhk4tTU`。本地以附件 zip 的 sha256 `bea9ac1f…` 为准，两条短链我都没有下载。请 Milo 或豆包确认是否同一个包，并统一交接单里的写法。

**仓库现状（只读 clone 在 `/workspace/crg-cgi-slm-lab`）：**
- `main` = `34e21d7`（Initial commit，只有 LICENSE、README）。工作区干净，`git status` 为空。
- 远端分支 `origin/lab/day-0-skeleton` = `2f96b86`，提交时间 2026-11-26 21:49 UTC+7。这个分支上有 `SPEC/03-metrics-and-gates.md`（blob sha256 `6ab91610…`），还有 `eval/cases/seed.jsonl`，它的 sha256 `4b6cc1cb…` 与包内 `eval/seed.jsonl` **逐字节相同**。
- `claim_runtime/` 不在 GitHub 上，与交接单 §0.2 一致。
- 我没有建分支、没有 commit、没有 push、没有开 PR。

---

## 1. 硬件实测与结论

### 1.1 命令与原始结果（2026-11-27 01:44 UTC+7，共享电脑「箱子」）

| 命令 | 结果 |
|---|---|
| `which nvidia-smi` | 无输出，rc=1 |
| `ls /dev/nvidia*` | No such file or directory |
| `ls -d /usr/local/cuda*` | No such file or directory |
| `python3 -c "import torch"` | `ModuleNotFoundError: No module named 'torch'`；Python 3.13.5 |
| `lspci` | 命令不存在。改读 `/sys/bus/pci/devices/*/vendor`：8 个设备，1 个是 `0x8086`（Intel 主桥），7 个是 `0x1af4`（virtio）。**没有 `0x10de`（NVIDIA）** |
| `nproc` / `lscpu` | 8 核，`Intel(R) Xeon(R) Processor`，KVM 虚拟机，支持 AVX-512 / AMX |
| `/proc/meminfo` | `MemTotal: 16386416 kB`（`free -h` 显示 15Gi），`SwapTotal: 0 kB` |
| `df -h /workspace` | 125G，剩余 102G |
| HF_TOKEN / HUGGING_FACE_HUB_TOKEN | 都没有设置（只检查了是否存在，没有打印值） |

### 1.2 结论

- **GPU：无。显存：无。CUDA：无。**
- **本机只能做推理评测，不能训练。** 交接单 §6.1 的要求是 ≥12GB VRAM 才做 4-bit QLoRA，低于 8GB 不开训，本机不满足。
- 本机内存 15Gi、没有 swap。BF16 safetensors 单文件 10,246,621,918 字节（约 10.25GB，见 §3）。即使只做 CPU 推理，加载 BF16 也很紧张，**不能当成训练环境**。本机适合跑 GGUF（约 2.8–3.1GB）的 llama.cpp CPU 推理，配合 `claim_engine.py` 做 S1 base 评测【推演：还没有实跑 llama.cpp】。
- 豆包那台 vm 是 4 vCPU / 7.2GB / 无 GPU。**这条来自交接单 §6.1 的记录，我没有实测。**
- 补充：交接单写的推理底座文件名是 `gemma-4-E2B-it-Q4_K_M.gguf`，但 `ggml-org/gemma-4-E2B-it-GGUF` 里**没有 Q4_K_M**，只有 Q4_0、Q8_0、BF16、mmproj 和 mtp。`unsloth/gemma-4-E2B-it-GGUF` 里有 `gemma-4-E2B-it-Q4_K_M.gguf`，3,106,738,272 字节，LFS sha256 `740185b2…`。用哪个来源需要 Milo 指定（见 §6）。

### 1.3 训练算力方案（供 Milo 选；我没有注册、没有租用、没有付费）

价格都是 2026-11-27 查到的，标 `[C]`，下单前以官网实时页为准。

| # | 方案 | 公开条件（来源） | 是否满足 ≥12GB | 注意 |
|---|---|---|---|---|
| A | 本机只做推理评测（S1 base、S4 对照），不训练 | 本机实测 | 否 | 不花钱。能先把 E2B base 的 10 条评测跑出来 |
| B | 已有的 NVIDIA ≥12GB 机器（Milo 或团队自有） | — | 视机器而定 | 不花钱；需要 Milo 提供机器和访问方式。我这边不能自己接入 |
| C | Kaggle Notebooks（免费） | GPU T4 x2，每卡 16GB；每周约 30 小时，「有时更多」；单次会话最长 12 小时；需要验证过手机号的账号（kaggle.com/docs/notebooks、kaggle.com/docs/efficient-gpu-usage；P100 已退役这一条来自第三方汇总） `[C]` | 是（单卡 16GB） | T4 是 Turing 架构，没有原生 bf16，计算 dtype 可能要改成 fp16【推演】。需要 Milo 本人的账号 |
| D | 阿里云 PAI-DSW 新用户免费试用 | 750 计算时，3 个月有效；A10 24GB 规格 `ecs.gn7i-c8g1.2xlarge` 每小时消耗 6.991 计算时，约 107 小时；只限从没建过 DSW/DLC/EAS 实例的实名新用户；**额度用完或到期后，实例如果还在运行会自动转按量付费**（help.aliyun.com/zh/pai/product-overview/free-trial-guide） `[C]` | 是（24GB） | 需要 Milo 实名账号；有转成付费的风险，必须手动停止并删除实例 |
| E | AutoDL 按量租用 | RTX 4090 24GB 约 ¥1.88–1.98/时；RTX 3090 24GB 约 ¥1.32–1.39/时。**这些价格来自第三方比价站（gpuprice.cn、rentgpu.link、ganai360.com），时间 2026-11-13 到 27 日**。autodl.com 首页是 JS 渲染，我没能直接读到 4090 的标价 `[C]` | 是 | 付费，需要 Milo 本人账号和批准 |
| F | Google Colab | 免费版「GPU 访问非常有限」，单次最长 12 小时；Pro+ 页面标价 CA$67.20/月；**Pro 和按量付费的现价没有查到**（colab.research.google.com/signup）；资源不保证 `[C]` | 视分到的卡而定 | 付费档需要 Milo 本人订阅 |
| G | Lambda 按需实例 | A10 24GB $1.29/GPU/时；A6000 48GB $1.09/时；A100 40GB $1.99/时；另加税（lambda.ai/pricing） `[C]` | 是 | 付费，海外信用卡和账号都要 Milo 本人 |

**参考 `[C]`，厂商自测数字，未复现：**
- Gemma 官方文档（gemma.ai/tuning/）：E2B 做 QLoRA、序列长 2048 时峰值约 7GB。
- Unsloth 文档：E2B LoRA 需要 8–10GB。

所以交接单的 ≥12GB 门槛留有余量。**我的建议**：先走 A，在本机跑 base 评测；训练从 C 或 D（零现金，但需要 Milo 的账号）和 B 里选一个。E、G 作为付费备选。按 CRG-GATE-001 第 6 类，以上都是 **HOLD，等 Milo 本人操作**。

---

## 2. 训练框架：选 PEFT + TRL（Unsloth 作为备选，不作主选）

### 2.1 理由

1. **官方路径。** Google 的 Gemma 文档（gemma.ai/tuning/qlora/，2026-11-27 查阅）的 QLoRA 教程直接用 `transformers` + `peft` + `trl` + `bitsandbytes`，模型正是 `google/gemma-4-E2B-it`，并给出了 E2B 的 `LoraConfig` 写法（见 §3）。
2. **Unsloth 也官方支持 Gemma 4 E2B**（unsloth.ai/docs/models/gemma-4/train，以及 GitHub discussion #4921，2026-04-08）。Gemma 文档也把 Unsloth 列成单卡加速的可选替换。不过：
   - Unsloth 会对 transformers 和 trl 打补丁，训练过程不如原生 PEFT/TRL 透明，对审计和复跑不利；
   - 它说「Gemma 4 训练只有在 Unsloth 里才正常」，这是厂商自述 `[C]`。
   本步要求「可复现、可审计」，所以主线选 PEFT/TRL。如果在 T4 等小显存卡上不够用，再由 Milo 决定是否换 Unsloth。
3. **已知坑：** transformers issue #45242 报告 Gemma 4 在 `use_cache=False` 时 logits 是乱的，loss 在 10–15。该 issue 已关闭，说明修复在 PR #45312。训练时必须用包含这个修复的 transformers 版本；开训前先做一个前向自检：同一输入在 `use_cache=True` 和 `use_cache=False` 下的 logits 应当一致【推演：版本 5.24.1 应已包含该修复，未实测】。

### 2.2 拟采用的版本

来源：PyPI JSON API，2026-11-27 约 01:46 UTC+7 查询。**只是记录，没有安装。** 实际版本以训练机上的 `pip freeze` 为准，并写进 `runs/<id>/manifest.json`。

| 包 | 拟用版本 | PyPI 发布时间 | Gemma 文档给的下限 |
|---|---|---|---|
| transformers | 5.24.1 | 2026-11-24 | ≥5.10.1 |
| peft | 0.22.0 | 2026-11-19 | ≥0.19.0（需要支持 `exclude_modules`） |
| trl | 1.19.0 | 2026-11-25 | ≥0.16.0 |
| bitsandbytes | 0.50.2 | 2026-08-27 | — |
| accelerate | 1.16.0 | 2026-11-16 | — |
| torch | 2.15.0（CUDA 构建按训练机驱动选） | 2026-10-28 | — |
| 备选：unsloth / unsloth_zoo | 2026.11.12 | 2026-11-25 | — |

所有包要求 Python ≥3.11。CUDA 和 cuDNN 版本要到训练机上实测后才能写，现在不填。

---

## 3. E2B 结构与 LoRA target modules

### 3.1 证据来源（都是公开的，没用 token；仓库 `gated=false`，license 为 apache-2.0）

- **E1：** `https://huggingface.co/api/models/google/gemma-4-E2B-it` → 仓库 sha `4adf15748de9e1a0097b6274cee9c15836c41c37`，`safetensors.parameters.BF16 = 5,123,178,051`
- **E2：** `.../raw/main/config.json`（4954 字节）→ `Gemma4ForConditionalGeneration`，带 `audio_config`、`vision_config` 和 `text_config`
- **E3：** `.../raw/main/README.md`（模型卡）
- **E4：** `model.safetensors` **只读了文件头**。用 HTTP Range 取前 8 字节加 263,952 字节的 JSON 头，**没有下载权重本体**。头 JSON 的 sha256 是 `12740d6f…`，共 2011 个张量名
- **E5：** Gemma 官方 QLoRA 教程（gemma.ai/tuning/qlora/）
- **E6：** transformers issue #45242 的讨论（KV 共享与 `use_cache`）

### 3.2 参数规模

| 项 | 数值 | 来源 |
|---|---|---|
| 总参数 | 5,123,178,051（约 5.1B） | E1 |
| 张量头合计 | 5,123,178,979 | E4。比 E1 多出 928，正好是 928 个标量张量（如 `input_max`、`input_min`、`layer_scalar`）；我推测 E1 没有计入这些标量【推演】 |
| 模型卡写法 | 「2.3B effective（5.1B with embeddings）」 `[C]` | E3。E 的意思是 effective，靠 Per-Layer Embeddings（PLE）实现 |
| `embed_tokens_per_layer` | 2,348,810,240，形状 [262144, 8960] | E4 |
| 文本 decoder 层合计 | 1,882,222,115（35 层） | E4 |
| `embed_tokens` | 402,653,184 | E4 |
| audio_tower 及投影 | 约 0.30B（模型卡写 ~300M `[C]`） | E4 / E3 |
| vision_tower 及投影 | 约 0.17B（模型卡写 ~150M `[C]`） | E4 / E3 |
| BF16 单文件大小 | 10,246,621,918 字节，LFS sha256 `2db5482b…` | HF tree API |

### 3.3 多模态：有音频塔和视觉塔，要冻结

- **有音频塔：** 12 层 conformer 类结构，`model.audio_tower.*`。
- **有视觉塔：** 16 层，`model.vision_tower.*`。
- 两个塔里的线性层都包在 `Gemma4ClippableLinear` 里，实际权重名是 `...q_proj.linear.weight`，同一个模块下还有 `input_min/max` 和 `output_min/max` 标量（E4、E5）。
- **建议：** LoRA 只挂在 `model.language_model.layers.*` 上。音频塔、视觉塔，以及 `embed_audio`、`embed_vision`、PLE 相关部分，全部冻结、不挂 adapter。

### 3.4 推荐的 target modules

文本 decoder 每层都有这 7 个线性层，35 层全有（E4 张量名实证）：

```
self_attn.q_proj  self_attn.k_proj  self_attn.v_proj  self_attn.o_proj
mlp.gate_proj     mlp.up_proj       mlp.down_proj
```

这些名字正好与 Qwen 的同名。这一点是**由 E4 张量名证实的，不是照抄 Qwen**。

推荐写法与 Gemma 官方教程 E5 一致：

```python
LoraConfig(r=16, lora_alpha=32, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
  target_modules=["q_proj","k_proj","v_proj","o_proj","gate_proj","up_proj","down_proj"],
  exclude_modules=r"model\.(vision_tower|audio_tower)\..*")
```

更严格的备选：用正则 `r"model\.language_model\.layers\.\d+\.(self_attn\.(q|k|v|o)_proj|mlp\.(gate|up|down)_proj)"`，只匹配文本层。

**这里哪些有证据、哪些是推演：**

| 结论 | 证据级别 |
|---|---|
| 7 个模块名存在于全部 35 层 | E4 实证 |
| 每层形状不一样，不是统一大小：<br>• `layer_types` 里第 4/9/14/19/24/29/34 层是 full_attention，这些层 q 为 4096×1536、k/v 为 512×1536、o 为 1536×4096；<br>• 其余是 sliding 层，q 为 2048、k/v 为 256、o 为 1536×2048；<br>• 第 15–34 层的 MLP 是双宽，intermediate 为 12288，第 0–14 层是 6144（对应 `use_double_wide_mlp=true`） | E4 实证 |
| `num_key_value_heads=1`；head_dim 256，global 层 512 | E2 |
| `num_kv_shared_layers=20`（E2）。我推测第 15–34 层复用前面层的 K/V，**这些层的 `k_proj`/`v_proj` 在前向里可能根本不参与计算，挂上 LoRA 也拿不到梯度**【推演：要在训练机上加载后，看这些 lora_B 的梯度是否恒为 0】。这部分只占 r16 adapter 的 1,179,648 个参数 | E2 + E6 + 推演 |
| r=16、7 个模块、35 层时，adapter 总参数约 25,337,856（约 0.49%） | 按 E4 形状算出来的【推演】；实际 `print_trainable_parameters()` 要等加载后才能确认 |
| PEFT 在塔内会不会误匹配 `q_proj` 等包装模块并报错，`exclude_modules` 能否完全规避 | E5 的说法是能规避【推演：未实跑】 |

**还需要在训练机上用 `model.named_modules()` 实测的项：**
1. 实际 `nn.Linear` 和 `bnb.Linear4bit` 的完整名单；
2. 4-bit 加载后，塔内的 ClippableLinear 是否被量化；
3. KV 共享层上 k/v LoRA 的梯度；
4. 可训练参数比例；
5. `use_cache` 前向一致性。

---

## 4. 50 train + 10 holdout 数据计划（只是计划，没有生成任何 train.jsonl / holdout.jsonl）

### 4.1 已能读到的资产（包内，sha256 见下）

| 资产 | sha256 | 内容 |
|---|---|---|
| `eval/seed.jsonl` | `4b6cc1cb…` | 10 条，E001–E010，字段 id/prompt/anchor/expect/fail_if/claim |
| `claim_runtime/claim_engine.py` | `7050977d…` | -1 校验器 |
| `claim_runtime/governed_runtime.py` | `22ec3970…` | — |
| `claim_runtime/run_eval.py` | `38fcb317…` | — |
| `governance/claim_policy_v0.json` | 文件 `96591271…` / 规范化 `72b5c2d4…` | **只覆盖 E003、E004、E006、E009 这 4 个 case** |
| `governance/calibration_e003.jsonl` | `ec3a8caf…` | 18 条：E003 有 6 PASS / 6 HOLD；E004/E006/E009 各 1 PASS / 1 HOLD。来源字段 src 为 frozen-commit / frozen-e003 / poison-all / synthetic |
| `governance/holdout_e003.jsonl` | `9696e097…` | 10 条，全是 E003，6 PASS / 4 HOLD |

**只读复跑**（在 `/tmp/crt` 的临时拷贝里跑，没碰包内的 `state/` 账本）：

```
python3 claim_engine.py calibrate --file governance/calibration_e003.jsonl  → calibration: 18/18
python3 claim_engine.py calibrate --file governance/holdout_e003.jsonl      → calibration: 10/10
```

这是对 -1 校验器本身的复现，与 CLAIM_LEVEL_REPORT 一致，**不是模型能力数字**。

### 4.2 关键约束（来自包内事实）

1. **只有 4 个 case 能被 claim_engine 判定**（E003/E004/E006/E009）。E001/E002/E005/E007/E008/E010 在 `claim_policy_v0` 里没有规则。所以 smoke 数据**只从这 4 个 case 出**。要扩 case，需要 Milo 或豆包先扩 policy，我不自己改。
2. **路径不一致：** `run_eval.py` 和 `governed_runtime.py` 都写死读 `ROOT.parents[1]/eval/cases/seed.jsonl`，而 v2 §0.3 的放法是 `lab/02-gemma-e2b-eval/eval/seed.jsonl`，按这个放法会读不到。后续新写的 `eval_e2b.py` 应该显式传路径，不去改包内脚本。
3. **流程冲突要 Milo 明确：** CLAIM_LEVEL_REPORT §6 和 GOVERNANCE_REPORT §4.3 都写着「现在仍然不该 QLoRA」，要求先把 holdout 扩到每类 50+。交接单 §5.3 把每类 50+ 定为「正式训练前」的 G0 门槛，smoke 只要求 ≥50/≥10。我的理解是：**smoke 只验证过程能不能学会，不产出正式权重，不与报告冲突**【推演】。这一点请 Milo 书面确认。

### 4.3 schema

沿用交接单 §5.1：`id, case_id, prompt, anchor_excerpt, draft, claims[{claim_id, subject, predicate, object, polarity, kind, evidence}], verdict, hold_reason, rollback_required, source, license, split`。

另外建议加 4 个字段：
- `engine_verdict`：claim_engine 的实际输出
- `engine_sha`：claim_engine.py 的 sha256
- `policy_hash`：规范化后的 `72b5c2d4…`
- `text_sha256`：draft 和 target 各算一个哈希，用于去重和防泄漏

**训练 target 的形态需要 Milo 选：**
- **形态 1（推荐）：** 输入是 prompt + 可选的 anchor_excerpt + draft；目标是 claims、verdict 提议和 hold_reason。adapter 学的是给 draft 做 claim 标注。
- **形态 2：** 输入是 prompt；目标是「定位/收束/回轴」格式的回答，外加 claims 列表。

不管哪种形态：**adapter 输出的 verdict 只是提议，最终判定一律由 claim_engine.py 做**，满足硬约束 §3.2「-1 独立」。

### 4.4 配比（50 train）

| case | 条数 | 正例 PASS | 负例 HOLD |
|---|---|---|---|
| E003（必须覆盖） | 20 | 10 | 10 |
| E004 | 10 | 5 | 5 |
| E006 | 10 | 5 | 5 |
| E009 | 10 | 5 | 5 |
| **合计** | **50** | **25** | **25** |

25 条负例全部是交接单 §5.2 定义的「漂移」类，**不是胡编**。5 类漂移每类各 5 条：
1. 结论对，但 evidence 是假的；
2. 前半对，后半偷偷 `self+`；
3. 把条件句的前件当成断言；
4. 把疑问句当成主张；
5. 双重否定被否定窗口带跑。

注意以下两点：
- 第 1 类「假 evidence」，claim_engine 自己判不出来，因为 engine 的 evidence 就是原句本身。需要另加一条 schema 级检查：**`evidence` 必须是 draft 的逐字子串**。
- 第 5 类双重否定，报告承认还没压测。engine 判出来的结果如果与人工标注不一致，**不许改标签去迁就 engine**，要记成 `FAIL-###`。

### 4.5 holdout（10 条）

- **建议**直接用现成的 `holdout_e003.jsonl` 的 10 条做 draft：6 PASS / 4 HOLD，全是 E003，哈希已固定（`9696e097…`）。
- 缺点：只覆盖 E003。是否另补 E004/E006/E009 的 holdout，由 Milo 定。
- **holdout 绝不进 train。**
- **calibration_e003 的 18 条也不进 train**，因为它是用来调 -1 的，混进去会让 +1 和 -1 共享数据。
- 去重分两步：
  1. 对规范化文本（去空白和标点）做 sha256 精确比对；
  2. 再做近重复检查：字符 5-gram 的 Jaccard ≥0.6 就判为重复，剔除【推演阈值，请豆包定】。
- 两步都要跨 train、holdout、calibration 三个集合做，结果写进 `data/manifest.json`。

### 4.6 来源与许可

- **prompt：** 来自 `seed.jsonl` 里那 4 个 case 的原题，加上人工改写的问法。
- **draft 来源只允许三种：**
  - (a) 包内 state/state_claim 里 Qwen3-4B 的真实草稿（model sha `8cdb57cb…`；Qwen3 许可需要 Milo 确认）；
  - (b) 本机跑 E2B base 推理得到的草稿；
  - (c) Milo 或豆包人工写的变体。
- **不使用 Claude 或 OpenAI API 生成任何数据。**
- `source` 字段取 `model|human|synthetic`，并写明具体出处（文件名或 run_id）。
- `license` 字段：仓库代码为 Apache-2.0、文档为 CC BY 4.0。最终用 `CC-BY-NC-4.0`（交接单示例）还是其它许可，由 Milo 定。
- **不含学生数据，不含未脱敏的教师轨迹，不含真实姓名或作文。** E009 只是关于学生数据政策的问答，不含任何学生数据本身。

### 4.7 0 不进权重（A1）

- 训练 target 里**不得出现** `anchor_v0.json` 9 行 `lines` 中的任何一行原文，也不得出现 `claim_policy_v0.json` 的 `question`、`note` 原文或正则规则原文。
- 这些内容只能放在输入的 `anchor_excerpt` 里。
- 检查方式：
  1. 自动比对子串；
  2. 再算 target 与每一行 anchor 的最长公共子串，≥10 个汉字就打标，交人工复核【推演阈值】。
- seed 的 `expect` 字段与 anchor 文字很接近，**不能直接当 target**。

### 4.8 生成后的闸门

1. 每条都过 schema 校验。
2. 每条都跑 `claim_engine.evaluate`：`engine_verdict` 必须等于标注的 `verdict`；不一致的条目不进集合，记成 FAIL。
3. 检查 evidence 是否逐字回指 draft。
4. 做去重和防泄漏检查。
5. 写 `manifest.json`：逐条哈希，以及 engine、policy、anchor 的规范化哈希。
6. **豆包抽检 10 条，正例、负例各 5 条。**

---

## 5. 重要异常：固定哈希「不一致」已查清，**能复现**

交接单 §4.1 的「固定哈希」**不是文件级 sha256**，而是 `governed_runtime.py` 里的规范化 JSON 哈希。源码第 28–57 行：

```python
canon(obj) = json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode()
anchor_hash(a) = sha256(canon(a 去掉 "sha256" 键))
```

`claim_policy_v0` 用同样的方法算，结果就是文件里自带的 `sha256` 字段。

| 文件 | 文件级 sha256 | 规范化（去掉 sha256 键）sha256 | 文件内自带 sha256 字段 | 交接单 §4.1 |
|---|---|---|---|---|
| anchor_v0.json | `112da3a3…` | `86f481cf1f3508c2…f32be` | `86f481cf…` | `86f481cf…` ✅ |
| claim_policy_v0.json | `96591271…` | `72b5c2d4e7f6641e…a438` | `72b5c2d4…` | `72b5c2d4…` ✅ |
| policy_v0.json（旧的正则版 policy） | `c02e3b92…` | `060df934ff2d8bf3…84ba` | `060df934…` | — |
| anchor_flipped.json（投毒锚定） | `c79b2f3d…` | `e70d541c…` | `e70d541c…` | — |

- 反例检查：如果改用 `ensure_ascii=True` 或带缩进的序列化，算出来的值都对不上（例如 anchor 会得到 `2c2e2fe3…` 或 `a89948f9…`）。**只有上面这个算法能复现。**
- **audit 里的 `policy_hash 060df934…`** 对应 `governance/policy_v0.json`，也就是旧的正则 policy。它只出现在 `state/audit*.jsonl`；claim 版账本 `state_claim/audit*.jsonl` 里的 `policy_hash` 是 `72b5c2d4…`。
- 账本里的 `anchor_hash` 有两种值：
  - `86f481cf…`：冻结锚定；
  - `e70d541c…`：anchor_flipped，也就是投毒或回滚测试用的锚定。
- 包里两个 `state*/model.sha256` 都是 `8cdb57cb…`，与交接单里 Qwen3-4B 的哈希一致。

**结论：规范化哈希一致，文件级哈希不同，不算 FAIL。** 建议交接单 §4.1 注明算法：`sha256(json.dumps(obj 去掉 "sha256" 键, ensure_ascii=False, sort_keys=True, separators=(",",":")).encode("utf-8"))`，并同时列出文件级 sha256，免得验收时误判。我没有改任何文件。

---

## 6. 缺资产 / 待提供清单（不重写，等 Milo）

| # | 项 | 状态 |
|---|---|---|
| 1 | seed.jsonl、claim_engine.py、governed_runtime.py、run_eval.py、anchor、policy | ✅ 已在包内拿到 |
| 2 | SPEC/03-metrics-and-gates.md | ✅ 远端 `origin/lab/day-0-skeleton` 上可读（只读 `git show`，没有 checkout）。是否以这一版为准，待确认 |
| 3 | E004/E006/E009 的 holdout，以及 E001/E002/E005/E007/E008/E010 的 claim policy | ❌ 缺。要扩 policy 归 Milo 或豆包 |
| 4 | 训练算力（§1.3 里选一个）和对应账号 | ❌ 待 Milo |
| 5 | GGUF 来源：ggml-org 的 Q4_0，还是 unsloth 的 Q4_K_M | ❌ 待 Milo |
| 6 | 数据许可口径（CC-BY-NC-4.0 还是其他）；Qwen 草稿能否再用于训练 | ❌ 待 Milo |
| 7 | HF 访问 | 不需要。`google/gemma-4-E2B-it` 是公开仓库（gated=false），以后下载不需要 token |

## 7. 待 Milo 决定

1. 训练算力选哪个方案（§1.3 的 A–G）。凡是付费或要开账号的，都要 Milo 本人操作。
2. **下一步待 Milo 批：在本地建分支 `lab/02-gemma-e2b-smoke`，按 v2 §0.3 把 `claim_runtime/` 和 `eval/seed.jsonl` 放进 `lab/02-gemma-e2b-eval/`，并开 PR。** 只走 PR，不碰 main，不 merge。
3. smoke 与报告里「先别 QLoRA」的关系，需要书面确认（§4.2 第 3 条）。
4. 训练 target 形态选 1 还是 2（§4.3）；holdout 是否只用 E003（§4.5）。
5. 包链接 `XCzWwH2UJK` 和 `x9uMhk4tTU` 哪个对（§0）；交接单 §4.1 是否补上哈希算法（§5）。
6. 选好的 GGUF 量化版本。
7. adapter 是否不进 git、只留 manifest 加 hash（交接单 §11.6 的建议是「是」）。

---

*本文件的 sha256 不写进文件本身，因为写进去就会变。请豆包验收时自己跑 `sha256sum /workspace/handoffs/gemma-e2b/STATUS.md`。*

---

## 8. 补记 · 2026-11-27 02:20 (UTC+7)：Milo 回复后的更新

本节只追加，前面各节的原文没有改动。

### 8.1 HASH-01：NOT FAIL（完整 64 位哈希）

规范化算法（来源：`governed_runtime.py`）：

```python
o = json.loads(open(path, "rb").read()); o.pop("sha256", None)
sha256(json.dumps(o, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode("utf-8")).hexdigest()
```

| 文件 | 文件级 sha256 | 规范化 sha256 |
|---|---|---|
| anchor_v0.json | 112da3a356b95cef817099a2d142b5ee8fa11fadb8ea5b00cba22afb08668a03 | 86f481cf1f3508c2cf92bb7b1e9ce8299532bdd0122b5e707273dca4814f32be |
| claim_policy_v0.json | 96591271f747fa111c4360f0843a352af34467d6653b2b525b373862a525c5a3 | 72b5c2d4e7f6641eacfddd34f639b0b9ff5eed414d0e22af8480e4d946d1a438 |
| policy_v0.json（旧正则版） | c02e3b9219597ec650d6c5047d82f7afa12c4a6711b63f167022af468961c29d | 060df934ff2d8bf39618bb3374bf6785f89293ac4a71a72057f1c9b681b784ba |
| anchor_flipped.json（投毒/回滚测试） | c79b2f3da5807bb59a90b42df636ecf3a759a01084064c07b0befdb74c5036c6 | e70d541ce1d209f5ac9735dd9ef69f40051ac6b63049e211377194cba73ce5d9 |

以上数值在本机实算（02:20 UTC+7）。规范化哈希与交接单 §4.1 一致，记 **HASH-01: NOT FAIL**。

其他输入文件：
- runtime 包 zip：bea9ac1f068b35b07f79e584ced3d703bc4bf3b978a1a1fdf5df16e41ae42390
- v2 交接单：cc55633563caac9d970e046877ba25ad1ccb4305576b746632d53e18849cf6b5

### 8.2 包链接

据 Milo 转述，两个短码都返回 200、57,808 字节，是同一文件。以 `x9uMhk4tTU` 为准，本节第 6 条的待核项关闭。

说明：我这边没有下载核对。附件 zip 本机实测为 57,808 字节（见下方命令）。这个包现在只作离线备份，主路径改为 GitHub PR 分支。

### 8.3 Milo 给出的建议口径（照录；凡是动仓库或花钱的，都要等 Milo 明确批准才执行）

- **算力**：首选阿里云 PAI-DSW A10 试用；没有阿里云账号就用 AutoDL 3090 24GB，充值上限 ¥20；Kaggle T4 作零成本兜底，设 `save_total_limit=1`，不存 merged BF16；不用 3080Ti 12GB，不开 Colab Pro，不用 Lambda。估算区间 ¥0–8，标 [C]。
- **分支与 PR**：建议只开 draft PR，只提交 STATUS.md、探测脚本和 data manifest；不提交权重和 safetensors，不 merge。
- **GGUF**：推理基线用 ggml-org Q4_0（canonical）；unsloth Q4_K_M 只作社区量化对照，两者的结论不混用。训练底座为 `google/gemma-4-E2B-it` safetensors。
- **smoke 书面口径（待 Milo 定稿）**：批准一次 E2B smoke QLoRA，仅用于流程验证；不进入正式后训练，不发布权重，不声称提升；0 不进权重；-1 仍由 `claim_engine.py` 在外部执行；train 与 holdout 不交叉。

### 8.4 范围提醒：holdout 只覆盖 E003

holdout 只有 E003 的 10 条，所以这一轮 smoke 最多只能说明「E003 的过程可学」，不能说明 E004/E006/E009 能泛化。

建议开训前先补 E004/E006/E009 的 holdout。这是 CPU 上的工作，不占 GPU：
- 每个 case 至少 4 条，正负都要有，用 `claim_engine.py calibrate` 判定；
- 与 train、calibration 做哈希去重和近重复检查；
- 由豆包抽检；
- 需要 Milo 先确认：候选草稿从哪里来、用什么许可（第 6 节第 6 条）。

### 8.5 关于豆包读不到本文件

本文件在幕僚长助手和 CGI/CRG 治理共用的云端电脑上，豆包那台机器默认读不到。可选的同步方式：
- (a) 随 draft PR 推上仓库，需要 Milo 批准 push；
- (b) 由 Milo 或幕僚长助手按 SYNC-LOG 的做法复制到 Windows，再用 Get-FileHash 核对。

本文件的 sha256 不写进文件本身。
