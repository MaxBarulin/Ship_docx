# -*- coding: utf-8 -*-
r"""Солнечная палуба в модели - 72 фундамента-замка ВГ-2026.46.00 и модули темы «трансформера».

    import blender_модули as Мд
    Мд.собрать(тема="президентская")                # после blender_судно.собрать()
    Мд.собрать(тема="президентская", висит="А-3-ПБ", подъём=2.2)   # модуль на крюке - кадр у причала

Фундаменты - те же тела, что в КД - CAD/GLB/VG-2026_46_00_twistlock_open.glb из
CAD/src/twistlock.py. Каждая деталь - отдельный объект (связанные копии одной
сетки), швы glTF сшиваются, чтобы аудит замкнутости видел тела, а не лоскуты.
Замок под модулем - «закрыто», на свободном слоте - «открыто», рычаг смотрит в
торцевой проход. У кормовых опор слота - в корму, у носовых - в нос.

Модуль - контейнер 20' high cube - угловые фитинги ISO 1161 (нижние полые, с
отверстием 124,5 × 63,5 - упор и конус фундамента входят в них без пересечений),
рамы, короб, отделка по типу модуля. Слоты и темы - gorizont_modules.
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
from lib import gorizont as G, gorizont_modules as M, gorizont_twistlock as T
import blender_стиль as Ст

КОЛ_ФУНД = "08_Фундаменты"
КОЛ_МОД = "09_Модули"
GLB = os.path.join(ROOT, "CAD", "GLB", "VG-2026_46_00_twistlock_open.glb")
Z_НАСТИЛ = G.DECKS["солнечная"]
Z_ФУНД = Z_НАСТИЛ + (T.ОПОРА["лист"][2] + T.ОПОРА["прокладка"]) / 1000.0     # подошва корпуса
Z_ПЛОЩАДКА = Z_НАСТИЛ + T.высота_опоры()                                        # низ фитинга модуля
К = M.КОНТЕЙНЕР
ФИТ = tuple(v / 1000.0 for v in К["фитинг_мм"])                                 # 0,178 × 0,162 × 0,118
ОТВ = tuple(v / 1000.0 for v in К["отверстие_мм"])
#: Детали фундамента, которые ставятся в модель судна. Болты с гайками под настилом не ставятся:
#: настил в модели - плита 0,1 м, болт прошёл бы её насквозь; головки болтов добавляются отдельно.
ДЕТАЛИ = {"pos.1 ": "Сталь_ТДЦ", "pos.2 ": "Сталь_ТДЦ", "pos.3 ": "Сталь_ТДЦ", "pos.16": "Сталь_нерж",
          "pos.5 ": "СТЭФ", "pos.8 ": "АМг5_лист", "pos.11 washer under head": "Сталь_нерж"}
ПОВОРОТНЫЕ = ("pos.2 ", "pos.3 ", "pos.16")          # поворачиваются рычагом на 90° при запирании


# --- служебное ---------------------------------------------------------------------------------
def _кол(имя):
    c = bpy.data.collections.get(имя)
    if c is None:
        c = bpy.data.collections.new(имя)
        bpy.context.scene.collection.children.link(c)
    return c


def _очистить_кол(имя):
    c = bpy.data.collections.get(имя)
    if c is None:
        return
    for o in list(c.all_objects):
        bpy.data.objects.remove(o, do_unlink=True)
    for ch in list(c.children):
        bpy.data.collections.remove(ch)


def _материал(имя, цвет, металл=0.0, шерох=0.5, прозрачность=0.0, ior=1.45):
    m = bpy.data.materials.get(имя)
    if m is None:
        m = bpy.data.materials.new(имя)
    m.use_nodes = True
    b = next(n for n in m.node_tree.nodes if n.type == "BSDF_PRINCIPLED")
    b.inputs["Base Color"].default_value = цвет
    b.inputs["Metallic"].default_value = металл
    b.inputs["Roughness"].default_value = шерох
    if прозрачность:
        for key in ("Transmission Weight", "Transmission"):
            if key in b.inputs:
                b.inputs[key].default_value = прозрачность
                break
        b.inputs["IOR"].default_value = ior
    m.diffuse_color = цвет
    return m


def материалы():
    _материал("Сталь_ТДЦ", (0.46, 0.48, 0.50, 1.0), 0.85, 0.42)
    _материал("Сталь_нерж", (0.78, 0.79, 0.80, 1.0), 1.0, 0.22)
    _материал("СТЭФ", (0.55, 0.60, 0.28, 1.0), 0.0, 0.55)
    _материал("АМг5_лист", (0.70, 0.72, 0.74, 1.0), 0.9, 0.35)
    _материал("Контейнер_графит", (0.10, 0.11, 0.12, 1.0), 0.3, 0.45)
    _материал("Контейнер_белый", (0.86, 0.87, 0.86, 1.0), 0.1, 0.4)
    _материал("Фитинг_ISO", (0.20, 0.21, 0.22, 1.0), 0.6, 0.5)
    _материал("Вода_бассейн", (0.10, 0.55, 0.62, 1.0), 0.0, 0.05, прозрачность=0.85, ior=1.33)
    _материал("Тент", (0.93, 0.92, 0.88, 1.0), 0.0, 0.8)


def _назначить(ob, имя):
    m = bpy.data.materials.get(имя)
    if m is None:
        Ст.назначить(ob, имя)
        return
    ob.data.materials.clear()
    ob.data.materials.append(m)


def _сетка_короб(имя, размеры):
    dx, dy, dz = (d / 2.0 for d in размеры)
    me = bpy.data.meshes.new(имя)
    v = [(sx * dx, sy * dy, sz * dz) for sx in (-1, 1) for sy in (-1, 1) for sz in (-1, 1)]
    f = [[0, 1, 3, 2], [4, 6, 7, 5], [0, 2, 6, 4], [1, 5, 7, 3], [0, 4, 5, 1], [2, 3, 7, 6]]
    me.from_pydata(v, [], f)
    me.update()
    return me


def _короб(имя, центр, размеры, кол, материал, поворот=0.0, наклон=0.0):
    ob = bpy.data.objects.new(имя, _сетка_короб(имя, размеры))
    кол.objects.link(ob)
    ob.location = центр
    ob.rotation_euler = (наклон, 0.0, поворот)
    _назначить(ob, материал)
    return ob


def _цилиндр(имя, центр, r, h, кол, материал, n=24):
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=n, radius1=r, radius2=r, depth=h)
    me = bpy.data.meshes.new(имя)
    bm.to_mesh(me); bm.free()
    ob = bpy.data.objects.new(имя, me)
    кол.objects.link(ob)
    ob.location = центр
    _назначить(ob, материал)
    return ob


def _вычесть(база, *резцы):
    """Булева разность через оценённую сетку - без bpy.ops и активного объекта."""
    for r in резцы:
        mod = база.modifiers.new("вычесть", "BOOLEAN")
        mod.operation, mod.solver, mod.object = "DIFFERENCE", "EXACT", r
    dg = bpy.context.evaluated_depsgraph_get()
    me = bpy.data.meshes.new_from_object(база.evaluated_get(dg))
    for m_ in list(база.modifiers):
        база.modifiers.remove(m_)
    старая = база.data
    база.data = me
    bpy.data.meshes.remove(старая)
    for r in резцы:
        bpy.data.objects.remove(r, do_unlink=True)
    return база


# --- фундаменты -------------------------------------------------------------------------------
_ПРОТО = {}


def _живы(кэш):
    """Сетки из кэша ещё в файле? После очистки сцены или открытия .blend ссылки мертвеют."""
    try:
        return bool(кэш) and all(me.name in bpy.data.meshes for me in (v[0] if isinstance(v, tuple) else v for v in кэш.values()))
    except ReferenceError:
        return False


def _прототип():
    """Сетки деталей узла из GLB (одна на деталь) и головка болта."""
    if _живы(_ПРОТО):
        return _ПРОТО
    _ПРОТО.clear()
    до = set(bpy.data.objects)
    bpy.ops.import_scene.gltf(filepath=GLB)
    новые = [o for o in bpy.data.objects if o not in до]
    for o in новые:
        if o.type != "MESH":
            continue
        ключ = next((k for k in ДЕТАЛИ if o.name.startswith(k)), None)
        if ключ is None or (ключ == "pos.11 washer under head" and not o.name.endswith(" 1")):
            continue
        o.data.transform(o.matrix_world)                               # поворот Y-вверх → Z-вверх и угол детали
        bm = bmesh.new(); bm.from_mesh(o.data)
        bmesh.ops.remove_doubles(bm, verts=bm.verts, dist=1e-5)       # glTF режет вершины по нормалям - сшить
        bm.to_mesh(o.data); bm.free()
        o.data.shade_flat() if hasattr(o.data, "shade_flat") else None
        if ключ.startswith("pos.11"):                                  # шайба - одна сетка на четыре болта, в ноль по XY
            xs = [v.co.x for v in o.data.vertices]; ys = [v.co.y for v in o.data.vertices]
            o.data.transform(Matrix.Translation((-0.5 * (min(xs) + max(xs)), -0.5 * (min(ys) + max(ys)), 0.0)))
        _ПРОТО[ключ] = (o.data, None)
    for o in новые:
        bpy.data.objects.remove(o, do_unlink=True)
    bm = bmesh.new()
    bmesh.ops.create_cone(bm, cap_ends=True, segments=6, radius1=0.0208, radius2=0.0208, depth=0.015)
    me = bpy.data.meshes.new("Головка_М24"); bm.to_mesh(me); bm.free()
    _ПРОТО["голова"] = (me, None)
    return _ПРОТО


def _угол_опоры(sx):
    """Поворот корпуса опоры. У кормовых фитингов слота рычаг в корму (0°), у носовых - в нос (180°)."""
    return 0.0 if sx < 0 else math.pi


def фундаменты(кол, занятые, открытые=()):
    """72 опоры по M.фундаменты(). Занятые слоты - «закрыто», остальные и `открытые` - «открыто»."""
    п = _прототип()
    сд = {s["слот"]: s for s in M.слоты()}
    n = 0
    for f in M.фундаменты():
        s = сд[f["слот"]]
        sx = 1.0 if f["x"] > s["xc"] else -1.0
        база = _угол_опоры(sx)
        закрыто = f["слот"] in занятые and f["слот"] not in открытые
        имя = "Фунд_%02d" % f["номер"]
        for ключ, материал in ДЕТАЛИ.items():
            me, mw = п[ключ]
            копии = 4 if ключ.startswith("pos.11") else 1
            for k in range(копии):
                ob = bpy.data.objects.new("%s_%s%s" % (имя, ключ.strip().replace(" ", "_")[:22], "_%d" % k if копии > 1 else ""), me)
                кол.objects.link(ob)
                доп = math.radians(90.0) if (закрыто and ключ in ПОВОРОТНЫЕ) else 0.0
                ob.location = (f["x"], f["y"], Z_ФУНД)
                ob.rotation_euler = (0.0, 0.0, база + доп)
                if копии > 1:
                    bx, by = T.КОРПУС["болт_x"] / 1000.0, T.КОРПУС["болт_y"] / 1000.0
                    dx, dy = [(-bx, -by), (-bx, by), (bx, -by), (bx, by)][k]
                    ob.location = (f["x"] + dx, f["y"] + dy, Z_ФУНД)
                _назначить(ob, материал)
                n += 1
        bx, by = T.КОРПУС["болт_x"] / 1000.0, T.КОРПУС["болт_y"] / 1000.0
        z_h = Z_ФУНД + (T.КОРПУС["t_фл"] - T.КОРПУС["цековка"][1] + 4.0 + 7.5) / 1000.0
        for k, (dx, dy) in enumerate([(-bx, -by), (-bx, by), (bx, -by), (bx, by)]):
            ob = bpy.data.objects.new("%s_головка_%d" % (имя, k), п["голова"][0])
            кол.objects.link(ob)
            ob.location = (f["x"] + dx, f["y"] + dy, z_h)
            _назначить(ob, "Сталь_нерж")
            n += 1
    return n


# --- модули -----------------------------------------------------------------------------------
_ФИТИНГ = {}


def _сетка_фитинга():
    """Нижний угловой фитинг ISO 1161 - полый, с отверстием в днище, одна сетка на все."""
    if _живы(_ФИТИНГ):
        return _ФИТИНГ["низ"]
    _ФИТИНГ.clear()
    tmp = bpy.data.collections.new("_tmp_фитинг")
    bpy.context.scene.collection.children.link(tmp)
    дно = T.ФИТИНГ_ДНО / 1000.0
    база = _короб("_фитинг", (0, 0, ФИТ[2] / 2.0), ФИТ, tmp, "Фитинг_ISO")
    полость = _короб("_полость", (0, 0, дно + 0.031), (0.140, 0.120, 0.062), tmp, "Фитинг_ISO")
    отв = _короб("_отв", (0, 0, дно / 2.0), (ОТВ[0], ОТВ[1], дно + 0.004), tmp, "Фитинг_ISO")
    _вычесть(база, полость, отв)
    me = база.data
    me.transform(Matrix.Translation(база.location))               # сетка после булевой - в осях объекта
    bpy.data.objects.remove(база, do_unlink=True)
    bpy.data.collections.remove(tmp)
    _ФИТИНГ["низ"] = me
    return me


def контейнер(имя, xc, yc, z0, тип, кол):
    """Модуль на базе 20' HC - фитинги, рамы, короб и отделка по типу. z0 - низ фитингов."""
    L, B, H = К["длина"], К["ширина"], К["высота"]
    fx, fy = К["фитинги_x"] / 2.0, К["фитинги_y"] / 2.0
    fl, fw, fh = ФИТ
    наружу = 1.0 if yc >= 0 else -1.0                 # борт, к которому смотрит модуль
    сделано = []
    for sx in (-1, 1):
        for sy in (-1, 1):
            ob = bpy.data.objects.new("%s_фитинг_н_%d%d" % (имя, sx > 0, sy > 0), _сетка_фитинга())
            кол.objects.link(ob); ob.location = (xc + sx * fx, yc + sy * fy, z0)
            _назначить(ob, "Фитинг_ISO"); сделано.append(ob)
    открытый = тип.startswith("бассейн")
    б = M.БАССЕЙН
    h_кор = (б["борт"] if открытый else H - 2 * fh)
    # нижние обвязки между фитингами
    for sy in (-1, 1):
        сделано.append(_короб("%s_обвязка_н_%d" % (имя, sy > 0), (xc, yc + sy * fy, z0 + fh / 2.0), (2 * fx - fl, fw, fh), кол, "Фитинг_ISO"))
    for sx in (-1, 1):
        сделано.append(_короб("%s_торец_н_%d" % (имя, sx > 0), (xc + sx * fx, yc, z0 + fh / 2.0), (fl, 2 * fy - fw, fh), кол, "Фитинг_ISO"))
    zк = z0 + fh
    материал_короба = {"люкс": "Контейнер_графит", "спа": "Интерьер_дерево", "офис": "Контейнер_белый",
                       "бар": "Контейнер_графит", "бассейн": "Контейнер_белый"}.get(тип, "Контейнер_графит")
    if not открытый:
        сделано.append(_короб("%s_короб" % имя, (xc, yc, zк + h_кор / 2.0), (L, B, h_кор), кол, материал_короба))
        for sx in (-1, 1):
            for sy in (-1, 1):
                сделано.append(_короб("%s_фитинг_в_%d%d" % (имя, sx > 0, sy > 0), (xc + sx * fx, yc + sy * fy, zк + h_кор + fh / 2.0), ФИТ, кол, "Фитинг_ISO"))
        for sy in (-1, 1):
            сделано.append(_короб("%s_обвязка_в_%d" % (имя, sy > 0), (xc, yc + sy * fy, zк + h_кор + fh / 2.0), (2 * fx - fl, fw, fh), кол, "Фитинг_ISO"))
    else:
        t, дн, бт = б["стенка"], б["днище"], б["бортик"]
        сделано.append(_короб("%s_днище" % имя, (xc, yc, zк + дн / 2.0), (L, B, дн), кол, материал_короба))
        for sy in (-1, 1):
            сделано.append(_короб("%s_стенка_%d" % (имя, sy > 0), (xc, yc + sy * (B / 2.0 - t / 2.0), zк + дн + (h_кор - дн) / 2.0), (L, t, h_кор - дн), кол, материал_короба))
        for sx in (-1, 1):
            сделано.append(_короб("%s_торец_%d" % (имя, sx > 0), (xc + sx * (L / 2.0 - t / 2.0), yc, zк + дн + (h_кор - дн) / 2.0), (t, B - 2 * t, h_кор - дн), кол, материал_короба))
        сделано.append(_короб("%s_вода" % имя, (xc, yc, zк + дн + б["вода"] / 2.0), (L - 2 * t - 0.002, B - 2 * t - 0.002, б["вода"]), кол, "Вода_бассейн"))
        for sy in (-1, 1):
            сделано.append(_короб("%s_бортик_%d" % (имя, sy > 0), (xc, yc + sy * (B / 2.0 - 0.09), zк + h_кор + бт / 2.0), (L + 0.10, 0.18, бт), кол, "Настил_дерево"))
        for sx in (-1, 1):
            сделано.append(_короб("%s_бортик_т_%d" % (имя, sx > 0), (xc + sx * (L / 2.0 - 0.09), yc, zк + h_кор + бт / 2.0), (0.18, B - 0.36 - 0.002, бт), кол, "Настил_дерево"))
        сделано.append(_короб("%s_стекло" % имя, (xc, yc + наружу * (B / 2.0 - 0.05), zк + h_кор + бт + б["стекло"] / 2.0), (L - 0.4, 0.02, б["стекло"]), кол, "Остекление"))
        return сделано
    # отделка по типу - тонкие панели в миллиметре от короба
    yф = yc + наружу * (B / 2.0 + 0.011)
    yв = yc - наружу * (B / 2.0 + 0.011)
    zc = zк + h_кор / 2.0
    if тип == "люкс":
        сделано.append(_короб("%s_витраж" % имя, (xc, yф, zc), (L - 0.60, 0.02, h_кор - 0.30), кол, "Остекление"))
        сделано.append(_короб("%s_обшивка" % имя, (xc, yв, zc), (L - 0.40, 0.02, h_кор - 0.20), кол, "Настил_дерево"))
        сделано.append(_короб("%s_козырёк" % имя, (xc, yc + наружу * (B / 2.0 + 0.45 + 0.012), zк + h_кор - 0.05), (L - 0.40, 0.90, 0.06), кол, "Контейнер_графит"))
    elif тип == "спа":
        for i in (-1, 1):
            сделано.append(_короб("%s_окно_%d" % (имя, i > 0), (xc + i * 1.4, yф, zc + 0.3), (0.70, 0.02, 0.70), кол, "Остекление"))
        сделано.append(_короб("%s_дверь" % имя, (xc, yв, zc - 0.15), (0.90, 0.02, 2.00), кол, "Надстройка_графит"))
        сделано.append(_цилиндр("%s_труба_печи" % имя, (xc + 1.8, yc, zк + h_кор + 0.40), 0.09, 0.80, кол, "Сталь_нерж"))
    elif тип == "офис":
        for yy, nm in ((yф, "ф"), (yв, "в")):
            сделано.append(_короб("%s_остекление_%s" % (имя, nm), (xc, yy, zc + 0.15), (L - 0.80, 0.02, 1.60), кол, "Остекление"))
    elif тип == "бар":
        сделано.append(_короб("%s_проём" % имя, (xc, yв, zc + 0.25), (L - 1.20, 0.02, 1.20), кол, "Остекление"))
        сделано.append(_короб("%s_стойка" % имя, (xc, yc - наружу * (B / 2.0 + 0.012 + 0.20), zк + 1.05), (L - 1.20, 0.40, 0.05), кол, "Настил_дерево"))
        for i in (-1, 1):
            сделано.append(_короб("%s_упор_стойки_%d" % (имя, i > 0), (xc + i * (L / 2.0 - 0.75), yc - наружу * (B / 2.0 + 0.012 + 0.20), zк + 0.515), (0.05, 0.05, 1.02), кол, "Надстройка_серебро"))
        сделано.append(_короб("%s_навес" % имя, (xc, yc - наружу * (B / 2.0 + 0.55), zк + h_кор + 0.10), (L - 0.60, 1.00, 0.04), кол, "Тент"))
    return сделано


