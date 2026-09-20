# -*- coding: utf-8 -*-
r"""Внешние виды и палубные ракурсы судна.

Камеры заданы числами от главных размерений, а не расставлены руками:
поменялась длина или высота яруса — ракурс переедет вместе с судном.
Рендер идёт в судовой сцене, поэтому солнце, небо и вода те же, что и
в остальных кадрах; настройки сцены скрипт возвращает как было.

    exec(open(r"E:\Ship_docx\scripts\blender_рендер_видов.py", encoding="utf-8").read())
    render_views()
"""
import bpy, os, sys, math
from mathutils import Vector

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont as G

OUT = r"E:\Ship_docx\renders\горизонт_2026\виды"
SAMPLES = 160
EXPOSURE = -3.1
RES = (2200, 1240)

L, B = G.LOA, G.BEAM
DK = G.DECKS

# имя файла, положение камеры, точка взгляда, фокусное (мм) либо
# ("орто", ширина кадра в метрах), [разрешение], [показывать ли окружение]
VIEWS = [
    ("01_общий_вид",
     (L * 1.34, -B * 5.6, 48.0), (L * 0.45, 0.0, 7.0), 42.0),
    ("02_борт",
     (L * 0.50, -B * 14.0, 8.2), (L * 0.50, 0.0, 8.2), ("орто", 150.0),
     (2600, 620), False),
    ("03_корма",
     (-L * 0.34, -B * 2.3, 16.0), (L * 0.12, 0.0, 6.0), 40.0),
    ("04_нос_и_рубка",
     (L * 1.30, B * 2.3, 21.0), (L * 0.86, 0.0, 10.0), 48.0),
    ("05_шлюпочный_променад",
     (L * 0.28, B * 0.40, DK["шлюпочная"] + 1.62),
     (L * 0.85, B * 0.40, DK["шлюпочная"] + 1.05), 24.0),
    ("06_солнечная_палуба",
     (L * 0.36, -B * 0.24, DK["солнечная"] + 1.62),
     (L * 0.84, 0.0, DK["солнечная"] + 1.15), 22.0),
    ("07_главная_палуба_променад",
     (L * 0.24, B * 0.44, DK["главная"] + 1.62),
     (L * 0.80, B * 0.42, DK["главная"] + 1.10), 24.0),
    ("08_вид_сверху",
     (L * 0.50, 0.0, 120.0), (L * 0.50, 0.0, 6.0), ("орто", 150.0),
     (2600, 420), False),
    ("09_у_набережной",
     (L * 0.98, -B * 2.5, 5.2), (L * 0.12, B * 0.10, 8.0), 32.0),
]

def _hide_env():
    """Убрать набережную и воду: на бортовой проекции и виде сверху нужен
    только пароход, а не дома за ним."""
    hidden = []
    objs = []
    c = bpy.data.collections.get("60_Окружение")
    if c:
        objs += list(c.objects)
    o = bpy.data.objects.get("вода")
    if o:
        objs.append(o)
    for o in objs:
        if o.type == "MESH" and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    return hidden


def _cam(name, loc, tgt, lens):
    d = bpy.data.cameras.new(name)
    if isinstance(lens, tuple):
        d.type = "ORTHO"
        d.ortho_scale = lens[1]
    else:
        d.lens = lens
    d.sensor_width = 36.0
    d.clip_start = 0.05
    d.clip_end = 900.0
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(o)
    return o


def render_views(only=None, verbose=True):
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    keep = (sc.camera, sc.render.filepath, sc.render.resolution_x,
            sc.render.resolution_y, sc.render.resolution_percentage,
            sc.render.image_settings.file_format,
            getattr(sc.cycles, "samples", None), sc.render.engine)
    keep_view = (sc.view_settings.view_transform, sc.view_settings.look,
                 sc.view_settings.exposure)
    made = []
    try:
        sc.render.engine = "CYCLES"
        sc.cycles.device = "GPU"
        sc.cycles.samples = SAMPLES
        sc.cycles.use_denoising = True
        sc.render.resolution_x, sc.render.resolution_y = RES
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = 92
        # тонирование под судовую сцену: солнце подобрано под AgX и -3.1 EV,
        # при Standard и нулевой экспозиции кадр выбивается в белое
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.exposure = EXPOSURE
        for look in ("AgX - Medium High Contrast", "AgX - Base Contrast", "None"):
            try:
                sc.view_settings.look = look
                break
            except TypeError:
                continue
        for item in VIEWS:
            name, loc, tgt, lens = item[:4]
            if only and name not in only:
                continue
            res = item[4] if len(item) > 4 else RES
            env_on = item[5] if len(item) > 5 else True
            sc.render.resolution_x, sc.render.resolution_y = res
            hidden = [] if env_on else _hide_env()
            cam = _cam("_вид_" + name, loc, tgt, lens)
            sc.camera = cam
            p = os.path.join(OUT, name + ".jpg")
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            bpy.data.objects.remove(cam, do_unlink=True)
            for o in hidden:
                o.hide_render = False
            made.append(p)
            if verbose:
                print(name, "готово")
    finally:
        (sc.camera, sc.render.filepath, sc.render.resolution_x,
         sc.render.resolution_y, sc.render.resolution_percentage,
         sc.render.image_settings.file_format, smp, eng) = keep
        sc.render.engine = eng
        if smp is not None:
            sc.cycles.samples = smp
        # Сцена остаётся в судовом тонировании: солнце и материалы подобраны
        # под AgX и -3.1 EV. Возврат к тому, что было, только если это тоже
        # AgX — иначе следующий кадр из окна Blender снова выбьется в белое.
        if keep_view[0] == "AgX":
            (sc.view_settings.view_transform, sc.view_settings.look,
             sc.view_settings.exposure) = keep_view
    return made
