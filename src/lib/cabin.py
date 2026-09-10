"""Оболочка каюты и планировки четырёх категорий.

Оболочка одна на все категории и строится по модульной сетке из lib.ship:
меняется только число модулей вдоль борта. Планировка — это расстановка
элементов из lib.furniture внутри этой оболочки.

Начало координат — левый угол каюты у борта, на уровне чистого пола.
Ось X идёт вдоль борта, ось Y от борта вглубь к коридору, ось Z вверх.
"""

from cadgen import build123d as bd

from . import furniture as fu
from . import palette as p
from . import ship


def place(shape, x=0.0, y=0.0, z=0.0, turn=0):
    """Поставить элемент углом в (x, y), развернув его на turn градусов.

    Поворот вокруг Z уводит угол элемента из начала координат, поэтому
    компенсируем сдвигом — вызывающий думает про угол, а не про матрицы.
    """
    box = shape.bounding_box()
    w, d = box.size.X, box.size.Y
    turn %= 360
    shift = {0: (0, 0), 90: (d, 0), 180: (w, d), 270: (0, w)}[turn]
    moved = bd.Pos(x + shift[0], y + shift[1], z) * bd.Rot(0, 0, turn) * shape
    moved.label = shape.label
    return moved


def shell(category, wall=None, floor=None, window=None, door_x=None,
          balcony_depth=0):
    """Пол, подволок, переборки, окно и дверь для каюты заданной категории.

    window — (отступ от левого угла, ширина, низ, верх) в мм; None ставит
    типовое окно по центру борта. Проёмы вырезаются, стёкла вставляются.
    """
    wall = wall or p.WALL_LIGHT
    floor = floor or p.FLOOR_CARPET
    w = ship.clear_width(category)
    d = ship.clear_depth()
    h = ship.CEILING_HEIGHT
    t = ship.BULKHEAD

    if window is None:
        win_w = min(w - 700, 2400)
        window = ((w - win_w) / 2, win_w, 750, 1950)
    win_x, win_w, win_lo, win_hi = window

    door_w, door_h = 800, 2000
    if door_x is None:
        door_x = w - door_w - 250

    deck = fu._part(w, d, 25, (0, 0, -25), floor, p.MAT_CARPET, "палубный настил")
    ceiling = fu._part(w, d, 25, (0, 0, h), p.CEILING, p.MAT_PAINT, "подволок")

    side = fu.block(w, t, h) - fu.block(win_w, t, win_hi - win_lo).moved(
        bd.Location((win_x, 0, win_lo)))
    side = p.finish(bd.Pos(0, -t, 0) * side, wall, p.MAT_PAINT, "борт")
    glazing = fu._part(win_w, 16, win_hi - win_lo, (win_x, -t / 2 - 8, win_lo),
                       p.GLASS, p.MAT_GLASS, "остекление")

    inner = fu.block(w, t, h) - fu.block(door_w, t, door_h).moved(
        bd.Location((door_x, 0, 0)))
    inner = p.finish(bd.Pos(0, d, 0) * inner, wall, p.MAT_PAINT, "переборка коридора")
    leaf = fu._part(door_w - 20, 40, door_h - 20, (door_x + 10, d + 5, 0),
                    p.WOOD_LIGHT, p.MAT_WOOD, "дверь")

    ends = [
        fu._part(t, d, h, (-t, 0, 0), wall, p.MAT_PAINT, "переборка"),
        fu._part(t, d, h, (w, 0, 0), wall, p.MAT_PAINT, "переборка"),
    ]

    parts = [deck, ceiling, side, glazing, inner, leaf, *ends]

    if balcony_depth:
        slab = fu._part(w, balcony_depth, 30, (0, -t - balcony_depth, -30),
                        p.FLOOR_WOOD, p.MAT_WOOD, "палуба балкона")
        rail_glass = fu._part(w, 18, 1000, (0, -t - balcony_depth, 0),
                              p.GLASS, p.MAT_GLASS, "ограждение")
        rail_top = fu._part(w, 60, 60, (0, -t - balcony_depth - 20, 1000),
                            p.METAL, p.MAT_METAL, "поручень")
        parts += [slab, rail_glass, rail_top]

    return parts


# --- Планировки ------------------------------------------------------------

def layout_econom():
    """Эконом, 2 модуля. Две койки в два яруса, санблок у входа, стол у окна.

    Каюта минимальной площади, поэтому койка ставится поперёк под окном —
    иначе не остаётся прохода к санблоку.
    """
    w, d = ship.clear_width("econom"), ship.clear_depth()
    items = shell("econom", door_x=1650)
    items += [
        place(fu.bunk(900, 2000), (w - 2000) / 2, 60, turn=90),
        place(fu.bath_pod(1500, 1700, door_side="right"), 0, d - 1700),
        place(fu.desk(1000, 450), w - 1000, 1150),
        place(fu.chair(), w - 900, 1030, turn=180),
        place(fu.wardrobe(700, 550), w - 700, d - 1700),
        place(fu.luggage_rack(700, 500), w - 700, d - 1700, z=2060),
        place(fu.ceiling_light(), w / 2, d / 2, z=ship.CEILING_HEIGHT),
    ]
    return items


