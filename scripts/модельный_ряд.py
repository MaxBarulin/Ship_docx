# -*- coding: utf-8 -*-
"""Модельный ряд - три версии на одном корпусе, две диаграммы как из Excel.

Вверху - число кают по типам для трёх версий (линейчатая с накоплением), внизу -
пассажирских мест по версиям с линией нормы вместимости. Таблица версий и пояснения -
в тексте записки (раздел 2.4), на рисунке только диаграммы.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from lib import gorizont as G, gorizont_ga as GA, gorizont_range as R, plain as P

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "схемы")
os.makedirs(OUT, exist_ok=True)
#: требование к вместимости по КЗ (им же проверяется kz_ok версии)
НОРМА_МЕСТ = G.МЕСТ_КЗ
#: типы кают в порядке компоновки, только те, что есть хотя бы в одной версии
ТИПЫ = [k for k in GA.КАЮТЫ if any(v["cabins"].get(k) for v in R.VERSIONS)]
ТЁМНЫЕ = {P.OFFICE[0], P.OFFICE[1], P.OFFICE[4], P.OFFICE[5]}   # на них подпись белая


def _дюймы(fig, x0, y0, w, h, H):
    """Оси по дюймам от левого верхнего угла фигуры."""
    W = fig.get_figwidth()
    return fig.add_axes([x0 / W, 1 - (y0 + h) / H, w / W, h / H])


def _рамка(fig, x0, y0, w, h, H):
    """Рамка области диаграммы - у каждой из двух своя, как у вставленных из Excel."""
    fig.patches.append(Rectangle((x0, H - y0 - h), w, h, transform=fig.dpi_scale_trans,
                                 fill=False, edgecolor=P.СЕТКА, lw=1.0))


def _ширина_px(ax, текст, размер):
    t = ax.text(0, 0, текст, fontsize=размер)
    w = t.get_window_extent(renderer=ax.figure.canvas.get_renderer()).width
    t.remove()
    return w


def рисунок():
    rows = R.table()
    версии = [s["name"] for s in rows]
    W, H = 7.4, 6.4
    ВЕРХ_Н = 3.35                                  # высота области верхней диаграммы, дюймы
    with P.excel():
        fig = plt.figure(figsize=(W, H))
        # --- число кают по типам ---------------------------------------------------------
        _рамка(fig, 0.02, 0.02, W - 0.04, ВЕРХ_Н - 0.08, H)
        высота = ВЕРХ_Н - 1.12
        ax = _дюймы(fig, 0.95, 0.22, W - 1.35, высота, H)
        ys = list(range(len(rows)))[::-1]          # первая версия сверху
        лев = [0] * len(rows)
        сегменты = []
        for i, k in enumerate(ТИПЫ):
            n = [s["cabins"].get(k, 0) for s in rows]
            цвет = P.OFFICE[i % len(P.OFFICE)]
            ax.barh(ys, n, left=лев, height=0.55, color=цвет, label=k, zorder=2)
            сегменты += [(x0 + v / 2.0, y, v, цвет) for y, x0, v in zip(ys, лев, n) if v]
            лев = [a + b for a, b in zip(лев, n)]
        верх = (max(лев) // 10 + 2) * 10
        ax.set_xlim(0, верх)
        ax.set_xticks(range(0, верх + 1, 10))
        ax.set_ylim(-0.6, len(rows) - 0.4)
        ax.set_yticks(ys)
        ax.set_yticklabels(версии, fontsize=10)
        P.оси(ax, сетка="x")
        ax.spines["left"].set_visible(True)        # у линейчатой ось категорий слева
        ax.spines["bottom"].set_visible(False)
        ax.set_xlabel("Число кают")
        fig.canvas.draw()
        px = ax.transData.transform((1, 0))[0] - ax.transData.transform((0, 0))[0]
        for x, y, v, цвет in сегменты:             # подпись внутри сегмента, если помещается
            if _ширина_px(ax, str(v), 9) + 6 <= v * px:
                ax.text(x, y, str(v), ha="center", va="center", fontsize=9,
                        color="white" if цвет in ТЁМНЫЕ else "#404040", zorder=3)
        for y, v in zip(ys, лев):                  # всего кают - у конца полосы
            ax.text(v + 0.8, y, str(v), ha="left", va="center", fontsize=9)
        P.легенда(ax, ncol=len(ТИПЫ), dy=-0.56 / высота, handlelength=1.0, columnspacing=1.2)

        # --- пассажирских мест ------------------------------------------------------------
        y0 = ВЕРХ_Н + 0.02
        _рамка(fig, 0.02, y0, W - 0.04, H - y0 - 0.02, H)
        высота = H - y0 - 0.95
        ax = _дюймы(fig, 0.85, y0 + 0.25, W - 1.25, высота, H)
        xs = range(len(rows))
        места = [s["berths"] for s in rows]
        ax.bar(xs, места, width=0.5, color=P.OFFICE[0], label="пассажирских мест", zorder=2)
        ax.plot(list(xs), [НОРМА_МЕСТ] * len(rows), color=P.OFFICE[1], lw=2.0, zorder=3,
                label="норма вместимости, %d мест" % НОРМА_МЕСТ)
        for x, v in zip(xs, места):
            ax.text(x, v + 4, str(v), ha="center", va="bottom", fontsize=9)
        верх = (int(max(места + [НОРМА_МЕСТ]) * 1.1) // 50 + 1) * 50
        ax.set_ylim(0, верх)
        ax.set_yticks(range(0, верх + 1, 50))
        ax.set_xlim(-0.6, len(rows) - 0.4)
        ax.set_xticks(list(xs))
        ax.set_xticklabels(версии, fontsize=10)
        P.оси(ax)
        ax.set_ylabel("Число мест")
        h, l = ax.get_legend_handles_labels()      # столбцы - первым рядом, как в таблице Excel
        порядок = sorted(range(len(l)), key=lambda i: l[i] != "пассажирских мест")
        ax.legend([h[i] for i in порядок], [l[i] for i in порядок], loc="upper center",
                  bbox_to_anchor=(0.5, -0.33 / высота), ncol=2, frameon=False)
        p = P.сохранить(fig, os.path.join(OUT, "модельный_ряд.png"))
        plt.close(fig)
    print(p)
    return p


if __name__ == "__main__":
    рисунок()
