# lab/00 · 合成 logits 的 smoke test

**状态：** working（本地已跑通）
**主张标签：** `[D]` 工程验证
**最后更新：** 2026-11-26

---

## 这是什么

一个**不加载模型**的数学单测：用 6 个 token 的玩具分布，验证 `SPEC/01` 的三元采样器公式是否成立。

它不做的事：

- 不证明模型有效；
- 不证明端侧能跑；
- 不证明 QLoRA 有提升。

它只回答一个问题：

> **采样器的数学有没有写错？**

---

## 跑法

```bash
python3 lab/00-smoke-test/test_sampler.py
```

无依赖（只用标准库）。CI 也会跑这一条。

---

## 检查项

| 检查 | 含义 |
|---|---|
| `beta=0,gamma=0` 是 no-op | 采样器不能偷偷改基线 |
| 锚定拉力 | `beta>0` 时，锚定 token 的质量上升 |
| 熵下限 | 锚定不能把分布压成复读机 |
| 发散惩罚 | `gamma>0` 时，锚定外质量下降 |
| 自锚定只变尖 | 模型自己当锚定，只能锐化，不能产生新原点 |
| `top_k_hash` | 同输入同构建的可复现指纹 |

---

## 当前结果

```text
baseline entropy = 1.3781
anchor entropy   = 0.9664
baseline anchor mass = 0.7133

[PASS] zero-order baseline is a no-op
[PASS] anchor pull: mass 0.7133 -> 0.9507
[PASS] entropy floor: 0.7485 >= 0.6
[PASS] divergence penalty: off-anchor mass 0.0493 -> 0.0430
[PASS] self-anchor only sharpens; it cannot create a new origin (H 1.3781 -> 0.8913)
[PASS] top_k_hash = 25601179049b2669

ALL CHECKS PASSED
```

---

## 下一步

1. 把同一组公式接到 `llama-cpp-python` 的 `LogitsProcessor`，用真实模型跑 10 条 `eval/cases/seed.jsonl`。
2. 记录 `beta=0` 基线；没有基线，不算提升。
3. 如果熵塌，先写 `FAIL-###`，再调参。

---

## 不做什么

- 不把 toy 结果写成“模型有效”。
- 不用这个测试替代 G1/G2/G3。
- 不在这个目录里放模型权重或学生数据。
