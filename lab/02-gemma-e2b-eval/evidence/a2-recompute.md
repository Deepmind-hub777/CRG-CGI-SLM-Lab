# A2 · 四个 eval 产物的统一 rubric 重算

**口径：** `rubric_v1.json`；只解析落盘输出，不加载模型、不改权重。旧文件里已有的 `model_verdict` 单独列为“记录值”，避免把“raw 输出契约失败”误读成“模型判错”。

| 产物 | prompt | 结构 | 严格 schema | 宽松 schema | 核心三元组 | raw verdict | 记录 verdict | HOLD recall | always-PASS | claim set | 失败分类 |
|---|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---|
| `base_old_384` | old: 384 tokens | 0/10 | 0/10 | 0/10 | 0/10 | 0.00 | 0.40 | 0/4 | 0.60 | — | `{"fence": 10, "bad_json": 20}` |
| `adapter_old_384` | old: 384 tokens | 0/10 | 0/10 | 0/10 | 0/10 | 0.00 | 0.00 | 0/4 | 0.60 | — | `{"truncated": 3, "bad_json": 3, "missing_verdict": 7, "bad_polarity": 9, "bad_kind": 6, "dupkey": 4, "missing_field": 9}` |
| `base_new_prompt` | new: 768 / rep 1.05 / fence-stop | 8/10 | 0/10 | 7/10 | 8/10 | 0.50 | 0.50 | 0/4 | 0.60 | — | `{"bad_polarity": 12, "bad_kind": 12, "missing_verdict": 1, "trailing": 1}` |
| `adapter_new_prompt` | new: 768 / rep 1.05 / fence-stop | 8/10 | 0/10 | 0/10 | 8/10 | 0.50 | 0.50 | 0/4 | 0.60 | — | `{"missing_field": 24, "bad_polarity": 13, "bad_kind": 11, "truncated": 2, "bad_json": 2}` |

## 读法

- **旧 base / 旧 adapter 的 raw 结构都是 0/10。** 旧 base 的 0.4 是文件里已经记录的 `model_verdict`，不是本次从 raw 输出重算出来的；严格 rubric 下它连围栏和单对象根都没过。
- **新 prompt 把结构拉到 8/10，但严格 schema 仍是 0/10。** base 主要是 `positive/negative`、`fact/restriction` 别名；adapter 是 `missing_field`、`polarity`、`kind` 与 2 条截断。
- **HOLD recall 四个产物全是 0/4。** 这不是 prompt 或 rubric 能救的；它是当前权重与数据共同造成的模型侧缺口。
- **claim set 在严格 schema 下没有可计算样本。** 只有“结构 + schema”都合格的行才进入精确匹配；现在没有行达到该门槛，所以不把 `claim_set_exact` 写成能力分数。
- **always-PASS 基线恒为 0.6。** 任何 verdict 指标都必须和这个 0.6 一起读；0.5 低于基线，不能叫“判对”。
