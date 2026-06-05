import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch

fig, ax = plt.subplots(figsize=(18, 11))
ax.set_xlim(0, 18)
ax.set_ylim(0, 11)
ax.axis('off')
fig.patch.set_facecolor('#f8f9fa')
ax.set_facecolor('#f8f9fa')

SRC  = "#aecde8"   # source datasets — blue
PROC = "#f9c784"   # processing steps — amber
OUT  = "#95d5b2"   # intermediate outputs — green
KG   = "#c9b1e8"   # knowledge graph — purple
EDGE = "#333333"

TITLE_FS   = 15
BODY_FS    = 14
LABEL_FS   = 12
LEGEND_FS  = 12


def box(ax, x, y, w, h, title, body, color, title_fs=TITLE_FS, body_fs=BODY_FS):
    patch = FancyBboxPatch((x, y), w, h,
                           boxstyle="round,pad=0.05,rounding_size=0.18",
                           linewidth=1.6, edgecolor=EDGE, facecolor=color,
                           zorder=3)
    ax.add_patch(patch)
    cx, cy = x + w / 2, y + h / 2
    if body:
        ax.text(cx, cy + 0.28, title, ha='center', va='center',
                fontsize=title_fs, fontweight='bold', zorder=4)
        ax.text(cx, cy - 0.28, body, ha='center', va='center',
                fontsize=body_fs, color='#333333', zorder=4, linespacing=1.4)
    else:
        ax.text(cx, cy, title, ha='center', va='center',
                fontsize=title_fs, fontweight='bold', zorder=4)
    # return centre, left-mid, right-mid, top-mid, bot-mid
    return dict(c=(cx, cy), L=(x, cy), R=(x+w, cy),
                T=(cx, y+h), B=(cx, y), x=x, y=y, w=w, h=h)


def arrow(ax, p_from, p_to, label="", rad=0.0, lbl_off=(0, 0)):
    a = FancyArrowPatch(p_from, p_to,
                        connectionstyle=f"arc3,rad={rad}",
                        arrowstyle='-|>', mutation_scale=16,
                        linewidth=1.5, color=EDGE, zorder=2)
    ax.add_patch(a)
    if label:
        mx = (p_from[0] + p_to[0]) / 2 + lbl_off[0]
        my = (p_from[1] + p_to[1]) / 2 + lbl_off[1]
        ax.text(mx, my, label, ha='center', va='center',
                fontsize=LABEL_FS, style='italic', color='#111',
                bbox=dict(boxstyle="round,pad=0.22", fc="white",
                          ec="#bbbbbb", alpha=0.92), zorder=5)


# ── Column x-anchors ──────────────────────────────────────────────
COL1_X = 0.4    # sources
COL2_X = 7.0    # processing  (gap widened: 7.0 - (0.4+4.8) = 1.8 units)
COL3_X = 13.0   # outputs
W_SRC  = 4.8
W_PRO  = 4.8
W_OUT  = 4.7
BOX_H  = 1.85

# ── Row y-anchors (bottom of each box) ────────────────────────────
ROW_TOP = 7.8
ROW_MID = 4.9
ROW_BOT = 2.0

# ── Source datasets ────────────────────────────────────────────────
foods = box(ax, COL1_X, ROW_TOP, W_SRC, BOX_H,
            "Dataset Foods  ·  Kaggle 10K Recipes",
            "recipes · ingredients · steps\nnutrition · ratings",
            SRC)

wolf = box(ax, COL1_X, ROW_MID, W_SRC, BOX_H,
           "Food Carbon Footprint  ·  Wolfram",
           "538 foods · CO₂e per kg\n+ OWID fallback (9 foods)",
           SRC)

usda = box(ax, COL1_X, ROW_BOT, W_SRC, BOX_H,
           "Dataset Quantities  ·  USDA SR 2018",
           "4,446 gram-weight portion entries",
           SRC)

