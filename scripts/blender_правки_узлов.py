# -*- coding: utf-8 -*-
r"""Правки узлов по результатам аудита сцены.

Каждая правка отвечает конкретной находке blender_аудит.audit():

* набор корпуса режется туннелями гребных винтов и дейдвудными трубами —
  в металле там вырез, а не пересечение;
* отдельные фрагменты палубного насыщения (кнехты, киповые планки,
  шезлонги, мебель) сдвигаются внутрь, чтобы не влезать в фальшборт,
  дымовые шахты, леера и борт надстройки;
* кронштейн РЛС укорачивается до антенны.

Правки написаны как перебор связных кусков сетки: двигается только тот
кусок, который нарушает габарит, остальная геометрия не трогается.

    exec(open(r"E:\Ship_docx\scripts\blender_правки_узлов.py", encoding="utf-8").read())
    fix_all()
"""
import bpy, bmesh, math, re, sys

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont as G, gorizont_hydro as H


def islands(bm):
    """Связные куски сетки."""
    seen, out = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, grp = [v], []
        seen.add(v)
        while stack:
            c = stack.pop()
            grp.append(c)
            for e in c.link_edges:
                o = e.other_vert(c)
                if o not in seen:
                    seen.add(o)
                    stack.append(o)
        out.append(grp)
    return out


def nudge(name, fix, verbose=True):
    """Сдвинуть куски сетки, для которых fix(bbox) вернёт смещение."""
    o = bpy.data.objects.get(name)
    if not o:
        return 0
    bm = bmesh.new()
    bm.from_mesh(o.data)
    mw = o.matrix_world
    inv = mw.inverted()
    n = 0
    for grp in islands(bm):
        ws = [mw @ v.co for v in grp]
        bb = (min(p.x for p in ws), max(p.x for p in ws),
              min(p.y for p in ws), max(p.y for p in ws),
              min(p.z for p in ws), max(p.z for p in ws))
        d = fix(bb)
        if not d:
            continue
        for v, w in zip(grp, ws):
            v.co = inv @ (w + __import__("mathutils").Vector(d))
        n += 1
    bm.to_mesh(o.data)
    bm.free()
    o.data.update()
    if verbose and n:
        print("  %s: сдвинуто кусков %d" % (name, n))
    return n


def cut_by(names, cutter_builder, tag="вырез"):
    """Булево вычитание общей формы из перечисленных объектов."""
    col = bpy.data.collections.get("40_Набор_корпуса") or bpy.context.scene.collection
    cutters = []
    for me in cutter_builder():
        co = bpy.data.objects.new("_cutter", me)
        col.objects.link(co)
        cutters.append(co)
    done = []
    for nm in names:
        o = bpy.data.objects.get(nm)
        if not o:
            continue
        for co in cutters:
            m = o.modifiers.new(tag, "BOOLEAN")
            m.operation = "DIFFERENCE"
            m.solver = "EXACT"
            m.object = co
            bpy.context.view_layer.objects.active = o
            try:
                bpy.ops.object.modifier_apply(modifier=m.name)
            except RuntimeError:
                o.modifiers.remove(m)
        done.append(nm)
    for co in cutters:
        bpy.data.objects.remove(co, do_unlink=True)
    return done


def _cyl(x0, x1, y, z, r, seg=24):
    bm = bmesh.new()
    rings = []
    for x in (x0, x1):
        rings.append([bm.verts.new((x, y + r * math.cos(2 * math.pi * k / seg),
                                    z + r * math.sin(2 * math.pi * k / seg)))
                      for k in range(seg)])
    for k in range(seg):
        k2 = (k + 1) % seg
        bm.faces.new([rings[0][k], rings[1][k], rings[1][k2], rings[0][k2]])
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[1])
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("_cyl")
    bm.to_mesh(me)
    bm.free()
    return me


def _prop_cutters():
    """Туннели винтов и дейдвудные трубы — вырез в наборе."""
    out = []
    r = G.NOZZLE_OUTER + 0.10
    for s in (1, -1):
        out.append(_cyl(-0.6, G.TUNNEL_LENGTH * 0.62, s * G.PROP_Y,
                        G.SHAFT_Z_PROP, r))
        out.append(_cyl(G.TUNNEL_LENGTH * 0.62, 20.0, s * G.PROP_Y,
                        (G.SHAFT_Z_PROP + G.SHAFT_Z_MOTOR) / 2, 0.42))
    return out


