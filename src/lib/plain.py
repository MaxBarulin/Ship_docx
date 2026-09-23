# -*- coding: utf-8 -*-
"""Простой вид схем и графиков - как у рабочих материалов, сделанных руками.

Графики - как диаграммы Excel в русской локали: Calibri, цвета Office по порядку рядов,
сетка по значениям, легенда снизу без рамки, десятичная запятая, рамка области диаграммы.
Схемы и планы - как рисунки в Word: Times New Roman, белые прямоугольники, чёрные линии,
то, что добавлено или вынесено в кооперацию, - пунктиром.

Заголовков и «штампов» на картинке нет, название даёт подпись «Рисунок N» в документе.
Нет заливок-плашек, скруглений, теней, тёмных фонов, цветных акцентов и текстовых колонок.

Выпуск - 200 dpi. В Calibri вшиты растровые глифы мелких кеглей, и на 150 dpi кегль 9
терял цифры (подписи «ноя.26» рисовались как «ноя»).

    from lib import plain as P
    with P.excel():
        fig, ax = plt.subplots(figsize=(8, 4))
        ax.plot(x, y, label="ряд 1")
        P.оси(ax); P.запятая(ax); P.легенда(ax); P.рамка(fig)
        P.сохранить(fig, путь)
"""
import os
import time

import matplotlib
import matplotlib.pyplot as plt
from cycler import cycler
from matplotlib.patches import Rectangle
from matplotlib.ticker import FuncFormatter

DPI = 200
OFFICE = ("#4472C4", "#ED7D31", "#A5A5A5", "#FFC000", "#5B9BD5", "#70AD47")   # порядок рядов Excel
СЕТКА, ОСЬ, ПОДПИСЬ = "#D9D9D9", "#BFBFBF", "#595959"
ЛИНИЯ = 0.8                                   # линия схемы Word, pt
МЕС = ("янв", "фев", "мар", "апр", "май", "июн", "июл", "авг", "сен", "окт", "ноя", "дек")

_ОБЩЕЕ = {"axes.unicode_minus": False, "figure.facecolor": "white", "savefig.facecolor": "white",
          "axes.facecolor": "white", "figure.dpi": DPI, "savefig.dpi": DPI}

EXCEL = dict(_ОБЩЕЕ, **{
    "font.family": ["Calibri", "DejaVu Sans"], "font.size": 10,
    "axes.prop_cycle": cycler(color=list(OFFICE)),
    "axes.edgecolor": ОСЬ, "axes.linewidth": 0.8, "axes.labelcolor": ПОДПИСЬ, "axes.labelsize": 10,
    "axes.titlesize": 11, "axes.titlecolor": ПОДПИСЬ, "axes.titleweight": "normal",
    "axes.spines.top": False, "axes.spines.right": False,
    "axes.grid": True, "axes.grid.axis": "y", "grid.color": СЕТКА, "grid.linewidth": 0.8,
    "axes.axisbelow": True,
    "xtick.color": ПОДПИСЬ, "ytick.color": ПОДПИСЬ, "xtick.labelsize": 9, "ytick.labelsize": 9,
    "xtick.major.size": 0, "ytick.major.size": 0,
    "legend.frameon": False, "legend.fontsize": 9, "legend.labelcolor": ПОДПИСЬ,
    "lines.linewidth": 2.0, "text.color": ПОДПИСЬ,
})

WORD = dict(_ОБЩЕЕ, **{
    "font.family": ["Times New Roman", "DejaVu Serif"], "font.size": 11,
    "text.color": "black", "axes.edgecolor": "black", "axes.labelcolor": "black",
    "xtick.color": "black", "ytick.color": "black",
    "lines.linewidth": ЛИНИЯ, "lines.color": "black",
    "patch.linewidth": ЛИНИЯ, "patch.edgecolor": "black", "patch.facecolor": "white",
    "hatch.color": "black", "hatch.linewidth": 0.5,
    "legend.frameon": False,
})