def layout_standard():
    """Стандарт, 3 модуля. Две раздельные койки, стол у окна, шкаф-купе.

    Койки стоят головой к борту, между ними тумба. Санблок в углу у входа,
    его переборка работает как основание под телевизор.
    """
    w, d = ship.clear_width("standard"), ship.clear_depth()
    items = shell("standard", door_x=1200)
    items += [
        place(fu.berth(900, 2000, p.TEXTILE_TEAL), 100, 200),
        place(fu.berth(900, 2000, p.TEXTILE_TEAL), 1400, 200),
        place(fu.nightstand(380, 400, 560), 1010, 200),
        place(fu.bath_pod(1500, 1700, door_side="left"), w - 1500, d - 1700),
        place(fu.wardrobe(800, 600), 200, d - 650, turn=180),
        place(fu.desk(1100, 480), w - 480, 300, turn=90),
        place(fu.chair(), w - 1050, 800),
        place(fu.tv_panel(900, 520), w - 1500, 400, z=900, turn=270),
        place(fu.luggage_rack(800, 500), 200, d - 1250, z=2060),
        place(fu.ceiling_light(), w / 2, d / 2, z=ship.CEILING_HEIGHT),
    ]
    return items


def layout_business():
    """Бизнес, 4 модуля. Двуспальная кровать, зона отдыха у окна, большой санблок.

    Кровать стоит изголовьем к борту и смотрит на переборку коридора, где
    висит телевизор. Диван и столик занимают освободившуюся часть окна.
    """
    w, d = ship.clear_width("business"), ship.clear_depth()
    items = shell("business", wall=p.WALL_WARM, floor=p.FLOOR_CARPET_RICH,
                  door_x=2300)
    items += [
        place(fu.double_bed(1600, 2000, p.TEXTILE_TEAL, p.WOOD_DARK), 400, 100),
        place(fu.nightstand(400, 400, 520), 0, 200),
        place(fu.nightstand(400, 400, 520), 2000, 200),
        place(fu.bath_pod(1800, 1900, door_side="left"), w - 1800, d - 1900),
        place(fu.sofa(1700, 780, p.TEXTILE_SAND), 2900, 150),
        place(fu.coffee_table(700, 480), 3400, 980),
        place(fu.wardrobe(1000, 620, 2100, p.WOOD_DARK), 60, d - 670, turn=180),
        place(fu.tv_panel(1100, 620), 1300, d - 45, z=850),
        place(fu.ceiling_light(), 1300, d / 2, z=ship.CEILING_HEIGHT),
        place(fu.ceiling_light(), w - 1100, d / 2, z=ship.CEILING_HEIGHT),
    ]
    return items


def layout_lux():
    """Люкс, 6 модулей. Спальня и гостиная в одном объёме, выход на балкон.

    Балкон занимает променад, который остался от поперечной схемы палубы —
    поэтому он есть только у люкса и только по этой причине.
    """
    w, d = ship.clear_width("lux"), ship.clear_depth()
    items = shell("lux", wall=p.WALL_WARM, floor=p.FLOOR_WOOD,
                  window=(200, w - 400, 300, 2150), door_x=5100,
                  balcony_depth=int(ship.promenade_width()))
    items += [
        # спальная зона
        place(fu.double_bed(1800, 2050, p.TEXTILE_WINE, p.WOOD_DARK), 450, 200),
        place(fu.nightstand(450, 420, 540), 0, 280),
        place(fu.nightstand(450, 420, 540), 2250, 280),
        place(fu.wardrobe(1200, 650, 2150, p.WOOD_DARK), 60, d - 700, turn=180),
        place(fu.bath_pod(2000, 2100, door_side="left"), 2900, d - 2100),
        # гостиная зона
        place(fu.sofa(1900, 820, p.TEXTILE_SAND), 5200, 200),
        place(fu.armchair(760, 760, p.TEXTILE_SAND), 5300, 1900, turn=180),
        place(fu.coffee_table(900, 560), 5600, 1200),
        place(fu.tv_panel(1300, 730), 6200, d - 45, z=800),
        place(fu.desk(1000, 460), w - 460, 1500, turn=90),
        place(fu.chair(), 6700, 1800),
        place(fu.ceiling_light(), 1400, d / 2, z=ship.CEILING_HEIGHT),
        place(fu.ceiling_light(), w / 2, d / 2, z=ship.CEILING_HEIGHT),
        place(fu.ceiling_light(), w - 1300, d / 2, z=ship.CEILING_HEIGHT),
        # мебель балкона
        place(fu.armchair(700, 700, p.TEXTILE_SAND), 700, -1900),
        place(fu.armchair(700, 700, p.TEXTILE_SAND), 1700, -1900),
        place(fu.coffee_table(600, 600, 400), 1500, -1100),
    ]
    return items


LAYOUTS = {
    "econom": layout_econom,
    "standard": layout_standard,
    "business": layout_business,
    "lux": layout_lux,
}


def build(category):
    """Собрать каюту категории в сборку с подписанными частями."""
    return bd.Compound(children=LAYOUTS[category](), label=f"каюта {category}")
