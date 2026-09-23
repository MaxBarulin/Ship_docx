# -*- coding: utf-8 -*-
"""Расчётно-теоретические листы РТ-01…РТ-09 в DXF - из данных, не из картинок.

    python scripts/чертежи_расчёты_dxf.py            # CAD/расчёты/ВГ-2026_РТ-*.dxf
    python scripts/чертежи_dwg.py                     # → CAD/DWG/расчёты/*.dwg

Каждый лист строится теми же примитивами ezdxf, что и чертежи ОР
(`чертежи_dxf`. Рамка и штамп по ГОСТ, таблицы, слои). Обводы - по ординатам
`gorizont_hydro`, кривые - по точкам гидростатики, остойчивости, прочности и
ходкости, таблицы - из библиотек, мидель и набор - по толщинам `gorizont_struct`
и профилям. Графики рисуются в миллиметрах листа с осями, делениями и сеткой,
чертежи - в натуральную величину с масштабом в штампе. Числа те же, что в
`docs/проект/теория_корабля.md` и на растровых листах `renders/…/расчёты/`.

  РТ-01  проекция «корпус» и таблица плазовых ординат (с ВЛ 1,26 факт и 1,30 расч.)
  РТ-02  кривые элементов теоретического чертежа
  РТ-03  строевая по шпангоутам, нагрузка масс и силы поддержания
  РТ-04  остойчивость - пантокарены, ДСО, ДДО, нормы РРР
  РТ-05  общая продольная прочность - q, N, M на тихой воде и волне, эквивалентный брус
  РТ-06  ходкость - сопротивление, мощность, мелководье
  РТ-07  электробаланс по режимам, проверка n-1
  РТ-08  мидель-шпангоут конструктивный, спецификация связей
  РТ-09  схема набора корпуса - бок и днище
"""
import os, sys, math, importlib

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
from lib import gorizont as G, gorizont_hydro as H, gorizont_struct as S, gorizont_strength as St
from lib import gorizont_power as P, gorizont_manoeuvre as MN, gorizont_lines as L
ЧД = importlib.import_module("чертежи_dxf")

OUT = os.path.join(ROOT, "CAD", "расчёты")
os.makedirs(OUT, exist_ok=True)
K = ЧД.K
# листы РТ мельче листов ОР: корпус и мидель влезают на А1 в 1:25…1:40, а не в 1:50
for _sc in (40, 30, 25):
    if _sc not in ЧД.SCALES:
        ЧД.SCALES.insert(0, _sc)
СЛОИ_ГРАФИКА = [("20_ГРАФИК", 8, "CONTINUOUS"), ("21_СЕТКА", 9, "CONTINUOUS"),
                ("22_КРИВАЯ_А", 5, "CONTINUOUS"), ("23_КРИВАЯ_Б", 1, "CONTINUOUS"),
                ("24_КРИВАЯ_В", 3, "CONTINUOUS"), ("25_КРИВАЯ_Г", 30, "CONTINUOUS")]
КРИВЫЕ = ["22_КРИВАЯ_А", "23_КРИВАЯ_Б", "24_КРИВАЯ_В", "25_КРИВАЯ_Г"]
A1 = ЧД.SHEETS["A1"]


def newdoc():
    doc = ЧД.newdoc()
    for nm, col, lt in СЛОИ_ГРАФИКА:
        if nm not in doc.layers:
            doc.layers.add(name=nm, color=col, linetype=lt)
    return doc


