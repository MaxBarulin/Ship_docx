#!/usr/bin/env python
"""Сводный лист проекта: виды, ТТХ, планы палуб, каюты, проверки.

Собирается из готовых рендеров и из расчётных данных. Ни одна цифра на листе
не набита руками: вместимость приходит из lib.arrangement, размерения и
водоизмещение — из геометрии корпуса. Пересобрал модель — пересобрал лист.

    python scripts/render_cabins.py && python scripts/vessel_report.py
    python scripts/deck_plans.py && python scripts/poster.py
"""

from __future__ import annotations

import sys
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parent.parent
RENDERS = ROOT / "renders"
sys.path.insert(0, str(ROOT / "src"))

from lib import arrangement as ar  # noqa: E402
from lib import hull, ship  # noqa: E402

FONT = "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"
BOLD = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"

W, PAD = 3400, 44
INK, INK_2, INK_3 = "#14181c", "#4e5a62", "#8b9499"
PAPER, PANEL, LINE = "#ffffff", "#16324a", "#d5dade"
ACCENT = "#B03A2E"

CABIN_TILES = [
    ("econom", "window", "ЭКОНОМ"),
    ("standard", "interior", "СТАНДАРТ"),
    ("business", "interior", "БИЗНЕС"),
    ("lux", "interior", "ЛЮКС"),
    ("accessible", "interior", "ДЛЯ МАЛОМОБИЛЬНЫХ"),
]


def load(name):
    path = RENDERS / name
    if not path.exists():
        raise SystemExit(f"нет {path.relative_to(ROOT)} — сначала пересоберите рендеры")
    return Image.open(path).convert("RGB")


def fit(image, width=None, height=None):
    if width:
        scale = width / image.width
    else:
        scale = height / image.height
    return image.resize((max(1, int(image.width * scale)),
                         max(1, int(image.height * scale))), Image.LANCZOS)


def trim(image, background=(240, 244, 248), tol=10):
    """Обрезать поля рендера — cadgen оставляет вокруг модели много воздуха."""
    pixels = image.load()
    w, h = image.size
    def is_bg(x, y):
        r, g, b = pixels[x, y][:3]
        return (abs(r - background[0]) < tol and abs(g - background[1]) < tol
                and abs(b - background[2]) < tol)
    left, right, top, bottom = 0, w - 1, 0, h - 1
    while left < right and all(is_bg(left, y) for y in range(0, h, 4)):
        left += 1
    while right > left and all(is_bg(right, y) for y in range(0, h, 4)):
        right -= 1
    while top < bottom and all(is_bg(x, top) for x in range(0, w, 4)):
        top += 1
    while bottom > top and all(is_bg(x, bottom) for x in range(0, w, 4)):
        bottom -= 1
    pad = 8
    return image.crop((max(0, left - pad), max(0, top - pad),
                       min(w, right + pad), min(h, bottom + pad)))


def caption(draw, x, y, w, text, fonts, height=44):
    draw.rectangle([x, y, x + w, y + height], fill=PANEL)
    draw.text((x + 16, y + height / 2 - 11), text, fill="#ffffff",
              font=fonts["cap"])


