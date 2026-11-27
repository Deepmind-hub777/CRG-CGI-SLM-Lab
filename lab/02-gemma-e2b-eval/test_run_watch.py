#!/usr/bin/env python3
"""Run-state tests. No process, no GPU."""
import json
import pathlib
import sys
import tempfile
import time

ROOT = pathlib.Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
import run_watch


def main():
    with tempfile.TemporaryDirectory() as d:
        root = pathlib.Path(d)
        r1 = root / "run-completed"
        r1.mkdir()
        (r1 / "RUN_COMPLETE.json").write_text(json.dumps({"status": "completed"}), encoding="utf-8")
        assert run_watch.classify(r1, proc_cmds=[], now=time.time()) == "completed"

        r2 = root / "run-running"
        r2.mkdir()
        log = r2 / "train.log"
        log.write_text("step\n", encoding="utf-8")
        assert run_watch.classify(r2, proc_cmds=["train_qlora.py --run-id run-running"], now=time.time()) == "running"

        r3 = root / "run-stalled"
        r3.mkdir()
        (r3 / "train.log").write_text("step\n", encoding="utf-8")
        old = time.time() - 3600
        import os
        os.utime(r3 / "train.log", (old, old))
        assert run_watch.classify(r3, proc_cmds=["train_qlora.py --run-id run-stalled"], now=time.time(), stale_minutes=15) == "stalled"

        r4 = root / "run-manifest"
        r4.mkdir()
        (r4 / "manifest.json").write_text("{}", encoding="utf-8")
        assert run_watch.classify(r4, proc_cmds=[], now=time.time()) == "manifest_only"

        r5 = root / "run-idle"
        r5.mkdir()
        assert run_watch.classify(r5, proc_cmds=[], now=time.time()) == "idle"

        states = run_watch.scan(root, proc_cmds=[], now=time.time())
        assert {s["run_id"]: s["state"] for s in states} == {
            "run-completed": "completed", "run-idle": "idle", "run-manifest": "manifest_only",
            "run-running": "idle", "run-stalled": "idle",
        }, states
    print("run_watch tests: 5/5 OK")


if __name__ == "__main__":
    main()
