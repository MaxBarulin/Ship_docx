# -*- coding: utf-8 -*-
"""2D-облик судна. Борт, план, два сечения - в цвете, из библиотек.

    python scripts/облик_2d.py

Стадия «визуальный концепт» - утверждается до модели. Ни одна линия не
нарисована руками - борт строится из `gorizont_lines` (корпус),
`gorizont_super` (ярусы, кожух, арка), `gorizont_facade` (панели из
компоновки), `gorizont_wheel` (колесо), цвет - из `gorizont_style`.
Поэтому облик и модель не могут разойтись - они читают одни функции.

Три листа:
  1_борт.png     вид с правого борта, ватерлиния, колесо в арке
  2_план.png     вид сверху - солнечная палуба, рубка, кожухи, нос и корма
  3_сечения.png  поперечные сечения по атриуму (через колесо) и по каютам
"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon, Rectangle, Circle, Ellipse, Wedge

from lib import gorizont as G, gorizont_lines as L, gorizont_super as SU
from lib import gorizont_facade as F, gorizont_wheel as W, gorizont_style as S, gorizont_ga as GA

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "облик")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"axes.unicode_minus": False, "font.family": "DejaVu Sans", "font.size": 8,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
П = S.ПАЛИТРА
ЧЁРНЫЙ, СЕРЕБРО, ГРАФИТ, КРАСНЫЙ = П["чёрный"], П["графит_серебро"], П["стекло_тон"], П["красный"]
СТЕКЛО, ПАЛУБА, ВОДА, ЛИНИЯ = П["стекло"], "#b9bdc2", "#cfe0ea", "#16202f"
X = W.X_AXIS


def _хс(x0, x1, шаг=0.5):
    xs, x = [], x0
    while x < x1:
        xs.append(x)
        x += шаг
    xs.append(x1)
    return xs


# ----------------------------------------------------------------- 1. борт
def борт(ax):
    ax.set_aspect("equal")
    ax.set_xlim(-4, G.LOA + 4)
    ax.set_ylim(-1.2, 13.0)
    ax.axis("off")
    # вода
    ax.add_patch(Rectangle((-4, -1.2), G.LOA + 8, G.DRAFT + 1.2, facecolor=ВОДА, edgecolor="none", zorder=0))
    # корпус: киль снизу, кромка борта сверху
    xs = _хс(0.0, G.LOA, 0.5)
    корп = [(x, L.keel_z(x)) for x in xs] + [(x, G.DEPTH) for x in reversed(xs)]
    ax.add_patch(Polygon(корп, closed=True, facecolor=ЧЁРНЫЙ, edgecolor=ЛИНИЯ, lw=0.8, zorder=2))
    # ниша колеса в борту: до киля со сходами
    к = SU.кожух()
    ниша = [(x, L.keel_z(x)) for x in _хс(к["ниша_x0"] - W.NICHE_FAIR, к["ниша_x1"] + W.NICHE_FAIR, 0.25)]
    ax.add_patch(Polygon(ниша + [(к["ниша_x1"] + W.NICHE_FAIR, G.DEPTH), (к["ниша_x0"] - W.NICHE_FAIR, G.DEPTH)],
                         closed=True, facecolor="#0c0e11", edgecolor="none", zorder=3))
    # ярусы
    for код, цвет in (("главная", ГРАФИТ), ("средняя", ГРАФИТ)):
        я = SU.ЯРУСЫ[код]
        пб = [(x, y) for x, y in SU.обвод(код, 0.5) if y > 0.06]
        x0, x1 = пб[0][0], пб[-1][0]
        x0в, x1в = SU.границы_яруса(код, я["z1"])
        x0н, x1н = SU.границы_яруса(код, я["z0"])
        ax.add_patch(Polygon([(x0н, я["z0"]), (x1н, я["z0"]), (x1в, я["z1"]), (x0в, я["z1"])], closed=True,
                             facecolor=цвет, edgecolor="none", zorder=4))
        # рама: цоколь и наклонные торцы светлые
        h = я["z1"] - я["z0"]
        ax.add_patch(Polygon([(x0н, я["z0"]), (x1н, я["z0"]), (x1н + (x1в - x1н) * 0.45 / h, я["z0"] + 0.45),
                              (x0н + (x0в - x0н) * 0.45 / h, я["z0"] + 0.45)], closed=True, facecolor=СЕРЕБРО, edgecolor="none", zorder=6))
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
                # блик по стеклу: тонкая светлая линия у верха
                ax.plot([a + 0.2, b - 0.2], [верх - 0.12] * 2, color="#3d5566", lw=0.5, zorder=6)
                if тип == "окна":
                    for xc in F.окна(код):
                        if a < xc - F.ШАГ_ОКОН / 2.0 < b:
                            ax.add_patch(Rectangle((xc - F.ШАГ_ОКОН / 2.0 - F.ИМПОСТ / 2.0, низ), F.ИМПОСТ, верх - низ,
                                                   facecolor="#6b737c", edgecolor="none", zorder=6))
            elif тип == "решётка":
                ax.add_patch(Rectangle((a, низ), b - a, верх - низ, facecolor="#3a3f45", edgecolor="none", zorder=5, hatch="---"))
        # карниз: светлая фасция под крышей яруса
        ax.add_patch(Polygon([(x0в - (x0в - x0н) * SU.ТЕНЬ / (я["z1"] - я["z0"]), я["z1"] - SU.ТЕНЬ),
                              (x1в - (x1в - x1н) * SU.ТЕНЬ / (я["z1"] - я["z0"]), я["z1"] - SU.ТЕНЬ),
                              (x1в, я["z1"]), (x0в, я["z1"])], closed=True, facecolor=СЕРЕБРО, edgecolor="none", zorder=6))
        if код == "главная":
            # портал: светлая рама во всю высоту надстройки вокруг колеса и атриума
            п0, п1 = SU.портал()
            ст = SU.ПОРТАЛ["стойка"]
            zв = G.DECKS["солнечная"]
            ax.add_patch(Rectangle((п0 - ст, к["z0"]), п1 - п0 + 2 * ст, zв - к["z0"], facecolor=СЕРЕБРО, edgecolor="none", zorder=6))
            # внутри портала: кожух над колесом светлый, над ним - стекло атриума во всю ширину
            ax.add_patch(Rectangle((п0, G.DECKS["средняя"] - 0.05), п1 - п0, zв - G.DECKS["средняя"] - 0.3,
                                   facecolor=СТЕКЛО, edgecolor="none", zorder=7))
            ax.text((п0 + п1) / 2.0, zв - 1.4, "атриум", ha="center", fontsize=6.5, color="#9fc3d6", zorder=8)
            cx, cz = SU.центр_проёма(); rп = SU.радиус_проёма(); rр = SU.ПРОЁМ_КОЖУХА["рамка"]
            ax.add_patch(Circle((cx, cz), rп + rр, facecolor=КРАСНЫЙ, edgecolor="none", zorder=7))
            ax.add_patch(Circle((cx, cz), rп, facecolor="#0c0e11", edgecolor="none", zorder=8))
            # ниже палубы - корпус, ниша тёмная (перекрыть нижнюю половину круга)
            ax.add_patch(Rectangle((cx - rп - rр - 0.5, cz - rп - rр - 0.5), 2 * (rп + rр) + 1.0, к["z0"] - (cz - rп - rр - 0.5),
                                   facecolor=ЧЁРНЫЙ, edgecolor="none", zorder=9))
            ax.add_patch(Polygon(ниша + [(к["ниша_x1"] + W.NICHE_FAIR, G.DEPTH), (к["ниша_x0"] - W.NICHE_FAIR, G.DEPTH)],
                                 closed=True, facecolor="#0c0e11", edgecolor="none", zorder=9))
            # колесо
            ax.add_patch(Circle((cx, cz), W.PIVOT_RADIUS + W.RIM_OUT, fill=False, ec="#c9ced4", lw=1.3, zorder=10))
            ax.add_patch(Circle((cx, cz), W.HUB_RADIUS, facecolor="#c9ced4", ec="none", zorder=10))
            for i in range(W.BLADES):
                a = 2 * math.pi * (i + 0.5) / W.BLADES
                ax.plot([cx + W.HUB_RADIUS * math.cos(a), cx + (W.PIVOT_RADIUS - W.RIM_IN) * math.cos(a)],
                        [cz + W.HUB_RADIUS * math.sin(a), cz + (W.PIVOT_RADIUS - W.RIM_IN) * math.sin(a)],
                        color="#c9ced4", lw=0.7, zorder=10)
            for п in W.blade_positions(G.DRAFT):
                dx, dz = W.blade_direction(math.radians(п["a"]))
                px, pz = cx + п["x"], п["z"]
                ax.plot([px, px + dx * (W.PIVOT_OFFSET + W.BLADE_HEIGHT)], [pz, pz + dz * (W.PIVOT_OFFSET + W.BLADE_HEIGHT)],
                        color=КРАСНЫЙ, lw=2.2, zorder=11, solid_capstyle="butt")
            # красная линия: по кромке прогулочной палубы, у колеса ныряет вокруг проёма
            # красная линия - по кромке прогулочной палубы вдоль всего борта, но тонкая;
            # у портала она ныряет и обходит колесо: единственный акцент судна
            пб1 = [(x, y) for x, y in SU.обвод("главная", 0.5) if y > 0.06]
            zл = я["z1"] - F.ВЫСОТА_ЛИНИИ / 2.0
            xa, xb = п0 - ст, п1 + ст
            ax.plot([пб1[0][0], xa], [zл, zл], color=КРАСНЫЙ, lw=1.6, zorder=13, solid_capstyle="butt")
            ax.plot([xb, пб1[-1][0]], [zл, zл], color=КРАСНЫЙ, lw=1.6, zorder=13, solid_capstyle="butt")
            # плавный спуск к кольцу (S-кривая) с обеих сторон
            import numpy as np
            for x_от, x_до in ((xa, cx - (rп + rр) * 0.62), (xb, cx + (rп + rр) * 0.62)):
                t = np.linspace(0, 1, 40)
                xx = x_от + (x_до - x_от) * t
                z_к = cz + math.sqrt(max((rп + rр) ** 2 - ((rп + rр) * 0.62) ** 2, 0.0))
                zz = zл + (z_к - zл) * (3 * t ** 2 - 2 * t ** 3)
                ax.plot(xx, zz, color=КРАСНЫЙ, lw=2.6, zorder=13, solid_capstyle="round")
    # солнечная палуба: карниз и леер
    пб2 = [(x, y) for x, y in SU.обвод("средняя", 0.5) if y > 0.06]
    ax.plot([пб2[0][0] - SU.КАРНИЗ, пб2[-1][0] + SU.КАРНИЗ], [G.DECKS["солнечная"]] * 2, color=ЛИНИЯ, lw=1.0, zorder=14)
    # стеклянные фальшборты вместо леерных стоек: солнечная и главная палубы
    ax.add_patch(Rectangle((пб2[0][0], G.DECKS["солнечная"]), пб2[-1][0] - пб2[0][0], 1.1, facecolor="#9fc3d6",
                           edgecolor="#5f8aa3", lw=0.5, zorder=14, alpha=0.45))
    ax.add_patch(Rectangle((5.0, G.DEPTH), G.LOA - 15.0, 1.1, facecolor="#9fc3d6", edgecolor="#5f8aa3", lw=0.5, zorder=3, alpha=0.45))
    ax.add_patch(Rectangle((0.0, G.DEPTH), 5.0, 1.1, facecolor="#9fc3d6", edgecolor="#5f8aa3", lw=0.5, zorder=3, alpha=0.45))
    # рубка (поднята): лоб вперёд, корма назад, сложенный плавник-мачта на крыше
    р = SU.РУБКА
    h = р["z1"] - р["z0"]
    накл = h * math.tan(math.radians(р["наклон_лба"]))
    ax.add_patch(Polygon([(р["x0"], р["z0"]), (р["x1"], р["z0"]), (р["x1"] + накл, р["z1"]), (р["x0"] - 0.8, р["z1"])],
                         closed=True, facecolor=ГРАФИТ, edgecolor=ЛИНИЯ, lw=0.6, zorder=14))
    ax.add_patch(Polygon([(р["x0"] + 0.2, р["z0"] + 0.62), (р["x1"] + накл * 0.62 / h, р["z0"] + 0.62),
                          (р["x1"] + накл * (h - 0.4) / h, р["z1"] - 0.4), (р["x0"] - 0.6, р["z1"] - 0.4)],
                         closed=True, facecolor=СТЕКЛО, edgecolor="none", zorder=15))
    ax.add_patch(Polygon([(р["x0"] - 0.8, р["z1"]), (р["x0"] - 4.5, р["z1"] + 0.25), (р["x0"] - 4.5, р["z1"] + 0.05), (р["x0"] + 1.5, р["z1"])],
                         closed=True, facecolor=ЛИНИЯ, edgecolor="none", zorder=15))
    ax.annotate("плавник-мачта сложен", (р["x0"] - 9.5, р["z1"] + 0.5), fontsize=6.5, color=ЛИНИЯ)
    ax.annotate("рубка опускается на %.1f м под мостами" % G.WHEELHOUSE_LIFT, (р["x1"] + 0.5, р["z1"] - 0.2),
                fontsize=6.5, color=ЛИНИЯ)
    # труба, руль, водомёт, аппарель
    ax.add_patch(Rectangle((X + 15.6, G.DECKS["солнечная"]), 2.8, 0.9, facecolor=ГРАФИТ, edgecolor=ЛИНИЯ, lw=0.5, zorder=14))
    ax.add_patch(Polygon([(1.2, 0.3), (3.4, 0.3), (3.4, L.keel_z(3.4) + 0.0 + 1.7), (1.2, 1.7)], closed=True,
                         facecolor="#3a3f45", edgecolor=ЛИНИЯ, lw=0.5, zorder=3))
    ax.annotate("руль ×2", (3.6, 0.9), fontsize=6.5, color=ЛИНИЯ)
    jx = G.THRUSTERS["носовой водомёт"]["x"]
    ax.plot([jx - 1.0, jx + 1.0], [L.keel_z(jx) + 0.05] * 2, color=КРАСНЫЙ, lw=2.5, zorder=3)
    ax.annotate("носовой водомёт", (jx - 14.0, L.keel_z(jx) - 0.9), fontsize=6.5, color=ЛИНИЯ)
    ax.add_patch(Polygon([(0.0, G.DEPTH), (-3.5, G.DRAFT + 0.4), (-3.5, G.DRAFT + 0.7), (0.0, G.DEPTH + 0.3)], closed=True,
                         facecolor="#9aa0a6", edgecolor=ЛИНИЯ, lw=0.5, zorder=3))
    ax.annotate("аппарель", (-4.0, G.DEPTH + 0.6), fontsize=6.5, color=ЛИНИЯ, ha="left")
    # скуловая линия на борту: подчёркивает длину и прячет высоту надводного борта
    ax.plot([2.0, G.LOA - 12.0], [G.DRAFT + 0.55] * 2, color="#2a2f35", lw=1.0, zorder=3)
    # ватерлиния и подписи
    ax.plot([-4, G.LOA + 4], [G.DRAFT, G.DRAFT], color="#2f6f9a", lw=0.8, ls="--", zorder=13)
    ax.text(G.LOA + 3.5, G.DRAFT + 0.15, "ВЛ %.2f" % G.DRAFT, fontsize=6.5, color="#2f6f9a", ha="right")
    for имя, z in (("главная 3,00", G.DECKS["главная"]), ("средняя 5,80", G.DECKS["средняя"]), ("солнечная 8,60", G.DECKS["солнечная"])):
        ax.text(-3.5, z + 0.12, имя, fontsize=6.5, color=ЛИНИЯ, ha="left")
    ax.annotate("габарит %.1f м над водой, самый низкий мост маршрута %.1f м" % (G.AIR_DRAFT, G.BRIDGE_MIN),
                (G.LOA * 0.5, G.DRAFT + G.AIR_DRAFT + 0.1), fontsize=6.5, color="#7a1020", ha="center")
    ax.plot([-4, G.LOA + 4], [G.DRAFT + G.AIR_DRAFT] * 2, color="#7a1020", lw=0.6, ls=":", zorder=13)
    ax.annotate("нос →", (G.LOA - 4, 12.3), fontsize=7, color="#7d858f")


# ----------------------------------------------------------------- 2. план
def план(ax):
    ax.set_aspect("equal")
    ax.set_xlim(-6, G.LOA + 4)
    ax.set_ylim(-10.5, 10.5)
    ax.axis("off")
    xs = _хс(0.0, G.LOA, 0.5)
    корп = [(x, L.side_half(x)) for x in xs] + [(x, -L.side_half(x)) for x in reversed(xs)]
    ax.add_patch(Polygon(корп, closed=True, facecolor=ПАЛУБА, edgecolor=ЛИНИЯ, lw=0.9, zorder=1))
    # ниши колёс в плане
    for s in (1, -1):
        н = [(x, s * W.niche_half(x)) for x in _хс(X - W.NICHE_LEN / 2 - W.NICHE_FAIR, X + W.NICHE_LEN / 2 + W.NICHE_FAIR, 0.25)]
        ax.add_patch(Polygon(н + [(н[-1][0], s * 8.25), (н[0][0], s * 8.25)], closed=True, facecolor="#0c0e11", edgecolor="none", zorder=2))
    # ярус главной (крыша = прогулочная палуба, светлая) с кожухами
    пб = [(x, SU.полуширота(x, "главная", z=G.DECKS["средняя"] - 0.01)) for x, _ in SU.обвод("главная", 0.5)]
    пб = [(x, L.side_half(x) - 0.02 if SU.в_портале(x) else y) for x, y in пб if y > 0.06]
    ax.add_patch(Polygon(пб + [(x, -y) for x, y in reversed(пб)], closed=True, facecolor=СЕРЕБРО, edgecolor=КРАСНЫЙ, lw=1.4, zorder=3))
    # солнечная палуба (крыша средней)
    пс = [(x, L.side_half(x) - 0.02 if SU.в_портале(x) else SU.полуширота(x, "средняя", z=G.DECKS["солнечная"] - 0.01) + SU.КАРНИЗ)
          for x, _ in SU.обвод("средняя", 0.5)]
    пс = [(x, y) for x, y in пс if y > 0.3]
    ax.add_patch(Polygon(пс + [(x, -y) for x, y in reversed(пс)], closed=True, facecolor="#d9c9a8", edgecolor=ЛИНИЯ, lw=0.8, zorder=4))
    # солнечные модули над атриумом, труба, рубка, зоны
    ax.add_patch(Rectangle((X - 8, -5.5), 16, 11, facecolor="#2b3a4a", edgecolor="none", zorder=5, alpha=0.85))
    for i in range(8):
        ax.plot([X - 8 + 2 * i] * 2, [-5.5, 5.5], color="#4c6178", lw=0.4, zorder=6)
    ax.text(X, 0, "солнечные модули 24 кВт\nсветовой фонарь атриума", ha="center", va="center", fontsize=6, color="white", zorder=7)
    ax.add_patch(Rectangle((X + 15.6, -0.9), 2.8, 1.8, facecolor=ГРАФИТ, edgecolor=ЛИНИЯ, lw=0.5, zorder=6))
    р = SU.РУБКА
    ax.add_patch(Rectangle((р["x0"], -р["полу"]), р["x1"] - р["x0"], 2 * р["полу"], facecolor=ГРАФИТ, edgecolor=ЛИНИЯ, lw=0.6, zorder=6))
    ax.text((р["x0"] + р["x1"]) / 2, 0, "рубка", ha="center", va="center", fontsize=6.5, color="white", zorder=7)
    for x0, x1, т, имя, _ in GA.ЗОНЫ["солнечная"]:
        if т == "open":
            ax.text((x0 + x1) / 2, -7.6 if (x0 // 10) % 2 else 7.6, imя_short(имя), ha="center", va="center", fontsize=6, color=ЛИНИЯ)
    # корма: терраса и аппарель; нос: площадка
    ax.add_patch(Rectangle((-4.5, -1.8), 4.5, 3.6, facecolor="#9aa0a6", edgecolor=ЛИНИЯ, lw=0.5, zorder=3))
    ax.text(-2.2, 2.6, "аппарель", fontsize=6, ha="center", color=ЛИНИЯ)
    ax.text(2.5, 0, "терраса", fontsize=6, ha="center", va="center", color=ЛИНИЯ, zorder=7)
    ax.text(G.LOA - 5, 0, "носовая\nпалуба", fontsize=6, ha="center", va="center", color=ЛИНИЯ, zorder=7)
    ax.annotate("нос →", (G.LOA - 4, 9.6), fontsize=7, color="#7d858f")


def imя_short(s):
    return s.split(",")[0].split(":")[0]


# ----------------------------------------------------------------- 3. сечения
def сечение(ax, x, заголовок, атриум):
    ax.set_aspect("equal")
    ax.set_xlim(-10.5, 10.5)
    ax.set_ylim(-0.6, 12.0)
    ax.axis("off")
    ax.set_title(заголовок, fontsize=9, loc="left", color=ЛИНИЯ)
    ax.add_patch(Rectangle((-10.5, -0.6), 21, G.DRAFT + 0.6, facecolor=ВОДА, edgecolor="none", zorder=0))
    # полусечение корпуса
    zk = L.keel_z(x); bb = L.side_half(x); bk = min(L.bottom_half(x), bb); phi = math.radians(L.flare(x))
    пол = [(bk * i / 5.0, zk) for i in range(6)]
    for i in range(1, 21):
        z = zk + (G.DEPTH - zk) * i / 20.0
        y = L.section_y(z, zk, bk, G.DEPTH, bb, phi)
        пол.append((y if y is not None else bk, z))
    if атриум:
        нш = W.niche_half(x)
        пол = [(min(y, нш), z) for y, z in пол]
    контур = пол + [(-y, z) for y, z in reversed(пол)]
    ax.add_patch(Polygon(контур, closed=True, facecolor="none", edgecolor=ЧЁРНЫЙ, lw=2.2, zorder=3))
    # второе дно и палубы
    ax.plot([-bk, bk], [G.DECKS["первая"]] * 2, color=ЛИНИЯ, lw=0.9, zorder=3)
    y_гл = SU.полуширота(x, "главная") if not атриум else SU.кожух()["y_внутр"]
    ax.plot([-bb, bb], [G.DECKS["главная"]] * 2, color=ЛИНИЯ, lw=1.2, zorder=3)
    # ярусы с завалом
    for код, цвет in (("главная", СЕРЕБРО), ("средняя", ГРАФИТ)):
        я = SU.ЯРУСЫ[код]
        y0 = SU.полуширота(x, код, z=я["z0"])
        y1 = SU.полуширота(x, код, z=я["z1"])
        if y0 <= 0.1:
            continue
        ax.add_patch(Polygon([(-y0, я["z0"]), (y0, я["z0"]), (y1, я["z1"]), (-y1, я["z1"])], closed=True,
                             facecolor=цвет, edgecolor=ЛИНИЯ, lw=0.8, zorder=4, alpha=0.95))
    ax.plot([-SU.полуширота(x, "средняя", z=G.DECKS["солнечная"]) - SU.КАРНИЗ, SU.полуширота(x, "средняя", z=G.DECKS["солнечная"]) + SU.КАРНИЗ],
            [G.DECKS["солнечная"]] * 2, color=ЛИНИЯ, lw=1.2, zorder=5)
    ax.plot([-bb, -bb], [G.DEPTH, G.DEPTH + 1.1], color="#7d858f", lw=0.6); ax.plot([bb, bb], [G.DEPTH, G.DEPTH + 1.1], color="#7d858f", lw=0.6)
    if атриум:
        # кожухи, колёса, атриум
        к = SU.кожух()
        z0 = W.axis_height(G.DRAFT)
        п = SU.портал_блок()
        for s in (1, -1):
            ax.add_patch(Rectangle((п["y_внутр"] if s > 0 else -п["y_наруж"], п["z0"]), п["y_наруж"] - п["y_внутр"],
                                   п["z1"] - п["z0"], facecolor=СЕРЕБРО, edgecolor=ЛИНИЯ, lw=0.8, zorder=5))
            ax.add_patch(Rectangle((п["y_наруж"] - 0.12 if s > 0 else -п["y_наруж"] + 0.06, п["z_атриум0"]), 0.06,
                                   п["z_атриум1"] - п["z_атриум0"], facecolor=СТЕКЛО, edgecolor="none", zorder=6))
            yc = s * (к["колесо_внутр"] + W.WIDTH / 2.0)
            ax.add_patch(Rectangle((yc - W.BLADE_SPAN / 2.0, z0 - W.PIVOT_RADIUS - W.BLADE_HEIGHT), W.BLADE_SPAN,
                                   2 * W.PIVOT_RADIUS + W.BLADE_HEIGHT, facecolor=КРАСНЫЙ, edgecolor="#7a0a1c", lw=0.6, zorder=6, alpha=0.85))
            ax.plot([yc - W.WIDTH / 2.0 + 0.12] * 2, [z0 - W.PIVOT_RADIUS, z0 + W.PIVOT_RADIUS], color="#c9ced4", lw=2.0, zorder=7)
            ax.plot([yc + W.WIDTH / 2.0 - 0.12] * 2, [z0 - W.PIVOT_RADIUS, z0 + W.PIVOT_RADIUS], color="#c9ced4", lw=2.0, zorder=7)
            ax.plot([s * (к["y_внутр"] + 0.03), yc + s * 0.0], [z0, z0], color="#c9ced4", lw=3.0, zorder=7)
            ax.add_patch(Rectangle((s * 3.0 if s > 0 else -4.6, G.DECKS["главная"]), 1.6, 1.4, facecolor="#e2e2e2", edgecolor=ЛИНИЯ, lw=0.5, zorder=6))
            ax.text(s * 3.8, G.DECKS["главная"] + 0.7, "ГЭД", ha="center", va="center", fontsize=6, color=ЛИНИЯ, zorder=7)
        ax.text(0, (G.DECKS["главная"] + G.DECKS["солнечная"]) / 2, "АТРИУМ\nдвухсветный\nтрап и лифты", ha="center", va="center",
                fontsize=7, color=ЛИНИЯ, zorder=7)
        ax.text(0, G.DECKS["первая"] + 1.0, "провизия", ha="center", va="center", fontsize=6.5, color=ЛИНИЯ, zorder=7)
        ax.text(0, G.DECKS["солнечная"] + 0.55, "световой фонарь, солнечные модули", ha="center", fontsize=6, color=ЛИНИЯ)
    else:
        # каюты: борт 3,00 - коридор 1,30 - внутренняя
        for палуба, код in (("главная", "главная"), ("средняя", "средняя")):
            z0 = G.DECKS[палуба]; z1 = z0 + G.DECK_PITCH
            yб = SU.полуширота(x, код, z=z0 + 0.6) - G.LINING / 2.0
            гв = GA.глубина_внутренней(палуба, x)
            for s in (1, -1):
                ax.add_patch(Rectangle((s * (yб - GA.ГЛУБИНА_БОРТ) if s > 0 else -yб, z0), GA.ГЛУБИНА_БОРТ, z1 - z0 - G.LINING,
                                       facecolor="#f3e6de", edgecolor=ЛИНИЯ, lw=0.5, zorder=5))
                ax.add_patch(Rectangle((s * (yб - GA.ГЛУБИНА_БОРТ - GA.КОРИДОР) if s > 0 else -(yб - GA.ГЛУБИНА_БОРТ), z0), GA.КОРИДОР,
                                       z1 - z0 - G.LINING, facecolor="#fbfbf7", edgecolor=ЛИНИЯ, lw=0.5, zorder=5))
                ax.add_patch(Rectangle((0 if s > 0 else -гв, z0), гв, z1 - z0 - G.LINING, facecolor="#efe7ef", edgecolor=ЛИНИЯ, lw=0.5, zorder=5))
                ax.text(s * (yб - GA.ГЛУБИНА_БОРТ / 2), z0 + 1.1, "каюта\n3,00", ha="center", va="center", fontsize=6, color=ЛИНИЯ, zorder=6)
                ax.text(s * (yб - GA.ГЛУБИНА_БОРТ - GA.КОРИДОР / 2), z0 + 1.1, "1,3", ha="center", va="center", fontsize=5.5, color=ЛИНИЯ, zorder=6, rotation=90)
                ax.text(s * гв / 2, z0 + 1.1, "внутр.\n%.2f" % гв, ha="center", va="center", fontsize=6, color=ЛИНИЯ, zorder=6)
            ax.text(0, z1 - 0.18, "зашивка 0,35 · в свету 2,33", ha="center", va="center", fontsize=5.5, color="#7d858f", zorder=6)
        ax.text(0, G.DECKS["первая"] + 1.0, "трюм - техника, в свету 1,85", ha="center", va="center", fontsize=6.5, color=ЛИНИЯ, zorder=7)
    ax.plot([-10.5, 10.5], [G.DRAFT] * 2, color="#2f6f9a", lw=0.8, ls="--", zorder=8)
    ax.plot([-10.5, 10.5], [G.DRAFT + 8.5] * 2, color="#7a1020", lw=0.6, ls=":", zorder=8)
    ax.text(10.3, G.DRAFT + 8.6, "8,5 над водой", fontsize=6, color="#7a1020", ha="right")
    ax.text(-10.3, 0.05, "ОП", fontsize=6, color=ЛИНИЯ)


def build(verbose=True):
    fig = plt.figure(figsize=(24, 5.2), dpi=150)
    ax = fig.add_axes([0.01, 0.02, 0.98, 0.86]); борт(ax)
    fig.text(0.01, 0.94, "1. Вид с правого борта - «Волжский Горизонт», %.0f × %.1f м, осадка %.2f" % (G.LOA, G.BEAM, G.DRAFT),
             fontsize=12, fontweight="bold", color=ЛИНИЯ)
    fig.text(0.01, 0.905, "стеклянный монолит в светлой раме. Оба яруса - тёмное стекло, рама - цоколь, карнизы, наклонные торцы · портал во всю высоту с колесом внизу и атриумом над ним · красная линия ныряет только там",
             fontsize=8, color="#7d858f")
    p1 = os.path.join(OUT, "1_борт.png"); fig.savefig(p1); plt.close(fig)

    fig = plt.figure(figsize=(24, 5.0), dpi=150)
    ax = fig.add_axes([0.01, 0.02, 0.98, 0.86]); план(ax)
    fig.text(0.01, 0.94, "2. Вид сверху", fontsize=12, fontweight="bold", color=ЛИНИЯ)
    fig.text(0.01, 0.905, "прогулочная палуба (крыша главной) с красной кромкой · солнечная палуба · солнечные модули над атриумом · рубка · ниши колёс в корпусе",
             fontsize=8, color="#7d858f")
    p2 = os.path.join(OUT, "2_план.png"); fig.savefig(p2); plt.close(fig)

    fig, (a1, a2) = plt.subplots(1, 2, figsize=(16, 8.2), dpi=150)
    сечение(a1, X, "3а. Сечение по оси колёс, x = %.0f - ниши, кожухи, атриум" % X, True)
    сечение(a2, 45.0, "3б. Сечение по каютному блоку, x = 45", False)
    fig.suptitle("3. Поперечные сечения", fontsize=12, fontweight="bold", color=ЛИНИЯ, x=0.01, ha="left")
    fig.tight_layout(rect=(0, 0, 1, 0.95))
    p3 = os.path.join(OUT, "3_сечения.png"); fig.savefig(p3); plt.close(fig)
    if verbose:
        for p in (p1, p2, p3):
            print("  ", os.path.basename(p))
    return p1, p2, p3


if __name__ == "__main__":
    build()
