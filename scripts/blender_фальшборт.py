# -*- coding: utf-8 -*-
r"""Плоская главная палуба и фальшборт по всей длине.

Обводы задают высоту борта с подъёмом к носу (4,20 м на миделе -> 4,90 м
на форштевне).  Раньше этот подъём был крышкой корпуса, то есть палубой:
каюты и выгородки в носу на отметке 4,20 оказывались утопленными в настил.
Правильное деление такое:

* главная палуба — плоская, на высоте борта D = 4,20 м по всей длине;
* подъём борта выше 4,20 м — фальшборт, стенка толщиной 60 мм, верхняя
  кромка на 4,90 м (0,70 м над палубой), на ней стоит леер 4,90...5,37 м,
  итого ограждение 1,17 м при нормативе 1,10 м.

Скрипт режет корпус плоскостью z = D, закрывает срез, строит фальшборт и
заново кладёт леер главной палубы по кромке фальшборта.

    exec(open(r"E:\Ship_docx\scripts\blender_фальшборт.py", encoding="utf-8").read())
    rebuild_bulwark()
"""
import bpy, bmesh, sys

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont as G, gorizont_hydro as H

Z_DECK = G.DEPTH           # 4,20 — плоская главная палуба
Z_BULW = 4.90              # верхняя кромка фальшборта
T_BULW = 0.06              # толщина листа фальшборта
X0_B, X1_B = 0.30, 138.40  # протяжённость фальшборта
RAIL_Z1 = 5.37


def _mat(name):
    return bpy.data.materials.get(name)


def _link(o, col_name):
    col = bpy.data.collections.get(col_name) or bpy.context.scene.collection
    col.objects.link(o)


def flatten_deck(obj_name="корпус"):
    """Срезать корпус плоскостью главной палубы и закрыть срез."""
    o = bpy.data.objects[obj_name]
    bm = bmesh.new()
    bm.from_mesh(o.data)
    n0, f0 = len(bm.verts), len(bm.faces)
    geom = list(bm.verts) + list(bm.edges) + list(bm.faces)
    bmesh.ops.bisect_plane(bm, geom=geom, dist=1e-5,
                           plane_co=(0.0, 0.0, Z_DECK),
                           plane_no=(0.0, 0.0, 1.0),
                           clear_outer=True, clear_inner=False)
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bm.edges.ensure_lookup_table()
    holes = [e for e in bm.edges if len(e.link_faces) == 1]
    if holes:
        bmesh.ops.holes_fill(bm, edges=holes, sides=0)
    bm.edges.ensure_lookup_table()
    left = [e for e in bm.edges if len(e.link_faces) != 2]
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    rep = dict(было_верш=n0, было_гран=f0,
               стало_верш=len(bm.verts), стало_гран=len(bm.faces),
               дыр_закрыто=len(holes), открытых_рёбер=len(left),
               z_max=round(max(v.co.z for v in bm.verts), 3))
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    return rep


def _xs(step=0.5):
    xs, x = [], X0_B
    while x < X1_B:
        xs.append(round(x, 3))
        x += step if 12.0 < x < 110.0 else step / 2.5
    xs.append(X1_B)
    return xs


def _edge(x, z):
    """Полуширота кромки палубы (фальшборта) на шпангоуте x и высоте z."""
    return H.half_breadth(x, min(z, H.side_height(x)))


def _box(bm, x0, x1, y0, y1, z0, z1):
    v = [bm.verts.new(p) for p in
         ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
          (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
              (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([v[k] for k in f])


def build_bulwark(name="фальшборт", mat="гор_корпус_борт"):
    """Стенка фальшборта от палубы до 4,90 м с обоих бортов."""
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    xs = _xs()
    zs = [Z_DECK, Z_DECK + (Z_BULW - Z_DECK) * 0.5, Z_BULW]
    nz = len(zs)
    bm = bmesh.new()
    for s in (1, -1):
        go, gi = [], []
        for x in xs:
            co, ci = [], []
            for z in zs:
                y = _edge(x, z)
                co.append(bm.verts.new((x, s * y, z)))
                ci.append(bm.verts.new((x, s * max(y - T_BULW, 0.0), z)))
            go.append(co)
            gi.append(ci)
        for i in range(len(xs) - 1):
            for k in range(nz - 1):
                q = (go[i][k], go[i + 1][k], go[i + 1][k + 1], go[i][k + 1])
                bm.faces.new(q if s > 0 else tuple(reversed(q)))
                q = (gi[i][k], gi[i + 1][k], gi[i + 1][k + 1], gi[i][k + 1])
                bm.faces.new(tuple(reversed(q)) if s > 0 else q)
            t = nz - 1
            q = (go[i][t], gi[i][t], gi[i + 1][t], go[i + 1][t])
            bm.faces.new(q if s > 0 else tuple(reversed(q)))
            q = (gi[i][0], go[i][0], go[i + 1][0], gi[i + 1][0])
            bm.faces.new(q if s > 0 else tuple(reversed(q)))
        for i in (0, len(xs) - 1):
            for k in range(nz - 1):
                bm.faces.new((go[i][k], gi[i][k], gi[i][k + 1], go[i][k + 1]))
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    m = _mat(mat)
    if m:
        o.data.materials.append(m)
    _link(o, "01_Корпус")
    return o


def rebuild_rail(mat="гор_металл"):
    """Леер главной палубы по кромке фальшборта."""
    for n in ("леер_главной_п", "леер_главной_л", "леер_главной_транец"):
        old = bpy.data.objects.get(n)
        if old:
            bpy.data.objects.remove(old, do_unlink=True)
    xs = _xs(0.6)
    bars = [(RAIL_Z1 - 0.035, RAIL_Z1), (5.10, 5.13)]
    made = []
    for s, nm in ((1, "леер_главной_п"), (-1, "леер_главной_л")):
        bm = bmesh.new()
        ys = [max(_edge(x, Z_BULW) - T_BULW / 2, 0.03) for x in xs]
        for z0, z1 in bars:
            for i in range(len(xs) - 1):
                x0, x1 = xs[i], xs[i + 1]
                y0, y1 = ys[i], ys[i + 1]
                v = [bm.verts.new(p) for p in
                     ((x0, s * (y0 - 0.018), z0), (x1, s * (y1 - 0.018), z0),
                      (x1, s * (y1 + 0.018), z0), (x0, s * (y0 + 0.018), z0),
                      (x0, s * (y0 - 0.018), z1), (x1, s * (y1 - 0.018), z1),
                      (x1, s * (y1 + 0.018), z1), (x0, s * (y0 + 0.018), z1))]
                for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                          (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
                    bm.faces.new([v[k] for k in f])
        for i in range(0, len(xs), 3):
            x, y = xs[i], ys[i]
            _box(bm, x - 0.024, x + 0.024,
                 s * y - 0.024, s * y + 0.024, Z_BULW, RAIL_Z1)
        bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
        me = bpy.data.meshes.new(nm)
        bm.to_mesh(me)
        bm.free()
        o = bpy.data.objects.new(nm, me)
        m = _mat(mat)
        if m:
            o.data.materials.append(m)
        _link(o, "07_Леера_и_оборудование")
        made.append(nm)
    return made


def rebuild_bulwark(verbose=True):
    rep = {"палуба": flatten_deck()}
    o = build_bulwark()
    rep["фальшборт"] = {"верш": len(o.data.vertices), "гран": len(o.data.polygons)}
    rep["леер"] = rebuild_rail()
    if verbose:
        print(rep)
    return rep
