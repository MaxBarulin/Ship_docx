# -*- coding: utf-8 -*-
r"""Узел ВГ-2026.46.00 «Литой фундамент-замок модуля» в Blender - сборка, взрыв-схема, отливка со стержнем.

    import blender_фундамент as Ф
    Ф.виды()        # renders/горизонт_2026/узел/46_01_сборка.png, 46_02_взрыв.png, 46_03_отливка_стержень.png

Отдельная сцена «Фундамент» - судовая сцена не трогается. Геометрия - те же
тела, что в КД и STEP - CAD/GLB/*.glb из CAD/src/twistlock.py (сборка в
положении «открыто», отливка с прибылью, стержень с ногой-знаком). Замок
«закрыто» - конус, рычаг и фиксатор повёрнуты на 90° вокруг оси узла, как
в модели судна. Под узлом - вырезка настила 6 мм с продольной балкой
Т 260 × 8 / 130 × 12, на которой он стоит.
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
ПОВОРОТНЫЕ = ("pos.2 ", "pos.3 ", "pos.16")

#: Материал по позиции спецификации: литьё, сталь, нержавейка, СТЭФ, АМг5, бронза.
МАТ = [("pos.1 ", "Ф_литьё"), ("pos.2 ", "Ф_40Х"), ("pos.3 ", "Ф_рычаг"), ("pos.16", "Ф_фиксатор"), ("pos.4 ", "Ф_бронза"),
       ("pos.5 ", "Ф_СТЭФ"), ("pos.6 ", "Ф_СТЭФ"), ("pos.7 ", "Ф_СТЭФ"), ("pos.8 ", "Ф_АМг5"), ("pos.", "Ф_нерж")]


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
    _материал("Ф_литьё", (0.34, 0.35, 0.36, 1.0), 0.55, 0.60)
    _материал("Ф_40Х", (0.50, 0.51, 0.53, 1.0), 0.80, 0.35)
    _материал("Ф_рычаг", (0.62, 0.10, 0.08, 1.0), 0.3, 0.40)      # рычаг окрашен: виден на палубе
    _материал("Ф_фиксатор", (0.85, 0.62, 0.05, 1.0), 0.3, 0.40)
    _материал("Ф_бронза", (0.72, 0.50, 0.25, 1.0), 1.0, 0.35)
    _материал("Ф_СТЭФ", (0.52, 0.56, 0.26, 1.0), 0.0, 0.55)
    _материал("Ф_АМг5", (0.70, 0.72, 0.74, 1.0), 0.65, 0.40)
    _материал("Ф_нерж", (0.72, 0.73, 0.75, 1.0), 0.80, 0.30)
    _материал("Ф_пол", (0.78, 0.79, 0.80, 1.0), 0.0, 0.85)
    _материал("Ф_настил", (0.28, 0.30, 0.33, 1.0), 0.6, 0.5)
    _материал("Ф_отливка", (0.30, 0.25, 0.22, 1.0), 0.5, 0.75)
    _материал("Ф_стержень", (0.80, 0.70, 0.52, 1.0), 0.0, 0.95)
    _материал("Ф_цифры", (0.08, 0.09, 0.10, 1.0), 0.0, 0.6)


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
    """Вырезка настила с отверстиями под болты и продольная балка Т под осью узла."""
    t = T.ОПОРА["настил"] / 1000.0
    z_верх = -(T.ОПОРА["лист"][2] + T.ОПОРА["прокладка"]) / 1000.0
    bx, by, r = T.КОРПУС["болт_x"] / 1000.0, T.КОРПУС["болт_y"] / 1000.0, T.КОРПУС["d_отв"] / 2000.0
    base = _короб("Настил_6", -0.34, 0.34, -0.26, 0.26, z_верх - t, z_верх, кол, "Ф_настил")
    резцы = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            bm = bmesh.new()
            bmesh.ops.create_cone(bm, cap_ends=True, segments=24, radius1=r, radius2=r, depth=t + 0.01)
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
    z_полки = z_верх - t - б["h"] / 1000.0
    стенка = _короб("Балка_стенка", -0.34, 0.34, -б["tw"] / 2000.0, б["tw"] / 2000.0, z_полки + б["tf"] / 1000.0, z_верх - t, кол, "Ф_настил")
    полка = _короб("Балка_полка", -0.34, 0.34, -б["bf"] / 2000.0, б["bf"] / 2000.0, z_полки, z_полки + б["tf"] / 1000.0, кол, "Ф_настил")
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


def _цифра(sc, кол, текст, loc, cam_loc, size=0.022):
    """Номер позиции - плоский текст, развёрнутый к камере."""
    cu = bpy.data.curves.new("поз_" + текст, "FONT")
    cu.body = текст
    cu.size = size
    cu.align_x, cu.align_y = "CENTER", "CENTER"
    cu.extrude = 0.0008
    o = bpy.data.objects.new("поз_" + текст, cu)
    кол.objects.link(o)
    o.location = loc
    o.rotation_euler = (Vector(cam_loc) - Vector(loc)).to_track_quat("Z", "Y").to_euler()
    o.data.materials.append(bpy.data.materials["Ф_цифры"])
    if hasattr(o, "visible_shadow"):
        o.visible_shadow = False                  # цифра без тени на полу
    return o


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


#: Взрыв-схема: сдвиг каждой позиции (м); детали внутри окна корпуса выходят через окно - по направлению рычага.
def _сдвиг(имя, окно):
    ox, oy = окно
    if имя.startswith("pos.2 "):
        return (0.0, 0.0, 0.30)
    if имя.startswith("pos.16"):
        return (0.0, 0.0, 0.16)
    if имя.startswith("pos.15"):                        # маслёнка на +X - за стаканом от камеры; выносится вправо в кадре
        return (0.14, -0.14, 0.02)
    if имя.startswith("pos.3 "):
        return (ox * 0.36, oy * 0.36, -0.02)
    for k, d in (("pos.4 ", 0.12), ("pos.13", 0.20), ("pos.12", 0.26), ("pos.14 end", 0.30), ("pos.14 screw", 0.33)):
        if имя.startswith(k):
            return (ox * d, oy * d, -0.03)
    for k, dz in (("pos.9 ", 0.36), ("pos.11 washer under head", 0.20), ("pos.5 ", -0.08), ("pos.8 ", -0.15),
                  ("pos.6 ", -0.24), ("pos.7 ", -0.28), ("pos.11 washer under nut", -0.32), ("pos.10", -0.38)):
        if имя.startswith(k):
            return (0.0, 0.0, dz)
    return (0.0, 0.0, 0.0)


def виды(samples=96, verbose=True):
    """Три кадра узла в сцене «Фундамент». Судовая сцена остаётся активной после рендера."""
    исходная = bpy.context.window.scene if bpy.context.window else bpy.context.scene
    материалы()
    sc, кол = _сцена()
    _мир_и_свет(sc)
    сделано = []
    # 1. сборка «закрыто» на вырезке настила с балкой
    детали = _импорт("VG-2026_46_00_twistlock_open.glb", кол)
    _повернуть(детали, 90.0)
    палуба(кол)
    _пол(кол, -0.30)
    сделано.append(_кадр(sc, "46_01_сборка.png", (0.62, -0.78, 0.52), (0.0, 0.0, 0.03), 60, samples=samples))
    # 2. взрыв-схема «открыто» с номерами позиций
    for o in list(кол.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    детали = _импорт("VG-2026_46_00_twistlock_open.glb", кол)
    окно = Vector((-1.0, 1.0, 0.0)).normalized()            # рычаг в GLB «открыто» смотрит на 135°
    cam = (-1.30, -1.30, 0.78)                                # поперёк окна: детали из окна уходят влево
    вправо = Vector((1.0, -1.0, 0.0)).normalized()           # «вправо» в кадре
    подписаны, якоря, z_мин = set(), [], 0.0
    for o in детали:
        d = Vector(_сдвиг(o.name, (окно.x, окно.y)))
        o.location = d
        vs = [v.co + d for v in o.data.vertices]              # сетка в осях узла, сдвиг - location
        z_мин = min(z_мин, min(v.z for v in vs))
        поз = o.name.split()[0].replace("pos.", "")
        if поз not in подписаны:
            подписаны.add(поз)
            c = sum(vs, Vector()) / len(vs)
            if поз == "1":                                      # корпус: точка на фланце, а не в пустом стакане
                c = Vector((c.x + 0.10, c.y - 0.10, min(v.z for v in vs) + 0.01))
            якоря.append((поз, (c.x, c.y, c.z)))
    # пол ниже самых нижних гаек: иначе они уходили под плиту пола и просвечивали сквозь неё
    _пол(кол, z_мин - 0.04)
    база = _кадр(sc, "_46_02_взрыв_база.png", cam, (-0.06, 0.06, 0.0), 50, res=(1800, 1500), samples=samples)
    сделано.append(_подписи_поверх(sc, база, os.path.join(OUT, "46_02_взрыв.png"), sorted(якоря, key=lambda a: int(a[0])),
                                   "Взрыв-схема узла ВГ-2026.46.00", "номера - позиции спецификации, замок «открыто»"))
    os.remove(база)
    # 3. отливка с прибылью, стержень с ногой-знаком и корпус после мехобработки
    for o in list(кол.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for o in _импорт("VG-2026_46_01_casting.glb", кол, (-0.34, 0.0, 0.0)):
        o.data.materials.clear(); o.data.materials.append(bpy.data.materials["Ф_отливка"])
    for o in _импорт("VG-2026_46_01_core.glb", кол, (0.0, 0.0, 0.045)):
        o.data.materials.clear(); o.data.materials.append(bpy.data.materials["Ф_стержень"])
    for o in _импорт("VG-2026_46_00_twistlock_open.glb", кол, (0.34, 0.0, 0.0)):
        if not o.name.startswith("pos.1 "):
            bpy.data.objects.remove(o, do_unlink=True)
    _пол(кол, -0.004)
    сделано.append(_кадр(sc, "46_03_отливка_стержень.png", (0.30, -1.30, 0.62), (0.0, 0.0, 0.08), 45, res=(2000, 1100), samples=samples))
    if bpy.context.window is not None:
        bpy.context.window.scene = исходная
    if verbose:
        for p in сделано:
            print("  ", os.path.relpath(p, ROOT))
    return сделано


if __name__ == "__main__":
    виды()
