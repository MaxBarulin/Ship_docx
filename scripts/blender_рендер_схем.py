# -*- coding: utf-8 -*-
r"""Схемы: набор корпуса и взрыв-модель ярусов.

Набор снимается с прозрачной обшивкой — иначе видно борт, а не связи.
Взрыв-модель разносит ярусы по высоте: каждая коллекция сдвигается на
свою величину, кадр снимается, положение возвращается. Ничего в файле
после работы скрипта не меняется.

    exec(open(r"E:\Ship_docx\scripts\blender_рендер_схем.py", encoding="utf-8").read())
    render_schemes()
"""
import bpy, os, sys, math
from mathutils import Vector

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont as G

OUT = r"E:\Ship_docx\renders\горизонт_2026\схемы"
SAMPLES = 96
L, B = G.LOA, G.BEAM

# подъём коллекции во взрыв-модели, м
LEVELS = {"01_Корпус": 0.0, "40_Набор_корпуса": 0.0, "33_Машинное": 0.0,
          "34_Фундамент_очистки": 0.0,
          "03_Палубы": 16.0, "10_Каюты": 10.0, "30_Общественные": 10.0,
          "31_Мебель": 10.0, "32_Служебные": 10.0, "11_Трапы_и_лифты": 10.0,
          "02_Надстройка": 23.0, "04_Остекление": 23.0, "08_Устройства": 23.0,
          "05_Четвёртый_ярус": 32.0, "06_Спасательные_средства": 32.0,
          "07_Леера_и_оборудование": 32.0, "50_Детали": 32.0}
HIDE = ("60_Окружение", "20_Эталоны_кают")
# на схеме набора всё, кроме самого набора и механизмов, только мешает
FRAME_KEEP = ("40_Набор_корпуса", "33_Машинное", "34_Фундамент_очистки")


def _cam(name, loc, tgt, lens=50.0, ortho=None):
    d = bpy.data.cameras.new(name)
    if ortho:
        d.type = "ORTHO"
        d.ortho_scale = ortho
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


def _hide(names):
    hidden = []
    for cn in names:
        c = bpy.data.collections.get(cn)
        if not c:
            continue
        for o in c.objects:
            if o.type == "MESH" and not o.hide_render:
                o.hide_render = True
                hidden.append(o)
    o = bpy.data.objects.get("вода")
    if o and not o.hide_render:
        o.hide_render = True
        hidden.append(o)
    return hidden


def _keep_only(keep):
    """Спрятать всё, кроме перечисленных коллекций."""
    hidden = []
    for c in bpy.data.collections:
        if c.name in keep:
            continue
        for o in c.objects:
            if o.type == "MESH" and not o.hide_render:
                o.hide_render = True
                hidden.append(o)
    o = bpy.data.objects.get("вода")
    if o and not o.hide_render:
        o.hide_render = True
        hidden.append(o)
    return hidden


def _hide_shell():
    """Снять обшивку и борта надстройки: иначе виден борт, а не связи."""
    saved = []
    names = ["корпус", "фальшборт", "надстройка_цоколь_главная",
             "надстройка_карниз_главная", "надстройка_цоколь_верхняя",
             "надстройка_карниз_верхняя", "надстройка_простенки_главная",
             "надстройка_простенки_верхняя"]
    # полосы и щиты, которыми закрыты дыры в ограждении, — та же обшивка
    names += [o.name for o in bpy.data.objects
              if o.name.startswith("ограждение_")]
    for n in names:
        o = bpy.data.objects.get(n)
        if o:
            saved.append((o, o.hide_render))
            o.hide_render = True
    return saved


def _setup(sc, res, workbench=True):
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.render.image_settings.file_format = "PNG"
    sc.render.image_settings.color_mode = "RGBA"
    sc.render.film_transparent = True
    if workbench:
        sc.render.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_cavity = True
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.exposure = 0.0
        try:
            sc.view_settings.look = "None"
        except TypeError:
            pass
    else:
        sc.render.engine = "CYCLES"
        sc.cycles.device = "GPU"
        sc.cycles.samples = SAMPLES
        sc.cycles.use_denoising = True


def render_schemes(only=None, verbose=True):
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    keep = (sc.camera, sc.render.filepath, sc.render.resolution_x,
            sc.render.resolution_y, sc.render.image_settings.file_format,
            sc.render.image_settings.color_mode, sc.render.film_transparent,
            getattr(sc.cycles, "samples", None), sc.render.engine,
            sc.view_settings.view_transform, sc.view_settings.look,
            sc.view_settings.exposure)
    made = []
    try:
        # --- набор корпуса, общий вид и фрагмент
        if not only or "набор" in " ".join(only):
            # набор снимаем Cycles-ом: в Workbench все связи одного серого
            # цвета, а материалы набора различают днище, борт и палубу
            _setup(sc, (2600, 1100), workbench=False)
            hid = _keep_only(FRAME_KEEP)
            for name, cam_args in (
                ("набор_корпуса_общий",
                 dict(loc=(L * 0.95, -B * 4.2, 48.0), tgt=(L * 0.44, 0.0, 1.2),
                      lens=52.0)),
                ("набор_корпуса_фрагмент",
                 dict(loc=(L * 0.33, -B * 1.5, 13.0), tgt=(L * 0.52, 1.0, 1.0),
                      lens=42.0)),
            ):
                if only and name not in only:
                    continue
                cam = _cam("_схкам", **cam_args)
                sc.camera = cam
                p = os.path.join(OUT, name + ".png")
                sc.render.filepath = p
                bpy.ops.render.render(write_still=True)
                bpy.data.objects.remove(cam, do_unlink=True)
                made.append(p)
                if verbose:
                    print(name, "готово")
            for o in hid:
                o.hide_render = False

        # --- взрыв-модель
        if not only or "взрыв" in " ".join(only):
            _setup(sc, (2400, 1500))
            hid = _hide(HIDE)
            moved = []
            for cn, dz in LEVELS.items():
                c = bpy.data.collections.get(cn)
                if not c or dz == 0.0:
                    continue
                for o in c.objects:
                    moved.append((o, o.location.z))
                    o.location.z += dz
            bpy.context.view_layer.update()
            for name, cam_args in (
                ("взрыв_модель",
                 dict(loc=(L * 0.50, -B * 11.0, 26.0), tgt=(L * 0.50, 0.0, 26.0),
                      ortho=152.0)),
                ("взрыв_модель_3д",
                 dict(loc=(L * 1.55, -B * 7.0, 82.0), tgt=(L * 0.44, 0.0, 20.0),
                      lens=40.0)),
            ):
                if only and name not in only:
                    continue
                cam = _cam("_схкам", **cam_args)
                sc.camera = cam
                p = os.path.join(OUT, name + ".png")
                sc.render.filepath = p
                bpy.ops.render.render(write_still=True)
                bpy.data.objects.remove(cam, do_unlink=True)
                made.append(p)
                if verbose:
                    print(name, "готово")
            for o, z in moved:
                o.location.z = z
            for o in hid:
                o.hide_render = False
            bpy.context.view_layer.update()
    finally:
        (sc.camera, sc.render.filepath, sc.render.resolution_x,
         sc.render.resolution_y, sc.render.image_settings.file_format,
         sc.render.image_settings.color_mode, sc.render.film_transparent,
         smp, eng, vt, lk, ex) = keep
        sc.render.engine = eng
        if smp is not None:
            sc.cycles.samples = smp
        sc.view_settings.view_transform = vt
        sc.view_settings.look = lk
        sc.view_settings.exposure = ex
    return made
