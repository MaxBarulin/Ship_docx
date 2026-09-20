# -*- coding: utf-8 -*-
"""Обстановка общественных помещений «Волжского горизонта».

Модуль чистый: ни bpy, ни mathutils, на выходе — список деталей, каждая из
которых либо прямоугольный ящик, либо цилиндр. В сетку их собирает
`scripts/blender_мебель.py`, а раскладку и проверки можно гонять без Blender.

Три правила, из-за нарушения которых развалилась прежняя обстановка:

1. Каждая деталь на чём-то стоит. Ножка доходит до настила, столешница лежит
   на ножках, кресло в зале стоит на ступени помоста, а не на удлинённой
   палке. Подъём рядов даёт помост, и он строится вместе с креслами.
2. Стул повёрнут к столу. Стул создаётся только через `chair(..., facing)`, а
   `facing` задаётся из центра стола, так что отвернуться он не может.
3. Ничто ни с чем не пересекается: расстановка идёт по сетке с проходами, и
   габарит группы проверяется до того, как детали попадут в список.
"""

# --- палитра ---------------------------------------------------------------
W_DARK = "гор_дерево"            # орех: столешницы, стойки, каркасы
W_LIGHT = "гор_дерево_светлое"   # ясень: корпусная мебель
LEATHER = "гор_кожа"
FAB = "гор_текстиль"
FAB_WARM = "гор_текстиль_тёплый"
MET = "гор_металл"
BRASS = "гор_акцент_латунь"
ACC = "гор_акцент"
STONE = "гор_гранит"
GLASS = "гор_стекло_каюты"
SCREEN_M = "гор_экран"
GREEN = "гор_зелень"
FLOWER = "гор_цветы"
CARPET = "гор_ковёр"
CARPET2 = "гор_ковролин"
MIRROR = "гор_зеркало"
ART = "гор_картина"
PORC = "гор_фарфор"
TILE = "гор_плитка"
LINEN = "гор_бельё"
BARK = "гор_кора"

# --- габариты, от которых всё считается ------------------------------------
SEAT_H = 0.45            # высота сиденья
SEAT_W = 0.46            # сторона сиденья
BACK_H = 0.94            # верх спинки
TABLE_H = 0.75           # столешница
BAR_H = 1.10             # барная стойка
STOOL_H = 0.76           # барный табурет
LOW_H = 0.42             # журнальный стол
LEG = 0.045              # сечение ножки
AISLE = 1.40             # магистральный проход
PASS = 0.80              # проход между спинками
WALL = 0.35              # отступ от переборки


def box(name, x0, x1, y0, y1, z0, z1, mat):
    return ("box", name, min(x0, x1), max(x0, x1), min(y0, y1), max(y0, y1),
            min(z0, z1), max(z0, z1), mat)


def cyl(name, cx, cy, r, z0, z1, mat, seg=16):
    return ("cyl", name, cx, cy, r, min(z0, z1), max(z0, z1), mat, seg)


def bounds(p):
    """Габарит детали независимо от её типа."""
    if p[0] == "box":
        return p[2], p[3], p[4], p[5], p[6], p[7]
    cx, cy, r, z0, z1 = p[2], p[3], p[4], p[5], p[6]
    return cx - r, cx + r, cy - r, cy + r, z0, z1


def group_bounds(parts):
    bs = [bounds(p) for p in parts]
    return (min(b[0] for b in bs), max(b[1] for b in bs),
            min(b[2] for b in bs), max(b[3] for b in bs),
            min(b[4] for b in bs), max(b[5] for b in bs))


def shift(parts, dz):
    """Поднять группу на dz: так мебель садится на ступень помоста."""
    out = []
    for p in parts:
        if p[0] == "box":
            out.append(("box", p[1], p[2], p[3], p[4], p[5],
                        p[6] + dz, p[7] + dz, p[8]))
        else:
            out.append(("cyl", p[1], p[2], p[3], p[4],
                        p[5] + dz, p[6] + dz, p[7], p[8]))
    return out


