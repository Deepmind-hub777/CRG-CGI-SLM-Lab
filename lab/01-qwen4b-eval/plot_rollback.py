import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch
from matplotlib import font_manager

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(12, 6.2), dpi=170)
ax.set_xlim(0, 12); ax.set_ylim(0, 6.2); ax.axis("off")
ax.set_facecolor("#f7f6f2")

def box(x, y, w, h, text, color="#2b2b2b", fill="#ffffff", fs=12):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12,rounding_size=0.18",
                       linewidth=1.2, edgecolor=color, facecolor=fill)
    ax.add_patch(p)
    ax.text(x + w/2, y + h/2, text, ha="center", va="center", fontsize=fs, color=color, linespacing=1.5)

def arrow(x1, y1, x2, y2, color="#2b2b2b", style="-|>", lw=1.6, ls="-"):
    a = FancyArrowPatch((x1, y1), (x2, y2), arrowstyle=style, mutation_scale=16,
                        linewidth=lw, color=color, linestyle=ls)
    ax.add_patch(a)

# top: three authorities
box(0.35, 5.05, 3.0, 0.85, "0 / 君\nanchor-v0  86f4…", fill="#eef2ea", fs=11)
box(4.55, 5.05, 3.0, 0.85, "+1 / 臣\nQwen3-4B draft", fill="#fdf3e3", fs=11)
box(8.75, 5.05, 2.9, 0.85, "-1 / 佐\nexternal policy  060d…", fill="#f6e9e9", fs=11)

# main transaction row
box(0.35, 3.15, 2.4, 1.15, "H_before\ndd73e7d41b\nlast committed", fill="#eef2ea", fs=11)
box(4.35, 3.15, 3.1, 1.15, "pending_bad\neca18399e1\nall drafts, incl. HOLD", fill="#f6e9e9", fs=11)
box(8.65, 3.15, 2.9, 1.15, "H_after\ndd73e7d41b\nrestored, hash equal", fill="#eef2ea", fs=11)

arrow(2.75, 3.72, 4.30, 3.72, color="#8a4b4b")
ax.text(3.55, 3.93, "write candidate", ha="center", fontsize=9.5, color="#8a4b4b")
arrow(7.45, 3.72, 8.60, 3.72, color="#2e6b4f")
ax.text(8.03, 3.93, "HOLD → restore", ha="center", fontsize=9.5, color="#2e6b4f")

# rollback loop
arrow(9.55, 3.10, 9.55, 2.55, color="#2e6b4f", style="-|>")
ax.text(9.70, 2.82, "after == before", fontsize=9.5, color="#2e6b4f")

# audit strip
box(0.35, 0.85, 11.25, 1.25,
    "audit chain（每条记录带 prev_hash / record_hash）\n"
    "before = dd73…   pending = eca1…   mid = eca1…   after = dd73…\n"
    "verdict = HOLD   rollback = REAL   txn = ee1d1bd38812d7ba",
    fill="#ffffff", fs=10.5)

# bottom note
ax.text(0.35, 0.35,
        "真实回滚的判据：pending ≠ before 且 mid == pending 且 after == before。"
        " 若 pending == before，只是 abort，不是 rollback。",
        fontsize=10, color="#555555")

plt.tight_layout()
plt.savefig("rollback_flow.png", facecolor="#f7f6f2")
print("saved rollback_flow.png")
