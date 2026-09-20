# -*- coding: utf-8 -*-
r"""Набор корпуса, настилы и переборки по плазовой таблице.

Запускается внутри Blender:
    exec(open(r"E:\Ship_docx\scripts\blender_набор_корпуса.py",
              encoding="utf-8").read())
    rebuild_all()

Все связи строятся по той же функции обвода, что и расчёты, поэтому набор
садится на обшивку без зазоров и без пересечений с ней.
"""
import bpy, bmesh, math, mathutils, sys, os

ROOT = r"E:\Ship_docx"
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))
for _m in [k for k in list(sys.modules) if k.startswith("lib")]:
    del sys.modules[_m]
from lib import gorizont as G, gorizont_hydro as H, gorizont_struct as S

M = mathutils.Matrix
COL = "40_Набор_корпуса"
DB = S.DB_HEIGHT            # 1.30 — второе дно = настил первой палубы
DB_ER = 0.465               # в машинном отделении
ER0, ER1 = 12.0, 34.0
SP = S.SPACING              # 0.55
FR = S.FRAME_SPACING        # 2.20
MARGIN = 0.060              # набор утоплен в обшивку на 60 мм


def col(name=COL):
    c = bpy.data.collections.get(name)
    if c is None:
        c = bpy.data.collections.new(name)
        bpy.context.scene.collection.children.link(c)
    return c


def drop(name):
    o = bpy.data.objects.get(name)
    if o:
        bpy.data.objects.remove(o, do_unlink=True)


def put(name, bm, matname, collection=COL):
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    col(collection).objects.link(o)
    m = bpy.data.materials.get(matname)
    if m:
        o.data.materials.append(m)
    return o


def box(bm, x0, x1, y0, y1, z0, z1):
    if x1 - x0 < 1e-5 or y1 - y0 < 1e-5 or z1 - z0 < 1e-5:
        return
    bmesh.ops.create_cube(bm, size=1.0,
        matrix=M.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        @ M.Diagonal((x1 - x0, y1 - y0, z1 - z0, 1.0)))


def hb(x, z):
    return H.half_breadth(x, z)


def db_top(x):
    """Верх второго дна: в машинном отделении опущено."""
    return DB_ER if ER0 <= x <= ER1 else DB


def deck_y(x, z, gap=MARGIN):
    return max(hb(x, z) - gap, 0.0)


def min_y(x0, x1, z0, z1, gap=MARGIN, n=12):
    """Наименьшая полуширота на участке — связь не должна выходить за обшивку."""
    m = 1e9
    for i in range(n + 1):
        x = x0 + (x1 - x0) * i / n
        for j in range(n + 1):
            z = z0 + (z1 - z0) * j / n
            m = min(m, hb(x, z))
    return max(m - gap, 0.0)


# --------------------------------------------------------------- настилы ----
def build_decks():
    """Настил второго дна и настил первой палубы с вырезами."""
    drop("настил_второго_дна")
    drop("настил_первой_палубы")
    # второе дно в машинном отделении
    bm = bmesh.new()
    x = ER0 + 1.5
    while x < ER1 - 1.5:
        xn = min(x + 0.5, ER1 - 1.5)
        y = min_y(x, xn, DB_ER - 0.008, DB_ER)
        box(bm, x, xn, -y, y, DB_ER - 0.008, DB_ER)
        x = xn
    put("настил_второго_дна", bm, "гор_палуба_сталь")
    # настил первой палубы
    HOLES = [(34.22, 39.52, -2.10, 2.22),      # кормовой трап-холл
             (92.22, 97.52, -2.10, 2.22),      # носовой трап-холл
             (ER0 + 0.6, ER1 - 0.6, -6.2, 6.2),  # машинное отделение
             (10.02, 11.48, -8.30, 8.30),      # помещение кормового ПУ
             (101.60, 102.40, -0.21, 0.21)]    # шахта привода носового ПУ
    bm = bmesh.new()
    x = 9.0
    while x < 127.0:
        xn = min(x + 0.5, 127.0)
        y = min_y(x, xn, DB - 0.008, DB)
        segs = [(-y, y)]
        for (hx0, hx1, hy0, hy1) in HOLES:
            if xn <= hx0 or x >= hx1:
                continue
            out = []
            for (a, b) in segs:
                if hy1 <= a or hy0 >= b:
                    out.append((a, b)); continue
                if a < hy0:
                    out.append((a, hy0))
                if hy1 < b:
                    out.append((hy1, b))
            segs = out
        for (a, b) in segs:
            if b - a > 1e-4:
                box(bm, x, xn, a, b, DB - 0.008, DB)
        x = xn
    put("настил_первой_палубы", bm, "гор_палуба_сталь")
    return ("настил_второго_дна", "настил_первой_палубы")


