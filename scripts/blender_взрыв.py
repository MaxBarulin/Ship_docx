# -*- coding: utf-8 -*-
"""Взрыв-схема судна: компоновочная схема изделия для дизайн-проекта (КЗ 2.1).

Запускается в открытой сессии Blender по MCP после `blender_судно.собрать()`:
    import blender_взрыв as В; В.рендер()
Сборки раздвигаются по вертикали и в стороны: корпус остаётся на месте,
палубы и ярусы поднимаются ступенями, колёса с кожухами выезжают по бортам,
рубка и солнечная палуба — выше всех. Сдвиги обратимы: после рендера всё
возвращается на место, модель не портится.
"""
import bpy, os, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUT = os.path.join(ROOT, "renders", "горизонт_2026", "виды")

#: (префиксы имён объектов, сдвиг (dx, dy, dz)); dy умножается на знак борта
СБОРКИ = [
    (("Палуба_главная", "Палуба_первая", "Переборка_ВНП", "Трюм_"), (0.0, 0.0, 3.0)),
    (("Надстройка_главная", "Цоколь_главная", "Карниз_главная", "Остекление_кают_главная", "Импост_главная", "Решётка_главная", "Проём_главная",
      "Каюта_", "Мебель_главная", "Переборка_главная", "Трап_", "Лифт_", "Гараж_", "Аппарель", "Ограждение_главной"), (0.0, 0.0, 6.5)),
    (("Палуба_прогулочная",), (0.0, 0.0, 10.5)),
    (("Надстройка_средняя", "Цоколь_средняя", "Карниз_средняя", "Остекление_кают_средняя", "Импост_средняя", "Решётка_средняя", "Проём_средняя",
      "Мебель_средняя", "Переборка_средняя", "Атриум_остекление", "Портал_", "Рамка_проёма", "Ласточка", "Акцент_линия"), (0.0, 0.0, 14.0)),
    (("Палуба_солнечная", "Ограждение_солнечной", "Солнечные_модули", "Труба", "Кнехт", "Якорная",
      "08_Фундаменты", "09_Модули"), (0.0, 0.0, 19.0)),
    (("Рубка", "Рубка_плавник"), (0.0, 0.0, 24.0)),
]
БОРТОВЫЕ = [(("Колесо_ПБ", "Кожух_ПБ", "Ласточка_ПБ"), (0.0, 9.0, 4.0)), (("Колесо_ЛБ", "Кожух_ЛБ", "Ласточка_ЛБ"), (0.0, -9.0, 4.0))]


def _объекты(префиксы):
    out = []
    for o in bpy.context.scene.objects:
        if o.type != "MESH":
            continue
        имя = o.name
        кол = o.users_collection[0].name if o.users_collection else ""
        if any(имя.startswith(p) or кол.startswith(p) for p in префиксы):
            out.append(o)
    return out


def сдвинуть(знак=1):
    сделано = []
    занятые = set()
    группы = [(p, d) for p, d in СБОРКИ] + [(p, d) for p, d in БОРТОВЫЕ]
    # порядок: бортовые первыми, чтобы колёса не попали в «главную» по коллекции
    for префиксы, (dx, dy, dz) in list(БОРТОВЫЕ) + list(СБОРКИ):
        for o in _объекты(префиксы):
            if o.name in занятые:
                continue
            занятые.add(o.name)
            o.location.x += знак * dx; o.location.y += знак * dy; o.location.z += знак * dz
            сделано.append((o.name, dx, dy, dz))
    return сделано


def подписи():
    """Подписи сборок текстом рядом с моделью — для схемы."""
    пометки = [("Корпус, второе дно, цистерны, трюм: ГДГ, приводы колёс", 0.0),
               ("Главная палуба: гараж, атриум, ресторан, театр, каюты", 6.5),
               ("Прогулочная палуба (крыша первого яруса)", 10.5),
               ("Средняя палуба: каюты, атриум, спа; портал с колёсами", 14.0),
               ("Солнечная палуба: 72 фундамента-замка, модули темы, навес с солнечными панелями", 19.0),
               ("Рубка", 24.0)]
    сделано = []
    for i, (т, dz) in enumerate(пометки):
        cu = bpy.data.curves.new("_взрыв_подпись_%d" % i, "FONT")
        cu.body = т; cu.size = 2.0
        ob = bpy.data.objects.new("_взрыв_подпись_%d" % i, cu)
        bpy.context.scene.collection.objects.link(ob)
        # столбик подписей перед судном, снизу вверх в порядке сборок; шаг ровный —
        # сверху под углом строки сжимаются, и при шаге по dz они наезжали друг на друга
        ob.location = (6.0, -44.0, 3.0 + 4.2 * i)
        ob.rotation_euler = (math.radians(90), 0, math.radians(-8))
        if hasattr(ob, "visible_glossy"):
            ob.visible_glossy = False           # без отражения в воде: зеркальные строки читались как мусор
        сделано.append(ob)
    return сделано


def рендер(samples=96, res=(2400, 1500), cycles=False):
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    сдвиги = сдвинуть(1)
    тексты = подписи()
    cam = sc.camera
    if cam is None:
        cam = bpy.data.objects.get("_взрыв_камера")
        if cam is None:
            cam = bpy.data.objects.new("_взрыв_камера", bpy.data.cameras.new("_взрыв_камера"))
            sc.collection.objects.link(cam)
        sc.camera = cam
    было = (tuple(cam.location), tuple(cam.rotation_euler), cam.data.lens, cam.data.type)
    from mathutils import Vector
    cam.data.type = "PERSP"
    cam.location = (-70.0, -120.0, 52.0)
    look = Vector((62.0, 0.0, 13.0)) - cam.location
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 38
    cam.data.clip_end = 80000.0       # вода до горизонта: при коротком clip_end под горизонтом тёмная полоса
    r = sc.render
    было_r = (r.resolution_x, r.resolution_y, r.filepath, r.engine)
    r.resolution_x, r.resolution_y = res
    # схема, а не картинка: EEVEE даёт её за секунды и не роняет MCP по таймауту
    if cycles:
        r.engine = "CYCLES"
        sc.cycles.samples = samples
    else:
        for eng in ("BLENDER_EEVEE_NEXT", "BLENDER_EEVEE"):
            try:
                r.engine = eng; break
            except Exception:
                pass
    r.filepath = os.path.join(OUT, "09_взрыв_схема.png")
    bpy.ops.render.render(write_still=True)
    путь = r.filepath
    # вернуть всё
    сдвинуть(-1)
    for t in тексты:
        bpy.data.objects.remove(t, do_unlink=True)
    cam.location, cam.rotation_euler, cam.data.lens, cam.data.type = было
    r.resolution_x, r.resolution_y, r.filepath, r.engine = было_r
    return путь, len(сдвиги)
