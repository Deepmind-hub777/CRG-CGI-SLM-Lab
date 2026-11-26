# src · 生产级代码入口

**状态：** empty / draft
**最后更新：** 2026-11-26

---

## 现在有什么

没有。Day 0 不放生产代码。

原型在：

- `lab/00-smoke-test/`：采样器数学单测。
- 后续 `lab/<id>-<slug>/`：可复现实验。

## 什么时候往这里放

只有满足三条，才从 `lab/` 提升到 `src/`：

1. 过 G1（或 G2/G3，视模块）。
2. 有可复现测试。
3. 有明确 owner 与回滚方案。

## 目录约定（未来）

```text
src/
├── sampler/        # C++ / Python 三元采样器
├── anchor/         # 冻结锚定的加载与检索
├── verifier/       # 独立 -1 校验器
├── export/         # GGUF 导出与校验
└── device/         # Termux / Android 适配
```

## 纪律

- 不在 `src/` 里放模型权重。
- 不在 `src/` 里放学生数据。
- 不把“能跑”当“可发布”；还要过 gate。
- 任何 `src/` 变更，必须说明对 `SPEC/` 的影响。
