# -*- coding: utf-8 -*-
r"""Каюты в Blender: сборка эталонов и расстановка на судне.

Вся геометрия и эргономика — в src/lib/gorizont_cabins.py; здесь только
превращение списка объёмов в сетки и размещение кают по палубам.

    exec(open(r"E:\Ship_docx\scriptslender_каюты.py", encoding="utf-8").read())
    rebuild_prototypes()
"""
import bpy, bmesh, math, mathutils, sys

M = mathutils.Matrix

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib.gorizont_cabins import (
    Part, P, check, check_fit, layout, layout_info, check_access, TYPES,
    T_WALL, H_ROOM, EPS, PASS, PASS_ACC)
from lib import gorizont_cabins as C


def _box(bm, b):
    x0, x1, y0, y1, z0, z1 = b
    bmesh.ops.create_cube(bm, size=1.0,
        matrix=M.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        @ M.Diagonal((max(x1 - x0, 1e-4), max(y1 - y0, 1e-4), max(z1 - z0, 1e-4), 1.0)))


def _cyl(bm, b, seg=16, axis="Z"):
    x0, x1, y0, y1, z0, z1 = b
    cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    if axis == "Z":
        r = min(x1 - x0, y1 - y0) / 2
        rot = M.Identity(4); d = z1 - z0
    elif axis == "X":
        r = min(y1 - y0, z1 - z0) / 2
        rot = M.Rotation(math.radians(90), 4, 'Y'); d = x1 - x0
    else:
        r = min(x1 - x0, z1 - z0) / 2
        rot = M.Rotation(math.radians(90), 4, 'X'); d = y1 - y0
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r, depth=d,
                          matrix=M.Translation((cx, cy, cz)) @ rot)


def build(name, parts, collection="20_Эталоны_кают", origin=(0, 0, 0)):
    """Собрать каюту в один объект с материалами по частям."""
    mats = []
    idx = {}
    for p in parts:
        if p.mat not in idx:
            idx[p.mat] = len(mats)
            mats.append(p.mat)
    bm = bmesh.new()
    faces_from = []
    for p in parts:
        n0 = len(bm.faces)
        if p.kind == "cyl":
            _cyl(bm, p.box, p.meta.get("seg", 16), p.meta.get("axis", "Z"))
        else:
            _box(bm, p.box)
        bm.faces.ensure_lookup_table()
        faces_from.append((n0, len(bm.faces), idx[p.mat]))
    bm.faces.ensure_lookup_table()
    for (a, b, mi) in faces_from:
        for k in range(a, b):
            bm.faces[k].material_index = mi
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    o = bpy.data.objects.new(name, me)
    col = bpy.data.collections.get(collection)
    if col is None:
        col = bpy.data.collections.new(collection)
        bpy.context.scene.collection.children.link(col)
    col.objects.link(o)
    for mn in mats:
        o.data.materials.append(bpy.data.materials.get(mn)
                                or bpy.data.materials.new(mn))
    o.location = origin
    return o


