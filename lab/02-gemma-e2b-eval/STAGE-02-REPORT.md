# STAGE-02 · 从链路验证到运行时治理灰箱

**状态：** 离线契约审计完成；模型 gate 仍未通过；未启动正式 run，未补数据，未发布权重。  
**日期：** 2026-11-27（Asia/Bangkok，UTC+7）  
**范围：** 只做 rubric、契约分层、灰箱定位与治理边界；不改 base 权重，不把 adapter 当底座能力。  
**主张标签：** 工程与实测记录 `[D]`；模型能力数字 `[C]`；治理架构判断 `[B]`，需跨模型实证后才能升级。

---

## 0. 一句话

链路验证证明“**能跑**”；阶段 02 证明“**能判、能定位、能分层**”。这不是模型变白箱，而是**链路从黑箱变灰箱**。

更准确地说：

> **治理架构与底座模型无关；这批数值与模型能力结论仍绑定 Gemma 4 E2B。**

---

## 1. 这次新增了什么

- `rubric_v1.json`：冻结结构、schema、完整三元组、诊断口径。
- `contract_eval.py`：直接解析云端原始报告，0 GPU 重算；支持 `eval.json` 与 Markdown 报告两种输入。
- `test_contract_eval.py`：4 个最小单测，覆盖好输出、围栏、别名、空三元组。
- `evidence/contract-eval-v1.md` / `.json`：统一 rubric 的逐行结果。
- 阶段 01 报告与 `NEXT-ACTIONS.md` 已按审计结果修正：target/gold 其实同源，真正问题是 claim 三元组字段为空 + 模型输出不匹配。

---

## 2. 结果：把“尺子”和“模型”拆开

| 口径 | base | adapter | 说明 |
|---|---:|---:|---|
| 结构合格 | 8/10 | 8/10 | 单对象、无围栏、顶层 verdict、claims 数组 |
| 核心三元组非空（诊断） | 8/10 | 8/10 | 只看 claim_id/subject/predicate/object；不看 polarity/kind/evidence |
| 宽松 schema（诊断） | **7/10** | **0/10** | 接受 positive/negative、fact/restriction 别名；仍拒绝 polarity 0、kind PASS |
| 严格 schema | **0/10** | **0/10** | target 的 `±1` + 枚举 + 字段齐全 |
| 完整三元组（严格） | **0/10** | **0/10** | 严格 schema + 非空 evidence |
| HOLD recall | 0/4 | 0/4 | 4 条 HOLD 全漏 |
| verdict 准确率 | 0.5 | 0.5 | always-PASS 基线是 0.6 |
| claim set 精确率 | 无法计算 | 无法计算 | 没有“结构 + schema”都合格的输出 |

四个判断：

1. **base 的严格 0/10 主要是 harness 严格度。** 它用 `"positive"` / `"negative"` 和 `fact` / `restriction`；放宽别名后是 7/10。不能把这个 0 写成“模型语义能力 0”。
2. **adapter 的 0/10 不能全推给 harness。** 即使放宽别名仍是 0/10：`polarity:0`、`kind:"PASS"`、缺 `polarity/kind/evidence`，另有 2 条截断。这里有 prompt 没把枚举说死的责任，但输出确实不合契约。
3. **核心三元组两边都是 8/10。** “完整三元组 0/10”是严格 schema 合并后的结果，不等于“三元组全空”。内容层不是主因，契约字段和 HOLD 才是。
4. **HOLD 0/4、0.5 < 0.6 是真实模型问题。** 这部分换 rubric 救不了，是数据分布和训练目标的问题。

---

## 3. “跟底座模型无关”能说到什么程度

**可以明确：治理架构是底座无关的；这批结果不是。**

| 层 | 是否与底座无关 | 这次证据 |
|---|---|---|
| 角色分离：`+1` 生发 / `-1` 否决 / `0` 锚定 | 设计上无关 | 已在 E2B 上跑通 |
| 外部 veto、冻结 rubric、同输入复算、hash、人工 merge | 设计上无关 | 已有雏形 |
| adapter、prompt、具体分数、HOLD 表现 | 与底座/数据绑定 | 只在 Gemma 4 E2B 上测得 |
| 跨模型可移植性 | 尚未实证 | 还没有第二个底座跑同一套契约 |

所以准确表述是：

> **治理层是 model-agnostic 的架构；阶段 02 的证据是 model-specific 的。**

不能写成“换任何底座都得到同样结果”。要证明跨模型可移植，至少要用同一套 rubric、同一批 gold、同一套 veto，在第二个底座上跑一次，并按底座分别报告；不能把两个底座的分数平均成一个“治理分”。

---

## 4. Ring 0 的边界

这次是 **Ring 0 的前庭/影子**，不是已经到 Ring 0。

| Ring 0 条件 | 当前状态 | 缺口 |
|---|---|---|
| `0` 不进权重，锚定在模型之外 | 有雏形；target 不含锚定原文 | `0` 的 canonical 定义、泄漏审计还没冻结 |
| `-1` 独立，能否决/回滚 | `claim_engine.py` 外置裁决 | 冲突优先级、回滚证据链、人工复核接口还没制度化 |
| `+1` 只在契约内生成 | prompt + claim schema | 还没有 runtime 结构化约束；目前是事后判 |
| 同一输入同一结果，可复算 | manifest/hash + `contract_eval` | gold 未冻结、`finish_reason` 未记录、全链路签名未做 |
| 最终裁决层 | PR draft + 人工 merge | Ring 0 由谁持有、如何授权，仍需明确 |

一句话：**模型层可以换，过程层可以回滚，治理层必须稳定；现在稳定的是 rubric 和外部 veto 的方向，不是完整的 Ring 0。**

