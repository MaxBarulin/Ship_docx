# -*- coding: utf-8 -*-
"""Проекция «корпус» крупно и таблица плазовых ординат.

Таблица - настоящая плазовая: теоретические шпангоуты (через L/20 и полушпангоуты в
оконечностях) на ватерлиниях плазовой таблицы. Ординаты в миллиметрах, как их и снимают с
плаза. Прочерк значит, что ватерлиния лежит ниже килевой линии этого шпангоута, то есть на нём
её просто нет. Под ординатами - параметры сечения, по которым оно построено - высота килевой
линии, полуширота днища, высота и полуширота по борту, радиус скулы и развал борта.

Вид - растровый чертёж (P.чертёж): шрифт ГОСТ, линии чёрные, таблица как в Word - тонкие
чёрные линии, шапка светло-серая. Строки фактической посадки и расчётной осадки выделены
полужирным (у шрифта ГОСТ нет начертания bold - обводка глифа). Заголовка и штампа нет.

Раскладка - под вставку в записку по ширине листа А4: ширина рисунка ШИРИНА при кегле КЕГЛЬ.
Ватерлинии внизу корпуса идут через 0,15 м - при таком кегле подписи у линий слиплись бы,
поэтому они вынесены столбцом влево с выносками. Номера шпангоутов - в два яруса над палубой,
выноска к верхнему ярусу поднимается вертикально между подписями нижнего.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.patheffects as pe
from lib import gorizont as G, gorizont_hydro as H, plain as P

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "расчёты")
os.makedirs(OUT, exist_ok=True)
ROWS = G.offsets_rows()
# ординаты - с нишей колеса: на шпангоутах 9 и 10 борт срезан стенкой ниши
for r in ROWS:
    yn = H.niche_half(r["x"])
    r["y"] = [None if y is None else min(y, yn) for y in r["y"]]
    r["b_brt"] = min(r["b_brt"], yn)
WL = list(G.WATERLINES)
T = H.equilibrium()["T"]
D = G.DEPTH
Б = G.BEAM / 2
КРАЙ = Б + 0.65                              # сетка корпуса за бортом, м
МИДЕЛЬ = max(r["n"] for r in ROWS) / 2

ШИРИНА = 8.0                                 # дюймов, 203 мм - вставка на 165 мм даёт 0,81
КЕГЛЬ = 8.5                                  # pt, после вставки 6,9
КЕГЛЬ_ТАБЛ = 8.0                             # 25 столбцов по 4 цифры - на 8,5 pt не помещаются
ПОЛЕ = 0.03                                  # дюйма по краям
КОНТУР, КРИВАЯ, ТОНКАЯ = 1.0, 0.6, 0.25      # толщины линий, pt
ШТРИХПУНКТИР = (0, (12, 3, 1.5, 3))
XL = КРАЙ + 1.5                              # поле корпуса по ширине, м от ДП
ПТ = 72.0 * (ШИРИНА - 2 * ПОЛЕ) / (2 * XL)   # pt на метр корпуса
СТРОКА_ТАБЛ = 12.0                           # высота строки таблицы, pt


def пт(v):
    """Отступ в pt -> в метрах корпуса."""
    return v / ПТ


def ном(n):
    return ("%g" % n).replace(".", ",")


def mm(v):
    return "-" if v is None else "%d" % round(v * 1000)


def _орд(r, z):
    """Полуширота шпангоута r на высоте z, м, None - ниже килевой линии."""
    if z < r["z_kil"] - 1e-6:
        return None
    return min(H.half_breadth(r["x"], min(z, r["z_brt"])), H.niche_half(r["x"]))


def разнести(zs, g):
    """Подписи на высотах zs (по возрастанию) не ближе g друг к другу, со средним сдвигом группы
    ноль - слипшиеся подписи раздвигаются от своего центра."""
    гр = []                                   # [первый индекс, число, низ]
    for i, z in enumerate(zs):
        гр.append([i, 1, z])
        while len(гр) > 1 and гр[-1][2] < гр[-2][2] + гр[-2][1] * g:
            a, b = гр[-2], гр[-1]
            n = a[1] + b[1]
            низ = sum(zs[a[0] + k] - k * g for k in range(n)) / n
            гр[-2:] = [[a[0], n, низ]]
    return [c[2] + k * g for c in гр for k in range(c[1])]


def таблица():
    """Строки таблицы: (подпись, ячейки, выделить)."""
    # Плазовые ватерлинии плюс две наши: фактическая посадка (из нагрузки масс) и расчётная
    # осадка, по которой построены обводы. Ординаты на них считаются той же геометрией
    # сечения, что и остальные строки, с нишей колеса.
    строки = [(z, P.ч(z, 2), [r["y"][k] for r in ROWS], False) for k, z in enumerate(WL)]
    for z, имя in ((T, "%s факт" % P.ч(T, 2)), (G.DRAFT, "%s расч." % P.ч(G.DRAFT, 2))):
        if all(abs(z - w) > 0.005 for w in WL):
            строки.append((z, имя, [_орд(r, z) for r in ROWS], True))
    строки.sort(key=lambda t: t[0])
    body = [(имя, [mm(y) for y in ys], выд) for z, имя, ys, выд in строки]
    body.append(("z киля, мм", ["%d" % round(r["z_kil"] * 1000) for r in ROWS], False))
    body.append(("полушир. днища", ["%d" % round(r["b_kil"] * 1000) for r in ROWS], False))
    body.append(("z борта, мм", ["%d" % round(r["z_brt"] * 1000) for r in ROWS], False))
    body.append(("полушир. борта", ["%d" % round(r["b_brt"] * 1000) for r in ROWS], False))
    # r <= 0 - сечение без скулы: библиотека строит его прямой от днища к борту (gorizont_lines.section_y)
    body.append(("R скулы, мм", ["%d" % round(r["r"] * 1000) if r["r"] > 1e-6 else "-" for r in ROWS], False))
    body.append(("развал, град", [P.ч(r["phi"], 1) for r in ROWS], False))
    return body


def ширина_текста(fig, s, fontsize=КЕГЛЬ):
    tt = fig.text(0, 0, s, fontsize=fontsize)
    w = tt.get_window_extent(fig.canvas.get_renderer()).width * 72.0 / fig.dpi
    tt.remove()
    return w


def draw():
    with P.чертёж():
        return _draw()


def _draw():
    h = пт(КЕГЛЬ * 0.93)                      # высота строки подписи, м корпуса
    # ------------------------------------------------ подписи ватерлиний и ярусы --
    лев = [(z, P.ч(z, 2)) for z in WL[0::2]]
    прав = sorted([(z, P.ч(z, 2)) for z in WL[1::2]] + [(T, "ВЛ %s" % P.ч(T, 2))])
    g = пт(КЕГЛЬ * 0.98)
    lz_л = разнести([z for z, _ in лев], g)
    lz_п = разнести([z for z, _ in прав], g)
    lz = lz_л + lz_п
    Z_КОЛЕНО = D + пт(24)                      # излом выносок номеров шпангоутов
    Z_ЯРУС = (Z_КОЛЕНО + пт(4), Z_КОЛЕНО + пт(4) + h + пт(3))
    z_низ = min(min(lz) - h / 2, -пт(3) - h) - пт(4)
    z_верх = Z_ЯРУС[1] + h + пт(3)
    h_корп = (z_верх - z_низ) * ПТ / 72.0     # дюймов

    body = таблица()
    cols = ["ВЛ, м"] + [ном(r["n"]) for r in ROWS]
    n_rows = len(body) + 1
    h_табл = n_rows * СТРОКА_ТАБЛ / 72.0
    ШАГ = КЕГЛЬ * 1.35 / 72.0                 # шаг строк пояснения, дюйма
    h_пояс = 3 * ШАГ + 0.06                   # три строки пояснения
    H_fig = ПОЛЕ + h_корп + 0.12 + h_пояс + h_табл + ПОЛЕ

    fig = plt.figure(figsize=(ШИРИНА, H_fig))
    # ------------------------------------------------------------- корпус --
    ax = fig.add_axes([ПОЛЕ / ШИРИНА, (H_fig - ПОЛЕ - h_корп) / H_fig,
                       1 - 2 * ПОЛЕ / ШИРИНА, h_корп / H_fig])
    ax.set_prop_cycle(color=["black"])
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_xlim(-XL, XL)
    ax.set_ylim(z_низ, z_верх)
    for y in range(-int(Б), int(Б) + 1):
        if y:
            ax.plot([y, y], [0, D], lw=ТОНКАЯ, zorder=1)
    for z in WL[1:]:
        ax.plot([-КРАЙ, КРАЙ], [z, z], lw=ТОНКАЯ, zorder=1)
    ax.plot([-КРАЙ, КРАЙ], [0, 0], lw=КРИВАЯ, zorder=2)
    for s, метки, уровни in ((-1, лев, lz_л), (1, прав, lz_п)):
        for (z, подпись), l in zip(метки, уровни):
            ax.plot([s * КРАЙ, s * (КРАЙ + 0.22), s * (КРАЙ + 0.32)], [z, l, l], lw=ТОНКАЯ, zorder=1)
            ax.text(s * (КРАЙ + 0.36), l, подпись, fontsize=КЕГЛЬ, ha="right" if s < 0 else "left",
                    va="center")
    стороны = {1: [], -1: []}
    for r in ROWS:
        n, x = r["n"], r["x"]
        s = 1 if n >= МИДЕЛЬ else -1
        pts = [p for p in H.profile(x) if p[0] <= D + 1e-9]
        yd = H.half_breadth(x, D)
        ys = [0] + [s * p[1] for p in pts] + [s * yd, 0]
        zs = [pts[0][0]] + [p[0] for p in pts] + [D, D]
        ax.plot(ys, zs, lw=КОНТУР if float(n) == int(n) else КРИВАЯ, zorder=3)
        стороны[s].append((n, yd))
    # номера шпангоутов - в два яруса над палубой: выноска от борта до излома, дальше
    # вертикально к подписи, к верхнему ярусу - между подписями нижнего
    for s, items in стороны.items():
        items.sort(key=lambda t: t[1])
        m = len(items)
        for i, (n, yd) in enumerate(items):
            lx = s * (0.8 + (КРАЙ + 0.9 - 0.8) * (i + 0.5) / m)
            ly = Z_ЯРУС[i % 2]
            ax.plot([s * yd, lx, lx], [D + пт(1), Z_КОЛЕНО, ly - пт(1)], lw=ТОНКАЯ, zorder=2)
            ax.text(lx, ly, ном(n), fontsize=КЕГЛЬ, ha="center", va="bottom")
    ax.plot([-КРАЙ, КРАЙ], [T, T], lw=КОНТУР, ls=ШТРИХПУНКТИР, zorder=4)
    ax.plot([0, 0], [-пт(4), D + пт(14)], lw=КРИВАЯ, ls=ШТРИХПУНКТИР, zorder=2)
    ax.text(0, Z_ЯРУС[0], "ДП", fontsize=КЕГЛЬ, ha="center", va="bottom")
    for s in (-1, 1):
        кадры = [ном(r["n"]) for r in ROWS if (r["n"] >= МИДЕЛЬ) == (s > 0)]
        ax.text(s * Б / 2, -пт(3), "%s шпангоуты %s-%s" % ("Носовые" if s > 0 else "Кормовые",
                                                        кадры[0], кадры[-1]),
                fontsize=КЕГЛЬ, ha="center", va="top")

    # ------------------------------------------------ таблица плазовых ординат --
    y_пояс = H_fig - ПОЛЕ - h_корп - 0.12
    ниша = [ном(r["n"]) for r in ROWS if H.niche_half(r["x"]) < Б - 1e-6]
    пояснение = [
        "Таблица плазовых ординат, мм от ДП. Строки - ватерлинии, м, столбцы - номера шпангоутов, "
        "шпация L/20 = %s м." % P.ч(G.LOA / 20, 3),
        "Прочерк - ватерлиния ниже килевой линии шпангоута, в строке R скулы - сечение без скулы, прямое.",
        "На шпангоутах %s ордината ограничена нишей колеса." % " и ".join(ниша)]
    for i, s in enumerate(пояснение):
        fig.text(ПОЛЕ / ШИРИНА, (y_пояс - i * ШАГ) / H_fig, s, fontsize=КЕГЛЬ, va="top")

    ax2 = fig.add_axes([ПОЛЕ / ШИРИНА, ПОЛЕ / H_fig, 1 - 2 * ПОЛЕ / ШИРИНА, h_табл / H_fig])
    ax2.axis("off")
    w_all = (ШИРИНА - 2 * ПОЛЕ) * 72.0
    w0 = max(ширина_текста(fig, b[0], КЕГЛЬ_ТАБЛ) for b in body) + 2 * 3.0
    w_col = (w_all - w0) / len(ROWS)
    w_макс = max(ширина_текста(fig, c, КЕГЛЬ_ТАБЛ) for b in body for c in b[1])
    assert w_col > w_макс + 2.5, "таблица не помещается по ширине: %.1f < %.1f pt" % (w_col, w_макс)
    tbl = ax2.table(cellText=[[b[0]] + b[1] for b in body], colLabels=cols,
                    colWidths=[w0 / w_all] + [w_col / w_all] * len(ROWS),
                    cellLoc="center", colLoc="center", bbox=[0, 0, 1, 1])
    tbl.auto_set_font_size(False)
    tbl.set_fontsize(КЕГЛЬ_ТАБЛ)
    выделить = {i + 1 for i, b in enumerate(body) if b[2]}
    for (r, c), cell in tbl.get_celld().items():
        cell.set_edgecolor("black")
        cell.set_linewidth(0.4)
        cell.set_facecolor("#F2F2F2" if r == 0 else "white")
        if c == 0:
            cell._loc = "left"
            cell.PAD = 3.0 / w0
            cell.get_text().set_ha("left")
        if r in выделить:
            cell.get_text().set_path_effects([pe.withStroke(linewidth=0.45, foreground="black")])

    p = os.path.join(OUT, "01б_корпус_и_ординаты.png")
    P.сохранить(fig, p)
    plt.close(fig)
    return p


if __name__ == "__main__":
    print(draw())
