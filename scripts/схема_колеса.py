# -*- coding: utf-8 -*-
"""Схема гребного колеса - шарнирная плица против радиальной, вид с борта.

    python scripts/схема_колеса.py

Один лист, два колеса в одном положении, как рисунок в учебнике: чёрные линии,
плицы - чёрные полосы, вода - линия ватерлинии с условной штриховкой.
Слева - как построено - механизм Моргана, плицы в воде отвесны, наверху откинуты
наружу. Справа - жёсткое радиальное колесо, плицы смотрят от оси. Углы входа и
выхода - строкой под своей схемой: это и есть разница в ударе и КПД, из-за
которой узел выбран шарнирным. Числа - из библиотек колеса и надстройки.
"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Circle, Polygon, FancyArrowPatch

from lib import gorizont as G, gorizont_wheel as W, gorizont_super as SU
from lib import plain as P

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "схемы")
os.makedirs(OUT, exist_ok=True)

ЧЁРН = "black"
ШТРИХПУНКТИР = (0, (8, 2.5, 1.2, 2.5))
X_ЛЕВ, X_ПРАВ, Z_НИЗ, Z_ВЕРХ = -4.35, 4.0, -0.35, 6.05     # м от оси колеса и от ОП
X_ПОДП = 2.65                                               # левый край подписей-выносок справа
ШРИФТ = 9.5


def _градусы(v):
    """Угол с запятой, минус - дефисом: «-8,6°», «0°»."""
    return ("%s°" % P.ч(v, 1)) if abs(v - round(v)) > 0.05 else "%d°" % round(v)


def _плица(ax, px, pz, dx, dz, длина):
    x1, z1 = px + dx * длина, pz + dz * длина
    t = W.BLADE_THICK
    nx, nz = -dz * t, dx * t
    ax.add_patch(Polygon([(px + nx, pz + nz), (x1 + nx, z1 + nz), (x1 - nx, z1 - nz), (px - nx, pz - nz)],
                         closed=True, facecolor=ЧЁРН, edgecolor=ЧЁРН, lw=0.3, zorder=4))
    return x1, z1


def _выноска(ax, точка, текст, куда):
    """Подпись справа от колеса: точка на детали, тонкая линия до левого края подписи."""
    ax.plot([точка[0]], [точка[1]], marker="o", ms=2.4, color=ЧЁРН, zorder=9)
    ax.plot([точка[0], куда[0] - 0.05], [точка[1], куда[1]], color=ЧЁРН, lw=0.5, zorder=9)
    ax.text(куда[0], куда[1], текст, ha="left", va="center", fontsize=ШРИФТ, linespacing=1.1, zorder=9)


def колесо(ax, шарнирное):
    z0 = W.axis_height(G.DRAFT)
    Rп, h = W.PIVOT_RADIUS, W.BLADE_HEIGHT
    ax.set_aspect("equal")
    ax.set_xlim(X_ЛЕВ, X_ПРАВ)
    ax.set_ylim(Z_НИЗ, Z_ВЕРХ)
    ax.axis("off")

    # уровни - тонкие штрихпунктирные линии, подпись над линией у левого края
    к = SU.кожух()
    палуба = G.DECKS["главная"]
    уровни = [(к["z1"], "лист кожуха %s" % P.ч(к["z1"], 2)),
              (палуба, "главная палуба %s" % P.ч(палуба, 2)),
              (0.0, "основная плоскость")]
    for z, подпись in уровни:
        ax.plot([X_ЛЕВ, X_ПРАВ], [z, z], color=ЧЁРН, lw=0.5, ls=ШТРИХПУНКТИР, zorder=1)
        ax.text(X_ЛЕВ + 0.05, z + 0.07, подпись, ha="left", va="bottom", fontsize=ШРИФТ, zorder=6)
    if abs(палуба - z0) >= 0.005:
        ax.plot([-0.5, 0.5], [z0, z0], color=ЧЁРН, lw=0.5, ls=ШТРИХПУНКТИР, zorder=1)

    # вода - линия ватерлинии и условная штриховка под ней у левого края
    T = G.DRAFT
    ax.plot([X_ЛЕВ, X_ПРАВ], [T, T], color=ЧЁРН, lw=0.8, zorder=1)
    ax.text(X_ЛЕВ + 0.05, T + 0.07, "ватерлиния %s" % P.ч(T, 2), ha="left", va="bottom", fontsize=ШРИФТ, zorder=6)
    for k, (a, b) in enumerate([(0.0, 1.3), (0.2, 1.0), (0.4, 0.7)]):
        z = T - 0.13 * (k + 1)
        ax.plot([X_ЛЕВ + 0.05 + a, X_ЛЕВ + 0.05 + b], [z, z], color=ЧЁРН, lw=0.5, zorder=1)

    # обод, ступица, спицы
    ax.add_patch(Circle((0, z0), Rп + W.RIM_OUT, fill=False, ec=ЧЁРН, lw=1.0, zorder=3))
    ax.add_patch(Circle((0, z0), Rп - W.RIM_IN, fill=False, ec=ЧЁРН, lw=0.6, zorder=3))
    ax.add_patch(Circle((0, z0), W.HUB_RADIUS, facecolor="white", ec=ЧЁРН, lw=0.8, zorder=3))
    ax.plot([0], [z0], marker="+", ms=5, mew=0.6, color=ЧЁРН, zorder=4)
    for i in range(W.BLADES):
        a = 2 * math.pi * (i + 0.5) / W.BLADES
        ax.plot([W.HUB_RADIUS * math.cos(a), (Rп - W.RIM_IN) * math.cos(a)],
                [z0 + W.HUB_RADIUS * math.sin(a), z0 + (Rп - W.RIM_IN) * math.sin(a)], color=ЧЁРН, lw=0.6, zorder=2)

    # плицы - чёрные полосы, оси плиц - белые кружки
    концы = {}
    for п in W.blade_positions(G.DRAFT):
        a = math.radians(п["a"])
        if шарнирное:
            dx, dz = W.blade_direction(a)
        else:
            dx, dz = math.cos(a), math.sin(a)          # радиально наружу от оси
        концы[п["i"]] = _плица(ax, п["x"], п["z"], dx, dz, W.PIVOT_OFFSET + h)
        ax.add_patch(Circle((п["x"], п["z"]), 0.06, facecolor="white", ec=ЧЁРН, lw=0.7, zorder=5))

    # механизм Моргана - только у шарнирного: кривошип на оси плицы и тяга к эксцентрику
    if шарнирное:
        ex, ez = W.eccentric_centre()
        for п in W.blade_positions(G.DRAFT):
            ax.plot([п["x"], п["Qx"]], [п["z"], п["Qz"]], color=ЧЁРН, lw=1.1, zorder=6, solid_capstyle="round")
            ax.plot([п["Qx"], ex], [п["Qz"], z0 + ez], color=ЧЁРН, lw=0.45, zorder=5)
        ax.add_patch(Circle((ex, z0 + ez), W.ECC_BOSS, facecolor="white", ec=ЧЁРН, lw=0.8, zorder=7))
        # выноски справа, сверху вниз: тяга плицы на 60°, плица на 30°, эксцентрик, кривошип плицы на 0°.
        # Точки выбраны так, чтобы линии проходили мимо плиц и кривошипов и не пересекались
        п0, п1, п2 = (next(п for п in W.blade_positions(G.DRAFT) if п["i"] == i) for i in (0, 1, 2))
        x1, z1 = концы[1]
        _выноска(ax, (п2["Qx"] + 0.38 * (ex - п2["Qx"]), п2["Qz"] + 0.38 * (z0 + ez - п2["Qz"])), "тяга",
                 (X_ПОДП, z0 + 2.35))
        _выноска(ax, (п1["x"] + 0.7 * (x1 - п1["x"]), п1["z"] + 0.7 * (z1 - п1["z"])),
                 "плица\n%s × %s м" % (P.ч(W.BLADE_SPAN, 2), P.ч(W.BLADE_HEIGHT, 2)), (X_ПОДП, z0 + 1.6))
        _выноска(ax, (ex, z0 + ez), "неподвижный\nэксцентрик", (X_ПОДП, z0 + 0.85))
        _выноска(ax, (п0["x"] + 0.65 * (п0["Qx"] - п0["x"]), п0["z"] + 0.65 * (п0["Qz"] - п0["z"])), "кривошип",
                 (X_ПОДП, z0 - 0.35))
    else:
        п1 = next(п for п in W.blade_positions(G.DRAFT) if п["i"] == 1)
        x1, z1 = концы[1]
        _выноска(ax, (п1["x"] + 0.6 * (x1 - п1["x"]), п1["z"] + 0.6 * (z1 - п1["z"])), "плица", (X_ПОДП, z0 + 1.6))

    # направление вращения - дуга со стрелкой по часовой стрелке над колесом слева
    R = Rп + W.PIVOT_OFFSET + h + 0.25
    a0, a1 = math.radians(150.0), math.radians(118.0)
    ax.add_patch(FancyArrowPatch((R * math.cos(a0), z0 + R * math.sin(a0)), (R * math.cos(a1), z0 + R * math.sin(a1)),
                                 connectionstyle="arc3,rad=-0.12", arrowstyle="-|>", mutation_scale=9,
                                 color=ЧЁРН, lw=0.7, zorder=6))
    # ход судна - в нос, вправо
    zх = 0.5 * T
    ax.add_patch(FancyArrowPatch((X_ПОДП, zх), (X_ПРАВ - 0.1, zх), arrowstyle="-|>", mutation_scale=9, color=ЧЁРН,
                                 lw=0.7, zorder=6))
    ax.text(0.5 * (X_ПОДП + X_ПРАВ - 0.1), zх + 0.08, "ход судна", ha="center", va="bottom", fontsize=ШРИФТ, zorder=6)


def подписи(шарнирное):
    f = W.feathering_sweep()
    дуга, _, _ = W.immersion_arc()
    if шарнирное:
        return ("а) шарнирные плицы, механизм Моргана",
                "вход %s, низ %s, выход %s от отвеса," % (_градусы(f["вход"]), _градусы(f["низ"]), _градусы(f["выход"])),
                "наверху плица откинута наружу на %d°" % round(abs(f["верх"]) - 90.0))
    return ("б) жёсткие радиальные плицы",
            "вход %s, низ 0°, выход %s от отвеса," % (_градусы(дуга / 2.0), _градусы(-дуга / 2.0)),
            "плица входит в воду плашмя и на выходе поднимает воду")


def build(verbose=True):
    with P.word():
        ШИР, зазор, низ_схем = 9.6, 0.15, 0.82         # дюймы, внизу - место под подписи
        w_ax = (ШИР - 3 * зазор) / 2.0
        h_ax = w_ax * (Z_ВЕРХ - Z_НИЗ) / (X_ПРАВ - X_ЛЕВ)
        ВЫС = низ_схем + h_ax + 0.05
        fig = plt.figure(figsize=(ШИР, ВЫС))
        for k, шарнирное in enumerate((True, False)):
            x_in = зазор + k * (w_ax + зазор)
            ax = fig.add_axes([x_in / ШИР, низ_схем / ВЫС, w_ax / ШИР, h_ax / ВЫС])
            колесо(ax, шарнирное)
            заг, с1, с2 = подписи(шарнирное)
            xc = (x_in + w_ax / 2.0) / ШИР
            fig.text(xc, (низ_схем - 0.12) / ВЫС, заг, ha="center", va="top", fontsize=11)
            fig.text(xc, (низ_схем - 0.42) / ВЫС, с1 + "\n" + с2, ha="center", va="top", fontsize=10, linespacing=1.2)
        p = P.сохранить(fig, os.path.join(OUT, "01_колесо_шарнирное_и_радиальное.png"))
        plt.close(fig)
    if verbose:
        print("  ", os.path.basename(p))
    return p


if __name__ == "__main__":
    build()
