# -*- coding: utf-8 -*-
"""Схема автономного управления и исключения столкновений.

    python scripts/схема_автономности.py

Лист А2 - цепочка расхождения в метрах, дальности датчиков, состав системы,
поведение при отказах и проверки. Числа считает `gorizont_autonomy`.
"""
import os, sys, math

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

import matplotlib
matplotlib.use("Agg")
from matplotlib.patches import Rectangle, Polygon as MPoly, Circle

from lib import gorizont_autonomy as A
from lib import gorizont as G
from lib import eskd

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
INK, ACC, SEA, GRN, GRY = "#16202f", "#b02634", "#1c5c8a", "#1f7a5a", "#9aa4b4"
WARM = "#b7772a"


def _chain(ax, r, s):
    """Цепочка расхождения - от обнаружения до полной остановки."""
    need = r["required"]
    ax.set_xlim(-60, need * 1.06)
    ax.set_ylim(-34, 40)
    ax.axis("off")
    # линия пути
    ax.plot([0, need], [0, 0], color=GRY, lw=1.0)
    marks = [
        (0.0, "препятствие", ACC),
        (r["stop"], "судно остановилось\n%.0f м" % r["stop"], SEA),
        (r["manoeuvre"], "решение и реверс\n%.0f м" % r["manoeuvre"], GRN),
        (need, "обнаружение\n%.0f м, двойной запас" % need, WARM),
    ]
    for x, lab, col in marks:
        ax.plot([x, x], [-6, 6], color=col, lw=2.0)
        ax.text(x, 10, lab, ha="center", va="bottom", fontsize=8.5,
                color=col, fontweight="bold")
    # зоны
    ax.add_patch(Rectangle((0, -5), r["stop"], 10, facecolor="#e8eef6",
                           edgecolor="none", zorder=0))
    ax.add_patch(Rectangle((r["stop"], -5), r["manoeuvre"] - r["stop"], 10,
                           facecolor="#e7f2ec", edgecolor="none", zorder=0))
    ax.add_patch(Rectangle((r["manoeuvre"], -5), need - r["manoeuvre"], 10,
                           facecolor="#f6efe4", edgecolor="none", zorder=0))
    ax.text(r["stop"] / 2.0, -12, "тормозной путь реверсом\n%.0f м, %.0f с"
            % (r["stop"], s["time"]), ha="center", va="top", fontsize=8.0,
            color=SEA)
    ax.text((r["stop"] + r["manoeuvre"]) / 2.0, -12,
            "путь за время реакции\n%.0f м, %.0f с" % (r["run"], r["t_total"]),
            ha="center", va="top", fontsize=8.0, color=GRN)
    ax.text((r["manoeuvre"] + need) / 2.0, -12,
            "запас на классификацию цели\nи выбор стороны расхождения",
            ha="center", va="top", fontsize=8.0, color=WARM)
    # судно
    L = 46.0
    hull = [(need + L, 18), (need + 10, 18), (need, 24), (need + 10, 30),
            (need + L, 30)]
    ax.add_patch(MPoly(hull, closed=True, facecolor="#cdd7e4",
                       edgecolor=INK, lw=1.0))
    ax.annotate("", (need - 40, 24), (need + 4, 24),
                arrowprops=dict(arrowstyle="-|>", color=INK, lw=1.4))
    ax.text(need + L + 12, 24, "%d км/ч" % G.SPEED_KMH, fontsize=8.5,
            color=INK, va="center")


def _ranges(ax, cov):
    """Дальности датчиков в логарифмическом масштабе."""
    rows = sorted(cov["rows"], key=lambda r: r["range"])
    ax.set_xscale("log")
    ax.set_xlim(80, 60000)
    ax.set_ylim(-0.8, len(rows) - 0.2)
    ax.axvline(cov["need"], color=ACC, lw=1.6, ls="--")
    ax.text(cov["need"] * 1.08, len(rows) - 0.6,
            "потребная дальность\n%.0f м" % cov["need"], fontsize=8.0,
            color=ACC, va="top")
    for i, r in enumerate(rows):
        col = GRN if r["ok"] else ACC
        ax.barh(i, r["range"] - 80, left=80, height=0.5, color=col,
                alpha=0.85, edgecolor="white")
        ax.text(90, i + 0.34, r["name"], fontsize=8.0, color=INK, va="bottom")
        lab = ("%.0f м" % r["range"] if r["range"] < 1000
               else "%.0f км" % (r["range"] / 1000.0))
        if not r["ok"]:
            lab += "  ·  ближняя зона"
        ax.text(r["range"] * 1.06, i, lab, fontsize=8.0, color=col,
                va="center")
    ax.set_yticks([])
    ax.tick_params(axis="x", labelsize=8, colors="#56627a")
    ax.set_xlabel("дальность, м (логарифмическая шкала)", fontsize=8.5,
                  color="#56627a")
    for sp in ("top", "right", "left"):
        ax.spines[sp].set_visible(False)
    ax.spines["bottom"].set_color("#c8cfd9")
    ax.grid(axis="x", color="#e6eaf0", lw=0.7)
    ax.set_axisbelow(True)


