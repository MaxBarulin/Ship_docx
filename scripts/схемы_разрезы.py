# -*- coding: utf-8 -*-
"""Схемы: продольный разрез по ДП и судовые системы.

Сырой ортогональный разрез рендерит Blender (камера SEC_CAM, борт, ortho 146,
2400 x 470, ближняя плоскость по ДП). Подписи берутся из gorizont_ga и
gorizont_mach, поэтому не расходятся с моделью.

    python scripts/схемы_разрезы.py [папка_с_сырым_разрезом]
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from PIL import Image, ImageDraw, ImageFont
import matplotlib
from lib import gorizont as G
from lib import gorizont_roll as _roll
from lib import gorizont_autonomy as _auto, gorizont_ga as GA, gorizont_hydro as H, gorizont_mach as M

RAW = sys.argv[1] if len(sys.argv) > 1 else r"F:\Temp\claude\gor\схемы_raw"
OUT = os.path.join(ROOT, "renders", "горизонт_2026", "схемы")
os.makedirs(OUT, exist_ok=True)
FDIR = os.path.join(os.path.dirname(matplotlib.__file__), "mpl-data", "fonts", "ttf")
def font(sz, b=False, i=False):
    n = "DejaVuSans-Bold.ttf" if b else ("DejaVuSans-Oblique.ttf" if i else "DejaVuSans.ttf")
    return ImageFont.truetype(os.path.join(FDIR, n), sz)

INK, INK2 = (24, 34, 52), (86, 98, 120)
ACC, SEA, GREEN, LINE = (176, 38, 52), (28, 92, 138), (24, 116, 84), (150, 160, 176)
EL, VENT, WAT, SEW, FIRE, STEAM = ((198, 124, 12), (52, 140, 196), (32, 150, 140),
                                   (126, 96, 168), (198, 54, 54), (206, 76, 24))
ROLL = (18, 108, 92)          # успокоение качки и её раннее предупреждение
AUTO = (92, 64, 148)          # автономное управление и расхождение
PPM = 2400 / 146.0
# Поле слева под отметками палуб: раньше подписи ярусов ложились прямо на
# модель и мешались с выносками. Схемы выставляют PADX перед отрисовкой.
PADX = 0
GUT = 292                # ширина левого поля отметок, px
RGUT = 300               # правое поле: ватерлиния и габаритная высота
def px(X): return PADX + 1200 + (X - 69.5) * PPM
def szz(Z): return 235 - (Z - 7.2) * PPM
T = H.equilibrium()["T"]


def tw(d, s, f):
    b = d.textbbox((0, 0), s, font=f)
    return b[2] - b[0], b[3] - b[1]


BOXES = []               # прямоугольники всех подписей для проверки наложений


def label(d, x, y, s, f, fill=INK, pad=4, track=True):
    w, h = tw(d, s, f)
    r = (x - w / 2 - pad, y - h / 2 - pad - 1, x + w / 2 + pad, y + h / 2 + pad + 1)
    d.rectangle(list(r), fill=(255, 255, 255))
    d.text((x, y), s, font=f, fill=fill, anchor="mm")
    if track:
        BOXES.append((r, s))


def level_label(d, y, s, f, fill=INK2, pad=5):
    """Отметка в левом поле, выключка вправо к корме судна."""
    w, h = tw(d, s, f)
    x1 = px(0) - 12
    r = (x1 - w - pad, y - h - pad - 2, x1 + pad, y + pad + 2)
    d.rectangle(list(r), fill=(255, 255, 255))
    d.text((x1, y), s, font=f, fill=fill, anchor="rs")
    BOXES.append((r, s))


def level_label_r(d, y, s, f, fill=INK2, pad=5):
    """Отметка в правом поле, за носом: ватерлиния и габаритная высота
    иначе ложатся на отметки палуб — между 1,40 и 2,22 м всего 13 px."""
    w, h = tw(d, s, f)
    x0 = px(G.LOA) + 12
    r = (x0 - pad, y - h - pad - 2, x0 + w + pad, y + pad + 2)
    d.rectangle(list(r), fill=(255, 255, 255))
    d.text((x0, y), s, font=f, fill=fill, anchor="ls")
    BOXES.append((r, s))


def collisions(tol=2):
    """Наезжающие друг на друга подписи."""
    bad = []
    for i in range(len(BOXES)):
        (a, sa) = BOXES[i]
        for j in range(i + 1, len(BOXES)):
            (b, sb) = BOXES[j]
            if (a[0] < b[2] - tol and b[0] < a[2] - tol
                    and a[1] < b[3] - tol and b[1] < a[3] - tol):
                bad.append((sa, sb))
    return bad


def leader(d, x0, y0, x1, y1, fill=LINE, w=1):
    d.line([x0, y0, x1, y1], fill=fill, width=w)
    d.ellipse([x0 - 2.5, y0 - 2.5, x0 + 2.5, y0 + 2.5], fill=fill)


def header(img, title, sub, right):
    d = ImageDraw.Draw(img)
    W = img.size[0]
    d.rectangle([0, 0, W, 86], fill=(246, 248, 251))
    d.line([0, 86, W, 86], fill=(206, 214, 226), width=2)
    d.text((46, 20), title, font=font(36, b=True), fill=INK)
    d.text((46, 62), sub, font=font(20), fill=INK2)
    d.text((W - 46, 26), right, font=font(19), fill=INK2, anchor="ra")
    d.text((W - 46, 56), "«Волжский Горизонт» · проект 2026", font=font(19), fill=INK2, anchor="ra")
    return d


def ruler(d, y):
    d.line([px(0), y, px(G.LOA), y], fill=INK2, width=2)
    f = font(16)
    for i in range(0, 15):
        X = i * 10.0
        d.line([px(X), y - 6, px(X), y + 6], fill=INK2, width=2)
        d.text((px(X), y + 10), "%d" % X, font=f, fill=INK2, anchor="ma")
    d.text((px(0), y - 14), "м от кормового перпендикуляра", font=f, fill=INK2, anchor="ls")
    d.line([px(126), y - 46, px(133), y - 46], fill=INK2, width=3)
    d.polygon([(px(133) + 14, y - 46), (px(133), y - 52), (px(133), y - 40)], fill=INK2)
    d.text((px(126) - 10, y - 46), "нос", font=font(17), fill=INK2, anchor="rm")


def place(d, items, f, off, imh, gap=30):
    """Раскладка выносок в строки без наложений.

    Строка подбирается так, чтобы не пересекалась ни сама подпись, ни её
    выноска: выноска идёт от модели через все строки до своей, и если в
    строке ближе к модели стоит подпись, выноска перечеркнёт её текст.
    """
    rows_up, rows_dn = [], []
    for (X, Z, s, side, col) in sorted(items, key=lambda r: r[0]):
        ax, ay = px(X), szz(Z) + off
        w = tw(d, s, f)[0]
        iv = (ax - w / 2 - 14, ax + w / 2 + 14)
        rows = rows_up if side == "up" else rows_dn
        k = 0
        while True:
            if k >= len(rows):
                rows.append([])
            free = all(iv[1] < a or iv[0] > b for (a, b) in rows[k])
            crossed = any(a - 6 <= ax <= b + 6
                          for j in range(k) for (a, b) in rows[j])
            if free and (not crossed or k >= 3):
                rows[k].append(iv)
                break
            k += 1
        if side == "up":
            y = off - 16 - k * gap
            leader(d, ax, ay, ax, y + 12, fill=col, w=2 if col != LINE else 1)
        else:
            y = off + imh + 16 + k * gap
            leader(d, ax, ay, ax, y - 12, fill=col, w=2 if col != LINE else 1)
        label(d, ax, y, s, f, col)
    return len(rows_up), len(rows_dn)


DECK_Z = {"первая": 1.40, "главная": 4.20, "верхняя": 7.00,
          "шлюпочная": 9.80, "солнечная": 12.60}


def section_items():
    items, seen = [], {"Машинное отделение"}
    for key, zones in GA.DECKS.items():
        z0 = DECK_Z.get(key)
        if z0 is None:
            continue
        side = "dn" if key == "первая" else "up"
        big = sorted(zones, key=lambda z: z[1] - z[0], reverse=True)[:4]
        for x0, x1, kind, name, cap, area in big:
            short = name.split(",")[0].split("(")[0].strip()
            if short in seen or x1 - x0 < 4.0:
                continue
            seen.add(short)
            items.append((0.5 * (x0 + x1), z0 + 1.2, short, side, LINE))
    items += [
        (0.5 * (M.MO_X0 + M.MO_X1), 1.9,
         "Машинное отделение · %d ГДГ по %d кВт" % (G.DG_COUNT, G.DG_POWER), "dn", ACC),
        (10.0, 1.2, "ГЭД %d × %d кВт, ВФШ в насадках Корт"
         % (G.PROP_MOTOR_COUNT, G.PROP_MOTOR_POWER), "dn", ACC),
        (G.THRUSTERS["носовое"]["x"], 0.9, "Носовое ПУ %d кВт" % G.THRUSTER_POWER, "dn", ACC),
        (G.THRUSTERS["кормовое"]["x"], 0.9, "Кормовое ПУ %d кВт" % G.THRUSTER_POWER, "dn", ACC),
        (58.0, 0.7, "Цистерны второго дна · %d шт., %.0f м³"
         % (len(G.TANKS), G.tank_summary()["vol"]), "dn", GREEN),
        (119.0, 15.2, "Мачта заваливается перед мостами", "up", LINE),
        (11.5, 10.5, "Дымовые шахты и трубы", "up", LINE),
    ]
    return items


def section():
    global PADX
    PADX, BOXES[:] = GUT, []
    im = Image.open(os.path.join(RAW, "разрез.png")).convert("RGBA")
    im = Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)),
                               im).convert("RGB")
    W, HI = im.size
    items = section_items()
    f = font(19)
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    nu, nd = place(probe, items, f, 0, HI)
    BOXES[:] = []          # пробный проход в учёт наложений не идёт
    TOP, BOT = 40 + nu * 30, 60 + nd * 30 + 110
    img = Image.new("RGB", (W + GUT + RGUT, 86 + TOP + HI + BOT), "white")
    img.paste(im, (GUT, 86 + TOP))
    off = 86 + TOP
    d = header(img, "Продольный разрез по диаметральной плоскости",
               "Четыре закрытых яруса, машинное отделение, мачта и габаритная высота",
               "Схемы · М 1:250 (A2)")
    fs = font(17)
    for key, z in DECK_Z.items():
        y = szz(z) + off
        d.line([px(0) - 10, y, px(G.LOA), y], fill=(196, 206, 220), width=1)
        level_label(d, y - 4, "%s палуба %.2f" % (key, z), fs)
    y = szz(T) + off
    d.line([px(0) - 10, y, px(G.LOA) + 10, y], fill=SEA, width=2)
    level_label_r(d, y - 5, "ВЛ · осадка %.2f м" % T, fs, SEA)
    y = szz(T + G.AIR_DRAFT) + off
    d.line([px(0) - 10, y, px(G.LOA) + 10, y], fill=ACC, width=2)
    level_label_r(d, y - 5, "габаритная высота %.1f м от ВЛ" % G.AIR_DRAFT, fs, ACC)
    place(d, items, f, off, HI)
    ruler(d, 86 + TOP + HI + BOT - 80)
    p = os.path.join(OUT, "продольный_разрез.png")
    img.save(p)
    return p


def systems():
    global PADX
    PADX, BOXES[:] = GUT, []
    im = Image.open(os.path.join(RAW, "разрез.png")).convert("RGBA")
    im = Image.alpha_composite(Image.new("RGBA", im.size, (255, 255, 255, 255)),
                               im).convert("RGB")
    W, HI = im.size
    items = [
        (0.5 * (M.MO_X0 + M.MO_X1), 1.9, "%d ГДГ по %d кВт" % (G.DG_COUNT, G.DG_POWER), "dn", EL),
        (32.0, 0.6, "ГРЩ %d В и батарея %d кВт·ч" % (G.SWITCHBOARD_V, G.BATTERY_KWH), "dn", EL),
        (9.6, 1.9, "%d ГЭД по %d кВт" % (G.PROP_MOTOR_COUNT, G.PROP_MOTOR_POWER), "dn", EL),
        (83.5, 12.9, "Солнечные батареи, 44 модуля", "up", EL),
        (12.5, 9.3, "Шахты дымоходов и ОВК", "up", VENT),
        (66.0, 12.1, "Кондиционирование по ярусам", "up", VENT),
        (69.0, 0.95, "Станция пресной воды", "dn", WAT),
        (31.5, 1.2, "AWTS: МБР, биоблок, УФ", "dn", SEW),
        (28.0, 2.6, "Котёл %d…%d бар и теплообменник"
         % (G.BOILER["pressure_bar"][0], G.BOILER["pressure_bar"][1]), "up", STEAM),
        (G.THRUSTERS["носовое"]["x"], 0.8, "Носовое ПУ %d кВт" % G.THRUSTER_POWER, "dn", EL),
        (G.THRUSTERS["кормовое"]["x"], 1.2, "Кормовое ПУ %d кВт" % G.THRUSTER_POWER, "dn", EL),
        (52.0, 0.25, "Успокоительная цистерна, кормовая пара", "dn", ROLL),
        (90.0, 0.25, "Успокоительная цистерна, носовая пара", "dn", ROLL),
        (121.0, 15.6, "Волномерный радар и метеостанция", "up", ROLL),
        (121.0, 12.6, "MRU, гирокомпас, вычислитель качки", "up", ROLL),
        (124.0, 16.2, "Радары X и S, АИС, тепловизоры", "up", AUTO),
        (118.0, 12.9, "Вычислитель автономного управления", "up", AUTO),
        (128.0, 5.2, "Лидар и камеры кругового обзора", "up", AUTO),
    ]
    probe = ImageDraw.Draw(Image.new("RGB", (10, 10)))
    nu, nd = place(probe, items, font(19), 0, HI)
    BOXES[:] = []
    HDR, BOT = 86, 60 + nd * 30 + 8 * 32 + 70
    TOP = 40 + nu * 30
    img = Image.new("RGB", (W + GUT + RGUT, HDR + TOP + HI + BOT), "white")
    img.paste(im, (GUT, HDR + TOP))
    off = HDR + TOP
    d = header(img, "Судовые системы",
               "Энергетика, ОВК, пресная вода и стоки, пар и утилизация тепла, пожарные зоны",
               "Схемы · М 1:250 (A2)")

    def run(pts, col, w=5):
        for i in range(len(pts) - 1):
            (x0, z0), (x1, z1) = pts[i], pts[i + 1]
            d.line([px(x0), szz(z0) + off, px(x1), szz(z1) + off], fill=col, width=w)

    run([(32, 1.9), (9.6, 1.9)], EL); run([(32, 1.9), (124, 1.9)], EL)
    for x in (36.8, 94.8):
        run([(x, 1.9), (x, 12.3)], EL)
    run([(75, 12.9), (92, 12.9)], EL)
    run([(32, 1.9), (32, 0.9)], EL)
    run([(G.THRUSTERS["носовое"]["x"], 1.9), (G.THRUSTERS["носовое"]["x"], 0.8)], EL, 4)
    run([(G.THRUSTERS["кормовое"]["x"], 1.9), (G.THRUSTERS["кормовое"]["x"], 1.2)], EL, 4)
    for z in (6.5, 9.3, 12.1):
        run([(12.5, z), (126, z)], VENT, 4)
    run([(12.5, 6.5), (12.5, 12.1)], VENT, 4)
    run([(69, 0.95), (69, 2.0)], WAT, 4)
    run([(69, 2.0), (36.8, 2.0)], WAT, 4); run([(69, 2.0), (94.8, 2.0)], WAT, 4)
    for x in (36.8, 94.8):
        run([(x, 2.0), (x, 11.6)], WAT, 4)
    for z in (4.6, 7.4, 10.2):
        run([(36.8, z), (94.8, z)], WAT, 3)
    for z in (4.4, 7.2, 10.0):
        run([(36.0, z), (95.6, z)], SEW, 3)
    for x in (36.0, 95.6):
        run([(x, 4.4), (x, 1.2)], SEW, 3)
    run([(36.0, 1.2), (31.5, 1.2)], SEW, 4); run([(95.6, 1.2), (78, 1.2)], SEW, 4)
    run([(78, 1.2), (31.5, 1.2)], SEW, 4)
    run([(28.0, 2.6), (12.5, 2.6)], STEAM, 4)
    run([(28.0, 2.6), (28.0, 1.2)], STEAM, 4)
    run([(28.0, 2.6), (44.0, 2.6)], STEAM, 4)
    # успокоение качки: ветви цистерн у бортов и перепускные каналы
    for a, b in ((46.0, 58.0), (84.0, 96.0)):
        run([(a, 0.25), (b, 0.25)], ROLL, 6)
    run([(52.0, 0.25), (52.0, 1.9)], ROLL, 3)
    run([(90.0, 0.25), (90.0, 1.9)], ROLL, 3)
    run([(52.0, 1.9), (90.0, 1.9)], ROLL, 3)
    run([(90.0, 1.9), (121.0, 1.9)], ROLL, 3)
    run([(121.0, 1.9), (121.0, 12.6)], ROLL, 3)
    # автономное управление: датчики в носу и на мачте, шина к рубке и
    # к движителям
    run([(128.0, 5.2), (121.0, 5.2)], AUTO, 3)
    run([(121.0, 5.2), (121.0, 12.9)], AUTO, 3)
    run([(124.0, 16.2), (124.0, 12.9)], AUTO, 3)
    run([(121.0, 12.9), (124.0, 12.9)], AUTO, 3)
    run([(121.0, 12.9), (121.0, 2.4)], AUTO, 3)
    run([(121.0, 2.4), (10.0, 2.4)], AUTO, 3)
    run([(102.0, 2.4), (102.0, 1.2)], AUTO, 2)
    for x in (34.0, 60.0, 92.0, 116.0):
        d.line([px(x), szz(0.2) + off, px(x), szz(12.9) + off], fill=FIRE, width=3)
        d.text((px(x), szz(13.6) + off), "ГВПЗ", font=font(15, b=True), fill=FIRE, anchor="ms")
    place(d, items, font(19), off, HI)
    ly = HDR + TOP + HI + BOT - 8 * 32 - 40
    LEG = [(EL, "электроэнергия: %d × %d кВт ГДГ, ГРЩ %d В, %d × %d кВт ГЭД, батарея %d кВт·ч, солнечные модули"
            % (G.DG_COUNT, G.DG_POWER, G.SWITCHBOARD_V, G.PROP_MOTOR_COUNT,
               G.PROP_MOTOR_POWER, G.BATTERY_KWH)),
           (VENT, "вентиляция и кондиционирование: шахты в корме, магистрали по подволокам ярусов"),
           (WAT, "пресная вода: %.0f м³ запаса, станция подготовки, стояки в трап-холлах" % G.FRESH_WATER_M3),
           (SEW, "сточные воды: вакуумная система, AWTS с МБР и УФ, нулевой сброс в акваторию"),
           (STEAM, "пар и тепло: утилизация ВТ-контура ГДГ, один центральный пластинчатый теплообменник"),
           (FIRE, "главные вертикальные противопожарные зоны — 5 зон, шпации 34 / 60 / 92 / 116"),
           (ROLL, "качка: волномерный радар, MRU и гирокомпас, две пассивные "
                  "успокоительные цистерны %.1f т, настройка на период %.2f с"
                  % (_roll.water()["mass"], _roll.tank_period())),
           (AUTO, "автономное управление: радары X и S, АИС, лидар, камеры и "
                  "тепловизоры; расхождение по ППВВП, обнаружение с %.0f м "
                  "при тормозном пути %.0f м"
                  % (_auto.reaction()["required"],
                     _auto.stopping()["distance"]))]
    for i, (c, t) in enumerate(LEG):
        y = ly + i * 32
        d.line([60, y, 110, y], fill=c, width=5)
        d.text((126, y - 11), t, font=font(19), fill=INK)
    for z, nm in ((1.40, "первая"), (4.20, "главная"), (7.00, "верхняя"),
                  (9.80, "шлюпочная"), (12.60, "солнечная")):
        level_label(d, szz(z) + off - 4, "%s %.2f" % (nm, z), font(17))
    p = os.path.join(OUT, "судовые_системы.png")
    img.save(p)
    return p


if __name__ == "__main__":
    for fn in (section, systems):
        p = fn()
        bad = collisions()
        print(os.path.basename(p),
              "— подписи не пересекаются" if not bad
              else "!! наложений: %d  %s" % (len(bad), bad[:4]))
