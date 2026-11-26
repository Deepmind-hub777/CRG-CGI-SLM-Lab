import struct, numpy as np
from pathlib import Path
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt

ROOT = Path(__file__).resolve().parent
PROBES = ROOT / "probes"

def load_last(path, token_idx):
    matrix = []
    with open(path, "rb") as f:
        n = struct.unpack("<i", f.read(4))[0]
        for _ in range(n):
            layer, typ, ndim = struct.unpack("<iii", f.read(12))
            ne = struct.unpack("<4q", f.read(32))
            num = 1
            for x in ne: num *= x
            data = np.frombuffer(f.read(num * 4), dtype=np.float32)
            arr = data.reshape((ne[3], ne[2], ne[1], ne[0]))[0]  # [head, query, kv]
            last = arr[:, -1, :ne[1]]
            last = last / (last.sum(-1, keepdims=True) + 1e-12)
            matrix.append(last[:, token_idx])
    return np.array(matrix)  # [layer, head]

correct = load_last(PROBES / "e001_correct.bin", 37)
flipped = load_last(PROBES / "e001_flipped.bin", 37)

fig, axes = plt.subplots(1, 2, figsize=(12, 5), sharey=True)
for ax, mat, title in [(axes[0], correct, "correct: 之外"), (axes[1], flipped, "flipped: 之内")]:
    im = ax.imshow(mat, aspect="auto", cmap="magma", origin="lower", vmin=0, vmax=max(correct.max(), flipped.max()))
    ax.set_title(title)
    ax.set_xlabel("head")
    ax.set_ylabel("layer")
    fig.colorbar(im, ax=ax, fraction=0.046, pad=0.04)
plt.tight_layout()
plt.savefig(ROOT / "attn_heads.png", dpi=170)

# print top heads and overlap
def top(mat, k=10):
    idx = np.dstack(np.unravel_index(np.argsort(mat.ravel())[-k:], mat.shape))[0]
    return [(int(l), int(h), float(mat[l, h])) for l, h in idx[::-1]]

print("correct top:", top(correct))
print("flipped top:", top(flipped))
print("layer20 correct:", [(h, round(float(correct[20, h]), 3)) for h in np.argsort(correct[20])[-3:][::-1]])
print("layer20 flipped:", [(h, round(float(flipped[20, h]), 3)) for h in np.argsort(flipped[20])[-3:][::-1]])
