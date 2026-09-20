# -*- coding: utf-8 -*-
"""Пересборка обстановки общественных помещений.

    import blender_мебель as M
    M.rebuild()                       # все помещения
    M.rebuild(["мебель_театр"])       # выборочно

Помещение не описано координатами переборок: полуширина берётся лучами по
конструкции на высоте 1,20 м над настилом, поэтому раскладка сама
подстраивается под обвод, простенки и шахты. Группа, которая во что-то
упирается, снимается — кроме обязательных, они попадают в отчёт.
"""

import bpy, bmesh, math, sys

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)

from mathutils import Vector
from mathutils.bvhtree import BVHTree
from lib import gorizont as G
from lib import gorizont_furniture as F
from lib import gorizont_rooms as R

DECK_TOP = {"первая": 1.44, "главная": 4.24, "верхняя": 7.04,
            "шлюпочная": 9.84, "солнечная": 12.64}

# что считается конструкцией: по ней меряем ширину и с ней сверяем габариты
STRUCT = ("переборка", "борт", "простенок", "цоколь", "стекло", "окно",
          "шахта", "лифт", "трап", "колонна", "пиллерс", "корпус",
          "надстройка", "рубка", "каюта_", "перегородка", "проём",
          "стойка_", "лобби_", "магазины_", "клуб_", "лаундж_", "холл_",
          "спа_", "камбуз_", "тамбур", "комингс", "выгородка", "остекление",
          "набор_", "шпангоут", "бимс", "стрингер", "флор", "пиллерс",
          "фундамент", "подволок", "ограждение_", "устр_", "мо_", "дрк_")

# Внутренние препятствия: шахты трапов и лифтов, пиллерсы, перегородки.
# Границу помещения они не задают — лифт стоит посреди детского клуба, и
# если мерить ширину по нему, помещение схлопывается в 3 см.
OBSTACLE = ("лифт", "трап_", "шахта", "колонна", "пиллерс", "комингс",
            "перегородка", "проём", "пост_", "киоск", "набор_", "шпангоут",
            "бимс", "стрингер", "флор", "фундамент", "устр_", "мо_", "дрк_")

MARGIN = 0.012          # зазор до конструкции, м


def _log(*a):
    print(" ".join(str(x) for x in a))


# --- разметка помещения ----------------------------------------------------

def _struct_bvh(exclude=(), skip=()):
    """BVH по конструкции: обстановка в него не входит."""
    dg = bpy.context.evaluated_depsgraph_get()
    vs, ts = [], []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.visible_get():
            continue
        n = o.name
        if n in exclude or n.startswith("мебель_"):
            continue
        low = n.lower()
        if skip and low.startswith(skip):
            continue
        if not (low.startswith(STRUCT) or "пол_" in low or "настил" in low):
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


def half_width(bvh, x, z, hmax=8.5):
    """Полуширина помещения на шпации x: ближайшая конструкция с борта."""
    w = []
    for d in (Vector((0, 1, 0)), Vector((0, -1, 0))):
        best = hmax
        for dz in (0.35, 1.20, 1.85):
            hit = bvh.ray_cast(Vector((x, 0.0, z + dz)), d, hmax)
            if hit[0] is not None:
                best = min(best, hit[3])
        w.append(best)
    return max(0.0, min(w))


def room_width(bvh, x0, x1, z, step=0.25):
    """Таблица полуширин по длине помещения и функция-интерполятор."""
    n = max(2, int((x1 - x0) / step) + 1)
    xs = [x0 + (x1 - x0) * k / (n - 1) for k in range(n)]
    ws = [half_width(bvh, x, z) for x in xs]
    # сглаживание: одиночный простенок не должен резать всю раскладку
    sm = []
    for i in range(n):
        a = max(0, i - 1)
        b = min(n - 1, i + 1)
        sm.append(min(ws[a:b + 1]) if 0 < i < n - 1 else ws[i])

    def hw(x):
        if x <= xs[0]:
            return sm[0]
        if x >= xs[-1]:
            return sm[-1]
        k = int((x - x0) / (x1 - x0) * (n - 1))
        k = max(0, min(n - 2, k))
        t = (x - xs[k]) / (xs[k + 1] - xs[k])
        return sm[k] * (1 - t) + sm[k + 1] * t

    return hw, sm


# --- проверка на столкновение ----------------------------------------------

_CUBE = ((0, 1, 2), (0, 2, 3), (4, 6, 5), (4, 7, 6), (0, 4, 5), (0, 5, 1),
         (1, 5, 6), (1, 6, 2), (2, 6, 7), (2, 7, 3), (3, 7, 4), (3, 4, 0))