def _table(sh, x, y, cols, rows, size=2.3, head=2.4, row_h=None):
    import textwrap
    total = sum(w for _, w in cols)
    hs = []
    wrapped_rows = []
    for r in rows:
        w_cells, n = [], 1
        for j, (_, w) in enumerate(cols):
            v = str(r[j]) if j < len(r) else ""
            lim = max(6, int((w - 2.5) / (size * 0.55)))
            lines = textwrap.wrap(v, lim) if v else []
            w_cells.append(lines)
            n = max(n, len(lines))
        wrapped_rows.append(w_cells)
        hs.append(max(row_h or 6.0, n * size * 1.5 + 2.2))
    hh = 7.0
    sh._line(x, y, x + total, y, eskd.THICK)
    sh._line(x, y - hh, x + total, y - hh, eskd.THICK)
    cx = x
    bottom = y - hh - sum(hs)
    for name, w in cols:
        sh._line(cx, y, cx, bottom)
        sh._text(cx + w / 2.0, y - hh / 2.0, name, size=head, ha="center")
        cx += w
    sh._line(cx, y, cx, bottom)
    yy = y - hh
    for i, cells in enumerate(wrapped_rows):
        h = hs[i]
        sh._line(x, yy - h, x + total, yy - h)
        cx = x
        for j, (_, w) in enumerate(cols):
            for m, ln in enumerate(cells[j]):
                ty = yy - h / 2.0 + (len(cells[j]) - 1 - 2 * m) * size * 0.78
                sh._text(cx + 1.4, ty, ln, size=size)
            cx += w
        yy -= h
    return bottom


def build(verbose=True):
    r = A.report()
    sh = eskd.Sheet("A2", mark="ВГ-2026.00.00 ПМ2",
                    name="Автономное управление" + chr(10)
                         + "и исключение столкновений",
                    material=None, mass=None, scale="-",
                    sheet_no=1, sheets=1)
    x0 = eskd.MARGIN_L + 4.0
    top = sh.H - eskd.MARGIN - 6.0

    sh._text(x0, top - 4.0, "Цепочка расхождения", size=4.2, bold=True)
    sh._text(x0, top - 11.0, r["degree_name"], size=2.8, color="#56627a")
    ax = sh.axes(x0, top - 86.0, 470.0, 70.0)
    _chain(ax, r["reaction"], r["stopping"])

    sh._text(x0, top - 96.0, "Дальности датчиков", size=4.2, bold=True)
    ax2 = sh.axes(x0 + 6.0, top - 190.0, 250.0, 86.0)
    ax2.axis("on")
    _ranges(ax2, r["coverage"])

    # таблица датчиков справа
    sh._text(x0 + 276.0, top - 96.0, "Состав и резервирование", size=4.2,
             bold=True)
    _table(sh, x0 + 276.0, top - 102.0,
           [("Датчик", 72.0), ("Что даёт", 108.0), ("Резерв", 62.0)],
           [[n, w, b] for n, _, w, b in A.SENSORS], size=2.3)

    # функции
    yf = top - 202.0
    sh._text(x0, yf, "Функции системы", size=4.2, bold=True)
    bottom = _table(sh, x0, yf - 6.0,
                    [("Функция", 62.0), ("Чем реализуется", 190.0)],
                    [[a, b] for a, b in A.FUNCTIONS], size=2.3)

    # отказы
    sh._text(x0 + 276.0, yf, "Поведение при отказах", size=4.2, bold=True)
    _table(sh, x0 + 276.0, yf - 6.0,
           [("Отказ", 66.0), ("Что происходит", 176.0)],
           [[a, b] for a, b in A.FAILSAFE], size=2.3)

    # проверки
    yc = bottom - 10.0
    sh._text(x0, yc, "Проверки", size=4.2, bold=True)
    _table(sh, x0, yc - 6.0,
           [("Проверка", 74.0), ("Значение", 24.0), ("Требуется", 24.0),
            ("Ед.", 14.0), ("Итог", 16.0), ("Примечание", 100.0)],
           [[c["name"], "%.1f" % c["value"], "%.1f" % c["allow"], c["unit"],
             "ок" if c["ok"] else "нет", c["note"]] for c in r["checks"]],
           size=2.3)

    # расхождение по ППВВП
    sh._text(x0 + 276.0, yc, "Расхождение по ППВВП", size=4.2, bold=True)
    _table(sh, x0 + 276.0, yc - 6.0,
           [("Ситуация", 50.0), ("Действие", 106.0), ("Подтверждение", 86.0)],
           [[a, b, c] for a, b, c in A.COLREG], size=2.3)

    p = sh.save(os.path.join(OUT, "15_автономное_управление.png"))
    if verbose:
        s, rc = r["stopping"], r["reaction"]
        print("торможение %.0f м за %.0f с, манёвр с %.0f м, "
              "обнаружение с %.0f м" % (s["distance"], s["time"],
                                        rc["manoeuvre"], rc["required"]))
        print("  ", os.path.basename(p))
    return p


if __name__ == "__main__":
    build()