FRAME_PARTS = ("набор_киль_и_стрингеры", "набор_продольные_рёбра",
               "набор_флоры", "набор_шпангоуты",
               "набор_рамные_шпангоуты_и_бимсы", "настил_второго_дна",
               "цистерны_поперечные_переборки", "цистерны_продольные_переборки")


def fix_propulsion():
    """Вырезать в наборе туннели винтов и дейдвуды."""
    return cut_by(FRAME_PARTS, _prop_cutters, tag="туннель")


def fix_mooring():
    """Швартовное устройство: убрать из дымовых шахт и из фальшборта."""
    def f(bb):
        x0, x1, y0, y1, z0, z1 = bb
        dx = dy = 0.0
        # кормовой пост — вперёд от дымовых шахт нельзя (там надстройка),
        # уводим в корму, на открытый участок палубы
        if 8.2 < x1 < 13.6 and max(abs(y0), abs(y1)) > 3.0:
            dx = 8.0 - x1
        # носовой пост — вперёд от переборки надстройки
        if x1 > 129.8 and x0 < 131.6:
            dx = 2.2
        # носовые фрагменты, вылезающие за кромку фальшборта
        lim = H.half_breadth((x0 + x1) / 2, G.DEPTH) - 0.30
        ym = max(abs(y0), abs(y1))
        if ym > lim:
            dy = -(ym - lim) * (1 if (y0 + y1) > 0 else -1)
        return (dx, dy, 0.0) if (dx or dy) else None
    return nudge("устр_якорно_швартовное", f)


def fix_super_furniture():
    """Мебель, вылезающую за борт надстройки, подобрать внутрь."""
    n = 0
    for nm in ("мебель_ресторан", "мебель_детский_клуб",
               "мебель_главная_носовой_салон", "мебель_верхняя_салон",
               "мебель_шлюпочная_салон"):
        def f(bb, _nm=nm):
            x0, x1, y0, y1, z0, z1 = bb
            xc = (x0 + x1) / 2
            lim = min(H.super_half_breadth(v) for v in (x0, xc, x1)) - 0.12
            ym = max(abs(y0), abs(y1))
            if lim > 0 and ym > lim:
                return (0.0, -(ym - lim + 0.02) * (1 if (y0 + y1) > 0 else -1), 0.0)
            return None
        n += nudge(nm, f)
    return n


def fix_deck_furniture():
    """Шезлонги на крыше — от леера внутрь."""
    def f(bb):
        x0, x1, y0, y1, z0, z1 = bb
        ym = max(abs(y0), abs(y1))
        if ym > 4.70:
            return (0.0, -(ym - 4.68) * (1 if (y0 + y1) > 0 else -1), 0.0)
        return None
    return nudge("шезлонги_крыши", f)


def fix_mast():
    """Кронштейн РЛС укоротить до антенны."""
    o = bpy.data.objects.get("мачта_кронштейн_рлс")
    a = bpy.data.objects.get("мачта_антенна_рлс")
    if not o or not a:
        return 0
    x0 = min((a.matrix_world @ v.co).x for v in a.data.vertices)
    mw, inv = o.matrix_world, o.matrix_world.inverted()
    for v in o.data.vertices:
        w = mw @ v.co
        if w.x > x0 - 0.01:
            w.x = x0 - 0.01
            v.co = inv @ w
    o.data.update()
    return 1


def fix_partitions():
    """Выгородки первой палубы — внутрь от бортового стрингера."""
    n = 0
    for o in list(bpy.data.objects):
        if not o.name.startswith("переборка_первая_") or o.type != "MESH":
            continue
        def f(bb):
            x0, x1, y0, y1, z0, z1 = bb
            ym = max(abs(y0), abs(y1))
            lim = min(H.half_breadth(x, 2.60) for x in (x0, (x0 + x1) / 2, x1)) - 0.48
            if ym > lim:
                return (0.0, -(ym - lim) * (1 if (y0 + y1) > 0 else -1), 0.0)
            return None
        n += nudge(o.name, f, verbose=False)
    return n


