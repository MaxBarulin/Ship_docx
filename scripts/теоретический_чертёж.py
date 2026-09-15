# -*- coding: utf-8 -*-
"""Теоретический чертёж в едином масштабе: бок, полуширота, корпус."""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import gorizont as G, gorizont_hydro as H

OUT = r"E:\Ship_docx\renders\горизонт_2026\расчёты"
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
os.makedirs(OUT, exist_ok=True)
INK, ACC, SEA, GRY = "#16202f", "#b02634", "#1c5c8a", "#9aa4b4"

STATIONS = [0, 10, 20, 30, 40, 50, 60, 70, 80, 90, 100, 110, 118, 124, 130, 136]
WL = [0.5 * i for i in range(1, 10)]
BUT = [1.0, 2.5, 4.0, 5.5, 7.0, 8.0]

Z_PROF = 13.2          # смещение бока по вертикали
X_BODY = 148.0         # центр корпуса по горизонтали
T = H.equilibrium()["T"]

fig, ax = plt.subplots(figsize=(34, 6.2))
ax.set_aspect("equal")
ax.axis("off")
xs = [i * 0.5 for i in range(int(G.LOA / 0.5) + 1)]


def prof_z(x, y):
    """Высота батокса y на шпангоуте x, либо None."""
    b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(x)
    if b_pal < y:
        return None
    n = int((z_brt - z_kil) / 0.01) + 1
    for k in range(n):
        z = z_kil + k * 0.01
        if H.half_breadth(x, z) >= y:
            return z
    return None


# ---- сетка шпангоутов
for x in STATIONS:
    ax.plot([x, x], [0, 9.0], color=GRY, lw=0.5)
    ax.plot([x, x], [Z_PROF, Z_PROF + 5.0], color=GRY, lw=0.5)
    ax.text(x, -0.55, str(x), ha="center", va="top", fontsize=7, color="#56627a")
ax.text(G.LOA / 2, -1.5, "шпангоуты, м от кормового перпендикуляра",
        ha="center", fontsize=8, color="#56627a")

# ---- бок: батоксы
for y in BUT:
    xx, zz = [], []
    for x in xs:
        z = prof_z(x, y)
        if z is not None:
            xx.append(x)
            zz.append(Z_PROF + z)
    if xx:
        ax.plot(xx, zz, color=INK, lw=0.8)
        ax.text(xx[0] - 0.6, zz[0], "%.1f" % y, fontsize=6.5, color=SEA,
                ha="right", va="center")
ax.plot(xs, [Z_PROF + H._station(x)[4] for x in xs], color=INK, lw=1.4)
ax.plot(xs, [Z_PROF + G.DEPTH for x in xs], color=INK, lw=1.4)
ax.plot([xs[0], xs[0]], [Z_PROF + H._station(0)[4], Z_PROF + G.DEPTH], color=INK, lw=1.4)
ax.plot([xs[-1], xs[-1]], [Z_PROF + H._station(139)[4], Z_PROF + G.DEPTH + 0.7],
        color=INK, lw=1.4)
for z in WL:
    ax.plot([0, G.LOA], [Z_PROF + z, Z_PROF + z], color="#dde2e9", lw=0.5)
ax.plot([0, G.LOA], [Z_PROF + T, Z_PROF + T], color=SEA, lw=1.2)
ax.text(1.0, Z_PROF + T + 0.18, "ВЛ %.2f м" % T, fontsize=7.5, color=SEA)
ax.text(0, Z_PROF + 5.6, "БОК — батоксы 1.0 / 2.5 / 4.0 / 5.5 / 7.0 / 8.0 м от ДП",
        fontsize=9.5, color=INK, fontweight="bold")

# ---- полуширота
for z in WL:
    yy = [H.half_breadth(x, z) for x in xs]
    ax.plot(xs, yy, color=INK, lw=0.8)
    j = next((i for i in range(len(yy)) if yy[i] > 0.05), 0)
    ax.text(xs[j] - 0.6, yy[j], "%.1f" % z, fontsize=6.5, color=SEA,
            ha="right", va="center")