# ------------------------------------------------------------ переборки ----
def build_bulkheads():
    drop("набор_переборки_водонепроницаемые")
    bm = bmesh.new()
    for xb in H.BULKHEADS[1:-1]:
        zk = H._column(xb)[0]
        n = 26
        for k in range(n):
            z0 = zk + (G.DEPTH - zk) * k / n
            z1 = zk + (G.DEPTH - zk) * (k + 1) / n
            y = min_y(xb, xb, z0, z1)
            box(bm, xb - 0.0035, xb + 0.0035, -y, y, z0, z1)
    put("набор_переборки_водонепроницаемые", bm, "гор_набор_переборка")
    return "набор_переборки_водонепроницаемые"


# ---------------------------------------------------- днищевой набор -------
def build_bottom():
    """Вертикальный киль, днищевые стрингеры, флоры."""
    drop("набор_киль_и_стрингеры")
    drop("набор_флоры")
    bm = bmesh.new()
    x = 2.0
    while x < 127.0:
        xn = min(x + 0.5, 127.0)
        zk = max(H._column(x)[0], H._column(xn)[0])
        top = min(db_top(x), db_top(xn))
        if top - zk > 0.08:
            box(bm, x, xn, -0.006, 0.006, zk, top)          # вертикальный киль
            ylim = min_y(x, xn, zk + 0.01, top)
            for yy in (2.75, 5.50):
                if ylim > yy + 0.2:
                    for s in (1, -1):
                        box(bm, x, xn, s * yy - 0.005, s * yy + 0.005, zk, top)
        x = xn
    put("набор_киль_и_стрингеры", bm, "гор_набор_днище")
    bm = bmesh.new()
    n = int(127.0 / FR)
    for i in range(1, n + 1):
        xf = i * FR
        if xf < 2.0 or xf > 126.0:
            continue
        zk = H._column(xf)[0]
        top = db_top(xf)
        if top - zk < 0.08:
            continue
        m = 12
        for k in range(m):
            z0 = zk + (top - zk) * k / m
            z1 = zk + (top - zk) * (k + 1) / m
            y = min_y(xf, xf, z0, z1)
            box(bm, xf - 0.0045, xf + 0.0045, -y, y, z0, z1)
    put("набор_флоры", bm, "гор_набор_днище")
    return ("набор_киль_и_стрингеры", "набор_флоры")


# ------------------------------------------------- шпангоуты и стрингеры ---
def _frame_strip(bm, x, half, z_from, z_to, n=18):
    """Полоса по обводу на шпангоуте x от z_from до z_to."""
    for k in range(n):
        z0 = z_from + (z_to - z_from) * k / n
        z1 = z_from + (z_to - z_from) * (k + 1) / n
        yo = min_y(x, x, z0, z1)
        yi = yo - half
        if yi <= 0.05:
            continue
        for s in (1, -1):
            box(bm, x - 0.004, x + 0.004, s * yi, s * yo, z0, z1)


def deck_top(x):
    """Верх набора на шпангоуте x.

    Главная палуба плоская на высоте борта D, подъём обвода выше неё —
    фальшборт, набора под ним нет (см. blender_фальшборт.py).
    """
    return min(H.side_height(x), G.DEPTH)


def build_frames():
    """Шпангоуты через 550 мм и рамные через 2200 мм."""
    drop("набор_шпангоуты")
    drop("набор_рамные_шпангоуты_и_бимсы")
    bm_o, bm_r = bmesh.new(), bmesh.new()
    n = int(G.LOA / SP)
    for i in range(1, n):
        x = i * SP
        if x < 2.0 or x > 136.5:
            continue
        zk = H._column(x)[0]
        zb = deck_top(x)
        frame = (abs(x / FR - round(x / FR)) < 1e-6)
        z_from = max(zk, db_top(x) - 0.05)
        if zb - z_from < 0.2:
            continue
        if frame:
            _frame_strip(bm_r, x, 0.50, z_from, zb, 20)
            # рамный бимс под главной палубой
            y = min_y(x, x, zb - 0.50, zb - 0.012)
            if y > 0.6:
                box(bm_r, x - 0.005, x + 0.005, -y, y, zb - 0.50, zb - 0.012)
        else:
            _frame_strip(bm_o, x, 0.12, z_from, zb, 14)
            y = min_y(x, x, zb - 0.12, zb - 0.012)
            if y > 0.6:
                box(bm_o, x - 0.004, x + 0.004, -y, y, zb - 0.12, zb - 0.012)
    put("набор_шпангоуты", bm_o, "гор_набор_борт")
    put("набор_рамные_шпангоуты_и_бимсы", bm_r, "гор_набор_борт")
    return ("набор_шпангоуты", "набор_рамные_шпангоуты_и_бимсы")


