# -*- coding: utf-8 -*-
r"""Рендеры кают: интерьер с точки входа и план сверху.

Каждый эталон каюты снимается в отдельной сцене, чтобы судно вокруг не
мешало: своя камера, свой свет за окном и ровный фон. Свет ставится так,
как он падает в настоящей каюте — дневной поток из окна плюс тёплые
светильники на подволоке, поэтому дерево и ткани показывают фактуру,
а не заливаются одной яркостью.

    exec(open(r"E:\Ship_docx\scripts\blender_рендер_кают.py", encoding="utf-8").read())
    render_all()
"""
import bpy, bmesh, os, math
from mathutils import Vector

OUT = r"E:\Ship_docx\renders\горизонт_2026\каюты"
SAMPLES = 220
RES = (1800, 1150)

SHOTS = [
    ("эталон_люкс",           "1_люкс"),
    ("эталон_люкс_дост",      "2_люкс_доступный"),
    ("эталон_бизнес",         "3_бизнес"),
    ("эталон_бизнес_дост",    "4_бизнес_доступный"),
    ("эталон_стандарт",       "5_стандарт"),
    ("эталон_стандарт_дост",  "6_стандарт_доступный"),
    ("эталон_эконом",         "7_эконом"),
    ("эталон_эконом_вн",      "8_эконом_внутренняя"),
    ("эталон_экипаж_2",       "9_каюта_экипажа"),
]


def _bbox(o):
    pts = [o.matrix_world @ v.co for v in o.data.vertices]
    return (min(p.x for p in pts), max(p.x for p in pts),
            min(p.y for p in pts), max(p.y for p in pts),
            min(p.z for p in pts), max(p.z for p in pts))


def _world(sc, strength=2.2, col=(0.62, 0.74, 0.92)):
    w = bpy.data.worlds.new("_каюта_мир")
    w.use_nodes = True
    nt = w.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputWorld")
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Color"].default_value = (col[0], col[1], col[2], 1.0)
    bg.inputs["Strength"].default_value = strength
    nt.links.new(bg.outputs["Background"], out.inputs["Surface"])
    sc.world = w
    return w


def _scene(name):
    sc = bpy.data.scenes.new(name)
    sc.render.engine = "CYCLES"
    sc.cycles.device = "GPU"
    sc.cycles.samples = SAMPLES
    sc.cycles.use_denoising = True
    sc.cycles.max_bounces = 10
    sc.cycles.transmission_bounces = 6
    sc.cycles.caustics_reflective = False
    sc.cycles.caustics_refractive = False
    sc.render.resolution_x, sc.render.resolution_y = RES
    sc.render.resolution_percentage = 100
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    for look in ("AgX - Punchy", "AgX - Medium High Contrast"):
        try:
            sc.view_settings.look = look
            break
        except TypeError:
            continue
    sc.view_settings.exposure = 0.30
    return sc


def _light(sc, kind, loc, energy, size=1.0, rot=(0, 0, 0), col=(1, 1, 1)):
    d = bpy.data.lights.new("_св", kind)
    d.energy = energy
    d.color = col
    if kind == "AREA":
        d.size = size
        d.size_y = size
    o = bpy.data.objects.new("_св", d)
    o.location = loc
    o.rotation_euler = rot
    sc.collection.objects.link(o)
    return o


def open_mesh(src, h_room=2.20, wall=0.06):
    """Копия сетки без подволока и коридорной переборки.

    Камеру внутрь каюты ставить некуда: 8 м² свободного пола на люкс,
    и объектив упирается то в торшер, то в шкаф. Поэтому снимаем каюту
    «кукольным домиком» — снаружи и сверху, сняв потолок и ближнюю стенку.
    """
    me = src.data.copy()
    bm = bmesh.new()
    bm.from_mesh(me)
    y1 = max(v.co.y for v in bm.verts)
    kill = []
    for f in bm.faces:
        c = f.calc_center_median()
        if c.z > h_room - 0.02 or c.y > y1 - wall:
            kill.append(f)
    bmesh.ops.delete(bm, geom=kill, context="FACES")
    bm.to_mesh(me)
    bm.free()
    return me


