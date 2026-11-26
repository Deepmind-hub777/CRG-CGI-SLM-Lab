---
name: android-termux-lab
status: draft
owner: Doubao
claim: "[D] proposal"
last_verified: never
---

# android-termux-lab

## 什么时候用

- 要在 Android 手机上跑本地 SLM（离线、无 API）。
- 要测 tokens/s、p50/p95、内存、温度、降频。
- 要验证“三元采样器在端侧是否可用”，而不只是 PC 上好看。

## 目标设备

| 项 | 值 |
|---|---|
| 手机 | 一加十二 |
| 内存 / 存储 | 24 GB / 1 TB |
| 模型 | Qwen3-4B Q4_K_M（2.5 GB）；LFM2.5 8B-A1B（4.84 GB，MoE） |
| 运行时 | Termux + llama.cpp（CPU / 可选 GPU） |

## 步骤

1. **装 Termux**（F-Droid 版，不用 Play 版旧包）。
2. **装依赖：** `git`、`cmake`、`make`、`clang`、`python`。
3. **编译 llama.cpp**：
   - 先 CPU 版，确认能跑；
   - 再试 GPU / OpenCL / Vulkan（按设备支持）；
   - 记录编译 flags 与 commit hash。
4. **放模型**：`~/models/`；校验 SHA256。
5. **跑基线**：
   - `llama-cli` 或 `llama-server`；
   - 固定 prompt、固定 seed、固定 `n_predict`；
   - 记录 tokens/s、首 token、内存。
6. **跑三元版**：
   - 先 `beta=0,gamma=0`；
   - 再小 `beta`；
   - 记录熵、KL、`top_k_hash`。
7. **温控 / 续航**：
   - 连续 30 分钟；
   - 每 5 分钟记录温度、频率、tokens/s；
   - 记录是否降频、是否杀后台。
8. **24 小时 soak**（发布前）：
   - 反复冷启动 / 热启动；
   - 观察内存泄漏、漂移、崩溃。
9. **回滚**：
   - 保留上一版模型 + 锚定；
   - 一键切回；记录回滚时间。

## 度量

| 指标 | 怎么测 | 备注 |
|---|---|---|
| tokens/s | 生成固定 128 token，计时 | 冷/热分开 |
| 首 token 延迟 | 从提交到第一个 token | p50/p95 |
| 内存 | `dumpsys meminfo` / Termux `free` | 峰值 |
| 温度 | 系统传感器 / `thermal` 日志 | 每 5 分钟 |
| 降频 | 频率日志 | 记录触发点 |
| 回滚 | 手动计时 | 目标待定 |

## 坑

| 坑 | 现象 | 处理 |
|---|---|---|
| Play 版 Termux | 包旧、权限怪 | 用 F-Droid |
| 模型放错目录 | 找不到 / 加载失败 | 固定 `~/models`，写进脚本 |
| 内存不足 | 被杀后台 | 4B Q4 优先；8B-A1B 需实测 |
| 发热降频 | 前 2 分钟快，后面掉 | 记录 30 分钟曲线，不报“峰值” |
| Android 后台限制 | 锁屏后停 | 前台服务 / wake lock；记录策略 |
| 直接跑双模型 | 延迟爆炸 | 熵门控；锚定预计算 |

## 验收

- 真机跑过，不是模拟器。
- 有 30 分钟温控曲线。
- 有 24 小时 soak（发布前）。
- 有回滚步骤与实测时间。
- 没跑过的不写“支持”；只写“未验证”。