def move(parts, dx=0.0, dy=0.0, dz=0.0):
    """Сдвиг группы: сборщик пробует так обойти шахту или простенок."""
    out = []
    for p in parts:
        if p[0] == "box":
            out.append(("box", p[1], p[2] + dx, p[3] + dx, p[4] + dy,
                        p[5] + dy, p[6] + dz, p[7] + dz, p[8]))
        else:
            out.append(("cyl", p[1], p[2] + dx, p[3] + dy, p[4],
                        p[5] + dz, p[6] + dz, p[7], p[8]))
    return out


def mirror_y(parts, suffix="_зерк"):
    """Отражение группы на другой борт."""
    out = []
    for p in parts:
        if p[0] == "box":
            out.append(("box", p[1] + suffix, p[2], p[3], -p[5], -p[4],
                        p[6], p[7], p[8]))
        else:
            out.append(("cyl", p[1] + suffix, p[2], -p[3], p[4],
                        p[5], p[6], p[7], p[8]))
    return out


# --- посадочные места ------------------------------------------------------
# facing: куда смотрит сидящий. (1,0) — в нос, (-1,0) — в корму,
# (0,1) — на левый борт, (0,-1) — на правый.

def chair(n, x, y, z, facing, seat=FAB, frame=W_DARK, w=SEAT_W):
    """Стул: четыре ножки до настила, сиденье на них, спинка сзади.

    Спинка ставится со стороны, обратной `facing`, поэтому стул физически не
    может оказаться повёрнутым от стола: направление задаёт тот, кто ставит
    стул, из центра стола.
    """
    fx, fy = facing
    h = w / 2
    p = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx = x + sx * (h - LEG / 2 - 0.015)
            ly = y + sy * (h - LEG / 2 - 0.015)
            p.append(box("%s_ножка" % n, lx - LEG / 2, lx + LEG / 2,
                         ly - LEG / 2, ly + LEG / 2, z, z + SEAT_H - 0.05,
                         frame))
    p.append(box("%s_царга" % n, x - h + 0.02, x + h - 0.02,
                 y - h + 0.02, y + h - 0.02,
                 z + SEAT_H - 0.11, z + SEAT_H - 0.05, frame))
    p.append(box("%s_сиденье" % n, x - h, x + h, y - h, y + h,
                 z + SEAT_H - 0.05, z + SEAT_H, seat))
    if fx:
        bx = x - fx * h
        p.append(box("%s_спинка" % n, min(bx, bx + 0.055 * fx),
                     max(bx, bx + 0.055 * fx), y - h, y + h,
                     z + SEAT_H, z + BACK_H, seat))
    else:
        by = y - fy * h
        p.append(box("%s_спинка" % n, x - h, x + h,
                     min(by, by + 0.055 * fy), max(by, by + 0.055 * fy),
                     z + SEAT_H, z + BACK_H, seat))
    return p


