# -*- coding: utf-8 -*-
r"""Контактный лист помещений: три ракурса на каждое, всё разом.

    import blender_контактный_лист as K
    K.sheet()

Один «красивый» рендер комнаты стоит полторы минуты и показывает один угол.
Брак масштаба «кресла висят», «стол без ножек», «диван смотрит в переборку»
виден и на превью 640 px — если смотреть на все помещения сразу и с разных
сторон. Лист снимается Workbench-ом за десяток секунд и служит визуальным
контролем перед чистовым рендером.

Ракурсы: от кормовой переборки вдоль зала, от носовой переборки обратно и
сверху под 45° — брак в плане виден именно сверху.
"""

import bpy, os, sys, math

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)

from mathutils import Vector
from lib import gorizont as G
from lib import gorizont_ga as GA
from lib import gorizont_rooms as R

OUT = r"F:\Temp\claude\gor\контакт"
TILE = (640, 400)
EYE = 1.62


def _rooms():
    """Помещения из таблицы обстановки плюс их габарит по длине."""
    out = []
    for obj, (deck, x0, x1, fn, pref) in R.ROOMS.items():
        out.append((obj.replace("мебель_", ""), deck, x0, x1))
    return sorted(out, key=lambda r: (G.DECKS[r[1]], r[2]))


def _shot(sc, cam, d, loc, tgt, lens, ortho=None, clip=0.05):
    d.type = "ORTHO" if ortho else "PERSP"
    if ortho:
        d.ortho_scale = ortho
    d.lens = lens
    d.clip_start = clip
    cam.location = loc
    cam.rotation_euler = (Vector(tgt) - Vector(loc)).to_track_quat(
        "-Z", "Y").to_euler()
    sc.camera = cam


def sheet(only=None, verbose=True):
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    keep = (sc.camera, sc.render.filepath, sc.render.resolution_x,
            sc.render.resolution_y, sc.render.engine,
            sc.render.image_settings.file_format,
            sc.view_settings.view_transform, sc.view_settings.exposure,
            sc.render.film_transparent)
    sh = sc.display.shading
    keep_sh = (sh.light, sh.color_type, sh.show_cavity,
               sh.show_object_outline, sh.show_shadows, sc.display.render_aa)
    d = bpy.data.cameras.new("_контакт")
    d.sensor_width = 36.0
    d.clip_start = 0.05
    cam = bpy.data.objects.new("_контакт", d)
    sc.collection.objects.link(cam)
    made = []
    try:
        sc.render.engine = "BLENDER_WORKBENCH"
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_cavity = True
        sh.show_shadows = False
        sh.show_object_outline = False
        sc.display.render_aa = "8"
        sc.render.resolution_x, sc.render.resolution_y = TILE
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        sc.render.film_transparent = False
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.exposure = 0.0
        for name, deck, x0, x1 in _rooms():
            if only and name not in only:
                continue
            z = G.DECKS[deck]
            L = x1 - x0
            views = (
                ("а", (x0 + L * 0.06, -1.2, z + EYE),
                 (x0 + L * 0.9, 0.5, z + 1.0), 20.0),
                ("б", (x1 - L * 0.06, 1.2, z + EYE),
                 (x1 - L * 0.9, -0.5, z + 1.0), 20.0),
                # третий ракурс — план помещения: брак расстановки (стул
                # впритык к переборке, стол без прохода) виден только сверху
                ("в", (x0 + L * 0.5, 0.0, z + 30.0),
                 (x0 + L * 0.5, 0.0, z), 20.0,
                 max(L, 16.0), 30.0 - 2.05),
            )
            for v in views:
                tag, loc, tgt, lens = v[0], v[1], v[2], v[3]
                _shot(sc, cam, d, loc, tgt, lens,
                      ortho=v[4] if len(v) > 4 else None,
                      clip=v[5] if len(v) > 5 else 0.05)
                p = os.path.join(OUT, "%s_%s.png" % (name, tag))
                sc.render.filepath = p
                bpy.ops.render.render(write_still=True)
                made.append(p)
            if verbose:
                print(name, "снято")
    finally:
        bpy.data.objects.remove(cam, do_unlink=True)
        (sc.camera, sc.render.filepath, sc.render.resolution_x,
         sc.render.resolution_y, sc.render.engine,
         sc.render.image_settings.file_format, vt, ex, tr) = keep
        sc.view_settings.view_transform = vt
        sc.view_settings.exposure = ex
        sc.render.film_transparent = tr
        (sh.light, sh.color_type, sh.show_cavity, sh.show_object_outline,
         sh.show_shadows, sc.display.render_aa) = keep_sh
    return made
