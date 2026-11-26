---
name: moe-qlora
status: draft
owner: Doubao
claim: "[D] proposal"
last_verified: never
---

# moe-qlora

## 什么时候用

- 要把“回到原点”的行为，训进权重（+1/-1），但 **不** 把 0 训进去。
- 要在 MoE 模型上做轻量后训练：冻结 router，只打 attention + expert up/down。
- 要导出 GGUF，回手机端侧。

## 不什么时候用

- 想靠 QLoRA 让模型“变成”绝对正确（不可能）。
- 想把 0 写进 adapter（禁止；0 必须外置）。
- 想让同一个 adapter 既生成又校验（禁止；-1 必须独立）。

## 训练顺序

1. **先 Qwen3-4B dense。** 管线跑通：数据、训练、导出、端侧加载、G0/G1。
2. **再 LFM2.5 8B-A1B MoE。** 冻结 router；只打 attention + expert up/down。
3. **最后才考虑架构改动**（ternary head/gate）；先有观察期，不先改结构。

## 数据

- 50–100 条已验证轨迹起步；每条带来源、许可、哈希。
- 不是教师原话；是“经过 -1 校验的轨迹”。
- 正例：模型回到原点、承认不确定、给出可核验步骤。
- 负例：讨好、刚愎、无支撑主张、把 0 当中间值。
- 不含学生数据；不含未脱敏教师轨迹。

**格式建议：**

```json
{
  "id": "...",
  "prompt": "...",
  "response_good": "...",
  "response_bad": "...",
  "anchor_refs": ["anchor-v0#..."],
  "why": "哪一句回到原点，哪一句漂了",
  "claim": "[C]"
}
```

## QLoRA 配置（起点，不是定论）

| 项 | 起点 |
|---|---|
| 量化 | 4-bit（nf4 / q4） |
| LoRA rank | 16–64 |
| LoRA alpha | 16–32 |
| dropout | 0.05 |
| lr | 1e-4 – 2e-4 |
| epochs | 1–3 |
| seq len | 2048–4096（按显存） |
| target | attention q/k/v/o + expert up/down |
| **router** | **冻结，不训练** |

> MoE 的 router 不是常规 LoRA target。不要因为“想让它学会路由”而训练 router；那会把路由分布一起漂掉。

## 0 怎么外置

- 训练数据里可以出现“锚定文本”，但**不要把锚定 embedding 加进 optimizer**。
- 训练目标：让模型在无锚定时也更容易“回到原点”；不是让模型背下锚定。
- 评测时仍然外置锚定；训练/评测条件要一致。

## 导出

1. 合并 adapter（如果工具支持）；或保留 adapter。
2. 转 GGUF；量化 Q4_K_M（端侧起点）。
3. 记录：
   - base model hash
   - adapter hash
   - GGUF hash
   - 转换命令
4. 手机加载；跑 `eval/cases/seed.jsonl`；过 G1/G3。

## 坑

| 坑 | 现象 | 处理 |
|---|---|---|
| 训练 router | 路由漂移，能力崩 | 冻结；只打 attention + expert |
| 数据太少 | 过拟合、复读 | 先 50–100 条，重质量不重数量 |
| 教师原话直接蒸馏 | 把讨好/幻觉一起学 | 只用验证过的轨迹 |
| 0 进 adapter | 原点漂移 | 0 外置；训练目标只到“回到” |
| 合并后掉点 | 合并方式/精度问题 | 保留 adapter；对比合并前后 |
| 只跑训练集 | 假通过 | held-out + 固定探针 |

## 验收

- G0 数据门通过。
- G1 生成门通过：比纯提示词基线好，熵不塌。
- 导出 GGUF 在手机上能加载。
- 有回滚：adapter / GGUF 可切回上一版。
- 没跑过的配置，标 `[B]`；不要写“已验证”。