ax.plot(xs, [H._station(x)[2] for x in xs], color=INK, lw=1.4)
ax.plot(xs, [H.half_breadth(x, T) for x in xs], color=SEA, lw=1.2)
ax.plot([0, G.LOA], [0, 0], color=INK, lw=1.0)
ax.text(0, 9.8, "ПОЛУШИРОТА — ватерлинии через 0.5 м, синяя — расчётная",
        fontsize=9.5, color=INK, fontweight="bold")

# ---- корпус
for x in STATIONS:
    poly = H.section_polygon(x, G.DEPTH)
    sign = 1 if x >= 70 else -1
    ys = [X_BODY + sign * abs(p[0]) for p in poly]
    zs = [Z_PROF + p[1] for p in poly]
    ax.plot(ys, zs, color=ACC if sign > 0 else INK, lw=0.9)
    ax.text(X_BODY + sign * (max(abs(v - X_BODY) for v in ys) + 0.25),
            Z_PROF + max(p[1] for p in poly) + 0.12, str(x), fontsize=6.5,
            color="#56627a", ha="left" if sign > 0 else "right")
ax.plot([X_BODY, X_BODY], [Z_PROF, Z_PROF + 5.2], color=INK, lw=1.0)
for z in WL:
    ax.plot([X_BODY - 8.6, X_BODY + 8.6], [Z_PROF + z, Z_PROF + z],
            color="#dde2e9", lw=0.5)
ax.plot([X_BODY - 8.6, X_BODY + 8.6], [Z_PROF + T, Z_PROF + T], color=SEA, lw=1.2)
ax.text(X_BODY - 8.6, Z_PROF + 5.6,
        "КОРПУС — слева кормовые, справа носовые шпангоуты",
        fontsize=9.5, color=INK, fontweight="bold")

# ---- таблица плазовых ординат
tx, ty = X_BODY - 9.0, 9.2
rows = [("L наибольшая", "139.0 м"), ("B наибольшая", "16.5 м"),
        ("Высота борта", "4.20 м"), ("Осадка расчётная", "%.2f м" % T),
        ("Водоизмещение", "%.0f т" % H.equilibrium()["D"]),
        ("Коэффициент общей полноты", "%.3f" % H.hydrostatics(T)["delta"]),
        ("Коэффициент полноты ВЛ", "%.3f" % H.hydrostatics(T)["alpha"]),
        ("Коэффициент полноты миделя", "%.3f" % H.hydrostatics(T)["beta"])]
for i, (k, v) in enumerate(rows):
    ax.text(tx, ty - i * 0.95, k, fontsize=7.5, color="#56627a")
    ax.text(tx + 15.5, ty - i * 0.95, v, fontsize=7.5, color=INK, ha="right",
            fontweight="bold")
ax.plot([tx - 0.3, tx + 15.8], [ty + 0.6, ty + 0.6], color="#c3cad5", lw=0.8)
ax.plot([tx - 0.3, tx + 15.8], [ty - len(rows) * 0.95 + 0.5,
                                ty - len(rows) * 0.95 + 0.5],
        color="#c3cad5", lw=0.8)

ax.text(0, 19.8, "ТЕОРЕТИЧЕСКИЙ ЧЕРТЁЖ  «ВОЛЖСКИЙ ГОРИЗОНТ»",
        fontsize=15, fontweight="bold", color=INK)
ax.text(0, 19.0, "Единый масштаб по всем трём проекциям. "
        "Обводы заданы таблицей шпангоутов src/lib/gorizont.py",
        fontsize=9, color="#56627a")
ax.text(X_BODY + 8.6, 19.8, "проект 2026 · УЖЦ ОСК", fontsize=9,
        color="#56627a", ha="right")
ax.set_xlim(-6, X_BODY + 10)
ax.set_ylim(-2.4, 20.6)
fig.savefig(os.path.join(OUT, "01_теоретический_чертёж.png"), dpi=200,
            bbox_inches="tight")
print("готово")
