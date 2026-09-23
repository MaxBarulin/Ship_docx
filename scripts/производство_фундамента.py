# -*- coding: utf-8 -*-
"""Производство узла ВГ-2026.46.00 - мощности, кооперация, участок, освоение (КЗ 4.3-4.6).

    python scripts/производство_фундамента.py

Всё - из lib.gorizont_twistlock: трудоёмкость по маршрутам, свободный фонд цехов,
цепочка кооперации, планировка участков и график, привязанный к дорожной карте постройки.
Картинки - renders/горизонт_2026/схемы/07…10_узел_*.png.

Вид - простой, как у рабочих материалов (lib.plain). Мощности и сроки - диаграммы Excel
(Calibri, цвета Office, легенда снизу, десятичная запятая), кооперация и планировка - рисунки
Word (Times New Roman, белые прямоугольники, чёрные линии 0,8 pt). Кооперация, новое
оборудование и подвод материалов - пунктиром, а не цветом. Заголовков на картинках нет -
название даёт подпись «Рисунок N» в документе, числа, которые были в колонках текста,
перенесены в записку узла (записка_фундамента.py). Рамки и переносы подгоняются под текст
по get_window_extent. После генерации картинки смотрят глазами.
"""
import os, re, sys, textwrap, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import matplotlib.transforms as mtransforms
from matplotlib.patches import FancyArrowPatch, Rectangle, Circle
from lib import gorizont_twistlock as T, gorizont_build as B, plain as P

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "схемы")
os.makedirs(OUT, exist_ok=True)
#: Цеха узла по ходу процесса и их названия на картинках.
ПОРЯДОК = ("ЛЦ", "ТО", "ОТК", "МЦ", "СЦ")
ИМЯ = {"ЛЦ": "Литейный цех", "ТО": "Термический участок", "ОТК": "ОТК", "МЦ": "Механический цех",
       "СЦ": "Сборочный участок", "К": "Кооперация"}
ШАГ_КОЛОНН = 6.0            # м, сетка колонн литейного пролёта (типовая планировка), только для рисунка осей
ЛИН = P.ЛИНИЯ


def ф(x, nd=0):
    return (("%." + str(nd) + "f") % x).replace(".", ",")


# --- измерение текста ----------------------------------------------------------------
def _нр(s):
    """Число с единицей не разрываются переносом - неразрывный пробел («3 т/ч», «по 6 шт»)."""
    s = re.sub(r"(\d) (?=(т/ч|т|кН|мм|м|шт|кг|мкм)(?![А-Яа-яЁё]))", "\\1\u00a0", s)
    return re.sub(r"(?<![А-Яа-яЁё])(КП|ГОСТ) (?=\d)", "\\1\u00a0", s)


def _размер(fig, текст, **kw):
    """Ширина и высота надписи в дюймах - по рендереру, а не на глаз."""
    t = fig.text(0, 0, текст, **kw)
    bb = t.get_window_extent(renderer=fig.canvas.get_renderer())
    t.remove()
    return bb.width / fig.dpi, bb.height / fig.dpi


def _уложить(fig, текст, ширина, **kw):
    """Перенос по словам в ширину (дюймы): самые длинные строки, что ещё влезают.
    Если не влезает даже по слову в строке - самый узкий вариант, флаг False."""
    узкий = None
    было = set()
    for n in range(len(текст), 3, -1):
        s = "\n".join(textwrap.wrap(текст, n))
        if s in было:
            continue
        было.add(s)
        w, h = _размер(fig, s, **kw)
        if w <= ширина:
            return s, w, h, True
        if узкий is None or w < узкий[1]:
            узкий = (s, w, h, False)
    return узкий


def _стрелка(ax, p0, p1, пунктир=False, lw=ЛИН, head=9):
    """Стрелка Word - линия и залитый треугольник на конце. Ломаная - список точек."""
    pts = [p0, p1] if not isinstance(p0, list) else p0
    ls = (0, (4, 2.5)) if пунктир else "-"
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    ax.plot(xs, ys, color="black", lw=lw, ls=ls, solid_capstyle="butt", dash_capstyle="butt", zorder=4)
    (xa, ya), (xb, yb) = pts[-2], pts[-1]
    L = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
    k = min(1.0, 0.02 / L) if L else 0
    ax.add_patch(FancyArrowPatch((xb - (xb - xa) * k, yb - (yb - ya) * k), (xb, yb), arrowstyle="-|>",
                                 mutation_scale=head, lw=lw, color="black", shrinkA=0, shrinkB=0, zorder=5))


