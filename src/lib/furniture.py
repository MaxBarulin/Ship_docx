"""Библиотека судовой мебели и оборудования каюты.

Система координат каюты: X вдоль борта, Y поперёк судна от борта вглубь,
Z вверх от чистого пола. Каждый элемент строится от своего левого ближнего
нижнего угла, поэтому ставится в каюту одним Pos(x, y, z) без арифметики.

Размеры — судовые, а не «мебельные из каталога»: койка 900 мм, проход у койки
не меньше 700 мм, санблок собран вокруг реального душевого поддона 900x900.
"""

from cadgen import build123d as bd

from . import palette as p


def block(w: float, d: float, h: float):
    """Параллелепипед с углом в начале координат, а не центром."""
    return bd.Pos(w / 2, d / 2, h / 2) * bd.Box(w, d, h)


def _part(w, d, h, at, color, material, label):
    x, y, z = at
    return p.finish(bd.Pos(x, y, z) * block(w, d, h), color, material, label)


# --- Спальные места --------------------------------------------------------

def berth(width=900, length=2000, textile=None):
    """Одиночная койка: подиум с ящиками, матрас, бельё, подушка."""
    textile = textile or p.TEXTILE_BLUE
    base = _part(width, length, 300, (0, 0, 0), p.WOOD_LIGHT, p.MAT_WOOD, "подиум")
    mattress = _part(width - 40, length - 40, 180, (20, 20, 300),
                     p.LINEN, p.MAT_TEXTILE, "матрас")
    cover = _part(width - 40, length - 700, 40, (20, 20, 480),
                  textile, p.MAT_TEXTILE, "покрывало")
    pillow = _part(width - 240, 380, 110, (120, 90, 480),
                   p.LINEN, p.MAT_TEXTILE, "подушка")
    return bd.Compound(children=[base, mattress, cover, pillow], label="койка")


def bunk(width=900, length=2000, upper_z=1450, textile=None):
    """Двухъярусная койка эконома: нижняя, верхняя на стойках, леер, трап."""
    textile = textile or p.TEXTILE_BLUE
    lower = berth(width, length, textile).moved(bd.Location((0, 0, 0)))
    lower.label = "нижняя койка"

    deck = _part(width, length, 60, (0, 0, upper_z), p.WOOD_LIGHT, p.MAT_WOOD, "настил")
    mattress = _part(width - 40, length - 40, 180, (20, 20, upper_z + 60),
                     p.LINEN, p.MAT_TEXTILE, "матрас")
    cover = _part(width - 40, length - 700, 40, (20, 20, upper_z + 240),
                  textile, p.MAT_TEXTILE, "покрывало")
    pillow = _part(width - 240, 380, 110, (120, 90, upper_z + 240),
                   p.LINEN, p.MAT_TEXTILE, "подушка")
    rail = _part(60, length - 500, 350, (width, 250, upper_z + 60),
                 p.METAL, p.MAT_METAL, "леер")
    posts = [
        _part(60, 60, upper_z, (width, y, 0), p.METAL, p.MAT_METAL, "стойка")
        for y in (0, length - 60)
    ]
    ladder = _part(60, 340, upper_z + 300, (width, length - 400, 0),
                   p.METAL, p.MAT_METAL, "трап")
    return bd.Compound(
        children=[lower, deck, mattress, cover, pillow, rail, ladder, *posts],
        label="койка двухъярусная",
    )


def double_bed(width=1600, length=2000, textile=None, wood=None):
    """Двуспальная кровать с изголовьем."""
    textile = textile or p.TEXTILE_TEAL
    wood = wood or p.WOOD_DARK
    base = _part(width, length, 320, (0, 0, 0), wood, p.MAT_WOOD, "основание")
    mattress = _part(width - 60, length - 60, 220, (30, 30, 320),
                     p.LINEN, p.MAT_TEXTILE, "матрас")
    runner = _part(width - 60, 700, 45, (30, length - 760, 540),
                   textile, p.MAT_TEXTILE, "покрывало")
    pillows = [
        _part(width / 2 - 140, 420, 130, (60 + i * (width / 2 + 20), 80, 540),
              p.LINEN, p.MAT_TEXTILE, "подушка")
        for i in range(2)
    ]
    headboard = _part(width, 80, 1050, (0, -80, 0), textile, p.MAT_TEXTILE, "изголовье")
    return bd.Compound(children=[base, mattress, runner, headboard, *pillows],
                       label="кровать двуспальная")