---

## 5. 留出的问题

1. **Ring 0 的最终裁决权归谁？** 人工 root、外部 `claim_engine`、还是两者分层？ veto 冲突时谁优先？
2. **`0` 的 canonical 定义是什么？** 锚定如何做到“不进权重、不泄漏进 target、又能被审计”？
3. **`-1` 的否决如何制度化？** 只判 PASS/HOLD 够不够？要不要记录回滚对象、回滚证据、失败原因？
4. **`+1` 的契约如何运行时强制？** 继续靠 prompt，还是上结构化解码/语法约束？后者会不会把模型能力压成模板？
5. **claim 三元组如何 canonical 化？** `predicate/object` 空字段是补抽取规则，还是在 `build_data` 写显式 triple？两者都会改变 target 语义，需要先定。
6. **gold 如何冻结？** `holdout.jsonl` 补 `gold_claims` 后，谁来签收？是否允许后续改 gold？
7. **harness 严格度如何披露？** 本次已证明 strict 0/10 与 lenient 7/10 可以同时成立；以后必须同时报告，不许只报一个总分。
8. **跨模型可移植性怎么测？** 第二底座选谁、预算怎么控制、是否只用 10 条 holdout 做契约对照？
9. **runtime monitor 要不要上？** 现在只有离线复算；在线漂移、异常输出、越权 claim 的告警还没有。
10. **人类 merge 是否就是 Ring 0 的物理锚？** 如果是，PR 规则、签名、审计日志要跟上来。

---

## 6. 未来建议

- **先冻结一份 `CRG-RUNTIME-CONTRACT-v1`：** 角色、优先级、证据、回滚、签名、人工复核，一页说清；不要继续用散落的 prompt 当宪法。
- **把契约评测进 CI：** 每次 adapter 或 prompt 变更，固定跑 `test_candidates.py`、`test_contract_eval.py`、`contract_eval.py`；不合格 fail closed。
- **加负对照：** always-PASS、随机输出、base、adapter 四条基线同表；没有负对照，不报“提升”。
- **加可复现字段：** `temperature=0`、`seed`、`max_new_tokens`、`finish_reason`、token 数、耗时；否则截断和尾部问题无法归因。
- **gold 冻结 + 双签：** `gold_claims` 落盘、hash、人工签收；后续改动必须新版本，不覆盖旧 gold。
- **做一次跨底座契约对照：** 同一 rubric、同一 gold、同一 veto，换一个底座；只报“契约是否可移植”，不报“模型谁更强”。
- **保留人工 root：** 自动化可以判契约，不能替代最终 merge；Ring 0 的物理锚仍然是人。

---

## 7. 不要写成什么

- 不要写“模型准确 / 零幻觉 / 超越某模型”。
- 不要写“治理层已经 model-agnostic 地被实证”。
- 不要写“已经达到 Ring 0”。
- 不要写“模型已经变白箱”。
- 不要只报 strict 0/10 或 lenient 7/10 其中一个；两个口径必须同时在场。

可以写的只有：

> 同一输入同一结果；可复现、可审计、可回滚；治理架构与底座可分离；这批证据绑定 Gemma 4 E2B。

---

## 8. 证据入口

- `rubric_v1.json` — 冻结 rubric。
- `contract_eval.py` — 统一重算器。
- `test_contract_eval.py` — 4/4 单测。
- `evidence/contract-eval-v1.md` — 分层结果摘要。
- `evidence/contract-eval-v1.json` — 逐行结果。
- `evidence/e2b-contract-eval-report.md` — 云端原始报告，只读。
- `STAGE-01-REPORT.md` — 阶段 01 链路验证与契约复盘。
- `NEXT-ACTIONS.md` — 阶段 02 修复清单与验收门槛。
- `STAGE-02-MANIFEST.json` — 本阶段状态与文件哈希。

---

## 9. A3 落地记录（离线，不训练）

A3 已完成离线部分，模型分数没有在新数据上重跑；这是“先修尺子”的第一步，不是新的模型结论。

- `claim_engine.py`：`CLAIM_META` 作为 canonical schema 填充；补了 `router_freeze`；evidence 仍取草稿原句。
- `train.jsonl`：70 条 claims 的空 `object` / `predicate` 均为 **0/70**（修复前为 60/70 与 24/70）。
- `holdout.jsonl`：11 条 `gold_claims`，空字段 **0/11**（修复前 11/11 为空）。
- `eval_e2b.py`：优先读冻结 `gold_claims`，不再每次现场重抽。
- 新哈希：`train=54fd202c4df00c635ab0086acf01493ecbdaed10f95624eec1655e2165994492`；`holdout=87d2fb1b0b85203fc34d55e37642acd063ba5ad356941e4067bb83b8f37846e3`；`data/manifest=82e23714310a07b3add247ddc8251d992542db01bb1c99c1eb6fbf53187f5836`。
- 校验：`test_candidates.py` 0 FAIL；`test_data_contract.py` 通过；`test_contract_eval.py` 4/4。审计快照见 `evidence/a3-freeze-audit.json`。
- 未做：A2 的四个旧 `eval.json` 重算、Qwen base 契约基线、Qwen 50 条 QLoRA。

---

## 10. 记录声明

- 本文只记录已发生的事实与已复算的数字；未跨模型复现的判断标 `[B]`。
- 不把“治理架构可分离”写成“治理效果已跨模型验证”。
- 不把“灰箱定位”写成“白箱理解”。
- 本阶段结论：**链路从黑箱进灰箱；治理层方向成立；Ring 0 尚未到达；模型 gate 仍未通过。**
