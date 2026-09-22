# -*- coding: utf-8 -*-
r"""Внешние виды и палубные ракурсы судна.

Камеры заданы числами от главных размерений, а не расставлены руками:
поменялась длина или высота яруса — ракурс переедет вместе с судном.
Рендер идёт в судовой сцене, поэтому солнце, небо и вода те же, что и
в остальных кадрах; настройки сцены скрипт возвращает как было.

    import blender_рендер_видов as РВ
    РВ.render_views()                       # внешние виды 01…08
    РВ.render_views(views=blender_причал.ВИДЫ)   # или через blender_причал.виды()

Кадры у причала (10…12) живут в `blender_причал.ВИДЫ`: там же сцена, ради
которой они снимаются. Рендер — GPU, если он есть, иначе процессор.
"""
import bpy, os, sys, math
from mathutils import Vector


def _корень():
    for к in (os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if "__file__" in globals() else None,
              os.environ.get("GORIZONT_ROOT"), r"E:\Ship_docx"):
        if к and os.path.isdir(os.path.join(к, "src", "lib")):
            return к
    raise RuntimeError("Не найден корень репозитория")


ROOT = _корень()
if os.path.join(ROOT, "src") not in sys.path:
    sys.path.insert(0, os.path.join(ROOT, "src"))
from lib import gorizont as G

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "виды")
SAMPLES = 160
EXPOSURE = -3.1
RES = (2200, 1240)

L, B = G.LOA, G.BEAM
DK = G.DECKS

# имя файла, положение камеры, точка взгляда, фокусное (мм) либо
# ("орто", ширина кадра в метрах), [разрешение], [показывать ли окружение]
VIEWS = [
    ("01_общий_вид",
     (L * 1.34, -B * 5.6, 44.0), (L * 0.50, 0.0, 6.5), 40.0),
    ("02_борт",
     (L * 0.50, -B * 14.0, 6.0), (L * 0.50, 0.0, 6.0), ("орто", 140.0),
     (2600, 620), False),
    ("03_корма_и_колесо",
     (-L * 0.24, -B * 1.9, 11.0), (L * 0.16, 0.0, 4.2), 42.0),
    ("04_нос_и_рубка",
     (L * 1.26, B * 2.1, 17.0), (L * 0.84, 0.0, 7.6), 48.0),
    ("05_прогулочная_палуба",
     (L * 0.18, 7.60, DK["главная"] + 1.62),
     (L * 0.82, 7.20, DK["главная"] + 1.15), 24.0),
    ("06_солнечная_палуба",
     (L * 0.22, -1.30, DK["солнечная"] + 1.62),
     (L * 0.74, 1.00, DK["солнечная"] + 1.10), 24.0),
    ("07_вид_сверху",
     (L * 0.50, 0.0, 130.0), (L * 0.50, 0.0, 5.0), ("орто", 140.0),
     (2600, 430), False),
    ("08_три_четверти_с_кормы",
     (-L * 0.42, B * 4.4, 26.0), (L * 0.42, 0.0, 6.0), 42.0),
]

# виды, где судно обязано быть в кадре целиком; корма и нос — крупные
# планы оконечностей, их подгонять по всей длине нельзя
FIT = ("01_общий_вид", "08_три_четверти_с_кормы")


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
    d.clip_end = 80000.0      # вода и дальний берег до горизонта; при 900 м под горизонтом шла тёмная полоса
    o = bpy.data.objects.new(name, d)
    o.location = loc
    o.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    bpy.context.scene.collection.objects.link(o)
    return o


def _ship_points():
    """Опорные точки габарита судна для проверки кадра."""
    pts = []
    for x in (0.0, L * 0.25, L * 0.5, L * 0.75, L):
        for y in (-B / 2, 0.0, B / 2):
            for z in (0.0, G.DECKS["солнечная"], G.WHEELHOUSE_ROOF):
                pts.append(Vector((x, y, z)))
    return pts


def _autofit(sc, cam, margin=0.05, tries=8):
    """Подогнать объектив так, чтобы судно влезло в кадр целиком.

    Кадр подбирался на глаз, и на общем виде и у набережной корма уходила
    за край. Теперь объектив ужимается по габариту судна: точки габарита
    проецируются в кадр, и фокусное делится, пока самая дальняя не войдёт
    с запасом `margin`.
    """
    from bpy_extras.object_utils import world_to_camera_view
    dg = bpy.context.evaluated_depsgraph_get()
    pts = _ship_points()
    lim = 0.5 * (1.0 - margin)
    for _ in range(tries):
        dg.update()
        us = [world_to_camera_view(sc, cam, p) for p in pts]
        us = [u for u in us if u.z > 0.0]
        if not us:
            return None
        mx = max(max(abs(u.x - 0.5), abs(u.y - 0.5)) for u in us)
        if mx <= lim:
            return mx
        cam.data.lens *= lim / mx
    return mx


def _устройство(sc):
    """GPU, если Cycles его видит; иначе процессор (облачная сессия, фоновый Blender)."""
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.get_devices()
        if any(d.type != "CPU" for d in prefs.devices):
            sc.cycles.device = "GPU"
            return "GPU"
    except Exception:
        pass
    sc.cycles.device = "CPU"
    return "CPU"


def render_views(only=None, verbose=True, views=None, samples=None, out=None):
    out = out or OUT
    os.makedirs(out, exist_ok=True)
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
        _устройство(sc)
        sc.cycles.samples = samples or SAMPLES
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
        for item in (views or VIEWS):
            name, loc, tgt, lens = item[:4]
            if only and name not in only:
                continue
            res = item[4] if len(item) > 4 else RES
            env_on = item[5] if len(item) > 5 else True
            sc.render.resolution_x, sc.render.resolution_y = res
            hidden = [] if env_on else _hide_env()
            cam = _cam("_вид_" + name, loc, tgt, lens)
            sc.camera = cam
            if not isinstance(lens, tuple) and name in FIT:
                mx = _autofit(sc, cam)
                if verbose and mx is not None:
                    print("   %s: объектив %.1f мм, габарит занимает %.0f%% кадра"
                          % (name, cam.data.lens, mx * 200))
            p = os.path.join(out, name + ".jpg")
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
