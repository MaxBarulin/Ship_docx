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
from . import public_furniture as pf
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

    Ширина каждой переборки берётся по обводу в её собственном сечении:
    номинальная ширина палубы в носу больше фактической, и переборка
    носового отсека вылезала за борт.
    """
    half_at = _zone_half_beam(deck_name)
    parts = []
    for zone in ar.place(deck_name):
        if zone.kind == "cabins":
            continue
        reach = min(half_beam, half_at(zone.x0)) - SKIN_GAP
        if reach < 500:
            continue
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
    parts += furnish(deck_name, level)
    return parts


def all_interior(levels):
    """Начинка всех палуб, у которых есть уровень в модели судна."""
    parts = []
    for deck_name, level in levels.items():
        parts += deck_interior(deck_name, level)
    return parts


# --- Мебель общественных зон ------------------------------------------------

def _zone_half_beam(deck_name):
    """Полуширота обвода палубы как функция длины.

    Мебель расставляется по фактическому обводу, а не по прямоугольнику:
    зоны в оконечностях лежат там, где палуба уже сузилась, и сетка столов,
    разложенная по номинальной ширине, уехала бы за борт — ровно та ошибка,
    которую аудит уже ловил на леерах и на каютах.
    """
    from scipy.interpolate import PchipInterpolator

    from . import vessel

    if deck_name not in vessel.DECK_SHAPE:
        return _hull_half_beam(ar.deck(deck_name)[2])
    stations = vessel.deck_stations(*vessel.DECK_SHAPE[deck_name])
    curve = PchipInterpolator([x for x, _ in stations], [y for _, y in stations])
    lo, hi = stations[0][0], stations[-1][0]
    return lambda x: float(curve(min(max(x, lo), hi)))


def _hull_half_beam(level):
    """Полуширота КОРПУСА на заданной высоте.

    Нижние палубы лежат внутри корпуса, а он и по длине сужается, и по
    высоте: у днища полуширота меньше, чем у палубы. Брать для них ширину
    надстройки — значит расставить цистерны сквозь обшивку.
    """
    from scipy.interpolate import PchipInterpolator

    xs = [row[0] for row in ship.STATIONS]
    curves = {}
    for index, key in ((1, "bottom"), (2, "bilge"), (3, "deck")):
        curves[key] = PchipInterpolator(xs, [row[index] for row in ship.STATIONS])
    z_bilge = PchipInterpolator(xs, [row[4] for row in ship.STATIONS])
    z_keel = PchipInterpolator(xs, [row[5] for row in ship.STATIONS])

    def at(x):
        x = min(max(x, xs[0]), xs[-1])
        keel, bilge = float(z_keel(x)), float(z_bilge(x))
        if level <= keel:
            return float(curves["bottom"](x))
        if level >= bilge + 1_100:
            return float(curves["deck"](x))
        if level <= bilge:
            span = max(bilge - keel, 1.0)
            ratio = (level - keel) / span
            return (float(curves["bottom"](x))
                    + ratio * (float(curves["bilge"](x))
                               - float(curves["bottom"](x))))
        span = 1_100.0
        ratio = (level - bilge) / span
        return (float(curves["bilge"](x))
                + ratio * (float(curves["deck"](x)) - float(curves["bilge"](x))))

    return at


def _usable(zone, half_at, margin=350):
    """Прямоугольник зоны, гарантированно лежащий внутри обвода."""
    x0 = zone.x0 + margin
    x1 = zone.x0 + zone.length - margin
    if x1 - x0 < 1_200:
        return None
    samples = [x0 + (x1 - x0) * i / 6 for i in range(7)]
    half = min(half_at(x) for x in samples) - margin
    if half < 1_200:
        return None
    return x0, x1, half


def _grid(area, step_x, step_y, make, half_at=None, z=0.0):
    """Разложить мебель сеткой, следуя обводу.

    Ширина ряда берётся в СВОЁМ сечении, а не по самому узкому месту зоны:
    иначе длинный кормовой зал застраивается по ширине своего носка, и
    посреди ресторана остаётся пустая полоса в половину палубы.
    """
    x0, x1, half = area
    parts = []
    x = x0
    while x + step_x <= x1:
        local = half if half_at is None else min(
            half_at(x) - 350, half_at(x + step_x) - 350)
        y = -local
        while y + step_y <= local:
            for item in make():
                moved = bd.Pos(x, y, z) * item
                moved.label, moved.color = item.label, item.color
                parts.append(moved)
            y += step_y
        x += step_x
    return parts


def _put(items, x, y, z=0.0):
    placed = []
    for item in items:
        moved = bd.Pos(x, y, z) * item
        moved.label, moved.color = item.label, item.color
        placed.append(moved)
    return placed


def furnish_zone(zone, deck_name, level, half_at):
    """Мебель одной общественной зоны — по её назначению."""
    area = _usable(zone, half_at)
    if area is None:
        return []
    x0, x1, half = area
    z = level + FLOOR
    name = zone.name.lower()
    parts = []

    if "ресторан" in name or "кафе" in name:
        parts += _grid(area, 2_700, 2_700, pf.dining_set, half_at, z)
    elif "бассейн" in name:
        parts += _put(pf.pool(min(x1 - x0 - 2_000, 9_000), min(2 * half - 1_500,
                                                              4_600)),
                      x0 + 1_000, -min(half - 750, 2_300), z)
        for index in range(int((x1 - x0) // 1_100)):
            parts += _put(pf.sun_lounger(), x0 + index * 1_100, half - 2_100, z)
    elif "бар" in name or "салон" in name or "холл" in name:
        parts += _put(pf.bar_counter(min(x1 - x0 - 2_000, 6_000)), x0 + 800,
                      half - 3_200, z)
        for index in range(int((x1 - x0 - 8_000) // 3_200)):
            parts += _put(pf.lounge(), x0 + 7_500 + index * 3_200,
                          -half + 600, z)
    elif "конференц" in name:
        parts += _put(pf.theatre_rows(x1 - x0, 2 * half), x0, -half, z)
    elif "фитнес" in name or "спа" in name:
        parts += _grid(area, 2_200, 2_400, pf.gym_station, half_at, z)
    elif "шезлонг" in name or "отдыха" in name:
        for index in range(int((x1 - x0) // 1_100)):
            for side in (-1, 1):
                parts += _put(pf.sun_lounger(), x0 + index * 1_100,
                              side * (half - 2_100) - (0 if side > 0 else 0), z)
    elif "магазин" in name or "кладов" in name or "провизион" in name:
        parts += _grid(area, 1_600, 3_000, pf.shop_unit, half_at, z)
    elif "боулинг" in name or "бильярд" in name:
        for index in range(2):
            parts += _put(pf.bowling_lane(min(x1 - x0 - 2_400, 19_000)),
                          x0 + 600, -half + 900 + index * 1_500, z)
        parts += _put(pf.billiard_table(), x0 + 1_500, half - 2_200, z)
    elif "вестибюль" in name or "ресепшн" in name:
        parts += _put(pf.reception_desk(min(x1 - x0 - 1_500, 4_500)),
                      x0 + 700, half - 2_400, z)
        parts += _put(pf.lounge(), x0 + 1_200, -half + 700, z)
    elif "камбуз" in name:
        parts += _grid(area, 2_400, 2_200, pf.galley_unit, half_at, z)
    elif "экипаж" in name:
        parts += _grid(area, 2_400, 1_100, pf.crew_berth, half_at, z)
    elif "машинное" in name or "электродвиг" in name:
        for side in (-1, 1):
            parts += _put(pf.main_engine(min(x1 - x0 - 2_000, 7_000)),
                          x0 + 1_000, side * 3_200 - 1_300, z)
    elif "танки" in name or "балласт" in name or "аккумулятор" in name:
        parts += _put(pf.tank(x1 - x0 - 600, 2 * half - 1_200), x0 + 300,
                      -half + 600, z)
    return parts


def furnish(deck_name, level):
    """Мебель всех общественных зон палубы."""
    half_at = _zone_half_beam(deck_name)
    parts = []
    for zone in ar.place(deck_name):
        if zone.kind == "cabins":
            continue
        parts += furnish_zone(zone, deck_name, level, half_at)
    return parts
