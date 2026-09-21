# -*- coding: utf-8 -*-
"""Закрытие дыр в ограждении надстройки.

    import blender_ограждение as E
    E.close_all()

Надстройка собрана протяжкой: цоколь, подоконник, полоса простенков,
перемычка, карниз. Остекление главной палубы обрывается на 128,05 м, а
полоса окон идёт до 130,40 м — в носовом салоне между простенками остаются
сквозные дыры, и с палубы виден горизонт. Кормовые переборки надстройки
перекрывают только 5,8 м из тринадцати, и так же открыт корм ресторана.

Скрипт не правит протяжку, а закрывает найденные дыры: пускает лучи из
диаметрали в борта и в оконечности на высоте окна, собирает промежутки, где
луч уходит за габарит, и ставит по обводу цоколя полосы остекления и торцевые
щиты.
"""

import bpy, bmesh, sys

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)

from mathutils import Vector
from mathutils.bvhtree import BVHTree
from lib import gorizont as G

DECKS = ("главная", "верхняя")
GLASS = "гор_остекление"
WALL = "гор_надстройка"
T = 0.06                 # толщина полосы, м
COLL = "02_Надстройка"


def _log(*a):
    print(" ".join(str(x) for x in a))


def _obj(name):
    return bpy.data.objects.get(name)


def _bvh(names):
    dg = bpy.context.evaluated_depsgraph_get()
    vs, ts = [], []
    for n in names:
        o = _obj(n)
        if o is None or o.type != "MESH":
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        base = len(vs)
        vs += [mw @ v.co for v in me.vertices]
        for p in me.polygons:
            vi = list(p.vertices)
            for k in range(1, len(vi) - 1):
                ts.append((base + vi[0], base + vi[k], base + vi[k + 1]))
        ev.to_mesh_clear()
    return BVHTree.FromPolygons(vs, ts, all_triangles=True)


def _deck_parts(deck):
    """Детали надстройки этой палубы и отметки оконной полосы."""
    base = _obj("надстройка_цоколь_%s" % deck)
    sill = _obj("надстройка_подоконник_%s" % deck)
    lint = _obj("надстройка_перемычка_%s" % deck)
    if not (base and sill and lint):
        return None
    zb = max((sill.matrix_world @ v.co).z for v in sill.data.vertices)
    zt = min((lint.matrix_world @ v.co).z for v in lint.data.vertices)
    xs = [(base.matrix_world @ v.co).x for v in base.data.vertices]
    return min(xs), max(xs), zb, zt


def outline(deck, step=0.06):
    """Полуширина цоколя по длине надстройки."""
    x0, x1, zb, zt = _deck_parts(deck)
    bvh = _bvh(["надстройка_цоколь_%s" % deck])
    z = (G.DECKS[deck] + 0.30)
    n = int((x1 - x0) / step) + 1
    out = []
    for k in range(n):
        x = x0 + k * step
        w = None
        for d in (Vector((0, 1, 0)), Vector((0, -1, 0))):
            hit = bvh.ray_cast(Vector((x, 0.0, z)), d, G.BEAM)
            if hit[0] is not None:
                w = hit[3] if w is None else min(w, hit[3])
        out.append((x, w if w else 0.0))
    return out, zb, zt


def _skin_names(deck):
    """Всё, что может закрывать оконную полосу этой палубы."""
    out = []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.visible_get():
            continue
        n = o.name
        if n.startswith(("надстройка_", "остекление_", "переборка_надстройки",
                         "ограждение_", "рубка", "шахта_", "лифт_", "трап_")) \
                and (deck in n or n.startswith(("рубка", "шахта_", "лифт_",
                                                "трап_"))):
            out.append(n)
    return out


def _runs(flags, xs, gap=1):
    """Непрерывные участки True с их шпациями."""
    runs, cur = [], None
    for i, f in enumerate(flags):
        if f and cur is None:
            cur = i
        elif not f and cur is not None:
            runs.append((cur, i - 1))
            cur = None
    if cur is not None:
        runs.append((cur, len(flags) - 1))
    return [(xs[a], xs[b]) for a, b in runs]


def _strip(name, pts, z0, z1, mat, side, t=T):
    """Полоса по обводу: пара рядов вершин, соединённых четырёхугольниками."""
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    rows = []
    for x, w in pts:
        y = side * w
        rows.append([bm.verts.new((x, y, z0)), bm.verts.new((x, y, z1)),
                     bm.verts.new((x, y - side * t, z1)),
                     bm.verts.new((x, y - side * t, z0))])
    for i in range(len(rows) - 1):
        a, b = rows[i], rows[i + 1]
        for k in range(4):
            bm.faces.new((a[k], a[(k + 1) % 4], b[(k + 1) % 4], b[k]))
    bm.faces.new(rows[0][::-1])
    bm.faces.new(rows[-1])
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    me.materials.append(bpy.data.materials.get(mat))
    obj = bpy.data.objects.new(name, me)
    (bpy.data.collections.get(COLL)
     or bpy.context.scene.collection).objects.link(obj)
    return obj


