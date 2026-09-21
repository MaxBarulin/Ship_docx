# -*- coding: utf-8 -*-
"""Чертёж общего вида узла ВГ-2026.15.00 «Шлюпочный пост» + спецификация."""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon as MPoly, Circle, FancyBboxPatch
from lib import gorizont as G, gorizont_hydro as H, gorizont_boatpost as B
from lib import eskd
from lib import gorizont_strength as St

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
BR = chr(10)
INK, ACC, SEA, GRY, GRN = "#16202f", "#b02634", "#1c5c8a", "#9aa4b4", "#1f7a5a"

# геометрия по модели, м
X0, X1 = B.X0, B.X1
DECK = B.Z_DECK
SP_Y0, SP_Y1 = 7.00, 8.15          # спонсон
BOAT = dict(x0=40.30, x1=48.90, y0=5.65, y1=8.00, z0=10.10, z1=11.10)
CAB = dict(x0=40.73, x1=48.47, y0=5.88, y1=7.76, z0=11.10, z1=11.80)
CHOCK = [(42.25, 42.65), (46.55, 46.95)]
DAVIT_X = [41.59, 47.61]
POST_Y, BEAM_Z, FALL_Y = 7.90, 12.43, 5.76
RAIL_Y, RAIL_Z = 8.07, (9.80, 10.92)
KN_X = [X0 + 0.55 + i * B.BRACKET_PITCH for i in range(B.N_BRACKETS)]

# Лист по ГОСТ 2.301 с основной надписью 2.104 формы 1:
# заголовок и подпись сверху ушли в штамп
_SHEET = eskd.Sheet('A1', mark="ВГ-2026.15.00 СБ",
                    name="Шлюпочный пост",
                    material="Сталь 09Г2С ГОСТ 19281-2014",
                    mass=None, scale="1:20",
                    sheet_no=1, sheets=1)
fig = _SHEET.fig


def _ax(x, y, w, h):
    return _SHEET.axes_frac(x, y, w, h)


def frame(ax, title, sub=""):
    ax.set_aspect("equal"); ax.axis("off")
    ax.set_title(title + ("   " + sub if sub else ""), fontsize=11, loc="left",
                 color=INK, fontweight="bold")


def dim(ax, p0, p1, txt, off=0.0, vert=False, fs=8.5):
    x0, y0 = p0; x1, y1 = p1
    if vert:
        ax.annotate("", (x0 + off, y0), (x1 + off, y1),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=0.8))
        ax.text(x0 + off - 0.12, (y0 + y1) / 2, txt, rotation=90, ha="right",
                va="center", fontsize=fs, color=INK)
    else:
        ax.annotate("", (x0, y0 + off), (x1, y1 + off),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=0.8))
        ax.text((x0 + x1) / 2, y0 + off + 0.06, txt, ha="center", va="bottom",
                fontsize=fs, color=INK)


def pos(ax, x, y, n, dx=0.0, dy=0.6):
    ax.plot([x, x + dx], [y, y + dy], color=GRY, lw=0.7)
    ax.add_patch(Circle((x + dx, y + dy), 0.22, facecolor="white",
                        edgecolor=INK, lw=0.8, zorder=5))
    ax.text(x + dx, y + dy, str(n), ha="center", va="center", fontsize=8,
            color=INK, zorder=6)


# ------------------------------------------------ вид с борта ---------------
ax = _ax(*[0.030, 0.600, 0.455, 0.315])
frame(ax, "Вид с борта", "шп. %d…%d, отметки от основной плоскости"
      % (round(X0 / 0.55), round(X1 / 0.55)))
ax.plot([X0 - 2.2, X1 + 2.2], [DECK, DECK], color=INK, lw=2.4)
ax.add_patch(Rectangle((X0 - 1.6, DECK - 0.12), (X1 - X0) + 3.2, 0.12,
                       facecolor="#dfe5ee", edgecolor=INK, lw=1.0))
