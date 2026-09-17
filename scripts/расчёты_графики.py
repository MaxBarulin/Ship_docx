# -*- coding: utf-8 -*-
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from lib import gorizont as G, gorizont_hydro as H, gorizont_struct as S, gorizont_strength as St
from lib import gorizont_power as P

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "расчёты")
plt.rcParams.update({
    "font.family": "DejaVu Sans", "font.size": 9,
    "axes.grid": True, "grid.color": "#d8dde5", "grid.linewidth": 0.6,
    "axes.edgecolor": "#3a4658", "axes.labelcolor": "#1a2334",
    "text.color": "#1a2334", "xtick.color": "#56627a", "ytick.color": "#56627a",
    "figure.facecolor": "white", "savefig.facecolor": "white",
})
os.makedirs(OUT, exist_ok=True)
INK, ACC, SEA, GRN = "#1a2334", "#b02634", "#1c5c8a", "#187454"


def head(fig, title, sub):
    h = fig.get_figheight()
    y1 = 1.0 - 0.30 / h
    y2 = 1.0 - 0.58 / h
    fig.suptitle(title, fontsize=15, fontweight="bold", x=0.01, ha="left", y=y1)
    fig.text(0.01, y2, sub, fontsize=9.5, color="#56627a", ha="left")
    fig.text(0.99, y1 - 0.01 / h, "«Волжский Горизонт» · проект 2026", fontsize=9,
             color="#56627a", ha="right")


def save(fig, name):
    fig.savefig(os.path.join(OUT, name), dpi=150, bbox_inches="tight")
    plt.close(fig)
    print("  ", name)


def hydro_curves():
    ts = [0.8 + 0.2 * i for i in range(17)]
    rows = [H.hydrostatics(t) for t in ts]
    fig, axs = plt.subplots(1, 4, figsize=(15.5, 5.6))
    head(fig, "Кривые элементов теоретического чертежа",
         "Осадка от 0.8 до 4.0 м. Штриховая линия — расчётная осадка в полном грузу")
    fig.subplots_adjust(top=0.80, wspace=0.34, bottom=0.12)
    T = H.equilibrium()["T"]
    sets = [
        [("Водоизмещение V, куб.м", [r["V"] for r in rows], SEA),
         ("Площадь ВЛ Aw, кв.м", [r["Aw"] for r in rows], GRN)],
        [("Абсцисса ЦВ xc, м", [r["xc"] for r in rows], SEA),
         ("Абсцисса ЦТ ВЛ xf, м", [r["xf"] for r in rows], GRN)],
        [("Аппликата ЦВ zc, м", [r["zc"] for r in rows], SEA),
         ("Метацентр zm, м", [r["zm"] for r in rows], ACC),
         ("Радиус r, м", [r["r"] for r in rows], GRN)],
        [("delta", [r["delta"] for r in rows], SEA),
         ("alpha", [r["alpha"] for r in rows], GRN),
         ("beta", [r["beta"] for r in rows], ACC)],
    ]
    for ax, grp in zip(axs, sets):
        for name, vals, col in grp:
            ax.plot(vals, ts, color=col, lw=1.8, label=name)
        ax.axhline(T, color=ACC, lw=1.0, ls="--")
        ax.set_ylabel("осадка T, м")
        ax.legend(fontsize=8, loc="lower right", framealpha=0.95)
    save(fig, "02_кривые_элементов.png")


def bonjean_and_load():
    xs = H._xs(1.0)
    T = H.equilibrium()["T"]
    fig, axs = plt.subplots(2, 1, figsize=(15.5, 7.4), sharex=True)
    head(fig, "Строевая по шпангоутам и нагрузка масс",
         "Слева корма. Площади погружённых сечений и распределение массы по длине")
    fig.subplots_adjust(top=0.85, hspace=0.18, bottom=0.09)
    om = [H.section_area(x, T) for x in xs]
    axs[0].fill_between(xs, om, color=SEA, alpha=0.18)
    axs[0].plot(xs, om, color=SEA, lw=1.8)
    axs[0].set_ylabel("omega(x), кв.м")
    axs[0].set_title("Строевая по шпангоутам при T = %.2f м, V = %.0f куб.м" %
                     (T, H._trapz(om, xs)), fontsize=10, loc="left")
    w = H.weight_distribution(xs)
    b = [H.RHO * o for o in om]
    axs[1].fill_between(xs, w, color=ACC, alpha=0.16)
    axs[1].plot(xs, w, color=ACC, lw=1.8, label="нагрузка масс w(x)")
    axs[1].plot(xs, b, color=SEA, lw=1.8, label="силы поддержания b(x)")
    axs[1].legend(fontsize=9)
    axs[1].set_ylabel("т/м")
    axs[1].set_xlabel("x от кормового перпендикуляра, м")
    for ax in axs:
        ax.xaxis.set_major_locator(MultipleLocator(10))
    save(fig, "03_строевая_и_нагрузка.png")


