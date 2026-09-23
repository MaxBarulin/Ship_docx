# -*- coding: utf-8 -*-
r"""Сцена под рендер - небо, солнце, вода, цветокоррекция.

    import blender_сцена as С
    С.построить()

Отдельный модуль, потому что сцена - это не модель. Судно собирается с
нуля скриптами, и если освещение живёт внутри .blend, то при пересборке
в чистом файле рендер выходит чёрным. Здесь всё задаётся числами.

Солнце и небо связаны - положение лампы берётся из тех же азимута и высоты,
что стоят в Sky Texture. Иначе блики на воде идут с одной стороны, а тени
на судне - с другой, и кадр разваливается, хотя каждый элемент по
отдельности выглядит правильно.

Высота солнца 24° - не «красиво», а функционально - при высоком солнце
графитовый борт становится плоским пятном, а вся пластика надстройки
(завал борта, утопленная оконная лента, обтекатели колёс) читается только
скользящим светом.
"""
import bpy, math, sys, os

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)

from lib import gorizont as G
from lib import gorizont_style as S

ВЫСОТА_СОЛНЦА = 24.0       # угол над горизонтом, градусов
АЗИМУТ = 138.0             # с кормы-правого борта: светит в скулу
ЭКСПОЗИЦИЯ = -3.1
ВОДА_РАЗМЕР = 60000.0     # до горизонта: при 3 км из-под края воды проступал тёмный низ неба


def _задать(нода, **поля):
    """Проставить только те свойства, которые есть в этой версии Blender."""
    for k, v in поля.items():
        if hasattr(нода, k):
            setattr(нода, k, v)


def _очистить(нода_дерево):
    for n in list(нода_дерево.nodes):
        нода_дерево.nodes.remove(n)


def небо():
    мир = bpy.data.worlds.get("Горизонт_небо") or bpy.data.worlds.new("Горизонт_небо")
    мир.use_nodes = True
    nt = мир.node_tree
    _очистить(nt)
    sky = nt.nodes.new("ShaderNodeTexSky")
    # Тип неба называется по-разному в разных версиях: в 4.x это NISHITA, в
    # 5.2 та же модель разложена на SINGLE_SCATTERING/MULTIPLE_SCATTERING.
    # Берётся первый доступный из списка предпочтений, а не константа, -
    # иначе скрипт падает при смене версии Blender.
    _типы = [i.identifier for i in
             sky.bl_rna.properties["sky_type"].enum_items]
    for t in ("MULTIPLE_SCATTERING", "NISHITA", "SINGLE_SCATTERING",
              "HOSEK_WILKIE"):
        if t in _типы:
            sky.sky_type = t
            break
    _задать(sky, sun_elevation=math.radians(ВЫСОТА_СОЛНЦА),
            sun_rotation=math.radians(АЗИМУТ),
            sun_intensity=0.6,   # диск солнца даёт лампа, небо - рассеянный свет
            altitude=80.0, air_density=1.1,
            dust_density=1.6)    # лёгкая дымка: без неё дали слишком синие
    bg = nt.nodes.new("ShaderNodeBackground")
    bg.inputs["Strength"].default_value = 1.0
    out = nt.nodes.new("ShaderNodeOutputWorld")
    nt.links.new(sky.outputs[0], bg.inputs[0])
    nt.links.new(bg.outputs[0], out.inputs[0])
    bpy.context.scene.world = мир
    return мир


def солнце():
    d = bpy.data.lights.get("Солнце") or bpy.data.lights.new("Солнце", "SUN")
    d.energy = 3.4
    d.angle = math.radians(1.2)
    d.color = (1.0, 0.96, 0.90)
    o = bpy.data.objects.get("Солнце")
    if o is None:
        o = bpy.data.objects.new("Солнце", d)
        bpy.context.scene.collection.objects.link(o)
    o.data = d
    # Та же пара углов, что у Sky Texture: свет и небо обязаны совпадать.
    el, az = math.radians(ВЫСОТА_СОЛНЦА), math.radians(АЗИМУТ)
    o.rotation_euler = (math.pi / 2.0 - el, 0.0, az + math.pi / 2.0)
    o.location = (G.LOA / 2.0, 0.0, 200.0)
    return o


