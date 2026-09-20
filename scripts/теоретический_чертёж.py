# -*- coding: utf-8 -*-
"""Теоретический чертёж: бок, полуширота, корпус — в одном масштабе.

Все три проекции строятся из одной функции обвода (gorizont_hydro.half_breadth),
то есть из той же геометрии, что и плазовая таблица и модель в Blender.
Шпангоуты — 25 теоретических сечений (20 основных через L/20 = 6,95 м и
полушпангоуты 0,5 / 1,5 / 18,5 / 19,5 в оконечностях, где обвод меняется
быстрее всего). Ватерлинии — 13 отметок плазовой таблицы, батоксы — через 1 м.

Правило чтения: на боку кривые суть батоксы, на полушироте — ватерлинии,
на корпусе — шпангоуты; остальные линии на каждой проекции прямые.
"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import gorizont as G, gorizont_hydro as H

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "расчёты")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
INK, ACC, SEA, GRY = "#16202f", "#b02634", "#1c5c8a", "#9aa4b4"
FRAMES = [r[0] for r in G.OFFSETS]
FX = {r[0]: r[1] for r in G.OFFSETS}
WL = list(G.WATERLINES)
BUT = [1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0, 8.0]
D = G.DEPTH
Y_PROF = 11.6
X_BODY = 156.0
XS = [i * 0.25 for i in range(int(G.LOA / 0.25) + 1)]


def buttock_z(x, y):
    """Высота батокса y на шпангоуте x, либо None."""
    zk, bk, zb, bb, phi = H._column(x)
    if bb < y:
        return None
    if bk >= y:
        return zk
    lo, hi = zk, zb
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if H.half_breadth(x, mid) < y:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def draw():
    fig, ax = plt.subplots(figsize=(35.4, 9.6))
    ax.set_aspect("equal")
    ax.axis("off")

    # ---------------------------------------------------------------- БОК --
    for z in WL:
        ax.plot([0, G.LOA], [Y_PROF + z] * 2, color=GRY, lw=0.35, zorder=1)
        ax.text(-1.2, Y_PROF + z, "%.1f" % z, ha="right", va="center",
                fontsize=6, color="#56627a")
    for n in FRAMES:
        x = FX[n]
        zk = H.keel_height(x)
        ax.plot([x, x], [Y_PROF + zk, Y_PROF + D], color=GRY, lw=0.45, zorder=1)
    ax.plot(XS, [Y_PROF + H.keel_height(x) for x in XS], color=INK, lw=1.5,
            zorder=4)
    ax.plot([0, G.LOA], [Y_PROF + D] * 2, color=INK, lw=1.5, zorder=4)
    ax.plot(XS, [Y_PROF + min(H.side_height(x), 4.90) for x in XS], color=INK,
            lw=0.9, ls=(0, (6, 3)), zorder=4)
    ax.plot([0, 0], [Y_PROF + H.keel_height(0), Y_PROF + D], color=INK, lw=1.5)
    ax.plot([G.LOA, G.LOA], [Y_PROF + H.keel_height(G.LOA), Y_PROF + 4.90],
            color=INK, lw=1.5)
    for y in BUT:
        xx, zz = [], []
        last = None
        for x in XS:
            z = buttock_z(x, y)
            if z is None:
                if xx:
                    ax.plot(xx, zz, color=SEA, lw=0.8, zorder=3)
                    last = (xx[-1], zz[-1])
                    xx, zz = [], []
                continue
            xx.append(x)
            zz.append(Y_PROF + z)
        if xx:
            ax.plot(xx, zz, color=SEA, lw=0.8, zorder=3)
            last = (xx[-1], zz[-1])
        if last:
            ax.text(last[0] + 0.7, last[1], "%g" % y, color=SEA, fontsize=6,
                    va="center")
    ax.text(G.LOA / 2, Y_PROF + 5.6, "БОК  —  кривые суть батоксы",
            ha="center", fontsize=10, color=INK, weight="bold")

    # -------------------------------------------------------- ПОЛУШИРОТА --
    ax.plot([0, G.LOA], [0, 0], color=INK, lw=1.2, zorder=4)
    for n in FRAMES:
        x = FX[n]
        ax.plot([x, x], [0, H.half_breadth(x, D)], color=GRY, lw=0.45, zorder=1)
        ax.text(x, -0.75, "%g" % n, ha="center", va="top", fontsize=6.5,
                color=INK)
    for y in BUT:
        ax.plot([0, G.LOA], [y, y], color=GRY, lw=0.35, zorder=1)
        ax.text(-1.2, y, "%g" % y, ha="right", va="center", fontsize=6,
                color="#56627a")
    for z in WL:
        xx, yy = [], []
        for x in XS:
            if z < H.keel_height(x) - 1e-9:
                if xx:
                    ax.plot(xx, yy, color=SEA, lw=0.8, zorder=3)
                    xx, yy = [], []
                continue
            xx.append(x)
            yy.append(H.half_breadth(x, z))
        if xx:
            ax.plot(xx, yy, color=SEA, lw=0.8, zorder=3)
    ax.plot(XS, [H.half_breadth(x, D) for x in XS], color=INK, lw=1.5, zorder=4)
    ax.text(G.LOA / 2, -2.4,
            "ПОЛУШИРОТА  —  кривые суть ватерлинии; цифры внизу суть номера "
            "теоретических шпангоутов", ha="center", fontsize=10, color=INK,
            weight="bold")

    # ------------------------------------------------------------- КОРПУС --
    for z in WL:
        ax.plot([X_BODY - 8.9, X_BODY + 8.9], [Y_PROF + z] * 2, color=GRY,
                lw=0.35, zorder=1)
    for y in BUT:
        for s in (1, -1):
            ax.plot([X_BODY + s * y] * 2, [Y_PROF, Y_PROF + D], color=GRY,
                    lw=0.35, zorder=1)
    ax.plot([X_BODY] * 2, [Y_PROF - 0.5, Y_PROF + 5.4], color=INK, lw=0.8,
            ls=(0, (7, 3, 1, 3)), zorder=2)
    ax.plot([X_BODY - 8.9, X_BODY + 8.9], [Y_PROF] * 2, color=INK, lw=0.8,
            zorder=2)
    for n in FRAMES:
        x = FX[n]
        s = -1 if n < 10 else 1
        pts = H.profile(x)
        xx = [X_BODY] + [X_BODY + s * p[1] for p in pts] + [X_BODY]
        zz = [Y_PROF + pts[0][0]] + [Y_PROF + p[0] for p in pts] + [Y_PROF + D]
        lw = 1.15 if float(n) == int(n) else 0.7
        ax.plot(xx, zz, color=ACC if n in (0, 10, 20) else SEA, lw=lw, zorder=3)
        ax.text(X_BODY + s * (H.half_breadth(x, D) + 0.28), Y_PROF + D + 0.14,
                "%g" % n, ha="center", va="bottom", fontsize=5.6, color=INK)
    ax.text(X_BODY, Y_PROF + 5.6, "КОРПУС  —  кривые суть шпангоуты",
            ha="center", fontsize=10, color=INK, weight="bold")
    ax.text(X_BODY - 4.6, Y_PROF - 1.1, "кормовые", ha="center", fontsize=7,
            color="#56627a")
    ax.text(X_BODY + 4.6, Y_PROF - 1.1, "носовые", ha="center", fontsize=7,
            color="#56627a")

    # ------------------------------------------------------------ подписи --
    e = H.equilibrium()
    ax.text(0, Y_PROF + 7.4,
            "«ВОЛЖСКИЙ ГОРИЗОНТ» — ТЕОРЕТИЧЕСКИЙ ЧЕРТЁЖ", fontsize=13,
            color=INK, weight="bold")
    ax.text(0, Y_PROF + 6.55,
            "L = %.1f м   B = %.2f м   H = %.2f м   T = %.2f м   "
            "теоретическая шпация L/20 = %.2f м   ватерлинии 0,00…4,20 м   "
            "батоксы через 1,00 м" % (G.LOA, G.BEAM, D, e["T"], G.LOA / 20),
            fontsize=9, color="#56627a")
    ax.text(0, -3.7,
            "Обвод: плоское днище, скуловая дуга, касательная к днищу и к "
            "борту, прямой борт с развалом — см. таблицу плазовых ординат. "
            "Штриховая линия на боку суть верхняя кромка фальшборта.",
            fontsize=8.5, color="#56627a")
    ax.set_xlim(-6, X_BODY + 12)
    ax.set_ylim(-4.8, Y_PROF + 8.4)
    p = os.path.join(OUT, "01_теоретический_чертёж.png")
    fig.savefig(p, dpi=170, bbox_inches="tight", pad_inches=0.25)
    plt.close(fig)
    return p


if __name__ == "__main__":
    print(draw())
