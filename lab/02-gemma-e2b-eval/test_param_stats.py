#!/usr/bin/env python3
"""Param accounting test. No model, no GPU."""
import json
import pathlib
import sys
import tempfile

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import param_stats


def main():
    with tempfile.TemporaryDirectory() as d:
        p = pathlib.Path(d)
        (p / "config.json").write_text(json.dumps({"torch_dtype": "bfloat16"}), encoding="utf-8")
        (p / "model.safetensors.index.json").write_text(json.dumps({"total_size": 8_045_591_552}), encoding="utf-8")
        rec = param_stats.audit_model_dir(p)
        assert rec["bytes_per_param"] == 2
        assert rec["params_est"] == 4_022_795_776, rec
        ratio = 33_030_144 / rec["params_est"]
        assert abs(ratio - 0.008210743432977096) < 1e-12, ratio
    print("param_stats tests: OK")


if __name__ == "__main__":
    main()
