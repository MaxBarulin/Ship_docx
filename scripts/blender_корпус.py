# -*- coding: utf-8 -*-
r"""Корпус по плазовой таблице: обшивка, плоская главная палуба, туннели.

Сечение берётся прямо из gorizont_hydro.section_y, то есть из той же
геометрии, по которой напечатана плазовая таблица и построен
теоретический чертёж. Поэтому модель и чертёж совпадают по построению,
а не «примерно».

Что строится:
  * замкнутая оболочка от килевой линии до главной палубы D = 4,20 м
    (подъём борта выше палубы — это фальшборт, он в blender_фальшборт.py);
  * плоская палуба-крышка на 4,20 м;
  * транец на кормовом перпендикуляре и сход обвода на форштевне;
  * два туннеля гребных винтов — конические выемки в днище, без них
    винт диаметром 1,70 м не уместится под кормовым подзором.

    exec(open(r"E:\Ship_docx\scripts\blender_корпус.py", encoding="utf-8").read())
    rebuild_hull()
"""
import bpy, bmesh, math, sys

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont as G, gorizont_hydro as H

Z_DECK = G.DEPTH
NB, NARC, NSIDE, ND = 4, 24, 10, 4   # точек: днище, скула, борт, палуба
TUNNEL_R = G.NOZZLE_OUTER + 0.08
TUNNEL_X1 = 16.0               # длина схода туннеля в нос
MAT = ("гор_корпус_подводный", "гор_корпус_ватерлиния",
       "гор_корпус_борт", "гор_палуба_тик")


def hull_xs(step_end=0.4, step_mid=1.0):
    """Сетка сечений: гуще в оконечностях, обязательно через шпангоуты."""
    xs, x = [], 0.0
    while x <= G.LOA + 1e-9:
        xs.append(round(x, 3))
        x += step_end if (x < 24.0 or x > 106.0) else step_mid
    xs += [round(r[1], 3) for r in G.OFFSETS]
    xs += [round(TUNNEL_X1, 3)]
    return sorted(set(v for v in xs if 0.0 <= v <= G.LOA))


def half_section(x):
    """Полусечение от ДП по днищу и борту до ДП по палубе: [(y, z), ...].

    Днище, скуловая дуга по углу (а не по высоте — иначе в крутой части
    дуги точек не хватает и модель отходит от таблицы) и прямой борт.
    """
    zk, bk, zb, bb, phi = H._column(x)
    zk = min(zk, Z_DECK - 0.02)
    r = H.bilge_radius(bk, bb, zk, zb, phi)
    pts = [(0.0, zk)]
    for k in range(1, NB + 1):
        pts.append((bk * k / NB, zk))
    z_t = zk + r * (1.0 - math.sin(phi)) if r > 1e-6 else zk
    a_max = math.pi / 2 - phi
    for k in range(1, NARC + 1):
        z = min(zk + r * (1.0 - math.cos(a_max * k / NARC)), Z_DECK)             if r > 1e-6 else zk
        pts.append((H.section_y(z, zk, bk, zb, bb, phi), z))
    for k in range(1, NSIDE + 1):
        z = min(z_t + max(Z_DECK - z_t, 0.0) * k / NSIDE, Z_DECK)
        pts.append((H.section_y(z, zk, bk, zb, bb, phi), z))
    yd = H.section_y(Z_DECK, zk, bk, zb, bb, phi)
    pts[-1] = (yd, Z_DECK)
    for k in range(1, ND):
        pts.append((yd * (1.0 - k / ND), Z_DECK))
    pts.append((0.0, Z_DECK))
    return pts


def ring(x):
    """Замкнутый контур шпангоута: оба борта, по часовой в плоскости yz."""
    h = half_section(x)
    return h + [(-y, z) for (y, z) in reversed(h[1:-1])]


