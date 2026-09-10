"""Мебель и оборудование общественных зон.

Средняя детализация: узнаваемый силуэт и правильный габарит, без обивки и
фурнитуры. На разрезе и на виде сверху важно, что зона занята мебелью
такого-то шага и на столько-то мест — по этому считается вместимость зала,
а не то, как выглядит спинка стула.

Каждый элемент строится от левого ближнего нижнего угла, как и судовая
мебель в lib.furniture, поэтому ставится одним Pos(x, y, z).
"""

import math

from cadgen import build123d as bd
from cadgen import srgb

from .furniture import _part, block

WOOD = srgb("#7E5B38")
WOOD_DARK = srgb("#6B4A32")
TEXTILE = srgb("#2F5A6B")
TEXTILE_WARM = srgb("#9C6B4A")
METAL = srgb("#AFB4B8")
STONE = srgb("#C9C4BB")
WATER = srgb("#4E93B8", 0.55)
DARK = srgb("#2A2E33")
GREEN = srgb("#2F6156")

MAT_WOOD = {"roughness": 0.45, "metalness": 0.0, "clearcoat": 0.3}
MAT_TEXTILE = {"roughness": 0.95, "metalness": 0.0}
MAT_METAL = {"roughness": 0.3, "metalness": 0.85}
MAT_STONE = {"roughness": 0.35, "metalness": 0.0}
MAT_WATER = {"roughness": 0.05, "metalness": 0.0}


def dining_set(diameter=1_100, seats=4):
    """Круглый стол с креслами — базовый модуль ресторана."""
    top = _part(diameter, diameter, 60, (0, 0, 700), WOOD, MAT_WOOD,
                "стол обеденный")
    stem = _part(180, 180, 700, ((diameter - 180) / 2, (diameter - 180) / 2, 0),
                 METAL, MAT_METAL, "опора стола")
    parts = [top, stem]
    offsets = [(-700, diameter / 2 - 220), (diameter + 260, diameter / 2 - 220),
               (diameter / 2 - 220, -700), (diameter / 2 - 220, diameter + 260)]
    for index in range(min(seats, 4)):
        dx, dy = offsets[index]
        # сиденье и спинка вместо куба: куб на четырёх углах стола читается
        # как коробка, а не как посадочное место
        parts.append(_part(460, 460, 60, (dx, dy, 420), TEXTILE, MAT_TEXTILE,
                           "сиденье"))
        parts.append(_part(460, 90, 480, (dx, dy + (0 if dy < 0 else 370), 420),
                           TEXTILE, MAT_TEXTILE, "спинка кресла"))
        for foot_x in (dx + 40, dx + 360):
            parts.append(_part(60, 60, 420, (foot_x, dy + 200, 0), METAL,
                               MAT_METAL, "опора кресла"))
    return parts


