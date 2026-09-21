# -*- coding: utf-8 -*-
r"""Сырые планы ярусов: вид сверху со срезом на 2,05 м над настилом.

Ортокамера смотрит вниз, а всё, что выше секущей плоскости, прячется
на время кадра: иначе подволок и вышележащая палуба закрывают помещения.
Подписи, зоны и масштабную линейку накладывает scripts/планы_палуб.py.

    exec(open(r"E:\Ship_docx\scripts\blender_рендер_планов.py", encoding="utf-8").read())
    render_plans()
"""
import bpy, os, sys

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont as G

OUT = r"F:\Temp\claude\gor\планы_raw"
ORTHO = 148.0          # ширина кадра, м — совпадает с планы_палуб.ORTHO
XC = 69.5              # центр кадра по длине
RES = (2800, 560)
SAMPLES = 64
CUT = 2.05             # секущая плоскость над настилом

PLANS = [
    ("0_трюм_второе_дно", 0.00, 1.30),
    ("1_первая_палуба", 1.40, CUT),
    ("2_главная_палуба", 4.20, CUT),
    ("3_верхняя_палуба", 7.00, CUT),
    ("4_шлюпочная_палуба", 9.80, CUT),
    ("5_солнечная_палуба", 12.60, CUT),
]
SKIP = ("20_Эталоны_кают", "60_Окружение")


def _hide_env():
    """Убрать из кадра воду и набережную: на плане нужен только корпус."""
    hidden = []
    objs = []
    for cn in ("60_Окружение",):
        c = bpy.data.collections.get(cn)
        if c:
            objs += list(c.objects)
    # вода лежит прямо в сцене, а не в коллекции окружения
    for n in ("вода", "море", "река"):
        o = bpy.data.objects.get(n)
        if o:
            objs.append(o)
    for o in objs:
        if o.type == "MESH" and not o.hide_render:
            o.hide_render = True
            hidden.append(o)
    return hidden


def _hide_above(z_cut):
    """Спрятать от рендера всё, что целиком выше секущей плоскости."""
    hidden = []
    for c in bpy.data.collections:
        if c.name in SKIP:
            continue
        for o in c.objects:
            if o.type != "MESH" or o.hide_render or not o.data.vertices:
                continue
            mw = o.matrix_world
            zmin = min((mw @ v.co).z for v in o.data.vertices)
            if zmin > z_cut - 0.01:
                o.hide_render = True
                hidden.append(o)
    return hidden


def _plan_filled(path, thr=0.02):
    """Доля непрозрачных пикселей: пустой план так и останется незамеченным.

    Первая палуба уходила в рендер пустой — выноски показывали в никуда,
    потому что палубный настил главной палубы скрыть как объект нельзя: его
    минимум по z лежит на днище. Теперь срез делает плоскость отсечения
    камеры, а доля заливки это подтверждает.
    """
    img = bpy.data.images.load(path)
    try:
        px = list(img.pixels)
        n = len(px) // 4
        full = sum(1 for k in range(n) if px[k * 4 + 3] > 0.35)
        return full / float(n)
    finally:
        bpy.data.images.remove(img)


