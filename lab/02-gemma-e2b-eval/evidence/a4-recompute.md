# A4: Qwen3-4B 契约基线 + 50 条 QLoRA（离线复算）

统一 `rubric_v1`；模型输出未重跑，只按 A3 冻结 gold 重算。

| 产物 | 结构 | 严格 schema | 宽松 schema | 核心三元组 | verdict | always-PASS | always-HOLD | HOLD recall | PASS recall | claim set |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen_base | 10/10 | 0/10 | 2/10 | 9/10 | 0.2 | 0.6 | 0.4 | 0.5 | 0.0 | None |
| qwen_adapter_50 | 10/10 | 5/10 | 5/10 | 8/10 | 0.3 | 0.6 | 0.4 | 0.75 | 0.0 | 0.0 |

## 失败分布

- **qwen_base**：{"bad_polarity": 15, "bad_kind": 14}
- **qwen_adapter_50**：{"missing_field": 4, "bad_polarity": 4}

## 读法

- `contract_ok_rate=1.0` 是云端弱门：只查单对象根、`verdict` 与 `claims` 列表，不查 claim 字段、polarity、kind。
- 严格 schema 下 base 0/10、adapter 5/10；宽松 schema base 2/10、adapter 5/10。
- base 与 adapter 都低于 always-PASS 0.60；adapter 0.30 也低于 always-HOLD 0.40。
- adapter 在 6 条 PASS 上全部输出 HOLD；HOLD recall 0.75 不能当总体能力。
- claim set 在严格合格样本上：base 不可计算（0 条合格），adapter 0.0；本机 raw 计数 base 0.0、adapter 0.0。
- 云端 summary 的 `claim_set_exact_rate` 是旧 gold/engine 口径：base 0.1、adapter 0.0；不与本机 strict 复算混用。
- 主要缺口不是 JSON 语法，而是 (a) PASS/HOLD 语义未在 prompt 定义；(b) claim_id 词表未给模型；(c) 云端 contract gate 过弱。

## 参数量核对

- `model.safetensors.index.json` 的 `total_size=8,045,591,552` bytes；按 bf16 每参数 2 bytes 估算约 **4.023B** 参数。
- `trainable=33,030,144`，真实占比 **0.821%**；manifest 里的 `2.238B / 1.475%` 是 4-bit 加载后的 `numel()` 伪影，不用作分母。
- 细表：`evidence/qwen3-4b/param_check.json`。
