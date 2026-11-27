# POST-TRAINING-LESSONS · 从灰箱链路到 DeepSeek 式验证器

**状态：** 方法论复盘，不是实验结论；已入仓库，未合并 main。
**日期：** 2026-11-27
**时区：** Asia/Bangkok (UTC+7)
**范围：** A4/A5 事实基线 + DeepSeek-V3/R1 公开后训练模式 + GitHub 小模型后训练能力地图。
**一句话：** 这次真正跑通的不是“训练一个更聪明的模型”，而是“训练—评测—外部裁决—证据落盘”的灰箱；下一步不是加 epoch，而是把验证器变成奖励、把拒绝采样放在 RL 前面。

---

## 0. 结论先行

1. **这次最大的收获不是某个 adapter，而是顺序被看清了：** 先冻结裁判，再训练模型；先有可验证的尺子，再谈模型能力。
2. **CRG 的 `0 / -1 / +1` 在模型内部被工程验证，而不是被口号验证：** `0` 不进权重，`-1` 不能自评，`+1` 只负责生发。
3. **DeepSeek 最值得学的不是 GRPO，而是“验证器优先”的后训练流水线：** 冷启动 SFT → 可验证奖励 RL → 拒绝采样 → 再 SFT → 蒸馏。
4. **对小模型最现实的第一步不是 RL，而是“拒绝采样 + 外部过滤 + SFT”：** 同一 prompt 采多条，用 `claim_engine` 过 policy，保留合格轨迹再训练。
5. **GitHub 上值得学的不是一堆框架，而是六种能力：** 低成本微调、数据构造、偏好/RL、结构化解码、评测复现、验证器过滤的蒸馏。

---

## 1. 这次训练真正收获了什么

### 1.1 从黑箱到灰箱

不是“看穿了神经元”，而是第一次把下面这些环节放在同一张桌上：

```text
prompt → target → adapter → eval → claim_engine → policy → evidence → hash → PR
```

模型的输入、输出、失败分类、外部裁决、证据哈希，都可追、可归因、可复现。这叫灰箱，不叫白箱。

行业里后训练闭环并不新鲜；真正少见的是在很小的教学/实验室场景、零预算下，把这条链完整跑通，并且不把“模型自评”当成最终裁决。

### 1.2 CRG 的边界被工程验证

从模型内部看，会看到它天然把三件事混在一起：

- **锚定从哪来**：模型会把训练数据里的“来源感”吸收进权重；
- **谁有否决权**：模型会把“我是否相信”混进“契约是否接受”；
- **谁只负责生发**：模型擅长生成候选，不擅长对外部规则做最终裁决。

于是：

- `0` 不进权重——锚定必须是外部参照，不是训练目标；
- `-1` 由 `claim_engine.py` 独立裁决——模型不能自己批自己；
- `+1` 只负责生发——claim 抽取、候选生成、语言组织。

这不是玄学，是训练目标决定的结构性边界。CRG 的“秩序”必须落到 target、prompt、policy、hash 上，否则只是话。

### 1.3 链路跑通

这次实际跑过的链路：

```text
A3 50 条 train
→ Qwen3-4B 4-bit QLoRA（13 步 / 50.8 秒 / train_loss 1.2597）
→ base / adapter 同尺评测
→ v2 prompt 不训练对照
→ 模型 claims 交外部 claim_engine 重判
→ 证据落盘 / 哈希 / PR
```

事实基线：

- base：结构 10/10、严格 schema 0/10、verdict 0.20；
- adapter：结构 10/10、严格 schema 5/10、verdict 0.30；
- v2 prompt base：结构 10/10、`claim_id_allowed` 10/10、`strict_contract_pass` 0/10、verdict 0.30；
- v2 模型 claims 交 policy 重判：0.80；模型自己的 verdict 与自己的 claims 的 policy 重判只有 5/10 一致。

这组数字说明的不是“模型变强了”，而是：**抽取先验比裁决先验更接近目标；裁决必须外置。**

### 1.4 底座观察：Qwen 与 Gemma