# --- Корпусная мебель ------------------------------------------------------

def wardrobe(width=800, depth=600, height=2000, wood=None):
    """Шкаф: корпус, две дверцы, ручки."""
    wood = wood or p.WOOD_LIGHT
    body = _part(width, depth, height, (0, 0, 0), wood, p.MAT_WOOD, "корпус")
    leaves = [
        _part(width / 2 - 15, 25, height - 100,
              (10 + i * (width / 2), depth, 50), p.LAMINATE, p.MAT_LACQUER, "дверца")
        for i in range(2)
    ]
    handles = [
        _part(25, 25, 320, (width / 2 - 45 + i * 60, depth + 25, height / 2),
              p.METAL, p.MAT_METAL, "ручка")
        for i in range(2)
    ]
    return bd.Compound(children=[body, *leaves, *handles], label="шкаф")


def nightstand(width=420, depth=400, height=560, wood=None):
    wood = wood or p.WOOD_LIGHT
    body = _part(width, depth, height, (0, 0, 0), wood, p.MAT_WOOD, "корпус")
    drawer = _part(width - 40, 20, 160, (20, depth, height - 220),
                   p.LAMINATE, p.MAT_LACQUER, "ящик")
    return bd.Compound(children=[body, drawer], label="тумба")


def desk(width=1100, depth=480, height=740, wood=None):
    """Столешница на боковинах — судовая мебель крепится к переборке."""
    wood = wood or p.WOOD_LIGHT
    top = _part(width, depth, 40, (0, 0, height - 40), wood, p.MAT_WOOD, "столешница")
    sides = [
        _part(40, depth, height - 40, (x, 0, 0), wood, p.MAT_WOOD, "боковина")
        for x in (0, width - 40)
    ]
    return bd.Compound(children=[top, *sides], label="стол")


def chair(width=440, depth=480, textile=None, wood=None):
    textile = textile or p.TEXTILE_BLUE
    wood = wood or p.WOOD_DARK
    seat = _part(width, depth, 60, (0, 0, 420), textile, p.MAT_TEXTILE, "сиденье")
    back = _part(width, 60, 420, (0, depth - 60, 480), textile, p.MAT_TEXTILE, "спинка")
    legs = [
        _part(45, 45, 420, (x, y, 0), wood, p.MAT_WOOD, "ножка")
        for x in (0, width - 45) for y in (0, depth - 45)
    ]
    return bd.Compound(children=[seat, back, *legs], label="стул")


def armchair(width=760, depth=760, textile=None):
    textile = textile or p.TEXTILE_SAND
    base = _part(width, depth, 340, (0, 0, 60), textile, p.MAT_TEXTILE, "основание")
    cushion = _part(width - 200, depth - 120, 130, (100, 40, 400),
                    textile, p.MAT_TEXTILE, "подушка")
    back = _part(width, 160, 500, (0, depth - 160, 400), textile, p.MAT_TEXTILE, "спинка")
    arms = [
        _part(100, depth - 160, 240, (x, 0, 340), textile, p.MAT_TEXTILE, "подлокотник")
        for x in (0, width - 100)
    ]
    feet = [
        _part(70, 70, 60, (x, y, 0), p.METAL, p.MAT_METAL, "опора")
        for x in (30, width - 100) for y in (30, depth - 100)
    ]
    return bd.Compound(children=[base, cushion, back, *arms, *feet], label="кресло")


def sofa(width=1900, depth=820, textile=None):
    textile = textile or p.TEXTILE_WINE
    base = _part(width, depth, 340, (0, 0, 60), textile, p.MAT_TEXTILE, "основание")
    seats = [
        _part(width / 2 - 130, depth - 180, 140, (110 + i * (width / 2 - 60), 40, 400),
              textile, p.MAT_TEXTILE, "подушка сиденья")
        for i in range(2)
    ]
    back = _part(width, 180, 520, (0, depth - 180, 400), textile, p.MAT_TEXTILE, "спинка")
    arms = [
        _part(110, depth - 180, 260, (x, 0, 340), textile, p.MAT_TEXTILE, "подлокотник")
        for x in (0, width - 110)
    ]
    feet = [
        _part(70, 70, 60, (x, y, 0), p.WOOD_DARK, p.MAT_WOOD, "опора")
        for x in (40, width - 110) for y in (40, depth - 110)
    ]
    return bd.Compound(children=[base, back, *seats, *arms, *feet], label="диван")