def stability_plots():
    a = H.stability_summary()
    b = H.stability_summary(z_top=7.00)
    wa = H.weather_criterion("О")
    wb = H.weather_criterion("О", z_top=7.00)
    fig, axs = plt.subplots(1, 3, figsize=(15.5, 5.4))
    head(fig, "Остойчивость на больших углах крена",
         "Сплошная — только корпус до 4.20 м, штриховая — с закрытой надстройкой до 7.00 м")
    fig.subplots_adjust(top=0.80, wspace=0.26, bottom=0.14)
    axs[0].plot(a["theta"], a["lk"], color=SEA, lw=2, label="корпус")
    axs[0].plot(b["theta"], b["lk"], color=SEA, lw=1.6, ls="--", label="с надстройкой")
    axs[0].set_title("Пантокарены l_k", fontsize=10, loc="left")
    axs[1].plot(a["theta"], a["gz"], color=ACC, lw=2, label="корпус")
    axs[1].plot(b["theta"], b["gz"], color=ACC, lw=1.6, ls="--", label="с надстройкой")
    axs[1].axhline(0, color=INK, lw=1)
    axs[1].plot([0, 57.3], [0, a["h"]], color=GRN, lw=1.2, ls=":")
    axs[1].annotate("h = %.2f м" % a["h"], (30, a["h"] * 0.52), color=GRN, fontsize=9)
    axs[1].set_title("ДСО: плечи статической остойчивости", fontsize=10, loc="left")
    axs[2].plot(a["theta"], a["dyn"], color=GRN, lw=2, label="корпус")
    axs[2].plot(b["theta"], b["dyn"], color=GRN, lw=1.6, ls="--", label="с надстройкой")
    axs[2].set_title("ДДО: работа восстанавливающего момента", fontsize=10, loc="left")
    for ax, yl in zip(axs, ("l_k, м", "GZ, м", "l_d, м*рад")):
        ax.set_xlabel("угол крена, град")
        ax.set_ylabel(yl)
        ax.legend(fontsize=8)
        ax.xaxis.set_major_locator(MultipleLocator(15))
    fig.text(0.01, 0.015,
             "Критерий погоды K = %.1f (корпус) и %.1f (с надстройкой) при норме не менее 1.0;  "
             "амплитуда качки %.1f град;  кренящий момент от ветра %.0f т*м" %
             (wa["K"], wb["K"], wa["theta_r"], wa["Mv"]), fontsize=9, color="#56627a")
    save(fig, "04_остойчивость.png")


