"""Внутреннее насыщение палуб: переборки, коридоры, санблоки, шахты.

Строится по lib.arrangement, поэтому каюта в 3D стоит ровно там же, где она
на плане и где её посчитала вместимость. Расходиться им негде.

Поперечная схема одна на все палубы кают и берётся из lib.ship:
борт — каюта — коридор — центральный блок — коридор — каюта — борт.
Центральный блок несёт трапы, лифты и шахты: без него четыре метра ширины
надстройки оставались пустотой без назначения.

Двери не вычитаются из переборки, а получаются разрывом между её кусками:
на сотню кают это сотня булевых операций против нуля, и сборка судна
остаётся секундной.
"""

from cadgen import build123d as bd
from cadgen import srgb

from . import arrangement as ar
from . import ship
from .furniture import _part

# Настил каюты красится по категории: сверху палуба читается как схема
# расстановки, а не как одна серая плоскость, и на разрезе сразу видно,
# где какой класс. Пол у каюты собственный, а не общая палубная плита —
# иначе в разрезе каюты стоят на пустоте.
CATEGORY_FLOOR = {
    "econom": srgb("#4E7C99"),
    "standard": srgb("#3F8375"),
    "business": srgb("#C2A883"),
    "lux": srgb("#8E4552"),
    "accessible": srgb("#D08A3E"),
}
FLOOR_CORRIDOR = srgb("#B9AE9C")
FLOOR_CENTRE = srgb("#9AA2A6")
BERTH = srgb("#EFEDE7")

WALL = srgb("#DEDAD2")
WALL_TECH = srgb("#B6BDC0")
DOOR = srgb("#9A7A52")
POD = srgb("#EDEDEA")
SHAFT = srgb("#8E979B")

MAT_WALL = {"roughness": 0.75, "metalness": 0.0}
MAT_DOOR = {"roughness": 0.4, "metalness": 0.0, "clearcoat": 0.3}
MAT_POD = {"roughness": 0.25, "metalness": 0.0, "clearcoat": 0.6}

HEIGHT = ship.CEILING_HEIGHT
DOOR_WIDTH = 800
POD_DEPTH = 1_700
FLOOR = 40  # толщина настила: всё вертикальное встаёт НА него, а не в него
SKIN_GAP = 30  # зазор начинки от борта: касание «в ноль» кернел считает
# пересечением на всю толщину панели, и отчёт о коллизиях наполняется
# сотнями срабатываний там, где детали просто соприкасаются


def _side_sign(side):
    return 1 if side == "правый" else -1


def cabin_walls(cabin, level):
    """Одна каюта: поперечные переборки, продольная с дверью, санблок."""
    sign = _side_sign(cabin["side"])
    x0, width = cabin["x0"], cabin["width"]
    near = ship.CORRIDOR_EDGE  # граница с коридором
    far = ship.CABIN_EDGE - SKIN_GAP  # борт, с зазором на зашивку
    depth = far - near

    y_lo = near if sign > 0 else -far
    base = level + FLOOR
    parts = [
        _part(ship.PARTITION, depth, HEIGHT, (x0, y_lo, base),
              WALL, MAT_WALL, "переборка каюты"),
    ]

    # Продольная переборка коридора начинается ЗА поперечной, а не от той
    # же координаты: сходясь в угол «в ноль», два тела дают кернелу
    # пересечение на всю толщину, и отчёт о коллизиях наполняется углами.
    inner_x = x0 + ship.PARTITION
    door_x = x0 + width - DOOR_WIDTH - 200
    y_wall = near - ship.BULKHEAD if sign > 0 else near
    y_wall = y_wall if sign > 0 else -near - ship.BULKHEAD
    left_len = door_x - inner_x
    if left_len > 50:
        parts.append(_part(left_len, ship.BULKHEAD, HEIGHT,
                           (inner_x, y_wall, base),
                           WALL, MAT_WALL, "переборка коридора"))
    right_len = x0 + width - (door_x + DOOR_WIDTH) - 20
    if right_len > 50:
        parts.append(_part(right_len, ship.BULKHEAD, HEIGHT,
                           (door_x + DOOR_WIDTH, y_wall, base),
                           WALL, MAT_WALL, "переборка коридора"))
    parts.append(_part(DOOR_WIDTH - 40, 40, 2_000,
                       (door_x + 20, y_wall + 5, base), DOOR, MAT_DOOR,
                       "дверь каюты"))

    # собственный настил каюты
    parts.append(_part(width - ship.PARTITION, depth, FLOOR,
                       (x0 + ship.PARTITION, y_lo, level),
                       CATEGORY_FLOOR.get(cabin["category"], WALL),
                       MAT_WALL, f"настил каюты {cabin['category']}"))

    # санблок ставится у входа, глухой стороной к коридору
    pod_width = min(1_500, width - 700)
    if pod_width > 800:
        gap = 80
        pod_y = near + gap if sign > 0 else -near - POD_DEPTH - gap
        parts.append(_part(pod_width, POD_DEPTH, 2_200,
                           (x0 + width - pod_width - 60, pod_y, base),
                           POD, MAT_POD, "санблок"))

    # Койки стоят ВДОЛЬ борта, а не поперёк: санблок глубиной 1.7 м и койка
    # длиной 2.0 м в глубину каюты 3.5 м в один ряд не помещаются, и койка
    # въезжала в санблок. Вдоль борта они расходятся по глубине.
    berth_len, berth_wide = 2_000, 900
    berth_y = far - berth_wide - 200 if sign > 0 else -far + 200
    berths = 1 if width < 3_600 else 2
    for index in range(berths):
        bx = x0 + 250 + index * (berth_len + 250)
        if bx + berth_len > x0 + width - 150:
            break
        parts.append(_part(berth_len, berth_wide, 620, (bx, berth_y, base),
                           BERTH, MAT_POD, "койка"))
    return parts


