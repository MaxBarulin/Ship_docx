# -*- coding: utf-8 -*-
r"""Узел ВГ-2026.46.00 «Фундамент-замок модуля (твистлок «ласточкин хвост»)» в Blender - сборка, взрыв-схема,
отливка корпуса со стержнем.

    import blender_фундамент as Ф
    Ф.виды()        # renders/горизонт_2026/узел/46_01_сборка.png, 46_02_взрыв.png, 46_03_отливка_стержень.png

Отдельная сцена «Фундамент» - судовая сцена не трогается. Геометрия - те же тела, что в КД и STEP -
CAD/GLB/*.glb из CAD/src/twistlock.py: корпус - модель конструктора, остальное по библиотеке узла
(сборка в положении «открыто», отливка с прибылями, стержень отверстия и полости). Замок «закрыто» -
запор и рукоятка повёрнуты на T.ПОВОРОТ вокруг оси узла, как в модели судна. Начало узла - плечо
корпуса под фитинг, под узлом - вырезка настила 6 мм с продольной балкой Т 260 × 8 / 130 × 12.
"""
import bpy, bmesh, math, os, sys
from mathutils import Matrix, Vector


def _корень():
    for к in (os.path.dirname(os.path.dirname(os.path.abspath(__file__))) if "__file__" in globals() else None,
              os.environ.get("GORIZONT_ROOT"), r"E:\Ship_docx"):
        if к and os.path.isdir(os.path.join(к, "src", "lib")):
            return к
    raise RuntimeError("Не найден корень репозитория")


ROOT = _корень()
for п in (os.path.join(ROOT, "src"), os.path.join(ROOT, "scripts")):
    if п not in sys.path:
        sys.path.insert(0, п)
from lib import gorizont_twistlock as T

GLB = os.path.join(ROOT, "CAD", "GLB")
OUT = os.path.join(ROOT, "renders", "горизонт_2026", "узел")
СЦЕНА = "Фундамент"
ПОВОРОТНЫЕ = ("pos.2 ", "pos.3 ")
#: высоты узла, м - от плеча корпуса (начало узла)
Z_ПЛ = T.КОРПУС["z"][0] / 1000.0                                              # верх платика
Z_НАСТИЛ = -T.высота_опоры()                                                   # верх настила
М = 1000.0

#: Материал по позиции спецификации: корпус, платик, запор и рукоятка окрашены эмалью ПФ-115,
#: вал запора и шайба - сталь, изоляция - СТЭФ, подкладной лист - АМг5, крепёж - нержавейка.
МАТ = [("pos.1 ", "Ф_окраска"), ("pos.2 ", "Ф_окраска"), ("pos.3 ", "Ф_окраска"), ("pos.4 ", "Ф_окраска"),
       ("pos.5 ", "Ф_сталь"), ("pos.6 ", "Ф_СТЭФ"), ("pos.7 ", "Ф_СТЭФ"), ("pos.8 ", "Ф_СТЭФ"), ("pos.9 ", "Ф_АМг5"),
       ("pos.", "Ф_нерж")]


def _материал(имя, цвет, металл, шерох):
    m = bpy.data.materials.get(имя) or bpy.data.materials.new(имя)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = цвет
    b.inputs["Metallic"].default_value = металл
    b.inputs["Roughness"].default_value = шерох
    m.diffuse_color = цвет
    return m


def материалы():
    _материал("Ф_окраска", (0.16, 0.012, 0.02, 1.0), 0.15, 0.45)     # эмаль ПФ-115 бордовая по технологии
    _материал("Ф_сталь", (0.50, 0.51, 0.53, 1.0), 0.80, 0.35)
    _материал("Ф_СТЭФ", (0.52, 0.56, 0.26, 1.0), 0.0, 0.55)
    _материал("Ф_АМг5", (0.70, 0.72, 0.74, 1.0), 0.65, 0.40)
    _материал("Ф_нерж", (0.72, 0.73, 0.75, 1.0), 0.80, 0.30)
    _материал("Ф_пол", (0.78, 0.79, 0.80, 1.0), 0.0, 0.85)
    _материал("Ф_настил", (0.28, 0.30, 0.33, 1.0), 0.6, 0.5)
    _материал("Ф_отливка", (0.30, 0.25, 0.22, 1.0), 0.5, 0.75)
    _материал("Ф_стержень", (0.80, 0.70, 0.52, 1.0), 0.0, 0.95)
    _материал("Ф_литьё", (0.34, 0.35, 0.36, 1.0), 0.55, 0.60)