# ------------------------------------------------------------- наполнение --
def rebuild_prototypes(verbose=True):
    """Собрать эталоны, проверив каждый на пересечения и на проходимость."""
    report = {}
    col = bpy.data.collections.get("20_Эталоны_кают")
    if col:
        for o in list(col.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    gx, gy = -60.0, -30.0
    for i, (name, W, D, kind, win, acc, bal) in enumerate(TYPES):
        parts = layout(W, D, kind, win, acc, bal)
        bad = check(parts)
        dxy = None
        for q in parts:
            if q.name == "дверь":
                dxy = (q.box[0] - 0.01, q.box[1] - q.box[0] + 0.02)
        acc_bad = check_access(parts, W, D, kind, acc, door=dxy)
        info = layout_info(W, D, kind, acc)
        report[name] = dict(parts=len(parts), overlaps=bad, W=W, D=D,
                            access=acc_bad, plan=info)
        if bad or acc_bad:
            continue
        ox = gx + (i % 4) * 11.0
        oy = gy + (i // 4) * 7.0
        build(name, parts, origin=(ox, oy, 0.0))
    if verbose:
        for k, v in report.items():
            pl = v["plan"] or {}
            print("%-24s частей %3d  план %s  %s  койка %s  проход %.2f  %s"
                  % (k, v["parts"], pl.get("plan", "-"),
                     pl.get("санузел", "-"), pl.get("койка", "-"),
                     pl.get("проход", 0.0),
                     "ок" if not v["overlaps"] and not v["access"]
                     else str(v["overlaps"][:2]) + str(v["access"][:2])))
    return report


# ------------------------------------------------- расстановка на судне ----
def _wall_limit(walls, deck, side, x0, x1):
    """Наружная грань продольной выгородки на участке [x0, x1] или None."""
    if not walls:
        return None
    best = None
    for (d, s_, wx0, wx1, ymax) in walls:
        if d != deck or s_ != side:
            continue
        if wx1 <= x0 + 0.01 or wx0 >= x1 - 0.01:
            continue
        best = ymax if best is None else max(best, ymax)
    return best



def place_all(rows, walls=None, margin=0.30, verbose=True):
    """Пересобрать все каюты судна по их габаритам из rows.

    rows — список словарей: name, deck, side, kind, dost, x0, x1, D, y_out, z.
    walls — продольные выгородки служебного блока: (палуба, борт, x0, x1, |y|).
    Каюта у борта отодвигается внутрь под новый обвод, а её внутренняя
    переборка садится точно на стенку выгородки: коридор не сужается и
    каюта ни во что не влезает.
    """
    import sys as _s
    if ROOT_SRC not in _s.path:
        _s.path.insert(0, ROOT_SRC)
    from lib import gorizont_hydro as H
    LEV = {"первая": 1.40, "главная": 4.20, "верхняя": 7.00, "шлюпочная": 9.80}
    col = bpy.data.collections.get("10_Каюты")
    if col is None:
        col = bpy.data.collections.new("10_Каюты")
        bpy.context.scene.collection.children.link(col)
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    cache = {}
    made, moved, bad = [], 0, []
    for r in rows:
        W = round(r["x1"] - r["x0"], 3)
        D = round(r["D"], 3)
        kind = r["kind"]
        base = kind if kind in ("эконом", "стандарт", "бизнес", "люкс") else "экипаж"
        lev = LEV.get(r["deck"], r["z"])
        n = 8
        if lev < 4.1:
            lim = min(H.half_breadth(r["x0"] + (r["x1"] - r["x0"]) * i / n, lev + 0.06)
                      for i in range(n + 1))
        else:
            lim = min(H.super_half_breadth(r["x0"] + (r["x1"] - r["x0"]) * i / n)
                      for i in range(n + 1))
        outboard = (lim - abs(r["y_out"])) < 0.45
        if outboard:
            y_out = lim - margin
            if abs(abs(r["y_out"]) - y_out) > 0.005:
                moved += 1
        else:
            y_out = abs(r["y_out"])
        yw = _wall_limit(walls, r["deck"], r["side"], r["x0"], r["x1"])
        if yw is not None:
            D = round(max(y_out - yw, 2.20), 3)
        window = outboard or base == "люкс"
        key = (W, D, base, window, bool(r["dost"]))
        if key not in cache:
            parts = layout(W, D, base, window, bool(r["dost"]))
            ov = check(parts)
            dxy = None
            for q in parts:
                if q.name == "дверь":
                    dxy = (q.box[0] - 0.01, q.box[1] - q.box[0] + 0.02)
            acc = check_access(parts, W, D, base, bool(r["dost"]), door=dxy)
            if ov or acc:
                bad.append((r["name"], ov[:3], acc[:3]))
                continue
            tmp = build("_tmp_%d" % len(cache), parts, collection="10_Каюты")
            cache[key] = tmp.data
            bpy.data.objects.remove(tmp, do_unlink=True)
        me = cache[key]
        o = bpy.data.objects.new(r["name"], me)
        col.objects.link(o)
        if r["side"] == "п":
            o.location = (r["x1"], y_out, lev)
            o.rotation_euler = (0.0, 0.0, math.pi)
        else:
            o.location = (r["x0"], -y_out, lev)
            o.rotation_euler = (0.0, 0.0, 0.0)
        made.append(o.name)
    if verbose:
        print("кают %d, сеток %d, сдвинуто внутрь %d, с пересечениями %d"
              % (len(made), len(cache), moved, len(bad)))
    return dict(made=made, meshes=len(cache), moved=moved, bad=bad)
