# -*- coding: utf-8 -*-
"""Планировки кают по нормам, с проверкой эргономики кодом.

    python scripts/планы_кают.py

Нормы — СанПиН 2.5.2-703-98 «Суда внутреннего и смешанного плавания»,
раздел 2.1 (судовые помещения):

    п. 2.1.1.6  высота в свету: 2,0 м при одноярусных койках, 2,2 при двухъярусных
    п. 2.1.1.7  нижняя койка 400 мм от палубы, верхняя не ниже 800 мм над нижней,
                от верхней до подволока не менее 800 мм
    п. 2.1.1.8  проход у койки: одноместная 700, двухместная 800, 3–4-местная 850 мм
    п. 2.1.1.9  койка не менее 2000 x 800 мм, свободный доступ не менее 2/3 длины

Сверх СанПиН — практика речных круизных судов: санузел не меньше
1,2 x 1,5 м (душ, унитаз, раковина), дверь каюты 0,70 м, для М4 — 0,90 м,
душ без порога и круг разворота 1,5 м (`gorizont.TURN_CIRCLE`).

Каждая каюта — список прямоугольников мебели. Проверка `эргономика()`
считает: мебель не пересекается и не выходит за стены; у каждой койки есть
проход нужной ширины вдоль не менее 2/3 длины; сектор двери свободен;
у М4 круг разворота свободен. Лист не сохраняется, пока проверка не
прошла: план с наложениями — это не план.
"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Wedge

from lib import gorizont as G, gorizont_ga as GA

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "планы")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 7.5,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
INK, GRY, ACC, SEA = "#16202f", "#8a94a6", "#b02634", "#1c5c8a"

# нормы и расстановка — в библиотеке, общей с моделью
from lib.gorizont_cabin_layout import *   # noqa: F401,F403
from lib import gorizont_cabin_layout as КЛ

def _пересекаются(a, b, зазор=1e-6):
    """Касание — не пересечение; допуск 1 мкм гасит хвосты плавающей точки
    (1,4 − 0,8 = 0,5999…, и шкаф высотой 0,6 «лез» в проход на 10⁻¹⁶ м)."""
    return not (a[0] + a[2] <= b[0] + зазор or b[0] + b[2] <= a[0] + зазор
                or a[1] + a[3] <= b[1] + зазор or b[1] + b[3] <= a[1] + зазор)


def _свободна(прямоугольник, мебель, кроме=()):
    """Прямоугольник пола не занят мебелью (кроме указанной)."""
    for имя, x, y, w, h, кл in мебель:
        if имя in кроме:
            continue
        if _пересекаются(прямоугольник, (x, y, w, h)):
            return False
    return True


def эргономика(тип):
    """Проверки по нормам. Возвращает список (проверка, ок, пояснение)."""
    к = GA.КАЮТЫ[тип]
    ф, гл, м = мебель(тип)
    мест = k = к["мест"]
    ярусов = 2 if any("2-яр" in n for n, *_ in м) else 1
    вых = []
    # 1) в стенах
    вых.append(("Мебель в стенах", all(x >= -1e-6 and y >= -1e-6 and x + w <= ф + 1e-6 and y + h <= гл + 1e-6
                                        for _, x, y, w, h, _ in м), ""))
    # 2) не пересекается
    пары = [(a[0], b[0]) for i, a in enumerate(м) for b in м[i + 1:] if _пересекаются(a[1:5], b[1:5])]
    вых.append(("Мебель не пересекается", not пары, "; ".join("%s × %s" % p for p in пары)))
    # 3) койки по размеру
    койки = [f for f in м if f[5] == "койка"]
    ок = all(max(f[3], f[4]) >= КОЙКА_L - 1e-6 and min(f[3], f[4]) >= КОЙКА_B - 1e-6 for f in койки)
    вых.append(("Койки не меньше 2,0 x 0,8 (СанПиН 2.1.1.9)", ок,
                ", ".join("%.1fx%.1f" % (f[3], f[4]) for f in койки)))
    # 4) проход у каждой койки вдоль 2/3 длины
    норма = ПРОХОД[min(мест, 4)]
    плохие = []
    for имя, x, y, w, h, кл in койки:
        вдоль_x = w >= h                       # койка лежит вдоль x
        L_ = w if вдоль_x else h
        кандидаты = []
        if вдоль_x:
            кандидаты = [(x, y - норма, w, норма), (x, y + h, w, норма)]
        else:
            кандидаты = [(x - норма, y, норма, h), (x + w, y, норма, h)]
        есть = False
        for r in кандидаты:
            # полоса прохода: внутри стен и не занята другой мебелью не менее чем на 2/3 длины
            if r[0] < -1e-6 or r[1] < -1e-6 or r[0] + r[2] > ф + 1e-6 or r[1] + r[3] > гл + 1e-6:
                continue
            # делим полосу на 12 кусков и считаем свободные
            своб = 0
            for i in range(12):
                if вдоль_x:
                    кусок = (r[0] + r[2] * i / 12.0, r[1], r[2] / 12.0, r[3])
                else:
                    кусок = (r[0], r[1] + r[3] * i / 12.0, r[2], r[3] / 12.0)
                if _свободна(кусок, м, кроме=(имя,)):
                    своб += 1
            if своб >= 8:
                есть = True
                break
        if not есть:
            плохие.append(имя)
    вых.append(("Проход у койки >= %.2f м на 2/3 длины (СанПиН 2.1.1.8)" % норма, not плохие, ", ".join(плохие)))
    # 5) санузел не меньше минимума
    су = [f for f in м if f[5] == "санузел"][0]
    ок = min(су[3], су[4]) >= САНУЗЕЛ_МИН[0] - 1e-6 and max(су[3], су[4]) >= САНУЗЕЛ_МИН[1] - 1e-6
    вых.append(("Санузел не меньше 1,2 x 1,5", ок, "%.1f x %.1f" % (су[3], су[4])))
    # 6) дверь каюты: сектор свободен; дверь у коридора, слева от санузла
    дв = ДВЕРЬ_М4 if к.get("М4") else ДВЕРЬ
    xд = су[1] - дв - 0.05
    сектор = (xд, 0.0, дв, дв)
    вых.append(("Сектор двери %.2f м свободен" % дв, _свободна(сектор, м), ""))
    # 7) М4: круг разворота
    if к.get("М4"):
        R = G.TURN_CIRCLE / 2.0
        центр = None
        for cx in (x / 10.0 for x in range(int(R * 10), int((ф - R) * 10) + 1)):
            for cy in (y / 10.0 for y in range(int(R * 10), int((гл - R) * 10) + 1)):
                if _свободна((cx - R, cy - R, 2 * R, 2 * R), м):
                    центр = (cx, cy)
                    break
            if центр:
                break
        вых.append(("Круг разворота Ø%.1f свободен" % G.TURN_CIRCLE, центр is not None,
                    "центр (%.1f, %.1f)" % центр if центр else "нет места"))
    # 8) высота
    вых.append(("Высота в свету %.2f >= %.1f (СанПиН 2.1.1.6)" % (ВЫСОТА_В_СВЕТУ, ВЫСОТА_НОРМА[ярусов]),
                ВЫСОТА_В_СВЕТУ >= ВЫСОТА_НОРМА[ярусов], ""))
    # 9) площадь по КЗ
    вых.append(("Площадь %.1f м² >= 8 (КЗ п. 6)" % (ф * гл), ф * гл >= 8.0, ""))
    return вых, центр if к.get("М4") else None


def каюта(ax, тип):
    к = GA.КАЮТЫ[тип]
    ф, гл, м = мебель(тип)
    проверки, центр = эргономика(тип)
    ax.set_xlim(-0.45, ф + 0.45)
    ax.set_ylim(-0.95, гл + 0.55)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((-0.2, -0.2), ф + 0.4, гл + 0.4, facecolor="#f2f2f0", edgecolor=INK, lw=1.2, zorder=1))
    ax.add_patch(Rectangle((0, 0), ф, гл, facecolor="white", edgecolor=INK, lw=0.8, zorder=1))
    ax.text(ф / 2.0, -0.6, "коридор 1,30 м", ha="center", va="center", fontsize=6, color=GRY)
    for имя, x, y, w, h, кл in м:
        ax.add_patch(Rectangle((x, y), w, h, facecolor=ЦВЕТ[кл], edgecolor=INK, lw=0.6, zorder=2))
        ax.text(x + w / 2.0, y + h / 2.0, имя, ha="center", va="center", fontsize=5.4, color=INK, zorder=3,
                rotation=90 if h > w * 1.6 else 0)
    су = [f for f in м if f[5] == "санузел"][0]
    дв = ДВЕРЬ_М4 if к.get("М4") else ДВЕРЬ
    xд = су[1] - дв - 0.05
    ax.add_patch(Wedge((xд, 0), дв, 0, 90, facecolor="none", edgecolor=INK, lw=0.6, ls=":", zorder=3))
    ax.plot([xд, xд], [0, дв], color=INK, lw=1.2, zorder=3)
    ax.text(xд + дв / 2.0, -0.28, "дверь %.2f" % дв, ha="center", fontsize=5, color=GRY)
    if тип == "семейная":
        ax.plot([ф / 2.0, ф / 2.0], [1.2, гл], color=INK, lw=0.8, ls=(0, (3, 2)), zorder=3)
        ax.text(ф / 2.0 + 0.12, гл - 0.9, "раздвижная перегородка", fontsize=5, color=GRY, rotation=90, va="center")
    if центр:
        ax.add_patch(Circle(центр, G.TURN_CIRCLE / 2.0, fill=False, ec=SEA, lw=0.8, ls="--", zorder=3))
        ax.text(центр[0], центр[1], "Ø1,5", ha="center", va="center", fontsize=5.5, color=SEA)
    if к["окно"]:
        ax.plot([0.3, ф - 0.3], [гл + 0.06, гл + 0.06], color=SEA, lw=2.2, zorder=3)
        ax.text(ф / 2.0, гл + 0.25, "окно", ha="center", fontsize=5.5, color=SEA)
    else:
        ax.text(ф / 2.0, гл + 0.25, "внутренняя: световод, виртуальное окно", ha="center", fontsize=5.5, color=SEA)
    ok = all(p[1] for p in проверки)
    ax.set_title("%s — %.1f x %.2f м = %.1f м², %d мест   %s" % (тип, ф, гл, ф * гл, к["мест"], "✓" if ok else "✗"),
                 fontsize=8.5, color=INK if ok else ACC, loc="left")
    return проверки


def build(verbose=True):
    типы = ["люкс", "бизнес", "стандарт", "стандарт М4", "семейная", "эконом"]
    fig, axes = plt.subplots(2, 3, figsize=(16, 9.6), dpi=140)
    итог, плохо = [], 0
    for ax, т in zip(axes.flat, типы):
        пр = каюта(ax, т)
        for имя, ok, поясн in пр:
            итог.append((т, имя, ok, поясн))
            if not ok:
                плохо += 1
    и = GA.итоги()
    fig.suptitle("Планировки кают «Волжского Горизонта» — %d пассажиров в %d каютах, %d кают М4; нормы СанПиН 2.5.2-703-98"
                 % (и["пассажиров"], и["пассажирских_кают"], и["кают_М4"]), fontsize=12, fontweight="bold", color=INK, x=0.02, ha="left")
    fig.text(0.02, 0.945, "Койка 2,0 x 0,8; проход у койки 0,80 (2 места) / 0,85 (4 места); высота в свету %.2f м; "
             "санузел не меньше 1,2 x 1,5; дверь 0,70, для М4 0,90 и круг разворота 1,5. Проверок %d, не прошло %d."
             % (ВЫСОТА_В_СВЕТУ, len(итог), плохо), fontsize=8, color=INK if not плохо else ACC)
    fig.tight_layout(rect=(0, 0, 1, 0.93))
    p = os.path.join(OUT, "5_каюты.png")
    if плохо:
        p = os.path.join(OUT, "5_каюты_НЕ_ПРОШЛО.png")
    fig.savefig(p)
    plt.close(fig)
    if verbose:
        for т, имя, ok, поясн in итог:
            if not ok:
                print("  НЕ ПРОШЛО: %-12s %s %s" % (т, имя, поясн))
        print("  ", os.path.basename(p), "— проверок %d, не прошло %d" % (len(итог), плохо))
    return p, плохо


if __name__ == "__main__":
    _, n = build()
    sys.exit(1 if n else 0)
