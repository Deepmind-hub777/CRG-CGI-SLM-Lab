---
name: ternary-decoding
status: draft
owner: Doubao
claim: "[D] proposal"
last_verified: never
---

# ternary-decoding

## 什么时候用

- 要在解码层加入 +1/-1/0，而不是只改 prompt。
- 要在不重训模型的前提下，先验证“锚定是否真的有用”。
- 要做一个可回滚的端侧实验。

## 不什么时候用

- 还没定义 0 的锚定对象（先读 `SPEC/02-anchor.md`）。
- 想让同一个模型“自我批评”当 -1（这不算）。
- 想用三值量化冒充三元算子（这不算）。

## 输入

| 输入 | 说明 |
|---|---|
| `model` | 本地 SLM（Qwen3-4B / LFM2.5 8B-A1B） |
| `anchor` | 冻结锚定：嵌入索引 / 参考模型 / 规范规则 |
| `beta` | 锚定强度，初值 0.0（先跑基线） |
| `gamma` | 收敛强度，初值 0.0 |
| `H_th` | 熵门控阈值；先按基线分位校准 |
| `T` | 温度；不改语义 |

## 步骤

1. **先跑基线。** `beta=0, gamma=0`，记录 `top_k_hash`、熵、延迟。
2. **只开锚定。** `beta=0.3–0.8`，`gamma=0`；看锚定一致率是否上升、熵是否塌。
3. **只开收敛。** `beta=0`，`gamma=0.1–0.5`；看无支撑主张是否下降、误报是否上升。
4. **双开。** 先小 `beta` + 小 `gamma`；每次只改一个变量。
5. **熵门控。** 只在高熵 token 调用锚定；记录调用比例与延迟。
6. **写 trace。** 每条样本记录 `anchor_id/hash`、`beta`、`gamma`、`H`、`KL`、`top_k_hash`。
7. **过 G1。** 没过就写 `FAIL-###`，不要“再调一下看看”。

## 输出契约

```json
{
  "run_id": "...",
  "commit": "...",
  "model_hash": "...",
  "anchor_id": "anchor-v0",
  "anchor_hash": "sha256:...",
  "beta": 0.6,
  "gamma": 0.3,
  "H_th": 1.5,
  "entropy": 1.42,
  "kl_to_anchor": 0.18,
  "top_k_hash": "...",
  "latency_ms": {"p50": 0, "p95": 0},
  "gate": "G1",
  "claim": "[C]"
}
```

## 伪代码

```python
def ternary_logits(base_logits, anchor_logits, beta, gamma, p, q):
    # p = softmax(base_logits), q = softmax(anchor_logits)
    d = [max(0.0, pi - qi) for pi, qi in zip(p, q)]
    return [b + beta * a - gamma * di
            for b, a, di in zip(base_logits, anchor_logits, d)]
```

## 坑

| 坑 | 现象 | 处理 |
|---|---|---|
| 锚定自指 | 越锚越自信，错得更稳 | 锚定必须来自冻结参照 |
| `beta` 太大 | 熵塌、复读 | 降 `beta`；加熵下限 |
| `gamma` 太大 | 句子断裂、过度保守 | 降 `gamma`；只惩罚正发散 |
| 逐 token 双模型 | 延迟爆炸、发热 | 熵门控；只在不确定时锚定 |
| 锚定太窄 | 只认术语，不会推理 | 锚定 + 规则分层；别把锚定当知识库 |
| 没有基线 | 不知道有没有用 | 先跑 `beta=0,gamma=0` |

## 验收

- `lab/00-smoke-test/test_sampler.py` 通过。
- `eval/cases/seed.jsonl` 全跑；有 `top_k_hash`。
- G1 通过，或写 `FAIL-###`。
- 能一键回滚到 `beta=0,gamma=0`。
