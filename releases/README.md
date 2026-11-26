# releases · 可复现的发布

**状态：** draft
**最后更新：** 2026-11-26

---

## 这里放什么

- `releases/<version>/MANIFEST.md`：commit、模型哈希、锚定哈希、gate 签字。
- `releases/<version>/CHECKSUMS.txt`：所有产物的 SHA256。
- 补丁/脚本：能复现构建，但不放权重。

**不放：**

- 模型权重、GGUF、adapter 大文件。
- 学生数据、密钥、受限语料。

## MANIFEST 模板

```markdown
# Release v0.x.y

- 日期：
- commit：
- 模型：
- 模型 hash：
- 量化：
- anchor id：
- anchor hash：
- 设备：

## Gates

| Gate | 结果 | 证据 | 签字 |
|---|---|---|---|
| G0 | pass/fail/not_run | ... | 豆包 / Milo |
| G1 |  |  |  |
| G2 |  |  |  |
| G3 |  |  |  |

## 已知限制

- ...

## 回滚

1. ...
2. ...
实测回滚时间：...

## 复现

```bash
# commands
```
```

## 纪律

- 没有 gate 签字，不发版。
- 没有 CHECKSUMS，不复现。
- 没有回滚步骤，不上手机。
- 发布说明只写可审计事实；不写“准确”“零幻觉”。