def fix_coamings():
    """Комингсы шахт подрезать у стенок лифтов, а не двигать.

    Комингс обрамляет вырез в палубе и сдвигать его нельзя — он сойдёт
    с выреза. Там, где через вырез проходит шахта лифта, комингс в металле
    просто обрывается у её стенки: обрезаем вершины по габариту шахты.
    """
    boxes = []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.startswith("лифт_"):
            continue
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        boxes.append((min(p.x for p in pts), max(p.x for p in pts),
                      min(p.y for p in pts), max(p.y for p in pts)))
    n = 0
    for o in list(bpy.data.objects):
        if not o.name.startswith("комингс_") or o.type != "MESH":
            continue
        mw, inv = o.matrix_world, o.matrix_world.inverted()
        ws = [mw @ v.co for v in o.data.vertices]
        x0, x1 = min(w.x for w in ws), max(w.x for w in ws)
        y0, y1 = min(w.y for w in ws), max(w.y for w in ws)
        moved = False
        for bx0, bx1, by0, by1 in boxes:
            if not (x1 > bx0 + 0.01 and x0 < bx1 - 0.01
                    and y1 > by0 + 0.01 and y0 < by1 - 0.01):
                continue
            along_x = (x1 - x0) > (y1 - y0)
            for v, w in zip(o.data.vertices, ws):
                if along_x:
                    if bx0 - 0.01 < w.x < bx1 + 0.01:
                        w.x = bx0 - 0.02 if w.x < (bx0 + bx1) / 2 else bx1 + 0.02
                        v.co = inv @ w
                        moved = True
                else:
                    if by0 - 0.01 < w.y < by1 + 0.01:
                        w.y = by0 - 0.02 if w.y < (by0 + by1) / 2 else by1 + 0.02
                        v.co = inv @ w
                        moved = True
        if moved:
            o.data.update()
            n += 1
    return n


def _centerline(o, tol=0.25):
    """Продольная ветвь комингса, лежащая на диаметральной плоскости."""
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
    x0, x1 = min(p.x for p in pts), max(p.x for p in pts)
    return abs(y0) < tol and abs(y1) < tol and (x1 - x0) > (y1 - y0)


def fix_coaming_dp(gap=0.01):
    """Ветви комингса на ДП — строго по разные стороны от неё.

    Сторона берётся из имени объекта: в нём записана исходная координата y
    выреза, который этот комингс обрамляет.
    """
    n = 0
    for o in list(bpy.data.objects):
        if not o.name.startswith("комингс_") or o.type != "MESH":
            continue
        if not _centerline(o):
            continue
        m = re.match(r"комингс_[\d.\-]+_(-?[\d.]+)_\d+$", o.name)
        ref = float(m.group(1)) if m else 0.0
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        y0, y1 = min(p.y for p in pts), max(p.y for p in pts)
        w = y1 - y0
        tgt0 = gap if ref >= 0 else -gap - w
        o.location.y += tgt0 - y0
        n += 1
    return n


def fix_coaming_pairs(gap=0.01):
    """Комингсы у диаметральной плоскости развести по её разные стороны.

    Две продольные ветви комингса у ДП обрамляют соседние вырезы и в
    прежней сборке налезали друг на друга. Ставим их строго по разные
    стороны от ДП с зазором на сварной шов.
    """
    cs = [o for o in bpy.data.objects
          if o.name.startswith("комингс_") and o.type == "MESH"]
    box = {}
    for o in cs:
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        box[o.name] = (min(p.x for p in pts), max(p.x for p in pts),
                       min(p.y for p in pts), max(p.y for p in pts))
    n = 0
    for i, a in enumerate(cs):
        for b in cs[i + 1:]:
            ax0, ax1, ay0, ay1 = box[a.name]
            bx0, bx1, by0, by1 = box[b.name]
            if not (ax1 > bx0 + 0.01 and ax0 < bx1 - 0.01
                    and ay1 > by0 + 0.01 and ay0 < by1 - 0.01):
                continue
            if _centerline(a) and _centerline(b):
                continue                       # их разводит fix_coaming_dp
            up = a if (ay0 + ay1) > (by0 + by1) else b
            dn = b if up is a else a
            ov = min(ay1 - by0, by1 - ay0) + gap
            du, dd = ov / 2, -ov / 2
            up.location.y += du
            dn.location.y += dd
            box[up.name] = (box[up.name][0], box[up.name][1],
                            box[up.name][2] + du, box[up.name][3] + du)
            box[dn.name] = (box[dn.name][0], box[dn.name][1],
                            box[dn.name][2] + dd, box[dn.name][3] + dd)
            n += 1
    return n



