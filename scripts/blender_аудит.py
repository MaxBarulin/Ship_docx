# -*- coding: utf-8 -*-
r"""Аудит сцены: пересечения объектов и выход за обвод корпуса.

Два независимых теста.

1.  Пересечения.  Широкая фаза — габаритные параллелепипеды в мировых
    координатах.  Узкая — BVHTree.overlap() по треугольникам.  Касание
    поверхностей (палуба под каютой, набор к обшивке) пересечением не
    считается: пара попадает в отчёт, только если реальная глубина
    взаимного проникновения больше DEPTH (25 мм).  Глубина меряется так:
    точки одной сетки, оказавшиеся внутри другой (чётность пересечений
    луча в двух направлениях), отодвигаются до ближайшей грани — берётся
    максимум.

2.  Выход за обвод.  Каждая вершина сравнивается с полуширотой корпуса
    (ниже 4,1 м) или надстройки (выше) на своей абсциссе и высоте.

Запуск внутри Blender:
    exec(open(r"E:\Ship_docx\scripts\blender_аудит.py", encoding="utf-8").read())
    audit()
"""
import bpy, sys, math
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont_hydro as H
from lib import gorizont as G

DEPTH = 0.025          # допустимая глубина взаимного проникновения, м
OUT_TOL = 0.02         # допустимый выход за обвод, м
Z_SUPER = 4.10         # выше этой отметки обвод задаёт надстройка
APPEND_HALF = 4.00     # предел для выступающих частей ниже киля

# Сварной корпус: обшивка, набор, палубы и переборки цистерн по определению
# примыкают друг к другу — взаимное касание пересечением не считается.
TOUCHING = ("40_Набор_корпуса", "01_Корпус", "03_Палубы", "02_Надстройка")
# Коллекции, которые вообще не участвуют в проверке обвода.
NO_HULL = ("60_Окружение", "20_Эталоны_кают")
SKIP = ("20_Эталоны_кают", "60_Окружение")
# Оболочки: находиться внутри них — норма, поэтому «точка внутри» для них
# пересечением не считается. Выход наружу ловит проверка обвода.
ENCLOSURE = ("корпус", "надстройка", "рубка", "настил_", "палуба_",
             "платформа_", "второе_дно", "обшивка")
# Надстройку проверяем по её борту только для внутреннего насыщения.
INSIDE_SUPER = ("10_Каюты", "30_Общественные", "31_Мебель", "32_Служебные")


def _mesh_objs(collections=None):
    out = []
    for c in bpy.data.collections:
        if c.name in SKIP:
            continue
        if collections and c.name not in collections:
            continue
        for o in c.objects:
            if o.type == "MESH" and len(o.data.polygons) and o.visible_get():
                out.append((c.name, o))
    return out


def _world_tris(o, dg):
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    mw = o.matrix_world
    vs = [mw @ v.co for v in me.vertices]
    tris = []
    for p in me.polygons:
        vi = list(p.vertices)
        for k in range(1, len(vi) - 1):
            tris.append((vi[0], vi[k], vi[k + 1]))
    ev.to_mesh_clear()
    return vs, tris


def _aabb(vs):
    xs = [v.x for v in vs]; ys = [v.y for v in vs]; zs = [v.z for v in vs]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


# Штатные проходы сквозь конструкцию: линии вала в дейдвудных трубах,
# баллеры рулей в гельмпортовых трубах, туннели подруливающих устройств.
# В металле это не пересечение, а вырез с уплотнением, поэтому такие пары
# в отчёт не идут.
PENETRATIONS = (
    ("дрк_", ("корпус", "набор_", "настил_", "цистерны_")),
    ("мо_гребные_электродвигатели", ("корпус", "набор_", "настил_")),
    ("устр_подрул", ("корпус", "набор_", "настил_")),
)


def _penetration(a, b):
    for pref, others in PENETRATIONS:
        if a.startswith(pref) and b.startswith(others):
            return True
        if b.startswith(pref) and a.startswith(others):
            return True
    return False


def _encl(d):
    return d["obj"].name.startswith(ENCLOSURE)


def _contains(outer, inner, m=0.05):
    ox0, ox1, oy0, oy1, oz0, oz1 = outer
    ix0, ix1, iy0, iy1, iz0, iz1 = inner
    return (ox0 <= ix0 + m and ox1 >= ix1 - m and oy0 <= iy0 + m
            and oy1 >= iy1 - m and oz0 <= iz0 + m and oz1 >= iz1 - m)


def _inside(bvh, p, span):
    """Точка внутри замкнутой сетки? Чётность пересечений в двух лучах."""
    hits = 0
    for d in (Vector((0, 0, 1)), Vector((0, 0, -1))):
        n, o, cnt = 0, p + d * 1e-4, 0
        pos = o.copy()
        while cnt < 64:
            hit = bvh.ray_cast(pos, d, span)
            if hit[0] is None:
                break
            n += 1
            pos = hit[0] + d * 1e-4
            cnt += 1
        if n % 2 == 1:
            hits += 1
    return hits == 2