| 维度 | Qwen3-4B-Instruct | Gemma 4 E2B | 判断 |
|---|---|---|---|
| 任务形态 | 纯文本、dense、工具链简单 | 多模态结构，文本之外还有塔和模板 | Qwen 更适合第一控实验 |
| 中文契约 | 中文语料和中文指令先验更贴近 | 多语言能力有，但中文不是主战场 | 中文 claim 任务，Qwen 摩擦更小 |
| 格式学习 | 旧 target 下 adapter strict schema 5/10 | 旧 prompt 下 adapter strict schema 0/10 | 只说明 Qwen 在这批 target 上更容易学格式，不是能力排名 |
| 行为先验 | base 8/10 HOLD，adapter 9/10 HOLD | 旧产物 HOLD 0/9，偏 PASS | 一个偏保守，一个偏放行；都不是校准好的裁决器 |
| 工程复杂度 | 4B 文本，16GB 可跑 | 多模态加载、processor、塔冻结多一层 | Qwen 先跑，Gemma 留第二底座 |

结论：**Qwen 更适合这条训练流程的第一底座；但“更可能产出 CRG 预期结果”不成立，除非 `-1` 继续外置。** Gemma 的价值在第二底座和多模态课堂演示，不是第一控实验。

---

## 2. 最大的遗憾，也是最大的收获

**遗憾：先训练，后修尺子。**

50 条 QLoRA adapter 是在旧 prompt、旧 verdict 语义、旧 claim_id 规则下训出来的；v2 契约出现后，它已经失去“受控对照”的资格。它不是没价值，而是不能拿来证明 v2 的效果。

**收获：因此看清了顺序。**

如果重来一次，顺序应该是：

```text
冻结 contract_semantics_v1
→ 冻结 claim_id allowlist + strict gate
→ 先跑 base / v2 prompt 对照
→ 再决定是否训练
→ 训练后仍由 claim_engine 做最终裁决
```

“裁判没定，训练已开跑”不是执行失误，是方法论缺口。这个缺口现在被写进了流程，而不是被藏进分数里。

---

## 3. DeepSeek 后训练模式，哪些能学

### 3.1 它的流水线

以 DeepSeek-V3 / R1 的公开技术报告为参照：

1. **冷启动 SFT**：先给模型一个稳定初始策略；
2. **可验证奖励的 RL**：数学、代码等可验证任务用规则奖励；开放任务才用奖励模型；
3. **拒绝采样**：用当前策略采多条，规则筛出合格轨迹；
4. **再 SFT**：把筛出的轨迹变成下一轮训练数据；
5. **蒸馏**：把大模型能力迁到小模型。

R1-Zero 证明纯 RL 可以从 base 涌现推理，但也暴露了语言混杂、重复、格式崩；后来的冷启动不是装饰，是稳定性修复。

### 3.2 五个可学机制

| DeepSeek 机制 | 核心 | 对我们的映射 | 现在能不能做 |
|---|---|---|---|
| 规则奖励 | 可验证任务不用奖励模型自由发挥 | `claim_engine` + 冻结 policy 就是规则验证器 | 能，零 GPU |
| 冷启动 | 少量高质量种子，先稳住策略 | A3 的 50 条 gold + 硬负例 | 能，先补负例 |
| 拒绝采样 | 多采、规则筛、再 SFT | 同一 prompt 采 4–8 条，用 policy 过滤 | 能，小 GPU |
| 蒸馏 | 大模型生成，小模型学习 | 大模型生成 claim，policy 过滤后蒸馏 | 能，中等 GPU |
| GRPO | 组内相对优势，省掉 critic | 只在窄任务、规则奖励稳定后试 | 最后再做 |

**最值得学的是前四个，不是第五个。** GRPO 省的是显存，不是采样成本；奖励不稳时，照样 reward hacking。

### 3.3 对我们的直接启示

1. **不要再训一个 reward model 判 PASS/HOLD。** `claim_engine` 就是你们的 rule-based verifier；把冻结 policy 直接当奖励函数，模型只负责抽 claim。
2. **先做拒绝采样 SFT，不要先 GRPO。** 同一 prompt 采 4–8 个候选，用 `claim_engine` 过 policy，保留 accepted 的做 SFT。零预算、单卡可跑，比 RL 稳。
3. **格式问题优先用 constrained decoding 解决。** JSON schema、claim_id 枚举、polarity 用 `outlines`/`sglang` 约束住，不要全交给 50 条训练数据。
4. **蒸馏要“验证器过滤”，不要信 teacher 的 verdict。** 大模型可以生成候选 claim，但 PASS/HOLD 必须由外部 policy 判；否则只是把大模型的偏差蒸馏进小模型。
5. **如果真做 RL，只做窄任务。** 4B + LoRA + GRPO + 规则奖励，可以试；开放式 RL 不要碰。先问“reward 是否可验证”，再问“算法是否先进”。

