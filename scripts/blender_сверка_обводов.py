# -*- coding: utf-8 -*-
r"""Сверка построенного корпуса с плазовой таблицей ординат.

Для каждого теоретического шпангоута и каждой ватерлинии таблицы луч
пускается снаружи внутрь и находится фактическая полуширота обшивки.
Она сравнивается с ординатой таблицы: модель и теоретический чертёж
обязаны совпадать, иначе расчёты и чертежи разойдутся.

    exec(open(r"E:\Ship_docx\scripts\blender_сверка_обводов.py", encoding="utf-8").read())
    compare()
"""
import bpy, sys
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont as G, gorizont_hydro as H


def _bvh(name="корпус"):
    o = bpy.data.objects[name]
    mw = o.matrix_world
    vs = [mw @ v.co for v in o.data.vertices]
    tris = []
    for p in o.data.polygons:
        vi = list(p.vertices)
        for k in range(1, len(vi) - 1):
            tris.append((vi[0], vi[k], vi[k + 1]))
    return BVHTree.FromPolygons(vs, tris, all_triangles=True)


def mesh_half(bvh, x, z, ymax=12.0):
    """Фактическая полуширота обшивки на (x, z) по лучу снаружи внутрь."""
    hit = bvh.ray_cast(Vector((x, ymax, z)), Vector((0, -1, 0)), 2 * ymax)
    if hit[0] is None:
        return None
    return round(hit[0].y, 4)


def compare(tol=0.03, verbose=True):
    bvh = _bvh()
    rows, bad = [], []
    for st in G.OFFSETS:
        num, x, zk, bk, zb, bb, ys = st
        for k, zw in enumerate(G.WATERLINES):
            tab = ys[k]
            if tab is None:
                continue
            # у самой кромки палубы луч скользит по ребру — отступаем на 5 мм
            zq = min(zw, G.DEPTH - 0.005)
            act = mesh_half(bvh, min(max(x, 0.05), G.LOA - 0.05), zq)
            if act is None:
                if tab > tol:
                    bad.append((num, zw, tab, None, round(tab, 3)))
                continue
            d = act - tab
            rows.append((num, zw, tab, act, round(d, 4)))
            if abs(d) > tol:
                bad.append((num, zw, round(tab, 3), round(act, 3), round(d, 3)))
    if verbose:
        print("точек сверено %d, расхождений > %.0f мм: %d" % (len(rows), tol * 1000, len(bad)))
        for r in bad[:40]:
            print("  шп %-5s ВЛ %-5s таблица %-7s модель %-7s  Δ %+.3f"
                  % (r[0], r[1], r[2], r[3], r[4]))
    worst = max((abs(r[4]) for r in rows), default=0.0)
    return {"точек": len(rows), "расхождений": len(bad),
            "макс_откл_мм": round(worst * 1000, 1), "список": bad}