def _сцена():
    sc = bpy.data.scenes.get(СЦЕНА) or bpy.data.scenes.new(СЦЕНА)
    if bpy.context.window is not None:
        bpy.context.window.scene = sc
    for o in list(sc.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for c in list(sc.collection.children):
        sc.collection.children.unlink(c)
    кол = bpy.data.collections.get("Фундамент_детали") or bpy.data.collections.new("Фундамент_детали")
    for o in list(кол.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    sc.collection.children.link(кол)
    return sc, кол


def _импорт(файл, кол, сдвиг=(0.0, 0.0, 0.0)):
    """Детали из GLB. Преобразование узла вшито в сетку, швы сшиты, объект - в начале координат узла."""
    до = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=os.path.join(GLB, файл))
    новые = [o for o in bpy.data.objects if o not in до]
    out = []
    for o in новые:
        if o.type != "MESH":
            continue
        me = o.data.copy()
        me.transform(o.matrix_world)
        bm = bmesh.new(); bm.from_mesh(me)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)
        bm.to_mesh(me); bm.free()
        if hasattr(me, "shade_flat"):
            me.shade_flat()
        ob = bpy.data.objects.new(o.name, me)
        кол.objects.link(ob)
        ob.location = сдвиг
        имя = next((m for k, m in МАТ if o.name.startswith(k)), "Ф_нерж")
        ob.data.materials.clear(); ob.data.materials.append(bpy.data.materials[имя])
        out.append(ob)
    for o in новые:
        bpy.data.objects.remove(o, do_unlink=True)
    return out


def _короб(имя, x0, x1, y0, y1, z0, z1, кол, мат):
    me = bpy.data.meshes.new(имя)
    v = [(x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0), (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1)]
    me.from_pydata(v, [], [[0, 3, 2, 1], [4, 5, 6, 7], [0, 1, 5, 4], [1, 2, 6, 5], [2, 3, 7, 6], [3, 0, 4, 7]])
    me.update()
    ob = bpy.data.objects.new(имя, me); кол.objects.link(ob)
    ob.data.materials.append(bpy.data.materials[мат])
    return ob


def палуба(кол):
    """Вырезка настила с отверстиями под втулки болтов и продольная балка Т под осью узла."""
    t = T.ОПОРА["настил"] / М
    z_верх = Z_НАСТИЛ
    bx, by = T.ПЛАТИК["болт_x"] / М, T.ПЛАТИК["болт_y"] / М
    r = (T.БОЛТ["втулка"][0] / 2.0 + 0.3) / М
    base = _короб("Настил_6", -0.34, 0.34, -0.26, 0.26, z_верх - t, z_верх, кол, "Ф_настил")
    резцы = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=32, radius1=r, radius2=r, depth=t + 0.01)
            me = bpy.data.meshes.new("_резец"); bm.to_mesh(me); bm.free()
            o = bpy.data.objects.new("_резец", me); кол.objects.link(o)
            o.location = (sx * bx, sy * by, z_верх - t / 2.0)
            m = base.modifiers.new("отв", "BOOLEAN"); m.operation, m.solver, m.object = "DIFFERENCE", "EXACT", o
            резцы.append(o)
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(base.evaluated_get(dg))
    for m in list(base.modifiers):
        base.modifiers.remove(m)
    старая = base.data; base.data = me; bpy.data.meshes.remove(старая)
    for o in резцы:
        bpy.data.objects.remove(o, do_unlink=True)
    б = T.БАЛКА
    z_полки = z_верх - t - б["h"] / М
    стенка = _короб("Балка_стенка", -0.34, 0.34, -б["tw"] / 2000.0, б["tw"] / 2000.0, z_полки + б["tf"] / М, z_верх - t, кол, "Ф_настил")
    полка = _короб("Балка_полка", -0.34, 0.34, -б["bf"] / 2000.0, б["bf"] / 2000.0, z_полки, z_полки + б["tf"] / М, кол, "Ф_настил")
    return [base, стенка, полка]


def _повернуть(детали, угол):
    R = Matrix.Rotation(math.radians(угол), 4, "Z")
    for o in детали:
        if o.name.startswith(ПОВОРОТНЫЕ):
            o.data.transform(R)


