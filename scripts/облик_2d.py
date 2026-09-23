# -*- coding: utf-8 -*-
"""2D-облик судна. Борт, план, два сечения - в цвете, из библиотек.

    python scripts/облик_2d.py

Стадия «визуальный концепт» - утверждается до модели. Ни одна линия не
нарисована руками - борт строится из `gorizont_lines` (корпус),
`gorizont_super` (ярусы, кожух, арка), `gorizont_facade` (панели из
компоновки), `gorizont_wheel` (колесо), цвет - из `gorizont_style`.
Поэтому облик и модель не могут разойтись - они читают одни функции.

Цвета самого судна (чёрный корпус, тёмное стекло, светлая рама, красная линия) - это облик,
они остаются. Оформление простое: без заголовков и заливки воды, подписи шрифтом по ГОСТ 2.304
чёрным, выносками над и под рисунком (раскладка и перенос - общие с планами палуб), ватерлиния -
линией с отметкой. Ширина рисунка 8 дюймов, кегль 8,5 - при вставке на ширину текста А4 6,9 pt.

Три листа:
  1_борт.png     вид с правого борта, ватерлиния, колесо в арке
  2_план.png     вид сверху - солнечная палуба, рубка, кожухи, нос и корма
  3_сечения.png  поперечные сечения по оси колёс (атриум) и по каютам
"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import numpy as np
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle

from lib import plain as P
from lib import gorizont as G, gorizont_lines as L, gorizont_super as SU
from lib import gorizont_facade as F, gorizont_wheel as W, gorizont_style as S, gorizont_ga as GA
from lib import gorizont_public as PB, gorizont_cabin_layout as КЛ
import планы_компоновки as ПЛ          # подписи-выноски: перенос по измеренному тексту, ряд без налезаний

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "облик")
os.makedirs(OUT, exist_ok=True)

ШИРИНА = 8.0                            # дюймов
КЕГЛЬ = ПЛ.КЕГЛЬ
П = S.ПАЛИТРА
ЧЁРНЫЙ, СЕРЕБРО, ГРАФИТ, КРАСНЫЙ = П["чёрный"], П["графит_серебро"], П["стекло_тон"], П["красный"]
СТЕКЛО, ПАЛУБА, ЛИНИЯ = П["стекло"], "#b9bdc2", "#16202f"
ТЁМНЫЙ = "#0c0e11"                      # ниша колеса, проём кожуха
СВЕТЛЫЙ = "#c9ced4"                     # обод и спицы колеса
ФАЛЬШБОРТ = "#9fc3d6"                   # стеклянный фальшборт
СЕРЫЙ = "#404040"                       # отметки уровней, ватерлиния
X = W.X_AXIS


def _хс(x0, x1, шаг=0.5):
    xs, x = [], x0
    while x < x1:
        xs.append(x)
        x += шаг
    xs.append(x1)
    return xs


def _метка(s, xa, ya, пт, до=4):
    return dict(s=s, xa=xa, ya=ya, вар=ПЛ.варианты(s, КЕГЛЬ, до, пт))


def _ряды(ax, верх, низ, lo, hi, пт, y_верх, y_низ, зазор=3.5, сдвиг=12.0, до=4):
    """Ряд выносок над рисунком (выше y_верх) и под ним (ниже y_низ). Возвращает (верх, низ) рисунка."""
    м1 = 1.0 / пт
    top, bot = y_верх, y_низ
    if верх:
        колено = y_верх + 4 * м1
        y_lab = колено + 8 * м1
        h = ПЛ.ряд(верх, lo, hi, до=до, сдвиг=сдвиг, зазор=зазор)
        ПЛ.нарисовать_ряд(ax, верх, колено, y_lab, 1, пт=пт, z=30, гало=True)
        top = y_lab + h
    if низ:
        колено = y_низ - 4 * м1
        y_lab = колено - 8 * м1
        h = ПЛ.ряд(низ, lo, hi, до=до, сдвиг=сдвиг, зазор=зазор)
        ПЛ.нарисовать_ряд(ax, низ, колено, y_lab, -1, пт=пт, z=30, гало=True)
        bot = y_lab - h
    return top, bot


def _выпуск(fig, ax, x0, x1, y0, y1, пт, путь):
    fig.set_size_inches(ШИРИНА, (y1 - y0) * пт / 72.0)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    P.сохранить(fig, путь)
    plt.close(fig)
    return путь


def _имя_зоны(s):
    """Короткое имя зоны - до первой запятой, со строчной буквы (как подписи элементов)."""
    s = s.split(",")[0].split(":")[0]
    return s[:1].lower() + s[1:]


# ----------------------------------------------------------------- 1. борт
def _судно_борт(ax):
    # корпус: киль снизу, кромка борта сверху
    xs = _хс(0.0, G.LOA, 0.5)
    корп = [(x, L.keel_z(x)) for x in xs] + [(x, G.DEPTH) for x in reversed(xs)]
    ax.add_patch(Polygon(корп, closed=True, facecolor=ЧЁРНЫЙ, edgecolor=ЛИНИЯ, lw=0.6, zorder=2))
    # ниша колеса в борту: до киля со сходами
    к = SU.кожух()
    ниша = [(x, L.keel_z(x)) for x in _хс(к["ниша_x0"] - W.NICHE_FAIR, к["ниша_x1"] + W.NICHE_FAIR, 0.25)]
    ниша_п = ниша + [(к["ниша_x1"] + W.NICHE_FAIR, G.DEPTH), (к["ниша_x0"] - W.NICHE_FAIR, G.DEPTH)]
    ax.add_patch(Polygon(ниша_п, closed=True, facecolor=ТЁМНЫЙ, edgecolor="none", zorder=3))
    for код in ("главная", "средняя"):
        я = SU.ЯРУСЫ[код]
        пб = [(x, y) for x, y in SU.обвод(код, 0.5) if y > 0.06]
        x0, x1 = пб[0][0], пб[-1][0]
        x0в, x1в = SU.границы_яруса(код, я["z1"])
        x0н, x1н = SU.границы_яруса(код, я["z0"])
        h = я["z1"] - я["z0"]
        ax.add_patch(Polygon([(x0н, я["z0"]), (x1н, я["z0"]), (x1в, я["z1"]), (x0в, я["z1"])], closed=True,
                             facecolor=ГРАФИТ, edgecolor="none", zorder=4))
        # рама: цоколь и наклонные торцы светлые
        ax.add_patch(Polygon([(x0н, я["z0"]), (x1н, я["z0"]), (x1н + (x1в - x1н) * 0.45 / h, я["z0"] + 0.45),
                              (x0н + (x0в - x0н) * 0.45 / h, я["z0"] + 0.45)], closed=True, facecolor=СЕРЕБРО,
                             edgecolor="none", zorder=6))
        for xa, xb in ((x0н, x0в), (x1н, x1в)):
            ax.add_patch(Polygon([(xa, я["z0"]), (xa + (0.9 if xa == x0н else -0.9), я["z0"]),
                                  (xb + (0.9 if xa == x0н else -0.9), я["z1"]), (xb, я["z1"])], closed=True,
                                 facecolor=СЕРЕБРО, edgecolor="none", zorder=6))
        низ, верх, _ = SU.лента(код)
        for a, b, тип, _ in F.ПАНЕЛИ[код]:
            a, b = max(a, x0 + 0.3), min(b, x1 - 0.3)
            if b <= a:
                continue
            if тип in ("проём", "окна"):
                ax.add_patch(Rectangle((a, низ), b - a, верх - низ, facecolor=СТЕКЛО, edgecolor="none", zorder=5))
                ax.plot([a + 0.2, b - 0.2], [верх - 0.12] * 2, color="#3d5566", lw=0.5, zorder=6)
                if тип == "окна":
                    for xc in F.окна(код):
                        if a < xc - F.ШАГ_ОКОН / 2.0 < b:
                            ax.add_patch(Rectangle((xc - F.ШАГ_ОКОН / 2.0 - F.ИМПОСТ / 2.0, низ), F.ИМПОСТ,
                                                   верх - низ, facecolor="#6b737c", edgecolor="none", zorder=6))
            elif тип == "решётка":
                ax.add_patch(Rectangle((a, низ), b - a, верх - низ, facecolor="#3a3f45", edgecolor="none",
                                       zorder=5, hatch="---"))
        # карниз: светлая фасция под крышей яруса
        ax.add_patch(Polygon([(x0в - (x0в - x0н) * SU.ТЕНЬ / h, я["z1"] - SU.ТЕНЬ),
                              (x1в - (x1в - x1н) * SU.ТЕНЬ / h, я["z1"] - SU.ТЕНЬ),
                              (x1в, я["z1"]), (x0в, я["z1"])], closed=True, facecolor=СЕРЕБРО, edgecolor="none",
                             zorder=6))
        if код == "главная":
            # портал: светлая рама во всю высоту надстройки вокруг колеса и атриума
            п0, п1 = SU.портал()
            ст = SU.ПОРТАЛ["стойка"]
            zв = G.DECKS["солнечная"]
            ax.add_patch(Rectangle((п0 - ст, к["z0"]), п1 - п0 + 2 * ст, zв - к["z0"], facecolor=СЕРЕБРО,
                                   edgecolor="none", zorder=6))
            # внутри портала: кожух над колесом светлый, над ним - стекло атриума во всю ширину
            ax.add_patch(Rectangle((п0, G.DECKS["средняя"] - 0.05), п1 - п0, zв - G.DECKS["средняя"] - 0.3,
                                   facecolor=СТЕКЛО, edgecolor="none", zorder=7))
            cx, cz = SU.центр_проёма()
            rп = SU.радиус_проёма()
            rр = SU.ПРОЁМ_КОЖУХА["рамка"]
            ax.add_patch(Circle((cx, cz), rп + rр, facecolor=КРАСНЫЙ, edgecolor="none", zorder=7))
            ax.add_patch(Circle((cx, cz), rп, facecolor=ТЁМНЫЙ, edgecolor="none", zorder=8))
            # ниже палубы - корпус, ниша тёмная (перекрыть нижнюю половину круга)
            ax.add_patch(Rectangle((cx - rп - rр - 0.5, cz - rп - rр - 0.5), 2 * (rп + rр) + 1.0,
                                   к["z0"] - (cz - rп - rр - 0.5), facecolor=ЧЁРНЫЙ, edgecolor="none", zorder=9))
            ax.add_patch(Polygon(ниша_п, closed=True, facecolor=ТЁМНЫЙ, edgecolor="none", zorder=9))
            # колесо
            ax.add_patch(Circle((cx, cz), W.PIVOT_RADIUS + W.RIM_OUT, fill=False, ec=СВЕТЛЫЙ, lw=1.0, zorder=10))
            ax.add_patch(Circle((cx, cz), W.HUB_RADIUS, facecolor=СВЕТЛЫЙ, ec="none", zorder=10))
            for i in range(W.BLADES):
                a = 2 * math.pi * (i + 0.5) / W.BLADES
                ax.plot([cx + W.HUB_RADIUS * math.cos(a), cx + (W.PIVOT_RADIUS - W.RIM_IN) * math.cos(a)],
                        [cz + W.HUB_RADIUS * math.sin(a), cz + (W.PIVOT_RADIUS - W.RIM_IN) * math.sin(a)],
                        color=СВЕТЛЫЙ, lw=0.5, zorder=10)
            for п in W.blade_positions(G.DRAFT):
                dx, dz = W.blade_direction(math.radians(п["a"]))
                px, pz = cx + п["x"], п["z"]
                ax.plot([px, px + dx * (W.PIVOT_OFFSET + W.BLADE_HEIGHT)],
                        [pz, pz + dz * (W.PIVOT_OFFSET + W.BLADE_HEIGHT)],
                        color=КРАСНЫЙ, lw=1.6, zorder=11, solid_capstyle="butt")
            # красная линия - по кромке прогулочной палубы вдоль всего борта, тонкая,
            # у портала ныряет и обходит колесо: единственный акцент судна
            пб1 = [(x, y) for x, y in SU.обвод("главная", 0.5) if y > 0.06]
            zл = я["z1"] - F.ВЫСОТА_ЛИНИИ / 2.0
            xa, xb = п0 - ст, п1 + ст
            ax.plot([пб1[0][0], xa], [zл, zл], color=КРАСНЫЙ, lw=1.2, zorder=13, solid_capstyle="butt")
            ax.plot([xb, пб1[-1][0]], [zл, zл], color=КРАСНЫЙ, lw=1.2, zorder=13, solid_capstyle="butt")
            for x_от, x_до in ((xa, cx - (rп + rр) * 0.62), (xb, cx + (rп + rр) * 0.62)):
                t = np.linspace(0, 1, 40)
                xx = x_от + (x_до - x_от) * t
                z_к = cz + math.sqrt(max((rп + rр) ** 2 - ((rп + rр) * 0.62) ** 2, 0.0))
                zz = zл + (z_к - zл) * (3 * t ** 2 - 2 * t ** 3)
                ax.plot(xx, zz, color=КРАСНЫЙ, lw=1.8, zorder=13, solid_capstyle="round")
    # солнечная палуба: карниз и стеклянный фальшборт, фальшборт главной палубы
    пб2 = [(x, y) for x, y in SU.обвод("средняя", 0.5) if y > 0.06]
    ax.plot([пб2[0][0] - SU.КАРНИЗ, пб2[-1][0] + SU.КАРНИЗ], [G.DECKS["солнечная"]] * 2, color=ЛИНИЯ, lw=0.8,
            zorder=14)
    ax.add_patch(Rectangle((пб2[0][0], G.DECKS["солнечная"]), пб2[-1][0] - пб2[0][0], 1.1, facecolor=ФАЛЬШБОРТ,
                           edgecolor="#5f8aa3", lw=0.4, zorder=14, alpha=0.45))
    ax.add_patch(Rectangle((5.0, G.DEPTH), G.LOA - 15.0, 1.1, facecolor=ФАЛЬШБОРТ, edgecolor="#5f8aa3", lw=0.4,
                           zorder=3, alpha=0.45))
    ax.add_patch(Rectangle((0.0, G.DEPTH), 5.0, 1.1, facecolor=ФАЛЬШБОРТ, edgecolor="#5f8aa3", lw=0.4, zorder=3,
                           alpha=0.45))
    # рубка стационарная: лоб вперёд, корма назад, плавник-мачта сложен на крыше
    р = SU.РУБКА
    h = р["z1"] - р["z0"]
    накл = h * math.tan(math.radians(р["наклон_лба"]))
    ax.add_patch(Polygon([(р["x0"], р["z0"]), (р["x1"], р["z0"]), (р["x1"] + накл, р["z1"]), (р["x0"] - 0.8, р["z1"])],
                         closed=True, facecolor=ГРАФИТ, edgecolor=ЛИНИЯ, lw=0.5, zorder=14))
    ax.add_patch(Polygon([(р["x0"] + 0.2, р["z0"] + 0.62), (р["x1"] + накл * 0.62 / h, р["z0"] + 0.62),
                          (р["x1"] + накл * (h - 0.4) / h, р["z1"] - 0.4), (р["x0"] - 0.6, р["z1"] - 0.4)],
                         closed=True, facecolor=СТЕКЛО, edgecolor="none", zorder=15))
    ax.add_patch(Polygon([(р["x0"] - 0.8, р["z1"]), (р["x0"] - 4.5, р["z1"] + 0.25), (р["x0"] - 4.5, р["z1"] + 0.05),
                          (р["x0"] + 1.5, р["z1"])], closed=True, facecolor=ЛИНИЯ, edgecolor="none", zorder=15))
    # труба, руль, водомёт, аппарель
    ax.add_patch(Rectangle((X + 15.6, G.DECKS["солнечная"]), 2.8, 0.9, facecolor=ГРАФИТ, edgecolor=ЛИНИЯ, lw=0.4,
                           zorder=14))
    ax.add_patch(Polygon([(1.2, 0.3), (3.4, 0.3), (3.4, L.keel_z(3.4) + 1.7), (1.2, 1.7)], closed=True,
                         facecolor="#3a3f45", edgecolor=ЛИНИЯ, lw=0.4, zorder=3))
    jx = G.THRUSTERS["носовой водомёт"]["x"]
    ax.plot([jx - 1.0, jx + 1.0], [L.keel_z(jx) + 0.05] * 2, color=КРАСНЫЙ, lw=2.0, zorder=3)
    ax.add_patch(Polygon([(0.0, G.DEPTH), (-3.5, G.DRAFT + 0.4), (-3.5, G.DRAFT + 0.7), (0.0, G.DEPTH + 0.3)],
                         closed=True, facecolor="#9aa0a6", edgecolor=ЛИНИЯ, lw=0.4, zorder=3))
    # скуловая линия на борту: подчёркивает длину и прячет высоту надводного борта
    ax.plot([2.0, G.LOA - 12.0], [G.DRAFT + 0.55] * 2, color="#2a2f35", lw=0.8, zorder=3)
    return dict(р=р, пб2=пб2, jx=jx, к=к)


def борт():
    x0, x1 = -21.0, G.LOA + 4.0
    пт = 72.0 * ШИРИНА / (x1 - x0)
    fig = plt.figure(figsize=(ШИРИНА, 2.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    д = _судно_борт(ax)
    р, пб2, к = д["р"], д["пб2"], д["к"]
    # отметки уровней палуб слева от кормы, ватерлиния - под своей линией
    м1 = 1.0 / пт
    xл = -5.0
    начало = {"главная": 0.0, "средняя": SU.границы_яруса("главная", G.DECKS["средняя"])[0],
              "солнечная": SU.границы_яруса("средняя", G.DECKS["солнечная"])[0]}
    for имя in ("главная", "средняя", "солнечная"):
        z = G.DECKS[имя]
        t = "%s %s" % (имя, P.ч(z, 2))
        w, _ = ПЛ.размер(t, КЕГЛЬ, пт)
        ax.text(xл, z + 1.5 * м1, t, ha="right", va="bottom", fontsize=КЕГЛЬ, zorder=20)
        ax.plot([xл - w, начало[имя]], [z, z], color=СЕРЫЙ, lw=0.4, zorder=1)
    t = "ВЛ %s" % P.ч(G.DRAFT, 2)
    w, _ = ПЛ.размер(t, КЕГЛЬ, пт)
    ax.text(xл, G.DRAFT - 1.5 * м1, t, ha="right", va="top", fontsize=КЕГЛЬ, zorder=20)
    ax.plot([xл - w, G.LOA + 3.0], [G.DRAFT] * 2, color=СЕРЫЙ, lw=0.6, zorder=1)
    # габарит по высоте - пунктир над рубкой
    zг = G.DRAFT + G.AIR_DRAFT
    ax.plot([0.0, G.LOA], [zг] * 2, color=СЕРЫЙ, lw=0.5, ls=(0, (2, 2)), zorder=13)
    # подписи выносками
    п0, п1 = SU.портал()
    ст = SU.ПОРТАЛ["стойка"]
    zл = SU.ЯРУСЫ["главная"]["z1"] - F.ВЫСОТА_ЛИНИИ / 2.0
    верх = [
        _метка("ярусы - тёмное стекло в светлой раме", 30.0, SU.лента("средняя")[0] + 0.9, пт),
        _метка("стеклянный фальшборт солнечной палубы", 50.0, G.DECKS["солнечная"] + 0.8, пт),
        _метка("атриум", X - 2.0, G.DECKS["средняя"] + 1.6, пт),
        _метка("портал", п1 + ст / 2.0, G.DECKS["средняя"] + 1.0, пт),
        _метка("дымовая труба", X + 17.0, G.DECKS["солнечная"] + 0.6, пт),
        _метка("плавник-мачта сложен", р["x0"] - 3.0, р["z1"] + 0.15, пт),
        _метка("рубка стационарная", (р["x0"] + р["x1"]) / 2.0 + 1.0, р["z1"] - 1.0, пт),
        _метка("габарит %s м над ВЛ, самый низкий мост маршрута %s м" % (P.ч(G.AIR_DRAFT), P.ч(G.BRIDGE_MIN)),
               8.0, zг, пт),
    ]
    низ = [
        _метка("аппарель", -1.8, G.DEPTH - 0.6, пт),
        _метка("два руля", 2.3, 0.7, пт),
        _метка("красная линия по кромке прогулочной палубы", 25.0, zл, пт),
        _метка("гребное колесо с шарнирными плицами в проёме портала", X + 1.2, SU.центр_проёма()[1] - 1.1, пт),
        _метка("носовой водомёт", д["jx"], L.keel_z(д["jx"]) + 0.05, пт),
    ]
    top, bot = _ряды(ax, верх, низ, x0 + 0.3, x1 - 0.3, пт, zг + 0.1, min(L.keel_z(x) for x in _хс(0, G.LOA, 1.0)),
                     до=3)
    return _выпуск(fig, ax, x0, x1, bot - 0.5, top + 0.5, пт, os.path.join(OUT, "1_борт.png"))


# ----------------------------------------------------------------- 2. план
def план():
    x0, x1 = -7.0, G.LOA + 4.0
    пт = 72.0 * ШИРИНА / (x1 - x0)
    fig = plt.figure(figsize=(ШИРИНА, 2.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    xs = _хс(0.0, G.LOA, 0.5)
    корп = [(x, L.side_half(x)) for x in xs] + [(x, -L.side_half(x)) for x in reversed(xs)]
    ax.add_patch(Polygon(корп, closed=True, facecolor=ПАЛУБА, edgecolor=ЛИНИЯ, lw=0.7, zorder=1))
    # ниши колёс сверху не видны - их закрывает крыша портала во всю ширину корпуса
    # ярус главной (крыша = прогулочная палуба, светлая) с красной кромкой
    пб = [(x, SU.полуширота(x, "главная", z=G.DECKS["средняя"] - 0.01)) for x, _ in SU.обвод("главная", 0.5)]
    пб = [(x, L.side_half(x) - 0.02 if SU.в_портале(x) else y) for x, y in пб if y > 0.06]
    ax.add_patch(Polygon(пб + [(x, -y) for x, y in reversed(пб)], closed=True, facecolor=СЕРЕБРО, edgecolor=КРАСНЫЙ,
                         lw=1.1, zorder=3))
    # солнечная палуба (крыша средней)
    пс = [(x, L.side_half(x) - 0.02 if SU.в_портале(x) else
           SU.полуширота(x, "средняя", z=G.DECKS["солнечная"] - 0.01) + SU.КАРНИЗ) for x, _ in SU.обвод("средняя", 0.5)]
    пс = [(x, y) for x, y in пс if y > 0.3]
    ax.add_patch(Polygon(пс + [(x, -y) for x, y in reversed(пс)], closed=True, facecolor="#d9c9a8", edgecolor=ЛИНИЯ,
                         lw=0.6, zorder=4))
    # солнечные модули над атриумом, труба, рубка
    ax.add_patch(Rectangle((X - 8, -5.5), 16, 11, facecolor="#2b3a4a", edgecolor="none", zorder=5, alpha=0.85))
    for i in range(8):
        ax.plot([X - 8 + 2 * i] * 2, [-5.5, 5.5], color="#4c6178", lw=0.4, zorder=6)
    ax.add_patch(Rectangle((X + 15.6, -0.9), 2.8, 1.8, facecolor=ГРАФИТ, edgecolor=ЛИНИЯ, lw=0.4, zorder=6))
    р = SU.РУБКА
    ax.add_patch(Rectangle((р["x0"], -р["полу"]), р["x1"] - р["x0"], 2 * р["полу"], facecolor=ГРАФИТ, edgecolor=ЛИНИЯ,
                           lw=0.5, zorder=6))
    # корма: аппарель
    ax.add_patch(Rectangle((-4.5, -1.8), 4.5, 3.6, facecolor="#9aa0a6", edgecolor=ЛИНИЯ, lw=0.4, zorder=3))
    # подписи выносками: зоны солнечной палубы - короткими именами из компоновки
    зоны = {_имя_зоны(z[3]): ((z[0] + z[1]) / 2.0) for z in GA.ЗОНЫ["солнечная"]}
    верх, низ = [], []
    сторона = 1
    for имя, xc in зоны.items():
        if abs(xc - X) < 1.0:
            верх.append(_метка(имя, X - 4.0, 3.0, пт))
            continue
        if "рубка" in имя.lower():
            верх.append(_метка(имя, xc - 1.5, 2.5, пт))
            continue
        y = SU.полуширота(xc, "средняя", z=G.DECKS["солнечная"] - 0.01) + SU.КАРНИЗ
        (верх if сторона > 0 else низ).append(_метка(имя, xc, сторона * max(min(y - 2.0, 4.5), 1.0), пт))
        сторона = -сторона
    xк = 35.0
    верх.append(_метка("красная кромка прогулочной палубы", xк,
                       SU.полуширота(xк, "главная", z=G.DECKS["средняя"] - 0.01), пт))
    верх.append(_метка("кормовая терраса", 2.5, 3.0, пт))
    верх.append(_метка("носовая палуба", G.LOA - 6.0, 1.2, пт))
    низ.append(_метка("аппарель", -2.2, -1.0, пт))
    низ.append(_метка("дымовая труба", X + 17.0, -0.4, пт))
    y_край = max(L.side_half(x) for x in xs)
    top, bot = _ряды(ax, верх, низ, x0 + 0.3, x1 - 0.3, пт, y_край + 0.2, -y_край - 0.2)
    return _выпуск(fig, ax, x0, x1, bot - 0.5, top + 0.5, пт, os.path.join(OUT, "2_план.png"))


# ----------------------------------------------------------------- 3. сечения
Я_ШИР = 11.5                             # полуширина поля одного сечения, м


def _зона(палуба, x):
    for x0, x1, тип, имя, _ in GA.ЗОНЫ[палуба]:
        if x0 <= x < x1:
            return имя
    return ""


def _корпус_сечения(ax, x, dx, атриум):
    zk = L.keel_z(x)
    bb = L.side_half(x)
    bk = min(L.bottom_half(x), bb)
    phi = math.radians(L.flare(x))
    пол = [(bk * i / 5.0, zk) for i in range(6)]
    for i in range(1, 21):
        z = zk + (G.DEPTH - zk) * i / 20.0
        y = L.section_y(z, zk, bk, G.DEPTH, bb, phi)
        пол.append((y if y is not None else bk, z))
    if атриум:
        нш = W.niche_half(x)
        пол = [(min(y, нш), z) for y, z in пол]
    контур = [(dx + y, z) for y, z in пол] + [(dx - y, z) for y, z in reversed(пол)]
    ax.add_patch(Polygon(контур, closed=True, facecolor="white", edgecolor=ЧЁРНЫЙ, lw=1.6, zorder=3))
    return bb, bk, пол


def _текст(ax, x, y, s, **kw):
    kw.setdefault("ha", "center")
    kw.setdefault("va", "center")
    kw.setdefault("fontsize", КЕГЛЬ)
    ax.text(x, y, ПЛ.гост(s), linespacing=ПЛ.ИНТЕРВАЛ, zorder=kw.pop("zorder", 20), **kw)


def сечение(ax, x, dx, атриум, пт, верх, низ):
    bb, bk, пол = _корпус_сечения(ax, x, dx, атриум)
    нш = W.niche_half(x) if атриум else bb
    # второе дно и главная палуба
    ax.plot([dx - min(bk, нш), dx + min(bk, нш)], [G.DECKS["первая"]] * 2, color=ЛИНИЯ, lw=0.7, zorder=4)
    ax.plot([dx - bb, dx + bb], [G.DECKS["главная"]] * 2, color=ЛИНИЯ, lw=1.0, zorder=4)
    # фальшборт главной палубы
    for s in (1, -1):
        ax.plot([dx + s * bb] * 2, [G.DEPTH, G.DEPTH + 1.1], color="#7d858f", lw=0.6, zorder=4)
    zс = G.DECKS["солнечная"]
    полу_с = SU.полуширота(x, "средняя", z=zс) + SU.КАРНИЗ
    трюм = "трюм, " + _имя_зоны(_зона("трюм", x + 0.01).split(" - ")[0])
    if атриум:
        к = SU.кожух()
        п = SU.портал_блок()
        z0 = W.axis_height(G.DRAFT)
        # атриум между порталами - светлый объём на две палубы, у колодца трапа - проём в средней палубе
        ax.add_patch(Rectangle((dx - п["y_внутр"], G.DECKS["главная"]), 2 * п["y_внутр"], zс - G.DECKS["главная"],
                               facecolor="white", edgecolor=ЛИНИЯ, lw=0.7, zorder=5))
        проёмы = [(y0, y1) for x0, x1, y0, y1 in PB.колодцы("средняя") if x0 <= x <= x1]
        отрезки = [(-п["y_внутр"], п["y_внутр"])]
        for a, b in проёмы:
            нов = []
            for c, d in отрезки:
                if b <= c or a >= d:
                    нов.append((c, d))
                    continue
                if a > c:
                    нов.append((c, a))
                if b < d:
                    нов.append((b, d))
            отрезки = нов
        for c, d in отрезки:
            ax.plot([dx + c, dx + d], [G.DECKS["средняя"]] * 2, color=ЛИНИЯ, lw=0.9, zorder=6)
        for s in (1, -1):
            # портал: светлый блок во всю высоту надстройки, в наружной стенке - стекло атриума
            ax.add_patch(Rectangle((dx + (п["y_внутр"] if s > 0 else -п["y_наруж"]), п["z0"]),
                                   п["y_наруж"] - п["y_внутр"], п["z1"] - п["z0"], facecolor=СЕРЕБРО,
                                   edgecolor=ЛИНИЯ, lw=0.6, zorder=5))
            ax.add_patch(Rectangle((dx + (п["y_наруж"] - 0.14 if s > 0 else -п["y_наруж"] + 0.02), п["z_атриум0"]),
                                   0.12, п["z_атриум1"] - п["z_атриум0"], facecolor=СТЕКЛО, edgecolor="none",
                                   zorder=6))
            # колесо: плицы красные, диски обода и вал светлые
            yc = s * (к["колесо_внутр"] + W.WIDTH / 2.0)
            ax.add_patch(Rectangle((dx + yc - W.BLADE_SPAN / 2.0, z0 - W.PIVOT_RADIUS - W.BLADE_HEIGHT), W.BLADE_SPAN,
                                   2 * W.PIVOT_RADIUS + W.BLADE_HEIGHT, facecolor=КРАСНЫЙ, edgecolor="#7a0a1c",
                                   lw=0.5, zorder=7, alpha=0.9))
            for yy in (yc - W.WIDTH / 2.0 + 0.12, yc + W.WIDTH / 2.0 - 0.12):
                ax.plot([dx + yy] * 2, [z0 - W.PIVOT_RADIUS, z0 + W.PIVOT_RADIUS], color=СВЕТЛЫЙ, lw=1.4, zorder=8)
            ax.plot([dx + s * (к["y_внутр"] + 0.03), dx + yc], [z0, z0], color=СВЕТЛЫЙ, lw=2.0, zorder=8)
            # выгородка ГЭД и редуктора у кожуха
            ax.add_patch(Rectangle((dx + (3.0 if s > 0 else -4.6), G.DECKS["главная"]), 1.6, 1.4, facecolor="white",
                                   edgecolor=ЛИНИЯ, lw=0.6, zorder=6))
            _текст(ax, dx + s * 3.8, G.DECKS["главная"] + 0.7, "ГЭД")
        _текст(ax, dx, (G.DECKS["средняя"] + zс) / 2.0, "атриум\nв два света")
        _текст(ax, dx, G.DECKS["главная"] + 1.4, "главный трап")
        ax.plot([dx - полу_с, dx + полу_с], [zс] * 2, color=ЛИНИЯ, lw=1.0, zorder=9)
        верх.append(_метка("световой фонарь и навес солнечных модулей", dx - 1.0, zс + 0.05, пт))
        верх.append(_метка("портал", dx + (п["y_внутр"] + п["y_наруж"]) / 2.0, zс - 1.2, пт))
        низ.append(_метка("гребное колесо", dx + к["колесо_внутр"] + W.WIDTH / 2.0, z0 - W.PIVOT_RADIUS, пт))
        _текст(ax, dx, (G.DECKS["первая"] + G.DECKS["главная"]) / 2.0, трюм)
    else:
        # ярусы с завалом: светлая рама главного, тёмное стекло среднего
        for код, цвет in (("главная", СЕРЕБРО), ("средняя", ГРАФИТ)):
            я = SU.ЯРУСЫ[код]
            y0 = SU.полуширота(x, код, z=я["z0"])
            y1 = SU.полуширота(x, код, z=я["z1"])
            ax.add_patch(Polygon([(dx - y0, я["z0"]), (dx + y0, я["z0"]), (dx + y1, я["z1"]), (dx - y1, я["z1"])],
                                 closed=True, facecolor=цвет, edgecolor=ЛИНИЯ, lw=0.6, zorder=5))
        # каюты: у борта - коридор - внутренние
        for палуба in ("главная", "средняя"):
            z0 = G.DECKS[палуба]
            z1 = z0 + G.DECK_PITCH - G.LINING
            yб = SU.полуширота(x, палуба, z=z0 + 0.6) - G.LINING / 2.0
            гв = GA.глубина_внутренней(палуба, x)
            for s in (1, -1):
                for a, b in ((yб - GA.ГЛУБИНА_БОРТ, yб), (yб - GA.ГЛУБИНА_БОРТ - GA.КОРИДОР, yб - GA.ГЛУБИНА_БОРТ),
                             (0.0, гв)):
                    ya, yb = sorted((s * a, s * b))
                    ax.add_patch(Rectangle((dx + ya, z0), yb - ya, z1 - z0, facecolor="white", edgecolor=ЛИНИЯ,
                                           lw=0.6, zorder=6))
                zm = (z0 + z1) / 2.0
                шк = ПЛ.размер("каюта", КЕГЛЬ, пт)[0] + 0.8
                for yc, ш in ((yб - GA.ГЛУБИНА_БОРТ / 2.0, GA.ГЛУБИНА_БОРТ), (гв / 2.0, гв)):
                    _текст(ax, dx + s * yc, zm, ("каюта\n" if ш >= шк else "") + P.ч(ш, 2))
                _текст(ax, dx + s * (yб - GA.ГЛУБИНА_БОРТ - GA.КОРИДОР / 2.0), zm, P.ч(GA.КОРИДОР, 2), rotation=90)
        ax.plot([dx - полу_с, dx + полу_с], [zс] * 2, color=ЛИНИЯ, lw=1.0, zorder=9)
        _текст(ax, dx, (G.DECKS["первая"] + G.DECKS["главная"]) / 2.0, трюм)
    # стеклянный фальшборт солнечной палубы
    for s in (1, -1):
        ax.plot([dx + s * (полу_с - SU.КАРНИЗ)] * 2, [zс, zс + 1.1], color="#5f8aa3", lw=0.8, zorder=9)
    # основная плоскость, ватерлиния, уровни палуб справа
    м1 = 1.0 / пт
    xп = dx + Я_ШИР
    ax.plot([dx - Я_ШИР + 1.2, xп], [G.DRAFT] * 2, color=СЕРЫЙ, lw=0.6, zorder=1)
    _текст(ax, xп, G.DRAFT + 1.5 * м1, "ВЛ %s" % P.ч(G.DRAFT, 2), ha="right", va="bottom")
    for имя in ("главная", "средняя", "солнечная"):
        z = G.DECKS[имя]
        _текст(ax, xп, z + 1.5 * м1, P.ч(z, 2), ha="right", va="bottom")
        ax.plot([xп - ПЛ.размер(P.ч(z, 2), КЕГЛЬ, пт)[0], xп], [z, z], color=СЕРЫЙ, lw=0.4, zorder=1)
    _текст(ax, dx - Я_ШИР, L.keel_z(x) + 1.5 * м1, "ОП", ha="left", va="bottom")
    ax.plot([dx - Я_ШИР, dx - min(bk, нш)], [L.keel_z(x)] * 2, color=СЕРЫЙ, lw=0.4, zorder=1)


def сечения():
    dx2 = 2 * Я_ШИР + 1.0
    x0, x1 = -Я_ШИР - 0.3, dx2 + Я_ШИР + 0.3
    пт = 72.0 * ШИРИНА / (x1 - x0)
    fig = plt.figure(figsize=(ШИРИНА, 3.0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.axis("off")
    xб = 45.0
    виды = ((X, 0.0, True, "а) по оси колёс, x = %s м" % P.ч(X, 0)),
            (xб, dx2, False, "б) по каютному блоку, x = %s м" % P.ч(xб, 0)))
    top, bot = G.DECKS["солнечная"] + 1.4, -0.3
    for x, dx, атриум, подпись in виды:
        верх, низ = [], []
        сечение(ax, x, dx, атриум, пт, верх, низ)
        t, b = _ряды(ax, верх, низ, dx - Я_ШИР, dx + Я_ШИР, пт, G.DECKS["солнечная"] + 1.2, L.keel_z(x) - 0.1,
                     зазор=1.2, сдвиг=4.0)
        top, bot = max(top, t), min(bot, b)
    м1 = 1.0 / пт
    yп = bot - 6 * м1
    for x, dx, атриум, подпись in виды:
        _текст(ax, dx, yп, подпись, va="top")
    h = ПЛ.размер("а)", КЕГЛЬ, пт)[1]
    y = yп - h - 6 * м1
    прим = ("Размеры в метрах, в каютах и коридорах - ширина поперёк судна, уровни палуб - от основной "
            "плоскости (ОП). Высота кают в свету %s, зашивка подволока %s." % (P.ч(КЛ.ВЫСОТА_В_СВЕТУ, 2),
                                                                             P.ч(G.LINING, 2)))
    for стр in ПЛ.перенос(прим, x1 - x0 - 0.6, КЕГЛЬ, пт):
        _текст(ax, x0 + 0.3, y, стр, ha="left", va="top")
        y -= ПЛ.размер(стр, КЕГЛЬ, пт)[1] + 2 * м1
    return _выпуск(fig, ax, x0, x1, y - 4 * м1, top + 4 * м1, пт, os.path.join(OUT, "3_сечения.png"))


def build(verbose=True):
    with P.чертёж():
        пути = (борт(), план(), сечения())
    if verbose:
        for p in пути:
            print("  ", os.path.basename(p))
    return пути


if __name__ == "__main__":
    build()
