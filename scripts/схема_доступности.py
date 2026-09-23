# -*- coding: utf-8 -*-
"""Схема доступности и путей эвакуации по четырём закрытым ярусам.

Берёт те же сырые ортогональные виды, что и планы ярусов.

    python scripts/схема_доступности.py [папка_с_сырыми_рендерами]
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from PIL import Image, ImageDraw, ImageFont
import matplotlib
from lib import gorizont as G, gorizont_ga as GA

RAW = sys.argv[1] if len(sys.argv) > 1 else r"F:\Temp\claude\gor\планы_raw"
OUT = os.path.join(ROOT, "renders", "горизонт_2026", "схемы")
os.makedirs(OUT, exist_ok=True)
FDIR = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
def font(sz, b=False, i=False):
    n = "DejaVuSans-Bold.ttf" if b else ("DejaVuSans-Oblique.ttf" if i else "DejaVuSans.ttf")
    return ImageFont.truetype(os.path.join(FDIR, n), sz)
INK, INK2 = (24, 34, 52), (86, 98, 120)
ACC, SEA, GREEN = (176, 38, 52), (28, 92, 138), (24, 116, 84)

W = 2400
ORTHO, RAWW, RAWH, XC = 148.0, 2800, 560, 69.5
SCALE = W / ORTHO
X0 = XC - ORTHO / 2.0
STRIP = int(RAWH * W / RAWW)          # высота полосы яруса
def px(x): return (x - X0) * SCALE

DECKS = [("1_первая_палуба",   "Первая палуба · 1.40",    "первая"),
         ("2_главная_палуба",  "Главная палуба · 4.20",   "главная"),
         ("3_верхняя_палуба",  "Верхняя палуба · 7.00",   "верхняя"),
         ("4_шлюпочная_палуба","Шлюпочная палуба · 9.80", "шлюпочная")]
HDR, GAP, BOT = 96, 66, 300
H = HDR + len(DECKS) * (STRIP + GAP) + BOT
LIFTS = [(35.6, 1.1), (93.6, 1.1)]
STAIRS = [(36.8, -1.05), (94.8, -1.05)]
ACCESS = {"шлюпочная": [(86.1, 3.2), (86.1, -3.2)],
          "верхняя": [(84.9, 5.36), (84.9, -5.36), (101.1, 5.33),
                      (107.1, 5.28), (101.1, -5.33), (107.1, -5.28)]}
WC = {"первая": [(62.0, 0.0)], "главная": [(80.0, -1.6)],
      "верхняя": [(45.0, 0.0)], "шлюпочная": [(96.0, 0.0)]}
MUSTER = [(44.6, 0.0), (53.4, 0.0), (94.1, 0.0)]

img = Image.new("RGB", (W, H), "white")
for i, (fn, _, _) in enumerate(DECKS):
    raw = Image.open(os.path.join(RAW, fn + ".png")).convert("RGBA")
    # у сырого плана фон прозрачный: без подложки он ложится чёрным
    raw = Image.alpha_composite(
        Image.new("RGBA", raw.size, (255, 255, 255, 255)), raw).convert("RGB")
    raw = raw.resize((W, STRIP), Image.LANCZOS)
    img.paste(raw, (0, HDR + i * (STRIP + GAP) + GAP))
d = ImageDraw.Draw(img)
d.rectangle([0, 0, W, HDR], fill=(246, 248, 251))
d.line([0, HDR, W, HDR], fill=(206, 214, 226), width=2)
d.text((46, 22), "Доступность и пути эвакуации", font=font(38, b=True), fill=INK)
d.text((46, 68), "Лифты на все ярусы · %d кают для маломобильных пассажиров в трёх "
       "категориях · сквозные шлюпочные променады" % GA.summary()["accessible"],
       font=font(20), fill=INK2)
d.text((W - 46, 30), "Схемы · «Волжский Горизонт»", font=font(19), fill=INK2, anchor="ra")
d.text((W - 46, 62), "проект 2026", font=font(19), fill=INK2, anchor="ra")


def Y(i, v): return HDR + i * (STRIP + GAP) + GAP + STRIP / 2 - v * SCALE


def wheel(dd, x, y, r=13):
    dd.ellipse([x-r, y-r, x+r, y+r], fill=(255, 255, 255), outline=GREEN, width=3)
    dd.ellipse([x-r+4, y-r+4, x+r-4, y+r-4], fill=GREEN)


for i, (fn, title, deck) in enumerate(DECKS):
    ytop = HDR + i * (STRIP + GAP) + GAP
    d.rectangle([0, ytop - GAP + 8, W, ytop - 6], fill=(243, 246, 250))
    d.text((46, ytop - GAP + 16), title, font=font(24, b=True), fill=INK)
    for sgn in (1, -1):
        yc = Y(i, sgn * (4.1 if deck == "первая" else 1.1))
        d.line([px(12), yc, px(128), yc], fill=(38, 150, 110), width=5)
    for (X, Yc) in LIFTS:
        x, y = px(X), Y(i, Yc)
        d.rectangle([x-14, y-14, x+14, y+14], fill=(255, 255, 255), outline=SEA, width=3)
        d.text((x, y), "Л", font=font(18, b=True), fill=SEA, anchor="mm")
    for (X, Yc) in STAIRS:
        x, y = px(X), Y(i, Yc)
        d.rectangle([x-14, y-14, x+14, y+14], fill=(255, 255, 255), outline=INK2, width=3)
        d.text((x, y), "Т", font=font(18, b=True), fill=INK2, anchor="mm")
    for (X, Yc) in ACCESS.get(deck, []):
        wheel(d, px(X), Y(i, Yc))
    for (X, Yc) in WC.get(deck, []):
        x, y = px(X), Y(i, Yc)
        d.ellipse([x-13, y-13, x+13, y+13], fill=(255, 255, 255), outline=GREEN, width=3)
        d.text((x, y), "WC", font=font(13, b=True), fill=GREEN, anchor="mm")
    if deck == "шлюпочная":
        for (X, _) in MUSTER:
            for sgn in (1, -1):
                x, y = px(X), Y(i, sgn * 7.4)
                d.rectangle([x-20, y-12, x+20, y+12], fill=ACC)
                d.text((x, y), "СБОР", font=font(13, b=True), fill=(255, 255, 255), anchor="mm")
        for sgn in (1, -1):
            d.line([px(13), Y(i, sgn * 7.4), px(130), Y(i, sgn * 7.4)], fill=ACC, width=4)

ly = HDR + len(DECKS) * (STRIP + GAP) + 54
def leg(x, y, draw, txt, sub=""):
    draw(x, y)
    d.text((x + 28, y - 13), txt, font=font(20), fill=INK)
    if sub:
        d.text((x + 28, y + 7), sub, font=font(17), fill=INK2)
leg(70, ly, lambda x, y: wheel(d, x, y), "каюта для маломобильных пассажиров",
    "8 кают - 4 бизнес, 2 люкс, 2 стандарт - выбор класса, а не «каюта для инвалида»")
leg(1000, ly, lambda x, y: (d.rectangle([x-14, y-14, x+14, y+14], fill=(255, 255, 255),
                                        outline=SEA, width=3),
                            d.text((x, y), "Л", font=font(18, b=True), fill=SEA, anchor="mm")),
    "лифт %.2f x %.2f м" % G.LIFT_CAR, "оба лифта обслуживают все четыре яруса")
leg(1650, ly, lambda x, y: d.line([x-16, y, x+16, y], fill=(38, 150, 110), width=5),
    "безбарьерный маршрут",
    "проезд %.2f м, разворот %.2f м, порогов нет" % (G.CLEAR_PASSAGE, G.TURN_CIRCLE))
leg(70, ly + 74, lambda x, y: d.line([x-16, y, x+16, y], fill=ACC, width=4),
    "шлюпочный променад и путь к местам сбора",
    "сквозной по обоим бортам, ширина 1.30 м, по два выхода на борт")
leg(1000, ly + 74, lambda x, y: (d.ellipse([x-13, y-13, x+13, y+13], fill=(255, 255, 255),
                                           outline=GREEN, width=3),
                                 d.text((x, y), "WC", font=font(13, b=True), fill=GREEN,
                                        anchor="mm")),
    "доступный санузел", "по одному на каждом ярусе")
leg(1650, ly + 74, lambda x, y: (d.rectangle([x-20, y-12, x+20, y+12], fill=ACC),
                                 d.text((x, y), "СБОР", font=font(13, b=True),
                                        fill=(255, 255, 255), anchor="mm")),
    "место сбора по тревоге", "у шлюпок, шесть постов")
p = os.path.join(OUT, "доступность_и_эвакуация.png")
img.save(p)
print(p)