DECKS = (1.40, 4.20, 7.00, 9.80, 12.60)


def fix_coaming_z():
    """Комингсы поднять на свою палубу: ниже настила им делать нечего."""
    n = 0
    for o in list(bpy.data.objects):
        if not o.name.startswith("комингс_") or o.type != "MESH":
            continue
        mw, inv = o.matrix_world, o.matrix_world.inverted()
        ws = [mw @ v.co for v in o.data.vertices]
        zmin = min(w.z for w in ws)
        deck = min(DECKS, key=lambda d: abs(d - zmin))
        if zmin >= deck - 1e-3:
            continue
        for v, w in zip(o.data.vertices, ws):
            if w.z < deck:
                w.z = deck
                v.co = inv @ w
        o.data.update()
        n += 1
    return n


def fix_furniture_vs_lifts():
    """Мебель — от стенок лифтов и трапов."""
    boxes = []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.startswith(("лифт_", "трап_")):
            continue
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        boxes.append((min(p.x for p in pts), max(p.x for p in pts),
                      min(p.y for p in pts), max(p.y for p in pts),
                      min(p.z for p in pts), max(p.z for p in pts)))
    n = 0
    for o in list(bpy.data.objects):
        if o.type != "MESH" or not o.name.startswith("мебель_"):
            continue
        def f(bb):
            x0, x1, y0, y1, z0, z1 = bb
            for bx0, bx1, by0, by1, bz0, bz1 in boxes:
                if (x1 > bx0 + 0.005 and x0 < bx1 - 0.005
                        and y1 > by0 + 0.005 and y0 < by1 - 0.005
                        and z1 > bz0 + 0.005 and z0 < bz1 - 0.005):
                    d = min(by1 - y0, y1 - by0) + 0.05
                    sg = 1.0 if (y0 + y1) / 2 > (by0 + by1) / 2 else -1.0
                    return (0.0, sg * d, 0.0)
            return None
        n += nudge(o.name, f, verbose=False)
    return n


MO_PARTS = ("набор_рамные_шпангоуты_и_бимсы", "набор_шпангоуты",
            "набор_продольные_рёбра", "набор_стрингеры_и_карлингсы",
            "набор_киль_и_стрингеры")


def fix_machinery_cutouts(clear=0.05):
    """Вырезать в наборе места под фундаменты механизмов.

    Механизм стоит не на голом наборе, а на фундаменте: рамный шпангоут
    и рёбра под ним вырезаны и заменены фундаментными балками. В модели
    это делается булевым вычитанием габарита механизма из набора.
    """
    cutters = []
    for o in bpy.data.objects:
        if o.type != "MESH" or not o.name.startswith("мо_"):
            continue
        pts = [o.matrix_world @ v.co for v in o.data.vertices]
        bb = (min(p.x for p in pts) - clear, max(p.x for p in pts) + clear,
              min(p.y for p in pts) - clear, max(p.y for p in pts) + clear,
              min(p.z for p in pts) - clear, max(p.z for p in pts) + clear)
        cutters.append(bb)
    if not cutters:
        return 0

    def build():
        out = []
        for x0, x1, y0, y1, z0, z1 in cutters:
            bm = bmesh.new()
            v = [bm.verts.new(p) for p in
                 ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
                  (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
            for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
                      (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
                bm.faces.new([v[k] for k in f])
            bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
            me = bpy.data.meshes.new("_mo")
            bm.to_mesh(me)
            bm.free()
            out.append(me)
        return out

    return len(cut_by(MO_PARTS, build, tag="фундамент"))


def fix_all(verbose=True):
    rep = {"туннели_в_наборе": fix_propulsion(),
           "швартовное": fix_mooring(),
           "мебель_надстройки": fix_super_furniture(),
           "шезлонги": fix_deck_furniture(),
           "мачта": fix_mast(),
           "выгородки": fix_partitions(),
           "комингсы_на_ДП": fix_coaming_dp(),
           "комингсы_парами": fix_coaming_pairs(),
           "комингсы_по_высоте": fix_coaming_z(),
           "комингсы": fix_coamings(),
           "мебель_у_лифтов": fix_furniture_vs_lifts(),
           "вырезы_под_фундаменты": fix_machinery_cutouts()}
    if verbose:
        print(rep)
    return rep
