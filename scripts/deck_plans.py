#!/usr/bin/env python
"""Планы палуб: контур корпуса, зоны, каюты с номерами.

Рисуются из lib.arrangement, то есть из того же источника, из которого
считается пассажировместимость. План не может показать больше кают, чем
записка, потому что и то и другое — одна раскладка.

Обвод корпуса на плане берётся из таблицы шпангоутов, а не рисуется от руки:
нос и корма на плане ровно те, что в 3D-модели.

    python scripts/deck_plans.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from lib import arrangement as ar  # noqa: E402
from lib import ship  # noqa: E402

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
FONT_BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

PX_PER_M = 13.0
MARGIN_X, ROW_GAP, HEADER = 170, 26, 54

INK = "#1a1c1b"
INK_2 = "#5a635f"
PAPER = "#ffffff"
HULL = "#e6e9e6"
HULL_LINE = "#9aa39d"
CORRIDOR = "#f4f2ec"

CATEGORY_COLOR = {
    "econom": "#4E7C99",
    "standard": "#3F8375",
    "business": "#C2A883",
    "lux": "#8E4552",
    "accessible": "#D08A3E",
}
CATEGORY_NAME = {
    "econom": "эконом", "standard": "стандарт",
    "business": "бизнес", "lux": "люкс",
    "accessible": "доступная",
}
KIND_COLOR = {
    "service": "#DED9CE",
    "tech": "#B9BEC2",
    "crew": "#9FB0A8",
    "open": "#D9C293",
}


def mm(value):
    return value / 1000.0 * PX_PER_M


def hull_outline(y_center):
    """Полигон обвода по палубным полуширотам из таблицы шпангоутов."""
    top = [(MARGIN_X + mm(x), y_center - mm(b_deck))
           for x, _, _, b_deck, _, _, _ in ship.STATIONS]
    bottom = [(MARGIN_X + mm(x), y_center + mm(b_deck))
              for x, _, _, b_deck, _, _, _ in reversed(ship.STATIONS)]
    return top + bottom


FURNITURE = "#8d9a9f"
WATER = "#7FB4CE"


def furnish(draw, zone, left, right, y_center, beam_px):
    """Расставить мебель в общественной зоне.

    Пустой прямоугольник с подписью «ресторан» ничего не доказывает: зал на
    сотню мест и зал на двадцать выглядят одинаково. Столы и кресла рисуются
    по реальному шагу посадки, поэтому по плану видно, сколько людей зона
    вмещает — а это следующий вопрос эксперта после «где ресторан».
    """
    name = zone.name.lower()
    top, bottom = y_center - beam_px / 2 + 6, y_center + beam_px / 2 - 6
    width, height = right - left, bottom - top
    if width < 30 or height < 20:
        return

    def grid(step_x, step_y, draw_cell, inset=14):
        x = left + inset
        while x + step_x <= right - inset:
            y = top + inset
            while y + step_y <= bottom - inset:
                draw_cell(x, y)
                y += step_y
            x += step_x

    if "ресторан" in name or "кафе" in name:
        grid(mm(2_600), mm(2_400), lambda x, y: draw.ellipse(
            [x, y, x + mm(1_300), y + mm(1_300)], outline=FURNITURE, width=2))
    elif "бассейн" in name:
        draw.rounded_rectangle([left + width * 0.18, top + height * 0.24,
                                left + width * 0.72, bottom - height * 0.24],
                               radius=12, fill=WATER, outline=FURNITURE)
        for index in range(3):
            x = right - mm(3_200) + index * mm(1_100)
            draw.ellipse([x, y_center - mm(500), x + mm(900),
                          y_center + mm(400)], outline=FURNITURE, width=2)
    elif "бар" in name or "салон" in name or "холл" in name:
        draw.rectangle([left + 16, top + 10, left + 16 + mm(1_000),
                        top + 10 + height * 0.5], fill=FURNITURE)
        grid(mm(2_800), mm(2_600), lambda x, y: draw.ellipse(
            [x, y, x + mm(1_100), y + mm(1_100)], outline=FURNITURE, width=2),
            inset=int(mm(2_600)))
    elif "конференц" in name:
        draw.rectangle([right - 20, top + height * 0.3, right - 12,
                        bottom - height * 0.3], fill=FURNITURE)
        grid(mm(1_100), mm(950), lambda x, y: draw.rectangle(
            [x, y, x + mm(600), y + mm(600)], fill=FURNITURE))
    elif "фитнес" in name or "спа" in name:
        grid(mm(2_000), mm(1_800), lambda x, y: draw.rectangle(
            [x, y, x + mm(1_200), y + mm(800)], outline=FURNITURE, width=2))
    elif "шезлонг" in name or "отдых" in name:
        grid(mm(1_300), mm(2_600), lambda x, y: draw.rectangle(
            [x, y, x + mm(700), y + mm(1_900)], outline=FURNITURE, width=2))
    elif "магазин" in name or "кладов" in name:
        grid(mm(1_600), mm(3_000), lambda x, y: draw.rectangle(
            [x, y, x + mm(900), y + mm(2_400)], fill=FURNITURE))
    elif "боулинг" in name or "бильярд" in name:
        for index in range(4):
            y = top + 12 + index * (height - 24) / 4
            draw.rectangle([left + 18, y, right - 18, y + (height - 24) / 4 - 6],
                           outline=FURNITURE, width=2)
    elif "вестибюль" in name or "ресепшн" in name:
        draw.rectangle([left + 18, y_center - mm(700), left + 18 + mm(4_000),
                        y_center + mm(700)], fill=FURNITURE)
    elif "камбуз" in name:
        grid(mm(2_200), mm(2_000), lambda x, y: draw.rectangle(
            [x, y, x + mm(1_600), y + mm(900)], fill=FURNITURE))
    elif "экипаж" in name:
        grid(mm(2_600), mm(2_800), lambda x, y: draw.rectangle(
            [x, y, x + mm(2_200), y + mm(2_400)], outline=FURNITURE, width=2))
    elif "машинное" in name:
        for dy in (-1, 1):
            draw.rectangle([left + width * 0.15, y_center + dy * mm(2_600)
                            - mm(1_200), left + width * 0.55,
                            y_center + dy * mm(2_600) + mm(1_200)],
                           outline=FURNITURE, width=2)
    elif "спортивная" in name:
        draw.rectangle([left + 20, top + 14, right - 20, bottom - 14],
                       outline=FURNITURE, width=2)


def fit_label(draw, text, left, right, y_center, fonts, height=None):
    """Подписать зону так, чтобы подпись читалась и в узком отсеке.

    Сначала пробуем вписать в строку, затем уменьшенным шрифтом, затем в две
    строки по словам, и лишь совсем узкие отсеки подписываются вертикально —
    иначе половина технических помещений на нижней палубе остаётся безымянной.
    """
    room = (right - left) - 8
    for font_key in ("zone", "small"):
        font = fonts[font_key]
        box = draw.textbbox((0, 0), text, font=font)
        if box[2] - box[0] <= room:
            draw.text(((left + right) / 2 - (box[2] - box[0]) / 2,
                       y_center - (box[3] - box[1]) / 2), text,
                      fill=INK, font=font)
            return

    words = text.split()
    for split in range(len(words) - 1, 0, -1):
        lines = [" ".join(words[:split]), " ".join(words[split:])]
        widths = [draw.textbbox((0, 0), line, font=fonts["small"])[2]
                  for line in lines]
        if max(widths) <= room:
            for i, line in enumerate(lines):
                draw.text(((left + right) / 2 - widths[i] / 2,
                           y_center - 15 + i * 16), line,
                          fill=INK, font=fonts["small"])
            return

    # вертикальная подпись обязана уместиться в высоту палубы, иначе она
    # вылезет на соседнюю строку листа и прочтётся как чужая
    limit = int(height) if height else 200
    text_width = int(draw.textlength(text, font=fonts["small"]))
    while text_width > limit and len(text) > 4:
        text = text[:-2] + "…"
        text_width = int(draw.textlength(text, font=fonts["small"]))
    image = Image.new("RGBA", (text_width + 8, 20), (0, 0, 0, 0))
    ImageDraw.Draw(image).text((0, 0), text, fill=INK, font=fonts["small"])
    turned = image.rotate(90, expand=True)
    draw._image.paste(turned,
                      (int((left + right) / 2 - turned.width / 2),
                       int(y_center - turned.height / 2)), turned)


def draw_deck(draw, deck_name, y_center, fonts):
    name, number, level, x0, available = ar.deck(deck_name)

    draw.polygon(hull_outline(y_center), fill=HULL, outline=HULL_LINE)

    beam = ship.SUPERSTRUCTURE_BEAM
    depth = ship.CABIN_DEPTH

    for zone in ar.place(deck_name):
        left = MARGIN_X + mm(zone.x0)
        right = left + mm(zone.length)
        if right <= left + 1:
            continue

        if zone.kind == "cabins":
            # два коридора вдоль бортов и центральный блок между ними
            for sign in (-1, 1):
                edges = sorted((y_center + sign * mm(ship.CENTRE_EDGE),
                                y_center + sign * mm(ship.CORRIDOR_EDGE)))
                draw.rectangle([left, edges[0], right, edges[1]],
                               fill=CORRIDOR, outline=HULL_LINE)
            draw.rectangle([left, y_center - mm(ship.CENTRE_EDGE),
                            right, y_center + mm(ship.CENTRE_EDGE)],
                           fill=KIND_COLOR["tech"], outline=HULL_LINE)
        else:
            draw.rectangle([left, y_center - mm(beam / 2),
                            right, y_center + mm(beam / 2)],
                           fill=KIND_COLOR[zone.kind], outline=HULL_LINE)
            furnish(draw, zone, left, right, y_center, mm(beam))
            fit_label(draw, zone.name, left, right, y_center, fonts,
                      height=mm(beam) - 14)

    for cabin in ar.cabin_numbers(deck_name):
        left = MARGIN_X + mm(cabin["x0"])
        right = left + mm(cabin["width"])
        near = mm(ship.CORRIDOR_EDGE)
        far = mm(ship.CABIN_EDGE)
        top, bottom = ((y_center - far, y_center - near)
                       if cabin["side"] == "левый"
                       else (y_center + near, y_center + far))
        draw.rectangle([left + 1, top, right - 1, bottom],
                       fill=CATEGORY_COLOR[cabin["category"]], outline="#ffffff")
        text = str(cabin["number"])
        box = draw.textbbox((0, 0), text, font=fonts["cabin"])
        if box[2] - box[0] < (right - left) - 4:
            draw.text(((left + right) / 2 - (box[2] - box[0]) / 2,
                       (top + bottom) / 2 - (box[3] - box[1]) / 2 - 2),
                      text, fill="#ffffff", font=fonts["cabin"])

    cabins = ar.cabin_numbers(deck_name)
    title = f"{name.capitalize()} палуба ({number})"
    draw.text((18, y_center - mm(beam / 2) - 28), title,
              fill=INK, font=fonts["title"])
    note = f"{level / 1000:.1f} м от ОП"
    if cabins:
        note += f"  ·  {len(cabins)} кают  ·  {len(cabins) * 2} мест"
    draw.text((18, y_center - mm(beam / 2) - 6), note,
              fill=INK_2, font=fonts["note"])


def legend(draw, y, fonts):
    x = MARGIN_X
    draw.text((18, y - 4), "Обозначения", fill=INK, font=fonts["title"])
    items = [(CATEGORY_COLOR[c], f"{CATEGORY_NAME[c]} · {ship.clear_area(c):.1f} м²")
             for c in ("econom", "standard", "business", "lux", "accessible")]
    items += [(KIND_COLOR["service"], "общественные помещения"),
              (KIND_COLOR["open"], "открытые палубы"),
              (KIND_COLOR["crew"], "экипаж"),
              (KIND_COLOR["tech"], "технические помещения")]
    for color, text in items:
        draw.rectangle([x, y, x + 26, y + 16], fill=color, outline=HULL_LINE)
        draw.text((x + 34, y + 1), text, fill=INK_2, font=fonts["note"])
        x += 34 + draw.textbbox((0, 0), text, font=fonts["note"])[2] + 30


def main():
    fonts = {
        "title": ImageFont.truetype(FONT_BOLD, 19),
        "note": ImageFont.truetype(FONT, 14),
        "zone": ImageFont.truetype(FONT, 13),
        "cabin": ImageFont.truetype(FONT, 10),
        "small": ImageFont.truetype(FONT, 11),
        "head": ImageFont.truetype(FONT_BOLD, 30),
    }
    row = mm(ship.HULL_BEAM) + ROW_GAP + 34
    width = int(MARGIN_X * 2 + mm(ship.HULL_LENGTH))
    height = int(HEADER + row * len(ar.DECKS) + 90)

    image = Image.new("RGB", (width, height), PAPER)
    draw = ImageDraw.Draw(image)
    draw._image = image  # нужен для вклейки повёрнутых подписей

    summary = ar.summary()
    draw.text((18, 14), "Общее расположение", fill=INK, font=fonts["head"])
    draw.text((width - 700, 24),
              f"{summary['cabins']} кают · {summary['passengers']} пассажиров · "
              f"экипаж {summary['crew']} · {len(ar.DECKS)} палуб",
              fill=INK_2, font=fonts["note"])

    for index, (name, *_rest) in enumerate(ar.DECKS[::-1]):
        y = HEADER + row * index + row / 2
        draw_deck(draw, name, y, fonts)

    # где нос, а где корма — на плане это не очевидно, а спрашивают всегда
    bottom = HEADER + row * len(ar.DECKS) - 6
    draw.text((MARGIN_X, bottom), "КОРМА", fill=INK_2, font=fonts["note"])
    draw.text((width - MARGIN_X - 46, bottom), "НОС", fill=INK_2,
              font=fonts["note"])

    legend(draw, HEADER + row * len(ar.DECKS) + 20, fonts)

    out = ROOT / "renders" / "палубы_общее_расположение.png"
    out.parent.mkdir(exist_ok=True)
    image.save(out)
    print(f"план: {out.relative_to(ROOT)}  {image.size[0]}x{image.size[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
