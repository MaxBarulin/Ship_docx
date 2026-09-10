"""Обводы корпуса: шпангоуты из lib.ship и лофт по ним.

Лофт сшивает сечения ПО ИНДЕКСУ точки, поэтому каждый шпангоут обязан иметь
одинаковое число точек в одном и том же порядке. Отсюда единственная функция
station(): она задаёт форму координатами, а не числом узлов — иначе на первой
же правке обводов лофт свернёт борт внутрь и никакая проверка это не поймает.
"""

from cadgen import build123d as bd

from . import ship


def station(x, b_bottom, b_bilge, b_deck, z_bilge, z_keel, z_deck):
    """Один шпангоут: замкнутый контур в плоскости x = const, 9 точек."""
    pts = [
        (x, -b_deck, z_deck),
        (x, -b_deck, z_bilge + 1_100),
        (x, -b_bilge, z_bilge),
        (x, -b_bottom, z_keel),
        (x, 0, z_keel),
        (x, b_bottom, z_keel),
        (x, b_bilge, z_bilge),
        (x, b_deck, z_bilge + 1_100),
        (x, b_deck, z_deck),
    ]
    return bd.make_face(bd.Polyline(*pts, close=True))


def hull_solid():
    """Корпус целиком, от транца до форштевня."""
    return bd.loft([station(*row) for row in ship.STATIONS])


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

    stowed = ship.air_draft(mast_height=0)  # мачта завалена
    raised = ship.air_draft()

    return [
        ("ширина в камере шлюза", beam, ship.LOCK_WIDTH, beam <= ship.LOCK_WIDTH),
        ("осадка на гарантированной глубине", ship.DRAFT, ship.FAIRWAY_DEPTH,
         ship.DRAFT <= ship.FAIRWAY_DEPTH),
        ("высота с заваленной мачтой", stowed, ship.BRIDGE_CLEARANCE,
         stowed <= ship.BRIDGE_CLEARANCE),
        ("высота с поднятой мачтой", raised, ship.BRIDGE_CLEARANCE,
         raised <= ship.BRIDGE_CLEARANCE),
    ]
