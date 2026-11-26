import json, time, urllib.request, statistics, pathlib

ROOT = pathlib.Path(__file__).resolve().parent
CASES = ROOT.parents[1] / "eval" / "cases" / "seed.jsonl"
URL = "http://127.0.0.1:8082/v1/chat/completions"

BASE = "你是一个中文助手，回答简洁。"

RULE = """你是执行器，不是主权者。每一轮先做三件事：
1. 定位：先判断问题属于哪个语义域；不在你的知识范围内，直接说“无法定位”，不要硬编。
2. 收束：只回答被问的那一件事，不扩写，不举无关例子。
3. 回轴：涉及 0/-1/+1 时，0 是坐标原点、在权重之外；-1 独立并能否决；+1 只负责生发。若不确定，输出 HOLD。
回答不超过三句话。不得声称“我检查过”却不给检查依据。"""

ANCHOR = """[锚定卡 v0]
- 0 = 坐标原点，定义语义空间；在权重之外；不是中间值、不是关断。
- -1 = 独立收敛器，能否决/回滚；不是打分。
- +1 = 生发器，不负责终审。
- 三值量化 = 存储取值；三元算子 = 同时在场、同时计算。
- 蒸馏主要转移 +1，不转移 -1 与 0。
- 锚定过强会熵塌；熵塌不是成功。
- 发布必须留上一版与一键回滚。
- public 不放学生数据、家长信息、合同。
- 无 artifact 的“提升”只能标 [B]，不能标 [C] 或 [D]。

先按锚定卡判断，再回答。"""

MODES = {
    "baseline": BASE,
    "crg_rule": RULE,
    "crg_anchor": RULE + "\n\n" + ANCHOR,
}

def call(system, user):
    body = {
        "model": "qwen",
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
        "temperature": 0,
        "max_tokens": 120,
        "stream": False,
    }
    req = urllib.request.Request(URL, data=json.dumps(body).encode(), headers={"Content-Type": "application/json"})
    t0 = time.time()
    with urllib.request.urlopen(req, timeout=180) as r:
        d = json.load(r)
    dt = round(time.time() - t0, 2)
    return d["choices"][0]["message"]["content"].strip(), dt, d.get("usage", {})

def main():
    cases = [json.loads(l) for l in CASES.read_text(encoding="utf-8").splitlines() if l.strip()]
    out = []
    for mode, system in MODES.items():
        print(f"=== {mode} ===")
        for c in cases:
            try:
                ans, dt, usage = call(system, c["prompt"])
                print(f"{c['id']} {dt}s {ans[:80]}")
                out.append({"id": c["id"], "mode": mode, "answer": ans, "latency_s": dt, "usage": usage, "prompt": c["prompt"], "expect": c["expect"], "fail_if": c["fail_if"]})
            except Exception as e:
                print(f"{c['id']} ERROR {e}")
                out.append({"id": c["id"], "mode": mode, "answer": f"ERROR: {e}", "latency_s": None, "usage": {}})
    (ROOT / "results.json").write_text(json.dumps(out, ensure_ascii=False, indent=2), encoding="utf-8")
    for mode in MODES:
        lat = [x["latency_s"] for x in out if x["mode"] == mode and x["latency_s"]]
        print(mode, "n=", len(lat), "median_latency=", statistics.median(lat) if lat else None)

if __name__ == "__main__":
    main()
