# -*- coding: utf-8 -*-
"""Сводный лист расчётов по теории корабля."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from PIL import ImageFont
F = r"C:\Windows\Fonts"
def font(sz, b=False):
    return ImageFont.truetype(os.path.join(F, "segoeuib.ttf" if b else "segoeui.ttf"), sz)
def text(d, xy, s, f, fill=(24,34,52), anchor="la"):
    d.text(xy, s, font=f, fill=fill, anchor=anchor)
def tw(d, s, f):
    b = d.textbbox((0,0), s, font=f); return b[2]-b[0], b[3]-b[1]
ROOT_R = os.path.join(ROOT, "renders", "горизонт_2026")
from PIL import Image, ImageDraw
from lib import gorizont_hydro as H, gorizont_struct as SS, gorizont_strength as St

R = ROOT_R
CALC = os.path.join(R, "расчёты")
DRW = os.path.join(R, "чертежи")
W, Ht = 3400, 7300
img = Image.new("RGB", (W, Ht), (255, 255, 255))
d = ImageDraw.Draw(img)

d.rectangle([0, 0, W, 196], fill=(18, 30, 48))
text(d, (64, 34), "ТЕОРИЯ КОРАБЛЯ И ПРОЧНОСТЬ", font(66, b=True), (255, 255, 255))
text(d, (64, 122), "«Волжский Горизонт» · проект 2026 · команда УЖЦ ОСК · "
     "методика СПбГМТУ", font(26), (176, 190, 212))
e = H.equilibrium(); st = H.initial_stability(); g = SS.equivalent_girder()
rr = St.stresses()
right = [("%.2f м" % e["T"], "осадка в полном грузу"),
         ("%.0f т" % e["D"], "водоизмещение"),
         ("%.2f м" % st["h"], "метацентрическая высота"),
         ("%.0f / %.0f МПа" % (max(x["sigma_deck"] for x in rr["rows"]),
                               rr["sigma_allow"]), "напряжение / допускаемое")]
x = W - 64
for t, s in reversed(right):
    w = max(tw(d, t, font(32, b=True))[0], tw(d, s, font(19))[0])
    text(d, (x, 48), t, font(32, b=True), (255, 255, 255), anchor="ra")
    text(d, (x, 94), s, font(19), (150, 168, 196), anchor="ra")
    x -= w + 56


def fit(path, x, y, w):
    if not os.path.exists(path):
        return y
    im = Image.open(path).convert("RGB")
    s = w / im.width
    im = im.resize((w, int(im.height * s)), Image.LANCZOS)
    img.paste(im, (x, y))
    return y + im.height


y = 226
y = fit(os.path.join(CALC, "01_теоретический_чертёж.png"), 40, y, W - 80) + 18
y = fit(os.path.join(CALC, "02_кривые_элементов.png"), 40, y, W - 80) + 18
y = fit(os.path.join(CALC, "04_остойчивость.png"), 40, y, W - 80) + 18
y = fit(os.path.join(CALC, "06_ходкость.png"), 40, y, W - 80) + 18
y = fit(os.path.join(CALC, "05_продольная_прочность.png"), 40, y, W - 80) + 18
y2 = fit(os.path.join(DRW, "01_мидель_шпангоут.png"), 40, y, (W - 100) // 2)
fit(os.path.join(DRW, "03_кница_спонсона.png"), 60 + (W - 100) // 2, y, (W - 100) // 2)
print("высота получилась", max(y2, y))
img = img.crop((0, 0, W, min(Ht, max(y2, y) + 90)))
d = ImageDraw.Draw(img)
d.rectangle([0, img.size[1] - 70, W, img.size[1]], fill=(18, 30, 48))
text(d, (64, img.size[1] - 52),
     "docs/расчёты/теория_корабля.md · src/lib/gorizont_hydro.py, gorizont_struct.py, "
     "gorizont_strength.py · scripts/расчёты_графики.py",
     font(20), (150, 168, 196))
img.save(os.path.join(R, "лист_расчётов_горизонт.png"))
print("готово", img.size)
