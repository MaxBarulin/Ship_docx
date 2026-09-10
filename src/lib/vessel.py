"""Судно в сборе: корпус, надстройка, палубы, оборудование.

Надстройка собрана не сплошным объёмом, а бортовыми поясами: цоколь, лента
остекления, фриз. Иначе окна кают не читались бы — сплошной блок закрыл бы
стекло изнутри, а на защите именно ряд окон показывает, где какая палуба.
"""

from cadgen import build123d as bd

from . import deckhouse as dh
from . import ship
from .furniture import _part
from .hull import hull_solid

CABIN_ZONE_X0 = 22_000  # начало зоны кают по длине
CABIN_ZONE_LEN = ship.CABIN_ZONE_LENGTH


def hull_parts():
    """Корпус, разрезанный по КВЛ: сурик ниже, борт выше."""
    body = hull_solid()
    box = body.bounding_box()
    cut = bd.Pos(box.center().X, 0, ship.DRAFT / 2) * bd.Box(
        box.size.X + 2_000, box.size.Y + 2_000, ship.DRAFT)

    below = body & cut
    below.color, below.label = dh.HULL_UNDERWATER, "подводная часть корпуса"
    below.cad_material = dict(dh.MAT_PAINT)

    above = body - cut
    above.color, above.label = dh.HULL_TOPSIDE, "надводный борт"
    above.cad_material = dict(dh.MAT_PAINT)
    return [below, above]


def deck_sides(x0, length, level, width, sill=800, window=1_400,
               pitch=ship.MODULE):
    """Бортовой пояс одной палубы: цоколь, лента окон, фриз, торцы.

    Торцевые переборки обязательны: без них надстройка просвечивает насквозь
    на видах с носа и с кормы, и уступы силуэта читаются как щели.
    """
    height = ship.DECK_PITCH
    parts = [
        _part(120, width, height, (x, -width / 2, level),
              dh.SUPERSTRUCTURE, dh.MAT_PAINT, "торцевая переборка")
        for x in (x0 - 120, x0 + length)
    ]
    for side in (-1, 1):
        y = side * width / 2
        parts.append(_part(length, 90, sill, (x0, y - 45, level),
                           dh.SUPERSTRUCTURE, dh.MAT_PAINT, "цоколь борта"))
        parts.append(_part(length, 90, height - sill - window,
                           (x0, y - 45, level + sill + window),
                           dh.SUPERSTRUCTURE, dh.MAT_PAINT, "фриз борта"))
    parts += dh.window_band(x0, length, level + sill, window, width, pitch=pitch)
    return parts


def build(explode=0):
    """Судно в сборе. explode раздвигает ярусы по вертикали — так получается
    взрыв-схема, которую требует блок дизайн-проекта, из той же геометрии.

    Ярусы нумеруются снизу вверх, сдвиг каждого кратен его номеру: палубы
    расходятся равномерно и остаются в том же порядке, в каком стоят на судне.
    """
    tiers: dict[int, list] = {}

    def tier(index, items):
        tiers.setdefault(index, []).extend(
            items if isinstance(items, list) else [items])

    parts = list(hull_parts())

    x0, xe = ship.DECKHOUSE_START, ship.DECKHOUSE_END
    length = xe - x0
    beam = ship.SUPERSTRUCTURE_BEAM

    tier(0, parts)

    # главная палуба: открытый променад по всей ширине корпуса
    tier(1, dh.deck_slab(ship.MAIN_DECK, 6_000, 128_000, 16_200,
                         dh.DECK_TEAK, "главная палуба"))
    tier(1, dh.railing(6_000, 128_000, ship.MAIN_DECK, 16_200))

    # общественные помещения главной палубы — панорамное остекление во всю высоту
    tier(1, deck_sides(x0, length, ship.MAIN_DECK, beam, sill=300, window=2_000,
                       pitch=2_600))

    # три палубы кают: каждая следующая короче — отсюда ступенчатый силуэт,
    # а заодно место под шлюпки и балконы на образовавшихся уступах
    for step_i, level in enumerate(
            (ship.CABIN_DECK_1, ship.CABIN_DECK_2, ship.CABIN_DECK_3)):
        deck_x0 = x0 + 2_000 * step_i
        deck_len = length - 5_000 * step_i - 2_000 * step_i
        tier(2 + step_i, dh.deck_slab(level, deck_x0, deck_len, beam,
                                      dh.DECK_PAINT))
        tier(2 + step_i, deck_sides(deck_x0, deck_len, level, beam))

    # балконы люксов — на верхней палубе кают, по остатку променада
    for side in (-1, 1):
        tier(4, dh.balcony(CABIN_ZONE_X0 + 4_000, 7_800 * 2, side,
                           ship.CABIN_DECK_3, depth=int(ship.promenade_width())))
        tier(4, dh.balcony(CABIN_ZONE_X0 + 24_000, 7_800 * 2, side,
                           ship.CABIN_DECK_3, depth=int(ship.promenade_width())))

    # солнечная палуба: уже нижних, открытая
    sun_beam = 10_600
    sun_x0, sun_len = x0 + 6_000, length - 30_000
    tier(5, dh.deck_slab(ship.SUN_DECK, sun_x0, sun_len, sun_beam,
                         dh.DECK_TEAK, "солнечная палуба"))
    tier(5, dh.railing(sun_x0, sun_len, ship.SUN_DECK, sun_beam))
    tier(5, dh.solar_array(30_000, 46_000, ship.SUN_DECK, sun_beam))

    # оборудование — на ярусе той палубы, к которой оно относится
    tier(5, dh.wheelhouse(122_000, ship.CABIN_DECK_3))
    tier(5, dh.mast(122_000, ship.CABIN_DECK_3 + 2_800))
    tier(5, dh.funnel(88_000, ship.SUN_DECK))
    for x in (34_000, 52_000):
        for side in (-1, 1):
            tier(3, dh.lifeboat(x, side, ship.CABIN_DECK_2))
    for side in (-1, 1):
        tier(1, dh.gangway(104_000, side, ship.MAIN_DECK))

    assembled = []
    for index in sorted(tiers):
        for part in tiers[index]:
            assembled.append(bd.Pos(0, 0, index * explode) * part if explode
                             else part)
            assembled[-1].label = part.label
            assembled[-1].color = part.color
    return bd.Compound(children=assembled, label="круизное судно")