def _render(sc, path):
    """Отрисовать именно свою сцену.

    bpy.ops.render.render(scene=...) сцену не переключает, а в фоновом
    процессе окна нет вовсе, поэтому сцена подменяется переопределением
    контекста; переключение окна остаётся запасным вариантом для работы
    из открытого Blender.
    """
    sc.render.filepath = path
    try:
        with bpy.context.temp_override(scene=sc):
            bpy.ops.render.render(write_still=True)
        return path
    except (AttributeError, TypeError, RuntimeError):
        pass
    win = bpy.context.window
    prev = win.scene
    win.scene = sc
    try:
        bpy.ops.render.render(write_still=True)
    finally:
        win.scene = prev
    return path


def render_cabin(proto, stem, plan=True, interior=True, verbose=True):
    src = bpy.data.objects.get(proto)
    if src is None:
        return []
    x0, x1, y0, y1, z0, z1 = _bbox(src)
    W, D = x1 - x0, y1 - y0
    made = []
    sc = _scene("_рендер_" + stem)
    _world(sc, strength=1.5)
    ob = src.copy()
    ob.data = open_mesh(src) if interior else src.data
    # эталоны в судовой сцене скрыты от рендера, чтобы не лезть в кадр;
    # в своей сцене их надо показать
    ob.hide_render = False
    ob.hide_viewport = False
    sc.collection.objects.link(ob)

    # дневной свет снаружи окна (окно на грани y = y0)
    _light(sc, "AREA", (x0 + W / 2, y0 - 1.2, z0 + 1.35), 760.0,
           size=max(W, 2.2), rot=(math.radians(90), 0, 0),
           col=(0.92, 0.96, 1.0))
    # тёплая подсветка изнутри, имитирует светильники и бра
    _light(sc, "AREA", (x0 + W * 0.55, y0 + D * 0.55, z0 + 2.05), 120.0,
           size=min(W, D) * 0.8, rot=(math.radians(180), 0, 0),
           col=(1.0, 0.86, 0.68))
    # верхний рассеянный свет вместо снятого подволока
    _light(sc, "AREA", (x0 + W * 0.5, y0 + D * 0.5, z0 + 3.4), 150.0,
           size=max(W, D) * 1.4, rot=(math.radians(180), 0, 0),
           col=(1.0, 0.94, 0.86))

    cam_d = bpy.data.cameras.new("_кам")
    cam = bpy.data.objects.new("_кам", cam_d)
    sc.collection.objects.link(cam)
    sc.camera = cam

    if interior:
        cam_d.type = "PERSP"
        cam_d.lens = 34.0
        cam_d.sensor_width = 36.0
        cam_d.clip_start = 0.02
        cam.location = (x1 + W * 0.30, y1 + D * 0.92, z0 + 2.05 + D * 0.30)
        tgt = Vector((x0 + W * 0.46, y0 + D * 0.48, z0 + 0.80))
        cam.rotation_euler = (tgt - cam.location).to_track_quat("-Z", "Y").to_euler()
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = 92
        made.append(_render(sc, os.path.join(OUT, stem + "_интерьер.jpg")))
    if plan:
        cam_d.type = "ORTHO"
        cam_d.ortho_scale = max(W, D) * 1.12
        cam.location = (x0 + W / 2, y0 + D / 2, z0 + 2.14)
        cam.rotation_euler = (0.0, 0.0, 0.0)
        sc.render.resolution_x = int(RES[0] * 0.8)
        sc.render.resolution_y = int(RES[0] * 0.8 * D / max(W, 1e-6))
        sc.render.image_settings.file_format = "PNG"
        made.append(_render(sc, os.path.join(OUT, stem + "_план.png")))
    w = sc.world
    bpy.data.scenes.remove(sc)
    bpy.data.worlds.remove(w)
    if verbose:
        print(stem, "готово")
    return made


def render_all(only=None, verbose=True):
    os.makedirs(OUT, exist_ok=True)
    made = []
    for proto, stem in SHOTS:
        if only and stem not in only and proto not in only:
            continue
        made += render_cabin(proto, stem, verbose=verbose)
    return made
