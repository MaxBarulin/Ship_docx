# -*- coding: utf-8 -*-
"""Сводный лист расчётов по теории корабля.

Лист собирается из готовых графиков `renders/горизонт_2026/расчёты/` и растров листов ОР.
Вид простой, как лист, сверстанный вручную: заголовок чёрным, строка ключевых чисел, под
каждым графиком подпись. Высота листа считается по содержимому - при фиксированной высоте
новые, более высокие графики обрезались снизу.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from PIL import Image, ImageDraw, ImageFont
from lib import gorizont_hydro as H, gorizont_strength as St

R = os.path.join(ROOT, "renders", "горизонт_2026")
CALC = os.path.join(R, "расчёты")
DXF = os.path.join(R, "чертежи_dxf")
F = r"C:\Windows\Fonts"
ЧЁРНЫЙ, СЕРЫЙ, ЛИНИЯ = (0, 0, 0), (89, 89, 89), (191, 191, 191)


def font(sz, b=False):
    for имя in (("calibrib.ttf" if b else "calibri.ttf"), ("DejaVuSans-Bold.ttf" if b else "DejaVuSans.ttf")):
        try:
            return ImageFont.truetype(os.path.join(F, имя), sz)
        except OSError:
            continue
    return ImageFont.load_default()


def з(x, nd=2):
    return ("%.*f" % (nd, x)).replace(".", ",")


W, ПОЛЕ, ЗАЗОР = 3400, 40, 40
КОЛ = (W - 2 * ПОЛЕ - ЗАЗОР) // 2
ПОДПИСЬ_H = 56                                   # строка подписи под рисунком

#: (файл, подпись) - подписи те же, что у рисунков приложения А
ШИРОКИЕ = []                                     # во всю ширину - сейчас ничего, чертежи тоже в колонках
ГРАФИКИ = [(os.path.join(CALC, "01_теоретический_чертёж.png"), "Теоретический чертёж"),
           (os.path.join(CALC, "01б_корпус_и_ординаты.png"), "Проекция «корпус» и плазовые ординаты"),
           (os.path.join(CALC, "02_кривые_элементов.png"), "Кривые элементов теоретического чертежа"),
           (os.path.join(CALC, "03_строевая_и_нагрузка.png"), "Строевая по шпангоутам и нагрузка масс"),
           (os.path.join(CALC, "04_остойчивость.png"), "Диаграммы остойчивости"),
           (os.path.join(CALC, "05_продольная_прочность.png"), "Общая продольная прочность"),
           (os.path.join(CALC, "06_ходкость.png"), "Сопротивление и потребная мощность"),
           (os.path.join(CALC, "07_электробаланс.png"), "Электробаланс по режимам")]
#: растры листов ОР-06 и ОР-07 на полколонки выходили почти пустыми - листы идут в пакете отдельно
ЛИСТЫ = []


def открыть(path):
    im = Image.open(path)
    if im.mode in ("RGBA", "LA", "P"):
        im = im.convert("RGBA")
        im = Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)), im)
    return im.convert("RGB")


def высота(path, w):
    with Image.open(path) as im:
        return int(im.height * w / im.width)


# --- раскладка: сначала считаем, где что стоит, потом рисуем ------------------------------------
ШАПКА = 190
места = []                                      # (путь, подпись, x, y, w)
y = ШАПКА
for p, s in ШИРОКИЕ:
    if os.path.exists(p):
        места.append((p, s, ПОЛЕ, y, W - 2 * ПОЛЕ))
        y += высота(p, W - 2 * ПОЛЕ) + ПОДПИСЬ_H + 24
# графики - в две колонки, каждый в ту, что короче (порядок по номерам сохраняется построчно)
колонки = [y, y]
for p, s in ГРАФИКИ:
    if not os.path.exists(p):
        continue
    к = 0 if колонки[0] <= колонки[1] else 1
    места.append((p, s, ПОЛЕ + к * (КОЛ + ЗАЗОР), колонки[к], КОЛ))
    колонки[к] += высота(p, КОЛ) + ПОДПИСЬ_H + 24
y = max(колонки)
низ = y
for к, (p, s) in enumerate(ЛИСТЫ):
    if os.path.exists(p):
        места.append((p, s, ПОЛЕ + к * (КОЛ + ЗАЗОР), y, КОЛ))
        низ = max(низ, y + высота(p, КОЛ) + ПОДПИСЬ_H + 24)
Ht = низ + 20

img = Image.new("RGB", (W, Ht), (255, 255, 255))
d = ImageDraw.Draw(img)
e = H.equilibrium(); st = H.initial_stability(); rr = St.stresses()
d.text((ПОЛЕ, 36), "Теория корабля и прочность", font=font(64, b=True), fill=ЧЁРНЫЙ)
d.text((ПОЛЕ, 116), "«Волжский Горизонт», расчёты по методике СПбГМТУ. Осадка в полном грузу %s м, водоизмещение %.0f т, "
       "метацентрическая высота %s м, напряжение в палубе %.0f МПа при допускаемом %.0f МПа."
       % (з(e["T"]), e["D"], з(st["h"]), max(x["sigma_deck"] for x in rr["rows"]), rr["sigma_allow"]),
       font=font(30), fill=СЕРЫЙ)
d.line([(ПОЛЕ, ШАПКА - 22), (W - ПОЛЕ, ШАПКА - 22)], fill=ЛИНИЯ, width=2)
for p, s, x, y0, w in места:
    im = открыть(p)
    im = im.resize((w, int(im.height * w / im.width)), Image.LANCZOS)
    img.paste(im, (x, y0))
    d.rectangle([x, y0, x + w - 1, y0 + im.height - 1], outline=ЛИНИЯ, width=1)
    d.text((x + w // 2, y0 + im.height + 12), s, font=font(32), fill=ЧЁРНЫЙ, anchor="ma")

путь = os.path.join(R, "лист_расчётов_горизонт.png")
tmp = путь + ".tmp.png"
img.save(tmp)
os.replace(tmp, путь)
print("готово", img.size)
