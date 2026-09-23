# -*- coding: utf-8 -*-
"""Графики теории корабля для приложения А записки - renders/горизонт_2026/расчёты/02…07.

Вид - диаграммы Excel в русской локали (lib.plain): Calibri, цвета Office по порядку
рядов, сетка, легенда снизу без рамки, десятичная запятая. Общего заголовка нет,
название даёт подпись «Рисунок А.N» в записке. Пояснения, которые не помещаются в
одну строку (критерий погоды, мелководье, состав станции), - в тексте приложения.
Все числа - из библиотек, руками не набрано.
"""
import os, sys, re
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from lib import gorizont as G, gorizont_hydro as H, gorizont_strength as St
from lib import gorizont_power as Pw
from lib import plain as P

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "расчёты")
os.makedirs(OUT, exist_ok=True)
C1, C2, C3 = P.OFFICE[:3]          # синий, оранжевый, серый - первый, второй, третий ряд
ОПОРА = "#595959"                   # опорные линии - осадка, предельный момент, уровни ГДГ
НОЛЬ = P.ОСЬ                        # линия нуля у знакопеременных рядов


def _зап(s):
    """Десятичная запятая в готовой подписи: «17.5 км/ч» -> «17,5 км/ч»."""
    return re.sub(r"(?<=\d)\.(?=\d)", ",", s)


def _оформить(ax, шаг_x=None):
    P.оси(ax, "both")
    P.запятая(ax)
    if шаг_x:
        ax.xaxis.set_major_locator(MultipleLocator(шаг_x))


def save(fig, name):
    P.рамка(fig)
    P.сохранить(fig, os.path.join(OUT, name))
    plt.close(fig)
    print("  ", name)


def hydro_curves():
    """Кривые элементов теоретического чертежа - четыре диаграммы 2 × 2 по осадке."""
    ts = [0.6 + 0.15 * i for i in range(17)]          # 0,6…3,0 - до высоты борта
    rows = [H.hydrostatics(t) for t in ts]
    T = H.equilibrium()["T"]
    панели = [
        ("Водоизмещение и площадь ватерлинии", "м³, м²",
         [("водоизмещение V, м³", "V"), ("площадь ватерлинии Aw, м²", "Aw")]),
        ("Абсциссы центров", "x от кормового перпендикуляра, м",
         [("центр величины xc", "xc"), ("центр тяжести ватерлинии xf", "xf")]),
        ("Аппликаты и метацентрический радиус", "м",
         [("центр величины zc", "zc"), ("метацентр zm", "zm"), ("радиус r", "r")]),
        ("Коэффициенты полноты", "коэффициент",
         [("общей полноты δ", "delta"), ("ватерлинии α", "alpha"), ("мидель-шпангоута β", "beta")]),
    ]
    with P.excel():
        fig, axs = plt.subplots(2, 2, figsize=(9.0, 8.2), sharey=True, layout="constrained")
        fig.get_layout_engine().set(h_pad=0.12, w_pad=0.1)
        for ax, (заголовок, ось_x, ряды) in zip(axs.flat, панели):
            for (подпись, ключ), цвет in zip(ряды, P.OFFICE):
                ax.plot([r[ключ] for r in rows], ts, color=цвет, label=подпись)
            ax.axhline(T, color=ОПОРА, lw=1.0, ls="--", label="полный груз T = %s м" % P.ч(T, 2))
            ax.set_title(заголовок)
            ax.set_xlabel(ось_x)
            _оформить(ax)
            ax.yaxis.set_major_locator(MultipleLocator(0.5))
            P.легенда(ax, ncol=2, dy=-0.15)
        for ax in axs[:, 0]:
            ax.set_ylabel("осадка T, м")
        save(fig, "02_кривые_элементов.png")


