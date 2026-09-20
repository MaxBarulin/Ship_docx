# -*- coding: utf-8 -*-
"""Планы ярусов: ортогональные виды из Blender + подписи помещений.

Сырые виды рендерит Blender (ортокамера PLAN_CAM, вид сверху, секущая
плоскость на 2.05 м над настилом). Здесь они обрезаются, подписываются
зонами из gorizont_ga и получают масштабную линейку.

    python scripts/планы_палуб.py [папка_с_сырыми_рендерами]
"""
import os, sys, io, json
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from PIL import Image, ImageDraw, ImageFont
import matplotlib
from lib import gorizont as G, gorizont_ga as GA, gorizont_hydro as H

RAW = sys.argv[1] if len(sys.argv) > 1 else r"F:\Temp\claude\gor\планы_raw"
OUT = os.path.join(ROOT, "renders", "горизонт_2026", "планы")
os.makedirs(OUT, exist_ok=True)
FDIR = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
F = lambda n, sz: ImageFont.truetype(os.path.join(FDIR, n), sz)
REG, BOLD, IT = "DejaVuSans.ttf", "DejaVuSans-Bold.ttf", "DejaVuSans-Oblique.ttf"
INK, GRY, ACC, SEA = (22, 32, 47), (110, 122, 140), (176, 38, 52), (28, 92, 138)

W, HH = 2400, 800           # итоговый лист
ORTHO, RAWW, RAWH, XC = 148.0, 2800, 560, 69.5
SCALE = W / ORTHO           # пикселей на метр на итоговом листе
X0 = XC - ORTHO / 2.0       # левый край кадра в метрах
# Полуширота судна в пикселях листа: от неё, а не от числа «на глаз»,
# отсчитываются выноски — иначе подписи наезжают на борт.
HULL_PX = max(H.half_breadth(x, G.DEPTH - 0.01)
              for x in [i * 0.5 for i in range(int(G.LOA * 2) + 1)]) * SCALE
LEAD = HULL_PX + 10         # начало выноски
LAB = HULL_PX + 34          # первая строка подписей

PLANS = [
    ("0_трюм_второе_дно", "Трюм и второе дно · 0.00…1.30 м",
     "Цистерны, машинное отделение, набор корпуса", None),
    ("1_первая_палуба", "Первая палуба · 1.40 м",
     "Каюты эконом и стандарт, камбуз, провизия, каюты экипажа", "первая"),
    ("2_главная_палуба", "Главная палуба · 4.20 м",
     "Ресторан, театр-лаунж, бистро, лобби с ресепшеном и медпунктом", "главная"),
    ("3_верхняя_палуба", "Верхняя палуба · 7.00 м",
     "Спа, фитнес, библиотека, магазины, каюты бизнес и стандарт", "верхняя"),
    ("4_шлюпочная_палуба", "Шлюпочная палуба · 9.80 м",
     "Люксы с балконами, бар-лаундж, детский клуб, рулевая рубка", "шлюпочная"),
    ("5_солнечная_палуба", "Солнечная палуба · 12.60 м",
     "Шезлонги, смотровая площадка, солнечные батареи, дрон-порт", "солнечная"),
]


def px(x):
    return (x - X0) * SCALE


