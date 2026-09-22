# -*- coding: utf-8 -*-
"""Комплект чертежей общего расположения в DXF (AutoCAD R2013), по листу на файл.

    python scripts/чертежи_dxf.py

Листы ОР-01…ОР-08: планы главной, средней и солнечной палуб, трюм и второе
дно с цистернами и механизмами, продольный разрез, поперечные сечения по
миделю и колёсам, шесть сечений по длине, теоретический чертёж. Единицы — миллиметры, судно вычерчено в натуральную
величину; рамка формата подобрана под масштаб из основной надписи, лист
печатается в этом масштабе 1:1.

Геометрия берётся из библиотек проекта: обводы — `gorizont_hydro`
(с нишами колёс), надстройка — `gorizont_super`, помещения и каюты —
`gorizont_ga`, цистерны и механизмы — `gorizont.TANKS` / `gorizont.ТРЮМ`,
набор — `gorizont_struct`. Чертёж и модель в Blender строятся из одних
функций, поэтому расходиться им негде.

DWG получается из этих DXF пакетно: `python scripts/чертежи_dwg.py`
(AutoCAD Core Console, формат 2018) → CAD/DWG/.
"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
from lib import gorizont as G, gorizont_hydro as H, gorizont_struct as S
from lib import gorizont_ga as GA, gorizont_super as SU, gorizont_wheel as W
from lib import gorizont_lines as L, gorizont_cabin_layout as ПК, gorizont_public as PB

OUT = os.path.join(ROOT, "CAD")
os.makedirs(OUT, exist_ok=True)
K = 1000.0                      # метры -> миллиметры
SHEETS = {"A1": (841, 594), "A0": (1189, 841), "A0x2": (1682, 1189)}
SCALES = [50, 75, 100, 150, 200, 250, 500]

LAYERS = [
    ("00_РАМКА",        7, "CONTINUOUS"),
    ("01_ОБШИВКА",      7, "CONTINUOUS"),
    ("02_ПАЛУБЫ",       4, "CONTINUOUS"),
    ("03_ПЕРЕБОРКИ",    1, "CONTINUOUS"),
    ("04_ЦИСТЕРНЫ",     3, "CONTINUOUS"),
    ("05_ОБОРУДОВАНИЕ", 5, "CONTINUOUS"),
    ("06_ПОМЕЩЕНИЯ",    8, "CONTINUOUS"),
    ("07_ОСИ",          2, "CENTER"),
    ("08_ТЕКСТ",        7, "CONTINUOUS"),
    ("09_РАЗМЕРЫ",      6, "CONTINUOUS"),
    ("10_НАБОР",        9, "CONTINUOUS"),
    ("11_КАЮТЫ",       30, "CONTINUOUS"),
    ("12_ТРАПЫ_ЛИФТЫ",  6, "CONTINUOUS"),
    ("13_КОЛЁСА",       1, "CONTINUOUS"),
    ("14_МЕБЕЛЬ",     252, "CONTINUOUS"),
]
КОД_КАЮТЫ = {"эконом": "Э", "стандарт": "С", "стандарт М4": "С·М4", "бизнес": "Б", "люкс": "Л",
             "семейная": "Сем", "экипаж 2": "Эк2", "экипаж 4": "Эк4"}
ЯРУС = {"главная": "главная", "средняя": "средняя", "солнечная": "средняя"}


# ------------------------------------------------------------- лист --------
def newdoc():
    doc = ezdxf.new("R2013", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    doc.header["$MEASUREMENT"] = 1
    for nm, col, lt in LAYERS:
        if nm not in doc.layers:
            doc.layers.add(name=nm, color=col, linetype=lt)
    if "ГОСТ" not in doc.styles:
        doc.styles.add("ГОСТ", font="ISOCPEUR.TTF")
    return doc


def pick_sheet(w_mm, h_mm):
    """Формат и масштаб, при которых содержимое влезает в поле чертежа."""
    for sh in ("A1", "A0", "A0x2"):
        Wd, Hd = SHEETS[sh]
        fw, fh = Wd - 45, Hd - 25
        for sc in SCALES:
            if w_mm / sc <= fw - 12 and h_mm / sc <= fh - 40:
                return sh, sc
    return "A0x2", 500


def frame(msp, sheet, scale, bbox, mark, title, subtitle, notes=(), material="—"):
    """Рамка ГОСТ 2.301 и основная надпись ГОСТ 2.104, форма 1."""
    Wd, Hd = SHEETS[sheet]
    Wd, Hd = Wd * scale, Hd * scale
    x0, y0, x1, y1 = bbox
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    ox, oy = cx - Wd / 2.0, cy - Hd / 2.0
    Ly = dict(layer="00_РАМКА")
    msp.add_lwpolyline([(ox, oy), (ox + Wd, oy), (ox + Wd, oy + Hd), (ox, oy + Hd)], close=True, dxfattribs=Ly)
    m_l, m = 20 * scale, 5 * scale
    msp.add_lwpolyline([(ox + m_l, oy + m), (ox + Wd - m, oy + m), (ox + Wd - m, oy + Hd - m), (ox + m_l, oy + Hd - m)],
                       close=True, dxfattribs=Ly)
    bw, bh = 185 * scale, 55 * scale
    bx, by = ox + Wd - m - bw, oy + m
    msp.add_lwpolyline([(bx, by), (bx + bw, by), (bx + bw, by + bh), (bx, by + bh)], close=True, dxfattribs=Ly)
    for dy in (12, 24, 36):
        msp.add_line((bx, by + dy * scale), (bx + bw, by + dy * scale), dxfattribs=Ly)
    msp.add_line((bx + 120 * scale, by), (bx + 120 * scale, by + 36 * scale), dxfattribs=Ly)

    def t(x, y, ss, h, al=TA.MIDDLE_LEFT):
        msp.add_text(ss, dxfattribs={"layer": "08_ТЕКСТ", "style": "ГОСТ", "height": h * scale}).set_placement((x, y), align=al)
    t(bx + 3 * scale, by + 45.5 * scale, title, 5.0)
    t(bx + 3 * scale, by + 30.0 * scale, subtitle, 2.5)
    t(bx + 3 * scale, by + 18.0 * scale, mark, 4.5)
    t(bx + 123 * scale, by + 18.0 * scale, "Масштаб 1 : %d" % scale, 3.5)
    t(bx + 3 * scale, by + 6.0 * scale, material, 2.5)
    t(bx + 123 * scale, by + 6.0 * scale, "Формат %s" % sheet.replace("x2", " x 2"), 3.0)
    t(bx + 3 * scale, by + bh + 4 * scale, "УЖЦ ОСК 2026 · «Волжский Горизонт» · ПБ «Без границ»", 3.0)
    ty0 = by + bh + 11 * scale
    if notes:
        n_last = len(notes)
        for i, n in enumerate(notes):
            t(bx + 3 * scale, ty0 + (n_last - 1 - i) * 5.0 * scale, "%d. %s" % (i + 1, n), 2.5)
        t(bx + 3 * scale, ty0 + n_last * 5.0 * scale + 1.5 * scale, "Технические требования", 3.5)
    return ox, oy, Wd, Hd


def table(msp, x, y, scale, head, rows, widths, h_row=6.0):
    """Таблица: x, y — левый верхний угол в модели (мм); widths — мм бумаги."""
    Wd = sum(widths) * scale
    hr = h_row * scale
    n = len(rows) + 1
    for i in range(n + 1):
        msp.add_line((x, y - i * hr), (x + Wd, y - i * hr), dxfattribs={"layer": "00_РАМКА"})
    cx = x
    for w in widths + [0]:
        msp.add_line((cx, y), (cx, y - n * hr), dxfattribs={"layer": "00_РАМКА"})
        cx += w * scale

    def cells(vals, yy, hgt):
        cx = x
        for v, w in zip(vals, widths):
            msp.add_text(str(v), dxfattribs={"layer": "08_ТЕКСТ", "style": "ГОСТ", "height": hgt * scale}
                         ).set_placement((cx + 1.5 * scale, yy), align=TA.MIDDLE_LEFT)
            cx += w * scale
    cells(head, y - hr / 2, 2.8)
    for i, r in enumerate(rows):
        cells(r, y - hr * (i + 1) - hr / 2, 2.5)
    return y - n * hr


def text(msp, x, y, s, h, scale, layer="08_ТЕКСТ", al=TA.MIDDLE_CENTER, rot=0.0):
    e = msp.add_text(s, dxfattribs={"layer": layer, "style": "ГОСТ", "height": h * scale, "rotation": rot})
    e.set_placement((x, y), align=al)
    return e


def poly(msp, pts, layer, close=False):
    if len(pts) > 1:
        msp.add_lwpolyline(pts, close=close, dxfattribs={"layer": layer})


def rect(msp, x0, y0, x1, y1, layer):
    poly(msp, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, close=True)


# ------------------------------------------------------------- обводы -------
def hull_outline(z, step=0.5):
    """Контур корпуса в плане на высоте z (с нишами колёс), мм."""
    xs, up = [], []
    x = 0.0
    while x <= G.LOA + 1e-6:
        b = H.half_breadth(x, z)
        if b > 0.01:
            xs.append(x); up.append(b)
        x += step
    if not xs:
        return []
    pts = [(xs[i] * K, up[i] * K) for i in range(len(xs))]
    pts += [(xs[i] * K, -up[i] * K) for i in range(len(xs) - 1, -1, -1)]
    return pts


def tier_outline(ярус, z):
    pts = [(x, SU.полуширота(x, ярус, z=z)) for x, _ in SU.обвод(ярус, шаг=0.5)]
    pts = [(x, y) for x, y in pts if y > 0.05]
    return [(x * K, y * K) for x, y in pts] + [(x * K, -y * K) for x, y in reversed(pts)]


def frames_ruler(msp, x0, x1, y, scale, every=20):
    """Разбивка по практическим шпангоутам: штрихи и номера через `every` шпаций."""
    n0 = int(math.ceil(x0 / S.SPACING)); n1 = int(x1 / S.SPACING)
    for n in range(n0, n1 + 1):
        if n % 5:
            continue
        x = n * S.SPACING * K
        big = (n % every == 0)
        msp.add_line((x, y), (x, y - (3.0 if big else 1.4) * scale), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        if big:
            text(msp, x, y - 7.0 * scale, str(n), 3.0, scale, "09_РАЗМЕРЫ", TA.MIDDLE_CENTER)
    msp.add_line((n0 * S.SPACING * K, y), (n1 * S.SPACING * K, y), dxfattribs={"layer": "09_РАЗМЕРЫ"})
    text(msp, x1 * K + 4.0 * K, y - 7.0 * scale, "№ шп., шпация %.0f" % (S.SPACING * 1000), 3.0, scale, "09_РАЗМЕРЫ", TA.MIDDLE_LEFT)


def wt_bulkheads(msp, z, scale, labels=True, y_label=None):
    """Водонепроницаемые переборки трюма — по gorizont_ga.ПЕРЕБОРКИ."""
    for xb in GA.ПЕРЕБОРКИ:
        bb = H.half_breadth(xb, z)
        if bb < 0.2:
            continue
        msp.add_line((xb * K, -bb * K), (xb * K, bb * K), dxfattribs={"layer": "03_ПЕРЕБОРКИ"})
        if labels:
            text(msp, xb * K, (y_label if y_label is not None else 11.4 * K), "%.0f" % xb, 2.8, scale, "03_ПЕРЕБОРКИ")


def wheels_plan(msp, scale, labels=True):
    """Колёса и ниши в плане: прямоугольник колеса, стенка ниши, ось."""
    к = SU.кожух()
    for s_ in (1, -1):
        rect(msp, (W.X_AXIS - W.DIAMETER / 2) * K, s_ * к["колесо_внутр"] * K,
             (W.X_AXIS + W.DIAMETER / 2) * K, s_ * к["колесо_наруж"] * K, "13_КОЛЁСА")
        msp.add_line((W.X_AXIS * K, s_ * к["колесо_внутр"] * K), (W.X_AXIS * K, s_ * (к["колесо_наруж"] + 0.4) * K),
                     dxfattribs={"layer": "07_ОСИ"})
        # стенка ниши — сходы по косинусу
        pts = []
        x = W.X_AXIS - W.NICHE_LEN / 2 - W.NICHE_FAIR
        while x <= W.X_AXIS + W.NICHE_LEN / 2 + W.NICHE_FAIR + 1e-6:
            pts.append((x * K, s_ * W.niche_half(x) * K))
            x += 0.25
        poly(msp, pts, "13_КОЛЁСА")
    if labels:
        text(msp, W.X_AXIS * K, (к["колесо_наруж"] + 1.1) * K, "гребное колесо D %.2f м, ось x = %.0f" % (W.DIAMETER, W.X_AXIS),
             2.8, scale, "13_КОЛЁСА")


def shafts(msp, палуба, scale):
    """Трап-холлы и лифты."""
    for имя, (a, b) in GA.ТРАПЫ.items():
        rect(msp, a * K, -1.6 * K, b * K, 1.6 * K, "12_ТРАПЫ_ЛИФТЫ")
        # марши — две ветви со стрелкой направления
        for s_ in (1, -1):
            rect(msp, (a + 0.2) * K, s_ * 0.1 * K, (b - 1.6) * K, s_ * 1.4 * K, "12_ТРАПЫ_ЛИФТЫ")
            for i in range(1, 8):
                xx = (a + 0.2 + (b - a - 1.8) * i / 8.0) * K
                msp.add_line((xx, s_ * 0.1 * K), (xx, s_ * 1.4 * K), dxfattribs={"layer": "12_ТРАПЫ_ЛИФТЫ"})
        text(msp, 0.5 * (a + b) * K, 0.0, "трап", 2.2, scale, "12_ТРАПЫ_ЛИФТЫ")
    for имя, (a, b, y0, y1) in GA.ЛИФТЫ.items():
        rect(msp, a * K, y0 * K, b * K, y1 * K, "12_ТРАПЫ_ЛИФТЫ")
        msp.add_line((a * K, y0 * K), (b * K, y1 * K), dxfattribs={"layer": "12_ТРАПЫ_ЛИФТЫ"})
        msp.add_line((a * K, y1 * K), (b * K, y0 * K), dxfattribs={"layer": "12_ТРАПЫ_ЛИФТЫ"})


def cabins(msp, палуба, scale, furniture=True):
    """Каюты по расстановке ГА с кодом типа; при крупном масштабе — с мебелью."""
    n = 0
    for c in GA.расстановка():
        if c["палуба"] != палуба:
            continue
        y0, y1 = sorted((c["y0"], c["y1"]))
        rect(msp, c["x0"] * K, y0 * K, c["x1"] * K, y1 * K, "11_КАЮТЫ")
        код = КОД_КАЮТЫ.get(c["тип"], c["тип"])
        text(msp, 0.5 * (c["x0"] + c["x1"]) * K, 0.5 * (y0 + y1) * K + 0.9 * scale, код, 2.4, scale, "11_КАЮТЫ")
        text(msp, 0.5 * (c["x0"] + c["x1"]) * K, 0.5 * (y0 + y1) * K - 2.0 * scale,
             "%.1f м² · %d" % (c["площадь"], c["мест"]), 1.8, scale, "11_КАЮТЫ")
        if furniture:
            тип = c["тип"] if c["тип"] in ("люкс", "бизнес", "стандарт", "стандарт М4", "семейная", "эконом") else "стандарт"
            ф, гл, м = ПК.мебель(тип)
            масштаб = min(1.0, (c["x1"] - c["x0"]) / ф)
            знак = 1 if c["борт"] == "ПБ" else -1
            a0, a1 = sorted((abs(c["y0"]), abs(c["y1"])))
            for имя, lx, ly, w, h, кл in м:
                x0 = c["x0"] + lx * масштаб; x1 = x0 + w * масштаб
                if c["ряд"] == "борт":
                    yy0, yy1 = a0 + ly, a0 + ly + h
                else:
                    yy0, yy1 = a1 - ly - h, a1 - ly
                if yy1 > a1 - 0.02 or x1 > c["x1"] - 0.02:
                    continue
                rect(msp, x0 * K, знак * yy0 * K, x1 * K, знак * yy1 * K, "14_МЕБЕЛЬ")
        n += 1
    return n


def zones(msp, палуба, z, scale, y_num):
    """Границы зон, номера в кружках и названия."""
    ярус = ЯРУС[палуба]
    rows = []
    for i, (x0, x1, kind, name, note) in enumerate(GA.ЗОНЫ[палуба], 1):
        for xb in (x0, x1):
            b = SU.полуширота(xb, ярус, z=z) if палуба != "трюм" else H.half_breadth(xb, z)
            b = max(b, H.half_breadth(xb, min(z, G.DEPTH - 0.01)) if палуба == "главная" and kind == "open" else 0.0)
            if b > 0.2:
                msp.add_line((xb * K, -b * K), (xb * K, b * K), dxfattribs={"layer": "06_ПОМЕЩЕНИЯ"})
        cx = 0.5 * (x0 + x1) * K
        r = 3.6 * scale
        msp.add_circle((cx, y_num), r, dxfattribs={"layer": "06_ПОМЕЩЕНИЯ"})
        text(msp, cx, y_num, str(i), 4.0, scale, "06_ПОМЕЩЕНИЯ")
        короткое = name.split(":")[0].split(",")[0]
        if (x1 - x0) * K / scale > len(короткое) * 1.6 + 4 and kind != "cabins":
            text(msp, cx, -0.2 * K, короткое, 2.8, scale, "06_ПОМЕЩЕНИЯ")
        s = GA.площадь_зоны(палуба, x0, x1)
        rows.append([i, name + ((" — " + note) if note else ""), "%.0f" % s,
                     "%d…%d" % (round(x0 / S.SPACING), round(x1 / S.SPACING)), "%.1f…%.1f" % (x0, x1)])
    return rows


def deck_plan(палуба, mark, title, extra=None):
    z = G.DECKS[палуба] + 1.2
    ярус = ЯРУС[палуба]
    zl = min(z, G.DEPTH - 0.01)
    ymax = 9.2 * K
    zrows = len(GA.ЗОНЫ[палуба]) + 1
    y_tab = -ymax - 14 * K
    bbox0 = (-2 * K, y_tab - zrows * 6.0 * 200 - 6 * K, (G.LOA + 6) * K, ymax + 9 * K)
    sheet, sc = pick_sheet(bbox0[2] - bbox0[0], bbox0[3] - bbox0[1])
    bbox = (-2 * K, y_tab - zrows * 6.0 * sc - 6 * K, (G.LOA + 6) * K, ymax + 9 * K)
    doc = newdoc(); msp = doc.modelspace()
    poly(msp, hull_outline(zl), "01_ОБШИВКА", close=True)
    if палуба == "солнечная":
        poly(msp, tier_outline("средняя", G.DECKS["солнечная"] - 0.05), "02_ПАЛУБЫ", close=True)
    else:
        poly(msp, tier_outline(ярус, z), "02_ПАЛУБЫ", close=True)
    msp.add_line((-2 * K, 0), ((G.LOA + 2) * K, 0), dxfattribs={"layer": "07_ОСИ"})
    rows = zones(msp, палуба, z, sc, ymax - 1.0 * K)
    n_cab = 0
    if палуба in ("главная", "средняя"):
        n_cab = cabins(msp, палуба, sc, furniture=(sc <= 100))
        shafts(msp, палуба, sc)
        # проёмы в переборках зон: разрыв линии переборки показан короткими штрихами
        for xb in sorted({z[0] for z in GA.ЗОНЫ[палуба]} | {z[1] for z in GA.ЗОНЫ[палуба]}):
            for y0, y1 in PB.проёмы_переборки(палуба, xb):
                msp.add_line(((xb - 0.3) * K, y0 * K), ((xb + 0.3) * K, y0 * K), dxfattribs={"layer": "06_ПОМЕЩЕНИЯ"})
                msp.add_line(((xb - 0.3) * K, y1 * K), ((xb + 0.3) * K, y1 * K), dxfattribs={"layer": "06_ПОМЕЩЕНИЯ"})
    # мебель и выгородки общественных помещений
    for p in PB.мебель(палуба):
        слой = "03_ПЕРЕБОРКИ" if p["класс"] in ("стена", "шахта") else "14_МЕБЕЛЬ"
        rect(msp, p["x0"] * K, p["y0"] * K, p["x1"] * K, p["y1"] * K, слой)
        # коридоры
        for c in GA.расстановка():
            pass
    if палуба == "главная":
        wheels_plan(msp, sc)
        г = G.GARAGE
        for i in range(г["places"]):
            cx = г["x0"] + 2.0 + (i % 2) * (г["vehicle_len"] + 1.2)
            cy = 2.8 if i < 2 else -2.8
            rect(msp, cx * K, (cy - г["vehicle_width"] / 2) * K, (cx + г["vehicle_len"]) * K, (cy + г["vehicle_width"] / 2) * K, "05_ОБОРУДОВАНИЕ")
        rect(msp, 0.0, -г["ramp_width"] / 2 * K, 0.4 * K, г["ramp_width"] / 2 * K, "05_ОБОРУДОВАНИЕ")
        text(msp, 1.6 * K, 0.0, "аппарель", 2.2, sc, "05_ОБОРУДОВАНИЕ", rot=90)
    if палуба == "средняя":
        # проём атриума в палубе
        X = W.X_AXIS
        rect(msp, (X + 1.0) * K, -3.4 * K, (X + 7.5) * K, 3.4 * K, "02_ПАЛУБЫ")
        text(msp, (X + 4.25) * K, 2.6 * K, "проём атриума", 2.2, sc, "02_ПАЛУБЫ")
        wheels_plan(msp, sc, labels=False)
    if палуба == "солнечная":
        р = SU.РУБКА
        rect(msp, р["x0"] * K, -р["полу"] * K, р["x1"] * K, р["полу"] * K, "02_ПАЛУБЫ")
        text(msp, 0.5 * (р["x0"] + р["x1"]) * K, 0.0, "рулевая рубка", 2.4, sc, "02_ПАЛУБЫ")
        X = W.X_AXIS
        rect(msp, (X - 8) * K, -5.5 * K, (X + 8) * K, 5.5 * K, "05_ОБОРУДОВАНИЕ")
        text(msp, X * K, 4.6 * K, "солнечные модули %.0f кВт на навесе h 2,6 м" % G.SOLAR_KW, 2.2, sc, "05_ОБОРУДОВАНИЕ")
        rect(msp, (X + 1) * K, -3.4 * K, (X + 7) * K, 3.4 * K, "02_ПАЛУБЫ")
        text(msp, (X + 4) * K, 0.0, "световой фонарь атриума", 2.0, sc, "02_ПАЛУБЫ")
        for имя in ("кормовой", "атриум"):
            a, b = GA.ТРАПЫ[имя]
            rect(msp, (a + 0.2) * K, -1.55 * K, (b - 0.2) * K, 1.55 * K, "12_ТРАПЫ_ЛИФТЫ")
            text(msp, 0.5 * (a + b) * K, 0.0, "трап", 2.2, sc, "12_ТРАПЫ_ЛИФТЫ")
        a, b, y0, y1 = GA.ЛИФТЫ["кормовой"]
        rect(msp, a * K, y0 * K, b * K, y1 * K, "12_ТРАПЫ_ЛИФТЫ")
        rect(msp, (X + 17.0 - 1.4) * K, -0.9 * K, (X + 17.0 + 1.4) * K, 0.9 * K, "05_ОБОРУДОВАНИЕ")
        text(msp, (X + 17.0) * K, 1.6 * K, "труба", 2.0, sc, "05_ОБОРУДОВАНИЕ")
    if extra:
        extra(msp, sc)
    frames_ruler(msp, 0, G.LOA, -ymax, sc)
    table(msp, 0.0, y_tab, sc, ["№", "Помещение", "Площадь, м²", "Шпангоуты", "x, м"], rows, [12, 200, 26, 26, 30])
    e = H.equilibrium()
    notes = ("Уровень палубы z = %.2f м от основной плоскости. Кают на палубе — %d." % (G.DECKS[палуба], n_cab),
             "Размеры в миллиметрах, ось x — от кормового перпендикуляра, шпация практическая %.0f мм." % (S.SPACING * 1000),
             "Красные линии — водонепроницаемые переборки трюма; тонкие — границы зон.",
             "Коридоры %.2f м в свету, бортовой проход главной палубы %.2f м, двери кают 0,70 (М4 — 0,90) м." % (GA.КОРИДОР, GA.ПРОХОД_БОРТОВОЙ),
             "Коды кают: Э эконом, С стандарт, Б бизнес, Л люкс, Сем семейная, Эк экипаж; М4 — доступная.")
    frame(msp, sheet, sc, bbox, mark, title,
          "Волжский Горизонт · L = %.1f м · B = %.1f м · T = %.2f м · %d пасс." % (G.LOA, G.BEAM, e["T"], GA.итоги()["пассажиров"]), notes,
          material="Корпус сталь D36; надстройка АМг5")
    path = os.path.join(OUT, mark.replace(" ", "_") + ".dxf")
    doc.saveas(path)
    return path


# ------------------------------------------------------------- трюм ---------
def hold_plan():
    z = 0.55
    ymax = 9.2 * K
    n_rows = len(G.TANKS) + len(G.ТРЮМ) + 2
    y_tab = -ymax - 9 * K
    bbox0 = (-2 * K, y_tab - n_rows * 5.0 * 200 - 6 * K, (G.LOA + 6) * K, ymax + 6 * K)
    sheet, sc = pick_sheet(bbox0[2] - bbox0[0], bbox0[3] - bbox0[1])
    bbox = (-2 * K, y_tab - n_rows * 5.0 * sc - 6 * K, (G.LOA + 6) * K, ymax + 6 * K)
    doc = newdoc(); msp = doc.modelspace()
    poly(msp, hull_outline(G.DEPTH - 0.01), "02_ПАЛУБЫ", close=True)
    poly(msp, hull_outline(z), "01_ОБШИВКА", close=True)
    msp.add_line((-2 * K, 0), ((G.LOA + 2) * K, 0), dxfattribs={"layer": "07_ОСИ"})
    for s_ in (1, -1):
        msp.add_line((26 * K, s_ * G.LONG_BULKHEAD_Y * K), (118 * K, s_ * G.LONG_BULKHEAD_Y * K), dxfattribs={"layer": "03_ПЕРЕБОРКИ"})
    # цистерны — по обшивке на z 0,5
    trows = []
    for i, t in enumerate(G.TANKS, 1):
        y0, y1 = t.get("y0", -G.LONG_BULKHEAD_Y), t.get("y1", G.LONG_BULKHEAD_Y)
        pts_u, pts_d = [], []
        x = t["x0"]
        while x <= t["x1"] + 1e-6:
            b = H.half_breadth(x, 0.5 * (t["z0"] + t["z1"])) - 0.05
            pts_u.append((x * K, min(y1, b) * K)); pts_d.append((x * K, max(y0, -b) * K))
            x = min(x + 0.5, t["x1"]) if x < t["x1"] else x + 1.0
        poly(msp, pts_u + pts_d[::-1], "04_ЦИСТЕРНЫ", close=True)
        cx = 0.5 * (t["x0"] + t["x1"]) * K
        cy = 0.5 * (max(y0, -7.0) + min(y1, 7.0)) * K
        text(msp, cx, cy + 0.9 * sc, t["code"], 2.6, sc, "04_ЦИСТЕРНЫ")
        text(msp, cx, cy - 1.8 * sc, "%.0f м³" % t["vol"], 2.0, sc, "04_ЦИСТЕРНЫ")
        trows.append([i, t["code"], t["name"], "%.1f…%.1f" % (t["x0"], t["x1"]), "%.1f…%.1f" % (y0, y1),
                      "%.2f…%.2f" % (t["z0"], t["z1"]), "%.0f" % t["vol"], "%.1f" % (t["vol"] * t["rho"])])
    # механизмы
    erows = []
    for j, (code, name, x0, x1, y0, y1, z0, z1, m) in enumerate(G.ТРЮМ, 1):
        rect(msp, x0 * K, y0 * K, x1 * K, y1 * K, "05_ОБОРУДОВАНИЕ")
        text(msp, 0.5 * (x0 + x1) * K, 0.5 * (y0 + y1) * K, code, 2.4, sc, "05_ОБОРУДОВАНИЕ")
        erows.append([len(G.TANKS) + j, code, name, "%.1f…%.1f" % (x0, x1), "%.1f…%.1f" % (y0, y1), "%.2f…%.2f" % (z0, z1), "—", "%.1f" % m])
    wheels_plan(msp, sc)
    wt_bulkheads(msp, z, sc, y_label=ymax - 1.0 * K)
    # названия отсеков
    for i, name in enumerate(H.COMPARTMENTS):
        x0, x1 = H.BULKHEADS[i], H.BULKHEADS[i + 1]
        if (x1 - x0) * K / sc > 24:
            text(msp, 0.5 * (x0 + x1) * K, ymax - 3.2 * K, name.split(",")[0].split(":")[0], 2.2, sc, "03_ПЕРЕБОРКИ")
    frames_ruler(msp, 0, G.LOA, -ymax, sc)
    ts = G.tank_summary()
    table(msp, 0.0, y_tab, sc, ["№", "Код", "Наименование", "x, м", "y, м", "z, м", "V, м³", "Масса, т"],
          trows + erows, [10, 16, 120, 26, 26, 24, 16, 18], h_row=5.0)
    notes = ("Второе дно z = 0…%.2f м; цистерны второго дна между продольными переборками y = ±%.2f м и обшивкой." % (G.DECKS["первая"], G.LONG_BULKHEAD_Y),
             "Метанол — в цистернах с коффердамами по торцам (1,0 м) и бортам; вентиляция и газоотвод в дымовую трубу.",
             "Всего %d цистерн, %.0f м³, масса содержимого при полном запасе %.0f т (балласт пустой)." % (len(G.TANKS), ts["vol"], ts["mass"]),
             "Машинное отделение %.0f…%.0f м вокруг колёс: три ГДГ по %d кВт, два ГЭД колёс по %d кВт с редукторами." % (62, 76, G.DG_POWER, G.WHEEL_MOTOR_POWER),
             "Красные линии — водонепроницаемые переборки (%d шт.), высота до главной палубы %.1f м." % (len(GA.ПЕРЕБОРКИ), G.DEPTH))
    frame(msp, sheet, sc, bbox, "ВГ-2026 ОР-04 трюм и второе дно", "Трюм и второе дно. План цистерн и механизмов",
          "Волжский Горизонт · %d цистерн · %.0f м³ · метанол %.0f м³" % (len(G.TANKS), ts["vol"], G.FUEL_METHANOL_M3), notes,
          material="Корпус сталь D36")
    p = os.path.join(OUT, "ВГ-2026_ОР-04_трюм_и_второе_дно.dxf")
    doc.saveas(p); return p


# ------------------------------------------------------------- разрез -------
def profile():
    step = 0.5
    keel, deck = [], []
    x = 0.0
    while x <= G.LOA + 1e-6:
        keel.append((x * K, H.keel_height(x) * K)); deck.append((x * K, H.side_height(x) * K))
        x += step
    e = H.equilibrium(); T = e["T"]
    ztop = G.WHEELHOUSE_ROOF + 0.5
    bbox0 = (-3 * K, -24 * K, (G.LOA + 34) * K, (ztop + 3) * K)
    sheet, sc = pick_sheet(bbox0[2] - bbox0[0], bbox0[3] - bbox0[1])
    doc = newdoc(); msp = doc.modelspace()
    poly(msp, keel, "01_ОБШИВКА"); poly(msp, deck, "01_ОБШИВКА")
    msp.add_line((0, keel[0][1]), (0, deck[0][1]), dxfattribs={"layer": "01_ОБШИВКА"})
    msp.add_line((G.LOA * K, keel[-1][1]), (G.LOA * K, deck[-1][1]), dxfattribs={"layer": "01_ОБШИВКА"})
    # палубы в корпусе
    for z, x0, x1 in ((G.DECKS["первая"], 2.0, 128.0), (G.DECKS["главная"], 0.0, G.LOA)):
        msp.add_line((x0 * K, z * K), (x1 * K, z * K), dxfattribs={"layer": "02_ПАЛУБЫ"})
    # ярусы с наклонными торцами
    for ярус, zt in (("главная", G.DECKS["средняя"]), ("средняя", G.DECKS["солнечная"])):
        я = SU.ЯРУСЫ[ярус]
        x0н, x1н = SU.границы_яруса(ярус, я["z0"]); x0в, x1в = SU.границы_яруса(ярус, я["z1"])
        poly(msp, [(x0н * K, я["z0"] * K), (x1н * K, я["z0"] * K), (x1в * K, я["z1"] * K), (x0в * K, я["z1"] * K)], "02_ПАЛУБЫ", close=True)
    р = SU.РУБКА
    poly(msp, [(р["x0"] * K, р["z0"] * K), (р["x1"] * K, р["z0"] * K), ((р["x1"] + 0.5) * K, р["z1"] * K), (р["x0"] * K, р["z1"] * K)], "02_ПАЛУБЫ", close=True)
    text(msp, 0.5 * (р["x0"] + р["x1"]) * K, 0.5 * (р["z0"] + р["z1"]) * K, "рубка, ход %.2f м" % G.WHEELHOUSE_LIFT, 2.4, sc, "02_ПАЛУБЫ")
    X = W.X_AXIS
    rect(msp, (X - 8) * K, (G.DECKS["солнечная"] + 2.6) * K, (X + 8) * K, (G.DECKS["солнечная"] + 2.68) * K, "05_ОБОРУДОВАНИЕ")
    text(msp, X * K, (G.DECKS["солнечная"] + 3.3) * K, "солнечный навес", 2.2, sc, "05_ОБОРУДОВАНИЕ")
    # колесо, кожух, ниша
    za = W.axis_height(T)
    msp.add_circle((X * K, za * K), W.DIAMETER / 2 * K, dxfattribs={"layer": "13_КОЛЁСА"})
    msp.add_circle((X * K, za * K), W.PIVOT_RADIUS * K, dxfattribs={"layer": "13_КОЛЁСА"})
    к = SU.кожух()
    rect(msp, к["x0"] * K, к["z0"] * K, к["x1"] * K, к["z1"] * K, "13_КОЛЁСА")
    msp.add_line(((X - W.NICHE_LEN / 2) * K, 0), ((X - W.NICHE_LEN / 2) * K, G.DEPTH * K), dxfattribs={"layer": "13_КОЛЁСА"})
    msp.add_line(((X + W.NICHE_LEN / 2) * K, 0), ((X + W.NICHE_LEN / 2) * K, G.DEPTH * K), dxfattribs={"layer": "13_КОЛЁСА"})
    text(msp, X * K, (к["z1"] + 0.5) * K, "колесо D %.2f, ось z = %.2f; ниша %.1f…%.1f м" % (W.DIAMETER, za, X - W.NICHE_LEN / 2, X + W.NICHE_LEN / 2), 2.4, sc, "13_КОЛЁСА")
    # трап-холлы и лифты
    for имя, (a, b) in GA.ТРАПЫ.items():
        rect(msp, a * K, G.DECKS["главная"] * K, b * K, G.DECKS["солнечная"] * K, "12_ТРАПЫ_ЛИФТЫ")
        text(msp, 0.5 * (a + b) * K, (G.DECKS["солнечная"] + 0.5) * K, "трап-холл", 2.2, sc, "12_ТРАПЫ_ЛИФТЫ")
    # переборки трюма
    for xb in GA.ПЕРЕБОРКИ:
        msp.add_line((xb * K, H.keel_height(xb) * K), (xb * K, G.DEPTH * K), dxfattribs={"layer": "03_ПЕРЕБОРКИ"})
        text(msp, xb * K, -1.1 * K, "%.0f" % xb, 2.6, sc, "03_ПЕРЕБОРКИ")
    # цистерны и механизмы трюма — контуры
    for t in G.TANKS:
        rect(msp, t["x0"] * K, t["z0"] * K, t["x1"] * K, t["z1"] * K, "04_ЦИСТЕРНЫ")
    for code, name, x0, x1, y0, y1, z0, z1, m in G.ТРЮМ:
        rect(msp, x0 * K, z0 * K, x1 * K, z1 * K, "05_ОБОРУДОВАНИЕ")
        if (x1 - x0) * K / sc > 8:
            text(msp, 0.5 * (x0 + x1) * K, 0.5 * (z0 + z1) * K, code, 1.8, sc, "05_ОБОРУДОВАНИЕ")
    # ватерлиния
    msp.add_line((-2 * K, T * K), ((G.LOA + 2) * K, T * K), dxfattribs={"layer": "07_ОСИ"})
    text(msp, (G.LOA + 1.5) * K, (T + 0.5) * K, "ВЛ %.2f м (Тк %.2f / Тн %.2f)" % (T, e["Ta"], e["Tf"]), 2.8, sc, "07_ОСИ", TA.MIDDLE_LEFT)
    # ярусы справа
    xr = (G.LOA + 9.0) * K
    tiers = [(0.0, G.DECKS["первая"], "второе дно, цистерны"), (G.DECKS["первая"], G.DECKS["главная"], "трюм: механизмы, приводы колёс"),
             (G.DECKS["главная"], G.DECKS["средняя"], "главная палуба: гараж, атриум, ресторан, театр, каюты"),
             (G.DECKS["средняя"], G.DECKS["солнечная"], "средняя палуба: каюты, атриум, спа"),
             (G.DECKS["солнечная"], G.WHEELHOUSE_ROOF, "солнечная палуба: навес, рубка")]
    for z0, z1, name in tiers:
        msp.add_line((xr, z0 * K), (xr, z1 * K), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        for z in (z0, z1):
            msp.add_line((xr - 0.6 * K, z * K), (xr + 0.6 * K, z * K), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        text(msp, xr + 1.0 * K, 0.5 * (z0 + z1) * K, "%.2f…%.2f  %s" % (z0, z1, name), 2.6, sc, "09_РАЗМЕРЫ", TA.MIDDLE_LEFT)
    frames_ruler(msp, 0, G.LOA, -2.2 * K, sc)
    trows = []
    for палуба in ("главная", "средняя", "солнечная"):
        for x0, x1, kind, name, note in GA.ЗОНЫ[палуба]:
            trows.append([палуба, "%.0f…%.0f" % (x0, x1), name[:70]])
    table(msp, 0.0, -6.0 * K, sc, ["Палуба", "x, м", "Помещения"], trows, [30, 26, 190], h_row=5.0)
    notes = ("Продольный разрез по ДП. Высоты от основной плоскости, м.",
             "Габаритная высота от ВЛ %.2f м, рубка стационарная; самый низкий мост маршрута %.1f м." % (G.AIR_DRAFT, G.BRIDGE_MIN),
             "Красные линии — водонепроницаемые переборки трюма (%d шт.)." % len(GA.ПЕРЕБОРКИ),
             "Колёса на миделе в бортовых нишах, ось x = %.0f м; кожух в объёме первого яруса, над ним атриум." % X)
    frame(msp, sheet, sc, bbox0, "ВГ-2026 ОР-05 продольный разрез", "Продольный разрез. Обозначение ярусов",
          "Волжский Горизонт · L = %.1f м · H = %.1f м · T = %.2f м" % (G.LOA, G.DEPTH, T), notes,
          material="Корпус сталь D36; надстройка АМг5")
    p = os.path.join(OUT, "ВГ-2026_ОР-05_продольный_разрез.dxf")
    doc.saveas(p); return p


# ------------------------------------------------------------- сечения ------
def _section_view(msp, x, dx, sc, T, label):
    """Половина сечения корпуса и надстройки на абсциссе x, смещённая по dx (мм)."""
    pts = [(y * K + dx, z * K) for z, y in H.profile(x)]
    for s_ in (1, -1):
        poly(msp, [((p[0] - dx) * s_ + dx, p[1]) for p in pts], "01_ОБШИВКА")
    # днище по ДП
    msp.add_line((dx, H.keel_height(x) * K), (dx + 0.0, H.keel_height(x) * K), dxfattribs={"layer": "01_ОБШИВКА"})
    # ярусы
    for ярус in ("главная", "средняя"):
        я = SU.ЯРУСЫ[ярус]
        проф = SU.профиль(ярус)
        side = [(SU.полуширота(x, ярус, z=z) + dy, z) for dy, z in проф]
        side = [(y, z) for y, z in side if y > 0.06]
        for s_ in (1, -1):
            poly(msp, [(s_ * y * K + dx, z * K) for y, z in side], "02_ПАЛУБЫ")
        for z in (я["z0"], я["z1"]):
            b = SU.полуширота(x, ярус, z=z)
            if b > 0.06:
                msp.add_line((-b * K + dx, z * K), (b * K + dx, z * K), dxfattribs={"layer": "02_ПАЛУБЫ"})
    for z, lab in ((G.DECKS["первая"], "второе дно %.2f" % G.DECKS["первая"]), (G.DECKS["главная"], "главная палуба %.2f" % G.DECKS["главная"]),
                   (G.DECKS["средняя"], "средняя палуба %.2f" % G.DECKS["средняя"]), (G.DECKS["солнечная"], "солнечная палуба %.2f" % G.DECKS["солнечная"])):
        b = H.half_breadth(x, min(z, G.DEPTH - 0.01)) if z <= G.DEPTH else SU.полуширота(x, "средняя" if z > G.DECKS["средняя"] else "главная", z=z - 0.01)
        if z <= G.DEPTH:
            msp.add_line((-b * K + dx, z * K), (b * K + dx, z * K), dxfattribs={"layer": "02_ПАЛУБЫ"})
        text(msp, (b + 0.5) * K + dx, (z + 0.3) * K, lab, 2.6, sc, "02_ПАЛУБЫ", TA.MIDDLE_LEFT)
    msp.add_line((-9.5 * K + dx, T * K), (9.5 * K + dx, T * K), dxfattribs={"layer": "07_ОСИ"})
    text(msp, 9.7 * K + dx, (T + 0.3) * K, "ВЛ T = %.2f" % T, 2.6, sc, "07_ОСИ", TA.MIDDLE_LEFT)
    msp.add_line((dx, -0.8 * K), (dx, (G.WHEELHOUSE_ROOF + 1.0) * K), dxfattribs={"layer": "07_ОСИ"})
    text(msp, dx, -1.6 * K, label, 3.2, sc, "09_РАЗМЕРЫ")


def sections():
    T = H.equilibrium()["T"]
    plates = list(S.PLATES.items())
    profs = [(k, "%d x %d" % (v[0], v[1]) + (" + %d x %d" % (v[2], v[3]) if v[2] else "")) for k, v in S.PROFILES.items()]
    n_rows = max(len(plates), len(profs)) + 1
    y_tab = -3.5 * K
    bbox0 = (-14 * K, y_tab - n_rows * 5.5 * 50 - 6 * K, 40 * K, 13.0 * K)
    sheet, sc = pick_sheet(bbox0[2] - bbox0[0], bbox0[3] - bbox0[1])
    bbox = (-14 * K, y_tab - n_rows * 5.5 * sc - 6 * K, 40 * K, 13.0 * K)
    doc = newdoc(); msp = doc.modelspace()
    xm = S.X_MID
    _section_view(msp, xm, 0.0, sc, T, "Сечение А-А, шп. %d (x = %.0f м), полная ширина" % (round(xm / S.SPACING), xm))
    # сечение по оси колеса
    dx = 26.0 * K
    X = W.X_AXIS
    _section_view(msp, X, dx, sc, T, "Сечение Б-Б, по оси колёс (x = %.0f м)" % X)
    к = SU.кожух(); za = W.axis_height(T)
    for s_ in (1, -1):
        rect(msp, s_ * к["колесо_внутр"] * K + dx, (za - W.DIAMETER / 2) * K, s_ * к["колесо_наруж"] * K + dx, (za + W.DIAMETER / 2) * K, "13_КОЛЁСА")
        msp.add_line((s_ * к["колесо_внутр"] * K + dx, za * K), (s_ * к["колесо_наруж"] * K + dx, za * K), dxfattribs={"layer": "07_ОСИ"})
        rect(msp, s_ * к["y_внутр"] * K + dx, к["z0"] * K, s_ * к["y_наруж"] * K + dx, к["z1"] * K, "13_КОЛЁСА")
    text(msp, dx, (za + W.DIAMETER / 2 + 0.6) * K, "колёса D %.2f × %.2f м в нишах, кожухи до z %.2f" % (W.DIAMETER, W.WIDTH, к["z1"]), 2.4, sc, "13_КОЛЁСА")
    # набор днища на сечении А-А
    msp.add_line((0, 0), (0, G.DECKS["первая"] * K), dxfattribs={"layer": "10_НАБОР"})
    b_dn = H._station(xm)[0]
    n = int((b_dn - 0.3) / 1.10)
    for i in range(1, n + 1):
        for s_ in (1, -1):
            msp.add_line((s_ * i * 1.10 * K, 0), (s_ * i * 1.10 * K, G.DECKS["первая"] * K), dxfattribs={"layer": "10_НАБОР"})
    eg = S.equivalent_girder()
    rows = []
    for i in range(n_rows - 1):
        pl = (plates[i][0], "%.0f" % plates[i][1]) if i < len(plates) else ("", "")
        pr = profs[i] if i < len(profs) else ("", "")
        rows.append([i + 1, pl[0], pl[1], pr[0], pr[1]])
    table(msp, -13.0 * K, y_tab, sc, ["№", "Лист обшивки и настила", "t, мм", "Профиль набора", "h x t + b x t, мм"], rows, [10, 76, 18, 60, 52], h_row=5.5)
    text(msp, 0, -2.6 * K, "B = %.0f   H = %.0f   T = %.0f" % (G.BEAM * 1000, G.DEPTH * 1000, T * 1000), 3.0, sc, "09_РАЗМЕРЫ")
    notes = ("Смешанная система набора: продольная в днище, втором дне и главной палубе, поперечная по бортам.",
             "Шпация %.0f мм, рамная %.0f мм. Корпус — сталь D36 (%s), надстройка — АМг5." % (S.SPACING * 1000, S.FRAME_SPACING * 1000, "ГОСТ Р 52927"),
             "Эквивалентный брус (сечение А-А): A = %.0f см², z0 = %.2f м, I = %.3f м⁴, W палубы %.3f м³, W днища %.3f м³." % (eg["A"], eg["z0"], eg["I_m4"], eg["W_deck_m3"], eg["W_bot_m3"]),
             "В сечении Б-Б борт вырезан нишей колеса от киля до главной палубы; момент передают переборки ниш и настилы.")
    frame(msp, sheet, sc, bbox, "ВГ-2026 ОР-06 поперечные сечения", "Поперечные сечения: по шп. %d и по оси колёс" % round(xm / S.SPACING),
          "Волжский Горизонт · B = %.1f м · H = %.1f м · T = %.2f м" % (G.BEAM, G.DEPTH, T), notes, material="Сталь D36 ГОСТ Р 52927")
    p = os.path.join(OUT, "ВГ-2026_ОР-06_поперечные_сечения.dxf")
    doc.saveas(p); return p


# ------------------------------------------------------------- сечения по длине
СЕЧЕНИЯ_ПО_ДЛИНЕ = (10.0, 30.0, 50.0, 85.0, 105.0, 125.0)


def _помещения_на_сечении(x):
    """Что стоит на абсциссе x по каждому уровню: зона и каюты (для подписей сечения)."""
    out = []
    for палуба in ("трюм", "главная", "средняя", "солнечная"):
        имя = next((z[3] for z in GA.ЗОНЫ[палуба] if z[0] <= x < z[1]), "")
        каюты = sorted({"%s %s" % (c["тип"], c["ряд"]) for c in GA.расстановка()
                        if c["палуба"] == палуба and c["x0"] <= x < c["x1"]})
        out.append((палуба, имя, каюты))
    return out


def sections_along():
    """ОР-08: шесть поперечных сечений по длине судна — корма, гараж, каюты,
    ресторан и МО, театр и люксы, носовой салон. На каждом — обвод корпуса с
    нишей, ярусы, палубы, ватерлиния, состав помещений по уровням."""
    T = H.equilibrium()["T"]
    doc = newdoc(); msp = doc.modelspace()
    шаг_x, шаг_z = 24.0 * K, -17.0 * K
    bbox = (-12 * K, шаг_z - 4 * K, 2 * шаг_x + 12 * K, 16 * K)
    sheet, sc = pick_sheet(bbox[2] - bbox[0], bbox[3] - bbox[1])
    for i, x in enumerate(СЕЧЕНИЯ_ПО_ДЛИНЕ):
        dx = (i % 3) * шаг_x
        dz = (i // 3) * шаг_z
        # смещение по z: рисуем в локальной системе и переносим блоком строк
        base = len(msp)
        _section_view(msp, x, dx, sc, T, "Сечение %d-%d, шп. %d (x = %.0f м)" % (i + 1, i + 1, round(x / S.SPACING), x))
        if W.X_AXIS - W.NICHE_LEN / 2.0 - W.NICHE_FAIR <= x <= W.X_AXIS + W.NICHE_LEN / 2.0 + W.NICHE_FAIR:
            к = SU.кожух(); za = W.axis_height(T)
            for s_ in (1, -1):
                rect(msp, s_ * к["колесо_внутр"] * K + dx, (za - W.DIAMETER / 2) * K, s_ * к["колесо_наруж"] * K + dx, (za + W.DIAMETER / 2) * K, "13_КОЛЁСА")
        # состав помещений слева от сечения
        y_txt = 12.4 * K
        for палуба, имя, каюты in reversed(_помещения_на_сечении(x)):
            стр = "%s: %s" % (палуба, имя[:60]) if имя else "%s: —" % палуба
            text(msp, -9.8 * K + dx, y_txt, стр, 2.4, sc, "06_ПОМЕЩЕНИЯ", TA.MIDDLE_LEFT)
            y_txt -= 1.1 * K
            if каюты:
                text(msp, -9.2 * K + dx, y_txt, "каюты: " + ", ".join(каюты)[:70], 2.0, sc, "06_ПОМЕЩЕНИЯ", TA.MIDDLE_LEFT)
                y_txt -= 1.0 * K
        # перенос второго ряда сечений вниз
        if dz:
            for e in list(msp)[base:]:
                try:
                    e.translate(0, dz, 0)
                except Exception:
                    pass
    notes = ("Сечения по длине корпуса: положение по шпангоутам и по x от кормового перпендикуляра.",
             "На каждом сечении: обвод корпуса (в районе колёс — с нишей), ярусы надстройки, уровни палуб, ватерлиния T = %.2f м." % T,
             "Состав помещений по уровням — из компоновки gorizont_ga; каюты — по расстановке рядов.",
             "Сечения по миделю и по оси колёс с набором и таблицей связей — лист ОР-06.")
    frame(msp, sheet, sc, bbox, "ВГ-2026 ОР-08 сечения по длине", "Поперечные сечения по длине судна: %s" % ", ".join("x = %.0f" % x for x in СЕЧЕНИЯ_ПО_ДЛИНЕ),
          "Волжский Горизонт · L = %.1f м · B = %.1f м · T = %.2f м" % (G.LOA, G.BEAM, T), notes, material="Сталь D36 ГОСТ Р 52927")
    p = os.path.join(OUT, "ВГ-2026_ОР-08_сечения_по_длине.dxf")
    doc.saveas(p); return p


# ------------------------------------------------------------- теоретический
def lines_plan():
    T = H.equilibrium()["T"]
    dz_bok = 12.0          # бок над полуширотой
    bbox0 = (-4 * K, -10 * K, (G.LOA + 30) * K, (dz_bok + G.WHEELHOUSE_ROOF + 2) * K)
    sheet, sc = pick_sheet(bbox0[2] - bbox0[0], bbox0[3] - bbox0[1])
    doc = newdoc(); msp = doc.modelspace()
    # --- бок: киль, палуба, батоксы
    keel, deck = [], []
    x = 0.0
    while x <= G.LOA + 1e-6:
        keel.append((x * K, (H.keel_height(x) + dz_bok) * K)); deck.append((x * K, (H.side_height(x) + dz_bok) * K))
        x += 0.5
    poly(msp, keel, "01_ОБШИВКА"); poly(msp, deck, "01_ОБШИВКА")
    msp.add_line((0, keel[0][1]), (0, deck[0][1]), dxfattribs={"layer": "01_ОБШИВКА"})
    msp.add_line((G.LOA * K, keel[-1][1]), (G.LOA * K, deck[-1][1]), dxfattribs={"layer": "01_ОБШИВКА"})
    for yb in (1.0, 2.0, 3.0, 4.0, 5.0, 6.0, 7.0):
        pts = []
        x = 0.0
        while x <= G.LOA + 1e-6:
            # z, на котором полуширота равна yb: перебор по высоте
            zz = None
            z = H.keel_height(x)
            while z <= G.DEPTH + 1e-6:
                if H.half_breadth(x, z) >= yb:
                    zz = z; break
                z += 0.02
            if zz is not None:
                pts.append((x * K, (zz + dz_bok) * K))
            elif pts:
                poly(msp, pts, "07_ОСИ"); pts = []
            x += 0.5
        poly(msp, pts, "07_ОСИ")
        text(msp, 2.0 * K, (dz_bok + G.DEPTH + 0.4) * K, "батоксы через 1 м", 2.4, sc, "09_РАЗМЕРЫ", TA.MIDDLE_LEFT)
    msp.add_line((-1 * K, (T + dz_bok) * K), ((G.LOA + 1) * K, (T + dz_bok) * K), dxfattribs={"layer": "07_ОСИ"})
    text(msp, (G.LOA + 1.5) * K, (T + dz_bok) * K, "КВЛ %.2f" % T, 2.6, sc, "07_ОСИ", TA.MIDDLE_LEFT)
    # надстройка на боку — тонко
    for ярус in ("главная", "средняя"):
        я = SU.ЯРУСЫ[ярус]
        x0н, x1н = SU.границы_яруса(ярус, я["z0"]); x0в, x1в = SU.границы_яруса(ярус, я["z1"])
        poly(msp, [(x0н * K, (я["z0"] + dz_bok) * K), (x1н * K, (я["z0"] + dz_bok) * K), (x1в * K, (я["z1"] + dz_bok) * K), (x0в * K, (я["z1"] + dz_bok) * K)], "02_ПАЛУБЫ", close=True)
    msp.add_circle((W.X_AXIS * K, (W.axis_height(T) + dz_bok) * K), W.DIAMETER / 2 * K, dxfattribs={"layer": "13_КОЛЁСА"})
    # --- полуширота: ватерлинии
    for z in list(G.WATERLINES) + [T]:
        pts = []
        x = 0.0
        while x <= G.LOA + 1e-6:
            b = H.half_breadth(x, z)
            if b > 0.005:
                pts.append((x * K, b * K))
            x += 0.5
        if len(pts) > 2:
            poly(msp, pts, "01_ОБШИВКА" if abs(z - T) > 1e-6 else "07_ОСИ")
            text(msp, pts[-1][0] + 0.3 * K, pts[-1][1], "ВЛ %.2f" % z, 1.8, sc, "09_РАЗМЕРЫ", TA.MIDDLE_LEFT)
    msp.add_line((0, 0), (G.LOA * K, 0), dxfattribs={"layer": "07_ОСИ"})
    # теоретические шпангоуты
    for n, x in L.stations():
        msp.add_line((x * K, -0.6 * K), (x * K, (G.BEAM / 2 + 0.6) * K), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        msp.add_line((x * K, (dz_bok - 0.6) * K), (x * K, (dz_bok + G.DEPTH + 0.6) * K), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        text(msp, x * K, -1.4 * K, "%g" % n, 2.4, sc, "09_РАЗМЕРЫ")
    # --- корпус: шпангоуты, справа от полушироты
    dx = (G.LOA + 16.0) * K
    for n, x in L.stations():
        pts = [(y, z) for z, y in H.profile(x)]
        s_ = -1 if x < G.LOA / 2 else 1     # кормовые слева от ДП, носовые справа
        poly(msp, [(s_ * y * K + dx, z * K) for y, z in pts], "01_ОБШИВКА")
    msp.add_line((dx, -0.5 * K), (dx, (G.DEPTH + 1.0) * K), dxfattribs={"layer": "07_ОСИ"})
    msp.add_line((dx - 9 * K, 0), (dx + 9 * K, 0), dxfattribs={"layer": "07_ОСИ"})
    msp.add_line((dx - 9 * K, T * K), (dx + 9 * K, T * K), dxfattribs={"layer": "07_ОСИ"})
    text(msp, dx, (G.DEPTH + 1.5) * K, "корпус: кормовые шпангоуты слева, носовые справа", 2.6, sc, "09_РАЗМЕРЫ")
    frames_ruler(msp, 0, G.LOA, -3.0 * K, sc)
    h = H.hydrostatics(T)
    notes = ("Теоретический чертёж: бок (поднят на %.0f м), полуширота, корпус. Ординаты — по gorizont_lines/gorizont_hydro с нишами колёс." % dz_bok,
             "L = %.1f, B = %.1f, H = %.2f, T = %.2f м; δ = %.3f, α = %.3f, β = %.3f; V = %.0f м³." % (G.LOA, G.BEAM, G.DEPTH, T, h["delta"], h["alpha"], h["beta"], h["V"]),
             "20 теоретических шпангоутов через L/20 = %.2f м и полушпангоуты в оконечностях; ватерлинии по плазовой таблице." % (G.LOA / 20),
             "Обвод: плоское днище, скуловая дуга, прямой борт с развалом; ниши колёс %.1f…%.1f м от киля до палубы." % (W.X_AXIS - W.NICHE_LEN / 2, W.X_AXIS + W.NICHE_LEN / 2))
    frame(msp, sheet, sc, bbox0, "ВГ-2026 ОР-07 теоретический чертёж", "Теоретический чертёж",
          "Волжский Горизонт · L = %.1f · B = %.1f · H = %.1f · T = %.2f" % (G.LOA, G.BEAM, G.DEPTH, T), notes)
    p = os.path.join(OUT, "ВГ-2026_ОР-07_теоретический_чертёж.dxf")
    doc.saveas(p); return p


def main():
    made = []
    made.append(deck_plan("главная", "ВГ-2026 ОР-01 главная палуба", "Общее расположение. Главная палуба"))
    made.append(deck_plan("средняя", "ВГ-2026 ОР-02 средняя палуба", "Общее расположение. Средняя палуба"))
    made.append(deck_plan("солнечная", "ВГ-2026 ОР-03 солнечная палуба", "Общее расположение. Солнечная палуба"))
    made.append(hold_plan())
    made.append(profile())
    made.append(sections())
    made.append(sections_along())
    made.append(lines_plan())
    for p in made:
        print(os.path.basename(p), os.path.getsize(p) // 1024, "КБ")
    return made


if __name__ == "__main__":
    main()
