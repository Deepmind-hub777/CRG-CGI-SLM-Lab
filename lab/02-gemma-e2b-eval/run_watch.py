#!/usr/bin/env python3
"""Run-state watcher: process + artifact sentinel, GPU is not the criterion.

States:
- completed: RUN_COMPLETE.json or EVAL_COMPLETE.json exists
- running: process alive and latest log mtime within --stale-minutes
- stalled: process alive and latest log older than --stale-minutes
- manifest_only: manifest/eval exists, no process, no sentinel
- idle: none of the above

This script does not launch or stop anything. It is safe to run on CPU.
"""
import argparse
import json
import pathlib
import time

LOG_GLOBS = ("*.log", "train.log", "eval.log")
SENTINELS = ("RUN_COMPLETE.json", "EVAL_COMPLETE.json")


def _read_proc_cmdlines():
    out = []
    for p in pathlib.Path("/proc").glob("[0-9]*/cmdline"):
        try:
            raw = p.read_bytes().replace(b"\x00", b" ").decode("utf-8", "ignore")
        except Exception:
            continue
        if raw.strip():
            out.append(raw)
    return out


def _latest_mtime(run_dir):
    times = []
    for pattern in LOG_GLOBS:
        for p in run_dir.glob(pattern):
            if p.is_file():
                times.append(p.stat().st_mtime)
    return max(times) if times else None


def classify(run_dir, now=None, stale_minutes=15, proc_cmds=None, run_id=None):
    now = time.time() if now is None else now
    run_dir = pathlib.Path(run_dir)
    run_id = run_id or run_dir.name
    if any((run_dir / s).exists() for s in SENTINELS):
        return "completed"
    proc_cmds = _read_proc_cmdlines() if proc_cmds is None else proc_cmds
    proc_alive = any(run_id in c or str(run_dir) in c for c in proc_cmds)
    latest = _latest_mtime(run_dir)
    stale_s = stale_minutes * 60
    if proc_alive:
        if latest is not None and now - latest <= stale_s:
            return "running"
        return "stalled"
    if (run_dir / "manifest.json").exists() or (run_dir / "eval.json").exists():
        return "manifest_only"
    return "idle"


def scan(root, stale_minutes=15, proc_cmds=None, now=None):
    root = pathlib.Path(root)
    if not root.exists():
        return []
    out = []
    for d in sorted(p for p in root.iterdir() if p.is_dir()):
        state = classify(d, now=now, stale_minutes=stale_minutes, proc_cmds=proc_cmds, run_id=d.name)
        out.append({"run_id": d.name, "state": state, "latest_log_mtime": _latest_mtime(d)})
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--root", default="runs")
    ap.add_argument("--stale-minutes", type=int, default=15)
    ap.add_argument("--json", action="store_true")
    args = ap.parse_args()
    states = scan(args.root, stale_minutes=args.stale_minutes)
    if args.json:
        print(json.dumps(states, ensure_ascii=False, indent=2))
    else:
        for s in states:
            print(f"{s['run_id']}\t{s['state']}")


if __name__ == "__main__":
    main()
