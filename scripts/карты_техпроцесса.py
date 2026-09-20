# -*- coding: utf-8 -*-
"""Технологические документы на балку ВГ-2026.16.01.

    python scripts/карты_техпроцесса.py

Маршрутная карта, операционная карта на сварку, карта эскизов с базированием
и карта контроля. Содержимое — из `gorizont_tp`, то есть из той же таблицы
операций, по которой считается трудоёмкость узла.
"""
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

import matplotlib
matplotlib.use("Agg")
from matplotlib.patches import Rectangle, Circle

from lib import gorizont_tp as T
from lib import eskd_tp

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
INK, ACC, GRY = "#16202f", "#b02634", "#9aa4b4"


def route():
    """Маршрутная карта, ГОСТ 3.1118-82 форма 1."""
    sh = eskd_tp.TechSheet("МК   ГОСТ 3.1118-82 форма 1",
                           T.DETAIL["mark"] + " МК", T.DETAIL)
    rows = []
    for o in T.OPS:
        rows.append([o["no"], o["shop"], o["area"], o["name"],
                     o["content"], o["equip"],
                     "%.2f" % o["tpz"], "%.2f" % o["tsht"]])
    t = T.totals()
    rows.append(["", "", "", "", "Итого на деталь при партии %d шт" % t["batch"],
                 "", "%.2f" % t["tpz"], "%.2f" % t["tsht"]])
    rows.append(["", "", "", "", "Итого на узел, %d балки" % t["batch"], "",
                 "", "%.2f" % t["per_node"]])
    sh.table([("Опер.", 9), ("Цех", 7), ("Уч.", 7), ("Наименование", 24),
              ("Содержание операции", 74), ("Оборудование", 36),
              ("Тпз", 9), ("Тшт", 9)],
             rows, row_h=9.0, head_h=8.0, size=2.0, center=(0, 1, 2, 6, 7))
    sh.block("Примечания", [
        "Нормы времени укрупнённые: заготовительные и слесарные по площади "
        "реза и длине кромок, сварочные по погонной длине шва,",
        "контрольные по числу контролируемых элементов. Тпз дан на партию "
        "%d деталей — ровно на один узел." % T.DETAIL["batch"],
        "Заготовка — %s." % T.DETAIL["blank"],
    ])
    return sh.save(os.path.join(OUT, "10_маршрутная_карта.png"))


def operation(no="020"):
    """Операционная карта, ГОСТ 3.1404-86 форма 3."""
    o = T.op(no)
    sh = eskd_tp.TechSheet("ОК   ГОСТ 3.1404-86 форма 3",
                           "%s ОК%s" % (T.DETAIL["mark"], no), T.DETAIL)
    sh.table([("Опер.", 10), ("Наименование операции", 40),
              ("Цех", 8), ("Уч.", 8), ("Оборудование", 60),
              ("Тпз", 10), ("Тшт", 10)],
             [[o["no"], o["name"], o["shop"], o["area"], o["equip"],
               "%.2f" % o["tpz"], "%.2f" % o["tsht"]]],
             row_h=8.0, head_h=8.0, size=2.2, center=(0, 2, 3, 5, 6))
    sh.block("Содержание переходов", o["transitions"], size=2.4, gap=5.2)
    rows = [[k, v] for k, v in o["modes"]]
    sh.table([("Параметр режима", 60), ("Значение", 65)], rows,
             y=sh.top - 2.0, row_h=7.0, head_h=8.0, size=2.3)
    sh.block("Требования по операции", [
        "Сварку вести в нижнем положении «в лодочку», деталь кантовать "
        "кантователем КБ-2.",
        "Обратноступенчатый порядок участками 300 мм от середины к концам "
        "— против поводки пояска.",
        "Температура металла перед сваркой не ниже +5 °C; при более низкой "
        "подогреть зону шва до 100…150 °C.",
        "Приёмка швов — по РД5Р.9083, контроль по операции 040.",
    ], size=2.3, gap=5.0)
    return sh.save(os.path.join(OUT, "11_операционная_карта.png"))


