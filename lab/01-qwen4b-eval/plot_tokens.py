import struct, numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
PROBES = ROOT / "probes"

def load(path):
    out = []
    with open(path, "rb") as f:
        n = struct.unpack("<i", f.read(4))[0]
        for _ in range(n):
            layer, typ, ndim = struct.unpack("<iii", f.read(12))
            ne = struct.unpack("<4q", f.read(32))
            num = 1
            for x in ne: num *= x
            data = np.frombuffer(f.read(num * 4), dtype=np.float32)
            arr = data.reshape((ne[3], ne[2], ne[1], ne[0]))[0]
            last = arr[:, -1, :ne[1]]
            last = last / (last.sum(-1, keepdims=True) + 1e-12)
            out.append(last)
    return np.array(out)  # [layer, head, kv]

C = load(PROBES / "e001_correct.bin")
F = load(PROBES / "e001_flipped.bin")

panels = [
    (C, 21, "anchor token '0' (stable)"),
    (C, 36, "'权重' (stable)"),
    (C, 37, "'之外' (correct)"),
    (F, 37, "'之内' (flipped)"),
]

fig, axes = plt.subplots(2, 2, figsize=(12, 8), sharex=True, sharey=True)
for ax, (M, tok, title) in zip(axes.ravel(), panels):
    mat = M[:, :, tok]
    im = ax.imshow(mat, aspect="auto", cmap="magma", origin="lower", vmin=0, vmax=0.16)
    ax.set_title(title)
    ax.set_xlabel("head")
    ax.set_ylabel("layer")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
plt.tight_layout()
plt.savefig(ROOT / "attn_tokens.png", dpi=170)
print("saved attn_tokens.png")