def strength_plots():
    r = St.stresses()
    fig, axs = plt.subplots(3, 1, figsize=(15.5, 9.6), sharex=True)
    head(fig, "Общая продольная прочность",
         "Нагрузка, перерезывающие силы и изгибающие моменты на тихой воде "
         "и на волне высотой 2.0 м, класс «О»")
    fig.subplots_adjust(top=0.90, hspace=0.16, bottom=0.07)
    cols = {"тихая вода": SEA, "перегиб": ACC, "прогиб": GRN}
    for row in r["rows"]:
        c = row["case"]
        axs[0].plot(c["xs"], c["q"], color=cols[c["condition"]], lw=1.5,
                    label=c["condition"])
        axs[1].plot(c["xs"], c["N"], color=cols[c["condition"]], lw=1.5)
        axs[2].plot(c["xs"], [m / 1000.0 for m in c["M"]],
                    color=cols[c["condition"]], lw=1.8)
    for ax in axs:
        ax.axhline(0, color=INK, lw=0.9)
        ax.xaxis.set_major_locator(MultipleLocator(10))
    axs[0].legend(fontsize=9)
    axs[0].set_ylabel("q(x), кН/м")
    axs[1].set_ylabel("N(x), кН")
    axs[2].set_ylabel("M(x), МН*м")
    axs[2].set_xlabel("x от кормового перпендикуляра, м")
    g = r["girder"]
    lim = r["sigma_allow"] * g["W_deck_m3"]
    axs[2].axhline(lim, color="#8a93a5", lw=1.2, ls="--")
    axs[2].axhline(-lim, color="#8a93a5", lw=1.2, ls="--")
    axs[2].annotate("предельный момент по допускаемому напряжению %.0f МПа: +/- %.0f МН*м"
                    % (r["sigma_allow"], lim), (4, lim * 1.04), fontsize=9, color="#56627a")
    txt = "  |  ".join("%s: M = %.1f МН*м, напряжение в палубе %.0f МПа" %
                       (row["condition"], row["M"] / 1000.0, row["sigma_deck"])
                       for row in r["rows"])
    fig.text(0.01, 0.012, txt + "   |   W палубы %.3f куб.м, W днища %.3f куб.м, I %.2f м4"
             % (g["W_deck_m3"], g["W_bot_m3"], g["I_m4"]), fontsize=9, color="#56627a")
    save(fig, "05_продольная_прочность.png")


def resistance_plots():
    vs = [10 + 0.5 * i for i in range(35)]
    deep = [H.power(v) for v in vs]
    fig, axs = plt.subplots(1, 2, figsize=(15.5, 5.4))
    head(fig, "Ходкость",
         "Сопротивление и потребная мощность на глубокой воде, ограничение по глубине фарватера")
    fig.subplots_adjust(top=0.80, wspace=0.22, bottom=0.16)
    axs[0].plot(vs, [p["R"] for p in deep], color=SEA, lw=2, label="полное R")
    axs[0].plot(vs, [0.5 * H.RHO * 1000 * p["S"] * p["v"] ** 2 *
                     (p["Cf"] * (1 + p["k"]) + 0.0004) / 1000 for p in deep],
                color=GRN, lw=1.4, ls="--", label="трение с формфактором")
    axs[0].plot(vs, [0.5 * H.RHO * 1000 * p["S"] * p["v"] ** 2 * p["Cr"] / 1000
                     for p in deep], color=ACC, lw=1.4, ls="--", label="остаточное")
    axs[0].set_xlabel("скорость, км/ч")
    axs[0].set_ylabel("R, кН")
    axs[0].legend(fontsize=8)
    axs[0].set_title("Буксировочное сопротивление", fontsize=10, loc="left")

    axs[1].plot(vs, [p["Pb"] for p in deep], color=SEA, lw=2, label="потребная мощность")
    axs[1].axhline(H.PROP_POWER, color=ACC, lw=1.6)
    axs[1].annotate("установлено 2 x %d = %d кВт на ГЭД"
                    % (G.PROP_MOTOR_POWER, H.PROP_POWER),
                    (10.4, H.PROP_POWER - 220), color=ACC, fontsize=9)
    P24 = H.power(24)["Pb"]
    axs[1].axhline(P24, color="#8a93a5", lw=1.2, ls="--")
    axs[1].annotate("на 24 км/ч нужно %.0f кВт — 48 %% от установленной" % P24,
                    (10.4, P24 + 90), color="#56627a", fontsize=9)
    vmax = H.max_speed()
    axs[1].plot([vmax, vmax], [0, H.power(vmax)["Pb"]], color=ACC, lw=1.0, ls=":")
    axs[1].annotate("%.1f км/ч" % vmax, (vmax - 0.45, 250), color=ACC, fontsize=9, rotation=90)
    for v, c, lab in ((22, GRN, "эксплуатационная 22"), (24, GRN, "по описанию 24")):
        axs[1].axvline(v, color=c, lw=1.2, ls=":")
        axs[1].annotate(lab, (v + 0.2, 2450), color=c, fontsize=9, rotation=90)
    axs[1].set_ylim(0, 4000)
    axs[1].set_xlabel("скорость, км/ч")
    axs[1].set_ylabel("мощность на движителях, кВт")
    axs[1].legend(fontsize=8, loc="upper left")
    axs[1].set_title("Потребная и установленная мощность", fontsize=10, loc="left")
    rows = []
    for d in (4, 5, 6, 8, 10, 15):
        rows.append("H=%d: v_кр=%.1f, предел %.1f, по мощности %.1f" %
                    (d, H.critical_speed(d), 0.7 * H.critical_speed(d),
                     H.max_speed(depth=d)))
    fig.text(0.01, 0.012, "Мелководье, км/ч —  " + ";  ".join(rows),
             fontsize=8.5, color="#56627a")
    save(fig, "06_ходкость.png")


