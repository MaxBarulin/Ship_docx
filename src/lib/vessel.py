"""Судно в сборе: корпус, надстройка по обводам, палубы, оборудование.

Надстройка построена не коробками, а по контурам палуб: каждая палуба —
замкнутый обвод со скруглённой кормой и сужением к носу, а борт собран
плоскими панелями по сегментам этого обвода. Поэтому остекление идёт и по
скруглениям, где прямоугольная надстройка обрывалась бы уступом.

Простенки ставятся только на прямых бортовых участках и с шагом в модуль
каюты: за прямым бортом стоят каюты, и снаружи видно, где какая. На носовых
и кормовых скруглениях простенков нет — там панорамные салоны, и сплошное
стекло там не украшение, а то, что действительно стоит за обводом.
"""

from cadgen import build123d as bd

from . import arrangement as ar_module
from . import deckhouse as dh
from . import interior as interior_mod
from . import lines
from . import ship
from .furniture import _part
from .hull import hull_solid

# уровень -> (начало, конец, полуширота надстройки)
DECK_SHAPE = ship.DECK_SHAPE

DECK_LEVEL = {
    "главная": ship.MAIN_DECK,
    "средняя": ship.CABIN_DECK_1,
    "шлюпочная": ship.CABIN_DECK_2,
    "верхняя": ship.CABIN_DECK_3,
    "солнечная": ship.SUN_DECK,
}


def deck_stations(x0, x1, half, stern=7_000, bow=16_000):
    """Обвод палубы: скруглённая корма, прямой борт, сужение к носу.

    Длина скруглений выбрана так, чтобы ВСЕ каюты попали в прямой участок:
    каюты расставляются по прямой на |y| = CABIN_EDGE, и там, где обвод уже
    этой линии, каюта торчит сквозь борт наружу. При скруглениях 11 и 24 м
    за обвод уезжали 26 кают — проверка в audit_model это ловит.
    """
    return [
        (x0, half * 0.40),
        (x0 + stern * 0.30, half * 0.78),
        (x0 + stern * 0.65, half * 0.95),
        (x0 + stern, half),
        (x1 - bow, half),
        (x1 - bow * 0.60, half * 0.95),
        (x1 - bow * 0.34, half * 0.78),
        (x1 - bow * 0.15, half * 0.48),
        (x1, half * 0.08),
    ]


def deck_contour(name):
    return lines.contour(deck_stations(*DECK_SHAPE[name]))


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