def armchair(n, x, y, z, facing, seat=LEATHER, frame=W_DARK, w=0.78, d=0.80):
    """Кресло с подлокотниками: цоколь, подушка, спинка, два подлокотника."""
    fx, fy = facing
    if fx:
        x0, x1 = x - d / 2, x + d / 2
        y0, y1 = y - w / 2, y + w / 2
    else:
        x0, x1 = x - w / 2, x + w / 2
        y0, y1 = y - d / 2, y + d / 2
    p = [box("%s_цоколь" % n, x0 + 0.05, x1 - 0.05, y0 + 0.05, y1 - 0.05,
             z, z + 0.14, frame),
         box("%s_основание" % n, x0 + 0.02, x1 - 0.02, y0 + 0.02, y1 - 0.02,
             z + 0.14, z + 0.36, seat),
         box("%s_подушка" % n, x0 + 0.06, x1 - 0.06, y0 + 0.06, y1 - 0.06,
             z + 0.36, z + SEAT_H, seat)]
    if fx:
        bx = x - fx * d / 2
        p.append(box("%s_спинка" % n, min(bx, bx + fx * 0.14),
                     max(bx, bx + fx * 0.14), y0, y1, z + 0.14, z + 0.88,
                     seat))
        for sy in (-1, 1):
            ay = y + sy * (w / 2 - 0.06)
            p.append(box("%s_подлокотник" % n, x0 + 0.10, x1 - 0.06,
                         ay - 0.06, ay + 0.06, z + SEAT_H, z + 0.63, frame))
    else:
        by = y - fy * d / 2
        p.append(box("%s_спинка" % n, x0, x1, min(by, by + fy * 0.14),
                     max(by, by + fy * 0.14), z + 0.14, z + 0.88, seat))
        for sx in (-1, 1):
            ax = x + sx * (w / 2 - 0.06)
            p.append(box("%s_подлокотник" % n, ax - 0.06, ax + 0.06,
                         y0 + 0.10, y1 - 0.06, z + SEAT_H, z + 0.63, frame))
    return p


def sofa(n, x0, x1, y0, y1, z, facing, seat=FAB_WARM, frame=W_DARK):
    """Диван по габариту: спинка со стороны, обратной `facing`."""
    fx, fy = facing
    p = [box("%s_цоколь" % n, x0 + 0.06, x1 - 0.06, y0 + 0.06, y1 - 0.06,
             z, z + 0.14, frame),
         box("%s_основание" % n, x0 + 0.02, x1 - 0.02, y0 + 0.02, y1 - 0.02,
             z + 0.14, z + 0.36, seat)]
    if fx:
        bx = x0 if fx > 0 else x1
        p.append(box("%s_спинка" % n, bx, bx + fx * 0.16, y0, y1,
                     z + 0.14, z + 0.86, seat))
        s0, s1 = sorted((bx + fx * 0.16, x1 if fx > 0 else x0))
        n_c = max(2, int(round((y1 - y0) / 0.62)))
        for k in range(n_c):
            c0 = y0 + (y1 - y0) * k / n_c + 0.03
            c1 = y0 + (y1 - y0) * (k + 1) / n_c - 0.03
            p.append(box("%s_подушка_%d" % (n, k), s0, s1, c0, c1,
                         z + 0.36, z + SEAT_H, seat))
        for yy, s in ((y0, 1), (y1, -1)):
            p.append(box("%s_подлокотник_%d" % (n, s), s0, s1,
                         min(yy, yy + s * 0.10), max(yy, yy + s * 0.10),
                         z + SEAT_H, z + 0.64, frame))
    else:
        by = y0 if fy > 0 else y1
        p.append(box("%s_спинка" % n, x0, x1, min(by, by + fy * 0.16),
                     max(by, by + fy * 0.16), z + 0.14, z + 0.86, seat))
        s0, s1 = sorted((by + fy * 0.16, y1 if fy > 0 else y0))
        n_c = max(2, int(round((x1 - x0) / 0.62)))
        for k in range(n_c):
            c0 = x0 + (x1 - x0) * k / n_c + 0.03
            c1 = x0 + (x1 - x0) * (k + 1) / n_c - 0.03
            p.append(box("%s_подушка_%d" % (n, k), c0, c1, s0, s1,
                         z + 0.36, z + SEAT_H, seat))
        for xx, s in ((x0, 1), (x1, -1)):
            p.append(box("%s_подлокотник_%d" % (n, s),
                         min(xx, xx + s * 0.10), max(xx, xx + s * 0.10),
                         s0, s1, z + SEAT_H, z + 0.64, frame))
    return p


