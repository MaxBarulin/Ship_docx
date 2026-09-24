# -*- coding: utf-8 -*-
"""Производство узла ВГ-2026.46.00 - схема производства и кооперации, планировка цеха, сроки, загрузка, себестоимость.

    python scripts/производство_фундамента.py

Всё - из lib.gorizont_twistlock: цепочка участков и кооперации, зоны ангара и маршруты деталей,
график с привязкой к дорожной карте постройки, загрузка оборудования серией, статьи себестоимости.
Картинки - renders/горизонт_2026/схемы/07…10, 12_узел_*.png.

Вид - простой (lib.plain). Загрузка, сроки и себестоимость - диаграммы Excel (Calibri, цвета Office,
десятичная запятая), схема производства и планировка - рисунки Word (Times New Roman, белые
прямоугольники, чёрные линии 0,8 pt). Покупка и кооперация - пунктиром. Заголовков на картинках нет -
название даёт подпись «Рисунок N» в документе. Рамки и переносы подгоняются под текст по
get_window_extent. После генерации картинки смотрят глазами.
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
from matplotlib.lines import Line2D
from lib import gorizont_twistlock as T, gorizont_build as B, plain as P

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "схемы")
os.makedirs(OUT, exist_ok=True)
ЛИН = P.ЛИНИЯ
ПУНКТИР = (0, (4, 2.5))


def ф(x, nd=0):
    return (("%." + str(nd) + "f") % x).replace(".", ",")


def тыс(x):
    """Рубли в тысячах с пробелом-разделителем разрядов: 1 268."""
    return "{:,}".format(int(round(x / 1000.0))).replace(",", "\u00a0")


# --- измерение текста ----------------------------------------------------------------
def _нр(s):
    """Число с единицей не разрываются переносом - неразрывный пробел («3 т/ч», «по 6 шт»)."""
    s = re.sub(r"(\d) (?=(т/ч|т|кН|мм|м|шт|кг|мкм|°С|кВт)(?![А-Яа-яЁё]))", "\\1\u00a0", s)
    s = re.sub(r"(\d) × (?=\d)", "\\1\u00a0×\u00a0", s)
    return re.sub(r"(?<![А-Яа-яЁё])(поз\.|ГОСТ) (?=\d)", "\\1\u00a0", s)


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
        s = "\n".join(textwrap.wrap(текст, n, break_on_hyphens=False))
        if s in было:
            continue
        было.add(s)
        w, h = _размер(fig, s, **kw)
        if w <= ширина:
            return s, w, h, True
        if узкий is None or w < узкий[1]:
            узкий = (s, w, h, False)
    return узкий


def _стрелка(ax, pts, стиль="-", lw=ЛИН, head=9):
    """Стрелка Word - ломаная и залитый треугольник на конце."""
    xs, ys = [p[0] for p in pts], [p[1] for p in pts]
    ax.plot(xs, ys, color="black", lw=lw, ls=стиль, solid_capstyle="butt", dash_capstyle="butt", zorder=4)
    (xa, ya), (xb, yb) = pts[-2], pts[-1]
    L = ((xb - xa) ** 2 + (yb - ya) ** 2) ** 0.5
    k = min(1.0, 0.02 / L) if L else 0
    ax.add_patch(FancyArrowPatch((xb - (xb - xa) * k, yb - (yb - ya) * k), (xb, yb), arrowstyle="-|>",
                                 mutation_scale=head, lw=lw, color="black", shrinkA=0, shrinkB=0, zorder=5))


def _линейчатая(ax):
    """Оси линейчатой диаграммы Excel: ось категорий слева серой линией, сетка по значениям вертикальная."""
    P.оси(ax, "x")
    ax.spines["left"].set_visible(True)
    ax.spines["left"].set_color(P.ОСЬ)
    ax.spines["bottom"].set_visible(False)


# --- 10. загрузка оборудования - линейчатая диаграмма Excel ---------------------------------
def загрузка():
    з = [r for r in T.загрузка()]
    с = T.серия()
    n = len(з)
    with P.excel():
        fig = plt.figure(figsize=(8.6, 4.8))
        подписи = [r["коротко"] for r in з]
        w_п = max(_размер(fig, s, fontsize=10)[0] for s in подписи)
        лев = (w_п + 0.25) / 8.6
        низ_текст = ("Загрузка за срок серии %d шт. Литейное оборудование - за %d дней плавок, остальное - за %d рабочих дней, "
                     "печь ПН-12-2 - в две смены, остальное - в одну." % (с["n"], с["дней_литья"], с["дней"]))
        s_н, _, h_н, _ = _уложить(fig, низ_текст, 8.3, fontsize=9)
        низ = (h_н + 0.85) / 4.8
        ax = fig.add_axes([лев, низ, 0.96 - лев, 0.97 - низ])
        ys = list(range(n))
        ax.barh(ys, [r["доля"] for r in з], height=0.6, color=P.OFFICE[0], zorder=2)
        for y, r in zip(ys, з):
            ax.text(r["доля"] + 1.0, y, "%s %%" % P.ч(r["доля"]), va="center", fontsize=9)
        ax.set_yticks(ys)
        ax.set_yticklabels(подписи, fontsize=10)
        ax.set_ylim(n - 0.5, -0.5)
        ax.set_xlim(0, 100)
        ax.set_xticks(range(0, 101, 20))
        _линейчатая(ax)
        P.запятая(ax, "x")
        ax.set_xlabel("Загрузка, %")
        fig.text(0.015, 0.03, s_н, fontsize=9, va="bottom")
        P.рамка(fig)
        p = P.сохранить(fig, os.path.join(OUT, "10_узел_мощности.png"))
        plt.close(fig)
    return p


# --- 12. себестоимость по статьям - линейчатая диаграмма Excel ------------------------------
def себестоимость():
    с = T.себестоимость()
    статьи = sorted(с["статьи"], key=lambda r: -r[1])
    n = len(статьи)
    with P.excel():
        W, Hs = 8.6, 0.36
        fig = plt.figure(figsize=(W, 4))
        подписи = [_уложить(fig, k, 3.3, fontsize=9, linespacing=1.05)[0] for k, _ in статьи]
        w_п = max(_размер(fig, s, fontsize=9, linespacing=1.05)[0] for s in подписи)
        низ_текст = ("Партия %d узлов - %s тыс. руб., за штуку %s тыс. руб. На установленный фундамент с учётом ЗИП и "
                     "испытательного образца - %s тыс. руб." % (с["штук"], тыс(с["партия"]), тыс(с["за_штуку"]), тыс(с["на_фундамент"])))
        s_н, _, h_н, _ = _уложить(fig, низ_текст, W - 0.3, fontsize=9)
        H = n * Hs + 0.95 + h_н
        fig.set_size_inches(W, H)
        лев = (w_п + 0.25) / W
        низ = (h_н + 0.75) / H
        ax = fig.add_axes([лев, низ, 0.95 - лев, 1 - 0.12 / H - низ])
        ys = list(range(n))
        v = [x / 1000.0 for _, x in статьи]
        ax.barh(ys, v, height=0.62, color=P.OFFICE[0], zorder=2)
        верх = 500 * (int(max(v) * 1.18) // 500 + 1)
        for y, x in zip(ys, v):
            ax.text(x + верх * 0.01, y, тыс(x * 1000.0), va="center", fontsize=9)
        ax.set_yticks(ys)
        ax.set_yticklabels(подписи, fontsize=9, linespacing=1.05)
        ax.set_ylim(n - 0.5, -0.5)
        ax.set_xlim(0, верх)
        _линейчатая(ax)
        ax.xaxis.set_major_formatter(matplotlib.ticker.FuncFormatter(lambda x, _p: "{:,}".format(int(x)).replace(",", "\u00a0")))
        ax.set_xlabel("Тысяч рублей на партию")
        fig.text(0.015, 0.1 / H, s_н, fontsize=9, va="bottom")
        P.рамка(fig)
        p = P.сохранить(fig, os.path.join(OUT, "12_узел_себестоимость.png"))
        plt.close(fig)
    return p


# --- 07. схема производства и кооперации - блок-схема Word ----------------------------------
#: (ключ, колонка, ряд, заголовок, пояснение, вид). Колонки - кооперация, литейная ветка, общий участок,
#: плазменная ветка и закупки. Вид: свой участок, кооп (покупка и кооперация), служба (верфь).
БЛОКИ = [
    ("МОД", 0, 1, "Модельный цех", "модели, стержневые ящики, кондукторы", "кооп"),
    ("ШИХТА", 1, 0, "Закупка", "лом, ферросплавы, песок, смола", "кооп"),
    ("ПОК", 2, 0, "Кузнечное производство", "поковки поз. 3 из стали 40Х, круг поз. 2 - металлобаза", "кооп"),
    ("ЛИСТ", 3, 0, "Закупка", "лист 09Г2С 20 и 12 мм", "кооп"),
    ("ЛАБ", 0, 2, "Лаборатория", "химсостав и механические свойства от плавки", "кооп"),
    ("ЛИТ", 1, 1, "Литейный участок", "стержни, формовка, плавка, заливка, выбивка. Литейщики-формовщики, плавильщик", "свой"),
    ("ВХК", 2, 1, "Входной контроль", "сертификат, твёрдость. Контролёр ОТК", "свой"),
    ("ПЛЗ", 3, 1, "Плазменная резка поз. 4 и 5", "платики с окном и овалами, шайбы-подковы. Оператор плазмы", "свой"),
    ("ОБР", 1, 2, "Обрубка и зачистка", "прибыли, литники, заусенцы. Литейщики-формовщики", "свой"),
    ("ТОК", 2, 2, "Токарная обработка", "вал поз. 3, стержень поз. 2. Станочник", "свой"),
    ("ЗАЧ", 3, 2, "Зачистка кромок", "грат и окалина. Оператор плазмы", "свой"),
    ("ТО", 1, 3, "Термический участок", "нормализация и отпуск. Термист", "свой"),
    ("ОТК1", 1, 4, "ОТК отливок", "осмотр, размеры, твёрдость. Контролёр ОТК", "свой"),
    ("СВЕ", 2, 4, "Сверлильная обработка", "отверстие Ø30 поз. 1, овалы поз. 4, отверстия поз. 2 и 3. Станочник", "свой"),
    ("СВА", 2, 5, "Сварка поз. 1 с поз. 4", "шов Т1 катет 10 по контуру. Сварщик", "свой"),
    ("З_СВ", 3, 5, "Закупка", "проволока Св-08Г2С, защитный газ", "кооп"),
    ("ОКР", 2, 6, "Окраска", "грунт ГФ-021, эмаль ПФ-115, сушка. Маляр", "свой"),
    ("З_ЛКМ", 3, 6, "Закупка", "грунт, эмаль, растворитель", "кооп"),
    ("СБ", 2, 7, "Сборка поз. 1-5", "вал, шайба в проточку, стержень на резьбе. Сварщик-сборщик", "свой"),
    ("З_КР", 3, 7, "Закупка", "крепёж А4-80, изоляция СТЭФ", "кооп"),
    ("ГП", 2, 8, "Приёмка и склад", "контроль, консервация, поддоны. Контролёр ОТК, кладовщик", "свой"),
    ("ИСП", 3, 8, "Лаборатория и РКО", "пробная и разрушающая нагрузка, акт испытаний", "кооп"),
    ("ВЕРФЬ", 2, 9, "Верфь", "установка %d фундаментов на солнечной палубе" % T.программа()["на_судно"], "служба"),
]
#: (откуда, куда, подпись, путь): «-» прямо, «в» - вниз и вбок, «обход» - слева по колонке.
СВЯЗИ = [
    ("МОД", "ЛИТ", "", "-"), ("ШИХТА", "ЛИТ", "", "-"), ("ОБР", "ЛАБ", "образцы", "-"), ("ЛИТ", "ОБР", "", "-"),
    ("ОБР", "ТО", "", "-"), ("ТО", "ОТК1", "", "-"), ("ОТК1", "СВЕ", "поз. 1", "-"),
    ("ПОК", "ВХК", "", "-"), ("ВХК", "ТОК", "", "-"), ("ТОК", "СВЕ", "поз. 2 и 3", "-"),
    ("ЛИСТ", "ПЛЗ", "", "-"), ("ПЛЗ", "ЗАЧ", "", "-"), ("ЗАЧ", "СВЕ", "поз. 4", "в"),
    ("СВЕ", "СВА", "поз. 1 и 4", "-"), ("СВЕ", "ОКР", "поз. 2 и 3", "обход"), ("СВА", "ОКР", "", "-"),
    ("ОКР", "СБ", "", "-"), ("СБ", "ГП", "", "-"), ("ГП", "ВЕРФЬ", "", "-"),
    ("З_СВ", "СВА", "", "-"), ("З_ЛКМ", "ОКР", "", "-"), ("З_КР", "СБ", "", "-"), ("ИСП", "ГП", "", "-"),
]


def схема():
    with P.word():
        return _схема()


def _схема():
    ШР, ШР_П, ПАД, М = 10.5, 9.5, 0.08, 0.14
    ШИР = 2.05                                                     # ширина текста в блоке, дюймы
    fig0 = plt.figure(figsize=(4, 4), dpi=P.DPI)
    бл = {}
    for к, col, row, заг, поясн, вид in БЛОКИ:
        s, w, h, _ = _уложить(fig0, _нр(поясн), ШИР, fontsize=ШР_П, linespacing=1.12)
        wz, hz = _размер(fig0, заг, fontsize=ШР, fontweight="bold")
        бл[к] = dict(col=col, row=row, заг=заг, текст=s, w=max(w, wz), h=hz + 0.05 + h, hz=hz, вид=вид)
    ncol = 1 + max(b["col"] for b in бл.values())
    nrow = 1 + max(b["row"] for b in бл.values())
    wк = [max(b["w"] for b in бл.values() if b["col"] == c) + 2 * ПАД for c in range(ncol)]
    hр = max(b["h"] for b in бл.values()) + 2 * ПАД
    g_к, g_р = 0.62, 0.36
    xл = [М]
    for c in range(ncol - 1):
        xл.append(xл[-1] + wк[c] + g_к)
    W = xл[-1] + wк[-1] + М
    подвал = ("Сплошной рамкой показаны участки цеха узла, пунктиром - покупка и кооперация, двойной рамкой - верфь. "
              "Шайбы поз. 5 после зачистки идут на окраску. Цехом руководит начальник участка (мастер).")
    s_п, _, h_п, _ = _уложить(fig0, подвал, W - 2 * М, fontsize=ШР_П)
    plt.close(fig0)
    yв = [-(М + r * (hр + g_р)) for r in range(nrow)]
    H = -yв[-1] + hр + 0.25 + h_п + М
    fig = plt.figure(figsize=(W, H), dpi=P.DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_xlim(0, W); ax.set_ylim(-H, 0); ax.axis("off")
    for к, b in бл.items():
        x0, yt = xл[b["col"]], yв[b["row"]]
        w = wк[b["col"]]
        b["рамка"] = (x0, yt - hр, x0 + w, yt)
        ax.add_patch(Rectangle((x0, yt - hр), w, hр, facecolor="white", edgecolor="black", lw=ЛИН,
                               ls=ПУНКТИР if b["вид"] == "кооп" else "-", zorder=2))
        if b["вид"] == "служба":
            d = 0.035
            ax.add_patch(Rectangle((x0 + d, yt - hр + d), w - 2 * d, hр - 2 * d, facecolor="none", edgecolor="black", lw=ЛИН, zorder=3))
        cy = yt - hр / 2 + b["h"] / 2
        ax.text(x0 + w / 2, cy, b["заг"], ha="center", va="top", fontsize=ШР, fontweight="bold", zorder=4)
        ax.text(x0 + w / 2, cy - b["hz"] - 0.05, b["текст"], ha="center", va="top", fontsize=ШР_П, linespacing=1.12, zorder=4)
    for a, b_, подп, путь in СВЯЗИ:
        ra, rb = бл[a]["рамка"], бл[b_]["рамка"]
        ca = ((ra[0] + ra[2]) / 2, (ra[1] + ra[3]) / 2)
        cb = ((rb[0] + rb[2]) / 2, (rb[1] + rb[3]) / 2)
        if путь == "обход":
            x = ra[0] - 0.2
            y0, y1 = ra[1] + 0.18 * hр, rb[3] - 0.3 * hр
            pts = [(ra[0], y0), (x, y0), (x, y1), (rb[0], y1)]
            _стрелка(ax, pts)
            ax.text(x - 0.06, (y0 + y1) / 2, подп, ha="right", va="center", fontsize=ШР_П)
            continue
        if путь == "в":
            if cb[1] < ca[1] and abs(ca[0] - cb[0]) > 0.01:        # вниз из-под блока, потом вбок в сторону цели
                x_end = rb[2] if cb[0] < ca[0] else rb[0]
                pts = [(ca[0], ra[1]), (ca[0], cb[1]), (x_end, cb[1])]
            _стрелка(ax, pts)
            if подп:
                ax.text((ca[0] + x_end) / 2, cb[1] + 0.05, подп, ha="center", va="bottom", fontsize=ШР_П)
            continue
        if abs(ca[0] - cb[0]) < 0.01:                                # по вертикали
            (y0, y1) = (ra[1], rb[3]) if cb[1] < ca[1] else (ra[3], rb[1])
            _стрелка(ax, [(ca[0], y0), (ca[0], y1)])
            if подп:
                ax.text(ca[0] + 0.06, (y0 + y1) / 2, подп, ha="left", va="center", fontsize=ШР_П)
        else:                                                         # по горизонтали
            (x0, x1) = (ra[2], rb[0]) if cb[0] > ca[0] else (ra[0], rb[2])
            _стрелка(ax, [(x0, ca[1]), (x1, ca[1])])
            if подп:
                ax.text((x0 + x1) / 2, ca[1] + 0.05, подп, ha="center", va="bottom", fontsize=ШР_П)
    ax.text(М, yв[-1] - hр - 0.22, s_п, ha="left", va="top", fontsize=ШР_П)
    p = P.сохранить(fig, os.path.join(OUT, "07_узел_кооперация.png"))
    plt.close(fig)
    return p


# --- 08. планировка цеха в ангаре - рисунок Word ---------------------------------------------
def _пересекает(seg, r, запас):
    """Осевой отрезок seg ((x0,y0),(x1,y1)) задевает прямоугольник r (x0,y0,x1,y1) с запасом."""
    (xa, ya), (xb, yb) = seg
    return (min(xa, xb) < r[2] + запас and max(xa, xb) > r[0] - запас and
            min(ya, yb) < r[3] + запас and max(ya, yb) > r[1] - запас)


def _путь(a, b, прочие, сдвиг=0.0):
    """Путь стрелки между прямоугольниками a и b (x0,y0,x1,y1): прямой по перекрытию проекций, иначе
    ломаная в один-два излома, не задевающая прочие прямоугольники. Сдвиг разводит параллельные линии."""
    ox = min(a[2], b[2]) - max(a[0], b[0])
    oy = min(a[3], b[3]) - max(a[1], b[1])
    прямо = []
    if oy > 0.6 and (b[0] >= a[2] or a[0] >= b[2]):
        y = (max(a[1], b[1]) + min(a[3], b[3])) / 2 + сдвиг
        прямо.append([(a[2], y), (b[0], y)] if b[0] >= a[2] else [(a[0], y), (b[2], y)])
    if ox > 0.6 and (b[1] >= a[3] or a[1] >= b[3]):
        x = (max(a[0], b[0]) + min(a[2], b[2])) / 2 + сдвиг
        прямо.append([(x, a[3]), (x, b[1])] if b[1] >= a[3] else [(x, a[1]), (x, b[3])])
    for pts in прямо:
        if not any(_пересекает(s, r, 0.05) for s in zip(pts, pts[1:]) for r in прочие):
            return pts
    вправо, вверх = (b[0] + b[2]) >= (a[0] + a[2]), (b[1] + b[3]) >= (a[1] + a[3])
    xa_г, xb_г = (a[2], b[0]) if вправо else (a[0], b[2])
    ya_г, yb_г = (a[3], b[1]) if вверх else (a[1], b[3])
    cax, cay = (a[0] + a[2]) / 2 + сдвиг, (a[1] + a[3]) / 2 + сдвиг
    cbx, cby = (b[0] + b[2]) / 2 + сдвиг, (b[1] + b[3]) / 2 + сдвиг
    вар = прямо[:0] + [[(xa_г, cay), (cbx, cay), (cbx, yb_г)],
           [(cax, ya_г), (cax, cby), (xb_г, cby)]]
    for xc in ((xa_г + xb_г) / 2 + сдвиг, xa_г + (0.5 if вправо else -0.5), xb_г - (0.5 if вправо else -0.5)):
        вар.append([(xa_г, cay), (xc, cay), (xc, cby), (xb_г, cby)])
    for yc in ((ya_г + yb_г) / 2 + сдвиг, ya_г + (0.5 if вверх else -0.5), yb_г - (0.5 if вверх else -0.5)):
        вар.append([(cax, ya_г), (cax, yc), (cbx, yc), (cbx, yb_г)])
    for pts in вар:
        if not any(_пересекает(s, r, 0.2) for s in zip(pts, pts[1:]) for r in прочие):
            return pts
    return вар[0]


СТИЛИ = {"поз. 1": dict(ls="-", lw=1.1), "поз. 4": dict(ls=(0, (5, 2.5)), lw=1.1),
         "поз. 2 и 3": dict(ls=(0, (1.2, 1.8)), lw=1.3), "узел": dict(ls="-", lw=2.0)}
ИМЕНА_МАРШРУТОВ = {"поз. 1": "поз. 1 корпус", "поз. 4": "поз. 4 платик", "поз. 2 и 3": "поз. 2 и 3 стержень и запор",
                   "узел": "узел в сборе"}


def планировка():
    with P.word():
        return _планировка()


def _планировка():
    А = T.АНГАР
    L, Bw = А["L"], А["B"]
    W = 9.6
    поле_л, поле_п = 1.3, 0.5
    S = (W - 0.2) / (L + поле_л + поле_п)                           # дюймов на метр
    x0, x1 = -поле_л, L + поле_п
    y0, y1 = -1.2, Bw + 1.6
    ШР, ШР_П = 8.5, 9.5
    fig = plt.figure(figsize=(W, 4), dpi=P.DPI)
    легенда_h = 0.55
    подвал = ("Цифры в кружках - порядок участков по ходу процесса, площадь участка - в правом нижнем углу. Рамы ангара "
              "через %s м, %s над всем пролётом. Тонкий пунктир - подача материалов, стержней и форм. Поз. 2 и 3 после "
              "сверлильного станка, шайбы поз. 5 после зачистки идут на окраску." % (
                  ф(А["шаг_рам"]), А["кран"]))
    s_п, _, h_п, _ = _уложить(fig, подвал, W - 0.3, fontsize=ШР_П)
    низ = h_п + легенда_h + 0.25
    H = (y1 - y0) * S + низ
    fig.set_size_inches(W, H)
    ax = fig.add_axes([0.1 / W, низ / H, (x1 - x0) * S / W, (y1 - y0) * S / H])
    ax.set_xlim(x0, x1); ax.set_ylim(y0, y1); ax.axis("off")
    м = 1.0 / S
    # стены, ворота, оси рам
    ax.add_patch(Rectangle((0, 0), L, Bw, facecolor="none", edgecolor="black", lw=1.6, zorder=1))
    for имя, (xw, ya, yb) in T.ВОРОТА.items():
        ax.plot([xw, xw], [ya, yb], color="white", lw=3.0, zorder=1.5)
        ax.plot([xw - 0.25, xw + 0.25], [ya, ya], color="black", lw=1.2, zorder=2)
        ax.plot([xw - 0.25, xw + 0.25], [yb, yb], color="black", lw=1.2, zorder=2)
        ax.text(xw + (-0.35 if xw == 0 else 0.35), (ya + yb) / 2, имя, rotation=90, ha="right" if xw == 0 else "left",
                va="center", fontsize=ШР_П)
    n_ос = int(round(L / А["шаг_рам"]))
    for i in range(n_ос + 1):
        x = i * А["шаг_рам"]
        ax.plot([x, x], [Bw, Bw + 0.5], color="black", lw=0.5, zorder=0)
        ax.add_patch(Circle((x, Bw + 0.95), 0.38, facecolor="white", edgecolor="black", lw=0.5))
        ax.text(x, Bw + 0.95, "%d" % (i + 1), ha="center", va="center", fontsize=ШР)
    for y, б in ((0.0, "А"), (Bw, "Б")):
        ax.plot([-0.5, 0], [y, y], color="black", lw=0.5)
        ax.add_patch(Circle((-0.9, y), 0.38, facecolor="white", edgecolor="black", lw=0.5))
        ax.text(-0.9, y, б, ha="center", va="center", fontsize=ШР)
    ax.text(L / 2, -0.55, "ангар %s × %s м, %s м²" % (ф(L), ф(Bw), ф(L * Bw)), ha="center", va="top", fontsize=ШР_П)
    пл = T.планировка()
    ax.text(3.0, 12.0, "проезд %s м" % ф(пл["проезд"]), ha="left", va="center", fontsize=ШР_П, zorder=6,
            bbox=dict(boxstyle="square,pad=0.1", facecolor="white", edgecolor="none"))
    # зоны
    рамка = {z["ключ"]: (z["x"], z["y"], z["x"] + z["w"], z["y"] + z["h"]) for z in T.ЗОНЫ}
    номер = {k: i for i, k in enumerate(T.ПОРЯДОК_ЗОН, 1)}
    ПАД, D = 0.04, 0.2
    for z in T.ЗОНЫ:
        a0, b0, a1, b1 = рамка[z["ключ"]]
        ax.add_patch(Rectangle((a0, b0), a1 - a0, b1 - b0, facecolor="white", edgecolor="black", lw=ЛИН, zorder=2))
        w_in, h_in = (a1 - a0) * S, (b1 - b0) * S
        пл_ = "%s м²" % ф(z["w"] * z["h"])
        wп, hп = _размер(fig, пл_, fontsize=ШР)
        низ_п = max(D, hп) + ПАД
        s, wт, hт, ок = _уложить(fig, _нр(z["имя"]), w_in - 2 * ПАД, fontsize=ШР, linespacing=1.05)
        if not ок or hт + низ_п + 2 * ПАД > h_in:
            raise ValueError("не влезает подпись зоны %s" % z["ключ"])
        ax.text((a0 + a1) / 2, b1 - (h_in - низ_п) / 2 * м, s, ha="center", va="center", fontsize=ШР, linespacing=1.05, zorder=6)
        ax.text(a1 - ПАД * м, b0 + ПАД * м, пл_, ha="right", va="bottom", fontsize=ШР, zorder=6)
        if z["ключ"] in номер:
            cx, cy = a0 + (ПАД + D / 2) * м, b0 + (ПАД + D / 2) * м
            ax.add_patch(Circle((cx, cy), D / 2 * м, facecolor="white", edgecolor="black", lw=ЛИН, zorder=6))
            ax.text(cx, cy, "%d" % номер[z["ключ"]], ha="center", va="center", fontsize=ШР - 0.5, zorder=7)
    # маршруты и подача
    сдвиги = {"поз. 1": 0.0, "поз. 4": -0.35, "поз. 2 и 3": 0.35, "узел": 0.0}
    for имя, путь in T.МАРШРУТЫ:
        ст = СТИЛИ[имя]
        for a, b in zip(путь, путь[1:]):
            прочие = [r for k, r in рамка.items() if k not in (a, b)]
            pts = _путь(рамка[a], рамка[b], прочие, сдвиги[имя])
            _стрелка(ax, pts, стиль=ст["ls"], lw=ст["lw"], head=8)
    for a, b, _txt in T.ПОДВОД:
        прочие = [r for k, r in рамка.items() if k not in (a, b)]
        _стрелка(ax, _путь(рамка[a], рамка[b], прочие), стиль=(0, (2, 2)), lw=0.5, head=6)
    # легенда и подвал
    lax = fig.add_axes([0.1 / W, (h_п + 0.2) / H, 1 - 0.2 / W, легенда_h / H])
    lax.axis("off")
    ручки = [Line2D([0], [0], color="black", ls=СТИЛИ[k]["ls"], lw=СТИЛИ[k]["lw"]) for k, _ in T.МАРШРУТЫ]
    ручки.append(Line2D([0], [0], color="black", ls=(0, (2, 2)), lw=0.5))
    lax.legend(ручки, [ИМЕНА_МАРШРУТОВ[k] for k, _ in T.МАРШРУТЫ] + ["подача"], loc="center left", ncol=5, frameon=False,
               fontsize=ШР_П, handlelength=3.0, columnspacing=1.6)
    fig.text(0.15 / W, (h_п + 0.08) / H, s_п, ha="left", va="top", fontsize=ШР_П)
    p = P.сохранить(fig, os.path.join(OUT, "08_узел_участок.png"))
    plt.close(fig)
    return p


# --- 09. сроки освоения - диаграмма Ганта в Excel --------------------------------------------
def освоение():
    г = T.график()
    карта = {t[0]: t for t in B.ЛЕНА}
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
        W, Hs = 9.6, 0.42
        fig = plt.figure(figsize=(W, 1), dpi=P.DPI)
        подписи = [_уложить(fig, s, 3.1, fontsize=9, linespacing=1.1)[0] for s in имена]
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
            if x + 3 + w <= X1 + (прав * W - 0.08) * дней_на_дюйм:
                ax.text(x + 3, 1.015, текст, transform=тр, ha="left", va="bottom", fontsize=9)
            else:
                ax.text(x - 3, 1.015, текст, transform=тр, ha="right", va="bottom", fontsize=9)
        P.рамка(fig)
        p = P.сохранить(fig, os.path.join(OUT, "09_узел_освоение.png"))
        plt.close(fig)
    return p


def main():
    for f in (схема, планировка, освоение, загрузка, себестоимость):
        print("  ", os.path.relpath(f(), ROOT))


if __name__ == "__main__":
    main()