def терраса(имя, x0, x1, yc, кол):
    """Терраса люкса в торцевом зазоре между двумя секциями - настил над фундаментами, стойки, стекло."""
    B = К["ширина"]
    z = Z_ПЛОЩАДКА + ФИТ[2]
    наружу = 1.0 if yc >= 0 else -1.0
    сделано = [_короб("%s_настил" % имя, (0.5 * (x0 + x1), yc, z + 0.03), (x1 - x0 - 0.06, B - 0.10, 0.06), кол, "Настил_дерево")]
    for yy in (yc - 1.0, yc + 1.0):
        сделано.append(_короб("%s_стойка_%d" % (имя, yy > yc), (0.5 * (x0 + x1), yy, 0.5 * (Z_НАСТИЛ + z)), (0.08, 0.08, z - Z_НАСТИЛ), кол, "Надстройка_серебро"))
    сделано.append(_короб("%s_стекло" % имя, (0.5 * (x0 + x1), yc + наружу * (B / 2.0 - 0.10), z + 0.06 + 0.55), (x1 - x0 - 0.10, 0.02, 1.10), кол, "Остекление"))
    return сделано


def _освободить(прямоугольники):
    """Мебель солярия (шезлонги базовой темы), попавшая на занятые слоты и террасы, убирается из сцены."""
    убрано = []
    for o in list(bpy.data.objects):
        if not o.name.startswith("Общ_") or o.type != "MESH":
            continue
        vs = [o.matrix_world @ Vector(c) for c in o.bound_box]
        x0, x1 = min(v.x for v in vs), max(v.x for v in vs)
        y0, y1 = min(v.y for v in vs), max(v.y for v in vs)
        z0 = min(v.z for v in vs)
        if abs(z0 - Z_НАСТИЛ) > 0.5:
            continue
        if any(x0 < px1 and x1 > px0 and y0 < py1 and y1 > py0 for px0, px1, py0, py1 in прямоугольники):
            убрано.append(o.name)
            bpy.data.objects.remove(o, do_unlink=True)
    return убрано


