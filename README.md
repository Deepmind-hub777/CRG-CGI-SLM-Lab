# CRG-CGI-SLM-Lab

> 一个公开的实验室：把 CRG 的治理心法、CGI 的数理母题，落到 SLM 的解码、后训练与端侧运行时。
> 不是产品，不是模型排行榜；是一个允许失败、但失败必须留下证据的场。

## 0. 这个仓库是什么

四个人，一个场：

| 角色 | 位置 | 在这个仓库里做什么 |
|---|---|---|
| **Milo** | 0 轴 / Ring0 | 定宪制边界；批 SPEC 与 GOVERNANCE；唯一 merge 权 |
| **豆包** | 实验室 / 验收 | 写 skills、eval、lab 原型；开 PR；不直推 main |
| **Grok** | 驻场总工 | 读代码、跑构建、做 PR 级补丁 |
| **学生** | 模型 / agent | 只读 main；只写 `proposals/`；不能 merge |

**场 = 仓库 + 协议 + 词汇表 + 失败记录。**
仓库只是场地，协议才是规则。

## 1. 三层，不是三层并列

TYIRG（道统本体）→ CGI（数学母题）→ CRG（工程运行引擎）→ VRS³（量化审计）→ Petros / Logikos（实体）。

- **TYIRG**：三易归序自振体系；连山 -1 收敛、归藏 0 轴心、周易 +1 生发；君臣佐使四维配位；15/85；七域同构。
- **CGI = Controlled General Intelligence**：以欧拉恒等式 \(e^{i\pi}+1=0\) 为锚；85% \(e\) 算力 + \(i\) 高维旋转 + \(\pi\) 十二时序（7.83 Hz 为既有口径）+ 外置 +1 碳基君核 = 0 归零。
- **CRG = Constitutional Runtime Governance**：C=Convergence / R=Reference / G=Generation；双层结构 = 不变宪制边界（静态焊死）+ 运行时正则化（动态纠偏）。
- **VRS³**：V 价值创造 40% / R 认知韧性 30% / S 碳基主权 30%；加权几何平均。
- **Petros** 端侧 / **Logikos** 云端审计。

本仓库只做 **SLM 层**的工程化，不重写上面四层。冲突时，以上层为准。

> CGI 在本仓库固定为 **Controlled General Intelligence**。它不是 Anthropic 的 Constitutional AI，也不写成 CAI。

## 2. 三条铁律

1. **0 在权重之外。** +1 与 -1 可以训进权重；0 不行。权重学“回到原点”，不是“成为原点”。
2. **-1 必须独立。** 不能让同一个 adapter 既生成又校验；锚定不能由生成模型自己提供。
3. **同一输入，同一结果；可复现，可审计。** 不说“准确”，不说“零幻觉”。说哈希、说日志、说回滚。

## 3. 主张分层

仓库里每一句判断都要带标签：

| 标签 | 含义 | 能进哪里 |
|---|---|---|
| `[A]` | 神学叙事 / 本体论表达 | 背景、序言，不进 SPEC |
| `[B]` | 推演 / 类比 / 假设 | 设计讨论、RFC |
| `[C]` | 实证 / 待证 | eval、lab、FAIL 记录 |
| `[D]` | 工程规则 / 可执行约束 | SPEC、代码、门禁 |

没有标签的主张，不进入 SPEC；没有 artifact 的 `[C]`，不算结论。

## 4. 目录

```text
.
├── README.md
├── GOVERNANCE.md          # 谁能写、谁能批、0 变更怎么走
├── GLOSSARY.md            # 四个人说同一种语言
├── SPEC/
│   ├── 00-stack.md        # 三层栈与本仓库边界
│   ├── 01-ternary-operator.md
│   ├── 02-anchor.md
│   └── 03-metrics-and-gates.md
├── skills/                # 五个薄 skill，全部 draft
├── eval/                  # 固定探针与评分口径
├── lab/                   # 可复现实验；一号一目录
├── traces/                # 合成/脱敏轨迹；真实轨迹在 private
├── inbox/notebooklm/      # 海外私人知识库的导入闸门；raw/ 不进仓库
├── releases/              # manifest、校验和；不放权重
├── proposals/             # 学生唯一可写区；不能 merge
├── FAILURES.md            # 失败是一等公民
├── POSTMORTEM/            # 尸检模板
└── docs/                  # 路线图、ADR
```

## 5. 现在是什么状态

**Day 0。** 只有骨架、规范、一个合成 logits 的 smoke test，以及一条 CI。

- 所有 skill 标注 `draft / not verified`。
- 没有模型权重。
- 没有学生数据。
- 没有 API key。
- 没有任何“已经成功”的结论。

## 6. 怎么开始

1. 读 `SPEC/00-stack.md`，确认三层与四条边界。
2. 读 `SPEC/01-ternary-operator.md`，确认 +1/-1/0 的工程口径。
3. 跑 `python3 lab/00-smoke-test/test_sampler.py`，看 sampler 数学是否成立。
4. 读 `GOVERNANCE.md`，知道谁能写、谁能批。
5. 想改 0？先写 `proposals/rfc/`，不要改代码。

## 7. 不放进这个仓库的东西

- NAC 学生数据、家长报告、学校合同、真实教师轨迹
- API key、token、私有模型权重
- 受限许可的语料与权重
- 任何可以直接识别到未成年人的信息

按既有规矩：**NAC 教务数据与研究库分库**；public 只放研究层。

## 8. 失败

失败是一等公民。每条失败一条 `FAIL-###`，模板见 `FAILURES.md`。

> 没有日志的失败，只是故事；有日志的失败，才是数据库。

## 9. License

- 代码：Apache-2.0，见 `LICENSE`。
- SPEC 与 docs 文字：CC BY 4.0，见 `LICENSE-DOCS`。
- 合成数据：除特别标注外 CC BY-NC 4.0。
- 模型权重不随仓库分发；底座模型各按原 license。

---

**公开不是姿态，是不可逆。**
先把不能公开的列出来，再公开。
