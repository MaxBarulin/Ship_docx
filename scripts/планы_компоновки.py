# -*- coding: utf-8 -*-
"""Планы палуб из компоновки — стадия проектирования, без Blender.

    python scripts/планы_компоновки.py

Пять листов: второе дно (цистерны), трюм, главная, средняя, солнечная.
Обвод берётся из `gorizont_lines` и `gorizont_super`, зоны и каюты — из
`gorizont_ga`. Всё, что на листе, посчитано; ни одна линия не нарисована
руками. Поэтому план — это и есть задание на модель: что здесь, то и
собирать.
"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Polygon, FancyBboxPatch

from lib import gorizont as G, gorizont_lines as L, gorizont_super as SU
from lib import gorizont_ga as GA, gorizont_public as PB, gorizont_wheel as W, gorizont_facade as F
from lib import gorizont_modules as MOD

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "планы")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
INK, GRY, ACC, SEA = "#16202f", "#8a94a6", "#b02634", "#1c5c8a"
ЦВЕТ = {"tech": "#e6e9ee", "service": "#efe7d6", "public": "#dfeee4",
        "cabins": "#e9e2ef", "open": "#f6f6f4", "trunk": "#cfd9e6", "garage": "#e5e5e0"}
КАТ = {"люкс": "#d9c2a6", "бизнес": "#e6d3bd", "стандарт": "#efe1d0",
       "эконом": "#f3ece3", "экипаж": "#dfe3e8"}


def обвод(палуба):
    """Контур палубы в плане: [(x, y), …] по часовой."""
    if палуба in ("второе дно", "трюм"):
        xs = [i * 1.0 for i in range(int(G.LOA) + 1)]
        пб = [(x, L.side_half(x) - (0.0 if палуба == "трюм" else 0.0)) for x in xs]
    elif палуба == "солнечная":
        пб = [(x, SU.полуширота(x, "средняя", z=G.DECKS["солнечная"] - 0.01) + SU.КАРНИЗ)
              for x, _ in SU.обвод("средняя", 0.5)]
    else:
        ярус = "главная" if палуба == "главная" else "средняя"
        пб = [(x, SU.полуширота(x, ярус, z=G.DECKS[палуба] + 0.6)) for x, _ in SU.обвод(ярус, 0.5)]
    пб = [(x, y) for x, y in пб if y > 0.05]
    return пб + [(x, -y) for x, y in reversed(пб)]


def _полу(палуба, x):
    if палуба in ("второе дно", "трюм"):
        return L.side_half(x)
    if палуба == "солнечная":
        return SU.полуширота(x, "средняя", z=G.DECKS["солнечная"] - 0.01)
    ярус = "главная" if палуба == "главная" else "средняя"
    return SU.полуширота(x, ярус, z=G.DECKS[палуба] + 0.6)


def _зона(ax, палуба, x0, x1, цвет, кромка=GRY):
    """Заливка зоны по обводу, а не прямоугольником."""
    xs = [x0 + (x1 - x0) * i / 24.0 for i in range(25)]
    верх = [(x, _полу(палуба, x)) for x in xs]
    верх = [(x, y) for x, y in верх if y > 0.05]
    if len(верх) < 2:
        return
    ax.add_patch(Polygon(верх + [(x, -y) for x, y in reversed(верх)], closed=True,
                         facecolor=цвет, edgecolor=кромка, lw=0.6, zorder=1))


def лист(палуба, заголовок, подпись):
    fig = plt.figure(figsize=(22, 6.4), dpi=140)
    ax = fig.add_axes([0.02, 0.10, 0.96, 0.78])
    ax.set_aspect("equal")
    ax.set_xlim(-3, G.LOA + 3)
    ax.set_ylim(-13.0, 13.0)
    ax.axis("off")
    к = обвод(палуба)
    ax.add_patch(Polygon(к, closed=True, facecolor="white", edgecolor=INK, lw=1.2, zorder=0))

    # --- зоны
    if палуба == "второе дно":
        k = 0
        for t in G.TANKS:
            if t["z1"] > 1.0:
                continue
            xc = (t["x0"] + t["x1"]) / 2.0
            if "y0" in t:
                ax.add_patch(Rectangle((t["x0"], t["y0"]), t["x1"] - t["x0"], t["y1"] - t["y0"],
                                       facecolor="#dbe7f0", edgecolor=GRY, lw=0.6, zorder=1))
                ax.text(xc, (t["y0"] + t["y1"]) / 2.0, "%s %.0f м³" % (t["code"], t["vol"]),
                        ha="center", va="center", fontsize=6.0, color=INK, zorder=5)
                if t["y0"] < 0:
                    continue
                ax.text(xc, 8.6, t["name"].replace(" ПБ", "").replace(" ЛБ", "") + " (ЛБ/ПБ)",
                        ha="center", va="center", fontsize=6.0, color=INK, zorder=5)
                continue
            _зона(ax, палуба, t["x0"], t["x1"], "#dbe7f0")
            метка = "%s\n%s\n%.0f м³" % (t["code"], t["name"], t["vol"])
            if t["x1"] - t["x0"] >= 8.0:
                ax.text(xc, 0.0, метка, ha="center", va="center", fontsize=6.0, color=INK, zorder=5)
            else:
                верх = k % 2 == 0
                k += 1
                yт = 9.9 if верх else -9.9
                ax.plot([xc, xc], [_полу("трюм", xc) * (1 if верх else -1), yт * 0.93], color=GRY, lw=0.5)
                ax.text(xc, yт, метка, ha="center", va="bottom" if верх else "top",
                        fontsize=5.8, color=INK, zorder=6)
        ax.axhline(G.LONG_BULKHEAD_Y, color=GRY, lw=0.6, ls="--")
        ax.axhline(-G.LONG_BULKHEAD_Y, color=GRY, lw=0.6, ls="--")
    else:
        import textwrap
        снаружи = 0
        for z in GA.ЗОНЫ.get(палуба, []):
            x0, x1, тип, имя, прим = z
            _зона(ax, палуба, x0, x1, ЦВЕТ[тип])
            if тип == "cabins":
                continue
            xc = (x0 + x1) / 2.0
            # на солнечной палубе середину занимают слоты модулей — подписи всех зон на выносках
            if x1 - x0 >= 11.0 and тип != "trunk" and палуба != "солнечная":
                ш = max(10, int((x1 - x0) / 0.55))
                ax.text(xc, 0.0, "\n".join(textwrap.wrap(имя, ш)), ha="center", va="center",
                        fontsize=6.2, color=INK, zorder=5,
                        bbox=dict(boxstyle="round,pad=0.25", fc="white", ec="none", alpha=0.8))
            else:
                верх = снаружи % 2 == 0
                снаружи += 1
                yт = 9.9 if верх else -9.9
                yк = _полу(палуба, xc)
                ax.plot([xc, xc], [yк if верх else -yк, yт * 0.93], color=GRY, lw=0.5, zorder=5)
                ax.text(xc, yт, "\n".join(textwrap.wrap(имя, 28)), ha="center",
                        va="bottom" if верх else "top", fontsize=6.0, color=INK, zorder=6)
    # --- каюты
    if палуба in ("главная", "средняя"):
        for c in GA.расстановка():
            if c["палуба"] != палуба:
                continue
            y0, y1 = sorted((c["y0"], c["y1"]))
            ax.add_patch(Rectangle((c["x0"], y0), c["x1"] - c["x0"], y1 - y0,
                                   facecolor=КАТ[c["категория"]], edgecolor=INK, lw=0.5, zorder=3))
            метка = {"люкс": "Л", "бизнес": "Б", "стандарт": "С", "эконом": "Э", "экипаж": "Эк"}[c["категория"]]
            if c["тип"] == "семейная":
                метка = "Сем"
            if c["М4"]:
                метка += " М4"
            ax.text((c["x0"] + c["x1"]) / 2.0, (y0 + y1) / 2.0, "%s\n%d" % (метка, c["мест"]),
                    ha="center", va="center", fontsize=5.6, color=INK, zorder=4)
        # коридоры
        for x0, x1, тип, имя, _ in GA.ЗОНЫ[палуба]:
            if тип == "cabins":
                for s in (1, -1):
                    yb = _полу(палуба, (x0 + x1) / 2.0) - G.LINING / 2.0 - GA.ГЛУБИНА_БОРТ
                    ax.add_patch(Rectangle((x0, s * yb - (GA.КОРИДОР if s > 0 else 0.0)),
                                           x1 - x0, GA.КОРИДОР, facecolor="#fbfbf7",
                                           edgecolor="none", zorder=2))
        # трапы и лифты
        for имя, (a, b) in GA.ТРАПЫ.items():
            ax.add_patch(Rectangle((a, -1.6), b - a, 3.2, facecolor="none", edgecolor=SEA,
                                   lw=1.0, hatch="///", zorder=4))
            ax.text((a + b) / 2.0, -2.6, "трап " + имя, ha="center", va="top", fontsize=6, color=SEA)
        for имя, (a, b, y0, y1) in GA.ЛИФТЫ.items():
            ax.add_patch(Rectangle((a, y0), b - a, y1 - y0, facecolor=SEA, edgecolor="none", zorder=4))
    # --- мебель и выгородки общественных помещений, проёмы переборок, колодцы
    ЦВЕТ_МЕБ = {"стол": "#8c6d3f", "стул": "#b39b6f", "диван": "#9a7b4f", "кресло": "#9a7b4f", "стойка": "#5f4b2e",
            "сцена": "#c9b8a0", "шкаф": "#6b5a3e", "оборудование": "#8d97a6", "стена": INK, "шезлонг": "#c2a878",
            "тренажёр": "#8d97a6", "кабина": "#b58a5a", "лежак": "#c2a878", "витрина": SEA, "шахта": "#555555",
            "ограждение": SEA, "киоск": "#8d97a6", "скамья": "#9a7b4f"}
    for p in PB.мебель(палуба):
        кл = p["класс"]
        ax.add_patch(Rectangle((p["x0"], p["y0"]), p["x1"] - p["x0"], p["y1"] - p["y0"],
                               facecolor=ЦВЕТ_МЕБ.get(кл, "#999999") if кл not in ("стена", "ограждение") else "none",
                               edgecolor=ЦВЕТ_МЕБ.get(кл, INK), lw=1.0 if кл in ("стена", "ограждение") else 0.3, zorder=5))
    if палуба in ("главная", "средняя"):
        границы = sorted({z[0] for z in GA.ЗОНЫ[палуба]} | {z[1] for z in GA.ЗОНЫ[палуба]})
        for x in границы:
            for y0, y1 in PB.проёмы_переборки(палуба, x):
                ax.plot([x, x], [y0, y1], color="white", lw=2.2, zorder=6, solid_capstyle="butt")
                ax.plot([x - 0.25, x + 0.25], [y0, y0], color=INK, lw=0.5, zorder=6)
                ax.plot([x - 0.25, x + 0.25], [y1, y1], color=INK, lw=0.5, zorder=6)
        плита = "средняя" if палуба == "главная" else "солнечная"
        for x0, x1, y0, y1 in PB.колодцы(плита):
            if x1 - x0 > 3.0:
                ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="none", edgecolor=SEA, lw=0.6, ls="--", zorder=6))
    # --- солнечная палуба: слоты модулей (пунктир) и фундаменты-замки ВГ-2026.46.00 — постоянные, стоят и без модулей
    if палуба == "солнечная":
        for s in MOD.слоты():
            ax.add_patch(Rectangle((s["x0"], s["y0"]), s["x1"] - s["x0"], s["y1"] - s["y0"], facecolor="none",
                                   edgecolor="#1f7a5a", lw=0.7, ls=(0, (3, 2)), zorder=6))
            ax.text(s["xc"], s["yc"], s["слот"], ha="center", va="center", fontsize=5.4, color="#1f7a5a", zorder=7,
                    bbox=dict(boxstyle="round,pad=0.15", fc="white", ec="none", alpha=0.8))
            for (x, y) in s["фундаменты"]:
                ax.add_patch(Rectangle((x - 0.17, y - 0.17), 0.34, 0.34, facecolor=ACC, edgecolor="none", zorder=7))
    # --- колёса и кожухи
    if палуба in ("трюм", "главная", "средняя"):
        к = SU.кожух()
        for s in (1, -1):
            if палуба != "средняя":
                ax.add_patch(Rectangle((к["ниша_x0"], s * к["колесо_внутр"] if s > 0 else -к["колесо_наруж"]),
                                       к["ниша_x1"] - к["ниша_x0"], к["колесо_наруж"] - к["колесо_внутр"],
                                       facecolor="#f7d6d6", edgecolor=ACC, lw=0.8, zorder=4))
                ax.text(W.X_AXIS, s * (к["колесо_внутр"] + 1.6), "гребное\nколесо", ha="center",
                        va="center", fontsize=6, color=ACC, zorder=5)
            if палуба == "главная":
                xx0, xx1 = W.X_AXIS - 3.0, W.X_AXIS + 3.0
                ax.add_patch(Rectangle((xx0, 3.0 if s > 0 else -4.6), xx1 - xx0, 1.6,
                                       facecolor="#e2e2e2", edgecolor=INK, lw=0.6, zorder=4))
                ax.text((xx0 + xx1) / 2.0, s * 3.8, "ГЭД+редуктор", ha="center", va="center",
                        fontsize=5.6, color=INK, zorder=5)
                ax.add_patch(Rectangle((к["x0"], к["y_внутр"] if s > 0 else -к["y_наруж"]),
                                       к["x1"] - к["x0"], к["y_наруж"] - к["y_внутр"],
                                       facecolor="none", edgecolor=ACC, lw=0.8, ls="--", zorder=4))
        if палуба == "главная":
            г = G.GARAGE
            for i in range(г["places"]):
                cx = г["x0"] + 2.0 + (i % 2) * (г["vehicle_len"] + 1.2)
                cy = 2.8 if i < 2 else -2.8
                ax.add_patch(FancyBboxPatch((cx, cy - г["vehicle_width"] / 2.0), г["vehicle_len"], г["vehicle_width"],
                                            boxstyle="round,pad=0,rounding_size=0.5", facecolor="#c9ced4",
                                            edgecolor=INK, lw=0.5, zorder=4))
            ax.add_patch(Rectangle((-4.0, -1.8), 9.0, 3.6, facecolor="#dcdcd8", edgecolor=INK, lw=0.6, zorder=3))
            ax.text(0.5, 0.0, "аппарель\n9,0 x 3,6", ha="center", va="center", fontsize=5.6, color=INK, zorder=5)
            ax.add_patch(Rectangle((W.X_AXIS + 16.0, -1.0), 2.0, 2.0, facecolor="#555555", edgecolor="none", zorder=4))
            ax.text(W.X_AXIS + 17.0, -1.6, "шахта\nвыхлопа", ha="center", va="top", fontsize=5.4, color=INK)
    # --- переборки
    if палуба in ("второе дно", "трюм", "главная"):
        for x in GA.ПЕРЕБОРКИ:
            y = _полу("трюм", x)
            ax.plot([x, x], [-y, y], color=INK, lw=0.9, ls=(0, (4, 2)), zorder=6)
            ax.text(x, y + 0.4, "%.0f" % x, ha="center", va="bottom", fontsize=5.5, color=INK)
    # --- шкала и подписи
    for x in range(0, int(G.LOA) + 1, 10):
        ax.plot([x, x], [-12.4, -12.0], color=GRY, lw=0.6)
        ax.text(x, -12.5, str(x), ha="center", va="top", fontsize=6, color=GRY)
    ax.plot([0, G.LOA], [-12.2, -12.2], color=GRY, lw=0.6)
    ax.annotate("нос →", (G.LOA - 6, 12.2), fontsize=7, color=GRY)
    fig.text(0.02, 0.955, заголовок, fontsize=13, fontweight="bold", color=INK)
    fig.text(0.02, 0.915, подпись, fontsize=8, color=GRY)
    # легенда
    leg = [("tech", "технические"), ("service", "служебные"), ("public", "общественные"),
           ("cabins", "каюты"), ("trunk", "трап-холлы"), ("open", "открытые"), ("garage", "гараж")]
    for i, (t, n) in enumerate(leg):
        fig.patches.append(FancyBboxPatch((0.60 + i * 0.055, 0.935), 0.012, 0.025,
                                          boxstyle="square,pad=0", fc=ЦВЕТ[t], ec=GRY,
                                          transform=fig.transFigure, figure=fig))
        fig.text(0.614 + i * 0.055, 0.947, n, fontsize=6.5, color=INK, va="center")
    return fig


def build(verbose=True):
    и = GA.итоги()
    листы = [
        ("второе дно", "0. Второе дно, 0,00…0,90 м", "цистерны по gorizont.TANKS; продольные переборки ±%.2f м" % G.LONG_BULKHEAD_Y),
        ("трюм", "1. Трюм (технический ярус), 0,90…3,00 м", "нежилой: в свету 1,85 м, локально 2,15…2,30 при пониженном втором дне"),
        ("главная", "2. Главная палуба, 3,00…5,80 м", "палуба переборок; бортовой проход 1,0 м — открытый путь эвакуации"),
        ("средняя", "3. Средняя палуба, 5,80…8,60 м", "каютный блок в четыре ряда; %d пассажиров в %d каютах на судне" % (и["пассажиров"], и["пассажирских_кают"])),
        ("солнечная", "4. Солнечная палуба, 8,60 м",
         "открытая; рубка стационарная; %d слотов под модули 20' HC (пунктир) на %d фундаментах-замках ВГ-2026.46.00 (красные), "
         "темы модулей — docs/проект/модульное_решение.md" % (len(MOD.слоты()), len(MOD.фундаменты()))),
    ]
    пути = []
    for i, (п, заг, под) in enumerate(листы):
        fig = лист(п, заг, под)
        p = os.path.join(OUT, "%d_%s.png" % (i, п.replace(" ", "_")))
        fig.savefig(p)
        plt.close(fig)
        пути.append(p)
        if verbose:
            print("  ", os.path.basename(p))
    return пути


if __name__ == "__main__":
    build()
