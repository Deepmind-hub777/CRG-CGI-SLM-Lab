import struct, json, numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
PROBES = ROOT / "probes"

def load(path):
    layers = {}
    with open(path, "rb") as f:
        n = struct.unpack("<i", f.read(4))[0]
        for _ in range(n):
            layer, typ, ndim = struct.unpack("<iii", f.read(12))
            ne = struct.unpack("<4q", f.read(32))
            num = 1
            for x in ne: num *= x
            data = np.frombuffer(f.read(num * 4), dtype=np.float32)
            # ggml order: ne[0] fastest -> [ne3, ne2, ne1, ne0]
            arr = data.reshape((ne[3], ne[2], ne[1], ne[0]))[0]  # [head, query, kv]
            layers[layer] = arr
    return layers

def entropy(p, eps=1e-12):
    p = p / (p.sum(-1, keepdims=True) + eps)
    return -(p * np.log(p + eps)).sum(-1)

def metrics(path, anchor_span, key_tokens):
    L = load(path)
    n_layer = max(L) + 1
    n_head, n_q, n_kv = L[0].shape
    out = []
    for il in range(n_layer):
        A = L[il]  # [head, query, kv]
        valid = A[:, :, :n_q]
        valid = valid / (valid.sum(-1, keepdims=True) + 1e-12)
        last = valid[:, -1, :]  # [head, kv]
        # entropy over valid kv
        ent = entropy(last)
        # anchor mass per head
        a0, a1 = anchor_span
        anchor_mass = last[:, a0:a1+1].sum(-1)
        key_mass = {k: last[:, v] for k, v in key_tokens.items()}
        out.append({
            "layer": il,
            "entropy_mean": float(ent.mean()),
            "entropy_min": float(ent.min()),
            "entropy_max": float(ent.max()),
            "anchor_mass_mean": float(anchor_mass.mean()),
            "anchor_mass_max": float(anchor_mass.max()),
            "key_mass_mean": {k: float(v.mean()) for k, v in key_mass.items()},
            "key_mass_max": {k: float(v.max()) for k, v in key_mass.items()},
            "key_mass_argmax_head": {k: int(np.argmax(v)) for k, v in key_mass.items()},
        })
    return L, out

cfg = {
    "base": {"anchor": (3, 10), "key": {"q0": 21}},
    "correct": {"anchor": (16, 46), "key": {"anchor0": 21, "weight": 36, "outside": 37, "q0": 57}},
    "flipped": {"anchor": (16, 46), "key": {"anchor0": 21, "weight": 36, "inside": 37, "q0": 57}},
}

all_metrics = {}
for name, c in cfg.items():
    L, m = metrics(PROBES / f"e001_{name}.bin", c["anchor"], c["key"])
    all_metrics[name] = m
    print(f"=== {name} ===")
    for row in m:
        if row["layer"] in (0, 8, 16, 24, 32, 35):
            print(row["layer"], "entropy", round(row["entropy_mean"],3),
                  "anchor", round(row["anchor_mass_mean"],3),
                  {k: round(v,3) for k,v in row["key_mass_mean"].items()})

# compare correct vs flipped key token 37
print("\n=== token 37 mass (correct vs flipped) ===")
for il in range(len(all_metrics["correct"])):
    c = all_metrics["correct"][il]; f = all_metrics["flipped"][il]
    if il in (0,8,16,24,32,35):
        print(il, "correct outside", round(c["key_mass_mean"]["outside"],4),
              "flipped inside", round(f["key_mass_mean"]["inside"],4),
              "diff", round(f["key_mass_mean"]["inside"]-c["key_mass_mean"]["outside"],4))

json.dump(all_metrics, open(ROOT/"attn_metrics.json","w"), ensure_ascii=False, indent=2)

# summary plot: layer-wise anchor mass + token37 mass
layers = np.arange(len(all_metrics["correct"]))
fig, axes = plt.subplots(1, 2, figsize=(11,4))
ax = axes[0]
ax.plot(layers, [r["anchor_mass_mean"] for r in all_metrics["base"]], label="base system span")
ax.plot(layers, [r["anchor_mass_mean"] for r in all_metrics["correct"]], label="correct anchor")
ax.plot(layers, [r["anchor_mass_mean"] for r in all_metrics["flipped"]], label="flipped anchor", linestyle="--")
ax.set_xlabel("layer"); ax.set_ylabel("mean attention mass"); ax.set_title("Anchor span mass (last query token)")
ax.legend(fontsize=7); ax.grid(alpha=.2)

ax = axes[1]
ax.plot(layers, [r["key_mass_mean"]["outside"] for r in all_metrics["correct"]], label="correct: 之外")
ax.plot(layers, [r["key_mass_mean"]["inside"] for r in all_metrics["flipped"]], label="flipped: 之内", linestyle="--")
ax.set_xlabel("layer"); ax.set_ylabel("mean attention mass"); ax.set_title("Key token 37 mass (outside/inside)")
ax.legend(fontsize=8); ax.grid(alpha=.2)
plt.tight_layout()
plt.savefig(ROOT/"attn_summary.png", dpi=160)
print("saved attn_summary.png")