def _panel(name, x, y0, y1, z0, z1, mat, t=T):
    me = bpy.data.meshes.new(name)
    bm = bmesh.new()
    res = bmesh.ops.create_cube(bm, size=1.0)
    for v in res["verts"]:
        v.co.x = x - t / 2 + (v.co.x + 0.5) * t
        v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
        v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
    bm.to_mesh(me)
    bm.free()
    me.materials.append(bpy.data.materials.get(mat))
    obj = bpy.data.objects.new(name, me)
    (bpy.data.collections.get(COLL)
     or bpy.context.scene.collection).objects.link(obj)
    return obj


def close_deck(deck, verbose=True):
    pts, zb, zt = outline(deck)
    zc = (zb + zt) / 2
    bvh = _bvh(_skin_names(deck))
    made = []
    # --- борта: где луч из диаметрали уходит за габарит
    for side, tag in ((1, "л"), (-1, "п")):
        flags = []
        for x, w in pts:
            if w < 0.12:
                flags.append(False)
                continue
            # короткий луч изнутри самого борта: длинный из диаметрали
            # упирается в мебель и шахты и врёт
            hit = bvh.ray_cast(Vector((x, side * max(0.0, w - 0.40), zc)),
                               Vector((0, side, 0)), 0.80)
            flags.append(hit[0] is None)
        xs = [p[0] for p in pts]
        for a, b in _runs(flags, xs):
            seg = [p for p in pts if a - 1e-6 <= p[0] <= b + 1e-6]
            if len(seg) < 2 or seg[-1][0] - seg[0][0] < 0.04:
                continue
            nm = "ограждение_%s_борт_%s_%.0f" % (deck, tag, seg[0][0] * 100)
            if _obj(nm):
                bpy.data.objects.remove(_obj(nm), do_unlink=True)
            made.append(_strip(nm, seg, zb, zt, GLASS, side))
            if verbose:
                _log("  борт %s: %.2f..%.2f м" % (tag, seg[0][0], seg[-1][0]))
    # --- оконечности: закрыта ли торцевая плоскость оконной полосы
    # Торец ищется по самим торцевым переборкам: дымовые шахты стоят близко
    # к корме и перекрывают длинный луч, хотя стены там нет.
    x0, x1 = pts[0][0], pts[-1][0]
    ends = _bvh([o.name for o in bpy.data.objects
                 if o.type == "MESH"
                 and (o.name.startswith("переборка_надстройки")
                      or o.name.startswith("ограждение_")
                      or o.name.startswith("рубка"))])
    for end, sx, tag in ((x0, -1, "корма"), (x1, 1, "нос")):
        wmax = max(w for _, w in pts)
        ys, flags = [], []
        k = int(wmax / 0.15)
        for i in range(-k, k + 1):
            y = i * 0.15
            ys.append(y)
            px = end - sx * 0.30
            w = _w_at(pts, px)
            if abs(y) > w - 0.12:
                flags.append(False)
                continue
            hit = ends.ray_cast(Vector((px, y, zc)), Vector((sx, 0, 0)),
                                1.60)
            flags.append(hit[0] is None)
        for a, b in _runs(flags, ys):
            if b - a < 0.2:
                continue
            nm = "ограждение_%s_%s_%.0f" % (deck, tag, (a + 10) * 10)
            if _obj(nm):
                bpy.data.objects.remove(_obj(nm), do_unlink=True)
            xe = end - sx * 0.05
            made.append(_panel(nm, xe, a - 0.075, b + 0.075, zb, zt, WALL))
            if verbose:
                _log("  %s: y %.2f..%.2f м" % (tag, a, b))
    # --- глухие торцы по краям обвода: их ставим всегда, а не по лучу.
    # Сквозные щели в оконечностях узкие, и луч с шагом 5° их то находит,
    # то нет; закрыть торец целиком надёжнее, чем ловить каждую щель.
    for end, sx, tag, mat in ((x0, -1, "торец_корма", WALL),
                              (x1, 1, "торец_нос", GLASS)):
        w = _w_at(pts, end - sx * 0.10)
        if w < 0.10:
            continue
        nm = "ограждение_%s_%s" % (deck, tag)
        if _obj(nm):
            bpy.data.objects.remove(_obj(nm), do_unlink=True)
        made.append(_panel(nm, end - sx * 0.05, -w, w, zb, zt, mat))
    band = _obj("надстройка_простенки_%s" % deck)
    bx = [(band.matrix_world @ v.co).x for v in band.data.vertices]
    for end, sx, tag in ((min(bx), -1, "полоса_корма"),
                         (max(bx), 1, "полоса_нос")):
        w = _w_at(pts, end + sx * 0.10)
        if w < 0.10:
            continue
        nm = "ограждение_%s_%s" % (deck, tag)
        if _obj(nm):
            bpy.data.objects.remove(_obj(nm), do_unlink=True)
        made.append(_panel(nm, end + sx * 0.03, -w, w, zb, zt, GLASS))
    return made


def _w_at(pts, x):
    best = None
    for px, w in pts:
        if best is None or abs(px - x) < abs(best[0] - x):
            best = (px, w)
    return best[1]


def close_all(verbose=True):
    made = []
    for d in DECKS:
        if verbose:
            _log("—", d)
        made += close_deck(d, verbose)
    if verbose:
        _log("поставлено полос и щитов:", len(made))
    return [o.name for o in made]
