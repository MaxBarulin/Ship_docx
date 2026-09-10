"""Общее расположение: что и где стоит на каждой палубе.

Это единственный источник правды о начинке судна. Из него считается
пассажировместимость, из него же рисуются планы палуб — поэтому план и
цифра в записке не могут разойтись: разойтись им негде.

Зоны идут вдоль борта от кормы к носу в порядке списка. Каюты занимают оба
борта с коридором посередине, общественные помещения — всю ширину.
"""

from __future__ import annotations

from dataclasses import dataclass, field

from . import ship

# --- Палубы ----------------------------------------------------------------
# Нижняя палуба лежит внутри корпуса: без неё некуда деть экипаж, запасы и
# машинное отделение, а без запасов не обосновать автономность в 10 суток.

LOWER_DECK = 2_400

DECKS = [
    ("нижняя", 2, LOWER_DECK, 11_000, 122_000),
    ("главная", 3, ship.MAIN_DECK, 11_000, 122_000),
    ("средняя", 4, ship.CABIN_DECK_1, 11_000, 122_000),
    ("шлюпочная", 5, ship.CABIN_DECK_2, 13_000, 115_000),
    ("верхняя", 6, ship.CABIN_DECK_3, 15_000, 108_000),
    ("солнечная", 7, ship.SUN_DECK, 17_000, 92_000),
]

CREW_CABIN_LENGTH = 2_600  # каюта экипажа на двоих, площадь около 8 м²


@dataclass
class Zone:
    """Участок палубы. kind решает, как он считается и как рисуется."""

    kind: str  # cabins | service | tech | crew | open
    name: str
    length: float
    mix: dict[str, int] = field(default_factory=dict)
    x0: float = 0.0


# Раскладка. Длины общественных помещений заданы явно: их диктуют вместимость
# зала и нормы на посадочное место, а не сетка кают.
LAYOUT: dict[str, list[Zone]] = {
    "нижняя": [
        Zone("tech", "Провизионные кладовые", 14_000),
        Zone("crew", "Каюты экипажа", 26_000),
        Zone("tech", "Прачечная", 10_000),
        Zone("tech", "Машинное отделение", 30_000),
        Zone("tech", "Танки топлива и воды", 24_000),
        Zone("tech", "Очистка стоков", 10_000),
        Zone("tech", "Подруливающее", 8_000),
    ],
    "главная": [
        Zone("service", "Панорамный ресторан", 26_000),
        Zone("service", "Камбуз и буфетная", 12_000),
        Zone("service", "Вестибюль и ресепшн", 10_000),
        Zone("cabins", "Каюты эконом", 0, {"econom": 8}),
        Zone("service", "Магазины и медпункт", 8_000),
        Zone("cabins", "Каюты эконом", 0, {"econom": 6}),
        Zone("service", "Конференц-зал и кинолекторий", 18_000),
        Zone("service", "Пост швартовки", 8_000),
    ],
    "средняя": [
        Zone("service", "Кормовой салон отдыха", 10_000),
        Zone("cabins", "Каюты эконом и стандарт", 0,
             {"econom": 10, "standard": 6}),
        Zone("service", "Трапы и лифты", 8_000),
        Zone("cabins", "Каюты стандарт", 0, {"standard": 10}),
        Zone("service", "Фитнес-зал и СПА", 14_000),
    ],
    "шлюпочная": [
        Zone("service", "Кафе и детская комната", 12_000),
        Zone("cabins", "Каюты стандарт и бизнес", 0,
             {"standard": 8, "business": 4}),
        Zone("service", "Трапы и лифты", 8_000),
        Zone("cabins", "Каюты бизнес", 0, {"business": 5}),
        Zone("service", "Боулинг и бильярд", 14_000),
    ],
    "верхняя": [
        Zone("service", "Панорамный бар-салон", 15_000),
        Zone("cabins", "Каюты бизнес и люкс с балконами", 0,
             {"business": 3, "lux": 4}),
        Zone("service", "Трапы и лифты", 8_000),
        Zone("cabins", "Каюты люкс с балконами", 0, {"lux": 3}),
        Zone("service", "Рулевая рубка", 14_000),
    ],
    "солнечная": [
        Zone("open", "Шезлонги и зона отдыха", 20_000),
        Zone("open", "Бассейн и бар у бассейна", 18_000),
        Zone("open", "Солнечные панели", 30_000),
        Zone("open", "Спортивная площадка", 14_000),
    ],
}


def zone_length(zone: Zone) -> float:
    """Длина зоны: у кают считается по сетке, у остальных задана явно."""
    if zone.kind == "cabins":
        return sum(count * ship.cabin_width(category)
                   for category, count in zone.mix.items())
    if zone.kind == "crew":
        return zone.length
    return zone.length


def place(deck_name: str) -> list[Zone]:
    """Разложить зоны палубы по длине, проставив каждой её начало."""
    _, _, _, x0, _ = deck(deck_name)
    cursor = x0
    placed = []
    for zone in LAYOUT[deck_name]:
        length = zone_length(zone)
        placed.append(Zone(zone.kind, zone.name, length, dict(zone.mix), cursor))
        cursor += length
    return placed


def deck(name: str):
    for row in DECKS:
        if row[0] == name:
            return row
    raise KeyError(name)


def cabin_numbers(deck_name: str) -> list[dict]:
    """Каюты палубы с номерами, как они пойдут на план и в прайс.

    Нумерация судовая: номер начинается с номера палубы, правый борт
    нечётный, левый чётный — так пассажир находит каюту по табличке.
    """
    _, level_no, _, _, _ = deck(deck_name)
    result = []
    counter = {"правый": 1, "левый": 2}
    for zone in place(deck_name):
        if zone.kind != "cabins":
            continue
        for side in ("правый", "левый"):
            cursor = zone.x0
            for category in ("econom", "standard", "business", "lux"):
                for _ in range(zone.mix.get(category, 0)):
                    width = ship.cabin_width(category)
                    result.append({
                        "number": level_no * 100 + counter[side],
                        "deck": deck_name,
                        "side": side,
                        "category": category,
                        "x0": cursor,
                        "width": width,
                        "area": ship.clear_area(category),
                    })
                    counter[side] += 2
                    cursor += width
    return result


def crew_berths() -> int:
    """Спальных мест экипажа — по длине зоны кают экипажа на обоих бортах."""
    total = 0
    for zone in place("нижняя"):
        if zone.kind == "crew":
            total += int(zone.length // CREW_CABIN_LENGTH) * 2 * 2
    return total


def summary() -> dict:
    """Итог по судну: каюты, пассажиры, занятость палуб, сервисы."""
    cabins = []
    overflow = []
    for name, _, _, x0, available in DECKS:
        placed = place(name)
        used = sum(z.length for z in placed)
        if used > available:
            overflow.append((name, used, available))
        cabins += cabin_numbers(name)

    by_category: dict[str, int] = {}
    for cabin in cabins:
        by_category[cabin["category"]] = by_category.get(cabin["category"], 0) + 1

    services = [z.name for name in LAYOUT for z in LAYOUT[name]
                if z.kind in ("service", "open")]
    return {
        "cabins": len(cabins),
        "passengers": len(cabins) * ship.BERTHS_PER_CABIN,
        "by_category": by_category,
        "crew": crew_berths(),
        "services": services,
        "overflow": overflow,
    }