for xk in KN_X:
    ax.add_patch(MPoly([(xk, DECK - 0.12), (xk, DECK - 0.55), (xk + 0.10, DECK - 0.12)],
                       closed=True, facecolor="#c9d3e0", edgecolor=INK, lw=0.8))
ax.add_patch(Rectangle((BOAT["x0"], BOAT["z0"]), BOAT["x1"] - BOAT["x0"],
                       BOAT["z1"] - BOAT["z0"], facecolor="#eef2f7",
                       edgecolor=INK, lw=1.4))
ax.add_patch(Rectangle((CAB["x0"], CAB["z0"]), CAB["x1"] - CAB["x0"],
                       CAB["z1"] - CAB["z0"], facecolor="#dbe6f1",
                       edgecolor=INK, lw=1.2))
for a, b in CHOCK:
    ax.add_patch(Rectangle((a, DECK), b - a, BOAT["z0"] - DECK,
                           facecolor="#c9d3e0", edgecolor=INK, lw=1.0))
for xd in DAVIT_X:
    ax.plot([xd, xd], [DECK, BEAM_Z], color=SEA, lw=3.0, solid_capstyle="butt")
    ax.plot([xd, xd], [BEAM_Z, BEAM_Z + 0.10], color=SEA, lw=3.0)
ax.plot([DAVIT_X[0], DAVIT_X[1]], [BEAM_Z, BEAM_Z], color=SEA, lw=2.0, ls=":")
ax.plot([X0 - 1.2, X1 + 1.2], [RAIL_Z[1], RAIL_Z[1]], color=GRY, lw=1.4)
for xr in [X0 - 1.2 + i * 1.6 for i in range(8)]:
    ax.plot([xr, xr], RAIL_Z, color=GRY, lw=1.0)
ax.add_patch(Rectangle((X1 + 0.5, DECK), 1.2, 0.85, facecolor="#f2d9a8",
                       edgecolor=INK, lw=1.0))
ax.text(X1 + 1.1, DECK + 1.05, "лебёдка", fontsize=8, color=INK, ha="center")
dim(ax, (X0, DECK), (X1, DECK), "8600", off=-1.05)
dim(ax, (DAVIT_X[0], DECK), (DAVIT_X[1], DECK), "6020", off=-0.55)
dim(ax, (X0 - 1.9, DECK), (X0 - 1.9, BEAM_Z), "2630", off=0.0, vert=True)
pos(ax, KN_X[2], DECK - 0.42, 1, dx=-1.0, dy=-0.9)
pos(ax, X0 + 1.0, DECK - 0.06, 2, dx=-1.4, dy=1.1)
pos(ax, DAVIT_X[0], 11.4, 4, dx=-1.5, dy=1.0)
pos(ax, CHOCK[1][1], DECK + 0.15, 5, dx=1.4, dy=-0.7)
pos(ax, X1 + 1.1, DECK + 0.45, 10, dx=1.3, dy=0.9)
pos(ax, CAB["x1"] - 1.0, CAB["z1"], 11, dx=1.2, dy=1.0)
ax.set_xlim(X0 - 3.6, X1 + 4.0)
ax.set_ylim(DECK - 2.2, BEAM_Z + 1.6)

# ------------------------------------------------ план ----------------------
ax2 = _ax(*[0.515, 0.600, 0.455, 0.315])
frame(ax2, "План", "полуширота от диаметральной плоскости")
ax2.add_patch(Rectangle((X0 - 1.6, SP_Y0), (X1 - X0) + 3.2, SP_Y1 - SP_Y0,
                        facecolor="#e8edf4", edgecolor=INK, lw=1.2))