def вода():
    имя = "вода"
    ст = bpy.data.objects.get(имя)
    if ст is not None:
        bpy.data.objects.remove(ст, do_unlink=True)
    me = bpy.data.meshes.new(имя)
    r = ВОДА_РАЗМЕР
    me.from_pydata([(G.LOA / 2 - r, -r, G.DRAFT), (G.LOA / 2 + r, -r, G.DRAFT),
                    (G.LOA / 2 + r, r, G.DRAFT), (G.LOA / 2 - r, r, G.DRAFT)],
                   [], [[0, 1, 2, 3]])
    me.update()
    o = bpy.data.objects.new(имя, me)
    bpy.context.scene.collection.objects.link(o)

    m = bpy.data.materials.get("гор_вода") or bpy.data.materials.new("гор_вода")
    m.use_nodes = True
    nt = m.node_tree
    _очистить(nt)
    p = nt.nodes.new("ShaderNodeBsdfPrincipled")
    # Волжская вода не прозрачная: дно не просвечивает, работает отражение
    # и мутный зелёно-серый цвет. Прозрачность здесь дала бы чёрное зеркало.
    p.inputs["Base Color"].default_value = (0.020, 0.034, 0.038, 1.0)
    p.inputs["Roughness"].default_value = 0.085
    if "IOR" in p.inputs:
        p.inputs["IOR"].default_value = 1.333
    noise = nt.nodes.new("ShaderNodeTexNoise")
    noise.inputs["Scale"].default_value = 9.0
    noise.inputs["Detail"].default_value = 8.0
    noise.inputs["Roughness"].default_value = 0.62
    bump = nt.nodes.new("ShaderNodeBump")
    bump.inputs["Strength"].default_value = 0.09
    bump.inputs["Distance"].default_value = 0.04
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    nt.links.new(noise.outputs["Fac"], bump.inputs["Height"])
    nt.links.new(bump.outputs["Normal"], p.inputs["Normal"])
    nt.links.new(p.outputs[0], out.inputs[0])
    o.data.materials.append(m)
    return o


def настройки(движок="CYCLES", сэмплов=96):
    sc = bpy.context.scene
    sc.render.engine = движок
    if движок == "CYCLES":
        sc.cycles.samples = сэмплов
        sc.cycles.use_denoising = True
        sc.cycles.max_bounces = 6
        sc.cycles.transmission_bounces = 6
        try:
            sc.cycles.device = "GPU"
        except Exception:
            pass
    sc.render.film_transparent = False
    sc.view_settings.view_transform = "AgX"
    # Название пресета контраста меняется от версии к версии; берётся
    # первое подходящее из фактического списка.
    _looks = [i.identifier for i in
              sc.view_settings.bl_rna.properties["look"].enum_items]
    for l in ("AgX - Medium Contrast", "AgX - Base Contrast",
              "AgX - Medium High Contrast", "None"):
        if l in _looks:
            sc.view_settings.look = l
            break
    sc.view_settings.exposure = ЭКСПОЗИЦИЯ
    sc.render.image_settings.file_format = "JPEG"
    sc.render.image_settings.quality = 92
    return sc


def построить(verbose=True):
    небо()
    солнце()
    вода()
    sc = настройки()
    if verbose:
        print("Сцена - солнце %.0f° / азимут %.0f°, вода на z=%.2f, %s, %d сэмплов"
              % (ВЫСОТА_СОЛНЦА, АЗИМУТ, G.DRAFT, sc.render.engine,
                 sc.cycles.samples if sc.render.engine == "CYCLES" else 0))
    return sc


if __name__ == "__main__":
    построить()