#: растровые чертежи (теоретический чертёж, проекция «корпус») - шрифт по ГОСТ 2.304, чёрные линии,
#: как лист, выведенный из САПР. Если шрифта ГОСТ нет (облачная сессия) - ISOCPEUR, затем DejaVu.
#: В GOST Common «°» рисуется как «¹», «Ø» как «Ý», «·» как «¾», кавычки «» как «¼½» - писать «град»,
#: «⌀» (U+2300), «⋅» (U+22C5) и обходиться без кавычек-ёлочек
ЧЕРТЁЖ = dict(_ОБЩЕЕ, **{
    "font.family": ["GOST Common", "ISOCPEUR", "DejaVu Sans"], "font.size": 10,
    "text.color": "black", "axes.edgecolor": "black", "axes.labelcolor": "black",
    "xtick.color": "black", "ytick.color": "black",
    "lines.linewidth": 0.7, "lines.color": "black",
    "patch.linewidth": 0.7, "patch.edgecolor": "black", "patch.facecolor": "white",
    "grid.color": СЕТКА, "grid.linewidth": 0.5,
    "legend.frameon": False,
})


def чертёж():
    """Контекст растрового чертежа - `with P.чертёж(): ...`."""
    return plt.rc_context(ЧЕРТЁЖ)


def excel():
    """Контекст диаграммы Excel - `with P.excel(): ...`."""
    return plt.rc_context(EXCEL)


def word():
    """Контекст схемы Word - `with P.word(): ...`."""
    return plt.rc_context(WORD)


def оси(ax, сетка="y"):
    """Оси как в Excel. Линии значений нет, ось категорий серая, сетка по значениям
    («y», «x» или «both» - у точечной диаграммы)."""
    ax.spines["left"].set_visible(сетка == "both")
    ax.spines["bottom"].set_color(ОСЬ)
    ax.spines["left"].set_color(ОСЬ)
    ax.grid(False)
    if сетка in ("y", "both"):
        ax.grid(axis="y", color=СЕТКА, lw=0.8)
    if сетка in ("x", "both"):
        ax.grid(axis="x", color=СЕТКА, lw=0.8)
    ax.tick_params(length=0, colors=ПОДПИСЬ)


def _число(v, _pos=None):
    s = ("%.10g" % v) if abs(v - round(v)) > 1e-9 else "%d" % round(v)
    return s.replace(".", ",")


def запятая(ax, ось="both"):
    """Десятичная запятая в подписях осей, как у Excel в русской локали."""
    if ось in ("x", "both"):
        ax.xaxis.set_major_formatter(FuncFormatter(_число))
    if ось in ("y", "both"):
        ax.yaxis.set_major_formatter(FuncFormatter(_число))


def ч(x, знаков=1):
    """Число с запятой для подписей: ч(4.9) -> «4,9», ч(1100, 0) -> «1100»."""
    return ("%.*f" % (знаков, x)).replace(".", ",")


def месяц(d):
    """Подпись месяца, как в Excel: «ноя.26»."""
    return "%s.%02d" % (МЕС[d.month - 1], d.year % 100)


def легенда(ax, ncol=None, dy=-0.14, **kw):
    """Легенда снизу по центру без рамки - как в Excel по умолчанию."""
    h, l = ax.get_legend_handles_labels()
    if not h:
        return None
    return ax.legend(h, l, loc="upper center", bbox_to_anchor=(0.5, dy), ncol=ncol or min(len(h), 4),
                     frameon=False, **kw)


def рамка(fig):
    """Рамка области диаграммы, как у вставленной из Excel в Word."""
    fig.patches.append(Rectangle((0.002, 0.004), 0.996, 0.992, transform=fig.transFigure,
                                 fill=False, edgecolor=СЕТКА, lw=1.0))


def сохранить(fig, путь, **kw):
    """PNG на 200 dpi. По кириллическому пути запись иногда даёт EINVAL - пишем во
    временное имя и переносим, с повтором."""
    kw.setdefault("dpi", DPI)
    tmp = путь + ".tmp.png"
    for попытка in range(4):
        try:
            fig.savefig(tmp, **kw)
            os.replace(tmp, путь)
            return путь
        except OSError:
            if попытка == 3:
                raise
            time.sleep(0.5)
    return путь
