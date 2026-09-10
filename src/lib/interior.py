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
from . import lines
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
# Зазор начинки от борта. Считается от ЗАВАЛА фриза: наклонённая верхняя
# лента борта уходит внутрь примерно на 60 мм, и начинка, отставленная на
# 30 мм, попадала прямо в неё.
SKIN_GAP = 130  # касание «в ноль» кернел считает
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
            x = start + ship.PARTITION + 20
            parts.append(_part(length, ship.BULKHEAD, HEIGHT,
                               (x, y, level + FLOOR),
                               WALL, MAT_WALL, "переборка центрального блока"))
            # Двери выгородок центрального блока. Без них коридор длиной
            # в тридцать метров упирается в глухую стену на всю длину:
            # на виде с уровня глаз это первое, что бросается в глаза, и
            # это же неверно по существу — за переборкой кладовые, посты
            # уборки и шахты, и в каждую есть вход.
            step = 6_500
            count = int(length // step)
            for index in range(count):
                door_x = x + step / 2 + index * step
                # полотно ставится СНАРУЖИ переборки с зазором 10 мм: на
                # левом борту оно врезалось в неё на 5 мм по всей площади,
                # и ядро считало это пересечением на 7.6 литра
                door_y = y + ship.BULKHEAD + 10 if sign > 0 else y - 50
                parts.append(_part(DOOR_WIDTH - 40, 40, 2_000,
                                   (door_x, door_y, level + FLOOR),
                                   DOOR, MAT_DOOR, "дверь выгородки"))
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
        block_len = min(zone.length - 2 * inset, 9_000)
        base = level + FLOOR
        # шахта, а в ней марш и лифт: раньше блок был глухим объёмом и на
        # разрезе читался как ещё одна переборка
        parts.append(_part(block_len, ship.CENTRE_BLOCK - 2 * inset, 120,
                           (zone.x0 + inset, -ship.CENTRE_EDGE + inset, base),
                           SHAFT, MAT_WALL, "площадка трапов"))
        for item in pf.stair_flight(ship.DECK_PITCH, 3_600, 1_200):
            moved = bd.Pos(zone.x0 + inset + 400, -ship.CENTRE_EDGE + 400,
                           base + 120) * item
            moved.label, moved.color = item.label, item.color
            parts.append(moved)
        for item in pf.lift_shaft(1_800, 1_800, HEIGHT):
            moved = bd.Pos(zone.x0 + inset + 5_400, -700, base + 120) * item
            moved.label, moved.color = item.label, item.color
            parts.append(moved)
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
    zones = ar.place(deck_name)
    transom = zones[0].x0 if zones else None
    parts = []
    for zone in zones:
        if zone.kind == "cabins":
            continue
        # На самом транце переборку не ставим: там уже стоит поперечный
        # пояс оболочки, и переборка отсека врезалась прямо в него на
        # всю ширину палубы — три литра пересечения в аудите.
        if transom is not None and abs(zone.x0 - transom) < 1:
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

        # Настилы коридоров и центрального блока кладутся ПОД КАЖДОЙ каютной
        # зоной по отдельности, а не одной полосой от первой каюты до
        # последней: между каютными зонами стоят общественные помещения со
        # своей отделкой, и сплошная полоса ложилась поверх них.
        for zone in ar.place(deck_name):
            if zone.kind != "cabins":
                continue
            for sign in (1, -1):
                y = ship.CENTRE_EDGE if sign > 0 else -ship.CORRIDOR_EDGE
                parts.append(_part(zone.length, ship.CORRIDOR_WIDTH, FLOOR,
                                   (zone.x0, y, level), FLOOR_CORRIDOR,
                                   MAT_WALL, "настил коридора"))
            parts.append(_part(zone.length, ship.CENTRE_BLOCK, FLOOR,
                               (zone.x0, -ship.CENTRE_EDGE, level),
                               FLOOR_CENTRE, MAT_WALL,
                               "настил центрального блока"))

    parts += centre_block(deck_name, level)
    parts += zone_walls(deck_name, level, half_beam)
    parts += zone_floors(deck_name, level)
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
    """Прямоугольник зоны, гарантированно лежащий внутри обвода.

    Если зона упирается в сужение (нос солнечной палубы, корма нижних),
    прямоугольник УКОРАЧИВАЕТСЯ по длине, а не отменяется целиком: иначе
    зона молча выпадает из расстановки и палуба остаётся голым настилом —
    ровно это и случилось со спортивной площадкой в носу.
    """
    x0 = zone.x0 + margin
    x1 = zone.x0 + zone.length - margin
    while x1 - x0 >= 1_200:
        samples = [x0 + (x1 - x0) * i / 6 for i in range(7)]
        half = min(half_at(x) for x in samples) - margin
        if half >= 1_200:
            return x0, x1, half
        x1 -= max(500.0, (x1 - x0) * 0.1)
    return None

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


def _put(items, x, y, z=0.0, turn=0):
    """Поставить набор деталей углом в точку (x, y, z).

    turn разворачивает набор вокруг вертикали и заново приводит его к тому
    же углу: мебель строится от ближнего угла, поэтому зеркалить её одним
    знаком координаты нельзя — спинка шезлонга левого борта иначе смотрит
    не к борту, а в проход.
    """
    placed = []
    for item in items:
        if turn:
            item = bd.Rot(0, 0, turn) * item
        moved = bd.Pos(x, y, z) * item
        moved.label, moved.color = item.label, item.color
        placed.append(moved)
    return placed


LOUNGER_PITCH = 1_100  # шезлонг 700 мм плюс проход между ними
LOUNGER_DEPTH = 1_900
LOUNGER_WIDTH = 700
LOUNGER_WALK = 1_100  # проход вдоль ограждения за спинками


def _loungers(x0, x1, half_at, z):
    """Два ряда шезлонгов вдоль бортов, спинками к ограждению.

    Ряд ЗЕРКАЛИТСЯ разворотом, а не сменой знака координаты: шезлонг
    строится от ближнего угла, и левый борт, посчитанный как -(half-2100),
    уезжал на два метра внутрь палубы. На виде с уровня глаз это читалось
    сплошной грудой мебели посреди прохода вместо ряда у борта.

    Полуширота берётся в СВОЁМ сечении, а не самая узкая по зоне: кормовая
    зона начинается там, где палуба ещё сужена, и ряд, разложенный по её
    носку, оказывался посреди палубы, а не у борта.

    Между группами оставлен поперечный проход к ограждению: сплошная
    двадцатиметровая шеренга отрезает борт от палубы.
    """
    parts = []
    index = 0
    x = x0
    while x + LOUNGER_PITCH <= x1:
        local = min(half_at(x), half_at(x + LOUNGER_WIDTH)) - 350
        inboard = local - LOUNGER_WALK - LOUNGER_DEPTH
        if index % 7 != 6 and inboard > 600:
            parts += _put(pf.sun_lounger(), x, inboard, z)
            parts += _put(pf.sun_lounger(), x + LOUNGER_WIDTH, -inboard, z,
                          turn=180)
        index += 1
        x += LOUNGER_PITCH
    return parts

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
        # Зал делится продольным проходом: столы у бортов на банкетках, в
        # середине — свободные круглые столы. Регулярная сетка во всю
        # ширину читается как столовая, а не как ресторан, и не оставляет
        # прохода официанту.
        # Секции ставятся с разрывом: банкетки вплотную одна к другой
        # читаются сплошной перегородкой вдоль борта, а не рядом столиков,
        # и между ними некуда подойти.
        step = 3_400
        seat_len = 2_200
        index = 0
        x = x0
        while x + step <= x1:
            local = min(half_at(x), half_at(x + step)) - 350
            for side in (-1, 1):
                edge = side * local
                parts += _put(pf.banquette(seat_len, 700),
                              x + 250, edge - 700 if side > 0 else edge, z)
                # стол отодвигается от банкетки на 350 мм: вплотную он
                # сливается с ней в один объём, и посадка не читается
                parts += _put(pf.table_rect(1_400, 800), x + 650,
                              edge - 1_850 if side > 0 else edge + 1_050, z)
            # круглые столы через секцию, иначе середина зала забивается
            # креслами и продольный проход исчезает
            if index % 2 == 0 and local > 3_400:
                parts += _put(pf.dining_set(1_100, 4), x + 700, -1_650, z)
            parts += _put(pf.pendant_light(), x + step / 2 - 210, -210, z)
            index += 1
            x += step
    elif "бассейн" in name:
        pool_len = min(x1 - x0 - 2_000, 9_000)
        parts += _put(pf.pool(pool_len, min(2 * half - 1_500, 4_600)),
                      x0 + 1_000, -min(half - 750, 2_300), z)
        # Бар у бассейна назван в плане — значит, он должен там стоять.
        # Ставится у борта за чашей, чтобы не перекрывать обход бассейна.
        parts += _put(pf.bar_counter(min(pool_len - 2_000, 5_000)),
                      x0 + 1_500, -half + 900, z)
        parts += _loungers(x0 + 10_500, x1, half_at, z)
    elif "бар" in name or "салон" in name or "холл" in name:
        parts += _put(pf.bar_counter(min(x1 - x0 - 2_000, 6_000)), x0 + 800,
                      half - 3_200, z)
        # мягкая зона вдоль обоих бортов и столики между ними
        for index in range(int((x1 - x0 - 8_000) // 3_400)):
            base_x = x0 + 7_500 + index * 3_400
            parts += _put(pf.lounge(), base_x, -half + 600, z)
            parts += _put(pf.banquette(2_600, 700), base_x, half - 1_500, z)
            parts += _put(pf.table_rect(1_200, 700), base_x + 400,
                          half - 2_600, z)
            parts += _put(pf.pendant_light(), base_x + 1_200, -400, z)
    elif "конференц" in name:
        parts += _put(pf.theatre_rows(x1 - x0, 2 * half), x0, -half, z)
    elif "фитнес" in name or "спа" in name:
        parts += _grid(area, 2_200, 2_400, pf.gym_station, half_at, z)
    elif "шезлонг" in name or "отдыха" in name:
        parts += _loungers(x0, x1, half_at, z)
    elif "вентиляц" in name or "кожух" in name:
        # у трубы стоит то, что и должно: агрегаты, а не пустой настил
        for index in range(2):
            parts += _put(pf.air_conditioning(), x0 + 600 + index * 3_200,
                          -half + 900, z)
        parts += _put(pf.pump_station(), x0 + 600, half - 3_000, z)
    elif "смотров" in name:
        # открытая площадка: скамьи вдоль ограждения, ничего капитального —
        # обвод здесь сужается вдвое, и любой объём вылезет за борт
        step = 2_600
        index = 0
        x = x0 + 1_000
        while x + step <= x1 - 1_000:
            local = min(half_at(x), half_at(x + step)) - 900
            if local > 1_400:
                for side in (-1, 1):
                    y = local - 700 if side > 0 else -local
                    parts += _put(pf.banquette(2_000, 700), x, y, z)
            index += 1
            x += step
    elif "спортив" in name:
        court = min(x1 - x0 - 2_000, 18_000)
        parts += _put(pf.sport_court(court, min(2 * half - 2_000, 9_000)),
                      x0 + 1_000, -min(half - 1_000, 4_500), z)
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
    elif "аккумулятор" in name:
        parts += _grid(area, 3_000, 1_600, pf.battery_rack, half_at, z)
    elif "танки" in name or "балласт" in name:
        parts += _put(pf.tank(x1 - x0 - 600, 2 * half - 1_200), x0 + 300,
                      -half + 600, z)
    elif "электростанц" in name or "грщ" in name:
        for index in range(2):
            parts += _put(pf.diesel_generator(), x0 + 600,
                          -half + 900 + index * 2_400, z)
        parts += _put(pf.switchboard(), x0 + 4_600, half - 1_800, z)
    elif "насосн" in name:
        parts += _grid(area, 3_000, 2_400, pf.pump_station, half_at, z)
    elif "кондиционир" in name or "вентиляц" in name:
        parts += _grid(area, 3_800, 2_600, pf.air_conditioning, half_at, z)
    elif "очистка стоков" in name or "опреснит" in name:
        parts += _put(pf.sewage_plant(), x0 + 800, -half + 800, z)
        parts += _put(pf.fresh_water_plant(), x0 + 800, half - 2_600, z)
    elif "рулевая машина" in name:
        parts += _put(pf.steering_gear(), x0 + 600, -1_300, z)
    elif "подруливающ" in name or "форпик" in name:
        parts += _put(pf.bow_thruster(), x0 + 600, -1_200, z)
    elif "гребные" in name or "ахтерпик" in name:
        for side in (-1, 1):
            parts += _put(pf.stabilizer(), x0 + 1_200,
                          side * (half - 1_400) - 1_400, z)
    elif "прачечн" in name or "бытов" in name:
        parts += _grid(area, 2_600, 2_200, pf.galley_unit, half_at, z)
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


# --- Отделка общественных зон -----------------------------------------------

ZONE_FLOOR = {
    "ресторан": srgb("#8C6A44"),
    "кафе": srgb("#8C6A44"),
    "бар": srgb("#5C4030"),
    "салон": srgb("#5C4030"),
    "холл": srgb("#7A6A58"),
    "вестибюль": srgb("#7A6A58"),
    "конференц": srgb("#3E4A52"),
    "фитнес": srgb("#4A5A52"),
    "спа": srgb("#4A5A52"),
    "боулинг": srgb("#6B5638"),
    "бильярд": srgb("#6B5638"),
    "магазин": srgb("#8A8073"),
    "медпункт": srgb("#C9CFCF"),
    "камбуз": srgb("#AEB6B8"),
    "прачечная": srgb("#AEB6B8"),
    "детская": srgb("#9C7A55"),
}


def zone_contour(x0, x1, half_at, margin=120, step=1_500):
    """Контур участка палубы, ВЫБРАННЫЙ по её полушироте.

    Прямоугольник по самому узкому сечению зоны, который отдаёт _usable,
    годится для расстановки мебели: там важно не вылезти за борт. Настилу
    он не годится — зал в оконечности сужается плавно, и прямоугольник по
    его носку оставляет остальную палубу без пола. На виде с уровня глаз
    это читается сразу: цветная дорожка посреди зала и голая палуба по
    бортам.
    """
    count = max(2, int((x1 - x0) / step))
    samples = [x0 + (x1 - x0) * i / count for i in range(count + 1)]
    right, left = [], []
    for x in samples:
        half = half_at(x) - margin
        if half < 400:
            continue
        right.append((x, half))
        left.append((x, -half))
    if len(right) < 2:
        return None
    return right + list(reversed(left))


def zone_floors(deck_name, level):
    """Настил общественной зоны в свой цвет.

    Отделка не украшение: на плане и в разрезе по ней видно границу зоны
    без подписи, а зал, отделённый только переборкой, сливается с соседним.
    """
    half_at = _zone_half_beam(deck_name)
    parts = []
    for zone in ar.place(deck_name):
        if zone.kind not in ("service", "open"):
            continue
        colour = next((c for key, c in ZONE_FLOOR.items()
                       if key in zone.name.lower()), None)
        if colour is None:
            continue
        points = zone_contour(zone.x0 + 120, zone.x0 + zone.length - 120,
                              half_at)
        if points is None:
            continue
        slab = lines.deck_slab(points, level + FLOOR, FLOOR, colour, MAT_WALL,
                               f"настил зоны: {zone.name}")
        parts.append(slab)
    return parts