def coffee_table(width=900, depth=560, height=420, wood=None):
    wood = wood or p.WOOD_DARK
    top = _part(width, depth, 35, (0, 0, height - 35), wood, p.MAT_LACQUER, "столешница")
    stem = _part(160, 160, height - 35, ((width - 160) / 2, (depth - 160) / 2, 0),
                 p.METAL, p.MAT_METAL, "опора")
    return bd.Compound(children=[top, stem], label="столик")


def tv_panel(width=1100, height=620, thickness=45):
    screen = _part(width, thickness, height, (0, 0, 0), bd.Color(0.02, 0.02, 0.02),
                   p.MAT_LACQUER, "экран")
    return bd.Compound(children=[screen], label="телевизор")


def luggage_rack(width=900, depth=520, height=60, wood=None):
    wood = wood or p.WOOD_LIGHT
    shelf = _part(width, depth, height, (0, 0, 0), wood, p.MAT_WOOD, "полка")
    return bd.Compound(children=[shelf], label="багажная полка")


def ceiling_light(diameter=260):
    lamp = p.finish(
        bd.Pos(0, 0, -30) * bd.Cylinder(diameter / 2, 60),
        p.LINEN, p.MAT_LACQUER, "плафон",
    )
    return bd.Compound(children=[lamp], label="светильник")


# --- Санитарный блок -------------------------------------------------------

def bath_pod(width=1500, depth=1700, height=2200, wet_stone=None, door_side="right"):
    """Санблок как готовый модуль — так он и ставится на судно.

    Собственные переборки, дверь, душевой уголок со стеклом, унитаз, раковина
    со столешницей и зеркало. Стенка со стороны каюты не ставится: модуль
    прислоняется к переборке каюты.

    door_side говорит, с какой стороны навешена дверь — от этого зависит,
    в какую сторону модуль открывается в каюту.
    """
    wet_stone = wet_stone or p.STONE
    t = 60
    walls = [
        _part(t, depth, height, (0, 0, 0), p.SANITARY, p.MAT_CERAMIC, "переборка"),
        _part(width, t, height, (0, depth - t, 0), p.SANITARY, p.MAT_CERAMIC, "переборка"),
        _part(t, depth - 900, height, (width - t, 900, 0),
              p.SANITARY, p.MAT_CERAMIC, "переборка"),
    ]
    floor = _part(width, depth, 30, (0, 0, 0), p.FLOOR_TILE, p.MAT_CERAMIC, "пол")

    door = _part(20, 820, 2000, (width - t, 40, 0), p.GLASS_SHOWER, p.MAT_GLASS, "дверь")

    tray = _part(900, 900, 90, (t, depth - t - 900, 30),
                 wet_stone, p.MAT_CERAMIC, "поддон")
    screen = _part(20, 900, 1900, (t + 900, depth - t - 900, 120),
                   p.GLASS_SHOWER, p.MAT_GLASS, "стекло душа")
    riser = _part(60, 60, 1100, (t + 60, depth - t - 160, 1000),
                  p.METAL, p.MAT_METAL, "стойка душа")

    bowl = _part(360, 560, 400, (width - 600, 100, 30),
                 p.SANITARY, p.MAT_CERAMIC, "унитаз")
    cistern = _part(360, 180, 480, (width - 600, 100, 430),
                    p.SANITARY, p.MAT_CERAMIC, "бачок")

    counter = _part(width - 2 * t, 480, 40, (t, 0, 850),
                    wet_stone, p.MAT_CERAMIC, "столешница")
    basin = p.finish(
        bd.Pos(t + 260, 240, 950) * bd.Cylinder(190, 120),
        p.SANITARY, p.MAT_CERAMIC, "раковина",
    )
    tap = _part(45, 45, 260, (t + 240, 60, 890), p.METAL, p.MAT_METAL, "смеситель")
    mirror = _part(width - 2 * t - 200, 20, 900, (t + 100, 0, 1150),
                   p.GLASS, p.MAT_GLASS, "зеркало")

    pod = bd.Compound(
        children=[*walls, floor, door, tray, screen, riser, bowl, cistern,
                  counter, basin, tap, mirror],
        label="санблок",
    )
    if door_side == "left":
        pod = bd.Pos(width, 0, 0) * bd.Rot(0, 0, 180) * bd.Pos(0, -depth, 0) * pod
        pod.label = "санблок"
    return pod