def build_shell(name="корпус"):
    xs = hull_xs()
    bm = bmesh.new()
    rings = []
    for x in xs:
        rings.append([bm.verts.new((x, y, z)) for (y, z) in ring(x)])
    n = len(rings[0])
    for i in range(len(xs) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(n):
            k2 = (k + 1) % n
            vs = [a[k], b[k], b[k2], a[k2]]
            if len(set(vs)) < 3:
                continue
            try:
                bm.faces.new(vs)
            except ValueError:
                pass
    for idx, rev in ((0, True), (len(xs) - 1, False)):
        vs = rings[idx][::-1] if rev else rings[idx]
        try:
            bm.faces.new(vs)
        except ValueError:
            pass
    bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name + "_mesh")
    bm.to_mesh(me)
    bm.free()
    return me


def _tunnel_mesh(sign):
    """Конус выемки туннеля гребного винта."""
    bm = bmesh.new()
    seg = 28
    xs = [-0.6, 0.0, 4.0, 8.0, 12.0, TUNNEL_X1]
    rings = []
    for x in xs:
        t = max(0.0, min(1.0, (x + 0.6) / (TUNNEL_X1 + 0.6)))
        r = TUNNEL_R * (1.0 - t ** 1.7)
        r = max(r, 0.01)
        ring_v = []
        for k in range(seg):
            a = 2 * math.pi * k / seg
            ring_v.append(bm.verts.new((x,
                                        sign * G.PROP_Y + r * math.cos(a),
                                        G.SHAFT_Z_PROP + r * math.sin(a))))
        rings.append(ring_v)
    for i in range(len(xs) - 1):
        for k in range(seg):
            k2 = (k + 1) % seg
            bm.faces.new([rings[i][k], rings[i + 1][k],
                          rings[i + 1][k2], rings[i][k2]])
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[-1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("_tunnel")
    bm.to_mesh(me)
    bm.free()
    return me


def assign_materials(o):
    T = H.equilibrium()["T"]
    for nm in MAT:
        m = bpy.data.materials.get(nm)
        if m and m.name not in [s.name for s in o.data.materials if s]:
            o.data.materials.append(m)
    idx = {m.name: i for i, m in enumerate(o.data.materials) if m}
    for p in o.data.polygons:
        z = p.center.z
        if z > Z_DECK - 0.01 and abs(p.normal.z) > 0.7:
            k = idx.get("гор_палуба_тик", 0)
        elif z < T - 0.15:
            k = idx.get("гор_корпус_подводный", 0)
        elif z < T + 0.25:
            k = idx.get("гор_корпус_ватерлиния", 0)
        else:
            k = idx.get("гор_корпус_борт", 0)
        p.material_index = k


def rebuild_hull(name="корпус", tunnels=True, verbose=True):
    old = bpy.data.objects.get(name)
    col = (old.users_collection[0] if old and old.users_collection
           else bpy.data.collections.get("01_Корпус")
           or bpy.context.scene.collection)
    me = build_shell(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    o = bpy.data.objects.new(name, me)
    col.objects.link(o)
    rep = {"обшивка": [len(me.vertices), len(me.polygons)]}
    if tunnels:
        for s in (1, -1):
            tm = _tunnel_mesh(s)
            to = bpy.data.objects.new("_tunnel", tm)
            col.objects.link(to)
            mod = o.modifiers.new("туннель", "BOOLEAN")
            mod.operation = "DIFFERENCE"
            mod.solver = "EXACT"
            mod.object = to
            bpy.context.view_layer.objects.active = o
            bpy.ops.object.modifier_apply(modifier=mod.name)
            bpy.data.objects.remove(to, do_unlink=True)
        rep["с_туннелями"] = [len(o.data.vertices), len(o.data.polygons)]
    assign_materials(o)
    bm = bmesh.new()
    bm.from_mesh(o.data)
    bm.edges.ensure_lookup_table()
    rep["открытых_рёбер"] = sum(1 for e in bm.edges if len(e.link_faces) != 2)
    bm.free()
    if verbose:
        print(rep)
    return rep