def собрать(тема="президентская", висит=None, подъём=0.0, verbose=True):
    """Фундаменты и модули темы. `висит` - слот, модуль которого поднят краном на `подъём` м (замки открыты)."""
    материалы()
    for к in (КОЛ_ФУНД, КОЛ_МОД):
        _очистить_кол(к)
    kф, kм = _кол(КОЛ_ФУНД), _кол(КОЛ_МОД)
    т = M.ТЕМЫ[тема]["модули"]
    сд = {s["слот"]: s for s in M.слоты()}
    n_ф = фундаменты(kф, set(т), открытые={висит} if висит else set())
    n_м = 0
    for слот, тип in sorted(т.items()):
        s = сд[слот]
        z0 = Z_ПЛОЩАДКА + (подъём if слот == висит else 0.0)
        n_м += len(контейнер("Мод_%s_%s" % (слот, тип), s["xc"], s["yc"], z0, тип, kм))
    # террасы между соседними секциями люкса одного ряда
    занято = [(сд[сл]["x0"], сд[сл]["x1"], сд[сл]["y0"], сд[сл]["y1"]) for сл in т]
    люксы = sorted((сд[сл] for сл, тип in т.items() if тип == "люкс"), key=lambda s: (s["yc"], s["xc"]))
    for a, b in zip(люксы, люксы[1:]):
        if abs(a["yc"] - b["yc"]) < 1e-6 and abs(b["x0"] - a["x1"] - M.ЗАЗОР_ВДОЛЬ) < 0.01:
            занято.append((a["x1"], b["x0"], a["y0"], a["y1"]))
            if висит not in (a["слот"], b["слот"]):
                n_м += len(терраса("Терраса_%s_%s" % (a["слот"], b["слот"]), a["x1"], b["x0"], a["yc"], kм))
    убрано = _освободить(занято)
    if verbose:
        print("Тема «%s» - фундаментов %d (объектов %d), модулей %d (объектов %d)%s, убрано с занятых слотов - %d" % (
            тема, len(M.фундаменты()), n_ф, len(т), n_м, ", на крюке %s +%.1f м" % (висит, подъём) if висит else "", len(убрано)))
    return n_ф, n_м


if __name__ == "__main__":
    собрать()