# --- Доступная среда -------------------------------------------------------

def grab_rail(length=800, vertical=False, diameter=40):
    """Поручень. Ставится там, где человек переносит вес: у унитаза,
    в душе, у кровати."""
    if vertical:
        bar = _part(diameter, diameter, length, (0, 0, 0),
                    p.METAL, p.MAT_METAL, "поручень")
    else:
        bar = _part(length, diameter, diameter, (0, 0, 0),
                    p.METAL, p.MAT_METAL, "поручень")
    return bd.Compound(children=[bar], label="поручень")


def shower_seat(width=450, depth=400):
    """Откидное сиденье в душе на высоте пересадки."""
    seat = _part(width, depth, 60, (0, 0, 480), p.LAMINATE, p.MAT_LACQUER,
                 "сиденье")
    bracket = _part(60, depth - 80, 200, (0, 40, 280),
                    p.METAL, p.MAT_METAL, "кронштейн")
    return bd.Compound(children=[seat, bracket], label="сиденье душевое")


def accessible_pod(width=2_400, depth=2_300, height=2_200, door_side="right"):
    """Санблок для маломобильных.

    Отличается от обычного не размером, а устройством: душ без поддона и
    порога (вода уходит в трап в полу), унитаз с боковым подходом под
    кресло, раковина без тумбы — под неё должны заезжать колени, — и
    поручни у каждой точки, где человек переносит вес.
    """
    t = 60
    walls = [
        _part(t, depth, height, (0, 0, 0), p.SANITARY, p.MAT_CERAMIC, "переборка"),
        _part(width, t, height, (0, depth - t, 0), p.SANITARY, p.MAT_CERAMIC,
              "переборка"),
        _part(t, depth - 1_100, height, (width - t, 1_100, 0),
              p.SANITARY, p.MAT_CERAMIC, "переборка"),
    ]
    floor = _part(width, depth, 30, (0, 0, 0), p.FLOOR_TILE, p.MAT_CERAMIC,
                  "пол без порога")
    drain = p.finish(bd.Pos(t + 600, depth - t - 600, 30) * bd.Cylinder(90, 20),
                     p.METAL, p.MAT_METAL, "трап")

    # душ: только штора и стойка, ни поддона, ни бортика
    riser = _part(60, 60, 1_100, (t + 60, depth - t - 120, 1_000),
                  p.METAL, p.MAT_METAL, "стойка душа")
    curtain = _part(20, 1_200, 1_900, (t + 1_300, depth - t - 1_200, 200),
                    p.GLASS_SHOWER, p.MAT_GLASS, "штора")

    bowl = _part(380, 580, 450, (width - 900, 120, 30),
                 p.SANITARY, p.MAT_CERAMIC, "унитаз")
    cistern = _part(380, 200, 500, (width - 900, 120, 480),
                    p.SANITARY, p.MAT_CERAMIC, "бачок")

    # раковина консольная: под ней пусто, чтобы подъехать на кресле
    basin = _part(650, 480, 140, (t + 120, 0, 780), p.SANITARY, p.MAT_CERAMIC,
                  "раковина консольная")
    tap = _part(45, 45, 240, (t + 420, 60, 920), p.METAL, p.MAT_METAL,
                "смеситель")
    mirror = _part(700, 20, 1_000, (t + 100, 0, 980), p.GLASS, p.MAT_GLASS,
                   "зеркало")

    rails = [
        place_rail(grab_rail(900), width - 1_000, 60, 850),
        place_rail(grab_rail(700, vertical=True), width - 1_050, 700, 800),
        place_rail(grab_rail(800), t + 100, depth - t - 80, 900),
        place_rail(grab_rail(600, vertical=True), t + 80, depth - t - 700, 900),
    ]
    seat = bd.Pos(t + 200, depth - t - 500, 0) * shower_seat()
    seat.label = "сиденье душевое"

    pod = bd.Compound(
        children=[*walls, floor, drain, riser, curtain, bowl, cistern,
                  basin, tap, mirror, seat, *rails],
        label="санблок доступный",
    )
    if door_side == "left":
        pod = bd.Pos(width, 0, 0) * bd.Rot(0, 0, 180) * bd.Pos(0, -depth, 0) * pod
        pod.label = "санблок доступный"
    return pod


def place_rail(rail, x, y, z):
    moved = bd.Pos(x, y, z) * rail
    moved.label = rail.label
    return moved