def piers(points, level, sill, window, name):
    """Простенки между окнами кают — только на прямом борту."""
    x0, x1, half = DECK_SHAPE[name]
    runs = lines.side_runs(points, x0 + 12_000, x1 - 26_000, half * 0.92)
    parts = []
    for segments in runs.values():
        for (ax, ay), (bx, by) in segments:
            start, end = min(ax, bx), max(ax, bx)
            # Шаг простенков — два модуля каюты, а не один: частая решётка
            # простенков читается как остекление прошлого поколения, тогда
            # как современное судно несёт сплошную ленту стекла.
            step = ship.MODULE * 2
            count = int((end - start) // step)
            for index in range(count + 1):
                x = start + index * step
                if x > end:
                    break
                # простенок ложится снаружи борта: изнутри на той же линии
                # стоит переборка между каютами, и простенок садился прямо
                # в неё — по одному пересечению на каждую каюту
                glass = 60 + 10  # лента остекления плюс зазор на касание
                y = ay + glass if ay > 0 else ay - glass - 260
                parts.append(_part(160, 260, window,
                                   (x - 80, y, level + sill),
                                   dh.SUPERSTRUCTURE, dh.MAT_PAINT, "простенок"))
    return parts


def deck_shell(name, sill=800, window=1_500, cabins=True):
    """Палуба целиком: плита, цоколь, остекление, фриз, простенки."""
    level = DECK_LEVEL[name]
    points = deck_contour(name)
    height = ship.DECK_PITCH
    t = 110

    parts = [lines.deck_slab(points, level, 120,
                             dh.DECK_PAINT if cabins else dh.DECK_TEAK,
                             dh.MAT_TEAK, f"{name} палуба")]
    parts += lines.band(points, level, sill, t, dh.SUPERSTRUCTURE,
                        dh.MAT_PAINT, "цоколь борта")
    parts += lines.band(points, level + sill, window, 60, dh.GLAZING,
                        dh.MAT_GLASS, "остекление")
    parts += lines.band(points, level + sill + window, height - sill - window,
                        t, dh.SUPERSTRUCTURE, dh.MAT_PAINT, "фриз борта",
                        tilt=9.0)
    # Карниз кладётся снаружи борта: его контур раздвинут на толщину
    # бортовой панели, иначе он совпадает с фризом гранью в грань и кернел
    # считает касание пересечением на всю толщину.
    parts += lines.eaves(
        lines.clip_to_hull(lines.inset(points, -(t + 40)), margin=260),
        level + height - 90, reach=260)
    if cabins:
        parts += piers(points, level, sill, window, name)
    return parts


def wheelhouse(x_center, level):
    """Рубка с наклонным лобовым стеклом и обтекаемой крышей."""
    stations = [(x_center - 4_200, 1_700), (x_center - 2_200, 2_900),
                (x_center + 600, 3_000), (x_center + 2_600, 2_400),
                (x_center + 4_000, 900)]
    points = lines.contour(stations, step=900)
    parts = [
        lines.deck_slab(points, level + 300, 300, dh.SUPERSTRUCTURE,
                        dh.MAT_PAINT, "основание рубки"),
    ]
    parts += lines.band(points, level + 300, 2_300, 70, dh.GLAZING,
                        dh.MAT_GLASS, "остекление рубки")
    parts += [lines.deck_slab(points, level + 2_800, 220, dh.SUPERSTRUCTURE,
                              dh.MAT_PAINT, "крыша рубки")]
    for side in (-1, 1):
        y = side * 6_100
        parts.append(_part(3_600, 1_900, 200,
                           (x_center - 1_800, y - 950, level),
                           dh.SUPERSTRUCTURE, dh.MAT_PAINT, "крыло мостика"))
    return parts


def funnel(x_center, level):
    """Труба: обтекаемая, с наклоном назад."""
    stations = [(x_center - 2_600, 700), (x_center - 900, 1_500),
                (x_center + 1_400, 1_450), (x_center + 2_800, 500)]
    points = lines.contour(stations, step=700)
    parts = lines.band(points, level, 2_000, 260, dh.DARK, dh.MAT_PAINT,
                       "труба")
    parts += [lines.deck_slab(points, level + 2_240, 240, dh.ACCENT,
                              dh.MAT_PAINT, "пояс трубы")]
    return parts


MAST_LABELS = ("мачта заваливающаяся", "рей")


def air_draft(solid=None, mast_raised=False):
    """Габаритная высота от воды — по фактическому верху модели.

    Считать её по номеру верхней палубы нельзя: выше стоят рубка, труба и
    мачта, и правка их высоты молча разошлась бы с проверкой подмостового
    габарита. Мачта считается отдельно: на ЕГС её заваливают, и в походном
    положении судна под мостами её просто нет.
    """
    solid = build() if solid is None else solid
    tops = [part.bounding_box().max.Z for part in solid.leaves
            if mast_raised or part.label not in MAST_LABELS]
    return max(tops) - ship.DRAFT


INTERIOR_DECKS = {
    "техническая": ar_module.TANK_TOP,
    "нижняя": ar_module.LOWER_DECK,
    "главная": ship.MAIN_DECK,
    "средняя": ship.CABIN_DECK_1,
    "шлюпочная": ship.CABIN_DECK_2,
    "верхняя": ship.CABIN_DECK_3,
    "солнечная": ship.SUN_DECK,
}


def build(explode=0, interior=True, half=False):
    """Судно в сборе.

    explode раздвигает ярусы — так получается взрыв-схема. interior решает,
    строить ли начинку палуб: во взрыв-схеме она только мешает читать
    ярусы, а в разрезе она и есть предмет показа.

    half отбрасывает детали правого борта и даёт продольный разрез. Именно
    отбрасывает, а не режет булевой операцией: резать две тысячи тел — это
    минуты счёта и риск самопересечений на каждом, а для показа начинки
    достаточно убрать то, что её загораживает.
    """
    tiers: dict[int, list] = {}

    def tier(index, items):
        tiers.setdefault(index, []).extend(
            items if isinstance(items, list) else [items])

    tier(0, hull_parts())

    # главная палуба: настил по обводу корпуса — это открытый променад
    promenade = lines.contour([(row[0], row[3]) for row in ship.STATIONS
                               if row[3] > 400])
    tier(1, lines.deck_slab(promenade, ship.MAIN_DECK, 120, dh.DECK_TEAK,
                            dh.MAT_TEAK, "главная палуба"))
    tier(1, lines.glass_railing(lines.inset(promenade, 220),
                                ship.MAIN_DECK))
    tier(1, deck_shell("главная", sill=350, window=2_000, cabins=False))
    for side in (-1, 1):
        tier(1, dh.gangway(104_000, side, ship.MAIN_DECK))

    for index, name in enumerate(("средняя", "шлюпочная", "верхняя")):
        tier(2 + index, deck_shell(name))
        if interior:
            tier(2 + index, interior_mod.deck_interior(name, DECK_LEVEL[name]))
    if interior:
        tier(1, interior_mod.deck_interior("главная", ship.MAIN_DECK))
        # нижние палубы лежат внутри корпуса, солнечная — открытая
        tier(0, interior_mod.deck_interior("техническая", ar_module.TANK_TOP,
                                           half_beam=7_200))
        tier(0, interior_mod.deck_interior("нижняя", ar_module.LOWER_DECK,
                                           half_beam=7_800))
        tier(5, interior_mod.furnish("солнечная", ship.SUN_DECK))

    for side in (-1, 1):
        tier(4, dh.balcony(46_000, 15_600, side, ship.CABIN_DECK_3,
                           depth=1_800))

    sun = deck_contour("солнечная")
    tier(5, lines.deck_slab(sun, ship.SUN_DECK, 120, dh.DECK_TEAK,
                            dh.MAT_TEAK, "солнечная палуба"))
    tier(5, lines.glass_railing(lines.inset(sun, 160), ship.SUN_DECK,
                                height=1_150))
    tier(5, dh.solar_array(48_000, 30_000, ship.SUN_DECK, 9_000))
    # козырёк над зоной отдыха: даёт тень и ломает плоскую крышу, из-за
    # которой верхняя палуба читалась пустой плитой
    canopy_x0, canopy_len = 32_000, 13_000
    canopy = lines.contour(deck_stations(canopy_x0, canopy_x0 + canopy_len,
                                         3_200, stern=2_500, bow=3_500))
    # Высота козырька выбрана от подмостового габарита, а не от удобства:
    # на 2.6 м он поднимал верх судна до 15.7 м при пределе 15.5, и модель
    # переставала проходить под мостами. 2.3 м над палубой — рабочая
    # высота прохода, и запас до предела сохраняется.
    canopy_height = 2_300
    tier(5, lines.deck_slab(canopy, ship.SUN_DECK + canopy_height, 140,
                            dh.SUPERSTRUCTURE, dh.MAT_PAINT, "козырёк"))
    for x in (canopy_x0 + 3_000, canopy_x0 + canopy_len - 3_000):
        for side in (-1, 1):
            # стойка доходит до НИЗА козырька, а не до его верха: иначе
            # она протыкает плиту насквозь на её толщину
            tier(5, _part(220, 220, canopy_height - 140,
                          (x, side * 2_600 - 110, ship.SUN_DECK),
                          dh.RAIL, dh.MAT_METAL, "стойка козырька"))

    tier(5, wheelhouse(118_000, ship.CABIN_DECK_3))
    tier(5, dh.mast(118_000, ship.CABIN_DECK_3 + 3_020))
    tier(5, funnel(88_000, ship.SUN_DECK))

    for x in (34_000, 52_000):
        for side in (-1, 1):
            tier(3, dh.lifeboat(x, side, ship.CABIN_DECK_2))

    assembled = []
    for index in sorted(tiers):
        for part in tiers[index]:
            if half and part.bounding_box().center().Y > 300:
                continue
            moved = bd.Pos(0, 0, index * explode) * part if explode else part
            moved.label = part.label
            moved.color = part.color
            assembled.append(moved)
    return bd.Compound(children=assembled, label="круизное судно")
