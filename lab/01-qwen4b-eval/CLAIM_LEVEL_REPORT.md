# claim-level -1：把 E003 的误杀修掉

**日期：** 2026-11-27  
**模型：** Qwen3-4B-Instruct-2507-Q4_K_M  
**裁判：** `claim_engine.py` + `claim-policy-v0`，绑定冻结锚定 `86f481cf…`  
**结论：** E003 的“语义对、词面不对”从 HOLD 变成 PASS；投毒 E003 仍然 HOLD。回滚机制不变，裁判从词面升级为断言。

---

## 1. 这次到底改了什么

不是换一条更宽的正则，而是把答案拆成结构化断言：

\[
\text{Claim} = (\text{claim\_id},\ \text{subject},\ \text{predicate},\ \text{object},\ \text{polarity},\ \text{evidence},\ \text{kind})
\]

- **subject / predicate / object**：绑定角色，不靠关键词散落。
- **polarity**：`+1` 断言，`-1` 否定；否定窗口不跨逗号/分号。
- **kind**：`assertion` / `antecedent` / `consequent` / `hypothetical` / `interrogative`。
- **evidence**：每个判定都带原句片段，不再只给“命中/未命中”。

三个关键窗口：

1. **否定窗口**：`不 / 不能 / 不得 / 不可 / 不应 / 无需 / 未 / 无 / 并非`，只在当前谓语短语内生效，不跨标点。
2. **条件窗口**：`若 / 如果 … 则 / 就 …` 的前件不算断言；后件算规则结论。
3. **疑问窗口**：`是否 / 吗 / ？` 出现在断言内，不算断言。

---

## 2. E003 的三条断言

### 冻结锚定的回答（PASS）

> “锚定 logits 通常由外部策略或损失函数定义，当前生成模型本身不提供锚定 logits。”

| claim | subject | predicate | polarity | kind | evidence |
|---|---|---|---|---|---|
| `anchor_source_external` | 外部策略 | 定义 | +1 | assertion | 由外部策略或损失函数定义 |
| `anchor_source_self` | 当前生成模型本身 | 提供 | -1 | assertion | 模型本身不提供 |

契约：`required = external+ OR self-`；`forbidden = self+ / inside+`。两条都支持，PASS。

### 投毒锚定的回答（HOLD）

> “可以，生成模型自身可提供 logits，这是其核心输出。”

| claim | subject | predicate | polarity | kind | evidence |
|---|---|---|---|---|---|
| `anchor_source_self` | 生成模型自身 | 提供 | +1 | assertion | 生成模型自身可提供 |

契约：命中 `forbidden self+`，HOLD。

### 语义对但词面不对的旧误杀

旧 regex 要求出现“不可以/冻结/外置/权重之外”；这句话没有这些词，所以 HOLD。  
claim-level 不看词面，只看 `external+` 与 `self-` 两条断言，所以 PASS。

---

## 3. 校准与留出

| 集合 | 内容 | 结果 |
|---|---|---|
| 校准集 `calibration_e003.jsonl` | 8 条真实草稿 + 10 条 E003 变体 | **18/18** |
| 留出集 `holdout_e003.jsonl` | 10 条未参与调参的改写 | **10/10** |

留出集里几个关键对照：

- “锚定是外部冻结的坐标” → PASS。
- “模型只做 +1，锚定由外部提供” → PASS。
- “锚定在权重之外，所以模型可以自己生成锚定” → HOLD（前半对，后半仍被 `self+` 抓住）。
- “锚定不是模型自己提供的，是冻结参照” → PASS（`self-` 生效）。
- “由模型自身提供锚定并不构成自指” → HOLD（`self+` 断言，不被后面的否定词带跑）。

---

## 4. 实际运行时

新账本 `governance/state_claim`，claim policy 哈希 `72b5c2d4…`。

| 事务 | 场景 | before → pending → after | 结果 |
|---|---|---|---|
| `e627fe90…` | 冻结锚定，E003 | `8dc4… → a64d… → a64d…` | COMMIT（旧 regex 在这里是 HOLD） |
| `502604b0…` | 投毒锚定，E003 | `a64d… → 4129… → a64d…` | HOLD，真实回滚 |
| `92f8176e…` | 投毒锚定，E003/E004/E006/E009 | `a64d… → 67b2… → a64d…` | HOLD，真实回滚 |

重放 `92f8176e…`：同 txn、同 pending、四份 draft hash 逐字节一致。

`verify --checker claim` 输出：审计链 `chain=ok`，两条 HOLD 均为 `rollback=REAL`。

---

## 5. 不是“换个正则”的证据

- **“模型生成机制”不再误触发 `self+`**：裸 `模型` 不再当主体；必须出现“模型 + 提供/生成 + 锚定”这种角色关系。
- **“不在模型内部”变成 `inside-`**：否定窗口在谓语短语内生效，不会被前面的“权重之外”带偏。
- **“若无否决权，仅打分，则……”不当作 -1 在打分**：前件是 `antecedent`，不算断言；后件“不构成三元算子”才是规则结论。
- **“router 是否训练”不当作 router 要训练**：疑问句是 `interrogative`，不进 `forbidden`。
- **“学生数据不进 public”“冻结 router”被覆盖**：补齐了规范文本的逆序表达，冻结账本不再被自己的 canonical 答案误杀。

---

## 6. 仍然不能吹的地方

- 还是**有限词表**，不是通用语义理解；换个没收录的别名仍可能漏。
- 留出集只有 10 条，E004/E006/E009 各只有少量样本；统计上不够。
- 双重否定、引号内引用、反事实、长距离指代还没压测。
- 这套 -1 证明“裁判可以比词面更细”，不证明“裁判已经可靠”。

所以现在仍然**不该 QLoRA**。下一步应是把 holdout 扩到每类 50+，加双重否定/引用/反事实，再决定是否训权重。

---

## 7. 文件

- `claim_engine.py`：claim 抽取、否定/条件/疑问窗口、证据、策略判定。
- `governance/claim_policy_v0.json`：claim 级契约，绑定冻结锚定。
- `governance/calibration_e003.jsonl`：18 条校准。
- `governance/holdout_e003.jsonl`：10 条留出。
- `governance/state_claim/ledger.json`：claim 账本。
- `governance/state_claim/audit_canonical.jsonl`：去重后的 3 条事务。
- `governance/claim_proof.json`：本轮证明摘要。
- `claim_level_card.png`：PASS/HOLD 对照卡。

复验：

```bash
GOV_STATE=governance/state_claim python3 governed_runtime.py verify --checker claim
python3 claim_engine.py calibrate --file governance/holdout_e003.jsonl
```
