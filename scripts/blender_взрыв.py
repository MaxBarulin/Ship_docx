# -*- coding: utf-8 -*-
"""Взрыв-схема судна: компоновочная схема изделия для дизайн-проекта (КЗ 2.1).

Запускается в открытой сессии Blender по MCP после `blender_судно.собрать()`:
    import blender_взрыв as В; В.рендер()
Сборки раздвигаются по вертикали и в стороны: корпус остаётся на месте,
палубы и ярусы поднимаются ступенями, колёса с кожухами выезжают по бортам,
рубка и солнечная палуба — выше всех. Сдвиги обратимы: после рендера всё
возвращается на место, модель не портится.

Подписи сборок — не 3D-текст в сцене (его закрывало колесо, он терялся белым
по светлому корпусу и не совпадал по высоте со своей сборкой), а выноски
поверх рендера: Blender проецирует точку на каждой сборке камерой, а
`scripts/подписи_рендера.py` (в .venv проекта — в Python Blender нет PIL)
рисует столбец подписей у правого края с выносками до этих точек.
"""
import bpy, os, math, json, subprocess, tempfile
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


#: Подписи сборок: текст и префиксы объектов для точки выноски. Точки всех ярусов — на одной абсциссе
#: X_ВЫНОСКИ в носовой части, где есть все ярусы: тогда порядок точек по высоте совпадает с порядком сборок,
#: и выноски к столбцу подписей идут веером без пересечений; колесо — в центре своей сборки.
X_ВЫНОСКИ = 104.0
ПОДПИСИ = [
    ("Корпус: второе дно, цистерны метанола и воды, трюм — ГДГ, ГРЩ, приводы колёс", ("Корпус",), X_ВЫНОСКИ),
    ("Первая и главная палубы, водонепроницаемые переборки, оборудование трюма", ("Палуба_главная", "Палуба_первая", "Переборка_ВНП", "Трюм_"), X_ВЫНОСКИ),
    ("Первый ярус: гараж и аппарель, атриум, ресторан, театр-лаунж, каюты", ("Надстройка_главная", "Каюта_", "Гараж_"), X_ВЫНОСКИ),
    ("Прогулочная палуба — крыша первого яруса", ("Палуба_прогулочная",), X_ВЫНОСКИ),
    ("Второй ярус: каюты, верх атриума, спа; портал колёс", ("Надстройка_средняя", "Портал_"), X_ВЫНОСКИ),
    ("Солнечная палуба: 72 фундамента-замка ВГ-2026.46.00, модули темы, навес с солнечными панелями", ("Палуба_солнечная", "08_Фундаменты", "09_Модули"), X_ВЫНОСКИ),
    ("Рулевая рубка, стационарная", ("Рубка",), X_ВЫНОСКИ),
    ("Гребное колесо Ø4,90 с кожухом — выдвинуто по борту", ("Колесо_ЛБ", "Кожух_ЛБ"), None),
]


def _точка(префиксы, x_точки):
    """Точка выноски: на ближнем к камере борту сборки (y — минимум), по длине — x_точки (None — середина сборки),
    по высоте — середина сборки."""
    from mathutils import Vector
    xs, ys, zs = [], [], []
    for o in _объекты(префиксы):
        for c in o.bound_box:
            w = o.matrix_world @ Vector(c)
            xs.append(w.x); ys.append(w.y); zs.append(w.z)
    if not xs:
        return None
    x = 0.5 * (min(xs) + max(xs)) if x_точки is None else min(max(x_точки, min(xs)), max(xs))
    return Vector((x, min(ys), 0.5 * (min(zs) + max(zs))))


def _подписи_поверх(sc, cam, база, выход):
    from bpy_extras.object_utils import world_to_camera_view
    W, H = sc.render.resolution_x, sc.render.resolution_y
    якоря = []
    for текст, префиксы, x_точки in ПОДПИСИ:
        p = _точка(префиксы, x_точки)
        if p is None:
            continue
        u, v, _ = world_to_camera_view(sc, cam, p)
        якоря.append({"текст": текст, "x": round(u * W, 1), "y": round((1.0 - v) * H, 1)})
    jp = os.path.join(tempfile.gettempdir(), "_подписи_09_взрыв.json")
    json.dump({"стиль": "сборки", "заголовок": "Компоновочная схема «Волжского Горизонта» (взрыв-модель)",
               "подзаголовок": "сборки судна раздвинуты по высоте, колесо с кожухом — по борту",
               "якоря": якоря}, open(jp, "w", encoding="utf-8"), ensure_ascii=False)
    py = os.path.join(ROOT, ".venv", "Scripts", "python.exe")
    if not os.path.exists(py):
        py = "python"
    r = subprocess.run([py, "-X", "utf8", os.path.join(ROOT, "scripts", "подписи_рендера.py"), база, jp, выход],
                       capture_output=True, text=True, encoding="utf-8")
    if r.returncode != 0:
        raise RuntimeError("подписи_рендера: " + r.stderr[-400:])
    return выход


def рендер(samples=96, res=(2400, 1500), cycles=False):
    os.makedirs(OUT, exist_ok=True)
    sc = bpy.context.scene
    сдвиги = сдвинуть(1)
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
    # цель смещена вправо по кадру: судно слева, справа — столбец подписей
    look = Vector((80.0, -20.0, 12.0)) - cam.location
    cam.rotation_euler = look.to_track_quat("-Z", "Y").to_euler()
    cam.data.lens = 30
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
    база = os.path.join(tempfile.gettempdir(), "_09_взрыв_база.png")
    r.filepath = база
    r.image_settings.file_format = "PNG"
    bpy.ops.render.render(write_still=True)
    путь = _подписи_поверх(sc, cam, база, os.path.join(OUT, "09_взрыв_схема.jpg"))
    # вернуть всё
    сдвинуть(-1)
    cam.location, cam.rotation_euler, cam.data.lens, cam.data.type = было
    r.resolution_x, r.resolution_y, r.filepath, r.engine = было_r
    return путь, len(сдвиги)