ax2.plot([X0 - 2.4, X1 + 2.6], [SP_Y0, SP_Y0], color=INK, lw=1.6)
ax2.text(X0 - 2.3, SP_Y0 - 0.22, "кромка шлюпочной палубы", fontsize=8, color=GRY)
ax2.add_patch(Rectangle((BOAT["x0"], BOAT["y0"]), BOAT["x1"] - BOAT["x0"],
                        BOAT["y1"] - BOAT["y0"], facecolor="#eef2f7",
                        edgecolor=INK, lw=1.4))
ax2.add_patch(Rectangle((CAB["x0"], CAB["y0"]), CAB["x1"] - CAB["x0"],
                        CAB["y1"] - CAB["y0"], facecolor="#dbe6f1",
                        edgecolor=INK, lw=1.0, ls="--"))
for a, b in CHOCK:
    ax2.add_patch(Rectangle((a, BOAT["y0"] + 0.23), b - a,
                            (BOAT["y1"] - BOAT["y0"]) - 0.46,
                            facecolor="#c9d3e0", edgecolor=INK, lw=1.0))
for xk in KN_X:
    ax2.plot([xk, xk], [SP_Y0, SP_Y1], color=GRY, lw=1.2, ls=(0, (5, 3)))
for xd in DAVIT_X:
    ax2.plot([xd, xd], [FALL_Y, POST_Y], color=SEA, lw=2.2)
    ax2.add_patch(Circle((xd, POST_Y), 0.11, facecolor="white", edgecolor=SEA, lw=1.6))
    ax2.add_patch(Circle((xd, FALL_Y), 0.07, facecolor="white", edgecolor=SEA, lw=1.4))
ax2.plot([X0 - 1.2, X1 + 1.2], [RAIL_Y, RAIL_Y], color=GRY, lw=1.4)
ax2.plot([X0 + 2.0, X0 + 3.6], [RAIL_Y, RAIL_Y], color=ACC, lw=2.6)
ax2.text(X0 + 2.8, RAIL_Y - 0.30, "калитка 1600", fontsize=8, color=ACC, ha="center")
ax2.add_patch(Rectangle((X1 + 0.5, SP_Y0 + 0.15), 1.2, 0.9, facecolor="#f2d9a8",
                        edgecolor=INK, lw=1.0))
ax2.add_patch(Rectangle((X0 - 1.5, BOAT["y0"] - 1.15), 3.0, 1.05,
                        facecolor="#e6f0e8", edgecolor=GRN, lw=1.2))
ax2.text(X0, BOAT["y0"] - 0.62, "посадочная площадка", fontsize=8,
         color=GRN, ha="center", va="center")
dim(ax2, (X0 - 1.6, SP_Y1), (X1 + 1.6, SP_Y1), "11800", off=0.78)
dim(ax2, (X1 + 2.2, SP_Y0), (X1 + 2.2, SP_Y1), "1150", off=0.0, vert=True)
dim(ax2, (X1 + 3.0, BOAT["y0"]), (X1 + 3.0, BOAT["y1"]), "2350", off=0.0, vert=True)
pos(ax2, KN_X[1], SP_Y0 + 0.55, 1, dx=-0.9, dy=0.95)
pos(ax2, X0 + 3.0, SP_Y1 - 0.25, 3, dx=0.8, dy=0.75)
pos(ax2, X0 + 4.4, RAIL_Y, 6, dx=0.9, dy=0.65)
pos(ax2, X1 + 1.1, SP_Y0 + 0.6, 7, dx=0.9, dy=0.9)
pos(ax2, X0, BOAT["y0"] - 1.1, 8, dx=-1.6, dy=-0.55)
ax2.set_xlim(X0 - 3.6, X1 + 4.0)
ax2.set_ylim(BOAT["y0"] - 2.1, SP_Y1 + 1.35)