def sketch(no="020"):
    """Карта эскизов, ГОСТ 3.1105-84 форма 7: базирование и закрепление."""
    o = T.op(no)
    sh = eskd_tp.TechSheet("КЭ   ГОСТ 3.1105-84 форма 7",
                           "%s КЭ%s" % (T.DETAIL["mark"], no), T.DETAIL)
    sh.table([("Опер.", 10), ("Наименование операции", 60),
              ("Приспособление", 60)],
             [[o["no"], o["name"], "Кондуктор сборочный СБ-16"]],
             row_h=8.0, head_h=8.0, size=2.3, center=(0,))

    # вид сбоку: тавр 3600 x 158 — сплющенный прямоугольник, поэтому
    # отдельно даётся сечение, где базы читаются
    MG = eskd_tp.eskd.MARGIN_L
    ax = sh.sh.axes(MG, sh.top - 34.0, 176.0, 30.0)
    ax.set_xlim(-320, 3920)
    ax.set_ylim(-260, 500)
    L = T.DETAIL["length_mm"]
    ax.add_patch(Rectangle((0, 0), L, 140, facecolor="#dfe6ef",
                           edgecolor=INK, lw=1.0))
    ax.add_patch(Rectangle((0, 140), L, 18, facecolor="#cdd7e4",
                           edgecolor=INK, lw=1.0))
    for x in (300, L / 2.0, L - 300):
        ax.add_patch(Rectangle((x - 70, -90), 140, 90, facecolor="#f2d9dc",
                               edgecolor=ACC, lw=0.9))
    for x in (500, 1400, 2300, 3200):
        ax.annotate("", (x, 158), (x, 300),
                    arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1.1))
    ax.add_patch(Rectangle((-150, 0), 120, 158, facecolor="#f2d9dc",
                           edgecolor=ACC, lw=0.9))
    ax.annotate("", (0, -150), (L, -150),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=0.7))
    ax.text(L / 2.0, -170, "%d" % L, ha="center", va="top", fontsize=7.0,
            color=INK)
    ax.text(L / 2.0, 460, "Вид сбоку: балка в кондукторе СБ-16",
            ha="center", fontsize=7.5, color="#56627a")
    ax.text(L / 2.0, 330, "4 прижима, усилие 4 кН", ha="center",
            fontsize=6.5, color=ACC)
    ax.text(1800, -215, "3 опоры кондуктора", ha="center", fontsize=6.5,
            color=ACC)
    # упор по длине — опорная база 3
    ax.add_patch(Circle((-230, 300), 90, facecolor="white", edgecolor=INK,
                        lw=0.9, zorder=6))
    ax.text(-230, 300, "3", ha="center", va="center", fontsize=6.5,
            color=INK, zorder=7)
    ax.plot([-230, -90], [300, 158], color=GRY, lw=0.7)

    # сечение с обозначением баз
    ax2 = sh.sh.axes(MG, sh.top - 90.0, 62.0, 52.0)
    ax2.set_xlim(-90, 120)
    ax2.set_ylim(-95, 210)
    ax2.add_patch(Rectangle((-4, 0), 8, 140, facecolor="#dfe6ef",
                            edgecolor=INK, lw=1.1))
    ax2.add_patch(Rectangle((-50, 140), 100, 10, facecolor="#cdd7e4",
                            edgecolor=INK, lw=1.1))
    ax2.plot([-50, 50], [-18, -18], color=ACC, lw=1.2)
    for x in (-34, 0, 34):
        ax2.annotate("", (x, 0), (x, -16),
                     arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1.0))
    ax2.annotate("", (-4, 70), (-40, 70),
                 arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1.0))
    ax2.annotate("", (0, 150), (0, 196),
                 arrowprops=dict(arrowstyle="-|>", color=ACC, lw=1.1))
    for n, x, y in (("1", 0, -44), ("2", -62, 70), ("4", 0, 200)):
        ax2.add_patch(Circle((x, y), 15, facecolor="white", edgecolor=INK,
                             lw=0.9, zorder=6))
        ax2.text(x, y, n, ha="center", va="center", fontsize=7.0, color=INK,
                 zorder=7)
    ax2.text(64, 145, "поясок 10", fontsize=6.5, color="#56627a", va="center")
    ax2.text(14, 70, "стенка 8", fontsize=6.5, color="#56627a", va="center")
    ax2.text(0, -86, "Сечение: базы 1, 2 и закрепление 4", ha="center",
             fontsize=7.0, color="#56627a")

    sh.top = sh.top - 96.0
    sh.block("Базирование и закрепление (ГОСТ 3.1107-81)",
             ["%s — %s" % (n, t) for n, t in T.BASES], size=2.3, gap=5.0)
    return sh.save(os.path.join(OUT, "12_карта_эскизов.png"))


def control():
    """Карта контроля, ГОСТ 3.1502-85 форма 2."""
    sh = eskd_tp.TechSheet("ККИ   ГОСТ 3.1502-85 форма 2",
                           T.DETAIL["mark"] + " ККИ", T.DETAIL)
    rows = [[c["no"], c["what"], c["param"], c["tool"], c["scope"], c["nd"]]
            for c in T.CONTROL]
    sh.table([("Опер.", 9), ("Объект контроля", 30),
              ("Контролируемый параметр", 52), ("Средство контроля", 48),
              ("Объём", 16), ("НД", 34)],
             rows, row_h=11.0, head_h=8.0, size=1.95, center=(0, 4))
    sh.block("Порядок приёмки", [
        "Контроль пооперационный; результаты заносятся в журнал ОТК и "
        "сопроводительный лист партии.",
        "При обнаружении дефекта шва участок вырубается и заваривается "
        "заново, контроль повторяется в полном объёме.",
        "Деталь предъявляется представителю РРР после операции 040 вместе с "
        "протоколом УЗК.",
    ], size=2.3, gap=5.0)
    return sh.save(os.path.join(OUT, "13_карта_контроля.png"))


def build(verbose=True):
    made = [route(), operation(), sketch(), control()]
    if verbose:
        t = T.totals()
        print("трудоёмкость: %.2f н·ч на деталь, %.2f н·ч на узел"
              % (t["per_detail"], t["per_node"]))
        for p in made:
            print("  ", os.path.basename(p))
    return made


if __name__ == "__main__":
    build()