def stool(n, x, y, z, top=LEATHER, frame=MET, h=STOOL_H, r=0.19):
    """Барный табурет: широкое основание, колонна, подножка, сиденье."""
    return [cyl("%s_основание" % n, x, y, r + 0.05, z, z + 0.04, frame, 20),
            cyl("%s_колонна" % n, x, y, 0.045, z + 0.04, z + h - 0.06,
                frame, 12),
            cyl("%s_подножка" % n, x, y, r - 0.02, z + 0.21, z + 0.25,
                frame, 20),
            cyl("%s_сиденье" % n, x, y, r, z + h - 0.06, z + h, top, 20)]


def bench(n, x0, x1, y0, y1, z, mat=FAB_WARM, frame=W_DARK, h=SEAT_H):
    """Банкетка или пуф без спинки."""
    return [box("%s_цоколь" % n, x0 + 0.06, x1 - 0.06, y0 + 0.06, y1 - 0.06,
                z, z + 0.12, frame),
            box("%s_сиденье" % n, x0, x1, y0, y1, z + 0.12, z + h, mat)]


# --- столы -----------------------------------------------------------------

def table_sq(n, x, y, z, w=0.90, d=None, h=TABLE_H, top=W_DARK, frame=MET):
    """Стол на четырёх ножках: ножки доходят до настила, царга их связывает."""
    d = w if d is None else d
    x0, x1 = x - w / 2, x + w / 2
    y0, y1 = y - d / 2, y + d / 2
    p = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx = x + sx * (w / 2 - 0.09)
            ly = y + sy * (d / 2 - 0.09)
            p.append(box("%s_ножка" % n, lx - 0.03, lx + 0.03,
                         ly - 0.03, ly + 0.03, z, z + h - 0.04, frame))
    p.append(box("%s_царга" % n, x0 + 0.10, x1 - 0.10, y0 + 0.10, y1 - 0.10,
                 z + h - 0.14, z + h - 0.04, frame))
    p.append(box("%s_столешница" % n, x0, x1, y0, y1, z + h - 0.04, z + h,
                 top))
    return p


def table_round(n, x, y, z, r=0.45, h=TABLE_H, top=STONE, frame=MET):
    """Круглый стол: тяжёлое основание, колонна, крестовина под столешницей.

    Раньше столешница 0,92 м лежала на палке 0,11 м и с низкой точки читалась
    как висящая в воздухе — отсюда «летающие столы» на рендерах.
    """
    return [cyl("%s_основание" % n, x, y, max(0.26, r * 0.62), z, z + 0.05,
                frame, 24),
            cyl("%s_юбка" % n, x, y, max(0.20, r * 0.46), z + 0.05, z + 0.09,
                frame, 24),
            cyl("%s_колонна" % n, x, y, 0.06, z + 0.09, z + h - 0.09,
                frame, 12),
            cyl("%s_крестовина" % n, x, y, max(0.18, r * 0.42),
                z + h - 0.09, z + h - 0.04, frame, 16),
            cyl("%s_столешница" % n, x, y, r, z + h - 0.04, z + h, top, 32)]


def low_table(n, x, y, z, w=1.10, d=0.62, h=LOW_H, top=W_DARK, frame=BRASS):
    """Журнальный стол: рама по периметру и четыре ножки, а не парящая доска."""
    x0, x1 = x - w / 2, x + w / 2
    y0, y1 = y - d / 2, y + d / 2
    p = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            lx = x + sx * (w / 2 - 0.07)
            ly = y + sy * (d / 2 - 0.07)
            p.append(box("%s_ножка" % n, lx - 0.025, lx + 0.025,
                         ly - 0.025, ly + 0.025, z, z + h - 0.05, frame))
    p.append(box("%s_рама_п" % n, x0 + 0.05, x1 - 0.05, y0 + 0.05,
                 y0 + 0.09, z + h - 0.13, z + h - 0.05, frame))
    p.append(box("%s_рама_л" % n, x0 + 0.05, x1 - 0.05, y1 - 0.09,
                 y1 - 0.05, z + h - 0.13, z + h - 0.05, frame))
    p.append(box("%s_полка" % n, x0 + 0.08, x1 - 0.08, y0 + 0.08, y1 - 0.08,
                 z + 0.16, z + 0.19, W_LIGHT))
    p.append(box("%s_столешница" % n, x0, x1, y0, y1, z + h - 0.05, z + h,
                 top))
    return p


