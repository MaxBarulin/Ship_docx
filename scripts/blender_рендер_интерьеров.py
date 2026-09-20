# -*- coding: utf-8 -*-
r"""Рендеры общественных помещений.

Камера ставится не «на глаз», а от зоны общего расположения: берётся
участок палубы из gorizont_ga, камера встаёт у его кормовой переборки на
высоте глаз и смотрит вдоль помещения. Подвинулась переборка — подвинулся
и кадр.

Подволок остаётся на месте: если его снять, в зал бьёт небо, кадр
выбивается в белое, а пассажиры с верхней палубы повисают в воздухе.
Вместо этого под подволоком ставятся мягкие источники — ровно так и
выглядит освещённый зал.

    exec(open(r"E:\Ship_docx\scripts\blender_рендер_интерьеров.py", encoding="utf-8").read())
    render_rooms()
"""
import bpy, os, sys, math
from mathutils import Vector

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont as G

OUT = r"E:\Ship_docx\renders\горизонт_2026\интерьеры"
SAMPLES = 150
RES = (2000, 1250)
EYE = 1.62

# файл, палуба, зона общего расположения, доля длины для камеры и цели, объектив
ROOMS = [
    ("1_главный_ресторан", "главная", "Главный ресторан", 0.06, 0.92, 20.0),
    ("2_театр_лаунж", "главная", "Театр-лаунж, вечером — ночной клуб",
     0.05, 0.94, 20.0),
    ("3_бар_лаунж", "шлюпочная", "Бар и лаунж-зона", 0.06, 0.92, 20.0),
    ("4_лобби_и_ресепшен", "главная",
     "Лобби-атриум, ресепшен, медпункт, изолятор, бутик", 0.05, 0.94, 20.0),
    ("5_бистро", "главная", "Бистро на 60 мест", 0.08, 0.90, 22.0),
    ("6_спа_и_фитнес", "верхняя", "Спа-комплекс", 0.07, 0.92, 21.0),
    ("7_носовой_салон", "верхняя", "Носовой панорамный салон",
     0.10, 0.90, 24.0),
]


def _zone(deck, name):
    from lib import gorizont_ga as GA
    for z in GA.DECKS.get(deck, []):
        if z[3] == name:
            return z[0], z[1]
    return None


def _light(loc, energy, size, col=(1.0, 0.93, 0.85), up=False, size_y=None):
    d = bpy.data.lights.new("_св", "AREA")
    d.energy = energy
    d.color = col
    d.size = size
    d.size_y = size if size_y is None else size_y
    o = bpy.data.objects.new("_св", d)
    o.location = loc
    if up:
        o.rotation_euler = (0.0, 0.0, 0.0)
        bpy.context.scene.collection.objects.link(o)
        return o
    o.rotation_euler = (math.radians(180), 0, 0)
    bpy.context.scene.collection.objects.link(o)
    return o


def render_rooms(only=None, verbose=True):
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    keep = (sc.camera, sc.render.filepath, sc.render.resolution_x,
            sc.render.resolution_y, sc.render.image_settings.file_format,
            getattr(sc.cycles, "samples", None), sc.render.engine,
            sc.view_settings.view_transform, sc.view_settings.look,
            sc.view_settings.exposure)
    made = []
    # солнце приглушаем на время интерьеров: иначе окна выбиваются в белое,
    # а по подволоку идут жёсткие полосы теней от простенков
    suns = [(o, o.data.energy) for o in bpy.data.objects
            if o.type == "LIGHT" and o.data.type == "SUN"]
    for o, e in suns:
        o.data.energy = e * 0.42
    try:
        sc.render.engine = "CYCLES"
        sc.cycles.device = "GPU"
        sc.cycles.samples = SAMPLES
        sc.cycles.use_denoising = True
        sc.render.resolution_x, sc.render.resolution_y = RES
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "JPEG"
        sc.render.image_settings.quality = 92
        sc.view_settings.view_transform = "AgX"
        sc.view_settings.exposure = -0.55
        for look in ("AgX - Medium High Contrast", "AgX - Base Contrast"):
            try:
                sc.view_settings.look = look
                break
            except TypeError:
                continue
        for name, deck, zone, a, b, lens in ROOMS:
            if only and name not in only:
                continue
            zz = _zone(deck, zone)
            if zz is None:
                continue
            x0, x1 = zz
            zd = G.DECKS[deck]
            L = x1 - x0
            d = bpy.data.cameras.new("_кам")
            d.lens = lens
            d.sensor_width = 36.0
            d.clip_start = 0.05
            cam = bpy.data.objects.new("_кам", d)
            cam.location = (x0 + L * a, -1.10, zd + EYE)
            tgt = Vector((x0 + L * b, 0.60, zd + 1.05))
            cam.rotation_euler = (tgt - Vector(cam.location)).to_track_quat(
                "-Z", "Y").to_euler()
            sc.collection.objects.link(cam)
            sc.camera = cam
            # подволок не снимаем: иначе в зал бьёт небо, а пассажиры с
            # верхней палубы повисают в воздухе. Вместо этого под подволок
            # идёт ряд мягких панелей по всей длине зала, а не три пятна:
            # от трёх источников подволок оставался в пятнах и провалах.
            n_l = max(3, int(L / 3.2))
            lights = []
            for i in range(n_l):
                xx = x0 + L * (i + 0.5) / n_l
                for y in (-3.4, 0.0, 3.4):
                    lights.append(_light((xx, y, zd + 1.98), 130.0, 2.6))
                # слабая подсветка подволока: иначе он уходит в грязь
                lights.append(_light((xx, 0.0, zd + 1.55), 26.0, 3.0,
                                     col=(1.0, 0.95, 0.9), up=True))
            p = os.path.join(OUT, name + ".jpg")
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            for o in lights:
                bpy.data.objects.remove(o, do_unlink=True)
            bpy.data.objects.remove(cam, do_unlink=True)
            made.append(p)
            if verbose:
                print(name, "готово")
    finally:
        for o, e in suns:
            o.data.energy = e
        (sc.camera, sc.render.filepath, sc.render.resolution_x,
         sc.render.resolution_y, sc.render.image_settings.file_format,
         smp, eng, vt, lk, ex) = keep
        sc.render.engine = eng
        if smp is not None:
            sc.cycles.samples = smp
        sc.view_settings.view_transform = vt
        sc.view_settings.look = lk
        sc.view_settings.exposure = ex
    return made
