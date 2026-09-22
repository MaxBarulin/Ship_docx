# -*- coding: utf-8 -*-
"""Узел ВГ-2026.31.00 «Ось плицы с кривошипом» в Blender: сборка, аудит, виды, STL.

Запускается в открытой сессии Blender по MCP (`собрать()`), строит узел в
отдельной сцене «Узел» в метрах из миллиметров `lib.gorizont_node` — тех
же, что у чертежа и STEP. Виды: изометрия, сбоку, взрыв-схема; экспорт STL.
"""
import bpy, math, os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
for p in (os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts")):
    if p not in sys.path:
        sys.path.insert(0, p)
from lib import gorizont_node as N
import blender_стиль as Ст

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "узел")
CAD = os.path.join(ROOT, "CAD", "STL")
MM = 0.001


def _сцена():
    sc = bpy.data.scenes.get("Узел")
    if sc is None:
        sc = bpy.data.scenes.new("Узел")
    bpy.context.window.scene = sc
    for o in list(sc.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(sc.collection.children):
        sc.collection.children.unlink(c)
    кол = bpy.data.collections.get("Узел_детали") or bpy.data.collections.new("Узел_детали")
    for o in list(кол.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sc.collection.children.link(кол)
    return sc, кол


def _mesh(имя, verts, faces, кол, материал):
    me = bpy.data.meshes.new(имя)
    me.from_pydata(verts, [], faces)
    me.validate(verbose=False); me.update()
    ob = bpy.data.objects.new(имя, me)
    кол.objects.link(ob)
    Ст.назначить(ob, материал)
    return ob


def цилиндр(имя, r, z0, z1, кол, материал, x=0.0, y=0.0, сег=48, r_in=None):
    """Цилиндр (или труба) вдоль Y — ось узла вдоль оси Y судна; z0..z1 — вдоль оси."""
    verts, faces = [], []
    rings = [(r, z0), (r, z1)]
    n = сег
    for rr, zz in rings:
        for i in range(n):
            a = 2 * math.pi * i / n
            verts.append((x + rr * math.cos(a), zz, y + rr * math.sin(a)))
    for i in range(n):
        faces.append([i, (i + 1) % n, n + (i + 1) % n, n + i])
    if r_in is None:
        c0 = len(verts); verts.append((x, z0, y)); c1 = len(verts); verts.append((x, z1, y))
        for i in range(n):
            faces.append([c0, (i + 1) % n, i])
            faces.append([c1, n + i, n + (i + 1) % n])
    else:
        b = len(verts)
        for rr, zz in ((r_in, z0), (r_in, z1)):
            for i in range(n):
                a = 2 * math.pi * i / n
                verts.append((x + rr * math.cos(a), zz, y + rr * math.sin(a)))
        for i in range(n):
            j = (i + 1) % n
            faces.append([b + i, b + n + i, b + n + j, b + j])          # внутренняя стенка (наизнанку — исправим)
            faces.append([i, b + j, b + i])                                # торец z0 — треугольники
            faces.append([i, j, b + j])
            faces.append([n + i, b + n + i, b + n + j])
            faces.append([n + i, b + n + j, n + j])
    ob = _mesh(имя, verts, faces, кол, материал)
    import bmesh
    bm = bmesh.new(); bm.from_mesh(ob.data); bmesh.ops.recalc_face_normals(bm, faces=bm.faces); bm.to_mesh(ob.data); bm.free()
    return ob


def короб(имя, центр, размеры, кол, материал):
    dx, dy, dz = (d / 2.0 for d in размеры)
    verts = [(sx * dx, sy * dy, sz * dz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    faces = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 2, 6, 4], [1, 5, 7, 3], [0, 4, 5, 1], [2, 3, 7, 6]]
    ob = _mesh(имя, verts, faces, кол, материал)
    ob.location = центр
    return ob


def собрать(verbose=True):
    """Собрать узел; координаты: ось вдоль Y, плица в плоскости XY со стороны +X."""
    sc, кол = _сцена()
    Ст.построить()
    r = N.D_AXIS / 2 * MM
    zj = (N.DISC_Y - N.DISC_T / 2 - 5.0) * MM
    jl = N.L_JOURNAL * MM
    детали = []
    детали.append(цилиндр("Ось_тело", r, -zj, zj, кол, "Леера_сталь"))
    детали.append(цилиндр("Ось_цапфа_ПБ", N.D_JOURNAL / 2 * MM, zj, zj + jl, кол, "Леера_сталь"))
    детали.append(цилиндр("Ось_цапфа_ЛБ", N.D_JOURNAL / 2 * MM, -zj - jl, -zj, кол, "Леера_сталь"))
    детали.append(цилиндр("Ось_хвостовик", 0.040, zj + jl, zj + jl + 0.045, кол, "Леера_сталь"))
    детали.append(цилиндр("Гайка_М80", 0.060, zj + jl + 0.004, zj + jl + 0.040, кол, "Технические_серые", сег=6, r_in=0.041))
    for s in (1, -1):
        yc = s * N.DISC_Y * MM
        детали.append(цилиндр("Втулка_%s" % ("ПБ" if s > 0 else "ЛБ"), N.BUSH_D_OUT / 2 * MM, yc - N.BUSH_L / 2 * MM, yc + N.BUSH_L / 2 * MM,
                              кол, "Технические_серые", r_in=N.D_JOURNAL / 2 * MM + 0.0005))
        # фрагмент диска обода — контекст, 0,3 м
        детали.append(короб("Диск_обода_фрагмент_%d" % s, (0.0, yc, 0.0), (0.30, N.DISC_T * MM, 0.30), кол, "Колесо_обод"))
    for hy in N.HUB_Y:
        for s in (1, -1):
            yc = s * hy * MM
            имя = "Ступица_%s_%.0f" % ("ПБ" if s > 0 else "ЛБ", hy)
            детали.append(цилиндр(имя, N.HUB_D / 2 * MM, yc - N.HUB_L / 2 * MM, yc + N.HUB_L / 2 * MM, кол, "Технические_серые", r_in=r + 0.0003))
            hz = (N.BLADE_H - 40) * MM
            детали.append(короб(имя + "_фланец", ((50 + N.LUG_T / 2) * MM, yc, 0.0), (N.LUG_T * MM, N.HUB_L * MM, hz), кол, "Технические_серые"))
            for sz in (1, -1):
                детали.append(короб(imя_болта(имя, sz), ((N.HUB_D / 2 + 12) * MM * sz, yc + 0.0, 0.0), (0.040, 0.060, 0.030), кол, "Технические_серые"))
    # панели плицы — контекст (тонкие, по 2 шт.)
    x_pl = (50 + N.LUG_T) * MM
    детали.append(короб("Плица_панель_верх", (x_pl + N.BLADE_T / 2 * MM, 0.0, (N.HUB_D / 2 + 30 + (N.BLADE_H / 2 - N.HUB_D / 2 - 30) / 2) * MM),
                        (N.BLADE_T * MM, N.BLADE_SPAN * MM, (N.BLADE_H / 2 - N.HUB_D / 2 - 30) * MM), кол, "Колесо_плица"))
    детали.append(короб("Плица_панель_низ", (x_pl + N.BLADE_T / 2 * MM, 0.0, -(N.HUB_D / 2 + 30 + (N.BLADE_H / 2 - N.HUB_D / 2 - 30) / 2) * MM),
                        (N.BLADE_T * MM, N.BLADE_SPAN * MM, (N.BLADE_H / 2 - N.HUB_D / 2 - 30) * MM), кол, "Колесо_плица"))
    # кривошип: ступица + щека + палец
    yc = N.CRANK_Y * MM
    детали.append(цилиндр("Кривошип_ступица", N.CRANK_HUB_D / 2 * MM, yc - 0.040, yc + 0.040, кол, "Технические_серые", r_in=r + 0.0003))
    детали.append(короб("Кривошип_щека", (0.0, yc, (N.CRANK_HUB_D / 2 * MM + N.CRANK_L * MM) / 2.0),
                        (N.CRANK_W * MM, N.CRANK_T * MM, N.CRANK_L * MM - N.CRANK_HUB_D / 2 * MM), кол, "Технические_серые"))
    детали.append(цилиндр("Кривошип_палец", N.PIN_D / 2 * MM, yc - N.PIN_L * MM + N.CRANK_T / 2 * MM - 0.001, yc + N.CRANK_T / 2 * MM + 0.010, кол, "Леера_сталь",
                          y=N.CRANK_L * MM))
    детали.append(цилиндр("Кривошип_палец_головка", (N.PIN_D / 2 + 12) * MM, yc + N.CRANK_T / 2 * MM + 0.010, yc + N.CRANK_T / 2 * MM + 0.022, кол, "Леера_сталь",
                          y=N.CRANK_L * MM))
    b, h, l = N.KEY
    детали.append(короб("Шпонка_кривошипа", (r - 0.0002, yc, 0.0), (h * MM, l * MM, b * MM), кол, "Леера_сталь"))
    if verbose:
        print("узел: %d деталей" % len(детали))
    return детали


def imя_болта(имя, sz):
    return имя + "_болт_%d" % (1 if sz > 0 else 2)


def виды(samples=64, res=(1800, 1200), взрыв=True):
    """Рендер: изометрия, сбоку; взрыв-схема — детали раздвинуты вдоль оси."""
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.data.scenes["Узел"]
    sc.render.engine = "CYCLES"
    sc.cycles.samples = samples
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.film_transparent = False
    w = bpy.data.worlds.get("Узел_мир") or bpy.data.worlds.new("Узел_мир")
    w.use_nodes = True
    bg = w.node_tree.nodes.get("Background")
    if bg:
        bg.inputs[0].default_value = (0.92, 0.93, 0.95, 1.0); bg.inputs[1].default_value = 1.0
    sc.world = w
    cam = bpy.data.objects.get("Узел_камера")
    if cam is None:
        cam = bpy.data.objects.new("Узел_камера", bpy.data.cameras.new("Узел_камера")); sc.collection.objects.link(cam)
    sc.camera = cam
    sun = bpy.data.objects.get("Узел_солнце")
    if sun is None:
        sun = bpy.data.objects.new("Узел_солнце", bpy.data.lights.new("Узел_солнце", "SUN")); sc.collection.objects.link(sun)
    sun.data.energy = 3.0
    sun.rotation_euler = (math.radians(50), math.radians(20), math.radians(30))
    сделано = []

    def кадр(имя, loc, look, lens=50):
        from mathutils import Vector
        cam.location = loc
        d = Vector(look) - Vector(loc)
        cam.rotation_euler = d.to_track_quat("-Z", "Y").to_euler()
        cam.data.lens = lens
        sc.render.filepath = os.path.join(OUT, имя)
        bpy.ops.render.render(write_still=True)
        сделано.append(sc.render.filepath)
    кадр("01_изометрия.png", (3.2, -3.6, 1.9), (0.1, 0.0, 0.1), 45)
    кадр("02_кривошип_крупно.png", (1.2, 0.6, 0.9), (0.05, 1.4, 0.25), 60)
    кадр("03_сверху.png", (0.0, 0.0, 4.6), (0.0, 0.0, 0.0), 40)
    if взрыв:
        # взрыв: раздвинуть детали вдоль оси Y от середины пропорционально положению
        сдвиги = {}
        for o in bpy.data.collections["Узел_детали"].objects:
            y = o.location.y if o.name.startswith(("Ступица", "Диск", "Втулка", "Кривошип", "Гайка", "Шпонка")) else None
            if o.name.startswith("Ось_"):
                continue
            if o.name.startswith("Плица"):
                o.location.x += 0.9; сдвиги[o.name] = ("x", 0.9); continue
            k = 0.45 if o.name.startswith(("Ступица", "Шпонка")) else 0.7
            dy = (1 if (y or 0) >= 0 else -1) * k * (1 + abs(y or 0) / 1.6)
            if o.name.startswith("Кривошип"):
                dy = 0.9
            o.location.y += dy; сдвиги[o.name] = ("y", dy)
            if o.name.startswith("Втулка") or o.name.startswith("Диск"):
                o.location.z += 0.5 if o.name.startswith("Втулка") else 0.0
        кадр("04_взрыв_схема.png", (3.6, -4.2, 2.2), (0.3, 0.0, 0.2), 42)
        for o in bpy.data.collections["Узел_детали"].objects:
            if o.name in сдвиги:
                ax, d = сдвиги[o.name]
                if ax == "x":
                    o.location.x -= d
                else:
                    o.location.y -= d
                    if o.name.startswith("Втулка"):
                        o.location.z -= 0.5
    return сделано


def экспорт():
    os.makedirs(CAD, exist_ok=True)
    sc = bpy.data.scenes["Узел"]
    bpy.context.window.scene = sc
    for o in sc.objects:
        o.select_set(o.type == "MESH")
    p = os.path.join(CAD, "ВГ-2026.31.00_ось_плицы_blender.stl")
    bpy.ops.wm.stl_export(filepath=p, export_selected_objects=True, global_scale=1000.0, ascii_format=False)
    return p