def render_plans(only=None, verbose=True, check=True):
    """Планы ярусов: срез плоскостью отсечения, плоская заливка без теней."""
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    keep = (sc.camera, sc.render.filepath, sc.render.resolution_x,
            sc.render.resolution_y, sc.render.image_settings.file_format,
            sc.render.engine, sc.view_settings.view_transform,
            sc.view_settings.look, sc.view_settings.exposure,
            sc.render.film_transparent,
            sc.render.image_settings.color_mode)
    sh = sc.display.shading
    keep_sh = (sh.light, sh.color_type, sh.show_cavity,
               sh.show_object_outline, sh.show_shadows,
               tuple(sh.object_outline_color),
               sc.display.render_aa)
    d = bpy.data.cameras.new("_планкам")
    d.type = "ORTHO"
    d.ortho_scale = ORTHO
    cam = bpy.data.objects.new("_планкам", d)
    sc.collection.objects.link(cam)
    made, thin = [], []
    env = []
    try:
        # Workbench с плоским светом: на плане нужен читаемый контур, а не
        # светотень. Тени от солнца забивали планы и сжигали палубу.
        sc.render.engine = "BLENDER_WORKBENCH"
        sh.light = "FLAT"
        sh.color_type = "MATERIAL"
        sh.show_cavity = False
        sh.show_shadows = False
        sh.show_object_outline = True
        sh.object_outline_color = (0.10, 0.11, 0.13)
        sc.display.render_aa = "16"
        sc.render.resolution_x, sc.render.resolution_y = RES
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGBA"
        sc.render.film_transparent = True
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.exposure = 0.0
        try:
            sc.view_settings.look = "None"
        except TypeError:
            pass
        sc.camera = cam
        cam.rotation_euler = (0.0, 0.0, 0.0)
        env = _hide_env()
        for name, z_deck, cut in PLANS:
            if only and name not in only:
                continue
            h = 60.0
            cam.location = (XC, 0.0, z_deck + h)
            # срез: от секущей плоскости вниз до самого настила яруса
            d.clip_start = h - cut
            d.clip_end = h + 0.35
            p = os.path.join(OUT, name + ".png")
            sc.render.filepath = p
            bpy.ops.render.render(write_still=True)
            made.append(p)
            fill = _plan_filled(p) if check else None
            if fill is not None and fill < 0.08:
                thin.append((name, round(fill, 3)))
            if verbose:
                print(name, "готово" if fill is None
                      else "заливка %.1f%%" % (fill * 100))
        if thin:
            print("!! планы почти пустые:", thin)
    finally:
        for o in env:
            o.hide_render = False
        bpy.data.objects.remove(cam, do_unlink=True)
        (sc.camera, sc.render.filepath, sc.render.resolution_x,
         sc.render.resolution_y, sc.render.image_settings.file_format,
         eng, vt, lk, ex, tr, cm) = keep
        sc.render.film_transparent = tr
        sc.render.image_settings.color_mode = cm
        sc.render.engine = eng
        sc.view_settings.view_transform = vt
        sc.view_settings.look = lk
        sc.view_settings.exposure = ex
        (sh.light, sh.color_type, sh.show_cavity, sh.show_object_outline,
         sh.show_shadows, oc, sc.display.render_aa) = keep_sh
        sh.object_outline_color = oc
    return made


SEC_OUT = r"F:\Temp\claude\gor\схемы_raw"
SEC_ORTHO = 146.0
SEC_RES = (2400, 470)


def render_section(verbose=True):
    """Сырой продольный разрез по ДП: ближняя половина судна отсечена."""
    os.makedirs(SEC_OUT, exist_ok=True)
    sc = bpy.context.scene
    keep = (sc.camera, sc.render.filepath, sc.render.resolution_x,
            sc.render.resolution_y, sc.render.image_settings.file_format,
            getattr(sc.cycles, "samples", None), sc.render.engine,
            sc.view_settings.view_transform, sc.view_settings.look,
            sc.view_settings.exposure, sc.render.film_transparent,
            sc.render.image_settings.color_mode)
    d = bpy.data.cameras.new("_разрезкам")
    d.type = "ORTHO"
    d.ortho_scale = SEC_ORTHO
    d.clip_start = 200.0          # ближняя плоскость ровно по ДП
    d.clip_end = 400.0
    cam = bpy.data.objects.new("_разрезкам", d)
    cam.location = (XC, -200.0, 6.6)
    cam.rotation_euler = (1.5707963, 0.0, 0.0)
    sc.collection.objects.link(cam)
    try:
        # разрез снимаем Workbench-ом: внутри корпуса нет света, и на Cycles
        # помещения ниже первой палубы уходят в чёрное
        sc.render.engine = "BLENDER_WORKBENCH"
        sh = sc.display.shading
        sh.light = "STUDIO"
        sh.color_type = "MATERIAL"
        sh.show_cavity = True
        sc.render.resolution_x, sc.render.resolution_y = SEC_RES
        sc.render.resolution_percentage = 100
        sc.render.image_settings.file_format = "PNG"
        sc.render.image_settings.color_mode = "RGBA"
        sc.render.film_transparent = True
        sc.view_settings.view_transform = "Standard"
        sc.view_settings.exposure = 0.0
        try:
            sc.view_settings.look = "None"
        except TypeError:
            pass
        sc.camera = cam
        env = _hide_env()
        p = os.path.join(SEC_OUT, "разрез.png")
        sc.render.filepath = p
        bpy.ops.render.render(write_still=True)
        if verbose:
            print("разрез готов")
        return p
    finally:
        for o in env:
            o.hide_render = False
        bpy.data.objects.remove(cam, do_unlink=True)
        (sc.camera, sc.render.filepath, sc.render.resolution_x,
         sc.render.resolution_y, sc.render.image_settings.file_format,
         smp, eng, vt, lk, ex, tr, cm) = keep
        sc.render.engine = eng
        if smp is not None:
            sc.cycles.samples = smp
        sc.view_settings.view_transform = vt
        sc.view_settings.look = lk
        sc.view_settings.exposure = ex
        sc.render.film_transparent = tr
        sc.render.image_settings.color_mode = cm
