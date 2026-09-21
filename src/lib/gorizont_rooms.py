# -*- coding: utf-8 -*-
"""Раскладка обстановки по общественным помещениям.

Каждая функция получает габарит помещения по длине, отметку настила и
функцию `hw(x)` — полуширину помещения в этой шпации (её считает
`scripts/blender_мебель.py` лучами по переборкам, поэтому раскладка не знает
и не должна знать, чем именно ограничено помещение).

Возвращается список групп: (имя, детали, обязательная). Необязательную
группу сборщик снимает, если она во что-то упирается; обязательная ставится
всегда и при конфликте попадает в отчёт.
"""

from . import gorizont_furniture as F

G = F  # короткое имя для палитры


def _band(hw, x, aisle, margin=F.WALL):
    """Полоса от прохода в диаметрали до борта на шпации x."""
    return aisle / 2.0, hw(x) - margin


def _groups(name, items):
    return [(name, p, opt) for p, opt in items]


# --- ресторан --------------------------------------------------------------

def restaurant(x0, x1, z, hw, n="рест"):
    """Главный ресторан: столы на четыре и на два, проход в диаметрали.

    Столы ставятся парами по бортам, стулья — по четырём сторонам стола и
    всегда лицом к нему. Крайний ряд у остекления — столы на двоих, чтобы
    между спинкой и бортовой переборкой оставался проход 0,80 м.
    """
    out = []
    aisle = 1.70
    step = 2.40
    out.append(("%s_ковёр" % n, F.rug("%s_ковёр" % n, x0 + 0.6, x1 - 0.6,
                                      -aisle / 2, aisle / 2, z,
                                      F.CARPET2), False))
    k = 0
    for x in F.rows(x0 + 2.2, x1 - 1.2, step):
        y0, y1 = _band(hw, x, aisle, margin=0.85)
        if y1 - y0 < 1.0:
            continue
        # сколько столов встаёт в полосу шириной y1-y0 с шагом 2.30
        n_t = int((y1 - y0 + 0.4) // 2.40)
        for s in (-1, 1):
            for j in range(max(1, n_t)):
                cy = y0 + 1.12 + j * 2.40
                if cy + 0.95 > y1:
                    cy = y1 - 0.95
                if cy - 0.95 < y0:
                    continue
                seats = 4 if y1 - y0 > 2.2 or j else 2
                p, b = F.table_set("%s_стол_%d" % (n, k), x, s * cy, z,
                                   seats=seats, w=0.90,
                                   round_top=(k % 3 == 0),
                                   top=F.STONE if k % 3 == 0 else F.W_DARK,
                                   seat=F.LEATHER if k % 3 == 0 else F.FAB,
                                   frame=F.MET)
                out.append(("%s_стол_%d" % (n, k), p, True))
                k += 1
    # раздаточная стойка и винный шкаф у кормовой переборки
    out.append(("%s_буфет" % n,
                F.counter("%s_буфет" % n, x0 + 0.35, x0 + 0.95, -2.2, 2.2,
                          z, h=1.05), False))
    for s in (-1, 1):
        out.append(("%s_витрина_%d" % (n, s),
                    F.cabinet("%s_витрина_%d" % (n, s), x1 - 0.70, x1 - 0.12,
                              s * 0.6, s * 2.9, z, h=1.85, top=F.STONE,
                              body=F.W_DARK), False))
        out.append(("%s_кадка_%d" % (n, s),
                    F.planter("%s_кадка_%d" % (n, s), x0 + 1.55,
                              s * (hw(x0 + 1.55) - 0.75), z), False))
    return out


# --- театр-лаунж -----------------------------------------------------------

def theatre(x0, x1, z, hw, n="театр", tiers=2, rise=0.12, depth=2.00,
            pitch=1.00):
    """Театр-лаунж: сцена в носу, плоский партер, ступени помоста в корме.

    Подъём рядов даёт помост, а не удлинённые ножки кресел: раньше кресла
    стояли на палках над пустым полом, и в кадре ряды «взлетали».

    Ряды привязаны к ступеням: на ступень глубиной 1,90 м садятся ровно два
    ряда с шагом 0,95 м, и ни одно кресло не встаёт на стык двух отметок.
    """
    out = []
    stage_x = x1 - 3.10
    t0 = x0 + 0.25
    flat_x = t0 + tiers * depth
    # помост: ступени растут к корме, кромка смотрит в нос
    levels = []           # (x_ряда, отметка над настилом)
    for t in range(tiers):
        a = t0 + t * depth
        h = rise * (tiers - t)
        wy = min(hw(a + 0.1), hw(a + depth - 0.1)) - 0.60
        if wy < 1.0:
            continue
        out.append(("%s_помост_%d" % (n, t),
                    F.tier("%s_помост_%d" % (n, t), a, a + depth, -wy, wy,
                           z, h), True))
        for k in range(int(depth / pitch)):
            levels.append((a + pitch / 2 + k * pitch, h))
    # марши между ступенями в диаметрали
    for t in range(tiers - 1):
        a = t0 + (t + 1) * depth
        h = rise * (tiers - t - 1)
        out.append(("%s_марш_%d" % (n, t),
                    [F.box("%s_марш_%d" % (n, t), a - 0.28, a, -0.68, 0.68,
                           z, z + h, F.CARPET2)], False))
    for x in F.rows(flat_x, stage_x - 1.2, pitch):
        levels.append((x, 0.0))
    out.append(("%s_ковёр" % n,
                F.rug("%s_ковёр" % n, x0 + 0.2, stage_x - 0.2,
                      -(hw((x0 + stage_x) / 2) - 0.55),
                      hw((x0 + stage_x) / 2) - 0.55, z, F.CARPET), False))
    k = 0
    for x, h in levels:
        y0, y1 = 0.70, hw(x) - 0.85
        if y1 - y0 < 0.6:
            continue
        n_s = int((y1 - y0) // 0.56)
        for s in (-1, 1):
            for j in range(n_s):
                cy = s * (y0 + 0.28 + j * 0.56)
                out.append(("%s_кресло_%d" % (n, k),
                            F.chair("%s_кресло_%d" % (n, k), x, cy, z + h,
                                    (1, 0), seat=F.FAB_WARM,
                                    frame=F.MET), True))
                k += 1
    # сцена, портал и экран у носовой переборки
    wy = min(hw(stage_x), hw(x1 - 0.2)) - 0.70
    out.append(("%s_сцена" % n,
                [F.box("%s_сцена_настил" % n, stage_x, x1 - 0.10, -wy, wy,
                       z, z + 0.25, F.W_DARK),
                 F.box("%s_сцена_кромка" % n, stage_x - 0.05, stage_x,
                       -wy, wy, z, z + 0.25, F.BRASS)], True))
    out.append(("%s_экран" % n,
                [F.box("%s_экран_рама" % n, x1 - 0.34, x1 - 0.28,
                       -wy + 0.35, wy - 0.35, z + 0.60, z + 2.05, F.MET),
                 F.box("%s_экран" % n, x1 - 0.36, x1 - 0.34,
                       -wy + 0.40, wy - 0.40, z + 0.65, z + 2.00,
                       F.SCREEN_M)], True))
    for s in (-1, 1):
        out.append(("%s_портал_%d" % (n, s),
                    [F.box("%s_портал_%d" % (n, s), x1 - 0.42, x1 - 0.26,
                           s * (wy - 0.32), s * wy, z, z + 2.00,
                           F.FAB_WARM)], False))
        out.append(("%s_колонка_%d" % (n, s),
                    [F.box("%s_колонка_%d" % (n, s), stage_x + 0.20,
                           stage_x + 0.50, s * (wy - 0.55), s * (wy - 0.25),
                           z + 0.25, z + 1.95, F.MET)], False))
    return out


# --- бистро ----------------------------------------------------------------

def bistro(x0, x1, z, hw, n="бистро"):
    """Бистро: стойка выдачи, столики на двоих, высокие места у остекления."""
    # линия выдачи идёт вдоль правого борта, а не поперёк у входа: поперёк
    # она перегораживала вход в зал и первый же кадр упирался в её торец
    wy = hw(x0 + 3.0) - 0.40
    out = [("%s_стойка" % n,
            F.counter("%s_стойка" % n, x0 + 0.70, x0 + 4.60,
                      wy - 0.72, wy, z, h=1.05), True),
           ("%s_витрина" % n,
            F.cabinet("%s_витрина" % n, x0 + 0.70, x0 + 4.60,
                      wy - 1.34, wy - 0.78, z, h=1.25, top=F.STONE,
                      body=F.W_LIGHT), False),
           ("%s_полка" % n,
            F.shelf("%s_полка" % n, x0 + 0.90, x0 + 4.40, wy, wy + 0.32, z,
                    h=1.95, shelves=4, body=F.W_LIGHT, fill=True), False)]
    k = 0
    for x in F.rows(x0 + 2.4, x1 - 0.9, 1.90):
        y0, y1 = _band(hw, x, 1.60, margin=0.75)
        if y1 - y0 < 0.9:
            continue
        n_t = max(1, int((y1 - y0 + 0.3) // 1.60))
        for s in (-1, 1):
            for j in range(n_t):
                cy = min(y0 + 0.80 + j * 1.60, y1 - 0.80)
                p, _ = F.table_set("%s_стол_%d" % (n, k), x, s * cy, z,
                                   seats=2, w=0.72, round_top=True,
                                   top=F.STONE, seat=F.LEATHER, along="x")
                out.append(("%s_стол_%d" % (n, k), p, True))
                k += 1
    # высокая стойка у носовой переборки с табуретами
    out.append(("%s_бар" % n,
                F.counter("%s_бар" % n, x1 - 0.85, x1 - 0.20, -2.1, 2.1, z,
                          h=F.BAR_H), False))
    for j in range(6):
        y = -1.75 + j * 0.70
        out.append(("%s_табурет_%d" % (n, j),
                    F.stool("%s_табурет_%d" % (n, j), x1 - 1.35, y, z),
                    False))
    return out


# --- лобби-атриум ----------------------------------------------------------

def lobby(x0, x1, z, hw, n="лобби"):
    """Лобби: ресепшен, зоны отдыха, бутик и зелень вдоль прохода."""
    out = [("%s_ресепшен" % n,
            F.counter("%s_ресепшен" % n, x0 + 0.60, x0 + 1.45, -2.6, 0.4, z,
                      h=1.12, top=F.STONE, body=F.W_DARK), True),
           ("%s_ресепшен_тумба" % n,
            F.cabinet("%s_ресепшен_тумба" % n, x0 + 1.55, x0 + 2.15,
                      -2.5, 0.3, z, h=0.80), False),
           ("%s_панно" % n,
            [F.box("%s_панно" % n, x0 + 0.01, x0 + 0.07, -2.6, 0.4,
                   z + 1.10, z + 2.05, F.ART)], False)]
    k = 0
    for x in F.rows(x0 + 3.2, x1 - 2.6, 3.95):
        wy = hw(x) - 0.70
        if wy < 2.2:
            continue
        for s in (-1, 1):
            cy = s * (wy - 1.05)
            out.append(("%s_ковёр_%d" % (n, k),
                        F.rug("%s_ковёр_%d" % (n, k), x - 1.55, x + 1.55,
                              cy - 1.05, cy + 1.05, z), False))
            out.append(("%s_диван_%d" % (n, k),
                        F.sofa("%s_диван_%d" % (n, k), x - 1.10, x + 1.10,
                               cy + s * 0.55, cy + s * 1.00, z, (0, -s)),
                        True))
            out.append(("%s_стол_%d" % (n, k),
                        F.low_table("%s_стол_%d" % (n, k), x, cy, z,
                                    w=1.10, d=0.62, top=F.STONE), True))
            for j, sx in enumerate((-1, 1)):
                out.append(("%s_кресло_%d_%d" % (n, k, j),
                            F.armchair("%s_кресло_%d_%d" % (n, k, j),
                                       x + sx * 1.05, cy - s * 0.52, z,
                                       (-sx, 0)), True))
            out.append(("%s_торшер_%d" % (n, k),
                        F.lamp("%s_торшер_%d" % (n, k), x - 1.35,
                               cy + s * 0.95, z), False))
            k += 1
    for j, x in enumerate(F.rows(x0 + 2.6, x1 - 1.5, 3.40)):
        out.append(("%s_кадка_%d" % (n, j),
                    F.planter("%s_кадка_%d" % (n, j), x, 0.0, z, r=0.40,
                              h=0.60), False))
    # бутик у носовой переборки
    out.append(("%s_бутик_стойка" % n,
                F.counter("%s_бутик_стойка" % n, x1 - 1.60, x1 - 0.95,
                          1.2, 3.4, z, h=1.00), False))
    for s in (-1, 1):
        out.append(("%s_бутик_стеллаж_%d" % (n, s),
                    F.shelf("%s_бутик_стеллаж_%d" % (n, s), x1 - 0.65,
                            x1 - 0.15, s * 1.0, s * 3.4, z, h=1.90,
                            shelves=4, body=F.W_LIGHT), False))
    return out


# --- носовой панорамный салон ---------------------------------------------

def bow_salon(x0, x1, z, hw, n="нос"):
    """Носовой салон: кресла лицом к остеклению, между ними низкие столы.

    Столы делаются на раме с ножками: прежние столешницы висели над настилом
    без единой опоры и читались как летающие доски.
    """
    out = []
    k = 0
    for x in F.rows(x0 + 0.8, x1 - 1.0, 1.55):
        wy = hw(x) - 0.60
        if wy < 1.1:
            continue
        for s in (-1, 1):
            cy = s * (wy - 0.45)
            out.append(("%s_кресло_%d" % (n, k),
                        F.armchair("%s_кресло_%d" % (n, k), x, cy, z,
                                   (0, s), seat=F.LEATHER, w=0.72, d=0.74),
                        True))
            k += 1
    # низкие столы между парами кресел, по одному через ряд
    for j, x in enumerate(F.rows(x0 + 1.6, x1 - 1.8, 3.10)):
        wy = hw(x) - 0.60
        for s in (-1, 1):
            cy = s * (wy - 0.45)
            out.append(("%s_стол_%d_%d" % (n, j, s),
                        F.low_table("%s_стол_%d_%d" % (n, j, s), x, cy, z,
                                    w=0.52, d=0.52, h=0.52, top=F.STONE),
                        True))
    # центральная группа: два кресла спинами к проходу и столик
    mid = (x0 + x1) / 2
    if hw(mid) > 2.6:
        out.append(("%s_центр_стол" % n,
                    F.low_table("%s_центр_стол" % n, mid, 0.0, z, w=0.90,
                                d=0.90, top=F.W_DARK), True))
        for s in (-1, 1):
            out.append(("%s_центр_кресло_%d" % (n, s),
                        F.armchair("%s_центр_кресло_%d" % (n, s),
                                   mid + s * 1.05, 0.0, z, (-s, 0),
                                   seat=F.FAB_WARM, w=0.72, d=0.74), True))
    out.append(("%s_кофе" % n,
                F.counter("%s_кофе" % n, x0 + 0.25, x0 + 0.85, -1.3, 1.3, z,
                          h=1.05), False))
    for s in (-1, 1):
        out.append(("%s_кадка_%d" % (n, s),
                    F.planter("%s_кадка_%d" % (n, s), x0 + 1.45,
                              s * (hw(x0 + 1.45) - 0.60), z, r=0.28,
                              h=0.46), False))
    out.append(("%s_ковёр" % n,
                F.rug("%s_ковёр" % n, x0 + 1.2, x1 - 1.2, -1.4, 1.4, z),
                False))
    return out


# --- бар и лаундж ----------------------------------------------------------

def bar_lounge(x0, x1, z, hw, n="бар"):
    """Бар-лаундж: стойка с табуретами по правому борту, диванные группы по
    левому, площадка для танцев в середине."""
    out = []
    wy = min(hw(x0 + 1.0), hw(x1 - 1.0)) - 0.55
    bx0, bx1 = x0 + 1.2, x0 + 8.6
    out.append(("%s_стойка" % n,
                F.counter("%s_стойка" % n, bx0, bx1, wy - 0.72, wy - 0.10,
                          z, h=F.BAR_H), True))
    out.append(("%s_подстолье" % n,
                [F.box("%s_подстолье" % n, bx0 + 0.1, bx1 - 0.1,
                       wy - 0.06, wy - 0.02, z + 0.92, z + 2.10, F.MIRROR)],
                False))
    out.append(("%s_бэкбар" % n,
                F.shelf("%s_бэкбар" % n, bx0 + 0.2, bx1 - 0.2,
                        wy - 0.02, wy + 0.28, z, h=2.05, shelves=5,
                        body=F.W_DARK, fill=True), False))
    for j in range(9):
        out.append(("%s_табурет_%d" % (n, j),
                    F.stool("%s_табурет_%d" % (n, j), bx0 + 0.55 + j * 0.88,
                            wy - 1.10, z), True))
    k = 0
    for x in F.rows(x0 + 1.4, x1 - 1.4, 3.6):
        cy = -(wy - 1.15)
        out.append(("%s_ковёр_%d" % (n, k),
                    F.rug("%s_ковёр_%d" % (n, k), x - 1.55, x + 1.55,
                          cy - 1.00, cy + 1.00, z), False))
        out.append(("%s_диван_%d" % (n, k),
                    F.sofa("%s_диван_%d" % (n, k), x - 1.25, x + 1.25,
                           cy - 1.00, cy - 0.55, z, (0, 1),
                           seat=F.LEATHER), True))
        out.append(("%s_стол_%d" % (n, k),
                    F.low_table("%s_стол_%d" % (n, k), x, cy + 0.05, z,
                                w=1.05, d=0.58, top=F.STONE), True))
        for j, sx in enumerate((-1, 1)):
            out.append(("%s_кресло_%d_%d" % (n, k, j),
                        F.armchair("%s_кресло_%d_%d" % (n, k, j),
                                   x + sx * 1.15, cy + 0.62, z, (0, -1),
                                   w=0.72, d=0.74), True))
        k += 1
    mid = (x0 + x1) / 2
    out.append(("%s_танцпол" % n,
                [F.box("%s_танцпол" % n, mid + 1.2, mid + 4.4, -1.5, 1.5,
                       z, z + 0.02, F.W_LIGHT)], False))
    out.append(("%s_пульт" % n,
                F.counter("%s_пульт" % n, x1 - 1.90, x1 - 0.90, -1.1, -0.2,
                          z, h=1.05, top=F.MET, body=F.MET), False))
    for s in (-1, 1):
        out.append(("%s_колонка_%d" % (n, s),
                    [F.box("%s_колонка_%d" % (n, s), x1 - 0.75, x1 - 0.40,
                           s * 1.4, s * 1.75, z, z + 1.60, F.MET)], False))
    return out


# --- библиотека и магазины -------------------------------------------------

def library_shops(x0, x1, z, hw, split=None, n="биб"):
    """Библиотека-лекторий в корме отсека, магазины в носовой части."""
    split = (x0 + x1) / 2 if split is None else split
    out = []
    for s in (-1, 1):
        wy = hw((x0 + split) / 2) - 0.30
        out.append(("%s_стеллаж_%d" % (n, s),
                    F.shelf("%s_стеллаж_%d" % (n, s), x0 + 0.70,
                            split - 0.90, s * wy, s * (wy - 0.34), z,
                            h=2.05, shelves=5), True))
    k = 0
    for x in F.rows(x0 + 1.0, split - 0.7, 1.75):
        p, _ = F.table_set("%s_стол_%d" % (n, k), x, 0.0, z, seats=4,
                           w=1.05, top=F.W_DARK, seat=F.LEATHER)
        p += [F.cyl("%s_лампа_%d" % (n, k), x, 0.0, 0.10,
                    z + F.TABLE_H - 0.01, z + F.TABLE_H + 0.34, F.BRASS,
                    12)]
        out.append(("%s_стол_%d" % (n, k), p, True))
        k += 1
    # магазины: витрины по бортам, касса и вешала в середине
    for s in (-1, 1):
        wy = hw((split + x1) / 2) - 0.30
        out.append(("%s_витрина_%d" % (n, s),
                    F.cabinet("%s_витрина_%d" % (n, s), split + 0.50,
                              x1 - 0.60, s * (wy - 0.55), s * wy, z,
                              h=1.55, top=F.GLASS, body=F.W_LIGHT), True))
    out.append(("%s_касса" % n,
                F.counter("%s_касса" % n, x1 - 1.55, x1 - 0.65, -0.9, 0.9,
                          z, h=1.05), False))
    for j, x in enumerate(F.rows(split + 0.9, x1 - 2.0, 1.9)):
        out.append(("%s_вешало_%d" % (n, j),
                    [F.cyl("%s_вешало_%d_нога" % (n, j), x, 0.0, 0.24,
                           z, z + 0.05, F.MET, 16),
                     F.cyl("%s_вешало_%d_стойка" % (n, j), x, 0.0, 0.03,
                           z + 0.05, z + 1.55, F.MET, 10),
                     F.box("%s_вешало_%d_штанга" % (n, j), x - 0.03,
                           x + 0.03, -0.55, 0.55, z + 1.50, z + 1.55,
                           F.MET),
                     F.box("%s_вешало_%d_одежда" % (n, j), x - 0.16,
                           x + 0.16, -0.50, 0.50, z + 0.55, z + 1.48,
                           F.FAB if j % 2 else F.FAB_WARM)], False))
    return out


# --- фитнес и йога ---------------------------------------------------------

def gym_yoga(x0, x1, z, hw, split=None, n="фит"):
    split = x0 + (x1 - x0) * 0.62 if split is None else split
    out = []
    k = 0
    for x in F.rows(x0 + 0.9, split - 0.8, 1.35):
        wy = hw(x) - 0.60
        for s in (-1, 1):
            cy = s * (wy - 0.42)
            out.append(("%s_дорожка_%d" % (n, k),
                        [F.box("%s_дорожка_%d_рама" % (n, k), x - 0.48,
                               x + 0.48, cy - 0.38, cy + 0.38, z, z + 0.22,
                               F.MET),
                         F.box("%s_дорожка_%d_полотно" % (n, k), x - 0.40,
                               x + 0.40, cy - 0.30, cy + 0.30, z + 0.22,
                               z + 0.26, F.ACC),
                         F.box("%s_дорожка_%d_стойка" % (n, k), x - 0.46,
                               x - 0.38, cy - 0.34, cy + 0.34, z + 0.26,
                               z + 1.15, F.MET),
                         F.box("%s_дорожка_%d_экран" % (n, k), x - 0.44,
                               x - 0.40, cy - 0.26, cy + 0.26, z + 1.00,
                               z + 1.32, F.SCREEN_M)], True))
            k += 1
    for s in (-1, 1):
        wy = hw((x0 + split) / 2) - 0.28
        out.append(("%s_зеркало_%d" % (n, s),
                    [F.box("%s_зеркало_%d" % (n, s), x0 + 0.6, split - 0.6,
                           s * wy, s * (wy - 0.02), z + 0.50, z + 2.05,
                           F.MIRROR)], False))
    out.append(("%s_стойка_гантелей" % n,
                [F.box("%s_стойка_гантелей_рама" % n, split - 2.2,
                       split - 0.9, -0.55, -0.20, z, z + 0.85, F.MET)]
                + [F.cyl("%s_гантель_%d" % (n, j), split - 2.1 + j * 0.28,
                         -0.38, 0.09, z + 0.85, z + 0.99, F.ACC, 10)
                   for j in range(5)], False))
    for j, x in enumerate(F.rows(split - 3.4, split - 0.8, 1.30)):
        out.append(("%s_скамья_%d" % (n, j),
                    [F.box("%s_скамья_%d_ложе" % (n, j), x - 0.55, x + 0.55,
                           0.20, 0.52, z + 0.40, z + 0.48, F.LEATHER),
                     F.box("%s_скамья_%d_нога_0" % (n, j), x - 0.52,
                           x - 0.42, 0.28, 0.44, z, z + 0.40, F.MET),
                     F.box("%s_скамья_%d_нога_1" % (n, j), x + 0.42,
                           x + 0.52, 0.28, 0.44, z, z + 0.40, F.MET)],
                    False))
    # йога
    ys = split + 0.7
    for j, x in enumerate(F.rows(ys, x1 - 0.7, 1.05)):
        wy = hw(x) - 0.70
        for s in (-1, 1):
            out.append(("%s_коврик_%d_%d" % (n, j, s),
                        [F.box("%s_коврик_%d_%d" % (n, j, s), x - 0.32,
                               x + 0.32, s * 0.35, s * (min(wy, 1.95)),
                               z, z + 0.02, F.ACC)], False))
    out.append(("%s_блоки" % n,
                [F.box("%s_блоки" % n, x1 - 1.1, x1 - 0.45, -0.35, 0.35,
                       z, z + 0.55, F.FAB_WARM)], False))
    return out


# --- спа и кормовой салон --------------------------------------------------

def spa_salon(x0, x1, z, hw, split=None, n="спа"):
    """В корме — салон отдыха, дальше в нос — спа с купелью и массажем."""
    split = x0 + 5.2 if split is None else split
    out = []
    k = 0
    for x in F.rows(x0 + 0.8, split - 0.6, 1.70):
        wy = hw(x) - 0.65
        for s in (-1, 1):
            cy = s * (wy - 0.55)
            out.append(("%s_кресло_%d" % (n, k),
                        F.armchair("%s_кресло_%d" % (n, k), x, cy, z,
                                   (0, -s), seat=F.FAB_WARM), True))
            k += 1
        out.append(("%s_стол_%d" % (n, k),
                    F.low_table("%s_стол_%d" % (n, k), x, 0.0, z, w=0.70,
                                d=0.70, top=F.W_DARK), True))
        k += 1
    # купель
    cx = split + 1.9
    out.append(("%s_купель" % n,
                [F.cyl("%s_купель_борт" % n, cx, 0.0, 1.35, z, z + 0.55,
                       F.TILE, 28),
                 F.cyl("%s_купель_вода" % n, cx, 0.0, 1.22, z + 0.30,
                       z + 0.48, "гор_вода", 28)], True))
    for j, x in enumerate(F.rows(split + 4.0, x1 - 1.1, 1.70)):
        wy = hw(x) - 0.70
        for s in (-1, 1):
            cy = s * (wy - 0.45)
            out.append(("%s_массаж_%d_%d" % (n, j, s),
                        [F.box("%s_массаж_%d_%d_цоколь" % (n, j, s),
                               x - 0.85, x + 0.85, cy - 0.32, cy + 0.32,
                               z, z + 0.16, F.W_LIGHT),
                         F.box("%s_массаж_%d_%d_ложе" % (n, j, s),
                               x - 0.95, x + 0.95, cy - 0.38, cy + 0.38,
                               z + 0.16, z + 0.70, F.LINEN),
                         F.box("%s_массаж_%d_%d_валик" % (n, j, s),
                               x + 0.68, x + 0.92, cy - 0.30, cy + 0.30,
                               z + 0.70, z + 0.84, F.LINEN)], True))
    # шезлонги вокруг купели
    for j, dx in enumerate((-1.05, 1.05)):
        for s in (-1, 1):
            lx = cx + dx
            ly = s * (hw(cx) - 1.05)
            out.append(("%s_шезлонг_%d_%d" % (n, j, s),
                        [F.box("%s_шезлонг_%d_%d_рама" % (n, j, s),
                               lx - 0.32, lx + 0.32, ly - 0.85, ly + 0.85,
                               z, z + 0.34, F.W_LIGHT),
                         F.box("%s_шезлонг_%d_%d_ложе" % (n, j, s),
                               lx - 0.34, lx + 0.34, ly - 0.90, ly + 0.90,
                               z + 0.34, z + 0.44, F.LINEN),
                         F.box("%s_шезлонг_%d_%d_изголовье" % (n, j, s),
                               lx - 0.32, lx + 0.32, ly - s * 0.90,
                               ly - s * 0.62, z + 0.44, z + 0.72, F.LINEN)],
                        True))
    out.append(("%s_бельё" % n,
                F.shelf("%s_бельё" % n, x1 - 1.95, x1 - 1.45,
                        -hw(x1 - 1.7) + 0.30, -hw(x1 - 1.7) + 0.64, z,
                        h=1.55, shelves=4, body=F.W_LIGHT, fill=False),
                False))
    out.append(("%s_стойка" % n,
                F.counter("%s_стойка" % n, x1 - 1.35, x1 - 0.55, -1.1, 1.1,
                          z, h=1.05), False))
    for s in (-1, 1):
        out.append(("%s_кадка_%d" % (n, s),
                    F.planter("%s_кадка_%d" % (n, s), split + 0.1,
                              s * (hw(split) - 0.70), z, r=0.30, h=0.50),
                    False))
    return out


# --- детский и подростковый клубы -----------------------------------------

def kids(x0, x1, z, hw, n="клуб"):
    out = []
    k = 0
    for x in F.rows(x0 + 1.1, x1 - 2.4, 2.15):
        wy = hw(x) - 0.75
        for s in (-1, 1):
            cy = s * (wy - 0.95)
            p, _ = F.table_set("%s_стол_%d" % (n, k), x, cy, z, seats=4,
                               w=0.80, round_top=True, top=F.W_LIGHT,
                               seat=F.ACC, reach=0.58)
            out.append(("%s_стол_%d" % (n, k), p, True))
            k += 1
    out.append(("%s_мат" % n,
                F.rug("%s_мат" % n, x0 + 0.6, x1 - 2.6, -1.0, 1.0, z,
                      F.ACC), False))
    for j in range(5):
        out.append(("%s_блок_%d" % (n, j),
                    F.bench("%s_блок_%d" % (n, j), x0 + 1.0 + j * 0.85,
                            x0 + 1.55 + j * 0.85, -0.45, 0.10, z,
                            mat=F.FAB_WARM, h=0.34), False))
    for s in (-1, 1):
        wy = hw(x1 - 1.5) - 0.30
        out.append(("%s_стеллаж_%d" % (n, s),
                    F.shelf("%s_стеллаж_%d" % (n, s), x1 - 2.1, x1 - 0.5,
                            s * wy, s * (wy - 0.32), z, h=1.35, shelves=3),
                    False))
    out.append(("%s_экран" % n,
                [F.box("%s_экран_рама" % n, x1 - 0.32, x1 - 0.26, -1.1, 1.1,
                       z + 0.85, z + 2.00, F.MET),
                 F.box("%s_экран" % n, x1 - 0.34, x1 - 0.32, -1.05, 1.05,
                       z + 0.90, z + 1.95, F.SCREEN_M)], False))
    return out


# --- служебные помещения ---------------------------------------------------

def galley_block(x0, x1, z, hw, n="служ"):
    """Камбуз, провизия, прачечная и кают-компания первой палубы."""
    out = []
    span = x1 - x0
    gal0, gal1 = x0, x0 + span * 0.38          # камбуз
    prov1 = gal1 + span * 0.26                 # провизия
    laun1 = prov1 + span * 0.18                # прачечная
    # камбуз: две технологические линии вдоль бортов и остров в середине
    for s in (-1, 1):
        wy = hw((gal0 + gal1) / 2) - 0.35
        out.append(("%s_линия_%d" % (n, s),
                    F.counter("%s_линия_%d" % (n, s), gal0 + 0.5, gal1 - 0.5,
                              s * (wy - 0.75), s * wy, z, h=0.90,
                              top=F.MET, body=F.MET), True))
        sy0, sy1 = sorted((s * (wy - 0.42), s * wy))
        brackets = [F.box("%s_кронштейн_%d_%d" % (n, s, bi), bx - 0.03,
                          bx + 0.03, sy0, sy1, z + 0.90, z + 1.50, F.MET)
                    for bi, bx in enumerate(F.rows(gal0 + 0.8, gal1 - 0.8,
                                                   1.60))]
        out.append(("%s_полка_%d" % (n, s),
                    brackets
                    + [F.box("%s_полка_%d" % (n, s), gal0 + 0.6, gal1 - 0.6,
                             sy0, sy1, z + 1.45, z + 1.50, F.MET)], False))
    for j, x in enumerate(F.rows(gal0 + 1.0, gal1 - 1.0, 2.2)):
        out.append(("%s_плита_%d" % (n, j),
                    [F.box("%s_плита_%d_корпус" % (n, j), x - 0.85, x + 0.85,
                           -0.60, 0.60, z, z + 0.88, F.MET),
                     F.box("%s_плита_%d_верх" % (n, j), x - 0.88, x + 0.88,
                           -0.63, 0.63, z + 0.88, z + 0.94, F.MET),
                     F.box("%s_плита_%d_зонт" % (n, j), x - 1.00, x + 1.00,
                           -0.75, 0.75, z + 1.75, z + 2.00, F.MET),
                     F.box("%s_плита_%d_подвес_0" % (n, j), x - 0.92,
                           x - 0.86, -0.70, -0.64, z + 2.00, z + 2.06,
                           F.MET),
                     F.box("%s_плита_%d_подвес_1" % (n, j), x + 0.86,
                           x + 0.92, 0.64, 0.70, z + 2.00, z + 2.06,
                           F.MET)], True))
    # провизионка: стеллажи поперёк
    for j, x in enumerate(F.rows(gal1 + 0.6, prov1 - 0.6, 1.5)):
        wy = hw(x) - 0.55
        out.append(("%s_провизия_%d" % (n, j),
                    F.shelf("%s_провизия_%d" % (n, j), x - 0.32, x + 0.32,
                            -wy, wy, z, h=2.00, shelves=4, body=F.MET,
                            fill=False), True))
    # прачечная: машины в линию и столы
    for j, x in enumerate(F.rows(prov1 + 0.6, laun1 - 0.6, 1.0)):
        for s in (-1, 1):
            wy = hw(x) - 0.45
            out.append(("%s_машина_%d_%d" % (n, j, s),
                        [F.box("%s_машина_%d_%d" % (n, j, s), x - 0.38,
                               x + 0.38, s * (wy - 0.72), s * wy, z,
                               z + 0.95, F.MET),
                         F.cyl("%s_люк_%d_%d" % (n, j, s), x,
                               s * (wy - 0.70), 0.22, z + 0.40, z + 0.42,
                               F.GLASS, 16)],
                        True))
    # кают-компания: столы со стульями
    k = 0
    for x in F.rows(laun1 + 0.8, x1 - 0.6, 2.1):
        wy = hw(x) - 0.75
        for s in (-1, 1):
            cy = s * (wy - 0.95)
            if wy < 1.6:
                continue
            p, _ = F.table_set("%s_стол_%d" % (n, k), x, cy, z, seats=4,
                               w=0.85, top=F.W_LIGHT, seat=F.FAB)
            out.append(("%s_стол_%d" % (n, k), p, True))
            k += 1
    return out


def service_counter(x0, x1, z, hw, n="разд"):
    """Раздаточная и буфет: линия выдачи, тепловые шкафы, мойка."""
    out = []
    wy = hw((x0 + x1) / 2) - 0.40
    out.append(("%s_линия" % n,
                F.counter("%s_линия" % n, x0 + 0.5, x1 - 0.5, -wy,
                          -wy + 0.70, z, h=0.92, top=F.MET, body=F.MET),
                True))
    out.append(("%s_шкафы" % n,
                F.cabinet("%s_шкафы" % n, x0 + 0.5, x1 - 0.5, wy - 0.65, wy,
                          z, h=1.80, top=F.MET, body=F.MET), True))
    for j, x in enumerate(F.rows(x0 + 1.0, x1 - 1.0, 1.6)):
        out.append(("%s_тележка_%d" % (n, j),
                    [F.box("%s_тележка_%d_корпус" % (n, j), x - 0.35,
                           x + 0.35, -0.30, 0.30, z + 0.10, z + 0.85,
                           F.MET)]
                    + [F.cyl("%s_тележка_%d_колесо_%d" % (n, j, c),
                             x + (0.28 if c % 2 else -0.28),
                             0.22 if c < 2 else -0.22, 0.05, z, z + 0.10,
                             F.MET, 8) for c in range(4)], False))
    return out


ROOMS = {
    "мебель_ресторан": ("главная", 11.30, 33.40, restaurant, "рест"),
    "мебель_раздаточная": ("главная", 40.30, 44.10, service_counter, "разд"),
    "мебель_театр": ("главная", 44.30, 63.10, theatre, "театр"),
    "мебель_бистро": ("главная", 66.30, 73.90, bistro, "бистро"),
    "мебель_лобби": ("главная", 74.10, 91.40, lobby, "лобби"),
    "мебель_главная_носовой_салон": ("главная", 124.10, 129.60, bow_salon,
                                     "нос_гл"),
    "мебель_верхняя_салон_спа": ("верхняя", 11.30, 26.40, spa_salon, "спа"),
    "мебель_фитнес_йога": ("верхняя", 26.60, 43.40, gym_yoga, "фит"),
    "мебель_библиотека_магазины": ("верхняя", 43.60, 51.80, library_shops,
                                   "биб"),
    "мебель_верхняя_носовой_салон": ("верхняя", 122.30, 129.60, bow_salon,
                                     "нос_вп"),
    "мебель_бар_лаундж": ("шлюпочная", 39.80, 58.10, bar_lounge, "бар"),
    "мебель_детский_клуб": ("шлюпочная", 90.40, 97.80, kids, "клуб"),
    "мебель_служебный_блок": ("первая", 39.70, 59.80, galley_block, "служ"),
}


# --- проверка проходов ------------------------------------------------------

def circulation(groups, x0, x1, z, hw, cell=0.10, main=1.20, access=0.50,
                seat_reach=0.75, h_block=1.10, h_floor=0.30):
    """Проходы в зале: магистраль и подход к каждому месту.

    Зал растрируется сеткой 100 мм. Занятая клетка — деталь, стоящая на полу
    и выше `h_floor`: помост, ступень, ковёр и танцпол проход не
    перекрывают, по ним ходят; подвес, экран и полка над головой — тоже нет.

    Два просвета, а не один. Магистраль зала меряется по `main` = 1,20 м:
    по ней расходятся на посадку и уходят по тревоге. Подход к своему месту
    меряется по `access` = 0,50 м — между спинками соседних стульев
    протискиваются, и требовать там 1,20 м значит выкинуть половину посадки.
    """
    nx = int((x1 - x0) / cell) + 1
    ny = int(2 * max(hw(x0 + (x1 - x0) * k / 20.0) for k in range(21))
             / cell) + 1
    y0 = -(ny - 1) * cell / 2.0

    def ij(x, y):
        return int(round((x - x0) / cell)), int(round((y - y0) / cell))

    free = [[False] * ny for _ in range(nx)]
    for i in range(nx):
        w = hw(x0 + i * cell)
        for j in range(ny):
            free[i][j] = abs(y0 + j * cell) <= w - 0.05
    seats = []
    for _, parts, _ in groups:
        for q in parts:
            a0, a1, b0, b1, c0, c1 = F.bounds(q)
            if q[1].endswith("_сиденье"):
                seats.append(((a0 + a1) / 2, (b0 + b1) / 2))
            if c0 - z > h_block or c1 - z <= h_floor:
                continue
            i0, j0 = ij(a0, b0)
            i1, j1 = ij(a1, b1)
            for i in range(max(0, i0), min(nx, i1 + 1)):
                for j in range(max(0, j0), min(ny, j1 + 1)):
                    free[i][j] = False
    INF = 10 ** 6
    d = [[0 if not free[i][j] else INF for j in range(ny)] for i in range(nx)]
    q = [(i, j) for i in range(nx) for j in range(ny) if d[i][j] == 0]
    head = 0
    while head < len(q):
        i, j = q[head]
        head += 1
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < nx and 0 <= b < ny and d[a][b] > d[i][j] + 1:
                d[a][b] = d[i][j] + 1
                q.append((a, b))

    def fill(need, seeds):
        seen = set()
        st = [c for c in seeds if d[c[0]][c[1]] >= need]
        seen.update(st)
        while st:
            i, j = st.pop()
            for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                a, b = i + di, j + dj
                if 0 <= a < nx and 0 <= b < ny and (a, b) not in seen                         and d[a][b] >= need:
                    seen.add((a, b))
                    st.append((a, b))
        return seen

    n_main = int(round(main / 2 / cell))
    wide = [(i, j) for i in range(nx) for j in range(ny)
            if d[i][j] >= n_main]
    best = set()
    left = set(wide)
    while left:
        comp = fill(n_main, [next(iter(left))])
        left -= comp
        if len(comp) > len(best):
            best = comp
    xs = [x0 + i * cell for (i, _) in best]
    reach = fill(int(round(access / 2 / cell)), list(best))
    r = int(round(seat_reach / cell))
    far = []
    for sx, sy in seats:
        si, sj = ij(sx, sy)
        ok = False
        for i in range(si - r, si + r + 1):
            for j in range(sj - r, sj + r + 1):
                if (i, j) in reach:
                    ok = True
                    break
            if ok:
                break
        if not ok:
            far.append((round(sx, 1), round(sy, 1)))
    span = round(max(xs) - min(xs), 1) if xs else 0.0
    rep = {"магистраль": span, "мест": len(seats), "без подхода": len(far),
           "примеры": far[:6]}
    return (not far and span > (x1 - x0) * 0.6), rep