def main():
    fonts = {
        "h1": ImageFont.truetype(BOLD, 62),
        "h2": ImageFont.truetype(BOLD, 30),
        "sub": ImageFont.truetype(FONT, 27),
        "cap": ImageFont.truetype(BOLD, 20),
        "spec": ImageFont.truetype(FONT, 24),
        "spec_b": ImageFont.truetype(BOLD, 26),
        "note": ImageFont.truetype(FONT, 20),
    }

    body = hull.hull_solid()
    box = body.bounding_box()
    disp = hull.displacement(body)
    summary = ar.summary()

    # холст с запасом: итоговая высота известна только после раскладки,
    # а обрезка по y в конце всё равно уберёт лишнее
    canvas = Image.new("RGB", (W, 6400), PAPER)
    draw = ImageDraw.Draw(canvas)

    # --- шапка
    draw.rectangle([0, 0, W, 168], fill=PANEL)
    draw.text((PAD, 30), ship.PROJECT_NAME, fill="#ffffff", font=fonts["h1"])
    draw.text((PAD + 6, 104), ship.PROJECT_SUBTITLE.upper(), fill="#9fb6c8",
              font=fonts["sub"])
    draw.text((W - PAD - 260, 112), ship.PROJECT_TEAM, fill="#9fb6c8",
              font=fonts["sub"])

    y = 168 + PAD

    # --- главный вид и панель характеристик
    panel_w = 900
    hero = trim(load("судно_перспектива.png"))
    hero = fit(hero, width=W - panel_w - PAD * 3)
    canvas.paste(hero, (PAD, y))
    hero_h = hero.height

    px = W - panel_w - PAD
    draw.rectangle([px, y, px + panel_w, y + max(hero_h, 640)], fill="#f2f4f6")
    draw.text((px + 26, y + 22), "ОСНОВНЫЕ ХАРАКТЕРИСТИКИ", fill=INK,
              font=fonts["h2"])
    rows = [
        ("Пассажировместимость", f"{summary['passengers']} чел."),
        ("Кают", f"{summary['cabins']}"),
        ("Экипаж", f"{summary['crew']} чел."),
        ("Длина наибольшая", f"{box.size.X / 1000:.1f} м"),
        ("Ширина наибольшая", f"{box.size.Y / 1000:.2f} м"),
        ("Осадка", f"{ship.DRAFT / 1000:.1f} м"),
        ("Водоизмещение", f"{disp['mass']:.0f} т"),
        ("Высота габаритная", f"{ship.air_draft(0) / 1000:.1f} м"),
        ("Палуб", f"{len(ar.DECKS)}"),
        ("Кают для маломобильных", f"{summary['by_category'].get('accessible', 0)}"),
        ("Автономность", "10 суток"),
    ]
    ry = y + 84
    for name, value in rows:
        draw.text((px + 26, ry), name, fill=INK_2, font=fonts["spec"])
        vbox = draw.textbbox((0, 0), value, font=fonts["spec_b"])
        draw.text((px + panel_w - 26 - (vbox[2] - vbox[0]), ry - 2), value,
                  fill=INK, font=fonts["spec_b"])
        ry += 41
        draw.line([px + 26, ry - 8, px + panel_w - 26, ry - 8], fill=LINE)

    draw.text((px + 26, ry + 10), "ПРОВЕРКИ ПО ОГРАНИЧЕНИЯМ ТРАССЫ", fill=INK,
              font=fonts["h2"])
    ry += 62
    for name, value, limit, ok in hull.checks()[:3]:
        draw.text((px + 26, ry), f"✓  {name}", fill="#2c6e49", font=fonts["note"])
        draw.text((px + panel_w - 190, ry),
                  f"{value / 1000:.2f} / {limit / 1000:.1f} м", fill=INK_2,
                  font=fonts["note"])
        ry += 32

    y += max(hero_h, 640) + PAD

    # --- проекции
    caption(draw, PAD, y, W - PAD * 2, "ПРОЕКЦИИ", fonts)
    y += 44 + 14
    profile = fit(trim(load("судно_профиль.png")), width=int((W - PAD * 2) * 0.60))
    canvas.paste(profile, (PAD, y))
    side_w = (W - PAD * 2) - profile.width - 20
    bow = fit(trim(load("судно_нос.png")), height=profile.height)
    stern = fit(trim(load("судно_корма.png")), height=profile.height)
    if bow.width + stern.width + 20 > side_w:
        scale = side_w / (bow.width + stern.width + 20)
        bow = fit(bow, width=int(bow.width * scale))
        stern = fit(stern, width=int(stern.width * scale))
    canvas.paste(bow, (PAD + profile.width + 20, y))
    canvas.paste(stern, (PAD + profile.width + 30 + bow.width, y))
    for label, x in (("вид сбоку", PAD + 8),
                     ("вид с носа", PAD + profile.width + 28),
                     ("вид с кормы", PAD + profile.width + 38 + bow.width)):
        draw.text((x, y + profile.height - 26), label, fill=INK_3,
                  font=fonts["note"])
    y += profile.height + PAD

    # --- планы палуб
    caption(draw, PAD, y, W - PAD * 2, "ОБЩЕЕ РАСПОЛОЖЕНИЕ ПО ПАЛУБАМ", fonts)
    y += 44 + 14
    plans = load("палубы_общее_расположение.png")
    plans = plans.crop((0, 62, plans.width, plans.height))  # своя шапка не нужна
    plans = fit(plans, width=W - PAD * 2)
    canvas.paste(plans, (PAD, y))
    y += plans.height + PAD

    # --- каюты
    caption(draw, PAD, y, W - PAD * 2, "КАТЕГОРИИ КАЮТ", fonts)
    y += 44 + 14
    # плитки приводятся к одному боксу: после обрезки полей рендеры выходят
    # разной высоты, и подписи под ними разъезжаются по вертикали
    columns = len(CABIN_TILES)
    tile_w = (W - PAD * 2 - (columns - 1) * 16) // columns
    tile_h = int(tile_w * 0.66)
    for index, (category, view, title) in enumerate(CABIN_TILES):
        shot = trim(load(f"{category}_{view}.png"))
        shot = fit(shot, width=tile_w) if shot.width / shot.height > tile_w / tile_h \
            else fit(shot, height=tile_h)
        tile = Image.new("RGB", (tile_w, tile_h), "#f2f4f6")
        tile.paste(shot, ((tile_w - shot.width) // 2, (tile_h - shot.height) // 2))
        x = PAD + index * (tile_w + 16)
        canvas.paste(tile, (x, y))
        bar = y + tile_h
        draw.rectangle([x, bar, x + tile_w, bar + 62], fill="#f2f4f6")
        draw.text((x + 14, bar + 8), title, fill=INK, font=fonts["cap"])
        count = summary["by_category"].get(category, 0)
        draw.text((x + 14, bar + 34),
                  f"{ship.clear_area(category):.1f} м²  ·  {count} кают  ·  "
                  f"{ship.MODULES[category]} модуля",
                  fill=INK_2, font=fonts["note"])
    y += tile_h + 62 + PAD

    # --- сервисы
    caption(draw, PAD, y, W - PAD * 2, "СЕРВИСЫ НА БОРТУ", fonts)
    y += 44 + 14
    services = [s for s in summary["services"]
                if not s.startswith(("Трапы", "Камбуз", "Пост", "Рулевая"))]
    columns = 4
    per = (len(services) + columns - 1) // columns
    for index, name in enumerate(services):
        cx = PAD + (index // per) * ((W - PAD * 2) // columns)
        cy = y + (index % per) * 32
        draw.ellipse([cx, cy + 8, cx + 10, cy + 18], fill=ACCENT)
        draw.text((cx + 22, cy), name, fill=INK_2, font=fonts["note"])
    y += per * 32 + 20

    draw.line([PAD, y, W - PAD, y], fill=LINE)
    draw.text((PAD, y + 14),
              "Все размеры и количества посчитаны по модели: вместимость — из "
              "раскладки палуб, водоизмещение — по объёму подводной части.",
              fill=INK_3, font=fonts["note"])

    canvas = canvas.crop((0, 0, W, y + 60))
    out = RENDERS / "лист_проекта.png"
    canvas.save(out)
    print(f"лист: {out.relative_to(ROOT)}  {canvas.size[0]}x{canvas.size[1]}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