def bonjean_and_load():
    """Строевая по шпангоутам и нагрузка масс - две диаграммы одна под другой."""
    xs = H._xs(1.0)
    T = H.equilibrium()["T"]
    om = [H.section_area(x, T) for x in xs]
    w = H.weight_distribution(xs)
    b = [H.RHO * o for o in om]
    with P.excel():
        fig, axs = plt.subplots(2, 1, figsize=(9.0, 6.6), sharex=True, layout="constrained")
        fig.get_layout_engine().set(h_pad=0.1)
        axs[0].plot(xs, om, color=C1)
        axs[0].set_title("Строевая по шпангоутам при T = %s м, V = %.0f м³" % (P.ч(T, 2), H._trapz(om, xs)))
        axs[0].set_ylabel("площадь сечения ω, м²")
        axs[1].plot(xs, w, color=C1, label="нагрузка масс w(x)")
        axs[1].plot(xs, b, color=C2, label="силы поддержания b(x)")
        axs[1].set_title("Нагрузка масс и силы поддержания")
        axs[1].set_ylabel("интенсивность, т/м")
        axs[1].set_xlabel("x от кормового перпендикуляра, м")
        for ax in axs:
            _оформить(ax, 10)
            ax.set_xlim(0, G.LOA)
            ax.set_ylim(bottom=0)
        P.легенда(axs[1], dy=-0.19)
        save(fig, "03_строевая_и_нагрузка.png")


def stability_plots():
    """Пантокарены, ДСО и ДДО - корпус и корпус с закрытым ярусом главной палубы."""
    zt = G.DECKS["средняя"]
    a = H.stability_summary()
    b = H.stability_summary(z_top=zt)
    корпус = "корпус до %s м" % P.ч(G.DEPTH, 2)
    ярус = "с ярусом главной палубы до %s м" % P.ч(zt, 2)
    with P.excel():
        fig, axs = plt.subplots(1, 3, figsize=(10.0, 4.4), layout="constrained")
        fig.get_layout_engine().set(w_pad=0.1)
        for ax, ключ, заголовок, ось_y in zip(
                axs, ("lk", "gz", "dyn"),
                ("Пантокарены", "Статическая остойчивость", "Динамическая остойчивость"),
                ("плечо lк, м", "плечо GZ, м", "плечо lд, м·рад")):
            ax.plot(a["theta"], a[ключ], color=C1, label=корпус)
            ax.plot(b["theta"], b[ключ], color=C2, ls="--", label=ярус)
            ax.set_title(заголовок)
            ax.set_xlabel("угол крена, град")
            ax.set_ylabel(ось_y)
            ax.set_xlim(0, 90)
            _оформить(ax, 15)
        ax = axs[1]
        ax.axhline(0, color=НОЛЬ, lw=0.8)
        # касательная к ДСО в начале - отрезок h на одном радиане (57,3 град)
        ax.plot([0, 57.3], [0, a["h"]], color=C3, lw=1.2, label="касательная в начале, h = %s м" % P.ч(a["h"], 2))
        верх = max(max(a["gz"]), max(b["gz"]))
        ax.set_ylim(min(0.0, min(a["gz"])) - 0.5, верх * 1.4)
        h, l = axs[1].get_legend_handles_labels()
        fig.legend(h, l, loc="outside lower center", ncol=3, frameon=False)
        save(fig, "04_остойчивость.png")