def _мир_и_свет(sc):
    w = bpy.data.worlds.get("Фундамент_мир") or bpy.data.worlds.new("Фундамент_мир")
    w.use_nodes = True
    bg = next((n for n in w.node_tree.nodes if n.type == "BACKGROUND"), None)
    if bg:
        bg.inputs[0].default_value = (0.55, 0.58, 0.63, 1.0)    # металл отражает фон: на светлом он пропадает
        bg.inputs[1].default_value = 0.8
    sc.world = w
    for имя, энергия, rot in (("Фундамент_солнце", 4.0, (48, 12, -30)), ("Фундамент_контр", 1.4, (65, -10, 150))):
        d = bpy.data.lights.get(имя) or bpy.data.lights.new(имя, "SUN")
        d.energy = энергия
        d.angle = math.radians(3.0)
        o = bpy.data.objects.get(имя) or bpy.data.objects.new(имя, d)
        if o.name not in sc.collection.objects:
            sc.collection.objects.link(o)
        o.rotation_euler = tuple(math.radians(a) for a in rot)
    sc.render.engine = "CYCLES"
    try:
        prefs = bpy.context.preferences.addons["cycles"].preferences
        prefs.get_devices()
        sc.cycles.device = "GPU" if any(d.type != "CPU" for d in prefs.devices) else "CPU"
    except Exception:
        sc.cycles.device = "CPU"
    sc.cycles.use_denoising = True
    sc.view_settings.view_transform = "AgX"
    sc.view_settings.exposure = -0.3
    sc.render.image_settings.file_format = "PNG"
    sc.render.film_transparent = False


def _пол(кол, z):
    """Пол под узлом - тени дают глубину."""
    return _короб("Пол", -3.0, 3.0, -3.0, 3.0, z - 0.02, z, кол, "Ф_пол")


def _кадр(sc, имя, loc, look, lens, res=(1800, 1200), samples=96):
    cam = bpy.data.objects.get("Фундамент_камера")
    if cam is None:
        cam = bpy.data.objects.new("Фундамент_камера", bpy.data.cameras.new("Фундамент_камера"))
    if cam.name not in sc.collection.objects:
        sc.collection.objects.link(cam)
    cam.data.lens = lens
    cam.data.clip_start = 0.005
    cam.location = loc
    cam.rotation_euler = (Vector(look) - Vector(loc)).to_track_quat("-Z", "Y").to_euler()
    sc.camera = cam
    sc.render.resolution_x, sc.render.resolution_y = res
    sc.render.resolution_percentage = 100
    sc.cycles.samples = samples
    os.makedirs(OUT, exist_ok=True)
    sc.render.filepath = os.path.join(OUT, имя)
    bpy.ops.render.render(write_still=True, scene=sc.name)
    return sc.render.filepath