def power_balance():
    """Электробаланс по режимам: из чего складывается нагрузка на шинах."""
    rows = P.table()
    names = [P.MODE_SHORT[r["key"]] for r in rows]
    hotel = [r["hotel"] for r in rows]
    prop = [r["propulsion"] for r in rows]
    total = [r["total"] for r in rows]

    fig, axs = plt.subplots(1, 2, figsize=(14.6, 4.6),
                            gridspec_kw={"width_ratios": [1.45, 1]})
    head(fig, "Электробаланс по режимам и выбор единичной мощности ГДГ",
         "Слева — потребность на шинах ГРЩ; справа — проверка n−1 на "
         "восьмиметровом фарватере, она и назначает мощность машины")
    fig.subplots_adjust(top=0.76, bottom=0.22, wspace=0.24)

    x = range(len(rows))
    ax = axs[0]
    ax.bar(x, hotel, color=SEA, label="судовые и бытовые")
    ax.bar(x, prop, bottom=hotel, color=ACC, label="гребные электродвигатели")
    for i, v in enumerate(total):
        ax.text(i, v + 60, "%.0f" % v, ha="center", fontsize=8.5, color=INK)
    # уровни мощности станции
    for n in (1, 2, 3):
        ax.axhline(n * G.DG_POWER, color="#8892a4", lw=0.9, ls="--")
        ax.text(len(rows) - 0.45, n * G.DG_POWER + 50, "%d ГДГ" % n,
                fontsize=8, color="#56627a", ha="right")
    ax.set_xticks(list(x))
    ax.set_xticklabels(names, fontsize=8)
    ax.set_ylabel("мощность на шинах ГРЩ, кВт")
    ax.set_ylim(0, G.DG_TOTAL + 300)
    ax.legend(fontsize=8, loc="upper center")
    ax.set_title("Потребность по режимам", fontsize=10, loc="left")

    ax = axs[1]
    units = (1200, 1400, 1600, 1800)
    speeds = [P.redundancy("мелководье", unit=u, count=3)["speed"] for u in units]
    colors = [GRN if s >= G.SPEED_KMH else ACC for s in speeds]
    ax.bar([str(u) for u in units], speeds, color=colors, width=0.55)
    ax.axhline(G.SPEED_KMH, color=INK, lw=1.4)
    ax.text(-0.42, G.SPEED_KMH + 0.12, "служебная %d км/ч" % G.SPEED_KMH,
            fontsize=8.5, color=INK, ha="left")
    for i, s in enumerate(speeds):
        ax.text(i, s + 0.12, "%.1f" % s, ha="center", fontsize=9, color=INK)
    ax.set_ylim(18, max(speeds) + 1.2)
    ax.set_xlabel("единичная мощность ГДГ, кВт (три машины)")
    ax.set_ylabel("достижимая скорость при отказе одного ГДГ, км/ч")
    ax.set_title("Проверка n−1, фарватер 8 м", fontsize=10, loc="left")

    sh = P.single_shaft_comparison(22)
    fig.text(0.01, 0.012,
             "Один вал при этой осадке невозможен: винт равной площади диска "
             "D = %.2f м встал бы кромкой на %.2f м выше ватерлинии; "
             "с винтом %.2f м потеря КПД %.0f %%."
             % (sh["equal_diameter"], abs(sh["immersion"]),
                G.PROP_DIAMETER, sh["power_penalty"]),
             fontsize=8.5, color="#56627a")
    save(fig, "07_электробаланс.png")


if __name__ == "__main__":
    print("строю графики:")
    hydro_curves()
    bonjean_and_load()
    stability_plots()
    strength_plots()
    resistance_plots()
    power_balance()
