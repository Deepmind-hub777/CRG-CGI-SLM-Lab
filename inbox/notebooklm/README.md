# inbox/notebooklm · 海外私人知识库的导入区

**状态：** draft
**最后更新：** 2026-11-26

---

## 1. 这是什么

NotebookLM（Gemini Notebook）是 Milo 的海外私人知识库。这个目录是它的**导入闸门**：

```text
NotebookLM（+1 草稿）
   │  导出包
   ▼
inbox/notebooklm/（拆卡、核引用、查冲突）
   │  PR
   ▼
GitHub main（-1 证据）
   │  同步
   ▼
飞书知识库（人读的桌面）
```

**NotebookLM 不是 0。** 它是有引用的生成器；引用可能错、可能过时、可能断章取义。它的输出先当 `[B]` 或 `[C-待证]`，核过 source 才升 `[C]`。

## 2. 什么进仓库，什么不进

| 内容 | 去哪 |
|---|---|
| 蒸馏卡（claim + source + tag） | 本目录，可进 public |
| 来源清单（标题/链接/页码） | 本目录，可进 public |
| 冲突记录、FAIL | 本目录 / `FAILURES.md` |
| 原始导出全文、PDF、音频转写 | `raw/`，**gitignored**，只留本地/私有 |
| 学生数据、家长信息、合同、密钥 | **不进仓库** |

**规则：** 先放 `raw/`，再拆卡；只提交拆过的卡，不提交原文。`raw/` 已在 `.gitignore`。

## 3. 目录规范

```text
inbox/notebooklm/<YYYY-MM-DD>-<slug>/
├── README.md        # 这个 notebook 是什么、来源、用途
├── cards.jsonl      # 原子主张卡，一行一卡
├── sources.md       # 引用清单：标题/链接/页码/短摘
└── notes.md         # 你的判断、可疑点、待决
```

## 4. 卡片格式

```json
{"claim_id":"NBL-001","claim":"……","source":"source-1 p.12","tag":"[C]","status":"verified","action":"spec","conflict":"none"}
```

| 字段 | 说明 |
|---|---|
| `claim_id` | `NBL-<三位序号>`；全局唯一 |
| `claim` | 一句一个主张；不要把整段塞进来 |
| `source` | 对应来源与位置；没有就写 `none` |
| `tag` | `[A]/[B]/[C]/[D]` |
| `status` | `unverified` / `verified` / `conflict` / `rejected` |
| `action` | `spec` / `eval` / `archive` / `rfc` / `reject` |
| `conflict` | 与哪条 SPEC/GLOSSARY/FAIL 冲突；没有写 `none` |

## 5. 处理流程

1. **收包**：原始内容放 `raw/`；记下 notebook 名、导出时间、导出类型、用途。
2. **拆卡**：一句一卡；不要把“背景”当“主张”。
3. **核引用**：每条 claim 找 source 段落；找不到 → `[B]`；找到但来源不可靠 → `[C-待证]`。
4. **查冲突**：与 `SPEC/`、`GLOSSARY.md`、`FAILURES.md` 对照；冲突开 RFC，不静默合并。
5. **定 action**：`spec`（进规范）/ `eval`（做探针）/ `archive`（只归档）/ `rfc`（要改宪制）/ `reject`（不成立）。
6. **走 PR**：Milo 批；合并后同步飞书。
7. **记状态**：`received → distilled → pr → merged → synced`。

## 6. 第一包建议

不要选最大的 notebook，选最关键的。建议选与“三元算子 / 0 轴 / 端侧 SLM”直接相关的 briefing；这样第一包能进 `SPEC` 或 `eval`，而不是只进归档。

## 7. 不做

- 不把 NotebookLM 的整篇输出直接倒进 public repo。
- 不把“音频概述”的转写当证据；它只是二次生成。
- 不把引用当“已经核实”；引用也要核。
- 不绕过 PR；不直推 main。
