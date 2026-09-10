"""Обводы в плане: контуры палуб и бортовые пояса по ним.

Почему не kernel-offset и не булевы вычеты колец. На гранях, ограниченных
плотным сплайном, kernel offset возвращает Null на части внутренних дельт, а
вычет двух сплайновых тел даёт то пустой результат, то самопересечения,
которые всплывают только в валидации STEP. Поэтому обвод считается
ЧИСЛЕННО набором точек, а борт собирается плоскими панелями по сегментам:
ни одной операции, способной молча испортить геометрию.

Плотность выборки задаёт гладкость: при шаге в пару метров гранёность
борта на рендере не читается, а число тел остаётся вменяемым.
"""

from __future__ import annotations

import math

from cadgen import build123d as bd
from scipy.interpolate import PchipInterpolator

from . import ship
from .furniture import _part


def half_beam_curve(stations):
    """Монотонная кривая полушироты по длине.

    Pchip, а не обычный кубический сплайн: обычный на редких узлах даёт
    выбросы между ними, и борт волнами уходит наружу за габарит.
    """
    xs = [x for x, _ in stations]
    ys = [y for _, y in stations]
    return PchipInterpolator(xs, ys)


def contour(stations, step=1_800):
    """Замкнутый контур палубы: правый борт от кормы к носу и обратно."""
    curve = half_beam_curve(stations)
    x0, x1 = stations[0][0], stations[-1][0]
    count = max(8, int((x1 - x0) / step))
    samples = [x0 + (x1 - x0) * i / count for i in range(count + 1)]

    right = [(x, float(curve(x))) for x in samples]
    right = [(x, y) for x, y in right if y > 1]
    right = simplify(right)
    left = [(x, -y) for x, y in reversed(right)]
    return right + left


def simplify(points, tolerance=25.0):
    """Проредить полилинию, не уводя её от исходного обвода (Дуглас–Пекер).

    На цилиндрической вставке полуширота постоянна, и равномерная выборка
    плодит там десятки одинаковых панелей: они ничего не добавляют картинке,
    но умножают время сборки и вес STEP. Скругления при этом остаются
    плотными — там точки не коллинеарны.

    Отклонение считается от хорды между СОХРАНЁННЫМИ концами, а не от линии
    через соседей выброшенной точки. Проверка по соседям накапливает ошибку:
    каждая точка длинного пологого участка коллинеарна своим соседям с
    точностью до долей миллиметра, и участок схлопывается целиком. Ровно это
    и случилось с променадом главной палубы: 114 метров борта стянуло в одну
    хорду, и настил с ограждением ушли внутрь корпуса почти на метр в
    середине судна, а на виде с уровня глаз человек оказался за леерами.
    """
    if len(points) < 3:
        return list(points)

    keep = [False] * len(points)
    keep[0] = keep[-1] = True
    stack = [(0, len(points) - 1)]
    while stack:
        first, last = stack.pop()
        if last - first < 2:
            continue
        (x1, y1), (x2, y2) = points[first], points[last]
        span = math.hypot(x2 - x1, y2 - y1)
        worst, at = -1.0, first
        for index in range(first + 1, last):
            x, y = points[index]
            if span < 1e-9:
                offset = math.hypot(x - x1, y - y1)
            else:
                offset = abs((x2 - x1) * (y1 - y) - (x1 - x) * (y2 - y1)) / span
            if offset > worst:
                worst, at = offset, index
        if worst > tolerance:
            keep[at] = True
            stack.append((first, at))
            stack.append((at, last))
    return [point for point, taken in zip(points, keep) if taken]


