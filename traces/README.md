# traces · 合成 / 脱敏轨迹

**状态：** draft
**最后更新：** 2026-11-26

---

## 这里放什么

- 合成轨迹：用来做 G0/G1 的公开样例。
- 脱敏轨迹：去掉姓名、学校、班级、时间、设备指纹，只剩“输入 → 输出 → 校验”。
- 失败轨迹：明确标 `fail`，不美化。

**不放：**

- 真实学生原文、家长信息、学校合同。
- 可反推到个人的元数据。
- 教师的未公开原始记录。

## 建议字段

```json
{
  "trace_id": "...",
  "source": "synthetic / redacted",
  "prompt": "...",
  "response": "...",
  "anchor_id": "anchor-v0",
  "anchor_hash": "sha256:...",
  "beta": 0.6,
  "gamma": 0.3,
  "entropy": 1.42,
  "top_k_hash": "...",
  "verdict": "pass / fail / unsure",
  "failure_mode": "drift / collapse / false_positive / ...",
  "gate": "G1",
  "claim": "[C]"
}
```

## 纪律

- 没有 `anchor_hash` 的轨迹，不能用于 eval。
- 没有 `verdict` 的轨迹，只是聊天记录。
- 脱敏要彻底；不要只改名字。
- 真实轨迹放 private；public 只放合成/脱敏。