def longitudinal_walls(deck_name, level, x_from, x_to):
    """Продольные переборки центрального блока.

    Режутся по границам отсеков: сплошная переборка во всю каютную зону
    проходит сквозь каждую поперечную переборку отсека, а на судне
    продольная переборка в поперечную упирается.
    """
    if x_to - x_from <= 0:
        return []
    edges = {x_from, x_to}
    for zone in ar.place(deck_name):
        edges.add(zone.x0)
        edges.add(zone.x0 + zone.length)
    cuts = sorted(x for x in edges if x_from <= x <= x_to)

    parts = []
    for start, end in zip(cuts, cuts[1:]):
        length = end - start - ship.PARTITION - 40
        if length < 300:
            continue
        for sign in (1, -1):
            y = ship.CENTRE_EDGE if sign > 0 else -ship.CENTRE_EDGE - ship.BULKHEAD
            parts.append(_part(length, ship.BULKHEAD, HEIGHT,
                               (start + ship.PARTITION + 20, y, level + FLOOR),
                               WALL, MAT_WALL, "переборка центрального блока"))
    return parts


def centre_block(deck_name, level):
    """Шахты трапов и лифтов в центральном блоке — по зонам плана."""
    parts = []
    for zone in ar.place(deck_name):
        if zone.kind != "service":
            continue
        name = zone.name.lower()
        if "трап" not in name and "лифт" not in name and "вестибюль" not in name:
            continue
        inset = ship.PARTITION + 40
        parts.append(_part(min(zone.length - 2 * inset, 9_000),
                           ship.CENTRE_BLOCK - 2 * inset, HEIGHT,
                           (zone.x0 + inset, -ship.CENTRE_EDGE + inset,
                            level + FLOOR),
                           SHAFT, MAT_WALL, "шахта трапов и лифтов"))
    return parts


def zone_walls(deck_name, level, half_beam):
    """Поперечные переборки между зонами палубы.

    Только у зон, где нет кают: в каютной зоне переборки уже стоят между
    каютами, и переборка отсека прошла бы прямо сквозь них через всю
    ширину палубы.
    """
    parts = []
    for zone in ar.place(deck_name):
        if zone.kind == "cabins":
            continue
        reach = half_beam - SKIN_GAP
        parts.append(_part(ship.PARTITION, reach * 2, HEIGHT,
                           (zone.x0, -reach, level + FLOOR),
                           WALL_TECH if zone.kind in ("tech", "crew") else WALL,
                           MAT_WALL, "переборка отсека"))
    return parts


def deck_interior(deck_name, level, half_beam=None):
    """Начинка одной палубы целиком."""
    half_beam = half_beam or ship.SUPERSTRUCTURE_HALF
    cabins = ar.cabin_numbers(deck_name)
    parts = []

    if cabins:
        starts = [cabin["x0"] for cabin in cabins]
        ends = [cabin["x0"] + cabin["width"] for cabin in cabins]
        parts += longitudinal_walls(deck_name, level, min(starts), max(ends))
        for cabin in cabins:
            parts += cabin_walls(cabin, level)

        # настилы коридоров и центрального блока по каютной зоне
        x_from, x_to = min(starts), max(ends)
        for sign in (1, -1):
            y = ship.CENTRE_EDGE if sign > 0 else -ship.CORRIDOR_EDGE
            parts.append(_part(x_to - x_from, ship.CORRIDOR_WIDTH, FLOOR,
                               (x_from, y, level), FLOOR_CORRIDOR, MAT_WALL,
                               "настил коридора"))
        parts.append(_part(x_to - x_from, ship.CENTRE_BLOCK, FLOOR,
                           (x_from, -ship.CENTRE_EDGE, level), FLOOR_CENTRE,
                           MAT_WALL, "настил центрального блока"))

    parts += centre_block(deck_name, level)
    parts += zone_walls(deck_name, level, half_beam)
    return parts


def all_interior(levels):
    """Начинка всех палуб, у которых есть уровень в модели судна."""
    parts = []
    for deck_name, level in levels.items():
        parts += deck_interior(deck_name, level)
    return parts
