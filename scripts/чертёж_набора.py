# -*- coding: utf-8 -*-
"""Схема набора корпуса: бок и вид на днище."""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from lib import gorizont as G, gorizont_hydro as H, gorizont_struct as S
from lib import eskd

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8.5,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
os.makedirs(OUT, exist_ok=True)
INK, ACC, SEA, GRY, GRN = "#16202f", "#b02634", "#1c5c8a", "#9aa4b4", "#187454"
SP, FS = S.SPACING, S.FRAME_SPACING
X0, X1 = 2.0, 137.0
DB = S.DB_HEIGHT
ER = (12.0, 34.0)
ER_TOP = 0.465

# Лист по ГОСТ 2.301 с основной надписью 2.104 формы 1:
# заголовок и подпись сверху ушли в штамп
SH = eskd.Sheet('A1x2', mark="ВГ-2026.02.00",
                name="Схема набора корпуса",
                material="Сталь 09Г2С ГОСТ 19281-2014",
                mass=None, scale="1:100",
                sheet_no=1, sheets=1)
fig = SH.fig


def _ax(x, y, w, h):
    return SH.axes_frac(x, y, w, h)



ax = _ax(*[0.012, 0.10, 0.976, 0.80])
ax.set_aspect("equal")
ax.axis("off")

Z_SIDE = 10.6     # смещение бокового вида


def side_z(x, z):
    return Z_SIDE + z


# ---------- БОК
xs = [X0 + i * 0.5 for i in range(int((X1 - X0) / 0.5) + 1)]
ax.plot(xs, [side_z(x, H._station(x)[4]) for x in xs], color=INK, lw=1.8)
ax.plot([X0, X1], [side_z(0, G.DEPTH)] * 2, color=INK, lw=1.8)
ax.plot([X0, X1], [side_z(0, DB)] * 2, color=SEA, lw=1.6)
ax.plot([ER[0], ER[1]], [side_z(0, ER_TOP)] * 2, color=SEA, lw=1.6)
ax.plot([ER[0]] * 2, [side_z(0, ER_TOP), side_z(0, DB)], color=SEA, lw=1.2)
ax.plot([ER[1]] * 2, [side_z(0, ER_TOP), side_z(0, DB)], color=SEA, lw=1.2)
# шпангоуты
n = int((X1 - X0) / SP)
for i in range(n + 1):
    x = X0 + i * SP
    if x > X1:
        break
    z0 = H._station(x)[4]
    heavy = abs((x - X0) % FS) < 1e-6
    ax.plot([x, x], [side_z(x, z0), side_z(0, G.DEPTH)],
            color=SEA if heavy else "#b9c2ce", lw=1.5 if heavy else 0.5)
# бортовой стрингер и палуба
ax.plot([X0, X1], [side_z(0, 2.60)] * 2, color=GRN, lw=1.4)
# переборки
for xb in H.BULKHEADS[1:-1]:
    ax.plot([xb, xb], [side_z(xb, H._station(xb)[4]) - 0.1, side_z(0, G.DEPTH) + 0.35],
            color=ACC, lw=2.4)
    ax.text(xb, side_z(0, G.DEPTH) + 0.5, "%.0f" % xb, color=ACC, fontsize=8.5,
            ha="center", fontweight="bold")
ax.text(X0, side_z(0, G.DEPTH) + 1.25, "БОК. Красные — водонепроницаемые переборки, "
        "синие — рамные шпангоуты через 2200 мм, серые — холостые через 550 мм",
        fontsize=11, color=INK, fontweight="bold")
ax.text(X1, side_z(0, DB) + 0.12, "второе дно 1.30", fontsize=8.5, color=SEA, ha="right")
ax.text(23, side_z(0, ER_TOP) - 0.38, "понижение второго дна в МО 0.47",
        fontsize=8.5, color=SEA, ha="center")
ax.text(X1, side_z(0, 2.60) + 0.12, "бортовой стрингер 2.60", fontsize=8.5,
        color=GRN, ha="right")

# ---------- ДНИЩЕ (вид сверху), полуширота вниз от оси
for i in range(n + 1):
    x = X0 + i * SP
    if x > X1:
        break
    heavy = abs((x - X0) % FS) < 1e-6
    b = H.half_breadth(x, DB if not (ER[0] <= x <= ER[1]) else ER_TOP)
    if b < 0.4:
        continue
    ax.plot([x, x], [-b, b], color=SEA if heavy else "#c7cfda",
            lw=1.6 if heavy else 0.45)
for y in (0.0, 2.75, 5.50):
    xx = [x for x in xs if H._station(x)[0] > abs(y) + 0.35]
    if xx:
        ax.plot(xx, [y] * len(xx), color=INK, lw=1.8 if y == 0 else 1.4)
        ax.plot(xx, [-y] * len(xx), color=INK, lw=1.8 if y == 0 else 1.4)
for j in range(1, 13):
    y = j * SP
    if abs(y - 2.75) < 0.15 or abs(y - 5.50) < 0.15:
        continue
    xx = [x for x in xs if H._station(x)[0] > y + 0.35]
    if xx:
        ax.plot(xx, [y] * len(xx), color="#8e98a8", lw=0.55)
        ax.plot(xx, [-y] * len(xx), color="#8e98a8", lw=0.55)
ax.plot(xs, [H.half_breadth(x, G.DEPTH) for x in xs], color=INK, lw=1.8)
ax.plot(xs, [-H.half_breadth(x, G.DEPTH) for x in xs], color=INK, lw=1.8)
for xb in H.BULKHEADS[1:-1]:
    b = H.half_breadth(xb, 2.0)
    ax.plot([xb, xb], [-b, b], color=ACC, lw=2.4)
ax.text(X0, 9.6, "ДНИЩЕ. Продольные рёбра через 550 мм, вертикальный киль и "
        "днищевые стрингеры на 2.75 и 5.50 м от ДП, флоры через 2200 мм",
        fontsize=11, color=INK, fontweight="bold")
ax.text(X1, 0.18, "вертикальный киль", fontsize=8.5, color=INK, ha="right")
ax.text(X1, 2.93, "днищевой стрингер", fontsize=8.5, color=INK, ha="right")

# шкала шпангоутов
for x in range(0, 141, 10):
    ax.plot([x, x], [-9.6, -9.9], color="#56627a", lw=0.9)
    ax.text(x, -10.5, str(x), fontsize=8, color="#56627a", ha="center")
ax.plot([0, 139], [-9.75, -9.75], color="#56627a", lw=0.9)
ax.text(69.5, -11.5, "x от кормового перпендикуляра, м   "
        "(номер шпангоута = x / 0.55)", fontsize=9, color="#56627a", ha="center")
ax.set_xlim(-4, 143)
ax.set_ylim(-12.4, 17.6)
SH.save(os.path.join(OUT, "02_схема_набора.png"))
print("готово")
