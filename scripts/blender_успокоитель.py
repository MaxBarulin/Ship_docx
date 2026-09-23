# -*- coding: utf-8 -*-
r"""Успокоительные цистерны в модели.

    import blender_успокоитель as U
    U.build()

Две пассивные цистерны U-образного типа - бортовые ветви в отсеках второго
дна и перепускной канал между ними. Геометрия берётся из `gorizont_roll`,
то есть из того же места, где считается настройка на период качки.

Строятся ограждающие связи - продольные и поперечные переборки ветвей и
стенки канала, как и у остальных цистерн второго дна - залитый объём в
модели не показывают.
"""

import bpy, bmesh, sys

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)

from lib import gorizont_roll as R
from lib import gorizont_hydro as H

COLL = "40_Набор_корпуса"
MAT = "гор_набор_переборка"
T = 0.008                       # толщина переборки, м
TOP = 0.90                      # верх ветви: уровень 0,45 плюс запас


def _coll():
    c = bpy.data.collections.get(COLL)
    return c or bpy.context.scene.collection


def _box(bm, x0, x1, y0, y1, z0, z1):
    res = bmesh.ops.create_cube(bm, size=1.0)
    for v in res["verts"]:
        v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
        v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
        v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)


def build(verbose=True):
    g = R.report()["geometry"]
    yi = g["branch_y"] - g["branch_b"] / 2.0      # внутренняя стенка ветви
    yo = g["branch_y"] + g["branch_b"] / 2.0      # наружная стенка ветви
    made = []
    for t in R.TANKS:
        x0, x1 = t["x0"], t["x1"]
        xm = 0.5 * (x0 + x1)
        bm = bmesh.new()
        for s in (-1, 1):
            a, b = sorted((s * yi, s * yo))
            # продольные стенки ветви
            _box(bm, x0, x1, a - T, a, 0.0, TOP)
            _box(bm, x0, x1, b, b + T, 0.0, TOP)
            # поперечные торцы ветви
            _box(bm, x0, x0 + T, a, b, 0.0, TOP)
            _box(bm, x1 - T, x1, a, b, 0.0, TOP)
        # перепускной канал между ветвями: стенки и подволок
        w = g["duct_h"]
        cw = g["branch_b"]
        _box(bm, xm - cw / 2.0 - T, xm - cw / 2.0, -yi, yi, 0.0, w)
        _box(bm, xm + cw / 2.0, xm + cw / 2.0 + T, -yi, yi, 0.0, w)
        _box(bm, xm - cw / 2.0, xm + cw / 2.0, -yi, yi, w, w + T)
        me = bpy.data.meshes.new("успокоитель_%s" % t["code"])
        me.materials.append(bpy.data.materials.get(MAT))
        bm.to_mesh(me)
        bm.free()
        name = "успокоитель_%s" % t["code"]
        o = bpy.data.objects.get(name)
        if o is None:
            o = bpy.data.objects.new(name, me)
            _coll().objects.link(o)
        else:
            old = o.data
            o.data = me
            if old.users == 0:
                bpy.data.meshes.remove(old)
        o.matrix_world.identity()
        made.append(o.name)
    if verbose:
        w = R.water()
        print("успокоительные цистерны - %d шт, жидкость %.1f т, "
              "период цистерны %.2f с при качке %.2f с"
              % (len(made), w["mass"], R.tank_period(), H.roll_period()))
        for n in made:
            print("  ", n)
    return made