def build_stringers():
    """Бортовые стрингеры и карлингсы главной палубы."""
    drop("набор_стрингеры_и_карлингсы")
    bm = bmesh.new()
    x = 2.0
    while x < 137.0:
        xn = min(x + 0.5, 137.0)
        for z in (2.60,):
            y = min_y(x, xn, z - 0.009, z)
            if y > 0.6:
                for s in (1, -1):
                    box(bm, x, xn, s * (y - 0.40), s * y, z - 0.009, z)
        zb = min(deck_top(x), deck_top(xn))
        for yy in (0.0, 4.10):
            yl = min_y(x, xn, zb - 0.60, zb - 0.012)
            if yl > yy + 0.3:
                for s in ((1, -1) if yy else (1,)):
                    box(bm, x, xn, s * yy - 0.005, s * yy + 0.005,
                        zb - 0.60, zb - 0.012)
        x = xn
    put("набор_стрингеры_и_карлингсы", bm, "гор_набор_палуба")
    return "набор_стрингеры_и_карлингсы"


def build_longitudinals():
    """Продольные рёбра днища, второго дна и главной палубы."""
    drop("набор_продольные_рёбра")
    bm = bmesh.new()
    x = 2.0
    while x < 137.0:
        xn = min(x + 1.0, 137.0)
        zk = max(H._column(x)[0], H._column(xn)[0])
        top = min(db_top(x), db_top(xn))
        zb = min(deck_top(x), deck_top(xn))
        ymax_b = min_y(x, xn, zk + 0.005, zk + 0.14)
        ymax_d = min_y(x, xn, top - 0.12, top)
        ymax_p = min_y(x, xn, zb - 0.12, zb - 0.012)
        j = 1
        while j * SP < 7.6:
            yy = j * SP
            for s in (1, -1):
                if yy < ymax_b - 0.15:
                    box(bm, x, xn, s * yy - 0.004, s * yy + 0.004, zk, zk + 0.14)
                if top - zk > 0.2 and yy < ymax_d - 0.15:
                    box(bm, x, xn, s * yy - 0.004, s * yy + 0.004, top - 0.12, top)
                if yy < ymax_p - 0.15:
                    box(bm, x, xn, s * yy - 0.004, s * yy + 0.004, zb - 0.12, zb - 0.012)
            j += 1
        x = xn
    put("набор_продольные_рёбра", bm, "гор_набор_продольный")
    return "набор_продольные_рёбра"


def build_tank_bulkheads():
    """Переборки цистерн второго дна."""
    drop("цистерны_поперечные_переборки")
    drop("цистерны_продольные_переборки")
    bm = bmesh.new()
    for xb in (40.0, 44.0, 58.0, 70.0, 78.0, 86.0, 100.0, 114.0):
        zk = H._column(xb)[0]
        top = db_top(xb)
        m = 10
        for k in range(m):
            z0 = zk + (top - zk) * k / m
            z1 = zk + (top - zk) * (k + 1) / m
            y = min_y(xb, xb, z0, z1)
            box(bm, xb - 0.0035, xb + 0.0035, -y, y, z0, z1)
    put("цистерны_поперечные_переборки", bm, "гор_набор_переборка")
    bm = bmesh.new()
    x = 34.0
    while x < 114.0:
        xn = min(x + 1.0, 114.0)
        zk = max(H._column(x)[0], H._column(xn)[0])
        top = min(db_top(x), db_top(xn))
        if min_y(x, xn, zk + 0.01, top) > G.LONG_BULKHEAD_Y + 0.05:
            for s in (1, -1):
                box(bm, x, xn, s * G.LONG_BULKHEAD_Y - 0.0035,
                    s * G.LONG_BULKHEAD_Y + 0.0035, zk, top)
        x = xn
    put("цистерны_продольные_переборки", bm, "гор_набор_переборка")
    return ("цистерны_поперечные_переборки", "цистерны_продольные_переборки")


def rebuild_all():
    made = []
    made += list(build_decks())
    made.append(build_bulkheads())
    made += list(build_bottom())
    made += list(build_frames())
    made.append(build_stringers())
    made.append(build_longitudinals())
    made += list(build_tank_bulkheads())
    return made