# ── Processing steps ───────────────────────────────────────────────
canon = box(ax, COL2_X, ROW_TOP, W_PRO, BOX_H,
            "Ingredient Canonicalisation",
            "103,908 raw strings  →  58 canonical names",
            PROC)

co2 = box(ax, COL2_X, ROW_MID, W_PRO, BOX_H,
          "CO₂e Rate Assignment",
          "Wolfram primary · OWID fallback\n→ emission factor per canonical entity",
          PROC)

gram = box(ax, COL2_X, ROW_BOT, W_PRO, BOX_H,
           "Gram-Weight Grounding",
           "USDA lookup  52.9%\nHeuristic fallback  47.1%",
           PROC)

# ── Outputs ────────────────────────────────────────────────────────
calc = box(ax, COL3_X, ROW_MID, W_OUT, BOX_H,
           "Recipe-Level CO₂e",
           "co2e_kg = Σ qty × g/unit × CO₂e/kg ÷ 1000\n9,997 recipes scored",
           OUT)

kg = box(ax, COL3_X, ROW_TOP, W_OUT, BOX_H,
         "Knowledge Graph",
         "~202,000 nodes & edges\nqueried via SPARQL",
         KG, title_fs=TITLE_FS + 1)

# ── Arrows: sources → processing ──────────────────────────────────
arrow(ax, foods['R'], canon['L'], "ingredient names", lbl_off=(0, 0.3))
arrow(ax, wolf['R'],  co2['L'],   "CO₂e factors",     lbl_off=(0, 0.3))
arrow(ax, usda['R'],  gram['L'],  "portion grams",    lbl_off=(0, 0.3))

# ── Canonicalisation → CO₂e assignment ───────────────────────────
arrow(ax, canon['B'], co2['T'], "58 canonical entities", lbl_off=(0.5, 0))

# ── CO₂e + gram-weight → recipe-level output ─────────────────────
arrow(ax, co2['R'],  calc['L'], "")
gram_right = (gram['x'] + gram['w'], gram['y'] + gram['h'] * 0.7)
calc_left  = (calc['x'], calc['y'] + calc['h'] * 0.2)
arrow(ax, gram_right, calc_left, "g per unit", rad=-0.2, lbl_off=(0.6, 0.45))

# ── Foods → KG direct (recipe/nutrition nodes) ────────────────────
# Exit top-right of Foods, enter left-mid of KG, arc curves above Canon box
foods_top_r = (foods['x'] + foods['w'] * 0.8, foods['y'] + foods['h'])
kg_left_mid = (kg['x'], kg['y'] + kg['h'] * 0.5)
arrow(ax, foods_top_r, kg_left_mid,
      "recipe & nutrition nodes", rad=-0.38, lbl_off=(-1.6, 1.0))

# ── Recipe CO₂e → KG (enriches HAS_INGREDIENT edges) ─────────────
arrow(ax, calc['T'], kg['B'],
      "enriches HAS_INGREDIENT edges", lbl_off=(1.8, 0.0))

# ── Title ─────────────────────────────────────────────────────────
ax.set_title("Data Sources & Exchange Pipeline",
             fontsize=20, fontweight='bold', pad=18, color='#111111')

# ── Legend ────────────────────────────────────────────────────────
handles = [
    mpatches.Patch(facecolor=SRC,  edgecolor=EDGE, label="Source dataset"),
    mpatches.Patch(facecolor=PROC, edgecolor=EDGE, label="Processing step"),
    mpatches.Patch(facecolor=OUT,  edgecolor=EDGE, label="Intermediate output"),
    mpatches.Patch(facecolor=KG,   edgecolor=EDGE, label="Knowledge Graph"),
]
ax.legend(handles=handles, loc='upper right', ncol=1, frameon=True,
          fontsize=LEGEND_FS,
          framealpha=0.95, edgecolor='#cccccc')

plt.tight_layout()
plt.savefig("./visualization_preprocessing/data_sources_exchange.png",
            dpi=200, bbox_inches='tight', facecolor=fig.get_facecolor())
plt.show()
