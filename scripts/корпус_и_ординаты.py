# -*- coding: utf-8 -*-
"""Корпус (проекция «корпус») крупно + таблица плазовых ординат."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import gorizont as G, gorizont_hydro as H

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "расчёты")
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
os.makedirs(OUT, exist_ok=True)
INK, ACC, SEA, GRY = "#16202f", "#b02634", "#1c5c8a", "#9aa4b4"
ST = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 118, 124, 130, 136]
WL = [0.0, 0.5, 1.0, 1.5, 2.0, 2.5, 3.0, 3.5, 4.0, 4.2]
T = H.equilibrium()["T"]

fig = plt.figure(figsize=(16.5, 9.4))
fig.suptitle("Проекция «корпус» и таблица плазовых ординат", fontsize=16,
             fontweight="bold", x=0.012, ha="left", y=0.985)
fig.text(0.012, 0.952, "Полушироты в метрах от диаметральной плоскости. "
         "Слева кормовые шпангоуты, справа носовые", fontsize=10, color="#56627a")
fig.text(0.988, 0.968, "«Волжский Горизонт» · проект 2026 · УЖЦ ОСК",
         fontsize=10, color="#56627a", ha="right")

ax = fig.add_axes([0.03, 0.42, 0.94, 0.50])
ax.set_aspect("equal")
ax.axis("off")
for x in ST:
    poly = H.section_polygon(x, G.DEPTH)
    sign = 1 if x >= 70 else -1
    ys = [sign * abs(p[0]) for p in poly]
    zs = [p[1] for p in poly]
    ax.plot(ys, zs, color=ACC if sign > 0 else INK, lw=1.3)
    ax.text(sign * (max(abs(v) for v in ys) + 0.22), max(zs) + 0.06, str(x),
            fontsize=8, color="#56627a", ha="left" if sign > 0 else "right")
for z in WL:
    ax.plot([-8.9, 8.9], [z, z], color="#dde2e9", lw=0.7)
    ax.text(-9.1, z, "%.1f" % z, fontsize=7.5, color="#56627a", ha="right", va="center")
for y in range(-8, 9, 2):
    ax.plot([y, y], [0, 4.4], color="#eef1f5", lw=0.7)
ax.plot([-8.9, 8.9], [T, T], color=SEA, lw=1.6)
ax.text(8.95, T, " ВЛ %.2f" % T, fontsize=8.5, color=SEA, va="center")
ax.plot([0, 0], [-0.1, 4.6], color=INK, lw=1.2)
ax.text(0, 4.75, "ДП", fontsize=9, color=INK, ha="center")
ax.set_xlim(-10.4, 10.4)
ax.set_ylim(-0.35, 5.0)

# --- таблица ординат
ax2 = fig.add_axes([0.03, 0.03, 0.94, 0.34])
ax2.axis("off")
cols = ["z, м"] + [str(x) for x in ST]
rows = []
for z in WL:
    rows.append(["%.1f" % z] + ["%.2f" % H.half_breadth(x, z) for x in ST])
tbl = ax2.table(cellText=rows, colLabels=cols, loc="upper center",
                cellLoc="center", colLoc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(8.5)
tbl.scale(1, 1.32)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#c8cfd9")
    cell.set_linewidth(0.6)
    if r == 0:
        cell.set_facecolor("#eef1f5")
        cell.set_text_props(fontweight="bold", color=INK)
    elif c == 0:
        cell.set_facecolor("#f6f8fa")
        cell.set_text_props(fontweight="bold", color=INK)
ax2.text(0.0, 1.02, "Таблица плазовых ординат: полуширота, м — строки по высоте, "
         "столбцы по шпангоутам, м от кормового перпендикуляра",
         transform=ax2.transAxes, fontsize=9.5, color="#56627a")
fig.savefig(os.path.join(OUT, "01б_корпус_и_ординаты.png"), dpi=165,
            bbox_inches="tight")
print("готово")
