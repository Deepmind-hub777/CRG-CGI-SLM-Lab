# MANIFEST · lab-qwen3-4b-v0.1

**状态：** `[C]` 实验资产  
**日期：** 2026-11-27  
**Release：** https://github.com/Deepmind-hub777/CRG-CGI-SLM-Lab/releases/tag/lab-qwen3-4b-v0.1

---

## 模型

```text
文件名：Qwen3-4B-Instruct-2507-Q4_K_M.gguf
大小：2,497,280,448 bytes（2.32 GiB）
SHA256：8cdb57cbb880d313736a9bc4e3d3d2485f145b5e19cf33783746e753e82641fc
来源：lmstudio-community/Qwen3-4B-Instruct-2507-GGUF
```

## Release 资产

| 文件 | 大小（bytes） | SHA256 |
|---|---:|---|
| `Qwen3-4B-Instruct-2507-Q4_K_M.gguf.part-00` | 1,258,291,200 | `cbb869d36ba713152bb4d88a105cb0b3083958305776f88fa09ab208baba6459` |
| `Qwen3-4B-Instruct-2507-Q4_K_M.gguf.part-01` | 1,238,989,248 | `24c81afe35eb4235bdaf080bd8ca2ef3bb3ccff9e98059d7ee06cac65e6610f4` |

合并：

```bash
cat Qwen3-4B-Instruct-2507-Q4_K_M.gguf.part-00 \
    Qwen3-4B-Instruct-2507-Q4_K_M.gguf.part-01 \
    > Qwen3-4B-Instruct-2507-Q4_K_M.gguf
sha256sum Qwen3-4B-Instruct-2507-Q4_K_M.gguf
```

## 验证

- 上传后已重新下载 `part-01`，独立回读哈希与本地分卷一致。
- 合并后完整模型哈希已本地验证为 `8cdb57cbb880d313736a9bc4e3d3d2485f145b5e19cf33783746e753e82641fc`。

## 边界

- 模型不进 git 树；只走 Release 资产。
- 不是通用模型发布；只用于 `lab/01-qwen4b-eval` 复现。
- 复用前核对上游模型卡与 license。
- 不声明“准确 / 零幻觉 / 超越某模型”。
