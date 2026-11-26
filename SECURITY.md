# SECURITY · 公开仓库的安全边界

**状态：** draft
**最后更新：** 2026-11-26

---

## 1. 报告问题

- 不要在公开 issue 里贴密钥、学生数据、可利用细节。
- 私下联系 0 轴（Milo），或在 GitHub 使用 private security advisory。
- 24 小时内确认收到；7 天内给处置计划（尽力而为，不承诺 SLA）。

---

## 2. 绝不进仓库

| 类型 | 例子 | 处置 |
|---|---|---|
| 个人信息 | 学生姓名、家长电话、成绩、作品 | 立即删除 + 轮换相关访问 |
| 学校数据 | 合同、报价、排课、教师评价 | 立即删除；检查 fork/缓存 |
| 密钥 | API key、PAT、cookie、私钥 | **轮换**；删文件不够 |
| 受限权重 | 不允许再分发的模型/语料 | 删除；改用下载脚本 |
| 内部链接 | 未公开的飞书/云盘链接 | 删除；改为公开说明 |

> 一旦推上 public，fork、缓存、镜像都可能留存。**删 commit 不等于回收。**

---

## 3. 提交前扫描

```bash
# 常见密钥模式
git diff --cached | grep -Ei \
  "api[_-]?key|secret|token|password|passwd|BEGIN.*PRIVATE|ghp_|sk-|AKIA"
```

建议启用：

- GitHub Secret Scanning（public repo 默认开启）。
- pre-commit hook（gitleaks / detect-secrets）。
- CI 里跑一次 `gitleaks detect`。

---

## 4. 依赖与构建

- 固定版本；不使用 `latest` 作为唯一约束。
- 构建脚本不执行远程未校验脚本（`curl | bash` 禁止）。
- 下载模型/数据时校验 SHA256。
- 不在 CI 里存长期 token；用最小权限的 short-lived token。

---

## 5. 模型与数据

- 模型权重不进仓库；用下载脚本 + 哈希 + license 说明。
- 数据集：合成/脱敏优先；真实数据放 private，不进 public。
- 任何“学生轨迹”必须脱敏：去掉姓名、学校、班级、时间、设备指纹。
- 遵守底座模型 license（Gemma / Qwen / LFM 各有条款）。

---

## 6. 公开仓库的“不可逆”提醒

- 公开前先列“不能公开”的清单。
- 公开后假设全世界已缓存；不要依赖“以后删掉”。
- 如果要放敏感内容，先开 private 仓库，再决定是否迁移。

---

## 7. 一句话

**公开的代价是不可逆；安全的底线是不可绕。**