def inset(points, amount):
    """Сдвинуть контур на amount ПО НОРМАЛИ: внутрь при amount > 0.

    Численно, а не kernel-offset: на плотных контурах offset возвращает
    Null. И именно по нормали, а не по оси Y: на прямом борту это одно и
    то же, но на скруглениях носа и кормы сегмент идёт под углом, и сдвиг
    по Y уводит точку вдоль контура вместо поперёк — карниз тогда садится
    прямо во фриз, хотя по числам «отстоит» на нужную величину.
    """
    if len(points) < 3:
        return list(points)

    result = []
    count = len(points)
    for index, (x, y) in enumerate(points):
        px, py = points[index - 1]
        nx, ny = points[(index + 1) % count]

        normal_x, normal_y = 0.0, 0.0
        for (ax, ay), (bx, by) in (((px, py), (x, y)), ((x, y), (nx, ny))):
            dx, dy = bx - ax, by - ay
            length = math.hypot(dx, dy)
            if length < 1e-6:
                continue
            # Нормаль НАРУЖУ. Контур обходится против часовой: правый борт
            # от кормы к носу, затем левый обратно, — поэтому наружу
            # смотрит (-dy, dx), а не (dy, -dx). На прямом борту знак не
            # виден, а на скруглениях уводит вынос внутрь корпуса.
            normal_x += -dy / length
            normal_y += dx / length
        norm = math.hypot(normal_x, normal_y)
        if norm < 1e-6:
            result.append((x, y))
            continue
        normal_x, normal_y = normal_x / norm, normal_y / norm

        shifted = (x - normal_x * amount, y - normal_y * amount)
        if abs(shifted[1]) < 150:
            continue
        result.append(shifted)
    return result


def clip_to_hull(points, margin=0.0):
    """Ограничить контур обводом КОРПУСА по палубе.

    Всё, что выносится наружу от надстройки — карнизы, полки, привальные
    брусья, — в оконечностях упирается в то, что корпус там уже. Обрезка по
    корпусу оставляет вынос ровно там, где под ним есть борт.
    """
    from scipy.interpolate import PchipInterpolator

    from . import ship

    xs = [row[0] for row in ship.STATIONS]
    curve = PchipInterpolator(xs, [row[3] for row in ship.STATIONS])

    result = []
    for x, y in points:
        limit = float(curve(min(max(x, xs[0]), xs[-1]))) - margin
        if limit <= 200:
            continue
        result.append((x, min(y, limit) if y > 0 else max(y, -limit)))
    return result


def deck_face(points, z):
    """Палубная плита по контуру."""
    wire = bd.Polyline(*[(x, y, z) for x, y in points], close=True)
    return bd.make_face(wire)


def deck_slab(points, z, thickness=120, color=None, material=None,
              label="палуба"):
    from . import deckhouse as dh

    slab = bd.extrude(deck_face(points, z - thickness), thickness)
    slab.color = color or dh.DECK_PAINT
    slab.cad_material = dict(material or dh.MAT_TEAK)
    slab.label = label
    return slab


def band(points, z, height, thickness, color, material, label,
         skip_short=400.0, tilt=0.0):
    """Пояс по контуру: по одной плоской панели на сегмент.

    Панель ставится серединой на сегмент и разворачивается по его
    направлению, поэтому пояс идёт и по скруглённой корме, и по носовому
    сужению — там, где прямоугольная надстройка обрывалась бы уступом.
    """
    parts = []
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length < skip_short:
            continue
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        # Панель длиннее сегмента на толщину и потому перекрывается с
        # соседней в углу обвода — это намеренно: иначе на каждом изломе
        # контура остаётся щель шириной в толщину борта. Проверка коллизий
        # видит здесь перекрытие, и это ожидаемо.
        # Панель ложится НАРУЖУ от линии обвода, а не по центру на неё:
        # внутренняя грань борта тогда совпадает с контуром, и настилы кают,
        # доведённые до той же линии, в борт не врезаются.
        panel = _part(length + thickness, thickness, height,
                      (-(length + thickness) / 2, 0, 0),
                      color, material, label)
        # tilt заваливает панель внутрь вокруг оси сегмента: положительный
        # угол уводит верх к диаметральной плоскости. Вертикальный борт по
        # всей высоте — примета судов прошлого поколения; завал верхней
        # ленты даёт подрез под палубой и ломает сплошную вертикаль.
        placed = (bd.Pos((x1 + x2) / 2, (y1 + y2) / 2, z)
                  * bd.Rot(0, 0, angle) * bd.Rot(tilt, 0, 0) * panel)
        placed.label = label
        placed.color = panel.color
        placed.cad_material = dict(material)
        parts.append(placed)
    return parts