def _подписи_поверх(sc, png_база, png_выход, якоря_мир, заголовок="", подзаголовок="", стиль="позиции"):
    """Номера позиций кружками с выносками - поверх рендера, в 2D (scripts/подписи_рендера.py в .venv проекта:
    в Python Blender нет PIL). Якоря - точки деталей в мировых координатах, проецируются камерой сцены."""
    import json, subprocess, tempfile
    from bpy_extras.object_utils import world_to_camera_view
    W = sc.render.resolution_x * sc.render.resolution_percentage // 100
    H = sc.render.resolution_y * sc.render.resolution_percentage // 100
    якоря = []
    for текст, p in якоря_мир:
        u, v, _ = world_to_camera_view(sc, sc.camera, Vector(p))
        якоря.append({"текст": текст, "x": round(u * W, 1), "y": round((1.0 - v) * H, 1)})
    jp = os.path.join(tempfile.gettempdir(), "_подписи_%s.json" % os.path.splitext(os.path.basename(png_выход))[0])
    json.dump({"стиль": стиль, "заголовок": заголовок, "подзаголовок": подзаголовок, "якоря": якоря},
              open(jp, "w", encoding="utf-8"), ensure_ascii=False)
    py = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
    if not os.path.exists(py):
        py = "python"
    r = subprocess.run([py, "-X", "utf8", os.path.join(ROOT, "scripts", "подписи_рендера.py"), png_база, jp, png_выход],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError("подписи_рендера - " + r.stderr[-400:])
    return png_выход


#: Взрыв-схема: сдвиг каждой позиции (м). Сверху вниз - запор, корпус с рукояткой, болты, платик, шайба,
#: прокладка, подкладной лист, втулки, изолирующие шайбы, шайбы и гайки. Рукоятка ещё и выходит из прорези.
_ВЗРЫВ = [("pos.3 ", 0.22), ("pos.1 ", 0.09), ("pos.2 ", 0.09), ("pos.10", 0.17), ("pos.4 ", 0.0), ("pos.5 ", -0.11),
          ("pos.6 ", -0.17), ("pos.9 ", -0.25), ("pos.7 ", -0.32), ("pos.8 ", -0.38), ("pos.12", -0.44), ("pos.11", -0.51)]


def _сдвиг(имя):
    dz = next((d for k, d in _ВЗРЫВ if имя.startswith(k)), 0.0)
    if имя.startswith("pos.2 "):
        a = math.radians(T.ВЫРЕЗЫ["открыто"])
        return (0.14 * math.cos(a), 0.14 * math.sin(a), dz)
    return (0.0, 0.0, dz)


def виды(samples=96, verbose=True, кадры=(1, 2, 3)):
    """Кадры узла в сцене «Фундамент» (1 - сборка, 2 - взрыв-схема, 3 - отливка). Судовая сцена остаётся активной."""
    исходная = bpy.context.window.scene if bpy.context.window else bpy.context.scene
    материалы()
    sc, кол = _сцена()
    _мир_и_свет(sc)
    сделано = []
    # 1. сборка «закрыто» на вырезке настила с балкой
    if 1 in кадры:
        детали = _импорт("VG-2026_46_00_twistlock_open.glb", кол)
        _повернуть(детали, T.ПОВОРОТ)
        палуба(кол)
        _пол(кол, Z_НАСТИЛ - 0.30)
        сделано.append(_кадр(sc, "46_01_сборка.png", (0.66, -0.80, 0.50), (0.0, 0.0, -0.03), 55, samples=samples))
    if 2 in кадры:
        сделано.append(_взрыв(sc, кол, samples))
    if 3 in кадры:
        сделано.append(_отливка(sc, кол, samples))
    if bpy.context.window is not None:
        bpy.context.window.scene = исходная
    if verbose:
        for p in сделано:
            print("  ", os.path.relpath(p, ROOT))
    return сделано


def _взрыв(sc, кол, samples):
    """Взрыв-схема «открыто» с номерами позиций поверх кадра."""
    for o in list(кол.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    детали = _импорт("VG-2026_46_00_twistlock_open.glb", кол)
    cam = (-1.02, -0.96, 0.40)
    подписаны, якоря, z_мин = set(), [], 0.0
    for o in детали:
        d = Vector(_сдвиг(o.name))
        o.location = d
        vs = [v.co + d for v in o.data.vertices]              # сетка в осях узла, сдвиг - location
        z_мин = min(z_мин, min(v.z for v in vs))
        поз = o.name.split()[0].replace("pos.", "")
        if поз not in подписаны:
            подписаны.add(поз)
            c = sum(vs, Vector()) / len(vs)
            if поз == "1":                                      # корпус: точка на плече, а не в отверстии
                c = Vector((c.x - 0.055, c.y - 0.02, d.z + 0.0))
            if поз == "4":                                      # платик: точка у края, а не в окне
                c = Vector((c.x - 0.15, c.y - 0.10, c.z))
            якоря.append((поз, (c.x, c.y, c.z)))
    _пол(кол, z_мин - 0.04)
    база = _кадр(sc, "_46_02_взрыв_база.png", cam, (0.0, 0.0, -0.16), 40, res=(1800, 1800), samples=samples)
    out = _подписи_поверх(sc, база, os.path.join(OUT, "46_02_взрыв.png"), sorted(якоря, key=lambda a: int(a[0])))
    # кадр без подписей - во временную папку, а не в корзину: подписи можно переложить без нового рендера
    import shutil, tempfile
    shutil.move(база, os.path.join(tempfile.gettempdir(), os.path.basename(база)))
    return out


def _отливка(sc, кол, samples):
    """Отливка корпуса с прибылями, стержень отверстия и полости, корпус после обработки."""
    for o in list(кол.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for o in _импорт("VG-2026_46_01_casting.glb", кол, (-0.26, 0.0, 0.0)):
        o.data.materials.clear(); o.data.materials.append(bpy.data.materials["Ф_отливка"])
    for o in _импорт("VG-2026_46_01_core.glb", кол, (0.0, 0.0, 0.0)):
        o.data.materials.clear(); o.data.materials.append(bpy.data.materials["Ф_стержень"])
    for o in _импорт("VG-2026_46_00_twistlock_open.glb", кол, (0.26, 0.0, 0.0)):
        if not o.name.startswith("pos.1 "):
            bpy.data.objects.remove(o, do_unlink=True)
        else:
            o.data.materials.clear(); o.data.materials.append(bpy.data.materials["Ф_литьё"])
    _пол(кол, T.КОРПУС["z"][0] / М - 0.02 - 0.002)
    return _кадр(sc, "46_03_отливка_стержень.png", (0.20, -1.05, 0.45), (0.0, 0.0, 0.0), 45, res=(2000, 1100), samples=samples)


if __name__ == "__main__":
    виды()
