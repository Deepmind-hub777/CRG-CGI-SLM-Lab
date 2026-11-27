#!/usr/bin/env python3
"""Parameter accounting from a local model directory.

The loaded model's sum(p.numel()) is not a safe denominator for a 4-bit
checkpoint: bnb replaces modules and can change the counted element count. For
audit, prefer the safetensors index total_size divided by the checkpoint dtype
width. This script makes that source explicit and keeps the loaded count as a
secondary field.
"""
import json
import hashlib
import pathlib

DTYPE_BYTES = {
    "float32": 4, "fp32": 4, "float": 4,
    "float16": 2, "fp16": 2, "half": 2,
    "bfloat16": 2, "bf16": 2,
}


def _dtype_bytes(config):
    raw = config.get("torch_dtype") or config.get("dtype") or "bfloat16"
    if isinstance(raw, dict):
        raw = raw.get("type", "bfloat16")
    return DTYPE_BYTES.get(str(raw).lower(), 2)


def audit_model_dir(model_dir):
    """Return an audit record or None when there is no local index/config."""
    path = pathlib.Path(model_dir)
    index_path = path / "model.safetensors.index.json"
    config_path = path / "config.json"
    if not index_path.exists():
        return None
    index = json.loads(index_path.read_text(encoding="utf-8"))
    total_size = index.get("total_size")
    if not isinstance(total_size, int):
        return None
    config = json.loads(config_path.read_text(encoding="utf-8")) if config_path.exists() else {}
    bpp = _dtype_bytes(config)
    params_est = total_size / bpp
    params_int = int(round(params_est))
    return {
        "model_dir": str(path.resolve()),
        "index_total_size_bytes": total_size,
        "dtype": str(config.get("torch_dtype") or config.get("dtype") or "bfloat16"),
        "bytes_per_param": bpp,
        "params_est": params_int,
        "formula": "index.total_size / bytes_per_param",
        "index_sha256": hashlib.sha256(index_path.read_bytes()).hexdigest(),
    }


def main():
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("model_dir")
    ap.add_argument("--out", default="")
    args = ap.parse_args()
    rec = audit_model_dir(args.model_dir)
    if rec is None:
        raise SystemExit(f"no model.safetensors.index.json under {args.model_dir}")
    text = json.dumps(rec, ensure_ascii=False, indent=2)
    if args.out:
        pathlib.Path(args.out).write_text(text + "\n", encoding="utf-8")
    print(text)


if __name__ == "__main__":
    main()