# ------------------------------------------------ сечение по книце ----------
ax3 = _ax(*[0.030, 0.300, 0.205, 0.250])
frame(ax3, "Сечение А—А по книце", "масштаб крупнее, размеры в мм")
xh = 44.6
hb = H.half_breadth(xh, DECK - 0.1) if H.half_breadth(xh, DECK - 0.1) > 0 else 7.0
SH = H.super_half_breadth(xh)
ax3.plot([SH, SH], [DECK - 2.6, DECK + 0.0], color=INK, lw=2.4)
ax3.plot([SH - 1.4, SP_Y1], [DECK, DECK], color=INK, lw=2.4)
ax3.add_patch(Rectangle((SP_Y0, DECK - 0.12), SP_Y1 - SP_Y0, 0.12,
                        facecolor="#dfe5ee", edgecolor=INK, lw=1.2))
ax3.add_patch(MPoly([(SP_Y0 - 0.02, DECK - 0.12), (SP_Y1, DECK - 0.12),
                     (SP_Y0 - 0.02, DECK - 0.55)],
                    closed=True, facecolor="#c9d3e0", edgecolor=INK, lw=1.4))
ax3.add_patch(Rectangle((BOAT["y0"], BOAT["z0"]), BOAT["y1"] - BOAT["y0"],
                        BOAT["z1"] - BOAT["z0"], facecolor="#eef2f7",
                        edgecolor=INK, lw=1.4))
ax3.add_patch(Rectangle((CAB["y0"], CAB["z0"]), CAB["y1"] - CAB["y0"],
                        CAB["z1"] - CAB["z0"], facecolor="#dbe6f1",
                        edgecolor=INK, lw=1.2))
ax3.add_patch(Rectangle((BOAT["y0"] + 0.23, DECK), 1.9, BOAT["z0"] - DECK,
                        facecolor="#c9d3e0", edgecolor=INK, lw=1.0))
ax3.plot([POST_Y, POST_Y], [DECK, BEAM_Z], color=SEA, lw=3.0)
ax3.plot([FALL_Y, POST_Y], [BEAM_Z, BEAM_Z], color=SEA, lw=2.6)
ax3.plot([FALL_Y, FALL_Y], [BOAT["z1"], BEAM_Z], color=SEA, lw=1.6)
ax3.plot([RAIL_Y, RAIL_Y], RAIL_Z, color=GRY, lw=1.6)
ax3.plot([RAIL_Y - 0.35, RAIL_Y + 0.05], [RAIL_Z[1], RAIL_Z[1]], color=GRY, lw=1.4)
dim(ax3, (SP_Y0, DECK + 0.02), (SP_Y1, DECK + 0.02), "1150", off=-1.35)
dim(ax3, (SP_Y1 + 0.55, DECK), (SP_Y1 + 0.55, DECK - 0.55), "420", off=0.0, vert=True)
dim(ax3, (SP_Y1 + 1.15, DECK), (SP_Y1 + 1.15, BEAM_Z), "2630", off=0.0, vert=True)
ax3.text(SH - 1.3, DECK - 1.35, "надстройка", fontsize=8, color=GRY)
pos(ax3, SP_Y0 + 0.5, DECK - 0.33, 1, dx=-1.0, dy=-0.8)
pos(ax3, SP_Y1 - 0.15, DECK - 0.06, 3, dx=0.55, dy=-1.15)
pos(ax3, POST_Y, 11.6, 4, dx=1.0, dy=0.6)
pos(ax3, BOAT["y0"] + 1.0, DECK + 0.15, 5, dx=-1.2, dy=-0.55)
pos(ax3, RAIL_Y, RAIL_Z[1], 6, dx=0.85, dy=0.7)
ax3.set_xlim(SH - 1.6, SP_Y1 + 2.1)
ax3.set_ylim(DECK - 2.0, BEAM_Z + 1.1)

# ------------------------------------------------ спецификация --------------
ax4 = _ax(*[0.300, 0.040, 0.690, 0.515])
ax4.axis("off")
ax4.set_xlim(0, 1); ax4.set_ylim(0, 1)
ax4.text(0, 0.985, "Спецификация ВГ-2026.15.00", fontsize=12,
         fontweight="bold", color=INK, va="top")