# --- корпусная мебель и оборудование ---------------------------------------

def counter(n, x0, x1, y0, y1, z, h=BAR_H, top=STONE, body=W_DARK, toe=0.06):
    """Стойка: корпус с подрезкой под ногу и каменная столешница."""
    return [box("%s_цоколь" % n, x0 + 0.10, x1 - 0.10, y0 + 0.10, y1 - 0.10,
                z, z + 0.12, MET),
            box("%s_корпус" % n, x0 + toe, x1 - toe, y0 + toe, y1 - toe,
                z + 0.12, z + h - 0.04, body),
            box("%s_столешница" % n, x0, x1, y0, y1, z + h - 0.04, z + h,
                top)]


def cabinet(n, x0, x1, y0, y1, z, h=0.90, top=W_LIGHT, body=W_LIGHT):
    return [box("%s_цоколь" % n, x0 + 0.05, x1 - 0.05, y0 + 0.05, y1 - 0.05,
                z, z + 0.10, MET),
            box("%s_корпус" % n, x0, x1, y0, y1, z + 0.10, z + h - 0.03,
                body),
            box("%s_крышка" % n, x0 - 0.01, x1 + 0.01, y0 - 0.01, y1 + 0.01,
                z + h - 0.03, z + h, top)]


def shelf(n, x0, x1, y0, y1, z, h=2.00, shelves=5, body=W_LIGHT, fill=True):
    """Стеллаж у переборки: боковины до настила, полки между ними."""
    p = [box("%s_бок_0" % n, x0, x0 + 0.04, y0, y1, z, z + h, body),
         box("%s_бок_1" % n, x1 - 0.04, x1, y0, y1, z, z + h, body),
         box("%s_задняя" % n, x0, x1, y0, y0 + 0.02, z, z + h, body)]
    for k in range(shelves + 1):
        zz = z + 0.12 + (h - 0.16) * k / shelves
        p.append(box("%s_полка_%d" % (n, k), x0 + 0.04, x1 - 0.04,
                     y0 + 0.02, y1, zz, zz + 0.03, body))
    if fill:
        for k in range(shelves):
            zz = z + 0.12 + (h - 0.16) * k / shelves
            p.append(box("%s_книги_%d" % (n, k), x0 + 0.08, x1 - 0.08,
                         y0 + 0.05, y0 + 0.24, zz + 0.03, zz + 0.26,
                         ACC if k % 2 else W_DARK))
    return p


def planter(n, x, y, z, r=0.34, h=0.55, pot=STONE):
    """Кадка с деревом: ствол стоит в кадке, крона на стволе."""
    return [cyl("%s_кадка" % n, x, y, r, z, z + h, pot, 20),
            cyl("%s_грунт" % n, x, y, r - 0.04, z + h - 0.03, z + h, BARK,
                20),
            cyl("%s_ствол" % n, x, y, 0.045, z + h - 0.03, z + h + 0.62,
                BARK, 10),
            cyl("%s_крона" % n, x, y, 0.42, z + h + 0.52, z + h + 1.28,
                GREEN, 16)]


def vase(n, x, y, z, r=0.10, h=0.26):
    return [cyl("%s_ваза" % n, x, y, r, z, z + h, PORC, 14),
            cyl("%s_букет" % n, x, y, r + 0.10, z + h - 0.02, z + h + 0.26,
                FLOWER, 12)]


def rug(n, x0, x1, y0, y1, z, mat=CARPET):
    return [box(n, x0, x1, y0, y1, z, z + 0.012, mat)]