def pairs(depth=DEPTH, collections=None, verbose=True):
    """Список пар объектов, реально влезающих друг в друга."""
    dg = bpy.context.evaluated_depsgraph_get()
    objs = _mesh_objs(collections)
    data = []
    for cname, o in objs:
        vs, tris = _world_tris(o, dg)
        if not tris:
            continue
        data.append(dict(col=cname, obj=o, vs=vs, tris=tris, bb=_aabb(vs),
                         bvh=None))
    bad = []
    n = len(data)
    for i in range(n):
        a = data[i]
        for j in range(i + 1, n):
            b = data[j]
            if a["col"] in TOUCHING and b["col"] in TOUCHING:
                continue
            if _penetration(a["obj"].name, b["obj"].name):
                continue
            ax0, ax1, ay0, ay1, az0, az1 = a["bb"]
            bx0, bx1, by0, by1, bz0, bz1 = b["bb"]
            if (ax0 > bx1 - depth or bx0 > ax1 - depth
                    or ay0 > by1 - depth or by0 > ay1 - depth
                    or az0 > bz1 - depth or bz0 > az1 - depth):
                continue
            if a["bvh"] is None:
                a["bvh"] = BVHTree.FromPolygons(a["vs"], a["tris"], all_triangles=True)
            if b["bvh"] is None:
                b["bvh"] = BVHTree.FromPolygons(b["vs"], b["tris"], all_triangles=True)
            if not a["bvh"].overlap(b["bvh"]):
                continue
            span = max(ax1 - ax0, ay1 - ay0, az1 - az0,
                       bx1 - bx0, by1 - by0, bz1 - bz0) * 2 + 1.0
            # Объект, габарит которого вмещает другой, — оболочка (корпус,
            # надстройка, палуба). Находиться внутри неё нормально, поэтому
            # в эту сторону глубину не меряем.
            dirs = []
            if not _contains(b["bb"], a["bb"]) and not _encl(b):
                dirs.append((a, b))
            if not _contains(a["bb"], b["bb"]) and not _encl(a):
                dirs.append((b, a))
            if not dirs:
                continue
            dmax, dpt = 0.0, None
            for src, dst in dirs:
                for p in src["vs"]:
                    if not _inside(dst["bvh"], p, span):
                        continue
                    nr = dst["bvh"].find_nearest(p)
                    if nr[0] is None:
                        continue
                    d = (nr[0] - p).length
                    if d > dmax:
                        dmax, dpt = d, (round(p.x, 2), round(p.y, 2), round(p.z, 2))
                if dmax > depth:
                    break
            if dmax > depth:
                bad.append((a["obj"].name, b["obj"].name, round(dmax, 4), dpt))
                if verbose:
                    print("  %-34s x %-34s %.0f мм %s"
                          % (a["obj"].name, b["obj"].name, dmax * 1000, dpt))
    bad.sort(key=lambda t: -t[2])
    if verbose:
        print("объектов %d, пар с проникновением > %.0f мм: %d"
              % (n, depth * 1000, len(bad)))
    return bad


def outside_hull(tol=OUT_TOL, verbose=True):
    """Объекты, вылезающие за обшивку корпуса.

    Ниже высоты борта предел — полуширота обвода на своей высоте; выше
    (фальшборт, леера, шлюпбалки, надстройка) — полуширота по палубе:
    наружу за линию борта не должно выходить ничего.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    bad = []
    for cname, o in _mesh_objs():
        if cname in NO_HULL:
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        worst, wp = 0.0, None
        for v in me.vertices:
            p = mw @ v.co
            if p.x < -0.5 or p.x > G.LOA + 0.5:
                continue
            zb = H.side_height(p.x)
            zk = H.keel_height(p.x)
            if p.z < zk - 0.02:
                lim = APPEND_HALF      # выступающие части: винты, насадки, рули
            else:
                lim = H.half_breadth(p.x, min(max(p.z, zk), zb))
            d = abs(p.y) - lim
            if d > worst:
                worst, wp = d, (round(p.x, 2), round(p.y, 2), round(p.z, 2))
        ev.to_mesh_clear()
        if worst > tol:
            bad.append((o.name, cname, round(worst, 3), wp))
            if verbose:
                print("  %-40s %-20s +%.0f мм %s" % (o.name, cname, worst * 1000, wp))
    bad.sort(key=lambda t: -t[2])
    if verbose:
        print("за обводом корпуса: %d" % len(bad))
    return bad


def outside_super(tol=0.03, verbose=True):
    """Насыщение, вылезающее за борт надстройки (выше главной палубы)."""
    dg = bpy.context.evaluated_depsgraph_get()
    bad = []
    for cname, o in _mesh_objs(INSIDE_SUPER):
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        worst, wp = 0.0, None
        for v in me.vertices:
            p = mw @ v.co
            if p.z < Z_SUPER or p.x < -0.5 or p.x > G.LOA + 0.5:
                continue
            lim = H.super_half_breadth(p.x)
            d = abs(p.y) - lim
            if d > worst:
                worst, wp = d, (round(p.x, 2), round(p.y, 2), round(p.z, 2))
        ev.to_mesh_clear()
        if worst > tol:
            bad.append((o.name, cname, round(worst, 3), wp))
            if verbose:
                print("  %-40s %-20s +%.0f мм %s" % (o.name, cname, worst * 1000, wp))
    bad.sort(key=lambda t: -t[2])
    if verbose:
        print("за бортом надстройки: %d" % len(bad))
    return bad


def audit(depth=DEPTH, tol=OUT_TOL, verbose=True):
    if verbose:
        print("--- пересечения ---")
    ov = pairs(depth, verbose=verbose)
    if verbose:
        print("--- обвод ---")
    out = outside_hull(tol, verbose=verbose)
    if verbose:
        print("--- борт надстройки ---")
    sup = outside_super(verbose=verbose)
    return {"пересечения": ov, "за_обводом": out, "за_надстройкой": sup,
            "чисто": not ov and not out and not sup}
