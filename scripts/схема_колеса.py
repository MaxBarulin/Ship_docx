# -*- coding: utf-8 -*-
"""Схема гребного колеса - шарнирная плица против радиальной, вид с борта.

    python scripts/схема_колеса.py

Один лист, два колеса в одном положении. Слева - как построено - механизм
Моргана, плицы в воде отвесны, наверху откинуты наружу. Справа - жёсткое
радиальное колесо, плицы смотрят от оси. Углы входа и выхода подписаны:
это и есть разница в ударе и КПД, из-за которой узел выбран шарнирным.
"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Rectangle, Polygon

from lib import gorizont as G, gorizont_wheel as W, gorizont_super as SU

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "схемы")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"axes.unicode_minus": False, "font.family": "DejaVu Sans", "font.size": 8,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
INK, GRY, ACC, SEA, WATER = "#16202f", "#8a94a6", "#b02634", "#1c5c8a", "#d8e8f2"


def колесо(ax, шарнирное, заголовок):
    z0 = W.axis_height(G.DRAFT)
    Rп, h = W.PIVOT_RADIUS, W.BLADE_HEIGHT
    ax.set_aspect("equal")
    ax.set_xlim(-3.6, 3.6)
    ax.set_ylim(-0.3, 6.2)
    ax.axis("off")
    # вода, палуба, кожух
    ax.add_patch(Rectangle((-3.6, -0.3), 7.2, G.DRAFT + 0.3, facecolor=WATER, edgecolor="none", zorder=0))
    ax.axhline(G.DRAFT, color=SEA, lw=0.8)
    ax.text(3.5, G.DRAFT + 0.08, "ватерлиния", ha="right", fontsize=7, color=SEA)
    ax.axhline(G.DECKS["главная"], color=GRY, lw=0.8, ls="--")
    ax.text(-3.5, G.DECKS["главная"] + 0.08, "главная палуба 3,00", fontsize=7, color=GRY)
    к = SU.кожух()
    ax.axhline(к["z1"], color=GRY, lw=0.8, ls="--")
    ax.text(-3.5, к["z1"] + 0.08, "лист кожуха %.2f" % к["z1"], fontsize=7, color=GRY)
    ax.axhline(0.0, color=INK, lw=1.2)
    ax.text(3.5, 0.06, "основная плоскость", ha="right", fontsize=7, color=INK)
    # обод и спицы
    ax.add_patch(Circle((0, z0), Rп + W.RIM_OUT, fill=False, ec=INK, lw=1.4, zorder=3))
    ax.add_patch(Circle((0, z0), Rп - W.RIM_IN, fill=False, ec=INK, lw=0.8, zorder=3))
    ax.add_patch(Circle((0, z0), W.HUB_RADIUS, facecolor="#d0d4d9", ec=INK, lw=0.8, zorder=3))
    for i in range(W.BLADES):
        a = 2 * math.pi * (i + 0.5) / W.BLADES
        ax.plot([W.HUB_RADIUS * math.cos(a), (Rп - W.RIM_IN) * math.cos(a)],
                [z0 + W.HUB_RADIUS * math.sin(a), z0 + (Rп - W.RIM_IN) * math.sin(a)], color=INK, lw=0.9, zorder=2)
    # плицы
    for п in W.blade_positions(G.DRAFT):
        a = math.radians(п["a"])
        px, pz = п["x"], п["z"]
        if шарнирное:
            dx, dz = W.blade_direction(a)
        else:
            dx, dz = math.cos(a), math.sin(a)          # радиально наружу от оси
        x1, z1 = px + dx * (W.PIVOT_OFFSET + h), pz + dz * (W.PIVOT_OFFSET + h)
        nx, nz = -dz * 0.035, dx * 0.035
        ax.add_patch(Polygon([(px + nx, pz + nz), (x1 + nx, z1 + nz), (x1 - nx, z1 - nz), (px - nx, pz - nz)],
                             closed=True, facecolor=ACC, edgecolor="#7a0a1c", lw=0.5, zorder=4))
        ax.add_patch(Circle((px, pz), 0.06, facecolor="white", ec=INK, lw=0.7, zorder=5))
    # механизм - только у шарнирного
    if шарнирное:
        ex, ez = W.eccentric_centre()
        ax.add_patch(Circle((ex, z0 + ez), W.ECC_BOSS, facecolor="#bfc5cc", ec=INK, lw=0.8, zorder=5))
        ax.text(ex + 0.22, z0 + ez, "неподвижный\nэксцентрик", fontsize=6.5, color=INK, va="center")
        for п in W.blade_positions(G.DRAFT):
            ax.plot([п["x"], п["Qx"]], [п["z"], п["Qz"]], color=SEA, lw=1.2, zorder=6)     # кривошип
            ax.plot([п["Qx"], ex], [п["Qz"], z0 + ez], color=GRY, lw=0.7, zorder=5)     # тяга
    # углы
    f = W.feathering_sweep()
    дуга, _, _ = W.immersion_arc()
    if шарнирное:
        подп = "вход %.1f°, низ %.1f°, выход %.1f° от отвеса\nнаверху плица откинута наружу на %.0f°" % (
            f["вход"], f["низ"], f["выход"], abs(f["верх"]) - 90.0)
    else:
        подп = "вход %.0f°, низ 0°, выход %.0f° от отвеса\nкоэффициент удара 3,0 против 1,1" % (дуга / 2.0, -дуга / 2.0)
    ax.set_title(заголовок, fontsize=10, color=INK, loc="left")
    ax.text(0.0, -0.22, подп, ha="center", va="top", fontsize=7.5, color=INK,
            bbox=dict(boxstyle="round,pad=0.3", fc="white", ec=GRY))
    ax.annotate("ход →", (2.4, z0 - Rп - 0.35), fontsize=8, color=INK)


def build(verbose=True):
    fig, (a1, a2) = plt.subplots(1, 2, figsize=(13, 7.2), dpi=140)
    колесо(a1, True, "Как построено - шарнирные плицы, механизм Моргана")
    колесо(a2, False, "Для сравнения - жёсткие радиальные плицы")
    fig.suptitle("Гребное колесо Ø%.2f м, %d плиц %.2f x %.2f м, ось на %.2f м над ОП" % (
        W.DIAMETER, W.BLADES, W.BLADE_SPAN, W.BLADE_HEIGHT, W.axis_height(G.DRAFT)),
        fontsize=11, fontweight="bold", color=INK, x=0.02, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    p = os.path.join(OUT, "01_колесо_шарнирное_и_радиальное.png")
    fig.savefig(p)
    plt.close(fig)
    if verbose:
        print("  ", os.path.basename(p))
    return p


if __name__ == "__main__":
    build()
