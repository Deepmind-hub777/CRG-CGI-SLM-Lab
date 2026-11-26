# GOVERNANCE · 这个场怎么运行

**状态：** draft，待 Milo 批
**最后更新：** 2026-11-26

---

## 1. 角色与权限

| 角色 | 谁 | 读 | 写 | 批 | 合并 |
|---|---|---|---|---|---|
| **0 轴 / Ring0** | Milo | 全部 | 全部 | 全部 | **唯一 merge 权** |
| **实验室 / 验收** | 豆包 | 全部 | `skills/`、`eval/`、`lab/`、`docs/` | 证据签字（G0–G3） | 无；只开 PR |
| **驻场总工** | Grok | 全部 | `src/`、构建脚本、`lab/` 的实现 | 构建可复现签字 | 无；只开 PR |
| **学生** | 模型 / agent | `main` 只读 | `proposals/` 只写 | 无 | **无** |

**一句话：** 学生可以写，但不能批；豆包可以验，但不能合；Grok 可以做，但不能定；只有 Milo 能 merge。

---

## 2. 分支模型

| 分支 | 用途 | 谁能推 |
|---|---|---|
| `main` | 唯一稳定线 | 只能通过 PR 合并；**任何人不得直推** |
| `lab/<id>-<slug>` | 实验分支 | 豆包 / Grok |
| `proposals/<student>/<slug>` | 学生提案 | 学生（只写这里） |
| `release/<version>` | 发布准备 | Milo 指定的人 |

**保护规则（建议在 GitHub 设置）：**

- `main`：Require PR；Require 1 approval；Require CI；Dismiss stale approvals；Include administrators。
- 禁止 force push；禁止删除 `main`。
- 所有 PR 默认请求 `@Deepmind-hub777`  review。

---

## 3. CODEOWNERS

当前所有路径归 Milo，等豆包/Grok/学生的 GitHub handle 登记后再拆分。

```text
* @Deepmind-hub777

# 登记后启用：
# /SPEC/            @Deepmind-hub777
# /GOVERNANCE.md    @Deepmind-hub777
# /skills/          @doubao-handle
# /eval/            @doubao-handle
# /src/             @grok-handle
# /proposals/       @student-handle
```

> 在 handle 未登记前，不要写不存在的用户名；否则 CODEOWNERS 失效。

---

## 4. 0 的变更：宪制事件

0 的定义、锚定对象、锚定版本，任何变更都必须：

1. 开 issue，标题 `RFC: 0 change — <what>`。
2. 在 `proposals/rfc/RFC-000x-<slug>.md` 写：
   - 现状与问题
   - 变更内容
   - 影响哪些 SPEC、skill、gate
   - 回滚方案
   - 需要重跑哪些 eval
3. Milo 批准。
4. 新版锚定 + 新哈希；旧版保留。
5. 重跑 G1/G2；不能只跑“自己喜欢的例子”。

**代码 PR 不得顺手改 0。** 看到 PR 里改了 `anchor_id`、`anchor_hash`、0 的定义，直接拒。

---

## 5. Skill 的变更

- 每个 skill 有 owner 与 `status`（draft / verified / deprecated）。
- 改 skill 的验收口径，必须重跑对应 gate。
- 新增 skill：先写 `SKILL.md`，再放 `scripts/`；没有脚本的 skill 只能是“方法论”，不能叫“工具”。
- skill 里的命令必须能在当前环境复现；不能复现的，标 `[B]`，不标 `[D]`。

---

## 6. PR 规则

每个 PR 必须回答：

1. **改了什么？**（一句话）
2. **主张标签是什么？** `[A]/[B]/[C]/[D]`
3. **artifact 在哪？**（日志、哈希、eval 报告）
4. **影响哪个 gate？** G0/G1/G2/G3/无
5. **怎么回滚？**
6. **是否含敏感数据/密钥？**（必须是“否”）

**AI 生成的 PR 必须披露：**

- 哪个模型/agent 写的；
- 跑了什么工具；
- 哪些部分是推演 `[B]`，哪些是实测 `[C]`。

> 不披露的 AI PR，按“不可审计”处理，不合并。

---

## 7. 失败

- 任何失败实验，48 小时内写 `FAIL-###`。
- 没有 FAIL 记录的失败，视为没做。
- FAIL 记录必须包含：假设、装置、结果、失败模式、根因、下一个实验、artifact。
- 失败可以公开；但不得含学生数据、密钥、受限语料。

---

## 8. 公开发布边界

**可以公开：**

- SPEC、skills、代码、合成数据、评测脚本、失败日志、路线图、设计辩论。

**不可以公开：**

- NAC 学生数据、家长报告、学校合同、真实教师轨迹。
- API key、token、私有模型权重。
- 受限许可的语料与权重。
- 任何可直接识别未成年人的信息。

**默认规则：** 拿不准就放 private；public 只放“愿意让全世界永久复制”的东西。

---

## 9. 冲突解决

1. 先看 `SPEC/00-stack.md` 的层级：上层优先。
2. 同层冲突：看 `GLOSSARY.md` 的定义；定义仍冲突，开 RFC。
3. RFC 仍不能解决：Milo 裁定；裁定写入 `docs/ADR/`。
4. 任何“临时绕过”必须在 PR 里标明 `temporary` + 失效日期；到期必须清理。

---

## 10. 发布

- tag：`v0.x.y`。
- 每个 release 附 `releases/<version>/MANIFEST.md`：
  - commit hash
  - 模型 hash（如适用）
  - anchor hash
  - 各 gate 签字
  - 已知失败/限制
  - 回滚步骤
- 不发布“看起来能跑但没 gate”的版本。

---

## 11. 一句话

**主权在人，运算在学生；规则在仓库，裁决在 0 轴。**