def _part_tris(p, shrink=MARGIN):
    """Габарит детали двенадцатью треугольниками, поджатый на зазор.

    Цилиндр берётся своим габаритным ящиком: для проверки на столкновение
    этого достаточно и с запасом в безопасную сторону.
    """
    x0, x1, y0, y1, z0, z1 = F.bounds(p)
    sx = min(shrink, (x1 - x0) / 3)
    sy = min(shrink, (y1 - y0) / 3)
    sz = min(shrink, (z1 - z0) / 3)
    x0, x1 = x0 + sx, x1 - sx
    y0, y1 = y0 + sy, y1 - sy
    z0, z1 = z0 + sz, z1 - sz
    return [Vector(v) for v in
            ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
             (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]


def _group_bvh(parts):
    vs, ts = [], []
    for p in parts:
        n = len(vs)
        vs += _part_tris(p)
        ts += [(a + n, b + n, c + n) for a, b, c in _CUBE]
    return BVHTree.FromPolygons(vs, ts, all_triangles=True)


def _blocked(bvh, parts):
    """Хоть одна деталь группы задевает конструкцию?"""
    return bool(bvh.overlap(_group_bvh(parts)))


# Сдвиги, которыми сборщик пробует обойти шахту, простенок или соседа:
# сначала на место, потом вдоль борта, потом вдоль судна.
_TRIES = [(0.0, 0.0)]
for _d in (0.30, 0.60, 0.90, 1.30, 1.80):
    _TRIES += [(0.0, _d), (0.0, -_d)]
for _d in (0.35, 0.70, 1.10):
    _TRIES += [(_d, 0.0), (-_d, 0.0)]


def _out_of_room(gb, hw, step=0.30):
    """Габарит группы выходит за переборки хотя бы на одной шпации."""
    n = max(2, int((gb[1] - gb[0]) / step) + 1)
    for k in range(n):
        xx = gb[0] + (gb[1] - gb[0]) * k / (n - 1)
        if max(abs(gb[2]), abs(gb[3])) > hw(xx) - MARGIN:
            return True
    return False


def _overlap(a, b, m=0.004):
    return (a[0] < b[1] - m and b[0] < a[1] - m
            and a[2] < b[3] - m and b[2] < a[3] - m
            and a[4] < b[5] - m and b[4] < a[5] - m)


# --- сборка сетки ----------------------------------------------------------

def _mat_slots(me, mats):
    me.materials.clear()
    for m in mats:
        me.materials.append(bpy.data.materials.get(m))


def _emit(bm, p, slot):
    """Деталь в сетку. Возвращает созданные грани, чтобы повесить материал.

    Назначать материал по индексу грани нельзя: `bm.to_mesh` переставляет
    грани, и материал уезжает на соседнюю деталь — на этом уже горел ковёр
    в каютах.
    """
    if p[0] == "box":
        _, _, x0, x1, y0, y1, z0, z1, _ = p
        res = bmesh.ops.create_cube(bm, size=1.0)
        verts = res["verts"]
        for v in verts:
            v.co.x = x0 + (v.co.x + 0.5) * (x1 - x0)
            v.co.y = y0 + (v.co.y + 0.5) * (y1 - y0)
            v.co.z = z0 + (v.co.z + 0.5) * (z1 - z0)
    else:
        _, _, cx, cy, r, z0, z1, _, seg = p
        res = bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False,
                                    segments=max(6, seg), radius1=r,
                                    radius2=r, depth=max(1e-4, z1 - z0))
        verts = res["verts"]
        for v in verts:
            v.co.x += cx
            v.co.y += cy
            v.co.z += (z0 + z1) / 2
    faces = {f for v in verts for f in v.link_faces}
    for f in faces:
        f.material_index = slot
    return faces


def build_room(name, deck, x0, x1, fn, pref, bvh, report, edge=None):
    z = DECK_TOP[deck]
    hw, prof = room_width(edge or bvh, x0, x1, z)
    groups = fn(x0, x1, z, hw, n=pref)
    kept, parts = [], []
    dropped = 0
    forced, drops = [], []
    for gname, gparts, must in groups:
        if not gparts:
            continue
        placed = None
        why = ""
        for dx, dy in _TRIES:
            cand = F.move(gparts, dx, dy) if (dx or dy) else gparts
            gb = F.group_bounds(cand)
            if _out_of_room(gb, hw):
                why = "за габарит"
                continue
            if _blocked(bvh, cand):
                why = "в конструкцию"
                continue
            if any(_overlap(gb, kb) for kb in kept):
                why = "в соседа"
                continue
            placed = (cand, gb)
            break
        if placed is None:
            drops.append((gname, why, must))
            if must:
                forced.append("%s (%s)" % (gname, why))
            dropped += 1
            continue
        kept.append(placed[1])
        parts += placed[0]
    mats = []
    for p in parts:
        m = p[8] if p[0] == "box" else p[7]
        if m not in mats:
            mats.append(m)
    bm = bmesh.new()
    for p in parts:
        m = p[8] if p[0] == "box" else p[7]
        _emit(bm, p, mats.index(m))
    obj = bpy.data.objects.get(name)
    if obj is None:
        me = bpy.data.meshes.new(name)
        obj = bpy.data.objects.new(name, me)
        coll = bpy.data.collections.get("31_Мебель") or bpy.context.scene.collection
        coll.objects.link(obj)
    me = obj.data
    bm.to_mesh(me)
    bm.free()
    _mat_slots(me, mats)
    me.update()
    obj.matrix_world.identity()
    report.append((name, len(parts), len(kept), dropped, len(forced),
                   round(min(prof), 2), round(max(prof), 2), drops))
    if forced:
        _log("  !! снято обязательных: %d — %s"
             % (len(forced), ", ".join(forced[:6])))
    return obj


def rebuild(only=None, verbose=True):
    names = list(R.ROOMS) if only is None else list(only)
    hit = _struct_bvh(exclude=set(names))
    edge = _struct_bvh(exclude=set(names), skip=OBSTACLE)
    report = []
    for nm in names:
        deck, x0, x1, fn, pref = R.ROOMS[nm]
        if verbose:
            _log("—", nm)
        build_room(nm, deck, x0, x1, fn, pref, hit, report, edge)
    if verbose:
        _log("%-32s %6s %6s %6s %6s %s" %
             ("помещение", "детал", "групп", "снято", "обяз", "полуширина"))
        for r in report:
            _log("%-32s %6d %6d %6d %6d  %.2f..%.2f м"
                 % (r[0], r[1], r[2], r[3], r[4], r[5], r[6]))
    return report