def bar_counter(length=6_000, depth=700):
    """Барная стойка с рабочим фронтом и табуретами."""
    parts = [
        _part(length, depth, 1_100, (0, 0, 0), WOOD_DARK, MAT_WOOD,
              "барная стойка"),
        _part(length, 120, 60, (0, -120, 1_100), STONE, MAT_STONE,
              "столешница бара"),
        _part(length, 500, 2_000, (0, depth + 900, 0), WOOD_DARK, MAT_WOOD,
              "бэкбар"),
    ]
    for index in range(int(length // 800)):
        parts.append(_part(380, 380, 760, (150 + index * 800, -900, 0),
                           METAL, MAT_METAL, "табурет"))
    return parts


def lounge(width=2_200):
    """Диван со столиком — модуль салона отдыха."""
    return [
        _part(width, 850, 780, (0, 0, 0), TEXTILE, MAT_TEXTILE, "диван"),
        _part(900, 550, 420, (width / 2 - 450, 1_150, 0), WOOD, MAT_WOOD,
              "столик"),
    ]


def theatre_rows(width, depth, seat_pitch=1_000, row_pitch=900):
    """Ряды кресел конференц-зала и экран перед ними."""
    parts = [_part(120, min(depth - 800, 5_000), 2_200,
                   (0, (depth - min(depth - 800, 5_000)) / 2, 400),
                   DARK, MAT_WOOD, "экран")]
    rows = int((width - 2_600) // row_pitch)
    seats = int((depth - 800) // seat_pitch)
    for row in range(rows):
        for seat in range(seats):
            parts.append(_part(600, 620, 900,
                               (2_000 + row * row_pitch,
                                400 + seat * seat_pitch, 0),
                               TEXTILE, MAT_TEXTILE, "кресло зрительное"))
    return parts


def gym_station(index=0):
    """Тренажёр: рама, платформа, стойка — силуэт читается, деталей нет."""
    return [
        _part(1_300, 800, 200, (0, 0, 0), DARK, MAT_METAL, "рама тренажёра"),
        _part(240, 700, 1_500, (1_000, 50, 200), METAL, MAT_METAL,
              "стойка тренажёра"),
        _part(700, 500, 300, (150, 150, 200), TEXTILE, MAT_TEXTILE,
              "скамья тренажёра"),
    ]


def sun_lounger():
    return [
        _part(700, 1_900, 380, (0, 0, 120), TEXTILE_WARM, MAT_TEXTILE,
              "шезлонг"),
        _part(700, 600, 500, (0, 1_300, 380), TEXTILE_WARM, MAT_TEXTILE,
              "спинка шезлонга"),
    ]


def pool(width=9_000, depth=4_600, rim=900):
    """Бассейн: приподнятая чаша, вода, обходной борт.

    Чаша стоит НА палубе, а не утоплена в неё: на судне бассейн верхней
    палубы приподнят, потому что под ним каюты, а не грунт.

    Чаша собирается ЧЕТЫРЬМЯ стенками, а не одним блоком: сплошной блок с
    водой внутри — это глухой каменный постамент, и ни воды, ни того, что
    это бассейн, с уровня глаз не видно. Борт 1.1 м над палубой, а не 1.5:
    с полутора метров вода не видна стоящему рядом человеку вообще.
    """
    wall = 350
    inner_depth = depth - 2 * wall
    return [
        _part(width, depth, 200, (0, 0, 0), STONE, MAT_STONE, "борт бассейна"),
        _part(width, wall, rim, (0, 0, 200), STONE, MAT_STONE, "стенка чаши"),
        _part(width, wall, rim, (0, depth - wall, 200), STONE, MAT_STONE,
              "стенка чаши"),
        _part(wall, inner_depth, rim, (0, wall, 200), STONE, MAT_STONE,
              "стенка чаши"),
        _part(wall, inner_depth, rim, (width - wall, wall, 200), STONE,
              MAT_STONE, "стенка чаши"),
        _part(width - 2 * wall, inner_depth, rim - 250, (wall, wall, 200),
              WATER, MAT_WATER, "вода"),
    ]

def shop_unit(width=1_000, depth=2_400):
    return [
        _part(width, depth, 1_900, (0, 0, 0), WOOD, MAT_WOOD, "стеллаж"),
    ]


def bowling_lane(length=19_000, width=1_100):
    return [
        _part(length, width, 120, (0, 0, 0), WOOD, MAT_WOOD, "дорожка боулинга"),
        _part(1_400, width, 1_600, (length, 0, 0), DARK, MAT_METAL,
              "пиншпот"),
    ]


def billiard_table():
    return [
        _part(2_600, 1_500, 800, (0, 0, 0), GREEN, MAT_TEXTILE,
              "бильярдный стол"),
    ]


def reception_desk(length=4_500):
    return [
        _part(length, 900, 1_100, (0, 0, 0), WOOD_DARK, MAT_WOOD,
              "стойка ресепшн"),
        _part(length, 120, 60, (0, -120, 1_100), STONE, MAT_STONE,
              "столешница ресепшн"),
    ]


def galley_unit(width=2_000, depth=900):
    return [
        _part(width, depth, 900, (0, 0, 0), METAL, MAT_METAL,
              "камбузное оборудование"),
        _part(width, 400, 700, (0, depth, 900), METAL, MAT_METAL, "вытяжка"),
    ]


def crew_berth():
    return [
        _part(2_000, 800, 1_700, (0, 0, 0), WOOD, MAT_WOOD,
              "койка экипажа двухъярусная"),
    ]


def main_engine(width=7_000, depth=2_600, height=2_800):
    """Главный двигатель гибридной установки на фундаменте."""
    return [
        _part(width, depth, 400, (0, 0, 0), DARK, MAT_METAL,
              "фундамент двигателя"),
        _part(width - 600, depth - 400, height - 400, (300, 200, 400),
              METAL, MAT_METAL, "главный двигатель"),
    ]


def tank(width, depth, height=1_400):
    return [
        _part(width, depth, height, (0, 0, 0), METAL, MAT_METAL, "цистерна"),
    ]


# --- Судовые системы: схематичные блоки -------------------------------------
# Не модели агрегатов, а занятое ими место с подписью. На защите вопрос
# звучит «где у вас ГРЩ и куда идёт вентиляция», и ответом служит блок в
# отсеке, а не обещание в записке.

SYSTEM = srgb("#6E7B82")
SYSTEM_HOT = srgb("#8C4A3A")
SYSTEM_COLD = srgb("#3F6E8C")
SYSTEM_ELECTRIC = srgb("#8A7A3A")


def system_block(width, depth, height, label, color=None):
    return [_part(width, depth, height, (0, 0, 0), color or SYSTEM,
                  MAT_METAL, label)]


def diesel_generator():
    return system_block(3_400, 1_600, 1_900, "дизель-генератор", SYSTEM_HOT)


def switchboard():
    return system_block(4_000, 900, 2_100, "главный распределительный щит",
                        SYSTEM_ELECTRIC)


def pump_station():
    return system_block(2_400, 1_800, 1_600,
                        "насосная: балластная, осушительная, пожарная")


def sewage_plant():
    return system_block(3_600, 2_200, 2_000,
                        "станция очистки сточных вод", SYSTEM_COLD)


def fresh_water_plant():
    return system_block(2_600, 1_800, 1_900, "водоопреснительная установка",
                        SYSTEM_COLD)


def air_conditioning():
    return system_block(3_200, 2_000, 2_100,
                        "центральный кондиционер и вентагрегаты", SYSTEM_COLD)


def steering_gear():
    return system_block(3_000, 2_600, 1_800, "рулевая машина")


def bow_thruster():
    return system_block(2_400, 2_400, 2_200, "подруливающее устройство")


def stabilizer():
    return system_block(1_800, 2_800, 1_200, "успокоитель качки")


def battery_rack():
    return system_block(2_600, 1_200, 1_800,
                        "аккумуляторные батареи гибридной установки",
                        SYSTEM_ELECTRIC)


# --- Трапы и лифты ----------------------------------------------------------

def stair_flight(rise=2_700, run=3_600, width=1_200):
    """Лестничный марш с площадкой: ступени задают уклон, а не намекают.

    Марш строится реальными ступенями, потому что уклон — то, что на разрезе
    сразу видно неправильным: наклонная плита читается как пандус.

    Поручень идёт ПО УКЛОНУ на стойках, а не вертикальной плитой вдоль
    марша: плита на виде с уровня глаз читается как глухая стена, и по ней
    не понять ни высоты поручня, ни того, есть ли он вообще. Высота 900 мм
    над проступью — то, что требуется от трапа для пассажиров.
    """
    steps = max(8, int(rise // 180))
    step_rise = rise / steps
    step_run = run / steps
    angle = math.degrees(math.atan2(rise, run))
    parts = []
    for index in range(steps):
        parts.append(_part(step_run + 40, width, step_rise + 30,
                           (index * step_run, 0, index * step_rise),
                           STONE, MAT_STONE, "ступень"))
    parts.append(_part(1_400, width, 120, (run, 0, rise - 120), STONE,
                       MAT_STONE, "площадка трапа"))
    # косоур: ступени опираются на него, а не висят каждая сама по себе
    for side in (0, width - 90):
        parts.append(_part(run, 90, 300, (0, side, 0), METAL, MAT_METAL,
                           "косоур"))
        parts.append(_part(run, 90, 300, (0, side, rise - 400), METAL,
                           MAT_METAL, "косоур"))

    HANDRAIL = 900  # над проступью
    # Поручень идёт ВНУТРИ проступи и снаружи косоура: между ними полоса
    # шириной 10 мм. Стоя на самом косоуре, он давал пересечение на литр,
    # а вынесенный за проступь — висел бы ни на чём.
    for side in (100, width - 160):
        rail = block(math.hypot(run, rise), 60, 60)
        rail = bd.Rot(0, -angle, 0) * rail
        rail = bd.Pos(0, side, HANDRAIL) * rail
        rail.color, rail.cad_material = METAL, dict(MAT_METAL)
        rail.label = "поручень трапа"
        parts.append(rail)
        for index in range(0, steps, 2):
            # стойка встаёт НА проступь, а не в неё, и доходит ровно до
            # поручня, который в этом сечении уже поднялся на полступени
            parts.append(_part(50, 50, HANDRAIL - step_rise / 2 - 30,
                               (index * step_run + step_run / 2, side + 5,
                                (index + 1) * step_rise + 30),
                               METAL, MAT_METAL, "стойка поручня"))
    return parts

def lift_shaft(width=1_800, depth=1_800, height=2_700):
    return [
        _part(width, depth, height, (0, 0, 0), METAL, MAT_METAL,
              "шахта лифта"),
        _part(width - 400, 60, 2_100, (200, -60, 0), DARK, MAT_METAL,
              "двери лифта"),
    ]


def banquette(length=3_200, depth=700):
    """Диван-банкетка вдоль борта: у окон сидят на диване, а не на стуле."""
    return [
        _part(length, depth, 420, (0, 0, 0), TEXTILE, MAT_TEXTILE, "банкетка"),
        _part(length, 180, 600, (0, depth - 180, 420), TEXTILE, MAT_TEXTILE,
              "спинка банкетки"),
    ]


def table_rect(width=1_400, depth=800):
    """Прямоугольный стол к банкетке."""
    return [
        _part(width, depth, 60, (0, 0, 700), WOOD, MAT_WOOD, "стол"),
        _part(160, 160, 700, ((width - 160) / 2, (depth - 160) / 2, 0),
              METAL, MAT_METAL, "опора стола"),
    ]


def pendant_light(diameter=420, drop=150):
    """Подвесной светильник: вертикальная деталь, которой не хватает залу.

    Вынос всего 150 мм, и это не скупость: подволок в свету 2350 мм, а
    светильники висят над проходом. При выносе 650 мм низ плафона
    оказывался на 1.48 м — ниже макушки любого пассажира. Судовой
    светильник в такой высоте потолка и делают полунакладным.
    """
    return [
        _part(60, 60, drop, (diameter / 2 - 30, diameter / 2 - 30,
                             HEIGHT_HINT - drop), METAL, MAT_METAL, "подвес"),
        _part(diameter, diameter, 220, (0, 0, HEIGHT_HINT - drop - 220),
              STONE, MAT_STONE, "плафон"),
    ]


HEIGHT_HINT = 2_350


# --- Фигура человека --------------------------------------------------------

FIGURE = srgb("#4A5560")


def figure(height=1_800, facing=0):
    """Габаритный манекен: рост, плечи, шаг. Стоит НА ОСИ, а не углом к ней.

    Без фигуры в кадре высоту ограждения и ширину прохода оценить нечем: на
    рендере без масштаба полутораметровый парапет и двухметровая стена
    выглядят одинаково. Поэтому рост задаётся явно — 1800 мм расчётного
    мужчины, глаз у него на 1690 мм, с этой же высоты снимаются виды.

    Доли роста антропометрические: ноги до 0.47, плечи на 0.82 — сумма
    даёт ровно заданный рост, а не обрывается ниже.
    """
    legs = height * 0.47
    torso = height * 0.35
    head = height - legs - torso
    shoulder = height * 0.26
    parts = [
        _part(190, 200, legs, (-95, -240, 0), FIGURE, MAT_TEXTILE,
              "фигура: нога"),
        _part(190, 200, legs, (-95, 40, 0), FIGURE, MAT_TEXTILE,
              "фигура: нога"),
        _part(240, shoulder, torso, (-120, -shoulder / 2, legs),
              FIGURE, MAT_TEXTILE, "фигура: корпус"),
        _part(190, 200, head, (-95, -100, legs + torso),
              FIGURE, MAT_TEXTILE, "фигура: голова"),
    ]
    if facing:
        turned = []
        for item in parts:
            moved = bd.Rot(0, 0, facing) * item
            moved.label, moved.color = item.label, item.color
            turned.append(moved)
        return turned
    return parts


EYE_HEIGHT = 1_690  # глаз стоящего человека ростом 1800 мм


def sport_court(width=18_000, depth=9_000):
    """Спортивная площадка: покрытие, разметка, сетка и ограждение по краю.

    Пустая зона на плане — это не «место под спорт», а дыра в компоновке:
    на виде с уровня глаз кормовая треть солнечной палубы читалась голым
    настилом. Площадка задаёт ей габарит и высоту ограждения.
    """
    net_x = width / 2
    parts = [
        _part(width, depth, 20, (0, 0, 0), srgb("#3E6B52"), MAT_TEXTILE,
              "покрытие площадки"),
        _part(width - 800, 80, 25, (400, depth / 2 - 40, 20), srgb("#E8EDEF"),
              MAT_TEXTILE, "разметка"),
    ]
    # боковые линии внутри поля: side + 400 у дальней кромки выносило
    # полосу на 320 мм ЗА площадку, прямо на тиковый настил
    for side in (400, depth - 480):
        parts.append(_part(width - 800, 80, 25, (400, side, 20),
                           srgb("#E8EDEF"), MAT_TEXTILE, "разметка"))
    # сетка: две стойки и полотно между ними
    for side in (0, depth - 100):
        parts.append(_part(100, 100, 1_800, (net_x - 50, side, 20), METAL,
                           MAT_METAL, "стойка сетки"))
    parts.append(_part(60, depth - 200, 800, (net_x - 30, 100, 1_020),
                       srgb("#8A9098", 0.45), MAT_TEXTILE, "сетка"))
    # Ограждение площадки: мяч не должен уходить за борт. Высота 2.0 м, а
    # не привычные 3–4: над солнечной палубой остаётся всего 2.3 м до
    # подмостового габарита 15.5 м, и трёхметровая сетка выводит судно за
    # него — под мостами ЕГС оно тогда просто не пройдёт.
    # Полотно прозрачное: сетка — это сетка, а не глухой щит. Сплошной
    # цвет превращал площадку в закрытый ящик и перекрывал вид вдоль
    # палубы у любого, кто стоит рядом.
    FENCE = 2_000
    MESH = srgb("#6E7A82", 0.30)
    for side in (0, depth - 60):
        parts.append(_part(width, 60, FENCE, (0, side, 20), MESH,
                           MAT_TEXTILE, "сетчатое ограждение"))
    for side in (0, width - 60):
        parts.append(_part(60, depth, FENCE, (side, 0, 20), MESH,
                           MAT_TEXTILE, "сетчатое ограждение"))
    # стойки ограждения: без них прозрачное полотно висит ни на чём
    for x in (0, width / 2 - 40, width - 80):
        for y in (0, depth - 80):
            parts.append(_part(80, 80, FENCE, (x, y, 20), METAL, MAT_METAL,
                               "стойка ограждения"))
    return parts