def side_runs(points, min_x, max_x, min_half_beam):
    """Прямые бортовые участки — только на них имеет смысл ставить окна кают.

    На скруглениях носа и кормы шаг простенков в модуль каюты не работает:
    там за бортом не каюты, а общественные помещения и открытые площадки.
    """
    # Сегмент ОБРЕЗАЕТСЯ по окну, а не отбрасывается целиком: после
    # упрощения контура весь прямой борт — один сегмент во всю длину, и
    # проверка «оба конца внутри окна» не пропускала ни одного.
    runs = {"right": [], "left": []}
    for (x1, y1), (x2, y2) in zip(points, points[1:]):
        if abs(y1) < min_half_beam or abs(y2) < min_half_beam:
            continue
        lo, hi = min(x1, x2), max(x1, x2)
        start, end = max(lo, min_x), min(hi, max_x)
        if end - start < 2_000:
            continue
        side = "right" if y1 > 0 else "left"
        y = (y1 + y2) / 2
        runs[side].append(((start, y), (end, y)))
    return runs


def glass_railing(points, z, height=1_100, panel_gap=40):
    """Стеклянное ограждение по контуру: панель во всю длину и поручень.

    Частые леерные стойки — примета судов прошлого поколения; на
    современных открытых палубах ставят сплошное стекло, и силуэт от этого
    читается как единый объём, а не как решётка.
    """
    from . import deckhouse as dh

    parts = band(points, z, height - 60, 26, dh.GLASS_RAIL, dh.MAT_GLASS,
                 "ограждение стеклянное")
    parts += band(points, z + height - 60, 60, 90, dh.RAIL, dh.MAT_METAL,
                  "поручень")
    return parts


def eaves(points, z, reach=320, thickness=90, color=None, material=None,
          label="карниз"):
    """Выносная полка по контуру палубы.

    Горизонтальная артикуляция: полка отбивает палубу от палубы, и борт
    перестаёт читаться сплошной стеной остекления в четыре этажа.
    """
    from . import deckhouse as dh

    return band(points, z, thickness, reach, color or dh.SUPERSTRUCTURE,
                material or dh.MAT_PAINT, label)


def railing(points, z, height=1_100, post_step=2_400):
    """Леера по контуру: стойки с шагом вдоль обвода и два поручня.

    Прямоугольный леер на сужающемся корпусе уезжает за борт в носу — на
    перспективе это читается как часть силуэта, а на виде сверху его
    закрывает палуба. По контуру стойки стоят там, где палуба есть.
    """
    from . import deckhouse as dh

    parts = []
    carry = 0.0
    for (x1, y1), (x2, y2) in zip(points, points[1:] + points[:1]):
        length = math.hypot(x2 - x1, y2 - y1)
        if length < 1:
            continue
        angle = math.degrees(math.atan2(y2 - y1, x2 - x1))
        for rail_z in (height * 0.45, height * 0.95):
            rail = _part(length, 55, 55, (-length / 2, -27, 0),
                         dh.RAIL, dh.MAT_METAL, "поручень")
            placed = bd.Pos((x1 + x2) / 2, (y1 + y2) / 2, z + rail_z) * \
                bd.Rot(0, 0, angle) * rail
            placed.label, placed.color = "поручень", dh.RAIL
            placed.cad_material = dict(dh.MAT_METAL)
            parts.append(placed)

        position = post_step - carry
        while position < length:
            t = position / length
            post = _part(60, 60, height,
                         (x1 + (x2 - x1) * t - 30, y1 + (y2 - y1) * t - 30, z),
                         dh.RAIL, dh.MAT_METAL, "стойка леера")
            parts.append(post)
            position += post_step
        carry = (carry + length) % post_step
    return parts
