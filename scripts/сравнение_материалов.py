# -*- coding: utf-8 -*-
"""Сравнительный анализ материалов корпуса с визуализацией.

    python scripts/сравнение_материалов.py

Лист А2: таблица характеристик трёх сталей, четыре диаграммы и вывод.
Числа считает `gorizont_materials.compare()` — от расчётного напряжения
общей прочности до массы связей и цены.
"""
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

import matplotlib
matplotlib.use("Agg")

from lib import gorizont_materials as M
from lib import eskd

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
INK, ACC, SEA, GRN, GRY = "#16202f", "#b02634", "#1c5c8a", "#1f7a5a", "#9aa4b4"
BAR = {"ВСт3сп5": "#b7772a", "09Г2С": "#1f7a5a", "AH36": "#1c5c8a"}


def _bars(ax, rows, key, title, unit, fmt="%.0f", line=None, line_lab=""):
    names = [r["key"] for r in rows]
    vals = [r[key] for r in rows]
    xs = range(len(names))
    ax.bar(xs, vals, width=0.58,
           color=[BAR[n] for n in names], edgecolor="white", linewidth=0.8)
    for x, v in zip(xs, vals):
        ax.text(x, v, fmt % v, ha="center", va="bottom", fontsize=8.5,
                color=INK, fontweight="bold")
    if line is not None:
        ax.axhline(line, color=ACC, lw=1.4, ls="--")
        ax.text(len(names) - 0.42, line, line_lab, fontsize=8.0, color=ACC,
                ha="right", va="bottom")
    ax.set_xticks(list(xs))
    ax.set_xticklabels(names, fontsize=9)
    ax.set_title("%s, %s" % (title, unit), fontsize=10.5, color=INK,
                 fontweight="bold", loc="left", pad=8)
    ax.set_ylim(0, max(vals + ([line] if line else [])) * 1.22)
    ax.tick_params(labelsize=8, colors="#56627a")
    for sp in ("top", "right"):
        ax.spines[sp].set_visible(False)
    for sp in ("left", "bottom"):
        ax.spines[sp].set_color("#c8cfd9")
    ax.grid(axis="y", color="#e6eaf0", lw=0.7)
    ax.set_axisbelow(True)


def build(verbose=True):
    c = M.compare()
    rows = c["rows"]
    sh = eskd.Sheet("A2", mark="ВГ-2026.00.00 ПМ",
                    name="Сравнительный анализ" + chr(10) + "материалов корпуса",
                    material=None, mass=None, scale="—",
                    sheet_no=1, sheets=1)

    # --- таблица характеристик
    tab = [["Показатель"] + [r["name"] for r in rows],
           ["Нормативный документ"] + [r["nd"] for r in rows],
           ["Предел текучести ReH, МПа"] + ["%.0f" % r["ReH"] for r in rows],
           ["Временное сопротивление Rm, МПа"]
           + ["%.0f…%.0f" % r["Rm"] for r in rows],
           ["Относительное удлинение δ5, %"] + ["%.0f" % r["d5"] for r in rows],
           ["Ударная вязкость KCU, Дж/см²"]
           + ["%.0f при %+.0f °C" % (r["kcu"], r["kcu_t"]) for r in rows],
           ["Углеродный эквивалент Cэкв, %"] + ["%.2f" % r["ceq"] for r in rows],
           ["Допускаемое 0,60·ReH, МПа"] + ["%.0f" % r["allow"] for r in rows],
           ["Расчётное напряжение, МПа"] + ["%.1f" % r["sigma"] for r in rows],
           ["Проверка общей прочности"]
           + ["проходит, запас %.0f %%" % ((r["margin"] - 1) * 100)
              if r["ok"] else "не проходит" for r in rows],
           ["Потребная масса связей, т"] + ["%.0f" % r["mass"] for r in rows],
           ["Цена стали, тыс. ₽/т"] + ["%.0f" % r["price"] for r in rows],
           ["Стоимость связей, млн ₽"] + ["%.1f" % r["cost"] for r in rows],
           ["Свариваемость"] + [r["weld"] for r in rows],
           ["Поставка"] + [r["supply"] for r in rows]]

    import textwrap
    x0 = eskd.MARGIN_L + 4.0
    y0 = sh.H - eskd.MARGIN - 8.0
    col = [122.0, 92.0, 92.0, 88.0]
    W = sum(col)
    hs = []
    for r in tab:
        n = 1
        for j_, v in enumerate(r):
            lim = max(6, int((col[j_] - 3.0) / 1.45))
            n = max(n, len(textwrap.wrap(str(v), lim)))
        hs.append(max(8.0, n * 3.8 + 3.4))
    sh._line(x0, y0, x0 + W, y0, eskd.THICK)
    yy = y0
    for i_, r in enumerate(tab):
        h = hs[i_]
        cx = x0
        for j_, v in enumerate(r):
            lim = max(6, int((col[j_] - 3.0) / 1.45))
            lines = textwrap.wrap(str(v), lim)
            for m, ln in enumerate(lines):
                ty = yy - h / 2.0 + (len(lines) - 1 - 2 * m) * 1.9
                sh._text(cx + 1.8, ty, ln, size=2.5,
                         bold=(i_ == 0 or (j_ == 0 and i_ in (8, 9, 12))))
            cx += col[j_]
        yy -= h
        sh._line(x0, yy, x0 + W, yy, eskd.THICK if i_ == 0 else eskd.THIN)
    cx = x0
    for w in col + [0]:
        sh._line(cx, y0, cx, yy)
        cx += w

    # --- вывод справа от таблицы
    vx = x0 + W + 14.0
    sh._text(vx, y0 - 4.0, "Вывод", size=4.2, bold=True)
    ty = y0 - 13.0
    for t in M.verdict():
        for k, ln in enumerate(textwrap.wrap(t, 46)):
            sh._text(vx + (0.0 if k == 0 else 3.5), ty,
                     ("— " if k == 0 else "") + ln, size=2.7)
            ty -= 5.4
        ty -= 2.6
    sh._text(vx, ty - 2.0,
             "Принята 09Г2С категории 12 по ГОСТ 19281-2014.", size=3.0,
             bold=True)

    # --- диаграммы
    ax_h = 148.0
    ax_y = yy - ax_h - 20.0
    w_ax = 126.0
    gap = 14.0
    for i_, (key, title, unit, fmt, line, lab) in enumerate([
            ("allow", "Допускаемое напряжение", "МПа", "%.0f",
             c["sigma"], "расчётное %.1f" % c["sigma"]),
            ("kcu", "Ударная вязкость", "Дж/см²", "%.0f", None, ""),
            ("mass", "Потребная масса связей", "т", "%.0f", None, ""),
            ("cost", "Стоимость связей", "млн ₽", "%.1f", None, "")]):
        ax = sh.axes(x0 + i_ * (w_ax + gap), ax_y, w_ax, ax_h)
        ax.axis("on")
        _bars(ax, rows, key, title, unit, fmt, line, lab)

    p = sh.save(os.path.join(OUT, "14_сравнение_материалов.png"))
    if verbose:
        print("сравнение материалов: расчётное %.1f МПа" % c["sigma"])
        for r in rows:
            print("  %-9s допуск %5.1f  %-11s масса %5.0f т  %5.1f млн ₽"
                  % (r["key"], r["allow"],
                     "проходит" if r["ok"] else "не проходит",
                     r["mass"], r["cost"]))
        print("  ", os.path.basename(p))
    return p


if __name__ == "__main__":
    build()
