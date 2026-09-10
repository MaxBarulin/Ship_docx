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
}
CATEGORY_NAME = {
    "econom": "эконом", "standard": "стандарт",
    "business": "бизнес", "lux": "люкс",
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
    corridor_half = ship.CORRIDOR_WIDTH / 2

    for zone in ar.place(deck_name):
        left = MARGIN_X + mm(zone.x0)
        right = left + mm(zone.length)
        if right <= left + 1:
            continue

        if zone.kind == "cabins":
            draw.rectangle([left, y_center - mm(corridor_half),
                            right, y_center + mm(corridor_half)],
                           fill=CORRIDOR, outline=HULL_LINE)
        else:
            draw.rectangle([left, y_center - mm(beam / 2),
                            right, y_center + mm(beam / 2)],
                           fill=KIND_COLOR[zone.kind], outline=HULL_LINE)
            fit_label(draw, zone.name, left, right, y_center, fonts,
                      height=mm(beam) - 14)

    for cabin in ar.cabin_numbers(deck_name):
        left = MARGIN_X + mm(cabin["x0"])
        right = left + mm(cabin["width"])
        near = mm(corridor_half)
        far = mm(corridor_half + depth)
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
             for c in ("econom", "standard", "business", "lux")]
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
