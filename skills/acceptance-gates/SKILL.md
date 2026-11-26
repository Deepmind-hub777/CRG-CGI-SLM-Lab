---
name: acceptance-gates
status: draft
owner: Doubao
claim: "[D] proposal"
last_verified: never
---

# acceptance-gates

## 什么时候用

- 任何“要发布 / 要上手机 / 要给学生用”的版本。
- 任何声称“三元采样有效 / QLoRA 有提升 / 锚定稳住了”的 PR。
- 任何 gate 失败后的复盘。

## 原则

> 一个 gate 是一张签了字的清单 + 一组 artifact，不是“我觉得可以了”。

- 没有 artifact，不算过。
- 没有基线，不算提升。
- 没有 `top_k_hash`，不算可复现。
- 没有回滚，不算可发布。

---

## G0 · 数据门

- [ ] 50–100 条已验证轨迹；有来源、许可、哈希。
- [ ] 双人标注一致率 > 0.70；分歧条目保留。
- [ ] 不含学生数据 / 未脱敏教师轨迹。
- [ ] 正例/负例都有；负例不是“胡编”，是“漂移”。
- [ ] 数据格式符合 `eval/README.md`。

**证据：** `eval/data-manifest.json` + 标注记录。
**签字：** 豆包（证据）/ Milo（批准）。

---

## G1 · 生成门

- [ ] 有 `beta=0,gamma=0` 基线。
- [ ] `AC` 相对基线提升。
- [ ] `H` 不低于 `H_min`；没有靠压扁分布换一致率。
- [ ] held-out 小集无严重回归。
- [ ] 记录 `top_k_hash`、`anchor_hash`、`beta`、`gamma`。

**证据：** `eval/report-G1.json` + 原始日志。
**签字：** 豆包（证据）/ Milo（批准）。

---

## G2 · 校验门

- [ ] `UCR` 下降。
- [ ] 误报率 < 10%。
- [ ] 校验器与生成器不是同一个 adapter；有独立版本/哈希。
- [ ] 抽 20 条失败案例，人工复核。
- [ ] 校验器能“否决并回滚”，不只是打分。

**证据：** 混淆矩阵 + 20 条案例 + 校验器哈希。
**签字：** 豆包（证据）/ Milo（批准）。

---

## G3 · 端侧门

- [ ] 真机跑过（一加十二），不是模拟器。
- [ ] p95 延迟在目标内（目标先测基线再定）。
- [ ] 30 分钟温控曲线；无断崖降频。
- [ ] 24 小时 soak；无内存泄漏/崩溃。
- [ ] 飞行模式可跑。
- [ ] 一键回滚；实测回滚时间。

**证据：** `lab/android-*/results/` + 温控/续航截图 + 回滚录屏。
**签字：** 豆包（证据）/ Milo（批准）。

---

## 证据包结构

```text
eval/evidence/<version>/
├── manifest.json          # commit, model_hash, anchor_hash, gates
├── G0-data.json
├── G1-generation.json
├── G2-verification.json
├── G3-device.json
├── logs/
└── README.md              # 怎么复跑
```

`manifest.json` 至少：

```json
{
  "version": "v0.1.0",
  "commit": "...",
  "model_hash": "...",
  "anchor_hash": "...",
  "gates": {
    "G0": "pass",
    "G1": "pass",
    "G2": "fail",
    "G3": "not_run"
  },
  "known_limitations": ["..."],
  "rollback": "..."
}
```

---

## 失败处理

1. 先写 `FAIL-###`。
2. 标“失败模式”：漂移 / 塌缩 / 误报 / 漏报 / 延迟 / 热 / 装置。
3. 写根因（具体机制，不是“模型不行”）。
4. 写“下一个最小实验”。
5. 再改代码。

**没有 FAIL 记录的重试，视为无效重试。**

---

## 发布签字

| Gate | 证据签字 | 批准 | 日期 |
|---|---|---|---|
| G0 | 豆包 | Milo |  |
| G1 | 豆包 | Milo |  |
| G2 | 豆包 | Milo |  |
| G3 | 豆包 | Milo |  |

> Grok 可提供“构建可复现”签字；不能替代 Milo 的批准。
