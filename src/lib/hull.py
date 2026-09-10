"""Обводы корпуса: шпангоуты из lib.ship и лофт по ним.

Лофт сшивает сечения ПО ИНДЕКСУ точки, поэтому каждый шпангоут обязан иметь
одинаковое число точек в одном и том же порядке. Отсюда единственная функция
station(): она задаёт форму координатами, а не числом узлов — иначе на первой
же правке обводов лофт свернёт борт внутрь и никакая проверка это не поймает.
"""

from cadgen import build123d as bd
from scipy.interpolate import PchipInterpolator

from . import ship


def station(x, b_bottom, b_bilge, b_deck, z_bilge, z_keel, z_deck):
    """Один шпангоут: замкнутый контур в плоскости x = const, 11 точек.

    Число точек одинаково у всех шпангоутов и порядок один: лофт сшивает
    сечения по индексу точки, и стоит одному сечению получить другую
    разбивку, как борт свернётся внутрь без единой ошибки в логе.
    """
    knuckle = z_bilge + 1_100
    mid_y = b_bilge - (b_bilge - b_bottom) * 0.35
    mid_z = z_keel + (z_bilge - z_keel) * 0.34
    pts = [
        (x, -b_deck, z_deck),
        (x, -b_deck, knuckle),
        (x, -b_bilge, z_bilge),
        (x, -mid_y, mid_z),
        (x, -b_bottom, z_keel),
        (x, 0, z_keel),
        (x, b_bottom, z_keel),
        (x, mid_y, mid_z),
        (x, b_bilge, z_bilge),
        (x, b_deck, knuckle),
        (x, b_deck, z_deck),
    ]
    return bd.make_face(bd.Polyline(*pts, close=True))


def interpolated_stations(step=3_000):
    """Сгустить таблицу шпангоутов монотонной интерполяцией.

    Сглаженный лофт по редким шпангоутам выпучивает борт между ними: при
    полушироте 8.06 м габарит выходил 17.32 м вместо 16.8, и запас до стенки
    шлюза таял незаметно. Лечится не подгонкой полуширот, а сменой схемы:
    частые сечения плюс ЛИНЕЙЧАТЫЙ лофт. Тогда обвод нигде не выходит за
    таблицу, а гладкость даёт монотонная интерполяция, а не кернел.
    """
    xs = [row[0] for row in ship.STATIONS]
    curves = [PchipInterpolator(xs, [row[i] for row in ship.STATIONS])
              for i in range(1, 7)]
    count = max(len(xs), int((xs[-1] - xs[0]) / step))
    samples = [xs[0] + (xs[-1] - xs[0]) * i / count for i in range(count + 1)]
    return [(x, *(float(curve(x)) for curve in curves)) for x in samples]


def hull_solid():
    """Корпус целиком, от транца до форштевня."""
    return bd.loft([station(*row) for row in interpolated_stations()],
                   ruled=True)


def displacement(solid=None, draft=None, density=1.0):
    """Водоизмещение по геометрии, а не по коэффициенту полноты.

    Отсекает подводную часть плоскостью осадки и меряет её объём. Возвращает
    объём, массу и фактический коэффициент общей полноты — последний нужен,
    чтобы сверить обводы с судами-аналогами.
    """
    solid = hull_solid() if solid is None else solid
    draft = ship.DRAFT if draft is None else draft

    box = solid.bounding_box()
    below = solid & bd.Pos(
        box.center().X, 0, draft / 2
    ) * bd.Box(box.size.X + 1_000, box.size.Y + 1_000, draft)

    volume = below.volume / 1e9  # м³
    waterline = below.bounding_box()
    block = (waterline.size.X / 1000) * (ship.HULL_BEAM / 1000) * (draft / 1000)
    return {
        "volume": volume,
        "mass": volume * density,
        "length_wl": waterline.size.X / 1000,
        "cb": volume / block,
    }


def checks(solid=None):
    """Проверки корпуса против ограничений трассы.

    Это ответ на вопрос эксперта «а пройдёт ли». Считается по геометрии
    модели, а не по заявленным размерениям, поэтому ловит и то, что сглаженный
    лофт выпучил борт между шпангоутами шире, чем задано в таблице.
    """
    solid = hull_solid() if solid is None else solid
    box = solid.bounding_box()
    beam = box.size.Y

    from .vessel import air_draft, build

    assembled = build()
    stowed = air_draft(assembled, mast_raised=False)
    raised = air_draft(assembled, mast_raised=True)

    return [
        ("ширина в камере шлюза", beam, ship.LOCK_WIDTH, beam <= ship.LOCK_WIDTH),
        ("осадка на гарантированной глубине", ship.DRAFT, ship.FAIRWAY_DEPTH,
         ship.DRAFT <= ship.FAIRWAY_DEPTH),
        ("высота с заваленной мачтой", stowed, ship.BRIDGE_CLEARANCE,
         stowed <= ship.BRIDGE_CLEARANCE),
        ("высота с поднятой мачтой", raised, ship.BRIDGE_CLEARANCE,
         raised <= ship.BRIDGE_CLEARANCE),
    ]