def strength_plots():
    """Нагрузка, перерезывающая сила и изгибающий момент - тихая вода и волна."""
    r = St.stresses()
    g = r["girder"]
    lim = r["sigma_allow"] * g["W_deck_m3"]                     # МПа × м³ = МН·м
    with P.excel():
        fig, axs = plt.subplots(3, 1, figsize=(9.0, 8.4), sharex=True, layout="constrained")
        fig.get_layout_engine().set(h_pad=0.1)
        for row, цвет in zip(r["rows"], P.OFFICE):
            c = row["case"]
            axs[0].plot(c["xs"], c["q"], color=цвет, lw=1.5, label=c["condition"])
            axs[1].plot(c["xs"], c["N"], color=цвет, lw=1.5)
            axs[2].plot(c["xs"], [m / 1000.0 for m in c["M"]], color=цвет, lw=1.5)
        axs[2].axhline(lim, color=ОПОРА, lw=1.0, ls="--",
                       label="предельный момент ±%.0f МН·м (%.0f МПа)" % (lim, r["sigma_allow"]))
        axs[2].axhline(-lim, color=ОПОРА, lw=1.0, ls="--")
        for ax, заголовок, ось_y in zip(axs, ("Нагрузка", "Перерезывающая сила", "Изгибающий момент"),
                                        ("q, кН/м", "N, кН", "M, МН·м")):
            ax.axhline(0, color=НОЛЬ, lw=0.8, zorder=1)
            ax.set_title(заголовок)
            ax.set_ylabel(ось_y)
            _оформить(ax, 10)
            ax.set_xlim(0, G.LOA)
        axs[2].set_xlabel("x от кормового перпендикуляра, м")
        h, l = axs[0].get_legend_handles_labels()
        h2, l2 = axs[2].get_legend_handles_labels()
        fig.legend(h + h2, l + l2, loc="outside lower center", ncol=4, frameon=False)
        save(fig, "05_продольная_прочность.png")


def resistance_plots():
    """Сопротивление и мощность на глубокой воде. Мелководье - таблицей в тексте."""
    vmax = H.max_speed()
    vs = [8 + 0.5 * i for i in range(int((vmax + 0.6 - 8) / 0.5) + 1)]   # до пересечения с установленной
    deep = [H.power(v) for v in vs]
    трение = [0.5 * H.RHO * 1000 * p["S"] * p["v"] ** 2 * (p["Cf"] * (1 + p["k"]) + 0.0004) / 1000 for p in deep]
    остаточное = [0.5 * H.RHO * 1000 * p["S"] * p["v"] ** 2 * p["Cr"] / 1000 for p in deep]
    with P.excel():
        fig, axs = plt.subplots(1, 2, figsize=(10.0, 4.4), layout="constrained")
        fig.get_layout_engine().set(w_pad=0.15)
        ax = axs[0]
        ax.plot(vs, [p["R"] for p in deep], color=C1, label="полное")
        ax.plot(vs, трение, color=C2, label="трение с формфактором")
        ax.plot(vs, остаточное, color=C3, label="остаточное")
        ax.set_title("Буксировочное сопротивление")
        ax.set_ylabel("R, кН")

        ax = axs[1]
        ax.plot(vs, [p["Pb"] for p in deep], color=C1, label="потребная мощность")
        ax.axhline(H.PROP_POWER, color=C2, lw=1.5,
                   label="установлено %d × %d = %d кВт" % (G.WHEEL_COUNT, G.WHEEL_MOTOR_POWER, H.PROP_POWER))
        # точки на кривой с подписями данных, как в Excel - слева сверху, над выпуклой кривой свободно
        for v in (G.SPEED_KMH, G.SPEED_MAX_KMH):
            pb = H.power(v)["Pb"]
            ax.plot([v], [pb], "o", color=C1, ms=5)
            текст = "%s км/ч, %.0f кВт" % (P.ч(v), pb)
            if v == G.SPEED_MAX_KMH:
                текст += "\n%.0f %% установленной" % (100 * pb / H.PROP_POWER)
            ax.annotate(текст, (v, pb), xytext=(-6, 5), textcoords="offset points",
                        ha="right", va="bottom", fontsize=9)
        ax.plot([vmax], [H.PROP_POWER], "o", color=C1, ms=5)
        ax.annotate("%s км/ч" % P.ч(vmax), (vmax, H.PROP_POWER), xytext=(-6, 5), textcoords="offset points",
                    ha="right", va="bottom", fontsize=9)
        ax.set_ylim(0, H.PROP_POWER * 1.3)
        ax.set_title("Потребная и установленная мощность")
        ax.set_ylabel("мощность на движителях, кВт")
        for ax in axs:
            ax.set_xlabel("скорость, км/ч")
            ax.set_xlim(vs[0], vs[-1])
            _оформить(ax, 2)
            P.легенда(ax, ncol=3, dy=-0.17)
        save(fig, "06_ходкость.png")


