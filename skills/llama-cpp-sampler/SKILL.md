---
name: llama-cpp-sampler
status: draft
owner: Doubao
claim: "[D] proposal"
last_verified: never
---

# llama-cpp-sampler

## 什么时候用

- 要把 `SPEC/01` 的三元采样器，落到 `llama.cpp` / `llama-cpp-python`。
- 要做一个 PC 原型，再决定是否移植到 Termux / Android。
- 要用 GBNF 或自定义 sampler 做锚定约束。

## 两条路径

| 路径 | 用途 | 优点 | 缺点 |
|---|---|---|---|
| **Python**：`llama-cpp-python` 的 `LogitsProcessor` | PC 快速原型 | 改一行就能试 | 手机端不直接可用 |
| **C++**：`llama.cpp` 的自定义 `llama_sampler` | 端侧 / 高性能 | 可进 Android / Termux | 要编译、要维护 patch |

> 先 Python 验证数学，再 C++ 移植。不要一上来改 C++。

## Python 路径

1. 安装 `llama-cpp-python`（CPU 版即可）。
2. 写一个 `TernaryLogitsProcessor`：
   - `__call__(input_ids, logits)`；
   - 用 `SPEC/01` 的公式改 logits；
   - 返回同形状的 logits。
3. 接到 `Llama(..., logits_processor=...)`。
4. 先跑 `beta=0,gamma=0`，确认输出与不接 processor 一致。
5. 再开 `beta`，记录熵、KL、`top_k_hash`。

**注意：**

- 不同版本的 `llama-cpp-python` 对 `logits` 的类型（list / numpy）可能不同；以当前安装版本的签名为准。
- 不要在 processor 里加载第二个模型；锚定 logits 要预先算好或缓存。
- processor 里不要做网络请求；端侧要离线。

## C++ 路径

1. 在 `llama.cpp` 里加一个自定义 sampler：
   - `llama_sampler_i` 的 `sample` / `apply` / `accept` / `reset` / `clone` / `free`；
   - 通过 `llama_sampler_chain_add` 接入。
2. 锚定 logits 由外部传入（冻结参照），不要在 sampler 里跑生成。
3. 用 `llama-bench` 或自定义 harness 记录：
   - tokens/s
   - p50/p95 首 token
   - 内存
   - 温度/降频
4. 把 patch 放在 `src/patches/`，附 `git diff` 与 upstream commit hash。

**不要**直接改用户全局安装的 llama.cpp；用独立 clone + patch。

## 锚定的三种接法

| 接法 | 做法 | 适用 |
|---|---|---|
| **GBNF 约束** | 把锚定词表/结构写成 grammar | 术语、格式、JSON |
| **logit bias** | 对锚定 token 加固定偏置 | 快速试验 |
| **完整三元 sampler** | `beta*a - gamma*d` | 研究主路径 |

先用 GBNF / logit bias 验证方向，再上完整 sampler。

## 输出

- `src/` 或 `lab/<id>/` 下的可复现脚本。
- `config.json`：模型、量化、`beta`、`gamma`、`H_th`、seed。
- `results/`：日志、`top_k_hash`、延迟。
- 一份 `README.md`：怎么跑、跑到什么程度、哪里没验证。

## 坑

| 坑 | 现象 | 处理 |
|---|---|---|
| 版本漂移 | API 签名变了 | 锁版本；记录 commit |
| logits 被原地改 | 基线也被污染 | 先 copy，再改 |
| 锚定 logits 每 token 重算 | 延迟爆炸 | 缓存 / 预计算 / 熵门控 |
| Python 与 C++ 结果不一致 | 浮点/归一化差异 | 用同一组合成 logits 对齐 |
| 手机编译 flags 不对 | 跑不起来 / 极慢 | 先 PC 交叉编译验证；再 Termux 原生编译 |

## 验收

- `lab/00-smoke-test` 通过。
- `beta=0,gamma=0` 与基线一致（数值容差内）。
- 同输入、同 seed、同构建，`top_k_hash` 一致。
- 记录“未验证”的部分；不要写“已支持 Android”，除非真机跑过。
