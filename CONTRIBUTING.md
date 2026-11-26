# CONTRIBUTING · 怎么往这个场里放东西

**状态：** draft
**最后更新：** 2026-11-26

---

## 1. 先问：这是哪一类变更？

| 类型 | 去哪 | 例子 |
|---|---|---|
| 修错字/链接 | 直接 PR | README 错别字 |
| 改 SPEC 口径 | issue → RFC → PR | 改 0 的定义、改 gate 阈值 |
| 加 skill | `skills/<name>/SKILL.md` + PR | 新的端侧实验方法 |
| 加实验 | `lab/<id>-<slug>/` + PR | QLoRA 消融 |
| 加评测 | `eval/` + PR | 新探针、新 rubric |
| 学生提案 | `proposals/` + PR | 新想法、新实验设计 |
| 失败 | `FAILURES.md` + PR | 实验失败、假设被推翻 |

**不确定就先开 issue，不要先写代码。**

---

## 2. 提案格式（RFC）

文件名：`proposals/rfc/RFC-000x-<slug>.md`

```markdown
# RFC-000x: <title>

- 作者：
- 日期：
- 状态：draft / accepted / rejected / superseded
- 主张标签：`[B]` / `[C]` / `[D]`

## 1. 现状
## 2. 问题
## 3. 提案
## 4. 影响
- 影响哪些 SPEC：
- 影响哪些 skill：
- 影响哪些 gate：
## 5. 回滚
## 6. 需要重跑的 eval
## 7. 未决
```

**0 的变更必须走 RFC；代码 PR 不能顺手改 0。**

---

## 3. PR 检查清单

复制 `.github/PULL_REQUEST_TEMPLATE.md`，逐条填。

最低要求：

- [ ] 一句话说明改了什么
- [ ] 标了主张标签
- [ ] 给了 artifact（日志/哈希/eval）
- [ ] 说明 gate 影响
- [ ] 说明回滚
- [ ] 确认无学生数据、无密钥、无受限权重
- [ ] 如果是 AI 生成，披露模型/工具

---

## 4. Commit 前缀

| 前缀 | 用途 |
|---|---|
| `spec:` | SPEC 变更 |
| `skill:` | skill 新增/修改 |
| `lab:` | 实验 |
| `eval:` | 评测 |
| `fix:` | 修错 |
| `gov:` | 治理/模板 |
| `fail:` | 失败记录 |

示例：`spec: clarify 0 is not a trainable bias`

---

## 5. 数据与密钥

**绝对不能进仓库：**

- 学生姓名、家长联系方式、成绩、作品。
- 学校合同、报价、内部排课。
- API key、token、cookie、私钥。
- 受限许可的语料、权重。

**提交前：**

```bash
git diff --cached | grep -Ei "api[_-]?key|token|secret|password|BEGIN.*PRIVATE"
```

发现泄漏：立即轮换密钥；仅删文件不够，历史里仍有。

---

## 6. 实验目录规范

每个实验一个目录：`lab/<两位编号>-<slug>/`

必须包含：

- `README.md`：假设、装置、跑法、预期、结论。
- `run.sh` 或 `run.py`：可复现入口。
- `config.json`：模型、量化、beta/gamma、seed。
- `results/`：日志、指标、`top_k_hash`。
- `FAIL-###` 链接（如果失败）。

没有 `README + 可复现入口 + 结果` 的实验，不算实验，只是折腾。

---

## 7. 评审

- 所有 PR 默认请求 `@Deepmind-hub777`。
- 豆包可以给“证据签字”，但不能 merge。
- Grok 可以给“构建可复现签字”，但不能 merge。
- 学生只能评论/提 proposal，不能 approve。

**Merge 前必须：**

1. CI 绿。
2. 至少 1 个人类 approve（当前只有 Milo）。
3. 没有 `temporary` 未标失效日期。
4. 没有敏感数据。

---

## 8. 对外话术

能说：

- 同一输入，同一结果。
- 可复现，可审计。
- 有 gate，有回滚。

不能说：

- 准确。
- 零幻觉。
- 超越某某模型（除非有同口径、同装置的公开 eval）。

---

## 9. 一句话

**先把话说清楚，再把代码写对；先让失败可复现，再谈成功。**