def power_balance():
    """Электробаланс по режимам и проверка n-1 для выбора единичной мощности ГДГ."""
    rows = Pw.table()
    names = [_зап(Pw.MODE_SHORT[r["key"]]) for r in rows]
    hotel = [r["hotel"] for r in rows]
    prop = [r["propulsion"] for r in rows]
    total = [r["total"] for r in rows]
    units = (400, 500, 600, 800)
    отказ = [Pw.redundancy("мелководье", unit=u, count=G.DG_COUNT) for u in units]
    speeds = [o["speed"] for o in отказ]

    with P.excel():
        fig, axs = plt.subplots(1, 2, figsize=(10.0, 4.6), layout="constrained",
                                gridspec_kw={"width_ratios": [1.6, 1]})
        fig.get_layout_engine().set(w_pad=0.15)
        ax = axs[0]
        x = list(range(len(rows)))
        ax.bar(x, hotel, width=0.6, color=C1, label="судовые и бытовые", zorder=2)
        ax.bar(x, prop, width=0.6, bottom=hotel, color=C2, label="гребные электродвигатели", zorder=2)
        for i, v in enumerate(total):
            ax.text(i, v + 25, "%.0f" % v, ha="center", va="bottom", fontsize=9)
        for n in range(1, G.DG_COUNT + 1):
            ax.axhline(n * G.DG_POWER, color=ОПОРА, lw=0.8, ls="--", zorder=3)
            ax.text(len(rows) - 0.45, n * G.DG_POWER + 25, "%d ГДГ" % n, ha="right", va="bottom", fontsize=9)
        ax.set_xticks(x)
        ax.set_xticklabels(names)
        ax.set_xlim(-0.6, len(rows) - 0.4)
        ax.set_ylim(0, G.DG_TOTAL + 300)
        ax.set_ylabel("мощность на шинах ГРЩ, кВт")
        ax.set_title("Нагрузка по режимам")
        P.оси(ax)
        P.легенда(ax, ncol=2, dy=-0.16)

        ax = axs[1]
        xs = list(range(len(units)))
        ax.bar(xs, speeds, width=0.6, color=C1, zorder=2)
        for i, s in enumerate(speeds):
            ax.text(i, s + 0.2, P.ч(s), ha="center", va="bottom", fontsize=9)
        ax.axhline(G.SPEED_KMH, color=C2, lw=1.5, zorder=3)
        ax.text(-0.45, G.SPEED_KMH + 0.25, "эксплуатационная %s км/ч" % P.ч(G.SPEED_KMH),
                ha="left", va="bottom", fontsize=9)
        ax.set_xticks(xs)
        ax.set_xticklabels([str(u) for u in units])
        ax.set_xlim(-0.6, len(units) - 0.4)
        ax.set_ylim(0, (int(max(max(speeds), G.SPEED_KMH)) // 5 + 1) * 5)
        ax.set_xlabel("мощность одного ГДГ, кВт")
        ax.set_ylabel("скорость при отказе одного ГДГ, км/ч")
        ax.set_title("Отказ одного ГДГ, фарватер %.0f м" % отказ[0]["depth"])
        P.оси(ax)
        P.запятая(ax, "y")
        save(fig, "07_электробаланс.png")


# Здесь был график «один вал против двух». Он умер вместе с винтами:
# движитель сменился на колёсный, и сравнивать теперь надо колесо с винтом
# на мелководье, а не вал с валом. Числа для такого графика уже есть в
# gorizont_wheel.propeller_comparison(); сам график - работа отдельная.


if __name__ == "__main__":
    print("строю графики:")
    hydro_curves()
    bonjean_and_load()
    stability_plots()
    strength_plots()
    resistance_plots()
    power_balance()
