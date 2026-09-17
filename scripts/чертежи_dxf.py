# -*- coding: utf-8 -*-
"""Комплект чертежей корпуса в DXF (AutoCAD R2013), отдельными файлами.

Яруса, поперечное сечение, продольный разрез, второе дно с цистернами,
машинное отделение и теоретический чертёж. Единицы — миллиметры, судно
вычерчено в натуральную величину, рамка формата подобрана под масштаб,
указанный в основной надписи: лист печатается в этом масштабе 1:1.

DWG напрямую не пишется ни одной свободной библиотекой; DXF R2013
открывается AutoCAD как родной формат и сохраняется в .dwg одной командой
СОХРАНИТЬ КАК.
"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
from lib import gorizont as G, gorizont_hydro as H, gorizont_struct as S
from lib import gorizont_mach as M, gorizont_ga as GA

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
    ("12_ТРАПЫ_ЛИФТЫ", 6, "CONTINUOUS"),
]

_MODEL = None


def model():
    """Габариты объектов из blender/gorizont.blend (экспорт gorizont_model.json)."""
    global _MODEL
    if _MODEL is None:
        import json
        with open(os.path.join(ROOT, "src", "lib", "gorizont_model.json"),
                  encoding="utf-8") as f:
            _MODEL = json.load(f)
    return _MODEL


CAB_SHORT = {"эконом": "Э", "стандарт": "С", "бизнес": "Б", "люкс": "Л",
             "экипаж_1": "Эк1", "экипаж_2": "Эк2"}


def draw_cabins(msp, level, scale):
    n = 0
    for name, b in sorted(model().get("10_Каюты", {}).items()):
        if abs(b[2] - level) > 0.30:
            continue
        rect(msp, b[0] * K, b[1] * K, b[3] * K, b[4] * K, "11_КАЮТЫ")
        t = "".join(CAB_SHORT.get(k, "") for k in CAB_SHORT if ("_" + k) in name)
        if "дост" in name:
            t += "·МГН"
        if t and (b[3] - b[0]) * K / scale > 8:
            text(msp, 0.5 * (b[0] + b[3]) * K, 0.5 * (b[1] + b[4]) * K, t,
                 2.6, scale, "11_КАЮТЫ")
        n += 1
    return n


def draw_shafts(msp, level, scale):
    for name, b in sorted(model().get("11_Трапы_и_лифты", {}).items()):
        if not (name.startswith("лифт_") or name.startswith("трап_")):
            continue
        if b[2] > level + 0.2 or b[5] < level + 1.0:
            continue
        if (b[3] - b[0]) < 0.6 or (b[4] - b[1]) < 0.6:
            continue
        rect(msp, b[0] * K, b[1] * K, b[3] * K, b[4] * K, "12_ТРАПЫ_ЛИФТЫ")


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
    """Подобрать формат и масштаб так, чтобы содержимое влезло в поле чертежа."""
    for sh in ("A1", "A0", "A0x2"):
        W, H = SHEETS[sh]
        fw, fh = W - 45, H - 25          # поле внутри рамки
        for sc in SCALES:
            if w_mm / sc <= fw - 12 and h_mm / sc <= fh - 40:
                return sh, sc
    return "A0x2", 500


def frame(msp, sheet, scale, bbox, mark, title, subtitle, notes=()):
    """Рамка ГОСТ 2.301 и основная надпись ГОСТ 2.104, форма 1."""
    W, H = SHEETS[sheet]
    W, H = W * scale, H * scale
    x0, y0, x1, y1 = bbox
    cx, cy = 0.5 * (x0 + x1), 0.5 * (y0 + y1)
    ox, oy = cx - W / 2.0, cy - H / 2.0
    L = dict(layer="00_РАМКА")
    msp.add_lwpolyline([(ox, oy), (ox + W, oy), (ox + W, oy + H), (ox, oy + H)],
                       close=True, dxfattribs=L)
    m_l, m = 20 * scale, 5 * scale
    msp.add_lwpolyline([(ox + m_l, oy + m), (ox + W - m, oy + m),
                        (ox + W - m, oy + H - m), (ox + m_l, oy + H - m)],
                       close=True, dxfattribs=L)
    bw, bh = 185 * scale, 55 * scale
    bx, by = ox + W - m - bw, oy + m
    msp.add_lwpolyline([(bx, by), (bx + bw, by), (bx + bw, by + bh), (bx, by + bh)],
                       close=True, dxfattribs=L)
    for dy in (12, 24, 36):
        msp.add_line((bx, by + dy * scale), (bx + bw, by + dy * scale), dxfattribs=L)
    msp.add_line((bx + 120 * scale, by), (bx + 120 * scale, by + 36 * scale), dxfattribs=L)

    def t(x, y, ss, h, al=TA.MIDDLE_LEFT):
        msp.add_text(ss, dxfattribs={"layer": "08_ТЕКСТ", "style": "ГОСТ",
                                     "height": h * scale}).set_placement((x, y), align=al)
    t(bx + 3 * scale, by + 45.5 * scale, title, 5.0)
    t(bx + 3 * scale, by + 30.0 * scale, subtitle, 2.5)
    t(bx + 3 * scale, by + 18.0 * scale, mark, 4.5)
    t(bx + 123 * scale, by + 18.0 * scale, "Масштаб 1 : %d" % scale, 3.5)
    t(bx + 3 * scale, by + 6.0 * scale, "Сталь 09Г2С ГОСТ 19281-2014", 2.5)
    t(bx + 123 * scale, by + 6.0 * scale, "Формат %s" % sheet.replace("x2", " x 2"), 3.0)
    t(bx + 3 * scale, by + bh + 4 * scale, "УЖЦ ОСК 2026 · «Волжский Горизонт»", 3.0)
    ty0 = by + bh + 11 * scale
    if notes:
        n_last = len(notes)
        for i, n in enumerate(notes):
            t(bx + 3 * scale, ty0 + (n_last - 1 - i) * 5.0 * scale,
              "%d. %s" % (i + 1, n), 2.5)
        t(bx + 3 * scale, ty0 + n_last * 5.0 * scale + 1.5 * scale,
          "Технические требования", 3.5)
    return ox, oy, W, H


def table(msp, x, y, scale, head, rows, widths, h_row=6.0):
    """Таблица: x, y — левый верхний угол в модели (мм). widths в мм бумаги."""
    W = sum(widths) * scale
    hr = h_row * scale
    n = len(rows) + 1
    for i in range(n + 1):
        msp.add_line((x, y - i * hr), (x + W, y - i * hr), dxfattribs={"layer": "00_РАМКА"})
    cx = x
    for w in widths + [0]:
        msp.add_line((cx, y), (cx, y - n * hr), dxfattribs={"layer": "00_РАМКА"})
        cx += w * scale
    def cells(vals, yy, hgt):
        cx = x
        for v, w in zip(vals, widths):
            msp.add_text(str(v), dxfattribs={"layer": "08_ТЕКСТ", "style": "ГОСТ",
                                             "height": hgt * scale}
                         ).set_placement((cx + 1.5 * scale, yy), align=TA.MIDDLE_LEFT)
            cx += w * scale
    cells(head, y - hr / 2, 2.8)
    for i, r in enumerate(rows):
        cells(r, y - hr * (i + 1) - hr / 2, 2.5)
    return y - n * hr


def text(msp, x, y, s, h, scale, layer="08_ТЕКСТ", al=TA.MIDDLE_CENTER, rot=0.0):
    e = msp.add_text(s, dxfattribs={"layer": layer, "style": "ГОСТ",
                                    "height": h * scale, "rotation": rot})
    e.set_placement((x, y), align=al)
    return e


def poly(msp, pts, layer, close=False):
    msp.add_lwpolyline(pts, close=close, dxfattribs={"layer": layer})


def rect(msp, x0, y0, x1, y1, layer):
    poly(msp, [(x0, y0), (x1, y0), (x1, y1), (x0, y1)], layer, close=True)


# ---------------------------------------------------------------- обводы ----
def hull_outline(z, step=0.5):
    xs, up, dn = [], [], []
    x = 0.0
    while x <= G.LOA + 1e-6:
        b = H.half_breadth(x, z)
        if b > 0.01:
            xs.append(x); up.append(b); dn.append(-b)
        x += step
    if not xs:
        return []
    pts = [(xs[i] * K, up[i] * K) for i in range(len(xs))]
    pts += [(xs[i] * K, dn[i] * K) for i in range(len(xs) - 1, -1, -1)]
    return pts


def super_outline(step=0.5):
    xs, up = [], []
    x = G.SUPER_START
    while x <= G.SUPER_END + 1e-6:
        b = H.super_half_breadth(x)
        if b > 0.01:
            xs.append(x); up.append(b)
        x += step
    pts = [(xs[i] * K, up[i] * K) for i in range(len(xs))]
    pts += [(xs[i] * K, -up[i] * K) for i in range(len(xs) - 1, -1, -1)]
    return pts


def frames_ruler(msp, x0, x1, y, scale, every=20):
    """Разбивка по шпангоутам: штрихи и номера через `every` шпаций."""
    n0 = int(math.ceil(x0 / S.SPACING)); n1 = int(x1 / S.SPACING)
    for n in range(n0, n1 + 1):
        if n % 5:
            continue
        x = n * S.SPACING * K
        big = (n % every == 0)
        msp.add_line((x, y), (x, y - (3.0 if big else 1.4) * scale),
                     dxfattribs={"layer": "09_РАЗМЕРЫ"})
        if big:
            text(msp, x, y - 7.0 * scale, str(n), 3.0, scale,
                 "09_РАЗМЕРЫ", TA.MIDDLE_CENTER)
    msp.add_line((n0 * S.SPACING * K, y), (n1 * S.SPACING * K, y),
                 dxfattribs={"layer": "09_РАЗМЕРЫ"})
    text(msp, x1 * K + 4.0 * K, y - 7.0 * scale,
         "№ шп., шпация 550", 3.0, scale, "09_РАЗМЕРЫ", TA.MIDDLE_LEFT)


def bulkheads(msp, z, scale, labels=True):
    for xb in H.BULKHEADS:
        if xb <= 0.01 or xb >= G.LOA - 0.01:
            continue
        bb = H.half_breadth(xb, z)
        if bb < 0.2:
            continue
        msp.add_line((xb * K, -bb * K), (xb * K, bb * K), dxfattribs={"layer": "03_ПЕРЕБОРКИ"})
        if labels:
            text(msp, xb * K, 11.4 * K, "%.1f" % xb, 2.8, scale,
                 "03_ПЕРЕБОРКИ", TA.MIDDLE_CENTER)


def zone_labels(msp, zones, z, scale, seats=True):
    """Границы помещений, номер в кружке и название, если оно влезает."""
    def hbx(x):
        b = H.half_breadth(x, z)
        if b < 0.2:
            b = H.super_half_breadth(x)
        return max(b, 0.6)
    for i, (x0, x1, kind, name, cap, area) in enumerate(zones, 1):
        for xb in (x0, x1):
            bb = hbx(xb)
            msp.add_line((xb * K, -bb * K), (xb * K, bb * K),
                         dxfattribs={"layer": "06_ПОМЕЩЕНИЯ"})
        cx = 0.5 * (x0 + x1) * K
        r = 3.6 * scale
        msp.add_circle((cx, 9.4 * K), r, dxfattribs={"layer": "06_ПОМЕЩЕНИЯ"})
        text(msp, cx, 9.4 * K, str(i), 4.0, scale, "06_ПОМЕЩЕНИЯ")
        room = (x1 - x0) * K / scale
        if kind != "cabins" and room > len(name) * 1.85 + 6:
            text(msp, cx, -1.0 * K, name, 3.2, scale, "06_ПОМЕЩЕНИЯ")
            if area:
                d = "%.0f м2" % area + ((" · %d мест" % cap) if (cap and seats) else "")
                text(msp, cx, -2.6 * K, d, 2.8, scale, "06_ПОМЕЩЕНИЯ")


def deck_plan(key, z, mark, title, extra=None, use_super=False):
    zl = min(z, G.DEPTH - 0.01)
    hull = hull_outline(zl)
    zones = GA.DECKS.get(key, [])
    ymax = 8.6 * K
    n_rows = len(zones) + 1
    y_tab = -ymax - 12 * K
    bbox = (-2 * K, y_tab - n_rows * 6.0 * 200 - 6 * K, (G.LOA + 6) * K, ymax + 9 * K)
    sheet, sc = pick_sheet(bbox[2] - bbox[0], bbox[3] - bbox[1])
    bbox = (-2 * K, -ymax - 12 * K - n_rows * 6.0 * sc - 6 * K,
            (G.LOA + 6) * K, ymax + 9 * K)
    doc = newdoc(); msp = doc.modelspace()
    if hull:
        poly(msp, hull, "01_ОБШИВКА", close=True)
    if use_super:
        poly(msp, super_outline(), "02_ПАЛУБЫ", close=True)
    msp.add_line((-2 * K, 0), ((G.LOA + 2) * K, 0), dxfattribs={"layer": "07_ОСИ"})
    n_cab = draw_cabins(msp, z - 0.05, sc)
    draw_shafts(msp, z - 0.05, sc)
    zone_labels(msp, zones, zl, sc)
    bulkheads(msp, zl, sc)
    if extra:
        extra(msp, sc)
    frames_ruler(msp, 0, G.LOA, -ymax, sc)
    rows = []
    for i, (x0, x1, kind, name, cap, area) in enumerate(zones, 1):
        rows.append([i, name, ("%.0f" % area) if area else "—",
                     str(cap) if cap else "—",
                     "%d…%d" % (round(x0 / S.SPACING), round(x1 / S.SPACING)),
                     "%.1f…%.1f" % (x0, x1)])
    table(msp, 0.0, y_tab, sc,
          ["№", "Наименование помещения", "Площадь, м2", "Мест", "Шпангоуты", "x, м"],
          rows, [12, 108, 26, 18, 26, 30])
    notes = ("Уровень палубы z = %.2f м от основной плоскости. Кают на ярусе — %d." % (z, n_cab),
             "Размеры в миллиметрах, ось x — от кормового перпендикуляра.",
             "Красные линии — водонепроницаемые переборки, цифра — абсцисса, м.",
             "Ширина коридоров в свету 1400 мм, дверных проёмов 900 мм.")
    frame(msp, sheet, sc, bbox, mark, title,
          "Волжский Горизонт · L = 139,0 м · B = 16,5 м · T = %.2f м" % H.equilibrium()["T"],
          notes)
    path = os.path.join(OUT, mark.replace(" ", "_") + ".dxf")
    doc.saveas(path)
    return path


# ------------------------------------------------------- второе дно ---------
def room_poly(x0, x1, zone, z=0.60, step=0.5):
    """Контуры помещения цистерны в плане (борта — по обшивке). (полигоны, площадь)."""
    xs, out, area = [], [], 0.0
    x = x0
    while x < x1 - 1e-9:
        xs.append(x); x = min(x + step, x1)
    xs.append(x1)
    if zone == "ц":
        inner = [(xx * K, 0.0) for xx in xs]
        for s_ in (1.0, -1.0):
            outer = []
            for xx in xs:
                b = max(H.half_breadth(xx, z) - 0.05, 0.0)
                outer.append((xx * K, s_ * min(G.LONG_BULKHEAD_Y, b) * K))
            out.append(inner + outer[::-1])
            area += sum((min(G.LONG_BULKHEAD_Y, max(H.half_breadth(xx, z) - 0.05, 0.0)))
                        for xx in xs) / len(xs) * (x1 - x0)
    else:
        s_ = 1.0 if zone == "п" else -1.0
        inner, outer, w = [], [], []
        for xx in xs:
            b = max(H.half_breadth(xx, z) - 0.05, 0.0)
            yi = min(G.LONG_BULKHEAD_Y, b)
            inner.append((xx * K, s_ * yi * K)); outer.append((xx * K, s_ * b * K))
            w.append(max(b - yi, 0.0))
        out.append(inner + outer[::-1])
        area = sum(w) / len(w) * (x1 - x0)
    return out, area


def tank_rooms(only_db=True):
    """Разворачивает TANKS в список помещений с объёмом каждого."""
    res = []
    for t in G.TANKS:
        rooms = [r for r in t["rooms"] if (not only_db or r[3] < 1.35)]
        if not rooms:
            continue
        geo = [room_poly(r[0], r[1], r[2], 0.5 * (r[3] + r[4])) for r in rooms]
        caps = [max(a, 1e-6) * (r[4] - r[3]) for (pg, a), r in zip(geo, rooms)]
        tot = sum(caps)
        for r, (pg, a), c in zip(rooms, geo, caps):
            res.append(dict(code=t["code"], name=t["name"], room=r, polys=pg,
                            area=a, vol=t["vol"] * c / tot, group=t["vol"]))
    return res


def tank_plan():
    z = 0.60
    hull = hull_outline(z)
    rooms = tank_rooms()
    ymax = 8.6 * K
    n_rows = len(rooms) + 1
    y_tab = -ymax - 7 * K
    bbox = (-2 * K, y_tab - n_rows * 5.0 * 200 - 6 * K, (G.LOA + 6) * K, ymax + 5 * K)
    sheet, sc = pick_sheet(bbox[2] - bbox[0], bbox[3] - bbox[1])
    bbox = (-2 * K, y_tab - n_rows * 5.0 * sc - 6 * K, (G.LOA + 6) * K, ymax + 5 * K)
    doc = newdoc(); msp = doc.modelspace()
    poly(msp, hull_outline(G.DEPTH - 0.01), "02_ПАЛУБЫ", close=True)
    poly(msp, hull, "01_ОБШИВКА", close=True)
    msp.add_line((-2 * K, 0), ((G.LOA + 2) * K, 0), dxfattribs={"layer": "07_ОСИ"})
    for s_ in (1, -1):
        msp.add_line((34 * K, s_ * G.LONG_BULKHEAD_Y * K),
                     (114 * K, s_ * G.LONG_BULKHEAD_Y * K), dxfattribs={"layer": "03_ПЕРЕБОРКИ"})
    for r in rooms:
        for pg in r["polys"]:
            poly(msp, pg, "04_ЦИСТЕРНЫ", close=True)
            cx = sum(pp[0] for pp in pg) / len(pg)
            cy = sum(pp[1] for pp in pg) / len(pg)
            wide = (r["room"][1] - r["room"][0]) * K / sc
            text(msp, cx, cy + (1.2 * sc if wide > 14 else 0), r["code"],
                 3.0 if wide > 10 else 2.2, sc, "04_ЦИСТЕРНЫ")
            if wide > 14:
                text(msp, cx, cy - 2.8 * sc, "%.0f м3" % (r["vol"] / len(r["polys"])),
                     2.5, sc, "04_ЦИСТЕРНЫ")
    hb12 = H.half_breadth(12.0, z); hb34 = H.half_breadth(34.0, z)
    rect(msp, M.MO_X0 * K, -min(hb12, hb34) * K, M.MO_X1 * K, min(hb12, hb34) * K,
         "05_ОБОРУДОВАНИЕ")
    text(msp, 0.5 * (M.MO_X0 + M.MO_X1) * K, (ymax + 1.6 * K),
         "Машинное отделение 12,0…34,0 м · второе дно опущено до 0,465 м",
         3.2, sc, "05_ОБОРУДОВАНИЕ")
    bulkheads(msp, z, sc)
    frames_ruler(msp, 0, G.LOA, -ymax, sc)
    trows = []
    for i, r in enumerate(sorted(rooms, key=lambda q: q["code"]), 1):
        x0, x1, zone, z0, z1 = r["room"]
        trows.append([i, r["code"], r["name"],
                      {"ц": "ДП", "п": "ПрБ", "л": "ЛБ"}[zone],
                      "%.1f…%.1f" % (x0, x1), "%.2f…%.2f" % (z0, z1),
                      "%.1f" % r["vol"]])
    ts = G.tank_summary()
    table(msp, 0.0, y_tab, sc,
          ["№", "Код", "Наименование цистерны", "Борт", "x, м", "z, м", "V, м3"],
          trows, [10, 16, 96, 14, 26, 24, 18], h_row=5.0)
    notes = ("Второе дно — от обшивки до настила первой палубы, z = 0…1,30 м.",
             "В машинном отделении второе дно опущено до 0,465 м; расходные, отстойные",
             "и масляные цистерны стоят там бортовыми выше настила.",
             "Продольные переборки y = ±4,15 м; вертикальный киль по ДП делит",
             "центральные цистерны на пару — вдвое меньше свободная поверхность.",
             "Всего %d цистерн, %.1f м3, масса содержимого при полном запасе %.1f т."
             % (len(G.TANKS), ts["vol"], ts["mass"]),
             "Цистерна ДТ-4 (аварийный ДГ, 5 м3) вынесена на шлюпочную палубу.")
    frame(msp, sheet, sc, bbox, "ВГ-2026 ярус 0 второе дно",
          "Второе дно и трюм. План цистерн",
          "Волжский Горизонт · 17 цистерн · %.0f м3" % ts["vol"], notes)
    p = os.path.join(OUT, "ВГ-2026_ярус_0_второе_дно.dxf")
    doc.saveas(p); return p


# ---------------------------------------------- машинное отделение ----------
def mach_plan():
    z, xs1 = 1.60, 38.0
    rows = [e for e in M.EQUIPMENT if e[3][0] <= xs1]
    n_rows = len(rows) + 1
    ymax = 8.6 * K
    y_tab = -ymax - 7 * K
    bbox = (-1 * K, y_tab - n_rows * 5.5 * 100 - 6 * K, (xs1 + 3) * K, ymax + 5 * K)
    sheet, sc = pick_sheet(bbox[2] - bbox[0], bbox[3] - bbox[1])
    bbox = (-1 * K, y_tab - n_rows * 5.5 * sc - 6 * K, (xs1 + 3) * K, ymax + 5 * K)
    doc = newdoc(); msp = doc.modelspace()
    up = []
    x = 0.0
    while x <= xs1 + 1e-6:
        b = H.half_breadth(x, z)
        if b > 0.01:
            up.append((x * K, b * K))
        x += 0.5
    poly(msp, up, "01_ОБШИВКА")
    poly(msp, [(pp[0], -pp[1]) for pp in up], "01_ОБШИВКА")
    poly(msp, [(pp[0], H.half_breadth(pp[0] / K, G.DEPTH - 0.01) * K) for pp in up], "02_ПАЛУБЫ")
    poly(msp, [(pp[0], -H.half_breadth(pp[0] / K, G.DEPTH - 0.01) * K) for pp in up], "02_ПАЛУБЫ")
    msp.add_line((0, 0), (xs1 * K, 0), dxfattribs={"layer": "07_ОСИ"})
    for xb in (9.5, 12.0, 30.0, 34.0):
        b = H.half_breadth(xb, z)
        msp.add_line((xb * K, -b * K), (xb * K, b * K), dxfattribs={"layer": "03_ПЕРЕБОРКИ"})
        text(msp, xb * K, (b + 1.0) * K, "%.1f" % xb, 3.0, sc, "03_ПЕРЕБОРКИ")
    for code, x0, x1, y0, y1, z0, z1 in M.boxes():
        if x0 > xs1:
            continue
        rect(msp, x0 * K, y0 * K, x1 * K, y1 * K, "05_ОБОРУДОВАНИЕ")
        text(msp, 0.5 * (x0 + x1) * K, 0.5 * (y0 + y1) * K, code, 3.2, sc, "05_ОБОРУДОВАНИЕ")
    frames_ruler(msp, 0, xs1, -ymax, sc)
    trows = []
    for i, (code, name, n, b, mir, pw, ms, note) in enumerate(rows, 1):
        trows.append([i, code, name, n * (2 if mir else 1),
                      ("%d" % pw) if pw else "—", ("%.1f" % ms) if ms else "—",
                      "%.1f…%.1f" % (b[0], b[1]), note])
    table(msp, 0.0, y_tab, sc,
          ["№", "Код", "Наименование", "Кол.", "кВт", "т", "x, м", "Примечание"],
          trows, [10, 16, 82, 14, 14, 12, 24, 96], h_row=5.5)
    notes = ("Машинное отделение между переборками 12,0 и 34,0 м.",
             "Второе дно в МО опущено до 0,465 м, подволок — главная палуба 4,20 м.",
             "ДЭУ: 3 ГДГ по 1600 кВт на ГРЩ 690 В, 2 ГЭД по 1800 кВт,",
             "две линии вала, ВФШ D = 1,70 м в насадках Корт, 2 полуподвесных руля.",
             "Тонкая линия — контур палубы на уровне 4,20 м.")
    frame(msp, sheet, sc, bbox, "ВГ-2026 машинное отделение",
          "Машинное отделение. План",
          "Волжский Горизонт · ДЭУ 3 x 1600 / 2 x 1800 кВт", notes)
    pth = os.path.join(OUT, "ВГ-2026_машинное_отделение.dxf")
    doc.saveas(pth); return pth


# ------------------------------------------- поперечное сечение -------------
def section(x=70.0, mark="ВГ-2026 поперечное сечение"):
    b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(x)
    T = H.equilibrium()["T"]
    sh = H.super_half_breadth(x)
    eg = S.equivalent_girder()
    plates = list(S.PLATES.items())
    profs = [(k, "%d x %d" % (v[0], v[1]) + (" + %d x %d" % (v[2], v[3]) if v[2] else ""))
             for k, v in S.PROFILES.items()]
    n_rows = max(len(plates), len(profs)) + 1
    y_tab = -4.0 * K
    bbox = (-13 * K, y_tab - n_rows * 5.5 * 50 - 6 * K, 13 * K, 15.0 * K)
    sheet, sc = pick_sheet(bbox[2] - bbox[0], bbox[3] - bbox[1])
    bbox = (-13 * K, y_tab - n_rows * 5.5 * sc - 6 * K, 13 * K, 15.0 * K)
    doc = newdoc(); msp = doc.modelspace()
    for s_ in (1, -1):
        poly(msp, [(0, z_kil * K), (s_ * b_dn * K, z_kil * K), (s_ * b_sk * K, z_sk * K),
                   (s_ * b_pal * K, z_brt * K)], "01_ОБШИВКА")
        msp.add_line((s_ * sh * K, G.DEPTH * K), (s_ * sh * K, 12.60 * K),
                     dxfattribs={"layer": "02_ПАЛУБЫ"})
    msp.add_line((0, (z_kil - 0.8) * K), (0, 13.4 * K), dxfattribs={"layer": "07_ОСИ"})
    text(msp, 0, 13.7 * K, "ДП", 3.5, sc, "07_ОСИ")
    decks = [(S.DB_HEIGHT, b_sk - 0.30, "Второе дно 1,30", -1),
             (G.DECKS["первая"], b_sk - 0.05, "Первая палуба 1,40", 1),
             (G.DECKS["главная"], b_pal, "Главная палуба 4,20", 1),
             (G.DECKS["верхняя"], sh, "Верхняя палуба 7,00", 1),
             (G.DECKS["солнечная"], sh, "Шлюпочная палуба 9,80", 1),
             (12.60, sh - 1.2, "Солнечная палуба 12,60", 1)]
    for z, b, lab, side in decks:
        msp.add_line((-b * K, z * K), (b * K, z * K), dxfattribs={"layer": "02_ПАЛУБЫ"})
        if side > 0:
            text(msp, (b + 0.5) * K, (z + 0.3) * K, lab, 3.2, sc, "02_ПАЛУБЫ", TA.MIDDLE_LEFT)
        else:
            text(msp, (-b - 0.5) * K, (z + 0.3) * K, lab, 3.2, sc, "02_ПАЛУБЫ", TA.MIDDLE_RIGHT)
    msp.add_line((-10.4 * K, T * K), (10.4 * K, T * K), dxfattribs={"layer": "07_ОСИ"})
    text(msp, 10.6 * K, (T + 0.3) * K, "ВЛ T = %.2f м" % T, 3.2, sc, "07_ОСИ", TA.MIDDLE_LEFT)
    msp.add_line((0, z_kil * K), (0, S.DB_HEIGHT * K), dxfattribs={"layer": "10_НАБОР"})
    nst = int((b_sk - 0.3) / 1.10)
    for i in range(1, nst + 1):
        for s_ in (1, -1):
            msp.add_line((s_ * i * 1.10 * K, z_kil * K), (s_ * i * 1.10 * K, S.DB_HEIGHT * K),
                         dxfattribs={"layer": "10_НАБОР"})
    text(msp, 0, -1.2 * K, "B = 16 500", 4.0, sc, "09_РАЗМЕРЫ")
    text(msp, 0, -2.3 * K, "Шп. %d  (x = %.1f м)   H = 4 200   T = %.0f"
         % (round(x / S.SPACING), x, T * 1000), 3.2, sc, "09_РАЗМЕРЫ")
    rows = []
    for i in range(n_rows - 1):
        pl = ("%s" % plates[i][0], "%.0f" % plates[i][1]) if i < len(plates) else ("", "")
        pr = profs[i] if i < len(profs) else ("", "")
        rows.append([i + 1, pl[0], pl[1], pr[0], pr[1]])
    table(msp, -12.0 * K, y_tab, sc,
          ["№", "Лист обшивки и настила", "t, мм", "Профиль набора", "h x t + b x t, мм"],
          rows, [10, 76, 18, 60, 52], h_row=5.5)
    notes = ("Сечение по мидель-шпангоуту. Смешанная система набора: продольная в днище,",
             "втором дне и главной палубе, поперечная по бортам.",
             "Шпация 550 мм, рамная шпация 2200 мм. Сталь 09Г2С ГОСТ 19281-2014.",
             "Эквивалентный брус: A = %.0f см2, z0 = %.3f м, I = %.3f м4," % (eg["A"], eg["z0"], eg["I_m4"]),
             "W палубы = %.3f м3, W днища = %.3f м3." % (eg["W_deck_m3"], eg["W_bot_m3"]))
    frame(msp, sheet, sc, bbox, mark, "Поперечное сечение по миделю",
          "Волжский Горизонт · B = 16,5 м · H = 4,2 м · T = %.2f м" % T, notes)
    pth = os.path.join(OUT, mark.replace(" ", "_") + ".dxf")
    doc.saveas(pth); return pth


# ------------------------------------------- продольный разрез --------------
TIERS = [(0.00, 1.30, "Ярус 0 · трюм, второе дно, цистерны"),
         (1.40, 4.20, "Ярус 1 · первая палуба"),
         (4.20, 7.00, "Ярус 2 · главная палуба"),
         (7.00, 9.80, "Ярус 3 · верхняя палуба"),
         (9.80, 12.60, "Ярус 4 · шлюпочная палуба"),
         (12.60, 15.40, "Ярус 5 · солнечная палуба и рубка")]


def profile():
    step = 0.5
    keel, deck = [], []
    x = 0.0
    while x <= G.LOA + 1e-6:
        b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(x)
        keel.append((x * K, z_kil * K)); deck.append((x * K, z_brt * K))
        x += step
    T = H.equilibrium()["T"]
    bbox = (-3 * K, -20 * K, (G.LOA + 34) * K, 18 * K)
    sheet, sc = pick_sheet(bbox[2] - bbox[0], bbox[3] - bbox[1])
    doc = newdoc(); msp = doc.modelspace()
    poly(msp, keel, "01_ОБШИВКА"); poly(msp, deck, "01_ОБШИВКА")
    msp.add_line((0, keel[0][1]), (0, deck[0][1]), dxfattribs={"layer": "01_ОБШИВКА"})
    msp.add_line((G.LOA * K, keel[-1][1]), (G.LOA * K, deck[-1][1]), dxfattribs={"layer": "01_ОБШИВКА"})
    # палубы внутри корпуса
    for z in (S.DB_HEIGHT, G.DECKS["первая"], G.DECKS["главная"]):
        msp.add_line((9.0 * K, z * K), (127.0 * K, z * K), dxfattribs={"layer": "02_ПАЛУБЫ"})
    # надстройка
    for z in (G.DECKS["верхняя"], G.DECKS["солнечная"], 12.60):
        msp.add_line((G.SUPER_START * K, z * K), (G.SUPER_END * K, z * K),
                     dxfattribs={"layer": "02_ПАЛУБЫ"})
    for xx in (G.SUPER_START, G.SUPER_END):
        msp.add_line((xx * K, G.DEPTH * K), (xx * K, 12.60 * K), dxfattribs={"layer": "02_ПАЛУБЫ"})
    rect(msp, 115.4 * K, 12.60 * K, 131.0 * K, 15.40 * K, "02_ПАЛУБЫ")
    text(msp, 123.2 * K, 14.0 * K, "рулевая рубка", 2.6, sc, "02_ПАЛУБЫ")
    # переборки
    for xb in H.BULKHEADS[1:-1]:
        b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(xb)
        msp.add_line((xb * K, z_kil * K), (xb * K, G.DEPTH * K), dxfattribs={"layer": "03_ПЕРЕБОРКИ"})
        text(msp, xb * K, -1.1 * K, "%.1f" % xb, 3.0, sc, "03_ПЕРЕБОРКИ")
    msp.add_line((-2 * K, T * K), ((G.LOA + 2) * K, T * K), dxfattribs={"layer": "07_ОСИ"})
    text(msp, (G.LOA + 1.5) * K, (T + 0.6) * K, "ВЛ %.2f м" % T, 3.0, sc, "07_ОСИ", TA.MIDDLE_LEFT)
    # обозначение ярусов
    xr = (G.LOA + 9.0) * K
    for z0, z1, name in TIERS:
        msp.add_line((xr, z0 * K), (xr, z1 * K), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        for z in (z0, z1):
            msp.add_line((xr - 0.6 * K, z * K), (xr + 0.6 * K, z * K),
                         dxfattribs={"layer": "09_РАЗМЕРЫ"})
        text(msp, xr + 1.0 * K, 0.5 * (z0 + z1) * K, name, 3.0, sc, "09_РАЗМЕРЫ", TA.MIDDLE_LEFT)
    frames_ruler(msp, 0, G.LOA, -2.2 * K, sc)
    trows = []
    KEY = {0: None, 1: "первая", 2: "главная", 3: "верхняя", 4: "шлюпочная", 5: "солнечная"}
    for i, (z0, z1, name) in enumerate(TIERS):
        zones = GA.DECKS.get(KEY.get(i) or "", [])
        area = sum(z[5] for z in zones if z[5])
        seats = sum(z[4] for z in zones if z[4])
        main = ", ".join(z[3].split(",")[0] for z in
                         sorted(zones, key=lambda q: q[1] - q[0], reverse=True)[:3]) or             "цистерны, машинное отделение, электростанция"
        if len(main) > 74:
            main = main[:71] + "…"
        trows.append([i, name.split("·")[1].strip() if "·" in name else name,
                      "%.2f…%.2f" % (z0, z1), "%.1f" % (z1 - z0),
                      ("%.0f" % area) if area else "—",
                      ("%d" % seats) if seats else "—", main])
    table(msp, 0.0, -6.0 * K, sc,
          ["Ярус", "Наименование", "z, м", "Высота, м", "Площадь, м2", "Мест",
           "Основные помещения"],
          trows, [14, 62, 30, 24, 26, 16, 150], h_row=6.0)
    notes = ("Продольный разрез по ДП — только обозначение ярусов.",
             "Высоты от основной плоскости, м. Габаритная высота от ВЛ — 13,2 м.",
             "Красные линии — водонепроницаемые переборки (8 шт.).")
    frame(msp, sheet, sc, bbox, "ВГ-2026 продольный разрез",
          "Продольный разрез. Обозначение ярусов",
          "Волжский Горизонт · L = 139,0 м · H = 4,2 м", notes)
    p = os.path.join(OUT, "ВГ-2026_продольный_разрез.dxf")
    doc.saveas(p); return p


# ---------------------------------------- теоретический чертёж --------------
def lines_plan():
    T = H.equilibrium()["T"]
    bbox = (-4 * K, -12 * K, (G.LOA + 4) * K, 12 * K)
    sheet, sc = pick_sheet(bbox[2] - bbox[0], bbox[3] - bbox[1])
    doc = newdoc(); msp = doc.modelspace()
    # бок: батоксы по килевой и палубной линии
    keel, deck = [], []
    x = 0.0
    while x <= G.LOA + 1e-6:
        b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(x)
        keel.append((x * K, (z_kil - 6.0) * K)); deck.append((x * K, (z_brt - 6.0) * K))
        x += 0.5
    poly(msp, keel, "01_ОБШИВКА"); poly(msp, deck, "01_ОБШИВКА")
    for z in (1.0, 2.0, T, 3.2, 4.0):
        msp.add_line((0, (z - 6.0) * K), (G.LOA * K, (z - 6.0) * K), dxfattribs={"layer": "07_ОСИ"})
    # полуширота: ватерлинии
    for z in (0.6, 1.2, 1.8, T, 3.0, 3.6, G.DEPTH - 0.01):
        pts = []
        x = 0.0
        while x <= G.LOA + 1e-6:
            b = H.half_breadth(x, z)
            if b > 0.005:
                pts.append((x * K, b * K))
            x += 0.5
        if len(pts) > 2:
            poly(msp, pts, "01_ОБШИВКА")
            text(msp, pts[len(pts) // 2][0], pts[len(pts) // 2][1] + 0.25 * K,
                 "ВЛ %.2f" % z, 2.0, sc, "09_РАЗМЕРЫ")
    msp.add_line((0, 0), (G.LOA * K, 0), dxfattribs={"layer": "07_ОСИ"})
    frames_ruler(msp, 0, G.LOA, -11.2 * K, sc)
    notes = ("Теоретический чертёж: бок (смещён вниз на 6 м) и полуширота.",
             "Ординаты — таблица STATIONS, 15 расчётных шпангоутов.",
             "Корпус: транцевая корма, скула с радиусом, цилиндрическая вставка 30…88 м.")
    frame(msp, sheet, sc, bbox, "ВГ-2026 теоретический чертёж",
          "Теоретический чертёж", "Волжский Горизонт · L = 139,0 · B = 16,5 · H = 4,2", notes)
    p = os.path.join(OUT, "ВГ-2026_теоретический_чертёж.dxf")
    doc.saveas(p); return p


def main():
    made = []
    made.append(tank_plan())
    made.append(deck_plan("первая", 1.45, "ВГ-2026 ярус 1 первая палуба",
                          "Первая палуба. План"))
    made.append(deck_plan("главная", 4.25, "ВГ-2026 ярус 2 главная палуба",
                          "Главная палуба. План", use_super=True))
    made.append(deck_plan("верхняя", 7.05, "ВГ-2026 ярус 3 верхняя палуба",
                          "Верхняя палуба. План", use_super=True))
    made.append(deck_plan("шлюпочная", 9.85, "ВГ-2026 ярус 4 шлюпочная палуба",
                          "Шлюпочная палуба. План", use_super=True))
    made.append(deck_plan("солнечная", 12.65, "ВГ-2026 ярус 5 солнечная палуба",
                          "Солнечная палуба. План", use_super=True))
    made.append(mach_plan())
    made.append(section())
    made.append(profile())
    made.append(lines_plan())
    for p in made:
        print(os.path.basename(p), os.path.getsize(p) // 1024, "КБ")
    return made


if __name__ == "__main__":
    main()