head = ["Поз.", "Обозначение", "Наименование", "Кол.", "Материал, примечание",
        "Масса, кг", "Всего, кг"]
colx = [0.0, 0.045, 0.185, 0.56, 0.60, 0.865, 0.935]
y = 0.925
for h_, x_ in zip(head, colx):
    ax4.text(x_, y, h_, fontsize=8.5, fontweight="bold", color=INK, va="top")
ax4.plot([0, 1], [y - 0.028, y - 0.028], color=INK, lw=1.0)
y -= 0.055
rows = B.rows()
for r in rows:
    if r["kind"] == "покупное" and rows[rows.index(r) - 1]["kind"] == "деталь":
        ax4.text(0, y, "Покупные изделия", fontsize=8.5, fontstyle="italic",
                 color=GRY, va="top")
        y -= 0.036
    vals = [str(r["pos"]), r["mark"], r["name"], str(r["n"]), r["material"],
            "%.1f" % r["mass"], "%.1f" % r["total"]]
    for v, x_ in zip(vals, colx):
        ax4.text(x_, y, v, fontsize=8.3, color=INK, va="top")
    ax4.plot([0, 1], [y - 0.012, y - 0.012], color="#e4e9f0", lw=0.7)
    y -= 0.042
ax4.plot([0, 1], [y + 0.004, y + 0.004], color=INK, lw=1.0)
y -= 0.028
ax4.text(0.185, y, "Масса металлоконструкций поста", fontsize=8.6,
         fontweight="bold", color=INK, va="top")
ax4.text(0.935, y, "%.1f" % B.steel_mass(), fontsize=8.6, fontweight="bold",
         color=INK, va="top")
y -= 0.042
ax4.text(0.185, y, "Масса поста со шлюпкой и снабжением", fontsize=8.6,
         fontweight="bold", color=INK, va="top")
ax4.text(0.935, y, "%.1f" % B.total_mass(), fontsize=8.6, fontweight="bold",
         color=INK, va="top")
bk = St.report()["bracket"]
ax5 = _ax(*[0.030, 0.035, 0.245, 0.245])
ax5.axis("off"); ax5.set_xlim(0, 1); ax5.set_ylim(0, 1)
TT = [
    "1. Сварка полуавтоматическая в среде CO2, катет 6 мм," + BR + "   швы сплошные двусторонние.",
    ("2. Кницы поз. 1 ставить по рамным шпангоутам с шагом" + BR
     + "   %d мм, всего %d на пост.") % (B.BRACKET_PITCH * 1000, B.N_BRACKETS),
    ("3. Расчёт кницы: P = %.1f кН, σ_экв = %.1f МПа при" + BR
     + "   допускаемых %.0f МПа, запас %.1f.")
    % (bk["P"], bk["sigma_eq"], bk["sigma_allow"], bk["sigma_allow"] / bk["sigma_eq"]),
    "4. Спусковое устройство испытывать нагрузкой 2,2 массы" + BR + "   шлюпки с полным комплектом.",
    "5. Ограждение поз. 6 съёмное, калитка открывается внутрь," + BR + "   замок с фиксацией.",
    "6. Проход к посту с обоих бортов не менее 1200 мм в свету.",
    "7. Покрытие: грунт эпоксидный 2 x 60 мкм, эмаль" + BR + "   полиуретановая 2 x 50 мкм.",
]
ax5.text(0, 1.0, "Технические требования", fontsize=10.5, fontweight="bold",
         color=INK, va="top")
yy = 0.905
for t in TT:
    ax5.text(0, yy, t, fontsize=8.4, color=INK, va="top", linespacing=1.35)
    yy -= 0.075 * (1 + t.count(BR))


p = os.path.join(OUT, "05_шлюпочный_пост.png")
_SHEET.save(p)
print(p)
