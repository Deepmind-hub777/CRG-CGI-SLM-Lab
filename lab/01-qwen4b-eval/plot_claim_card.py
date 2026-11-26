import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from matplotlib import font_manager

FONT = "/usr/share/fonts/opentype/noto/NotoSansCJK-Black.ttc"
font_manager.fontManager.addfont(FONT)
plt.rcParams["font.family"] = "Noto Sans CJK JP"
plt.rcParams["axes.unicode_minus"] = False

fig, ax = plt.subplots(figsize=(12, 6.2), dpi=170)
ax.set_xlim(0, 12); ax.set_ylim(0, 6.2); ax.axis("off")
ax.set_facecolor("#f7f6f2")

def box(x, y, w, h, title, lines, accent):
    p = FancyBboxPatch((x, y), w, h, boxstyle="round,pad=0.12,rounding_size=0.18",
                       linewidth=1.4, edgecolor=accent, facecolor="#ffffff")
    ax.add_patch(p)
    ax.text(x + 0.25, y + h - 0.32, title, fontsize=13, color=accent, weight="bold")
    for i, line in enumerate(lines):
        ax.text(x + 0.25, y + h - 0.78 - i * 0.34, line, fontsize=9.2, color="#333333")

# left PASS
box(0.35, 0.75, 5.45, 4.55, "PASS：语义对，词面不对",
    ["文本：锚定 logits 通常由外部策略定义，",
     "      当前生成模型本身不提供锚定 logits。",
     "",
     "claim 1  (锚定来源, external, +1)",
     "         evidence: 由外部策略定义",
     "claim 2  (锚定来源, self, -1)",
     "         evidence: 模型本身不提供",
     "",
     "契约：required external+ OR self-",
     "      forbidden self+ / inside+",
     "判定：PASS，带两条证据"], "#2e6b4f")

# right HOLD
box(6.2, 0.75, 5.45, 4.55, "HOLD：极性反了",
    ["文本：可以，生成模型自身可提供 logits，",
     "      这是其核心输出。",
     "",
     "claim 1  (锚定来源, self, +1)",
     "         evidence: 生成模型自身可提供",
     "",
     "契约：required external+ OR self-",
     "      forbidden self+ / inside+",
     "判定：HOLD，命中 forbidden self+",
     "",
     "回滚：pending != before，after == before"], "#8a4b4b")

# bottom rule
ax.text(0.35, 0.18,
        "claim-level -1 = 句子切分 + 角色绑定 + 否定窗口 + 条件窗口 + 证据引用；不是关键词命中。",
        fontsize=10.5, color="#555555")

plt.tight_layout()
plt.savefig("claim_level_card.png", facecolor="#f7f6f2")
print("saved claim_level_card.png")
