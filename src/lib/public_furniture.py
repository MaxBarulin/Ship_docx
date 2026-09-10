"""Мебель и оборудование общественных зон.

Средняя детализация: узнаваемый силуэт и правильный габарит, без обивки и
фурнитуры. На разрезе и на виде сверху важно, что зона занята мебелью
такого-то шага и на столько-то мест — по этому считается вместимость зала,
а не то, как выглядит спинка стула.

Каждый элемент строится от левого ближнего нижнего угла, как и судовая
мебель в lib.furniture, поэтому ставится одним Pos(x, y, z).
"""

from cadgen import build123d as bd
from cadgen import srgb

from .furniture import _part

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
    offsets = [(-560, diameter / 2 - 220), (diameter + 100, diameter / 2 - 220),
               (diameter / 2 - 220, -560), (diameter / 2 - 220, diameter + 100)]
    for index in range(min(seats, 4)):
        dx, dy = offsets[index]
        parts.append(_part(440, 440, 460, (dx, dy, 0), TEXTILE, MAT_TEXTILE,
                           "кресло"))
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


def pool(width=9_000, depth=4_600, rim=1_300):
    """Бассейн: приподнятая чаша, вода, обходной борт.

    Чаша стоит НА палубе, а не утоплена в неё: на судне бассейн верхней
    палубы приподнят, потому что под ним каюты, а не грунт.
    """
    return [
        _part(width, depth, 200, (0, 0, 0), STONE, MAT_STONE, "борт бассейна"),
        _part(width - 700, depth - 700, rim, (350, 350, 200), STONE,
              MAT_STONE, "чаша бассейна"),
        _part(width - 900, depth - 900, rim - 250, (450, 450, 300), WATER,
              MAT_WATER, "вода"),
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
    """
    steps = max(8, int(rise // 180))
    step_rise = rise / steps
    step_run = run / steps
    parts = []
    for index in range(steps):
        parts.append(_part(step_run + 40, width, step_rise + 30,
                           (index * step_run, 0, index * step_rise),
                           STONE, MAT_STONE, "ступень"))
    parts.append(_part(1_400, width, 120, (run, 0, rise - 120), STONE,
                       MAT_STONE, "площадка трапа"))
    for side in (0, width - 60):
        parts.append(_part(run, 60, 1_000, (0, side, rise * 0.45),
                           METAL, MAT_METAL, "поручень трапа"))
    return parts


def lift_shaft(width=1_800, depth=1_800, height=2_700):
    return [
        _part(width, depth, height, (0, 0, 0), METAL, MAT_METAL,
              "шахта лифта"),
        _part(width - 400, 60, 2_100, (200, -60, 0), DARK, MAT_METAL,
              "двери лифта"),
    ]
