# -*- coding: utf-8 -*-
"""Теоретический чертёж - бок, полуширота, корпус.

Все три проекции строятся из одной функции обвода (gorizont_hydro.half_breadth), то есть из той
же геометрии, что и плазовая таблица и модель в Blender. Шпангоуты - теоретические сечения
плазовой таблицы (через L/20 и полушпангоуты в оконечностях), ватерлинии - отметки плазовой
таблицы, батоксы - через 1 м до борта.

Правило чтения. На боку кривые - батоксы, на полушироте - ватерлинии, на корпусе - шпангоуты.
Остальные линии на каждой проекции прямые (сетка).

Вид - растровый чертёж (P.чертёж): шрифт ГОСТ, линии чёрные, контур толще, кривые средней
толщины, сетка тонкая. Заголовка и штампа нет, название даёт подпись рисунка.

Раскладка - под вставку в записку по ширине листа А4. Бок и полуширота во всю ширину друг под
другом, корпус под ними крупнее: в одном масштабе с боком его 3 м высоты мельче подписей.
Ширина рисунка ШИРИНА при кегле КЕГЛЬ - на полосе набора 165 мм шрифт не мельче 7 pt.
Высоты ватерлиний на боку подписаны только крайние (13 отметок на 3 мм полосы слипаются), все
отметки - в таблице плазовых ординат. Совпадающие шпангоуты цилиндрической вставки на корпусе
подписаны одной выноской («3-8», «11-17»), группы находятся сравнением сечений.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import gorizont as G, gorizont_hydro as H, plain as P

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "расчёты")
os.makedirs(OUT, exist_ok=True)
FRAMES = [r[0] for r in G.OFFSETS]
FX = {r[0]: r[1] for r in G.OFFSETS}
МИДЕЛЬ = max(FRAMES) / 2                    # слева от мидель-шпангоута - кормовые
WL = list(G.WATERLINES)
BUT = [float(y) for y in range(1, int(G.BEAM / 2) + 1)]      # батоксы через 1 м до борта
D = G.DEPTH
Б = G.BEAM / 2
K = 6                                       # корпус во столько раз крупнее бока и полушироты
XS = [i * 0.25 for i in range(int(G.LOA / 0.25) + 1)]

ШИРИНА = 8.0                                # дюймов, 203 мм - вставка на 165 мм даёт 0,81
КЕГЛЬ, КЕГЛЬ_ВИДА = 8.5, 9.5                # pt, после вставки 6,9 и 7,7
КОНТУР, КРИВАЯ, ТОНКАЯ = 1.1, 0.6, 0.25     # толщины линий, pt
ШТРИХПУНКТИР = (0, (12, 3, 1.5, 3))
X0, X1 = -5.5, G.LOA + 3.0                  # поле рисунка по длине, м
ПТ = 72.0 * ШИРИНА / (X1 - X0)              # pt на метр поля рисунка


def пт(v):
    """Отступ в pt -> в метрах поля рисунка."""
    return v / ПТ


def ном(n):
    return ("%g" % n).replace(".", ",")


def раз(k):
    return "раза" if k % 10 in (2, 3, 4) and k % 100 not in (12, 13, 14) else "раз"


def buttock_z(x, y):
    """Высота батокса y на шпангоуте x, либо None."""
    zk, bk, zb, bb, phi = H._column(x)
    if bb < y:
        return None
    if bk >= y:
        return zk
    lo, hi = zk, zb
    for _ in range(40):
        mid = 0.5 * (lo + hi)
        if H.half_breadth(x, mid) < y:
            lo = mid
        else:
            hi = mid
    return 0.5 * (lo + hi)


def группы(кадры):
    """Подряд идущие шпангоуты с одинаковым сечением - [[n, ...], ...]."""
    out = []
    for n in кадры:
        ключ = tuple((round(z, 4), round(y, 4)) for z, y in H.profile(FX[n]))
        if out and out[-1][1] == ключ:
            out[-1][0].append(n)
        else:
            out.append(([n], ключ))
    return [г for г, _ in out]


def подпись_группы(г):
    return ном(г[0]) if len(г) == 1 else "%s-%s" % (ном(г[0]), ном(г[-1]))


def перенос(fig, s, ширина_pt, fontsize):
    """Строка, разбитая по словам под ширину в pt - по измеренной длине текста."""
    r = fig.canvas.get_renderer()
    out, cur = [], ""
    for w in s.split(" "):
        t = (cur + " " + w).strip()
        tt = fig.text(0, 0, t, fontsize=fontsize)
        шир = tt.get_window_extent(r).width * 72.0 / fig.dpi
        tt.remove()
        if шир > ширина_pt and cur:
            out.append(cur)
            cur = w
        else:
            cur = t
    out.append(cur)
    return out


def примечания():
    e = H.equilibrium()
    вставка = " и ".join(подпись_группы(г) for г in группы(FRAMES) if len(г) > 1)
    return ["L = %s м, B = %s м, H = %s м, T = %s м, шпация L/20 = %s м, батоксы через %s м, "
            "высоты ватерлиний - по таблице плазовых ординат."
            % (P.ч(G.LOA, 1), P.ч(G.BEAM, 2), P.ч(D, 2), P.ч(e["T"], 2), P.ч(G.LOA / 20, 2),
               ном(BUT[1] - BUT[0])),
            "Обвод - плоское днище, скуловая дуга и прямой борт с развалом. Шпангоуты %s "
            "цилиндрической вставки на корпусе совпадают." % вставка]


def draw():
    with P.чертёж():
        return _draw()


def _draw():
    h_txt = пт(КЕГЛЬ * 0.93)                 # высота строки подписи, м поля
    h_вид = пт(КЕГЛЬ_ВИДА * 0.93)
    fig = plt.figure(figsize=(ШИРИНА, 3.0))
    прим = [стр for абз in примечания() for стр in перенос(fig, абз, (X1 - пт(4)) * ПТ, КЕГЛЬ)]
    # ------------------------------------------------ раскладка по высоте, сверху вниз --
    Y_B = 0.0                                # основная линия бока
    Y_P = Y_B - пт(6) - h_вид - пт(5) - Б     # ДП полушироты
    Y_ряд1 = Y_P - пт(3)                     # номера шпангоутов
    Y_ряд2 = Y_ряд1 - h_txt - пт(1.5)        # номера полушпангоутов
    Y_ком = Y_ряд2 - h_txt - пт(9)           # название корпуса (верх строки)
    Y_мет = Y_ком - h_вид - пт(5) - h_txt    # низ подписей шпангоутов корпуса
    Y_C = Y_мет - пт(22) - D * K             # основная линия корпуса
    Y_прим = Y_C - пт(10)                    # примечания (верх первой строки)
    ШАГ_СТРОК = h_txt + пт(2.5)
    Y0 = Y_прим - len(прим) * ШАГ_СТРОК - пт(6)
    Y1 = Y_B + D + пт(5) + h_вид + пт(4)
    X_C = G.LOA / 2                          # ДП корпуса - на мидель-шпангоуте

    fig.set_size_inches(ШИРИНА, ШИРИНА * (Y1 - Y0) / (X1 - X0))
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_prop_cycle(color=["black"])
    ax.set_xlim(X0, X1)
    ax.set_ylim(Y0, Y1)
    ax.set_aspect("equal")
    ax.axis("off")

    def text(x, y, s, **kw):
        kw.setdefault("fontsize", КЕГЛЬ)
        return ax.text(x, y, s, **kw)

    # ---------------------------------------------------------------- бок --
    for z in WL:
        ax.plot([0, G.LOA], [Y_B + z] * 2, lw=ТОНКАЯ, zorder=1)
    for n in FRAMES:
        x = FX[n]
        ax.plot([x, x], [Y_B + H.keel_height(x), Y_B + H.side_height(x)], lw=ТОНКАЯ, zorder=1)
    ax.plot(XS, [Y_B + H.keel_height(x) for x in XS], lw=КОНТУР, zorder=4)
    ax.plot(XS, [Y_B + H.side_height(x) for x in XS], lw=КОНТУР, zorder=4)
    for x in (0.0, G.LOA):
        ax.plot([x, x], [Y_B + H.keel_height(x), Y_B + H.side_height(x)], lw=КОНТУР, zorder=4)
    концы = []
    for y in BUT:
        xx, zz = [], []
        for x in XS + [None]:
            z = None if x is None else buttock_z(x, y)
            if z is None:
                if xx:
                    ax.plot(xx, zz, lw=КРИВАЯ, zorder=3)
                    конец = (xx[-1], zz[-1])
                    xx, zz = [], []
                continue
            xx.append(x)
            zz.append(Y_B + z)
        концы.append((y, конец))
    # номера батоксов - у носовых концов, ниже основной линии, с выноской
    концы.sort(key=lambda t: t[1][0])
    шаг = пт(КЕГЛЬ * 1.1)
    лx = []
    for y, (xe, ze) in концы:
        лx.append(max(xe, лx[-1] + шаг) if лx else xe)
    сдвиг = sum(a - c[1][0] for a, c in zip(лx, концы)) / len(лx)
    for (y, (xe, ze)), lx in zip(концы, лx):
        lx -= сдвиг
        ax.plot([xe, lx], [ze, Y_B - пт(3)], lw=ТОНКАЯ, zorder=2)
        text(lx, Y_B - пт(3.5), ном(y), ha="center", va="top")
    text(-пт(3), Y_B, "0", ha="right", va="center")
    text(-пт(3), Y_B + D, "%s м" % ном(D), ha="right", va="center")
    text(0, Y_B + D + пт(5), "Бок. Батоксы, номер - отстояние от ДП, м", fontsize=КЕГЛЬ_ВИДА,
         va="bottom")

    # -------------------------------------------------------- полуширота --
    ax.plot([0, G.LOA], [Y_P, Y_P], lw=КРИВАЯ, zorder=4)
    for y in BUT:
        ax.plot([0, G.LOA], [Y_P + y] * 2, lw=ТОНКАЯ, zorder=1)
    for n in FRAMES:
        x = FX[n]
        ax.plot([x, x], [Y_P, Y_P + H.half_breadth(x, D)], lw=ТОНКАЯ, zorder=1)
        целый = float(n) == int(n)
        text(x, Y_ряд1 if целый else Y_ряд2, ном(n), ha="center", va="top")
    for z in WL:
        xx, yy = [], []
        for x in XS + [None]:
            if x is None or z < H.keel_height(x) - 1e-9:
                if xx:
                    ax.plot(xx, yy, lw=КРИВАЯ, zorder=3)
                    xx, yy = [], []
                continue
            xx.append(x)
            yy.append(Y_P + H.half_breadth(x, z))
    ax.plot(XS, [Y_P + H.half_breadth(x, D) for x in XS], lw=КОНТУР, zorder=4)
    text(-пт(3), Y_P, "ДП", ha="right", va="center")
    text(0, Y_P + Б + пт(5), "Полуширота. Ватерлинии, внизу номера теоретических шпангоутов",
         fontsize=КЕГЛЬ_ВИДА, va="bottom")

    # ------------------------------------------------------------- корпус --
    край = Б + 0.65
    for z in WL:
        ax.plot([X_C - край * K, X_C + край * K], [Y_C + z * K] * 2, lw=ТОНКАЯ, zorder=1)
    for y in BUT:
        for s in (1, -1):
            ax.plot([X_C + s * y * K] * 2, [Y_C, Y_C + D * K], lw=ТОНКАЯ, zorder=1)
    ax.plot([X_C - край * K, X_C + край * K], [Y_C] * 2, lw=КРИВАЯ, zorder=2)
    ax.plot([X_C] * 2, [Y_C - пт(4), Y_C + D * K + пт(12)], lw=КРИВАЯ, ls=ШТРИХПУНКТИР, zorder=2)
    text(X_C, Y_мет, "ДП", ha="center", va="bottom")
    for n in FRAMES:
        s = -1 if n < МИДЕЛЬ else 1
        pts = H.profile(FX[n])
        xx = [X_C] + [X_C + s * p[1] * K for p in pts] + [X_C]
        zz = [Y_C + pts[0][0] * K] + [Y_C + p[0] * K for p in pts] + [Y_C + D * K]
        ax.plot(xx, zz, lw=КРИВАЯ if float(n) == int(n) else КРИВАЯ * 0.7, zorder=3)
    for s, кадры in ((-1, [n for n in FRAMES if n < МИДЕЛЬ]), (1, [n for n in FRAMES if n >= МИДЕЛЬ])):
        гг = sorted(группы(кадры), key=lambda г: H.profile(FX[г[0]])[-1][1])
        m = len(гг)
        for i, г in enumerate(гг):
            p = H.profile(FX[г[0]])[-1]
            lx = X_C + s * K * (0.9 + (Б + 0.6 - 0.9) * (i + 0.5) / m)
            ax.plot([X_C + s * p[1] * K, lx], [Y_C + p[0] * K + пт(1), Y_мет - пт(1.5)],
                    lw=ТОНКАЯ, zorder=2)
            text(lx, Y_мет, подпись_группы(г), ha="center", va="bottom")
    text(X_C, Y_ком, "Корпус, в %d %s крупнее. Слева кормовые шпангоуты, справа носовые"
         % (K, раз(K)), fontsize=КЕГЛЬ_ВИДА, ha="center", va="top")

    # ---------------------------------------------------------- примечания --
    for i, стр in enumerate(прим):
        text(0, Y_прим - i * ШАГ_СТРОК, стр, va="top")

    p = os.path.join(OUT, "01_теоретический_чертёж.png")
    P.сохранить(fig, p)
    plt.close(fig)
    return p


if __name__ == "__main__":
    print(draw())