def wall_panel(n, y0, y1, x, z, h0, h1, mat, t=0.03, side=1):
    """Панель на продольной переборке: борт на y=const, толщина внутрь."""
    return [box(n, y0, y1, min(x, x + t * side), max(x, x + t * side),
                z + h0, z + h1, mat)]


def side_panel(n, x0, x1, y, z, h0, h1, mat, t=0.03, side=1):
    """Панель на бортовой переборке: y=const, длина по x."""
    return [box(n, x0, x1, min(y, y + t * side), max(y, y + t * side),
                z + h0, z + h1, mat)]


def screen(n, x0, x1, y, z, h0=1.00, h1=2.30, t=0.07, side=1):
    """Экран на бортовой переборке."""
    y1 = y + t * side
    return [box("%s_рама" % n, x0, x1, min(y, y1), max(y, y1),
                z + h0 - 0.05, z + h1 + 0.05, MET),
            box("%s_экран" % n, x0 + 0.05, x1 - 0.05,
                min(y1, y1 + 0.01 * side), max(y1, y1 + 0.01 * side),
                z + h0, z + h1, SCREEN_M)]


def tier(n, x0, x1, y0, y1, z, h, mat=CARPET2):
    """Ступень помоста: сплошной блок от настила до своей отметки."""
    return [box("%s_ступень" % n, x0, x1, y0, y1, z, z + h, mat),
            box("%s_кромка" % n, x1 - 0.04, x1, y0, y1, z, z + h, BRASS)]


def lamp(n, x, y, z, h=1.55):
    """Торшер: основание на настиле, стойка, абажур."""
    return [cyl("%s_основание" % n, x, y, 0.16, z, z + 0.04, BRASS, 16),
            cyl("%s_стойка" % n, x, y, 0.022, z + 0.04, z + h - 0.20,
                BRASS, 10),
            cyl("%s_абажур" % n, x, y, 0.19, z + h - 0.20, z + h, LINEN, 16)]


# --- расстановка -----------------------------------------------------------

def table_set(n, x, y, z, seats=4, w=0.90, round_top=False, reach=None,
              top=W_DARK, seat=FAB, along="y", frame=W_DARK):
    """Стол со стульями: каждый стул повёрнут к центру стола.

    `along` задаёт, вдоль какой оси сажают пары при `seats == 2`.
    Возвращает (детали, габарит группы) — габарит нужен расстановке, чтобы
    проверить, влезает ли группа в отведённое место.
    """
    if reach is None:
        reach = w / 2 + 0.29
    p = (table_round(n, x, y, z, r=w / 2, top=top) if round_top
         else table_sq(n, x, y, z, w=w, top=top))
    if seats == 2:
        dirs = [(1, 0), (-1, 0)] if along == "x" else [(0, 1), (0, -1)]
    elif seats == 3:
        dirs = [(1, 0), (-1, 0), (0, 1)]
    elif seats >= 4:
        dirs = [(1, 0), (-1, 0), (0, 1), (0, -1)]
    else:
        dirs = [(0, 1)]
    for k, d in enumerate(dirs[:seats]):
        p += chair("%s_стул_%d" % (n, k), x - d[0] * reach, y - d[1] * reach,
                   z, d, seat=seat, frame=frame)
    return p, group_bounds(p)


def rows(x0, x1, step, margin=0.0):
    """Отметки рядов по длине помещения, выровненные по центру."""
    a, b = x0 + margin, x1 - margin
    n = int((b - a) // step)
    if n < 1:
        return []
    start = a + ((b - a) - n * step) / 2 + step / 2
    return [start + k * step for k in range(n)]


def fits(hw, x0, x1, y0, y1, margin=WALL):
    """Габарит целиком внутри помещения на всех своих шпациях."""
    n = max(2, int((x1 - x0) / 0.5) + 1)
    for k in range(n):
        x = x0 + (x1 - x0) * k / (n - 1)
        w = hw(x) - margin
        if max(abs(y0), abs(y1)) > w:
            return False
    return True