### 3.4 不可照搬

- **不要照搬 671B 的算力。** 我们学的是顺序，不是规模。
- **不要直接做 R1-Zero 式纯 RL。** 小模型大概率不稳定；先冷启动。
- **不要用奖励模型替代 `-1`。** 奖励模型也会被奖励 hacking，尤其在小数据上。
- **不要在尺子没冻结前开 RL。** 那会把错误口径放大成策略。

---

## 4. GitHub 小模型后训练能力地图

以下以公开仓库的 README 和常见用法为准；仓库可能改名，按 org 搜索最新地址。

| 能力 | 代表仓库 | 学什么 | 对 NAC 的用法 |
|---|---|---|---|
| 低成本微调 | [unsloth](https://github.com/unslothai/unsloth)、[peft](https://github.com/huggingface/peft)、[torchtune](https://github.com/pytorch/torchtune) | 4-bit QLoRA、16GB 单卡手感、可复现 recipe | 先把 Qwen3-4B 跑顺 |
| 统一训练/复现 | [LLaMA-Factory](https://github.com/hiyouga/LLaMA-Factory)、[axolotl](https://github.com/axolotl-ai-cloud/axolotl) | 配置驱动、多模型、日志与断点 | 做可复现实验记录 |
| 偏好优化/RL | [trl](https://github.com/huggingface/trl)、[OpenRLHF](https://github.com/OpenRLHF/OpenRLHF)、[verl](https://github.com/volcengine/verl) | SFT/DPO/GRPO 的真实实现、reward 接口 | 先读代码，不先跑大 RL |
| 结构化输出 | [outlines](https://github.com/dottxt-ai/outlines)、[guidance](https://github.com/guidance-ai/guidance)、[sglang](https://github.com/sgl-project/sglang) | JSON schema/grammar 约束解码 | 把格式从训练问题降成解码问题 |
| 数据构造 | [distilabel](https://github.com/argilla-io/distilabel)、[open-instruct](https://github.com/allenai/open-instruct)、[alignment-handbook](https://github.com/huggingface/alignment-handbook) | 合成数据、SFT 混合、偏好数据 | 造硬负例、做验证器过滤 |
| 评测 | [lm-evaluation-harness](https://github.com/EleutherAI/lm-evaluation-harness)、[lighteval](https://github.com/huggingface/lighteval)、[inspect_ai](https://github.com/UKGovernmentBEIS/inspect_ai) | 冻结评测、可复现日志、任务级诊断 | 先评测，再训练 |
| 小模型课程 | [smol-course](https://github.com/huggingface/smol-course)、[nanoGPT](https://github.com/karpathy/nanoGPT)、[LLMs-from-scratch](https://github.com/rasbt/LLMs-from-scratch) | 从零理解、小模型配方、教学视角 | 培训和校内老师 |

### 4.1 如果只选三个

1. **`unsloth`**——先让 4B 在 16GB 上跑得动，建立手感。
2. **`trl`**——看懂 SFT、DPO、GRPO 到底怎么实现，不被教程糊弄。
3. **`inspect_ai` + `lm-evaluation-harness`**——评测先行，别再用一个总分骗自己。

再加半个：**`outlines`**——把格式从“训练问题”降成“解码问题”。

### 4.2 不要做

- 不要一上来碰 `verl`/`OpenRLHF` 的大规模 RL；4B 单卡跑不动，容易变成调参。
- 不要收藏一堆 `awesome` 列表；选三个仓库跑通。
- 不要用 reward model 替代 `claim_engine`；会 reward hacking。
- 不要把“结构 10/10”当成“模型能力通过”；严格 schema 仍是 0/10。

---

## 5. 对 NAC Lab 的下一步

### P0 · 零 GPU：先把尺子修完

- [ ] 修 `eval_e2b.claim_set()` 与 `contract_eval.claim_set()` 的 polarity 归一化，从现有 v2 `eval.json` 重算。
- [ ] 决定 `kind` 是收紧到五枚举，还是把 `source/definition/existence` 纳入 rubric；先做离线影响评估。
- [ ] 明确 verdict 归属：模型 verdict 与 `claim_engine.adjudicate_claims()` 分两列，不互相替代。
- [ ] 把 `claim_id` 允许表、`kind` 枚举、strict gate 写进云端实际执行门，而不只是本机 rubric。
- [ ] 建硬负例池：alias polarity、`forbidden_any`、空 claims + PASS、双重否定、条件前件、长 claim 截断。

### P1 · 小 GPU：拒绝采样 SFT

- [ ] 同一 train prompt 采 4–8 条候选。
- [ ] 用 `claim_engine` 过 policy，保留 accepted 轨迹；不要用模型 verdict 过滤。
- [ ] accepted + 原 50 条一起做 1 epoch SFT。
- [ ] 同一 10 条 holdout 对比 base / 旧 adapter / 新 adapter。
- [ ] 先看 `strict_contract_pass` 是否从 0 变正，再看 verdict。

### P2 · 蒸馏：验证器过滤的蒸馏

- [ ] 用更大的 Qwen/DeepSeek 生成候选 claim。
- [ ] 只用 `claim_engine` 过滤，不信 teacher 的 PASS/HOLD。
- [ ] 把合格轨迹蒸馏到 Qwen3-4B；holdout 永不参与。
- [ ] 与 P1 的拒绝采样结果对比，不跨 rubric 比较。

### P3 · RL：只在窄任务上试

- [ ] 先确认 rejection sampling 已饱和；否则 RL 只是更贵的采样。
- [ ] reward 只做可验证项：结构、schema、claim_id、policy 接受。
- [ ] 4B + LoRA + GRPO，先算 token 预算；不碰开放式 RL。
- [ ] 任何 RL 结果仍由 `claim_engine` 做最终裁决。

### 验收门槛

| 项目 | 门槛 |
|---|---|
| 结构合格 | base 与 adapter 都 ≥ 8/10 |
| 严格契约 | `strict_contract_pass` 至少出现正例，且可解释 |
| claim_id | `claim_id_allowed` 10/10 |
| verdict | 高于 always-PASS 0.60；HOLD recall ≥ 1/4 |
| claims→policy | ≥ 0.80，且与模型 verdict 分开报 |
| 退化检查 | adapter 不得低于 always-HOLD 0.40；PASS recall 不得为 0 |

达不到：查生成停止、target 序列化、约束解码；不补数据、不加 epoch、不进正式 run。

---

## 6. 边界声明

- **不是行业首创。** 后训练闭环、QLoRA、评测集、错误分析，业界都做过；我们真正少见的是小场景、零预算、灰箱闭环。
- **不是白箱。** 没有看穿每个神经元；看到的是输入、输出、失败分类、外部裁决和证据链。
- **不是模型能力结论。** Qwen/Gemma 的对比只说明流程适配，不做能力排名。
- **不发布权重、不导出 GGUF、不合并 main。** PR 保持 draft，由 Milo 验收/merge。
- **对外禁说“准确 / 零幻觉 / 零骰子”。** 只说同一输入同一结果、可复现、可审计。

### 未决问题

1. `kind` 收紧还是扩 rubric？
2. verdict 最终归模型、归 policy，还是两列并存？
3. reward 用纯规则，还是规则 + 少量 RM？
4. 拒绝采样先做 4 条还是 8 条？
5. 蒸馏 teacher 用 Qwen3-8B 还是更大模型？
6. 约束解码用 `outlines` 还是 `sglang`？
7. RL 是否值得做，还是拒绝采样已够？
8. Lab 硬件按并发任务数、最大模型、用户/数据规模设计，先买可扩展单机还是直接上多卡？

---

## 附录 A · 证据索引

- `A5-INITIAL-TRAINING-STOCKTAKE.md` — A5 初步训练总盘点。
- `A5-ZERO-GPU-PATCH.md` — A5 零 GPU 口径修复。
- `evidence/qwen3-4b/base_prompt_v2_eval.json` — v2 云端原始输出。
- `evidence/qwen3-4b/base_prompt_v2_recompute.json` — v2 strict/policy/exact 本机复算。
- `evidence/a5-semantic-audit.json` / `.md` — 四源语义审计。
- `evidence/data-diff-a3-train.json` / `.md` — 训练集字段级 diff。
- `STAGE-02-MANIFEST.json` — 文件哈希与状态。

## 附录 B · 参考链接

- DeepSeek-V3 技术报告：<https://arxiv.org/abs/2412.19437>
- DeepSeek-R1 技术报告：<https://arxiv.org/abs/2501.12948>
- DeepSeekMath / GRPO：<https://arxiv.org/abs/2402.03300>
- DeepSeek-V3 仓库：<https://github.com/deepseek-ai/DeepSeek-V3>
- DeepSeek-R1 仓库：<https://github.com/deepseek-ai/DeepSeek-R1>