# --- 10. мощности - линейчатая диаграмма Excel ----------------------------------------
def _линейчатая(ax):
    """Оси линейчатой диаграммы Excel: ось категорий слева серой линией, ось значений без линии,
    сетка по значениям вертикальная."""
    P.оси(ax, "x")
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color(P.ОСЬ)
    ax.spines["bottom"].set_visible(False)


def мощности():
    м = {r["цех"]: r for r in T.мощности()}
    цеха = [c for c in ПОРЯДОК if c in м] + sorted(c for c in м if c not in ПОРЯДОК)
    n = len(цеха)
    загр = [м[c]["часы"] for c in цеха]
    своб = [м[c]["свободно"] for c in цеха]
    z = sorted(T.ЗАГРУЗКА_ТЕКУЩАЯ.values())
    with P.excel():
        fig = plt.figure(figsize=(9.0, 4.6))
        ax = fig.add_axes([0.175, 0.255, 0.795, 0.715])
        h = 0.36
        ys = list(range(n))
        ax.barh([y - h / 2 for y in ys], загр, height=h, color=P.OFFICE[0], label="загрузка партией, н·ч", zorder=2)
        ax.barh([y + h / 2 for y in ys], своб, height=h, color=P.OFFICE[2], label="свободный годовой фонд, н·ч", zorder=2)
        for y, c in zip(ys, цеха):
            r = м[c]
            ax.text(r["часы"] + 8, y - h / 2, "%s (%s %%)" % (P.ч(r["часы"]), P.ч(r["доля"])), va="center", fontsize=9)
            ax.text(r["свободно"] + 8, y + h / 2, "%d" % r["свободно"], va="center", fontsize=9)
        ax.set_yticks(ys)
        ax.set_yticklabels([ИМЯ.get(c, c) for c in цеха], fontsize=10)
        ax.set_ylim(n - 0.5, -0.5)
        шаг = 200
        верх = (int(max(своб) * 1.1) // шаг + 1) * шаг
        ax.set_xlim(0, верх)
        ax.set_xticks(range(0, верх + 1, шаг))
        _линейчатая(ax)
        P.запятая(ax, "x")
        ax.set_xlabel("Нормо-часы на партию %d шт" % T.программа()["всего"])
        P.легенда(ax, ncol=2, dy=-0.17)
        fig.text(0.012, 0.025, "Свободный фонд - фонд рабочего места %s ч в год в одну смену за вычетом загрузки цеха "
                 "другими заказами %d…%d %%." % (ф(T.ФОНД_Ч), round(100 * z[0]), round(100 * z[-1])), fontsize=9)
        P.рамка(fig)
        p = P.сохранить(fig, os.path.join(OUT, "10_узел_мощности.png"))
        plt.close(fig)
    return p


# --- 07. кооперация - блок-схема Word ---------------------------------------------------
def кооперация():
    with P.word():
        return _кооперация()


def _кооперация():
    п = T.программа()
    # (имя в T.КООПЕРАЦИЯ, колонка, ряд, подпись, пояснение, вид). Раскладка «П»: литьё сверху вниз
    # слева, обработка и сборка снизу вверх посередине, кооперация и службы - справа.
    БЛОКИ = [
        ("МТО", 0, 0, "МТО верфи", "закупка шихты и формовочных материалов", "служба"),
        ("ЛЦ", 0, 1, "Литейный цех", "стержни, формовка ХТС, плавка, заливка, выбивка, обрубка", "свой"),
        ("ТО", 0, 2, "Термический участок", "нормализация и отпуск", "свой"),
        ("ЛЦ очистка", 0, 3, "Литейный цех", "очистка в дробемётной камере", "свой"),
        ("ОТК", 0, 4, "ОТК", "контроль отливок, лаборатория", "свой"),
        ("МЦ", 1, 4, "Механический цех", "обработка корпусов и замков на станках с ЧПУ", "свой"),
        ("Цинкование (кооперация)", 1, 3, "Участок цинкования", "термодиффузионное цинкование", "кооп"),
        ("СЦ", 1, 2, "Сборочный участок", "сборка, испытания на стенде, маркировка", "свой"),
        ("Склад МСЧ", 1, 1, "Склад МСЧ", "хранение до установки", "служба"),
        ("Судно - солнечная палуба", 1, 0, "Судно, солнечная палуба", "установка %d фундаментов в достройку" % п["на_судно"], "служба"),
        ("Кузнечный цех (кооперация)", 2, 4, "Кузнечный цех", "штамповка замков", "кооп"),
        ("МТО", 2, 2, "МТО верфи", "покупные изделия", "служба"),
        ("Корпусный цех", 2, 0, "Корпусный цех", "постройка надстройки", "служба"),
    ]
    СЧЁТ = {("ЛЦ", "ТО"): п["всего"], ("Кузнечный цех (кооперация)", "МЦ"): п["всего"],
            ("СЦ", "Склад МСЧ"): п["на_судно"] + п["зип"]}
    ШР, ШР_П, ПАД, М = 11, 10, 0.09, 0.12
    fig0 = plt.figure(figsize=(4, 4), dpi=P.DPI)
    блоки = []
    for имя, к, р, подп, поясн, вид in БЛОКИ:
        текст = подп + "\n" + "\n".join(textwrap.wrap(_нр(поясн), 30))
        w, h = _размер(fig0, текст, fontsize=ШР, linespacing=1.15)
        блоки.append(dict(имя=имя, к=к, р=р, текст=текст, w=w, h=h, вид=вид))

    def найти(имя, к=None):
        кандидаты = [b for b in блоки if b["имя"] == имя]
        if к is None:
            return кандидаты[0]
        return min(кандидаты, key=lambda b: abs(b["к"] - к["к"]) + abs(b["р"] - к["р"]))

    рёбра = []
    for a, txt, b in T.КООПЕРАЦИЯ:
        кб = найти(b)
        ка = найти(a, кб)
        if (a, b) in СЧЁТ:
            txt += ", всего %d" % СЧЁТ[(a, b)]
        верт = ка["к"] == кб["к"]
        assert (верт and abs(ка["р"] - кб["р"]) == 1) or (ка["р"] == кб["р"] and abs(ка["к"] - кб["к"]) == 1), (a, b)
        s, w, h, _ = _уложить(fig0, _нр(txt), 2.0 if верт else 1.6, fontsize=ШР_П, linespacing=1.1)
        рёбра.append(dict(a=ка, b=кб, txt=s, w=w, h=h, верт=верт))
    nк = 1 + max(b["к"] for b in блоки)
    nр = 1 + max(b["р"] for b in блоки)
    wк = [max(b["w"] for b in блоки if b["к"] == к) + 2 * ПАД for к in range(nк)]
    гор = [r for r in рёбра if not r["верт"]]
    hб = max(max(b["h"] for b in блоки) + 2 * ПАД, 2 * (max(r["h"] for r in гор) + 0.08))
    gр = max(0.45, max(r["h"] for r in рёбра if r["верт"]) + 0.16)
    gк = []
    for к in range(nк - 1):
        g = 0.8
        for r in рёбра:
            if not r["верт"] and min(r["a"]["к"], r["b"]["к"]) == к:
                g = max(g, r["w"] + 0.24)
            if r["верт"] and r["a"]["к"] == к:
                g = max(g, r["w"] + 0.08 + 0.12 - wк[к] / 2)
        gк.append(g)
    xл = [М]
    for к in range(nк - 1):
        xл.append(xл[-1] + wк[к] + gк[к])
    W = xл[-1] + wк[-1] + М
    yв = [-(М + р * (hб + gр)) for р in range(nр)]
    подвал = "Сплошной рамкой показаны цеха, где изготавливается узел, пунктиром - кооперация, двойной рамкой - " \
             "другие подразделения верфи и судно."
    s_п, _, h_п, _ = _уложить(fig0, подвал, W - 2 * М, fontsize=ШР_П)
    plt.close(fig0)
    y_п = yв[-1] - hб - 0.22
    H = -y_п + h_п + М
    fig = plt.figure(figsize=(W, H), dpi=P.DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(-H, 0); ax.axis("off")
    for b in блоки:
        x0, yt = xл[b["к"]], yв[b["р"]]
        w = wк[b["к"]]
        b["рамка"] = (x0, yt - hб, x0 + w, yt)
        ls = (0, (4, 2.5)) if b["вид"] == "кооп" else "-"
        ax.add_patch(Rectangle((x0, yt - hб), w, hб, facecolor="white", edgecolor="black", lw=ЛИН, ls=ls, zorder=2))
        if b["вид"] == "служба":
            d = 0.035
            ax.add_patch(Rectangle((x0 + d, yt - hб + d), w - 2 * d, hб - 2 * d, facecolor="none", edgecolor="black",
                                   lw=ЛИН, zorder=3))
        ax.text(x0 + w / 2, yt - hб / 2, b["текст"], ha="center", va="center", fontsize=ШР, linespacing=1.15, zorder=4)
    for r in рёбра:
        a, b = r["a"]["рамка"], r["b"]["рамка"]
        if r["верт"]:
            x = (a[0] + a[2]) / 2
            y0, y1 = (a[1], b[3]) if b[3] <= a[1] else (a[3], b[1])
            _стрелка(ax, (x, y0), (x, y1))
            ax.text(x + 0.08, (y0 + y1) / 2, r["txt"], ha="left", va="center", fontsize=ШР_П, linespacing=1.1)
        else:
            y = (a[1] + a[3]) / 2
            x0, x1 = (a[2], b[0]) if b[0] >= a[2] else (a[0], b[2])
            _стрелка(ax, (x0, y), (x1, y))
            ax.text((x0 + x1) / 2, y + 0.05, r["txt"], ha="center", va="bottom", fontsize=ШР_П, linespacing=1.1,
                    multialignment="center")
    ax.text(М, y_п, s_п, ha="left", va="top", fontsize=ШР_П)
    p = P.сохранить(fig, os.path.join(OUT, "07_узел_кооперация.png"))
    plt.close(fig)
    return p


# --- 08. планировка - рисунок Word -----------------------------------------------------
def _пересекает(seg, r, запас):
    """Осевой отрезок seg ((x0,y0),(x1,y1)) задевает прямоугольник r (x0,y0,x1,y1) с запасом."""
    (xa, ya), (xb, yb) = seg
    return (min(xa, xb) < r[2] + запас and max(xa, xb) > r[0] - запас and
            min(ya, yb) < r[3] + запас and max(ya, yb) > r[1] - запас)


def _путь(a, b, прочие):
    """Путь стрелки между прямоугольниками a и b (x0,y0,x1,y1): прямой по перекрытию проекций, иначе
    ломаная в один-два излома, не задевающая прочие прямоугольники."""
    ox = min(a[2], b[2]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[1], b[1])
    if oy > 0.5 and (b[0] >= a[2] or a[0] >= b[2]):
        y = (max(a[1], b[1]) + min(a[3], b[3])) / 2
        return [(a[2], y), (b[0], y)] if b[0] >= a[2] else [(a[0], y), (b[2], y)]
    if ox > 0.5 and (b[1] >= a[3] or a[1] >= b[3]):
        x = (max(a[0], b[0]) + min(a[2], b[2])) / 2
        return [(x, a[3]), (x, b[1])] if b[1] >= a[3] else [(x, a[1]), (x, b[3])]
    вправо, вверх = b[0] >= a[2], b[1] >= a[3]

    def отст(r, ось):
        return min(1.0, (r[2 + ось] - r[ось]) / 3)
    xa_г, xb_г = (a[2], b[0]) if вправо else (a[0], b[2])
    ya_г, yb_г = (a[3], b[1]) if вверх else (a[1], b[3])
    # выход и вход - на 1 м от угла, чтобы линия не подходила к подписи площади в углу
    ya_в = a[3] - отст(a, 1) if вверх else a[1] + отст(a, 1)
    yb_в = b[1] + отст(b, 1) if вверх else b[3] - отст(b, 1)
    xa_в = a[2] - отст(a, 0) if вправо else a[0] + отст(a, 0)
    xb_в = b[0] + отст(b, 0) if вправо else b[2] - отст(b, 0)
    sx, sy = (1 if вправо else -1), (1 if вверх else -1)
    вар = [[(xa_г, ya_в), (xb_в, ya_в), (xb_в, yb_г)],
           [(xa_в, ya_г), (xa_в, yb_в), (xb_г, yb_в)]]
    for xc in ((xa_г + xb_г) / 2, xa_г + sx, xb_г - sx):
        вар.append([(xa_г, ya_в), (xc, ya_в), (xc, yb_в), (xb_г, yb_в)])
    for yc in ((ya_г + yb_г) / 2, ya_г + sy, yb_г - sy):
        вар.append([(xa_в, ya_г), (xa_в, yc), (xb_в, yc), (xb_в, yb_г)])
    for pts in вар:
        if not any(_пересекает(s, r, 0.25) for s in zip(pts, pts[1:]) for r in прочие):
            return pts
    return вар[0]


def участок():
    with P.word():
        return _участок()


def _участок():
    уч = T.УЧАСТОК
    мх, му, мw, мh = T.МЕХ_ПРОЛЁТ
    лит = [r for r in уч if r[3] >= 0]
    Lx0, Ly0 = min(r[2] for r in лит), min(r[3] for r in лит)
    Lx, Ly = max(r[2] + r[4] for r in лит), max(r[3] + r[5] for r in лит)
    проезд = Ly0 - (му + мh)
    ОТСТ = 0.15                                           # оборудование - внутри своей площадки
    рамка = {имя: (x + ОТСТ, y + ОТСТ, x + w - ОТСТ, y + h - ОТСТ) for _, имя, x, y, w, h in уч}
    площадь = {имя: w * h for _, имя, x, y, w, h in уч}
    новое = [имя for имя in рамка if "испытаний" in имя]    # стенд испытаний - единственное новое оборудование
    маршрут = T.МАРШРУТ_УЧАСТКА
    номер = {имя: i for i, имя in enumerate(маршрут, 1)}

    W, ПОЛЕ_М = 9.6, 1.2
    x0, x1 = Lx0 - ПОЛЕ_М, Lx + ПОЛЕ_М
    S = W / (x1 - x0)                                      # дюймов на метр
    y0, y1 = му - 1.9, Ly + 3.4
    ШР, ШР_З, ШР_П = 9, 10, 10
    fig = plt.figure(figsize=(W, 4), dpi=P.DPI)
    подвал = ["Цифры в кружках - порядок прохождения корпуса, пунктирные стрелки - подача шихты, металла, смеси, "
              "стержней и замков.",
              "Пунктирная рамка - новое оборудование под узел, остальное оборудование действующее."]
    строки = []
    for s in подвал:
        t, _, _, _ = _уложить(fig, s, W - 0.3, fontsize=ШР_П)
        строки.append(t)
    текст_п = "\n".join(строки)
    _, h_п = _размер(fig, текст_п, fontsize=ШР_П, linespacing=1.3)
    низ = h_п + 0.2
    H = (y1 - y0) * S + низ
    fig.set_size_inches(W, H)
    ax = fig.add_axes([0, низ / H, 1, 1 - низ / H])
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.axis("off")
    м = 1.0 / S                                            # метров в дюйме

    # стены и оси колонн
    ax.add_patch(Rectangle((Lx0, Ly0), Lx - Lx0, Ly - Ly0, facecolor="none", edgecolor="black", lw=1.4, zorder=1))
    ax.add_patch(Rectangle((мх, му), мw, мh, facecolor="none", edgecolor="black", lw=1.4, zorder=1))
    n_ос = int(round((Lx - Lx0) / ШАГ_КОЛОНН))
    for i in range(n_ос + 1):
        x = Lx0 + i * ШАГ_КОЛОНН
        ax.plot([x, x], [Ly0, Ly + 0.6], color="#808080", lw=0.4, zorder=0)
        ax.text(x, Ly + 0.8, "%d" % (i + 1), ha="center", va="bottom", fontsize=ШР)
    ax.text(Lx0, Ly + 2.3, "Литейный пролёт %s × %s м" % (ф(Lx - Lx0), ф(Ly - Ly0)), ha="left", va="bottom", fontsize=ШР_З)
    ax.text(мх + мw / 2, му - 0.6, "Механический цех, участок %s × %s м" % (ф(мw), ф(мh, 1 if мh % 1 else 0)),
            ha="center", va="top", fontsize=ШР_З)
    ax.text((Lx0 + Lx) / 2, (Ly0 + му + мh) / 2, "проезд %s м для электрокара" % ф(проезд), ha="center", va="center",
            fontsize=ШР)

    # оборудование: название по центру, внизу - номер по маршруту слева и площадь справа
    ПАД, D = 0.04, 0.19
    for имя, (a0, b0, a1, b1) in рамка.items():
        ax.add_patch(Rectangle((a0, b0), a1 - a0, b1 - b0, facecolor="white", edgecolor="black", lw=ЛИН,
                               ls=(0, (4, 2.5)) if имя in новое else "-", zorder=2))
        w_in, h_in = (a1 - a0) * S, (b1 - b0) * S
        пл = "%s м²" % ф(площадь[имя])
        wп, hп = _размер(fig, пл, fontsize=ШР)
        низ_п = max(D if имя in номер else 0, hп) + ПАД
        s, wт, hт, ок = _уложить(fig, _нр(имя), w_in - 2 * ПАД, fontsize=ШР, linespacing=1.1)
        if ок and hт + низ_п + 2 * ПАД <= h_in:
            ax.text((a0 + a1) / 2, (b1 + b0 + (низ_п + ПАД) * м) / 2, s, ha="center", va="center", fontsize=ШР,
                    linespacing=1.1, zorder=6)
            ax.text(a1 - ПАД * м, b0 + ПАД * м, пл, ha="right", va="bottom", fontsize=ШР, zorder=6)
        else:
            # не влезает - подпись рядом с площадкой, с той стороны, где свободно
            s, wт, hт, _ = _уложить(fig, _нр(имя) + ", " + пл, 1.4, fontsize=ШР, linespacing=1.1)
            wm, hm = wт * м, hт * м
            cy = (b0 + b1) / 2
            места = [((a1 + 0.3, cy - hm / 2, a1 + 0.3 + wm, cy + hm / 2), "left"),
                     ((a0 - 0.3 - wm, cy - hm / 2, a0 - 0.3, cy + hm / 2), "right")]
            for (r0, r1, r2, r3), ha in места:
                if not any(_пересекает(((r0, r1), (r2, r3)), q, 0.2) for n_, q in рамка.items() if n_ != имя):
                    break
            ax.text(r0 if ha == "left" else r2, cy, s, ha=ha, va="center", fontsize=ШР, linespacing=1.1, zorder=6,
                    bbox=dict(boxstyle="square,pad=0.1", facecolor="white", edgecolor="none"))
        if имя in номер:
            cx, cy = a0 + (ПАД + D / 2) * м, b0 + (ПАД + D / 2) * м
            ax.add_patch(Circle((cx, cy), D / 2 * м, facecolor="white", edgecolor="black", lw=ЛИН, zorder=6))
            ax.text(cx, cy, "%d" % номер[имя], ha="center", va="center", fontsize=ШР, zorder=7)

    # маршрут корпуса - сплошные стрелки, подвод - пунктир
    for a, b in zip(маршрут, маршрут[1:]):
        прочие = [r for n_, r in рамка.items() if n_ not in (a, b)]
        _стрелка(ax, _путь(рамка[a], рамка[b], прочие), None, head=8)
    for a, b, _txt in T.ПОДВОД_УЧАСТКА:
        прочие = [r for n_, r in рамка.items() if n_ not in (a, b)]
        _стрелка(ax, _путь(рамка[a], рамка[b], прочие), None, пунктир=True, lw=0.6, head=7)
    fig.text(0.15 / W, (низ - 0.12) / H, текст_п, ha="left", va="top", fontsize=ШР_П, linespacing=1.3)
    p = P.сохранить(fig, os.path.join(OUT, "08_узел_участок.png"))
    plt.close(fig)
    return p


# --- 09. сроки освоения - диаграмма Ганта в Excel ---------------------------------------
def освоение():
    г = T.график()
    карта = {t[0]: t for t in B.ЛЕНА}
    # вехи карты постройки, к которым привязан график (те же задачи, что в T.график)
    вехи = [(карта[38][3], "изготовление МСЧ с %s" % карта[38][3].strftime("%d.%m.%y")),
            (карта[45][3], "достройка с %s" % карта[45][3].strftime("%d.%m.%y"))]
    имена = ["%s (%s)" % (e["этап"], e["кто"]) for e in г]
    n = len(г)
    d_min = min(e["начало"] for e in г)
    d_max = max(e["конец"] for e in г)
    н0 = dt.date(d_min.year, d_min.month, 1)
    к_ = d_max + dt.timedelta(days=150)
    м_ = ((к_.month - 1) // 3 + 1) * 3 + 1
    к0 = dt.date(к_.year + (м_ > 12), (м_ - 1) % 12 + 1, 1)
    with P.excel():
        W, Hs = 9.6, 0.43
        fig = plt.figure(figsize=(W, 1), dpi=P.DPI)
        подписи = []
        for s in имена:
            t, w, h, _ = _уложить(fig, s, 3.1, fontsize=9, linespacing=1.1)
            подписи.append(t)
        w_п = max(_размер(fig, s, fontsize=9, linespacing=1.1)[0] for s in подписи)
        верх, низ = 0.42, 0.36
        H = верх + низ + n * Hs
        fig.set_size_inches(W, H)
        лев = (w_п + 0.22) / W
        прав = 0.4 / W
        ax = fig.add_axes([лев, низ / H, 1 - лев - прав, n * Hs / H])
        X0, X1 = mdates.date2num(н0), mdates.date2num(к0)
        ax.set_xlim(X0, X1)
        ax.set_ylim(n - 0.5, -0.5)
        дней_на_дюйм = (X1 - X0) / ((1 - лев - прав) * W)
        линии = [mdates.date2num(d) for d, _ in вехи]
        БЕЛО = dict(boxstyle="square,pad=0.05", facecolor="white", edgecolor="none")
        for i, e in enumerate(г):
            a, b = mdates.date2num(e["начало"]), mdates.date2num(e["конец"]) + 1
            ax.barh(i, b - a, left=a, height=0.55, color=P.OFFICE[0], zorder=2)
            s = "%s - %s" % (e["начало"].strftime("%d.%m.%y"), e["конец"].strftime("%d.%m.%y"))
            w = _размер(fig, s, fontsize=9)[0] * дней_на_дюйм
            пад = 0.06 * дней_на_дюйм
            справа = (b + пад, b + пад + w)
            слева = (a - пад - w, a - пад)

            def можно(r):
                return r[0] >= X0 and r[1] <= X1 and not any(r[0] - пад < x < r[1] + пад for x in линии)
            if можно(справа) or not можно(слева):
                ax.text(справа[0], i, s, ha="left", va="center", fontsize=9, bbox=БЕЛО, zorder=4)
            else:
                ax.text(слева[1], i, s, ha="right", va="center", fontsize=9, bbox=БЕЛО, zorder=4)
        ax.set_yticks(range(n))
        ax.set_yticklabels(подписи, fontsize=9, linespacing=1.1)
        тики = []
        d = н0
        while d <= к0:
            if d.month in (1, 4, 7, 10):
                тики.append(d)
            d = dt.date(d.year + (d.month == 12), d.month % 12 + 1, 1)
        ax.set_xticks([mdates.date2num(d) for d in тики])
        ax.set_xticklabels([P.месяц(d) for d in тики])
        _линейчатая(ax)
        тр = mtransforms.blended_transform_factory(ax.transData, ax.transAxes)
        for d, текст in вехи:
            x = mdates.date2num(d)
            ax.plot([x, x], [0, 1.0], transform=тр, color=P.ПОДПИСЬ, lw=0.9, ls=(0, (4, 3)), zorder=3, clip_on=False)
            w = _размер(fig, текст, fontsize=9)[0] * дней_на_дюйм
            if x + 3 + w <= X1 + (прав * W - 0.08) * дней_на_дюйм:      # можно зайти в правое поле рисунка
                ax.text(x + 3, 1.015, текст, transform=тр, ha="left", va="bottom", fontsize=9)
            else:
                ax.text(x - 3, 1.015, текст, transform=тр, ha="right", va="bottom", fontsize=9)
        P.рамка(fig)
        p = P.сохранить(fig, os.path.join(OUT, "09_узел_освоение.png"))
        plt.close(fig)
    return p


def main():
    for f in (мощности, кооперация, участок, освоение):
        print("  ", os.path.relpath(f(), ROOT))


if __name__ == "__main__":
    main()