def build(name, title, sub, key):
    raw = Image.open(os.path.join(RAW, name + ".png")).convert("RGBA")
    raw = raw.resize((W, int(RAWH * W / RAWW)), Image.LANCZOS)
    bg = Image.new("RGBA", raw.size, (255, 255, 255, 255))
    raw = Image.alpha_composite(bg, raw).convert("RGB")
    if key is None:
        raw = Image.blend(raw, Image.new("RGB", raw.size, "white"), 0.55)
    canvas = Image.new("RGB", (W, HH), "white")
    ship_top = 360
    canvas.paste(raw, (0, ship_top - raw.size[1] // 2))
    d = ImageDraw.Draw(canvas)
    d.rectangle([0, 0, W, 96], fill=(246, 248, 251))
    d.line([0, 96, W, 96], fill=(222, 228, 236))
    d.text((44, 26), title, font=F(BOLD, 38), fill=INK)
    d.text((44, 72), sub, font=F(IT, 22), fill=GRY)
    d.text((W - 44, 30), "Планы палуб · М 1:250 (А2)", font=F(REG, 20), fill=GRY, anchor="ra")
    d.text((W - 44, 62), "«Волжский Горизонт» · проект 2026", font=F(REG, 20), fill=GRY, anchor="ra")

    zones = GA.DECKS.get(key, []) if key else []
    items = []
    for x0, x1, kind, zname, want, area in zones:
        lab = zname
        if area:
            lab += " · %.0f м²" % area
        # пятое поле таблицы зон — площадь по описанию задания, а не места.
        # Раньше её печатали как «мест», и на плане стояло «Провизионные
        # склады · 87 м² · 110 мест».
        if want and area and abs(want - area) > 1.0:
            lab += " (по заданию %.0f м²)" % want
        n = _seats(x0, x1, key)
        if n:
            lab += " · %d мест" % n
        items.append([px(0.5 * (x0 + x1)), lab])
    items.sort()
    fnt = F(REG, 21)
    groups = {1: [], -1: []}
    for i, it in enumerate(items):
        groups[1 if i % 2 == 0 else -1].append(it)
    for side, lst in groups.items():
        rows_end = []
        for cx, lab in lst:
            wlab = d.textlength(lab, font=fnt)
            tx = min(max(cx, 16 + wlab / 2), W - 16 - wlab / 2)
            r = 0
            while r < len(rows_end) and tx - wlab / 2 < rows_end[r] + 18:
                r += 1
            if r == len(rows_end):
                rows_end.append(0)
            rows_end[r] = tx + wlab / 2
            if side > 0:
                ty = ship_top - LAB - r * 44
                d.line([cx, ship_top - LEAD, cx, ty + 30], fill=(170, 180, 194), width=2)
                if abs(tx - cx) > 2:
                    d.line([cx, ty + 30, tx, ty + 30], fill=(170, 180, 194), width=2)
                d.text((tx, ty), lab, font=fnt, fill=INK, anchor="ma")
            else:
                ty = ship_top + LAB + r * 44
                d.line([cx, ship_top + LEAD, cx, ty - 8], fill=(170, 180, 194), width=2)
                if abs(tx - cx) > 2:
                    d.line([cx, ty - 8, tx, ty - 8], fill=(170, 180, 194), width=2)
                d.text((tx, ty), lab, font=fnt, fill=INK, anchor="ma")

    if key is None:
        tf = F(BOLD, 19)
        out = [(px(x), ship_top - H.half_breadth(x, G.DEPTH - 0.01) * SCALE)
               for x in [i * 0.5 for i in range(0, int(G.LOA * 2) + 1)]
               if H.half_breadth(x, G.DEPTH - 0.01) > 0.01]
        d.line(out, fill=(150, 160, 175), width=2)
        d.line([(a_, ship_top * 2 - b_) for a_, b_ in out], fill=(150, 160, 175), width=2)
        d.text((px(132.0), ship_top - 5.2 * SCALE), "контур главной палубы",
               font=F(IT, 17), fill=(120, 132, 150), anchor="mb")
        for t in G.TANKS:
            for (rx0, rx1, zone, rz0, rz1) in t["rooms"]:
                if rz0 > 1.35:
                    continue
                zmid = 0.5 * (rz0 + rz1)
                sides = [(0.0, G.LONG_BULKHEAD_Y), (0.0, -G.LONG_BULKHEAD_Y)] if zone == "ц"                     else [((G.LONG_BULKHEAD_Y if zone == "п" else -G.LONG_BULKHEAD_Y),
                           (1 if zone == "п" else -1) * H.half_breadth(0.5 * (rx0 + rx1), zmid))]
                for ya, yb in sides:
                    x_a, x_b = px(rx0), px(rx1)
                    y_a = ship_top - ya * SCALE
                    y_b = ship_top - yb * SCALE
                    d.rectangle([x_a, min(y_a, y_b), x_b, max(y_a, y_b)],
                                outline=(24, 122, 90), width=2)
                    if x_b - x_a > 46:
                        d.text(((x_a + x_b) / 2, (y_a + y_b) / 2), t["code"],
                               font=tf, fill=(18, 96, 70), anchor="mm")
        d.rectangle([px(12.0), ship_top - 7.4 * SCALE, px(34.0), ship_top + 7.4 * SCALE],
                    outline=ACC, width=3)
        d.text((px(23.0), ship_top - 7.4 * SCALE - 26),
               "Машинное отделение 12.0…34.0 м · второе дно 0.465 м",
               font=F(BOLD, 20), fill=ACC, anchor="mb")

    # масштабная линейка
    ry = HH - 78
    d.text((px(0), ry - 34), "м от кормового перпендикуляра", font=F(REG, 18), fill=GRY)
    d.line([px(0), ry, px(G.LOA), ry], fill=INK, width=2)
    for m in range(0, int(G.LOA) + 1, 10):
        d.line([px(m), ry, px(m), ry + 12], fill=INK, width=2)
        d.text((px(m), ry + 18), str(m), font=F(REG, 18), fill=GRY, anchor="mt")
    for m in range(5, int(G.LOA), 10):
        d.line([px(m), ry, px(m), ry + 7], fill=(150, 160, 175), width=2)
    d.text((W - 150, ry - 26), "нос", font=F(REG, 20), fill=SEA, anchor="rb")
    d.line([W - 140, ry - 16, W - 40, ry - 16], fill=SEA, width=3)
    d.polygon([(W - 40, ry - 16), (W - 56, ry - 23), (W - 56, ry - 9)], fill=SEA)
    p = os.path.join(OUT, name + ".png")
    canvas.save(p)
    return p


def main():
    for name, title, sub, key in PLANS:
        print(os.path.basename(build(name, title, sub, key)))


if __name__ == "__main__":
    main()