def save(doc, name):
    p = os.path.join(OUT, name)
    doc.saveas(p)
    print("  %-52s %5d КБ" % (name, os.path.getsize(p) // 1024))
    return p


def ф(x, nd=1):
    return (("%%.%df" % nd) % x).replace(".", ",")


# --- график в миллиметрах листа ------------------------------------------------------
def _деления(lo, hi, n=6):
    span = max(hi - lo, 1e-9)
    raw = span / n
    mag = 10 ** math.floor(math.log10(raw))
    step = mag
    for m in (1, 2, 2.5, 5, 10):
        step = m * mag
        if span / step <= n + 1:
            break
    t0 = math.floor(lo / step) * step
    out = []
    i = 0
    while t0 + i * step <= hi + 1e-9:
        v = t0 + i * step
        if v >= lo - 1e-9:
            out.append(round(v, 10))
        i += 1
    return out, step


def график(msp, x0, y0, w, h, серии, xlabel, ylabel, заголовок="", xlim=None, ylim=None,
           hlines=(), vlines=(), легенда=True, h_text=2.5):
    """Оси, сетка, кривые. серии - [dict(имя, xs, ys, слой, тип)], hlines/vlines - [(значение, подпись, тип)]."""
    xs_all = [x for s in серии for x in s["xs"]]
    ys_all = [y for s in серии for y in s["ys"]]
    xlo, xhi = xlim if xlim else (min(xs_all), max(xs_all))
    ylo, yhi = ylim if ylim else (min(0.0, min(ys_all)), max(ys_all))
    if yhi - ylo < 1e-9:
        yhi = ylo + 1.0
    xt, _ = _деления(xlo, xhi)
    yt, _ = _деления(ylo, yhi)

    def X(v):
        return x0 + (v - xlo) / (xhi - xlo) * w

    def Y(v):
        return y0 + (v - ylo) / (yhi - ylo) * h
    ЧД.rect(msp, x0, y0, x0 + w, y0 + h, "20_ГРАФИК")
    for v in xt:
        if xlo - 1e-9 <= v <= xhi + 1e-9:
            msp.add_line((X(v), y0), (X(v), y0 + h), dxfattribs={"layer": "21_СЕТКА"})
            msp.add_line((X(v), y0), (X(v), y0 - 1.5), dxfattribs={"layer": "20_ГРАФИК"})
            ЧД.text(msp, X(v), y0 - 4.0, ("%g" % v).replace(".", ","), h_text, 1, "08_ТЕКСТ", TA.TOP_CENTER)
    for v in yt:
        if ylo - 1e-9 <= v <= yhi + 1e-9:
            msp.add_line((x0, Y(v)), (x0 + w, Y(v)), dxfattribs={"layer": "21_СЕТКА"})
            msp.add_line((x0, Y(v)), (x0 - 1.5, Y(v)), dxfattribs={"layer": "20_ГРАФИК"})
            ЧД.text(msp, x0 - 2.5, Y(v), ("%g" % v).replace(".", ","), h_text, 1, "08_ТЕКСТ", TA.MIDDLE_RIGHT)
    if ylo < 0 < yhi:
        msp.add_line((x0, Y(0)), (x0 + w, Y(0)), dxfattribs={"layer": "20_ГРАФИК"})
    ЧД.text(msp, x0 + w / 2.0, y0 - 9.5, xlabel, h_text + 0.3, 1, "08_ТЕКСТ", TA.TOP_CENTER)
    ЧД.text(msp, x0 - 14.0, y0 + h / 2.0, ylabel, h_text + 0.3, 1, "08_ТЕКСТ", TA.MIDDLE_CENTER, rot=90.0)
    if заголовок:
        ЧД.text(msp, x0, y0 + h + 3.0, заголовок, 3.5, 1, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    for v, подпись, тип in hlines:
        if ylo <= v <= yhi:
            msp.add_line((x0, Y(v)), (x0 + w, Y(v)), dxfattribs={"layer": "20_ГРАФИК", "linetype": тип})
            ЧД.text(msp, x0 + w - 1.0, Y(v) + 1.0, подпись, h_text - 0.3, 1, "08_ТЕКСТ", TA.BOTTOM_RIGHT)
    for v, подпись, тип in vlines:
        if xlo <= v <= xhi:
            msp.add_line((X(v), y0), (X(v), y0 + h), dxfattribs={"layer": "20_ГРАФИК", "linetype": тип})
            ЧД.text(msp, X(v) + 1.0, y0 + h - 1.0, подпись, h_text - 0.3, 1, "08_ТЕКСТ", TA.TOP_LEFT, rot=90.0)
    for i, s in enumerate(серии):
        pts = [(X(x), Y(y)) for x, y in zip(s["xs"], s["ys"]) if xlo - 1e-9 <= x <= xhi + 1e-9]
        if len(pts) > 1:
            msp.add_lwpolyline(pts, dxfattribs={"layer": s.get("слой", КРИВЫЕ[i % 4]), "linetype": s.get("тип", "CONTINUOUS")})
    if легенда:
        ly = y0 + h - 4.0
        for i, s in enumerate(серии):
            msp.add_line((x0 + 3.0, ly), (x0 + 11.0, ly), dxfattribs={"layer": s.get("слой", КРИВЫЕ[i % 4]), "linetype": s.get("тип", "CONTINUOUS")})
            ЧД.text(msp, x0 + 13.0, ly, s["имя"], h_text, 1, "08_ТЕКСТ", TA.MIDDLE_LEFT)
            ly -= 4.5
    return X, Y


def лист_графиков(mark, title, subtitle, notes, material="-"):
    """Лист А1 в миллиметрах бумаги - рамка с началом координат в левом нижнем углу."""
    doc = newdoc()
    msp = doc.modelspace()
    ЧД.frame(msp, "A1", 1, (0, 0, A1[0], A1[1]), mark, title, subtitle, notes, material)
    return doc, msp


def заголовок(msp, s, y=A1[1] - 14):
    ЧД.text(msp, 30, y, s, 5.0, 1, "08_ТЕКСТ", TA.MIDDLE_LEFT)


# --- РТ-01 корпус и ординаты --------------------------------------------------------------
def rt01():
    rows = G.offsets_rows()
    for r in rows:
        yn = H.niche_half(r["x"])
        r["y"] = [None if y is None else min(y, yn) for y in r["y"]]
        r["b_brt"] = min(r["b_brt"], yn)
    T = H.equilibrium()["T"]
    WL = list(G.WATERLINES)
    доп = [(T, "%s факт" % ф(T, 2)), (G.DRAFT, "%s расч." % ф(G.DRAFT, 2))]

    def орд(r, z):
        if z < r["z_kil"] - 1e-6:
            return None
        return min(H.half_breadth(r["x"], min(z, r["z_brt"])), H.niche_half(r["x"]))
    строки = [(z, ф(z, 2), [r["y"][k] for r in rows]) for k, z in enumerate(WL)]
    for z, имя in доп:
        if all(abs(z - w) > 0.005 for w in WL):
            строки.append((z, имя, [орд(r, z) for r in rows]))
    строки.sort(key=lambda t: t[0])
    n = len(rows)
    # лист: проекция «корпус» сверху (мм модели), таблица снизу
    ширины = [32] + [14] * n          # «радиус скулы, мм» - в графу, не на числа
    w_tab = sum(ширины)
    sc = 50
    bbox = (-9.5 * K, -(7.0 + (len(строки) + 8) * 5.5 * sc / K) * K, max(9.5 * K, w_tab * sc - 9.5 * K), 6.8 * K)
    sheet, sc = ЧД.pick_sheet(bbox[2] - bbox[0], bbox[3] - bbox[1])
    bbox = (-9.5 * K, -(7.0 * K + (len(строки) + 8) * 5.5 * sc), max(9.5 * K, w_tab * sc - 9.5 * K), 6.8 * K)
    doc = newdoc(); msp = doc.modelspace()
    # ватерлинии и ДП
    for z in WL:
        msp.add_line((-8.9 * K, z * K), (8.9 * K, z * K), dxfattribs={"layer": "07_ОСИ", "linetype": "DOT"})
        ЧД.text(msp, -9.1 * K, z * K, ф(z, 2), 2.2, sc, "08_ТЕКСТ", TA.MIDDLE_RIGHT)
    # фактическая и расчётная ВЛ почти совпадают: нижняя подписана под своей линией, верхняя - над
    for k, (z, имя) in enumerate(sorted(доп)):
        msp.add_line((-8.9 * K, z * K), (8.9 * K, z * K), dxfattribs={"layer": "07_ОСИ", "linetype": "DASHED"})
        ЧД.text(msp, 9.1 * K, z * K + (-0.4 if k == 0 else 0.4) * sc, "ВЛ " + имя, 2.4, sc, "07_ОСИ",
                TA.TOP_LEFT if k == 0 else TA.BOTTOM_LEFT)
    msp.add_line((0, -0.3 * K), (0, (G.DEPTH + 1.9) * K), dxfattribs={"layer": "07_ОСИ", "linetype": "CENTER"})
    ЧД.text(msp, 0, (G.DEPTH + 2.1) * K, "ДП", 3.0, sc, "08_ТЕКСТ")
    # шпангоуты: корма слева, нос справа
    подписи = {1: [], -1: []}
    for r in rows:
        nn, x = r["n"], r["x"]
        s_ = 1 if nn >= 10 else -1
        pts = [p for p in H.profile(x) if p[0] <= G.DEPTH + 1e-9]
        yd = H.half_breadth(x, G.DEPTH)
        ys = [0.0] + [s_ * p[1] for p in pts] + [s_ * yd, 0.0]
        zs = [pts[0][0]] + [p[0] for p in pts] + [G.DEPTH, G.DEPTH]
        ЧД.poly(msp, [(y * K, z * K) for y, z in zip(ys, zs)], "01_ОБШИВКА")
        zb = H.side_height(x)
        if zb > G.DEPTH + 0.01:
            zz = [G.DEPTH + (min(zb, 4.9) - G.DEPTH) * k / 6 for k in range(7)]
            msp.add_lwpolyline([(s_ * H.half_breadth(x, z) * K, z * K) for z in zz], dxfattribs={"layer": "02_ПАЛУБЫ", "linetype": "DASHED"})
        подписи[s_].append((nn, yd))
    for s_, items in подписи.items():
        items.sort(key=lambda t: t[1])
        m = len(items)
        for i, (nn, yd) in enumerate(items):
            lx = s_ * (1.2 + (9.6 - 1.2) * (i + 0.5) / m)
            ly = 5.6 if i % 2 == 0 else 5.1
            msp.add_line((s_ * yd * K, (G.DEPTH + 0.03) * K), (lx * K, (ly - 0.12) * K), dxfattribs={"layer": "09_РАЗМЕРЫ"})
            ЧД.text(msp, lx * K, ly * K, "%g" % nn, 2.4, sc, "08_ТЕКСТ", TA.BOTTOM_CENTER)
    ЧД.text(msp, -5.0 * K, (G.DEPTH + 2.5) * K, "кормовые шпангоуты 0…9", 2.6, sc, "08_ТЕКСТ")
    ЧД.text(msp, 5.0 * K, (G.DEPTH + 2.5) * K, "носовые шпангоуты 10…20", 2.6, sc, "08_ТЕКСТ")
    # таблица ординат
    def mm(v):
        return "-" if v is None else "%d" % round(v * 1000)
    head = ["ВЛ, м"] + ["%g" % r["n"] for r in rows]
    body = [[имя] + [mm(y) for y in ys] for z, имя, ys in строки]
    body += [["z киля, мм"] + ["%d" % round(r["z_kil"] * 1000) for r in rows],
             ["полушир. днища"] + ["%d" % round(r["b_kil"] * 1000) for r in rows],
             ["z борта, мм"] + ["%d" % round(r["z_brt"] * 1000) for r in rows],
             ["полушир. борта"] + ["%d" % round(r["b_brt"] * 1000) for r in rows],
             ["радиус скулы, мм"] + ["%d" % round(r["r"] * 1000) for r in rows],
             ["развал борта, °"] + [ф(r["phi"], 1) for r in rows]]
    y_tab = -1.2 * K
    ЧД.text(msp, -9.5 * K, y_tab + 3.5 * sc, "Таблица плазовых ординат, мм от ДП. Строки - ватерлинии, столбцы - теоретические шпангоуты "
            "(шпация L/20 = %s м). Выделены ватерлинии фактической посадки %s м и расчётной осадки %s м" % (ф(G.LOA / 20, 3), ф(T, 2), ф(G.DRAFT, 2)),
            2.6, sc, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    ЧД.table(msp, -9.5 * K, y_tab, sc, head, body, ширины, h_row=5.5)
    # выделение наших ватерлиний - рамка поверх строки
    for i, (z, имя, _) in enumerate(строки):
        if "факт" in имя or "расч" in имя:
            yy = y_tab - (i + 1) * 5.5 * sc
            ЧД.rect(msp, -9.5 * K, yy - 5.5 * sc, -9.5 * K + w_tab * sc, yy, "07_ОСИ")
    notes = ("Обводы - плоское днище, скуловая дуга, касательная к днищу и к борту, прямой борт с развалом, ординаты - по плазовой таблице.",
             "На шпангоутах в районе колёс (x = %s…%s м) борт срезан стенкой ниши - полуширота ограничена niche_half(x)." % (ф(L.WHEEL_X - L.NICHE_LEN / 2, 1), ф(L.WHEEL_X + L.NICHE_LEN / 2, 1)),
             "Прочерк - ватерлиния ниже килевой линии шпангоута. Штрих над палубой - фальшборт.",
             "Ординаты на ватерлиниях %s и %s м посчитаны той же геометрией сечения, что и плазовые." % (ф(T, 2), ф(G.DRAFT, 2)))
    ЧД.frame(msp, sheet, sc, bbox, "ВГ-2026 РТ-01 корпус и ординаты", "Проекция «корпус» и таблица плазовых ординат",
             "Волжский Горизонт · L = %s м · B = %s м · T = %s м" % (ф(G.LOA, 1), ф(G.BEAM, 1), ф(T, 2)), notes, "-")
    return save(doc, "ВГ-2026_РТ-01_корпус_и_ординаты.dxf")


# --- РТ-02 кривые элементов ------------------------------------------------------------------
def rt02():
    ts = [0.6 + 0.15 * i for i in range(17)]
    rows = [H.hydrostatics(t) for t in ts]
    T = H.equilibrium()["T"]
    doc, msp = лист_графиков("ВГ-2026 РТ-02 кривые элементов", "Кривые элементов теоретического чертежа",
                             "Волжский Горизонт · осадка 0,6…%s м · T = %s м" % (ф(G.DEPTH, 1), ф(T, 2)),
                             ("Гидростатика - интегрированием по обводам с нишами колёс, шаг по длине 0,5 м.",
                              "Штриховая горизонталь - осадка в полном грузу %s м по нагрузке масс." % ф(T, 2),
                              "Обозначения. V - объёмное водоизмещение, Aw - площадь ватерлинии, xc, xf - абсциссы ЦВ и ЦТ ВЛ,",
                              "zc - аппликата ЦВ, zm - поперечный метацентр, r - метацентрический радиус. Delta, alpha, beta - коэффициенты полноты."))
    заголовок(msp, "Кривые элементов теоретического чертежа - по осадке")
    панели = [
        ("Водоизмещение и площадь ватерлинии", "V, м³ / Aw, м²", [("V, м³", [r["V"] for r in rows]), ("Aw, м²", [r["Aw"] for r in rows])]),
        ("Абсциссы ЦВ и ЦТ ватерлинии", "x, м", [("xc, м", [r["xc"] for r in rows]), ("xf, м", [r["xf"] for r in rows])]),
        ("Аппликаты ЦВ и метацентра, радиус", "z, м", [("zc, м", [r["zc"] for r in rows]), ("zm, м", [r["zm"] for r in rows]), ("r, м", [r["r"] for r in rows])]),
        ("Коэффициенты полноты", "-", [("delta", [r["delta"] for r in rows]), ("alpha", [r["alpha"] for r in rows]), ("beta", [r["beta"] for r in rows])]),
    ]
    x = 40
    for заг, xl, серии in панели:
        график(msp, x, 120, 160, 330, [dict(имя=n, xs=v, ys=ts) for n, v in серии], xl, "осадка T, м", заг,
               ylim=(0.6, 3.0), hlines=[(T, "T = %s" % ф(T, 2), "DASHED")])
        x += 195
    return save(doc, "ВГ-2026_РТ-02_кривые_элементов.dxf")


# --- РТ-03 строевая и нагрузка ---------------------------------------------------------------
def rt03():
    xs = H._xs(1.0)
    T = H.equilibrium()["T"]
    om = [H.section_area(x, T) for x in xs]
    w = H.weight_distribution(xs)
    b = [H.RHO * o for o in om]
    doc, msp = лист_графиков("ВГ-2026 РТ-03 строевая и нагрузка", "Строевая по шпангоутам и нагрузка масс",
                             "Волжский Горизонт · T = %s м · V = %s м³" % (ф(T, 2), ф(H._trapz(om, xs), 0)),
                             ("Слева корма. Площади погружённых сечений omega(x) при осадке %s м - по обводам с нишами колёс." % ф(T, 2),
                              "Нагрузка масс w(x) - по группам нагрузки - корпус по площади обшивки, остальное равномерно по границам групп.",
                              "Силы поддержания b(x) = rho·omega(x). Их разность - нагрузка на корпус как балку (лист РТ-05)."))
    заголовок(msp, "Строевая по шпангоутам и нагрузка масс")
    график(msp, 40, 340, 700, 190, [dict(имя="omega(x), м²", xs=xs, ys=om)], "x от кормового перпендикуляра, м", "omega, м²",
           "Строевая по шпангоутам при T = %s м" % ф(T, 2), xlim=(0, G.LOA))
    график(msp, 40, 100, 700, 190, [dict(имя="нагрузка масс w(x), т/м", xs=xs, ys=w, слой="23_КРИВАЯ_Б"),
                                    dict(имя="силы поддержания b(x), т/м", xs=xs, ys=b, слой="22_КРИВАЯ_А")],
           "x от кормового перпендикуляра, м", "т/м", "Нагрузка масс и силы поддержания", xlim=(0, G.LOA))
    return save(doc, "ВГ-2026_РТ-03_строевая_и_нагрузка.dxf")


# --- РТ-04 остойчивость ------------------------------------------------------------------------
def rt04():
    zt = G.DECKS["средняя"]
    a = H.stability_summary()
    bb = H.stability_summary(z_top=zt)
    rows, s, wa, e = H.rrr_checks()
    wb = H.weather_criterion(H.CLASS, z_top=zt)
    doc, msp = лист_графиков("ВГ-2026 РТ-04 остойчивость", "Остойчивость на больших углах крена",
                             "Волжский Горизонт · класс «%s» · D = %s т · h = %s м" % (H.CLASS, ф(e["D"], 0), ф(a["h"], 2)),
                             ("Сплошная - корпус до высоты борта %s м, штриховая - с закрытым ярусом главной палубы до %s м." % (ф(G.DEPTH, 2), ф(zt, 2)),
                              "Пантокарены - по обводам с нишами колёс, ДСО GZ = l_k - zg·sin(theta), ДДО - интеграл ДСО.",
                              "Критерий погоды K = %s (корпус) и %s (с надстройкой) при норме не менее 1,0, амплитуда качки %s°, кренящий момент ветра %s т·м." % (ф(wa["K"], 1), ф(wb["K"], 1), ф(wa["theta_r"], 1), ф(wa["Mv"], 0))))
    заголовок(msp, "Остойчивость на больших углах крена - пантокарены, ДСО, ДДО и нормы РРР")
    x = 40
    for заг, yl, ka, kb, слой in (("Пантокарены l_k", "l_k, м", "lk", "lk", "22_КРИВАЯ_А"),
                                   ("ДСО - плечи статической остойчивости", "GZ, м", "gz", "gz", "23_КРИВАЯ_Б"),
                                   ("ДДО - работа восстанавливающего момента", "l_d, м·рад", "dyn", "dyn", "24_КРИВАЯ_В")):
        серии = [dict(имя="корпус", xs=a["theta"], ys=a[ka], слой=слой),
                 dict(имя="с надстройкой", xs=bb["theta"], ys=bb[kb], слой=слой, тип="DASHED")]
        if ka == "gz":
            серии.append(dict(имя="h = %s м (касательная)" % ф(a["h"], 2), xs=[0, 57.3], ys=[0, a["h"]], слой="25_КРИВАЯ_Г", тип="DOT"))
        график(msp, x, 300, 220, 220, серии, "угол крена, град", yl, заг, xlim=(0, 90))
        x += 255
    таб = [[r["name"], ф(r["value"], 2), "%s %s" % (r["op"], ("%g" % r["limit"]).replace(".", ",")), "выполнено" if r["ok"] else "НЕ ВЫПОЛНЕНО"] for r in rows]
    ЧД.text(msp, 40, 262, "Нормы остойчивости Российского Речного Регистра, класс «%s»" % H.CLASS, 3.5, 1, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    ЧД.table(msp, 40, 258, 1, ["Критерий", "Значение", "Норма", "Итог"], таб, [110, 30, 30, 34], h_row=6.0)
    return save(doc, "ВГ-2026_РТ-04_остойчивость.dxf")


# --- РТ-05 продольная прочность ------------------------------------------------------------------
def rt05():
    r = St.stresses()
    g = r["girder"]
    lim = r["sigma_allow"] * g["W_deck_m3"]
    doc, msp = лист_графиков("ВГ-2026 РТ-05 продольная прочность", "Общая продольная прочность",
                             "Волжский Горизонт · волна h = %s м, длина %s м, класс «%s»" % (ф(H.WAVE_HEIGHT[H.CLASS], 1), ф(St.WAVE_LENGTH[H.CLASS], 0), H.CLASS),
                             ("Нагрузка q(x) = b(x) - w(x) на тихой воде и на волне (перегиб, прогиб), N и M - интегрированием по длине.",
                              "Эквивалентный брус (лист РТ-08) - A = %s см², z0 = %s м, I = %s м⁴, W палубы %s м³, W днища %s м³." % (ф(g["A"], 0), ф(g["z0"], 3), ф(g["I_m4"], 3), ф(g["W_deck_m3"], 3), ф(g["W_bot_m3"], 3)),
                              "Предельный момент по допускаемому напряжению %s МПа (0,6 ReH стали %s) - ± %s МН·м - штриховые линии." % (ф(r["sigma_allow"], 0), r["steel"]["name"], ф(lim, 0))))
    заголовок(msp, "Общая продольная прочность - нагрузка, перерезывающие силы, изгибающие моменты")
    слои = {"тихая вода": "22_КРИВАЯ_А", "перегиб": "23_КРИВАЯ_Б", "прогиб": "24_КРИВАЯ_В"}
    cases = [row["case"] for row in r["rows"]]
    y = 395
    for заг, key, yl, k in (("Нагрузка q(x)", "q", "q, кН/м", 1.0), ("Перерезывающие силы N(x)", "N", "N, кН", 1.0), ("Изгибающие моменты M(x)", "M", "M, МН·м", 1e-3)):
        серии = [dict(имя=c["condition"], xs=c["xs"], ys=[v * k for v in c[key]], слой=слои[c["condition"]]) for c in cases]
        hl = [(lim, "+M доп", "DASHED"), (-lim, "-M доп", "DASHED")] if key == "M" else ()
        график(msp, 40, y, 700, 120, серии, "x от кормового перпендикуляра, м" if key == "M" else "", yl, заг, xlim=(0, G.LOA), hlines=hl)
        y -= 145
    таб = [[row["condition"], ф(row["M"] / 1000.0, 1), ф(row["sigma_deck"], 0), ф(row["sigma_bot"], 0), "проходит" if row["ok"] else "НЕ ПРОХОДИТ"] for row in r["rows"]]
    ЧД.table(msp, 40, 62, 1, ["Случай", "M, МН·м", "σ палубы, МПа", "σ днища, МПа", "Итог"], таб, [40, 30, 42, 42, 40], h_row=6.0)   # внизу слева, штамп справа
    return save(doc, "ВГ-2026_РТ-05_продольная_прочность.dxf")


# --- РТ-06 ходкость --------------------------------------------------------------------------------
def rt06():
    vs = [8 + 0.5 * i for i in range(27)]
    deep = [H.power(v) for v in vs]
    Rf = [0.5 * H.RHO * 1000 * p["S"] * p["v"] ** 2 * (p["Cf"] * (1 + p["k"]) + 0.0004) / 1000 for p in deep]
    Rr = [0.5 * H.RHO * 1000 * p["S"] * p["v"] ** 2 * p["Cr"] / 1000 for p in deep]
    P24 = H.power(G.SPEED_MAX_KMH)["Pb"]
    vmax = H.max_speed()
    doc, msp = лист_графиков("ВГ-2026 РТ-06 ходкость", "Ходкость - сопротивление, мощность, мелководье",
                             "Волжский Горизонт · %s км/ч эксплуатационная · %s км/ч максимальная" % (ф(G.SPEED_KMH, 1), ф(G.SPEED_MAX_KMH, 1)),
                             ("Сопротивление на глубокой воде - трение по ITTC-1957 с формфактором + остаточное.",
                              "Установлено 2 × %d = %d кВт на ГЭД колёс. На %s км/ч нужно %s кВт (%s %% установленной), предельная скорость %s км/ч." % (G.WHEEL_MOTOR_POWER, H.PROP_POWER, ф(G.SPEED_MAX_KMH, 1), ф(P24, 0), ф(100 * P24 / H.PROP_POWER, 0), ф(vmax, 1)),
                              "Мелководье - критическая скорость sqrt(g·H), предел 0,7 от неё, ограничение по мощности, просадка по Баррасу."))
    заголовок(msp, "Ходкость - буксировочное сопротивление и потребная мощность")
    график(msp, 40, 300, 340, 220, [dict(имя="полное R", xs=vs, ys=[p["R"] for p in deep], слой="22_КРИВАЯ_А"),
                                    dict(имя="трение с формфактором", xs=vs, ys=Rf, слой="24_КРИВАЯ_В", тип="DASHED"),
                                    dict(имя="остаточное", xs=vs, ys=Rr, слой="23_КРИВАЯ_Б", тип="DASHED")],
           "скорость, км/ч", "R, кН", "Буксировочное сопротивление")
    график(msp, 430, 300, 340, 220, [dict(имя="потребная мощность Pb", xs=vs, ys=[p["Pb"] for p in deep], слой="22_КРИВАЯ_А")],
           "скорость, км/ч", "мощность на движителях, кВт", "Потребная и установленная мощность", ylim=(0, H.PROP_POWER * 1.6),
           hlines=[(H.PROP_POWER, "установлено %d кВт" % H.PROP_POWER, "CONTINUOUS"), (P24, "%s кВт на %s км/ч" % (ф(P24, 0), ф(G.SPEED_MAX_KMH, 1)), "DASHED")],
           vlines=[(G.SPEED_KMH, "эксплуатационная %s" % ф(G.SPEED_KMH, 1), "DOT"), (G.SPEED_MAX_KMH, "максимальная %s" % ф(G.SPEED_MAX_KMH, 1), "DOT"), (vmax, "предел %s" % ф(vmax, 1), "DASHED")])
    таб1 = [["%d" % d, ф(H.critical_speed(d), 1), ф(0.7 * H.critical_speed(d), 1), ф(H.max_speed(depth=d), 1)] for d in (4, 5, 6, 8, 10, 15)]
    ЧД.text(msp, 40, 262, "Мелководье по глубине фарватера, км/ч", 3.5, 1, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    ЧД.table(msp, 40, 258, 1, ["H, м", "v критическая", "предел 0,7 v кр", "по мощности"], таб1, [24, 36, 36, 36], h_row=6.0)
    таб2 = [[ф(r["h"], 1), ф(r["v_fnh"], 1), ф(r["v"], 1), ф(r["squat"], 2), ф(r["запас"], 2)] for r in MN.shallow_table()]
    ЧД.text(msp, 200, 262, "Просадка и запас под килём при T = %s м" % ф(H.equilibrium()["T"], 2), 3.5, 1, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    ЧД.table(msp, 200, 258, 1, ["H, м", "по Fnh, км/ч", "идём, км/ч", "просадка, м", "под килём, м"], таб2, [24, 34, 30, 32, 34], h_row=6.0)
    return save(doc, "ВГ-2026_РТ-06_ходкость.dxf")


# --- РТ-07 электробаланс ------------------------------------------------------------------------------
def rt07():
    rows = P.table()
    units = (400, 500, 600, 800)
    speeds = [P.redundancy("мелководье", unit=u, count=3)["speed"] for u in units]
    doc, msp = лист_графиков("ВГ-2026 РТ-07 электробаланс", "Электробаланс по режимам и выбор мощности ГДГ",
                             "Волжский Горизонт · 3 ГДГ × %d кВт · батарея %d кВт·ч · солнечные модули %s кВт" % (G.DG_POWER, G.BATTERY_KWH, ф(G.SOLAR_KW, 0)),
                             ("Потребность на шинах ГРЩ по режимам - судовые и бытовые потребители плюс гребные ГЭД.",
                              "Проверка n-1 - при отказе одного ГДГ на фарватере 4 м достижимая скорость должна быть не ниже служебной %s км/ч." % ф(G.SPEED_KMH, 1),
                              "Аварийный ДГ %d кВт, гребные ГЭД колёс 2 × %d кВт." % (G.EMERGENCY_DG, G.WHEEL_MOTOR_POWER)))
    заголовок(msp, "Электробаланс по режимам и проверка n-1")
    # столбики режимов
    x0, y0, w, h = 40, 300, 440, 220
    ymax = G.DG_TOTAL + 300
    ЧД.rect(msp, x0, y0, x0 + w, y0 + h, "20_ГРАФИК")
    yt, _ = _деления(0, ymax, 6)
    for v in yt:
        yy = y0 + v / ymax * h
        msp.add_line((x0, yy), (x0 + w, yy), dxfattribs={"layer": "21_СЕТКА"})
        ЧД.text(msp, x0 - 2.5, yy, "%d" % v, 2.5, 1, "08_ТЕКСТ", TA.MIDDLE_RIGHT)
    for n in (1, 2, 3):
        yy = y0 + n * G.DG_POWER / ymax * h
        msp.add_line((x0, yy), (x0 + w, yy), dxfattribs={"layer": "20_ГРАФИК", "linetype": "DASHED"})
        ЧД.text(msp, x0 + w - 1, yy + 1, "%d ГДГ = %d кВт" % (n, n * G.DG_POWER), 2.4, 1, "08_ТЕКСТ", TA.BOTTOM_RIGHT)
    bw = w / len(rows)
    for i, r in enumerate(rows):
        xa = x0 + i * bw + bw * 0.2
        xb = x0 + (i + 1) * bw - bw * 0.2
        y1 = y0 + r["hotel"] / ymax * h
        y2 = y0 + r["total"] / ymax * h
        ЧД.rect(msp, xa, y0, xb, y1, "22_КРИВАЯ_А")
        ЧД.rect(msp, xa, y1, xb, y2, "23_КРИВАЯ_Б")
        ЧД.text(msp, (xa + xb) / 2, y2 + 1.5, "%d" % round(r["total"]), 2.6, 1, "08_ТЕКСТ", TA.BOTTOM_CENTER)
        ЧД.text(msp, (xa + xb) / 2, y0 - 4.0, P.MODE_SHORT[r["key"]].replace("\n", " "), 2.3, 1, "08_ТЕКСТ", TA.TOP_CENTER)
    ЧД.text(msp, x0 - 14, y0 + h / 2, "мощность на шинах ГРЩ, кВт", 2.8, 1, "08_ТЕКСТ", TA.MIDDLE_CENTER, rot=90)
    ЧД.text(msp, x0, y0 + h + 3, "Потребность по режимам. Нижняя часть столбика - судовые и бытовые, верхняя - гребные ГЭД", 3.5, 1, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    # таблица режимов
    таб = [[r["name"], ф(r["hotel"], 0), ф(r["propulsion"], 0), ф(r["total"], 0), "%d" % r["dg"], ф(r["load"], 0) + " %", "да" if r["ok"] else "нет"] for r in rows]
    ЧД.table(msp, 520, 520, 1, ["Режим", "Судовые, кВт", "ГЭД, кВт", "Всего, кВт", "ГДГ в работе", "Загрузка", "Резерв"], таб, [58, 30, 26, 28, 28, 24, 20], h_row=6.0)
    # n-1
    таб2 = [["%d" % u, ф(s, 1), "да" if s >= G.SPEED_KMH else "нет"] for u, s in zip(units, speeds)]
    ЧД.text(msp, 520, 430, "Проверка n-1 на фарватере 4 м - скорость при отказе одного из трёх ГДГ", 3.5, 1, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    ЧД.table(msp, 520, 426, 1, ["Единичная мощность ГДГ, кВт", "Скорость, км/ч", "≥ %s км/ч" % ф(G.SPEED_KMH, 1)], таб2, [70, 40, 40], h_row=6.0)
    return save(doc, "ВГ-2026_РТ-07_электробаланс.dxf")


# --- РТ-08 мидель-шпангоут ------------------------------------------------------------------------
def rt08():
    X = S.X_MID
    b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(X)
    T = H.equilibrium()["T"]
    DB, SP = S.DB_HEIGHT, S.SPACING
    PL, PR = S.PLATES, S.PROFILES
    g = S.equivalent_girder()
    r = St.stresses()
    bbox = (-6.0 * K, -1.8 * K, 20.5 * K, 5.2 * K)     # слева - выноски к днищу и палубе, справа - таблицы
    sheet, sc = ЧД.pick_sheet(bbox[2] - bbox[0], bbox[3] - bbox[1])
    doc = newdoc(); msp = doc.modelspace()
    XT = 15.0 * K                                         # левый край таблиц, мм модели

    def ln(y0, z0, y1, z1, layer="01_ОБШИВКА"):
        msp.add_line((y0 * K, z0 * K), (y1 * K, z1 * K), dxfattribs={"layer": layer})

    def профиль(y, z, имя, ang=90):
        hw, tw, bf, tf = PR[имя]
        a = math.radians(ang)
        dy, dz = math.cos(a) * hw / 1000.0, math.sin(a) * hw / 1000.0
        ln(y, z, y + dy, z + dz, "10_НАБОР")
        if bf:
            py, pz = -math.sin(a) * bf / 2000.0, math.cos(a) * bf / 2000.0
            ln(y + dy - py, z + dz - pz, y + dy + py, z + dz + pz, "10_НАБОР")
    # обшивка правого борта
    ln(0, z_kil, b_dn, z_kil); ln(b_dn, z_kil, b_sk, z_sk); ln(b_sk, z_sk, b_pal, z_brt)
    ln(0, DB, b_sk - 0.30, DB, "02_ПАЛУБЫ"); ln(0, z_brt, b_pal, z_brt, "02_ПАЛУБЫ")
    msp.add_line((0, (z_kil - 0.2) * K), (0, (z_brt + 0.5) * K), dxfattribs={"layer": "07_ОСИ", "linetype": "CENTER"})
    ЧД.text(msp, 0, (z_brt + 0.65) * K, "ДП", 3.0, sc, "08_ТЕКСТ")
    for y in (0.0, 2.75, 5.50):
        ln(y, z_kil, y, DB, "10_НАБОР")
    for j in range(1, 13):
        y = j * SP
        if y < b_dn - 0.35 and abs(y - 2.75) > 0.15 and abs(y - 5.50) > 0.15:
            профиль(y, z_kil, "ребро днища")
    for j in range(1, 14):
        y = j * SP
        if y < b_sk - 0.55:
            профиль(y, DB, "ребро второго дна", ang=-90)
        if y < b_pal - 0.75 and abs(y - 4.10) > 0.2:
            профиль(y, z_brt, "ребро палубы", ang=-90)
    for y in (0.0, 4.10):
        hw = PR["карлингс"][0] / 1000.0
        ln(y, z_brt - hw, y, z_brt, "10_НАБОР"); ln(y - 0.09, z_brt - hw, y + 0.09, z_brt - hw, "10_НАБОР")
    ln(b_sk - 0.12, z_sk, b_pal - 0.12, z_brt, "10_НАБОР")
    ln(b_sk - 0.52, 2.60, b_sk - 0.12, 2.60, "10_НАБОР"); ln(b_sk - 0.52, 2.55, b_sk - 0.52, 2.65, "10_НАБОР")
    ЧД.poly(msp, [((b_sk - 0.12) * K, DB * K), ((b_sk - 0.12) * K, (DB + 0.85) * K), ((b_sk - 1.05) * K, DB * K)], "10_НАБОР", close=True)
    ЧД.poly(msp, [((b_pal - 0.13) * K, z_brt * K), ((b_pal - 0.13) * K, (z_brt - 0.80) * K), ((b_pal - 1.00) * K, z_brt * K)], "10_НАБОР", close=True)
    msp.add_line((-0.2 * K, T * K), ((b_pal + 0.4) * K, T * K), dxfattribs={"layer": "07_ОСИ", "linetype": "DASHED"})
    ЧД.text(msp, (b_pal + 0.5) * K, T * K, "ВЛ %s" % ф(T, 2), 2.5, sc, "07_ОСИ", TA.MIDDLE_LEFT)
    # размеры
    def dim(y0, y1, z, txt):
        msp.add_line((y0 * K, z * K), (y1 * K, z * K), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        for yy in (y0, y1):
            msp.add_line((yy * K, (z - 0.08) * K), (yy * K, (z + 0.08) * K), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        ЧД.text(msp, (y0 + y1) / 2 * K, (z + 0.07) * K, txt, 2.5, sc, "09_РАЗМЕРЫ", TA.BOTTOM_CENTER)
    dim(0, b_pal, z_brt + 0.75, "полуширота %s" % ф(b_pal * 1000, 0))
    dim(0, b_dn, z_kil - 0.55, "плоское днище %s" % ф(b_dn * 1000, 0))
    for yy, z0, z1, txt in (((b_pal + 0.85), z_kil, z_brt, "H = %s" % ф(G.DEPTH * 1000, 0)), ((b_pal + 0.45), z_kil, DB, "двойное дно %s" % ф(DB * 1000, 0))):
        msp.add_line((yy * K, z0 * K), (yy * K, z1 * K), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        ЧД.text(msp, (yy + 0.08) * K, (z0 + z1) / 2 * K, txt, 2.5, sc, "09_РАЗМЕРЫ", TA.BOTTOM_CENTER, rot=90)

    def проф(имя):
        hw, tw, bf, tf = PR[имя]
        return "%d×%d" % (hw, tw) + ("/%d×%d" % (bf, tf) if bf else "")
    выноски = [
        ("Горизонтальный киль %s мм" % ф(PL["горизонтальный киль"], 0), 0.45, z_kil, -1.6, -0.95),
        ("Обшивка днища %s мм" % ф(PL["днище"], 1), 3.4, z_kil, 0.4, -1.30),
        ("Вертикальный киль %s" % проф("вертикальный киль"), 0.0, 0.62, -2.2, -0.35),
        ("Днищевые стрингеры %s" % проф("днищевой стрингер"), 2.75, 0.62, -2.5, 0.42),
        ("Рёбра днища %s, шаг %d" % (проф("ребро днища"), round(SP * 1000)), 4.4, 0.14, 0.2, -1.22),
        ("Настил второго дна %s мм" % ф(PL["второе дно"], 0), 6.4, DB, 2.0, 1.55),
        ("Рёбра второго дна %s" % проф("ребро второго дна"), 1.65, DB - 0.14, -3.1, 0.62),
        ("Скуловой пояс %s мм" % ф(PL["скула"], 1), (b_dn + b_sk) / 2, z_sk / 2, 3.4, -0.55),
        ("Обшивка борта %s мм, пояс ВЛ %s, ширстрек %s" % (ф(PL["борт ниже пояса"], 0), ф(PL["борт в районе ВЛ"], 1), ф(PL["ширстрек"], 0)), b_pal, 1.55, 2.5, -0.75),
        ("Шпангоут %s, шаг %d" % (проф("шпангоут"), round(SP * 1000)), b_pal - 0.12, 2.95, 2.7, -0.55),
        ("Бортовой стрингер %s" % проф("бортовой стрингер"), b_sk - 0.5, 2.60, -3.6, -0.15),
        ("Настил главной палубы %s мм" % ф(PL["настил главной палубы"], 0), 6.6, z_brt, 2.3, 0.72),
        ("Рёбра палубы %s, шаг %d" % (проф("ребро палубы"), round(SP * 1000)), 2.2, z_brt - 0.13, -3.6, 0.55),
        ("Карлингс %s" % проф("карлингс"), 4.10, z_brt - 0.60, -3.3, -0.62),
        ("Скуловая кница, лист %s мм" % ф(PL["скула"], 0), b_sk - 0.7, DB + 0.45, -3.9, 0.35),
        ("Палубная кница %s мм" % ф(PL["настил главной палубы"], 0), b_pal - 0.5, z_brt - 0.45, 2.6, -0.28),
    ]
    for txt, y, z, dy, dz in выноски:
        msp.add_line((y * K, z * K), ((y + dy) * K, (z + dz) * K), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        ЧД.text(msp, (y + dy) * K, (z + dz) * K, txt, 2.4, sc, "08_ТЕКСТ", TA.MIDDLE_LEFT if dy > 0 else TA.MIDDLE_RIGHT)
    # спецификация связей и результаты
    rows = [[n, ф(a, 0), ф(z, 2)] for n, a, z, i in g["elements"]]
    ЧД.text(msp, XT, 5.0 * K, "Спецификация связей эквивалентного бруса", 3.2, sc, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    yb = ЧД.table(msp, XT, 4.9 * K, sc, ["Связь", "A, см²", "z, м"], rows, [64, 18, 16], h_row=5.0)
    итоги = [["Площадь сечения A", ф(g["A"], 0) + " см²"], ["Нейтральная ось z0 от ОП", ф(g["z0"], 3) + " м"],
             ["Момент инерции I", ф(g["I_m4"], 3) + " м⁴"], ["W палубы / W днища", "%s / %s м³" % (ф(g["W_deck_m3"], 3), ф(g["W_bot_m3"], 3))]]
    for row in r["rows"]:
        итоги.append(["%s - M, σ палубы, σ днища" % row["condition"], "%s МН·м, %s, %s МПа - %s" % (ф(row["M"] / 1000.0, 1), ф(row["sigma_deck"], 0), ф(row["sigma_bot"], 0), "проходит" if row["ok"] else "НЕ ПРОХОДИТ")])
    итоги.append(["Допускаемое 0,6·ReH, сталь %s" % r["steel"]["name"], "%s МПа, использовано %s %%" % (ф(r["sigma_allow"], 0), ф(100 * max(x["sigma_deck"] for x in r["rows"]) / r["sigma_allow"], 0))])
    ЧД.text(msp, XT, yb - 7.0 * sc, "Результаты расчёта общей продольной прочности", 3.2, sc, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    ЧД.table(msp, XT, yb - 8.5 * sc, sc, ["Величина", "Значение"], итоги, [56, 60], h_row=5.0)
    notes = ("Мидель-шпангоут по шп. %d (x = %s м), правый борт, левый симметричен. Толщины и профили - по расчёту общей и местной прочности." % (round(X / S.SPACING), ф(X, 0)),
             "Система набора смешанная - продольная в днище, втором дне и палубе, поперечная по бортам, шпация %d мм, рамная %d мм." % (round(S.SPACING * 1000), round(S.FRAME_SPACING * 1000)),
             "Материал основных связей - сталь %s, ReH = %s МПа. Волна класса «%s» h = %s м." % (r["steel"]["name"], ф(r["steel"]["ReH"], 0), H.CLASS, ф(H.WAVE_HEIGHT[H.CLASS], 1)))
    ЧД.frame(msp, sheet, sc, bbox, "ВГ-2026 РТ-08 мидель-шпангоут", "Мидель-шпангоут конструктивный",
             "Волжский Горизонт · B = %s м · H = %s м · T = %s м" % (ф(G.BEAM, 1), ф(G.DEPTH, 2), ф(T, 2)), notes, "Сталь %s" % r["steel"]["name"])
    return save(doc, "ВГ-2026_РТ-08_мидель_шпангоут.dxf")


# --- РТ-09 схема набора ----------------------------------------------------------------------------
def rt09():
    SP, FS, DB = S.SPACING, S.FRAME_SPACING, S.DB_HEIGHT
    X0, X1 = 2.0, G.LOA - 3.0
    ER, ER_TOP = (12.0, 34.0), S.DB_HEIGHT_ER
    Z_SIDE = 11.0
    xs = [X0 + i * 0.5 for i in range(int((X1 - X0) / 0.5) + 1)]
    bbox = (-2.0 * K, -12.0 * K, (G.LOA + 4.0) * K, (Z_SIDE + G.DEPTH + 2.5) * K)
    sheet, sc = ЧД.pick_sheet(bbox[2] - bbox[0], bbox[3] - bbox[1])
    doc = newdoc(); msp = doc.modelspace()

    def sz(z):
        return (Z_SIDE + z) * K
    # бок
    ЧД.poly(msp, [(x * K, sz(H._station(x)[4])) for x in xs], "01_ОБШИВКА")
    msp.add_line((X0 * K, sz(G.DEPTH)), (X1 * K, sz(G.DEPTH)), dxfattribs={"layer": "02_ПАЛУБЫ"})
    msp.add_line((X0 * K, sz(DB)), (X1 * K, sz(DB)), dxfattribs={"layer": "02_ПАЛУБЫ"})
    msp.add_line((ER[0] * K, sz(ER_TOP)), (ER[1] * K, sz(ER_TOP)), dxfattribs={"layer": "02_ПАЛУБЫ"})
    for xe in ER:
        msp.add_line((xe * K, sz(ER_TOP)), (xe * K, sz(DB)), dxfattribs={"layer": "02_ПАЛУБЫ"})
    n = int((X1 - X0) / SP)
    for i in range(n + 1):
        x = X0 + i * SP
        if x > X1:
            break
        heavy = abs((x - X0) % FS) < 1e-6
        msp.add_line((x * K, sz(H._station(x)[4])), (x * K, sz(G.DEPTH)), dxfattribs={"layer": "10_НАБОР" if heavy else "21_СЕТКА"})
    msp.add_line((X0 * K, sz(2.60)), (X1 * K, sz(2.60)), dxfattribs={"layer": "10_НАБОР", "linetype": "DASHED"})
    for xb in H.BULKHEADS[1:-1]:
        msp.add_line((xb * K, sz(H._station(xb)[4]) - 0.1 * K), (xb * K, sz(G.DEPTH) + 0.35 * K), dxfattribs={"layer": "03_ПЕРЕБОРКИ"})
        ЧД.text(msp, xb * K, sz(G.DEPTH) + 0.5 * K, "%.0f" % xb, 2.6, sc, "03_ПЕРЕБОРКИ", TA.BOTTOM_CENTER)
    ЧД.text(msp, X0 * K, sz(G.DEPTH) + 1.4 * K, "БОК - водонепроницаемые переборки (красные), рамные шпангоуты через %d мм, холостые через %d мм" % (round(FS * 1000), round(SP * 1000)), 3.2, sc, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    ЧД.text(msp, X1 * K, sz(DB) + 0.12 * K, "второе дно %s" % ф(DB, 2), 2.4, sc, "02_ПАЛУБЫ", TA.BOTTOM_RIGHT)
    ЧД.text(msp, 23 * K, sz(ER_TOP) - 0.4 * K, "понижение второго дна в МО %s" % ф(ER_TOP, 2), 2.4, sc, "02_ПАЛУБЫ", TA.TOP_CENTER)
    ЧД.text(msp, X1 * K, sz(2.60) + 0.12 * K, "бортовой стрингер 2,60", 2.4, sc, "10_НАБОР", TA.BOTTOM_RIGHT)
    # днище (вид сверху): полуширота вверх и вниз от оси
    for i in range(n + 1):
        x = X0 + i * SP
        if x > X1:
            break
        heavy = abs((x - X0) % FS) < 1e-6
        b = H.half_breadth(x, DB if not (ER[0] <= x <= ER[1]) else ER_TOP)
        if b < 0.4:
            continue
        msp.add_line((x * K, -b * K), (x * K, b * K), dxfattribs={"layer": "10_НАБОР" if heavy else "21_СЕТКА"})
    for y in (0.0, 2.75, 5.50):
        xx = [x for x in xs if H._station(x)[0] > abs(y) + 0.35]
        if xx:
            for s_ in ((1,) if y == 0 else (1, -1)):
                msp.add_lwpolyline([(x * K, s_ * y * K) for x in xx], dxfattribs={"layer": "10_НАБОР"})
    for j in range(1, 13):
        y = j * SP
        if abs(y - 2.75) < 0.15 or abs(y - 5.50) < 0.15:
            continue
        xx = [x for x in xs if H._station(x)[0] > y + 0.35]
        if xx:
            for s_ in (1, -1):
                msp.add_lwpolyline([(x * K, s_ * y * K) for x in xx], dxfattribs={"layer": "21_СЕТКА"})
    for s_ in (1, -1):
        ЧД.poly(msp, [(x * K, s_ * H.half_breadth(x, G.DEPTH) * K) for x in xs], "01_ОБШИВКА")
    for xb in H.BULKHEADS[1:-1]:
        b = H.half_breadth(xb, 2.0)
        msp.add_line((xb * K, -b * K), (xb * K, b * K), dxfattribs={"layer": "03_ПЕРЕБОРКИ"})
    ЧД.text(msp, X0 * K, 9.4 * K, "ДНИЩЕ - продольные рёбра через %d мм, вертикальный киль и днищевые стрингеры на 2,75 и 5,50 м от ДП, флоры через %d мм" % (round(SP * 1000), round(FS * 1000)), 3.2, sc, "08_ТЕКСТ", TA.BOTTOM_LEFT)
    ЧД.text(msp, X1 * K, 0.18 * K, "вертикальный киль", 2.4, sc, "10_НАБОР", TA.BOTTOM_RIGHT)
    ЧД.text(msp, X1 * K, 2.93 * K, "днищевой стрингер", 2.4, sc, "10_НАБОР", TA.BOTTOM_RIGHT)
    ЧД.frames_ruler(msp, 0, G.LOA, -10.0 * K, sc)
    notes = ("Набор - шпация %d мм, рамная %d мм. Переборки - общие с ОР-04 и расчётом непотопляемости." % (round(SP * 1000), round(FS * 1000)),
             "Второе дно %s м, в машинном отделении (x = %s…%s) понижено до %s м." % (ф(DB, 2), ф(ER[0], 0), ф(ER[1], 0), ф(ER_TOP, 2)),
             "Профили набора - лист РТ-08. Толщины листов - там же и в таблице ОР-06.")
    ЧД.frame(msp, sheet, sc, bbox, "ВГ-2026 РТ-09 схема набора", "Схема набора корпуса - бок и днище",
             "Волжский Горизонт · L = %s м · B = %s м" % (ф(G.LOA, 1), ф(G.BEAM, 1)), notes, "Сталь D36 ГОСТ Р 52927")
    return save(doc, "ВГ-2026_РТ-09_схема_набора.dxf")


def main():
    print("листы РТ:")
    for f in (rt01, rt02, rt03, rt04, rt05, rt06, rt07, rt08, rt09):
        f()


if __name__ == "__main__":
    main()
