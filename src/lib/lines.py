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
    """Выбросить точки, лежащие на прямой между соседями.

    На цилиндрической вставке полуширота постоянна, и равномерная выборка
    плодит там десятки одинаковых панелей: они ничего не добавляют картинке,
    но умножают время сборки и вес STEP. Скругления при этом остаются
    плотными — там точки не коллинеарны.
    """
    if len(points) < 3:
        return points
    kept = [points[0]]
    for previous, current, following in zip(points, points[1:], points[2:]):
        (x1, y1), (x2, y2), (x3, y3) = previous, current, following
        span = math.hypot(x3 - x1, y3 - y1)
        if span == 0:
            continue
        offset = abs((x3 - x1) * (y1 - y2) - (x1 - x2) * (y3 - y1)) / span
        if offset > tolerance:
            kept.append(current)
    kept.append(points[-1])
    return kept


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
         skip_short=400.0):
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
        panel = _part(length + thickness, thickness, height,
                      (-(length + thickness) / 2, -thickness / 2, 0),
                      color, material, label)
        placed = bd.Pos((x1 + x2) / 2, (y1 + y2) / 2, z) * bd.Rot(0, 0, angle) * panel
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
