# -*- coding: utf-8 -*-
r"""Эталоны кают: параметрическая сборка с проверкой на пересечения.

Каждая каюта — список именованных объёмов в местной системе координат:
    x — вдоль борта (длина каюты), y — от борта внутрь, z — от пола.
Перед сборкой список прогоняется через check(): если два предмета
пересекаются по всем трём осям больше чем на 5 мм, сборка не начинается.
Поэтому «предметы влезают друг в друга» здесь невозможно по построению.

Запуск внутри Blender:
    exec(open(r"E:\Ship_docx\scripts\blender_каюты.py", encoding="utf-8").read())
    rebuild_prototypes()
"""
import bpy, bmesh, math, mathutils, os

ROOT_SRC = r"E:\Ship_docx\src"

M = mathutils.Matrix
T_WALL = 0.05
H_ROOM = 2.20
EPS = 0.005


# --------------------------------------------------------------- примитивы --
class Part:
    __slots__ = ("name", "box", "mat", "kind", "meta")

    def __init__(self, name, box, mat, kind="box", meta=None):
        self.name = name
        self.box = tuple(round(v, 4) for v in box)   # x0,x1,y0,y1,z0,z1
        self.mat = mat
        self.kind = kind
        self.meta = meta or {}

    def __repr__(self):
        return "%s %s" % (self.name, self.box)


def P(name, x0, x1, y0, y1, z0, z1, mat, kind="box", **meta):
    return Part(name, (x0, x1, y0, y1, z0, z1), mat, kind, meta)


def _ov(a0, a1, b0, b1):
    return min(a1, b1) - max(a0, b0)


def check(parts, allow=()):
    """Пары предметов, пересекающихся по всем трём осям."""
    bad = []
    allow = set(tuple(sorted(p)) for p in allow)
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            a, b = parts[i], parts[j]
            key = tuple(sorted((a.name, b.name)))
            if key in allow:
                continue
            dx = _ov(a.box[0], a.box[1], b.box[0], b.box[1])
            dy = _ov(a.box[2], a.box[3], b.box[2], b.box[3])
            dz = _ov(a.box[4], a.box[5], b.box[4], b.box[5])
            if dx > EPS and dy > EPS and dz > EPS:
                bad.append((a.name, b.name, round(min(dx, dy, dz), 3)))
    return bad


def _box(bm, b):
    x0, x1, y0, y1, z0, z1 = b
    bmesh.ops.create_cube(bm, size=1.0,
        matrix=M.Translation(((x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2))
        @ M.Diagonal((max(x1 - x0, 1e-4), max(y1 - y0, 1e-4), max(z1 - z0, 1e-4), 1.0)))


def _cyl(bm, b, seg=16, axis="Z"):
    x0, x1, y0, y1, z0, z1 = b
    cx, cy, cz = (x0 + x1) / 2, (y0 + y1) / 2, (z0 + z1) / 2
    if axis == "Z":
        r = min(x1 - x0, y1 - y0) / 2
        rot = M.Identity(4); d = z1 - z0
    elif axis == "X":
        r = min(y1 - y0, z1 - z0) / 2
        rot = M.Rotation(math.radians(90), 4, 'Y'); d = x1 - x0
    else:
        r = min(x1 - x0, z1 - z0) / 2
        rot = M.Rotation(math.radians(90), 4, 'X'); d = y1 - y0
    bmesh.ops.create_cone(bm, cap_ends=True, cap_tris=False, segments=seg,
                          radius1=r, radius2=r, depth=d,
                          matrix=M.Translation((cx, cy, cz)) @ rot)


def check_fit(parts, W, D, h=H_ROOM):
    """Всё ли внутри каюты и свободен ли проход у двери."""
    bad = []
    for p in parts:
        x0, x1, y0, y1, z0, z1 = p.box
        if p.name.startswith(("пол", "подволок", "переборка", "окно", "балкон",
                              "дверь", "проём", "карниз", "штора", "плинтус",
                              "ограждение", "настил")):
            continue
        if x0 < -EPS or x1 > W + EPS or y0 < -EPS or y1 > D + EPS                 or z0 < -EPS or z1 > h + EPS:
            bad.append(("вне габарита", p.name, p.box))
    return bad


def build(name, parts, collection="20_Эталоны_кают", origin=(0, 0, 0)):
    """Собрать каюту в один объект с материалами по частям."""
    mats = []
    idx = {}
    for p in parts:
        if p.mat not in idx:
            idx[p.mat] = len(mats)
            mats.append(p.mat)
    bm = bmesh.new()
    faces_from = []
    for p in parts:
        n0 = len(bm.faces)
        if p.kind == "cyl":
            _cyl(bm, p.box, p.meta.get("seg", 16), p.meta.get("axis", "Z"))
        else:
            _box(bm, p.box)
        bm.faces.ensure_lookup_table()
        faces_from.append((n0, len(bm.faces), idx[p.mat]))
    bm.faces.ensure_lookup_table()
    for (a, b, mi) in faces_from:
        for k in range(a, b):
            bm.faces[k].material_index = mi
    me = bpy.data.meshes.new(name)
    bm.normal_update()
    bm.to_mesh(me)
    bm.free()
    old = bpy.data.objects.get(name)
    if old:
        bpy.data.objects.remove(old, do_unlink=True)
    o = bpy.data.objects.new(name, me)
    col = bpy.data.collections.get(collection)
    if col is None:
        col = bpy.data.collections.new(collection)
        bpy.context.scene.collection.children.link(col)
    col.objects.link(o)
    for mn in mats:
        o.data.materials.append(bpy.data.materials.get(mn)
                                or bpy.data.materials.new(mn))
    o.location = origin
    return o


# ------------------------------------------------------------- наполнение --
def shell(W, D, door_x0, door_w, win=True, balcony=False):
    """Пол, подволок, переборки с дверным проёмом и окном."""
    p = []
    t = T_WALL
    p.append(P("пол", 0, W, 0, D, -0.02, 0.0, "гор_ковролин"))
    p.append(P("подволок", 0, W, 0, D, H_ROOM, H_ROOM + 0.06, "гор_подволок"))
    # борт с окном
    if win:
        wx0, wx1 = 0.45, W - 0.45
        p.append(P("борт_низ", 0, W, 0, t, 0.0, 0.95, "гор_переборка"))
        p.append(P("борт_верх", 0, W, 0, t, 2.00, H_ROOM, "гор_переборка"))
        p.append(P("борт_слева", 0, wx0, 0, t, 0.95, 2.00, "гор_переборка"))
        p.append(P("борт_справа", wx1, W, 0, t, 0.95, 2.00, "гор_переборка"))
        p.append(P("окно", wx0, wx1, 0.008, t - 0.008, 0.95, 2.00, "гор_стекло_каюты"))
        p.append(P("штора_л", wx0 - 0.10, wx0 + 0.28, t, t + 0.07, 0.95, 2.12,
                   "гор_текстиль_тёплый"))
        p.append(P("штора_п", wx1 - 0.28, wx1 + 0.10, t, t + 0.07, 0.95, 2.12,
                   "гор_текстиль_тёплый"))
        p.append(P("карниз", wx0 - 0.14, wx1 + 0.14, t, t + 0.09, 2.12, 2.16,
                   "гор_металл"))
    else:
        p.append(P("борт", 0, W, 0, t, 0.0, H_ROOM, "гор_переборка"))
    # коридорная переборка с дверью
    p.append(P("коридор_лево", 0, door_x0, D - t, D, 0.0, H_ROOM, "гор_переборка"))
    p.append(P("коридор_право", door_x0 + door_w, W, D - t, D, 0.0, H_ROOM,
               "гор_переборка"))
    p.append(P("коридор_над_дверью", door_x0, door_x0 + door_w, D - t, D, 2.05,
               H_ROOM, "гор_переборка"))
    p.append(P("дверь", door_x0 + 0.01, door_x0 + door_w - 0.01, D - t + 0.008,
               D - 0.008, 0.0, 2.05, "гор_дерево"))
    p.append(P("ручка_двери", door_x0 + door_w - 0.16, door_x0 + door_w - 0.06,
               D - t - 0.03, D - t + 0.005, 1.03, 1.09, "гор_металл"))
    # поперечные переборки
    p.append(P("переборка_нос", 0, t, t, D - t, 0.0, H_ROOM, "гор_переборка"))
    p.append(P("переборка_корма", W - t, W, t, D - t, 0.0, H_ROOM, "гор_переборка"))
    return p


def bathroom(x0, y0, w, d, roll_in=False):
    """Санузел: перегородки с дверным проёмом, душ, раковина, унитаз.

    Планировка: дверь в ближней переборке слева, раковина слева от входа,
    унитаз справа, душ в дальнем углу. Зоны не пересекаются по построению.
    """
    t = 0.04
    x1, y1 = x0 + w, y0 + d
    ix0, ix1 = x0, x1 - t            # чистый габарит по x
    iy0, iy1 = y0 + t, y1            # по y
    IW, ID = ix1 - ix0, iy1 - iy0
    dw = min(0.78 if not roll_in else 0.92, IW - 0.55)
    dx0 = ix0 + 0.05
    p = [
        P("су_стена_x", x1 - t, x1, y0, y1, 0.0, H_ROOM, "гор_плитка"),
        P("су_стена_y_л", x0, dx0, y0, y0 + t, 0.0, H_ROOM, "гор_плитка"),
        P("су_стена_y_п", dx0 + dw, x1 - t, y0, y0 + t, 0.0, H_ROOM, "гор_плитка"),
        P("су_стена_y_над", dx0, dx0 + dw, y0, y0 + t, 2.03, H_ROOM, "гор_плитка"),
        P("су_дверь", dx0 + 0.01, dx0 + dw - 0.01, y0 + t * 0.3, y0 + t * 0.7,
          0.0, 2.02, "гор_стекло_каюты"),
        P("су_пол", ix0, ix1, iy0, iy1, 0.0, 0.022, "гор_плитка"),
    ]
    # раковина со столешницей — слева от входа
    bw_ = min(0.62, IW * 0.44)
    p += [
        P("су_столешница", ix0 + 0.03, ix0 + 0.03 + bw_, iy0 + 0.03, iy0 + 0.50,
          0.80, 0.86, "гор_дерево"),
        P("су_раковина", ix0 + 0.12, ix0 + 0.12 + bw_ - 0.18, iy0 + 0.12, iy0 + 0.44,
          0.70, 0.80, "гор_бельё"),
        P("су_смеситель", ix0 + 0.03 + bw_ / 2 - 0.03, ix0 + 0.03 + bw_ / 2 + 0.03,
          iy0 + 0.05, iy0 + 0.11, 0.86, 1.00, "гор_металл", kind="cyl"),
        P("су_зеркало", ix0 + 0.03, ix0 + 0.03 + bw_, iy0 + 0.005, iy0 + 0.02,
          1.00, 1.86, "гор_экран"),
        P("су_полотенце", ix0 + 0.06, ix0 + 0.26, iy0 + 0.54, iy0 + 0.59,
          0.92, 1.18, "гор_бельё"),
    ]
    # унитаз — справа
    wy0 = iy0 + 0.34
    wc_x1 = ix1 - 0.02
    wc_x0 = max(ix1 - 0.58, ix0 + 0.03 + min(0.92, IW * 0.52) + 0.06)
    p += [
        P("унитаз_бак", wc_x1 - 0.18, wc_x1, wy0, wy0 + 0.40, 0.28, 0.92,
          "гор_бельё"),
        P("унитаз_чаша", wc_x0, wc_x1 - 0.20, wy0 + 0.02, wy0 + 0.38, 0.02, 0.42,
          "гор_бельё"),
        P("унитаз_крышка", wc_x0, wc_x1 - 0.20, wy0 + 0.02, wy0 + 0.38,
          0.42, 0.46, "гор_бельё"),
    ]
    # душ в дальнем углу
    sw = min(0.92, IW * 0.52)
    sd = min(0.95, (iy1 - 0.03) - (iy0 + 0.66))
    sx0, sx1 = ix0 + 0.03, ix0 + 0.03 + sw
    sy1, sy0 = iy1 - 0.03, iy1 - 0.03 - sd
    p += [
        P("душ_поддон", sx0, sx1, sy0, sy1, 0.022, 0.032 if roll_in else 0.13,
          "гор_плитка"),
        P("душ_стекло_1", sx1, sx1 + 0.012, sy0, sy1, 0.05, 2.02,
          "гор_стекло_каюты"),
        P("душ_стекло_2", sx0, sx1, sy0 - 0.012, sy0, 0.05, 2.02,
          "гор_стекло_каюты"),
        P("душ_лейка", sx0 + 0.06, sx0 + 0.18, sy1 - 0.20, sy1 - 0.08, 1.96, 2.02,
          "гор_металл"),
        P("душ_смеситель", sx0 + 0.04, sx0 + 0.12, sy1 - 0.24, sy1 - 0.14,
          1.05, 1.22, "гор_металл", kind="cyl", axis="Y"),
    ]
    if roll_in:
        p += [
            P("поручень_душ", sx0 + 0.05, sx0 + 0.09, sy0 + 0.08, sy1 - 0.08,
              0.83, 0.87, "гор_металл", kind="cyl", axis="Y"),
            P("поручень_унитаз", ix1 - 0.68, ix1 - 0.64, wy0 - 0.04, wy0 + 0.44,
              0.83, 0.87, "гор_металл", kind="cyl", axis="Y"),
            P("кнопка_вызова", ix1 - 0.08, ix1 - 0.02, wy0 + 0.44, wy0 + 0.52,
              0.88, 0.96, "гор_акцент"),
        ]
    return p


def bed(x0, y0, w, d, twin=False, nightstand="right"):
    """Кровать: основание, матрас, одеяло, подушки, прикроватная тумба."""
    p = []
    x1, y1 = x0 + w, y0 + d
    p.append(P("кровать_основание", x0, x1, y0, y1, 0.06, 0.34, "гор_дерево"))
    p.append(P("кровать_цоколь", x0 + 0.04, x1 - 0.04, y0 + 0.04, y1 - 0.04,
               0.0, 0.06, "гор_металл"))
    p.append(P("матрас", x0 + 0.01, x1 - 0.01, y0 + 0.01, y1 - 0.01, 0.34, 0.50,
               "гор_бельё"))
    p.append(P("одеяло", x0 + 0.02, x1 - 0.02, y0 + 0.02, y1 - 0.50, 0.50, 0.58,
               "гор_текстиль_тёплый"))
    n = 2 if not twin else 1
    pw = (w - 0.10) / n
    for k in range(n):
        p.append(P("подушка_%d" % k, x0 + 0.05 + k * pw, x0 + 0.05 + (k + 1) * pw - 0.04,
                   y1 - 0.46, y1 - 0.10, 0.50, 0.62, "гор_бельё"))
    p.append(P("изголовье", x0 - 0.02, x1 + 0.02, y1, y1 + 0.06, 0.34, 1.15,
               "гор_текстиль"))
    return p


def nightstand(x0, y0, w=0.42, d=0.40, lamp=True):
    p = [P("тумба", x0, x0 + w, y0, y0 + d, 0.0, 0.52, "гор_дерево"),
         P("тумба_ящик", x0 + 0.02, x0 + w - 0.02, y0 + d, y0 + d + 0.018,
           0.30, 0.48, "гор_дерево_светлое")]
    if lamp:
        p.append(P("лампа_ножка", x0 + w / 2 - 0.03, x0 + w / 2 + 0.03,
                   y0 + d / 2 - 0.03, y0 + d / 2 + 0.03, 0.52, 0.72,
                   "гор_акцент_латунь", kind="cyl"))
        p.append(P("лампа_абажур", x0 + w / 2 - 0.11, x0 + w / 2 + 0.11,
                   y0 + d / 2 - 0.11, y0 + d / 2 + 0.11, 0.72, 0.90,
                   "гор_текстиль_тёплый", kind="cyl"))
    return p


def wardrobe(x0, y0, w, d, h=2.02):
    return [
        P("шкаф_корпус", x0, x0 + w, y0, y0 + d, 0.0, h, "гор_дерево"),
        P("шкаф_дверь_1", x0 + 0.01, x0 + w / 2 - 0.005, y0 + d, y0 + d + 0.02,
          0.03, h - 0.03, "гор_дерево_светлое"),
        P("шкаф_дверь_2", x0 + w / 2 + 0.005, x0 + w - 0.01, y0 + d, y0 + d + 0.02,
          0.03, h - 0.03, "гор_дерево_светлое"),
        P("шкаф_ручки", x0 + w / 2 - 0.02, x0 + w / 2 + 0.02, y0 + d + 0.02,
          y0 + d + 0.05, 1.00, 1.30, "гор_акцент_латунь"),
    ]


def desk(x0, y0, w, d, chair=True, tv=True, wall_y=None, chair_side=1):
    p = [P("стол", x0, x0 + w, y0, y0 + d, 0.70, 0.75, "гор_дерево"),
         P("стол_опора_л", x0 + 0.03, x0 + 0.09, y0 + 0.04, y0 + d - 0.04,
           0.0, 0.70, "гор_металл"),
         P("стол_опора_п", x0 + w - 0.09, x0 + w - 0.03, y0 + 0.04, y0 + d - 0.04,
           0.0, 0.70, "гор_металл")]
    if chair:
        cx = x0 + w / 2
        if chair_side > 0:
            c0, c1 = y0 + d + 0.06, y0 + d + 0.52
            b0, b1 = y0 + d + 0.46, y0 + d + 0.54
        else:
            c0, c1 = y0 - 0.52, y0 - 0.06
            b0, b1 = y0 - 0.54, y0 - 0.46
        p += [P("кресло_сиденье", cx - 0.24, cx + 0.24, c0, c1, 0.42, 0.50,
                "гор_текстиль"),
              P("кресло_спинка", cx - 0.24, cx + 0.24, b0, b1, 0.50, 0.95,
                "гор_текстиль"),
              P("кресло_нога", cx - 0.04, cx + 0.04, (c0 + c1) / 2 - 0.04,
                (c0 + c1) / 2 + 0.04, 0.0, 0.42, "гор_металл", kind="cyl")]
    if tv and wall_y is not None:
        p.append(P("телевизор", x0 + w / 2 - 0.45, x0 + w / 2 + 0.45,
                   wall_y[0], wall_y[1], 1.05, 1.58, "гор_экран"))
    return p


def lights(x0, x1, y0, y1, n=2):
    """Светильники в свободной зоне каюты."""
    p = []
    for k in range(n):
        cx = x0 + (x1 - x0) * (k + 1) / (n + 1)
        cy = (y0 + y1) / 2
        p.append(P("светильник_%d" % k, cx - 0.16, cx + 0.16, cy - 0.16, cy + 0.16,
                   H_ROOM - 0.05, H_ROOM, "гор_щит", kind="cyl"))
    return p


def bed2(x0, y0, w, d, head_at="y0", twin=False):
    """Кровать с изголовьем у борта (head_at='y0') или у коридора."""
    p = []
    x1, y1 = x0 + w, y0 + d
    p.append(P("кровать_основание", x0, x1, y0, y1, 0.06, 0.34, "гор_дерево"))
    p.append(P("кровать_цоколь", x0 + 0.04, x1 - 0.04, y0 + 0.04, y1 - 0.04,
               0.0, 0.06, "гор_металл"))
    p.append(P("матрас", x0 + 0.01, x1 - 0.01, y0 + 0.01, y1 - 0.01, 0.34, 0.50,
               "гор_бельё"))
    if head_at == "y0":
        p.append(P("одеяло", x0 + 0.02, x1 - 0.02, y0 + 0.52, y1 - 0.02, 0.50, 0.58,
                   "гор_текстиль_тёплый"))
        py0, py1 = y0 + 0.08, y0 + 0.46
        p.append(P("изголовье", x0 - 0.02, x1 + 0.02, y0 - 0.06, y0, 0.34, 1.15,
                   "гор_текстиль"))
    else:
        p.append(P("одеяло", x0 + 0.02, x1 - 0.02, y0 + 0.02, y1 - 0.52, 0.50, 0.58,
                   "гор_текстиль_тёплый"))
        py0, py1 = y1 - 0.46, y1 - 0.08
        p.append(P("изголовье", x0 - 0.02, x1 + 0.02, y1, y1 + 0.06, 0.34, 1.15,
                   "гор_текстиль"))
    n = 1 if twin else 2
    pw = (w - 0.12) / n
    for k in range(n):
        p.append(P("подушка_%d" % k, x0 + 0.06 + k * pw, x0 + 0.06 + (k + 1) * pw - 0.04,
                   py0, py1, 0.50, 0.62, "гор_бельё"))
    return p


def free_circle(parts, W, D, r=0.75, step=0.05):
    """Центр круга разворота 2r на свободном полу (или None)."""
    t = T_WALL
    blockers = []
    for q in parts:
        x0, x1, y0, y1, z0, z1 = q.box
        if z0 > 0.32 or z1 < 0.02:          # висящее или плоское — не мешает
            continue
        if q.name.startswith(("пол", "ковёр", "круг", "подволок", "разметка")):
            continue
        blockers.append((x0, x1, y0, y1))
    lo_x, hi_x = t + r, W - t - r
    lo_y, hi_y = t + r, D - t - r
    if hi_x < lo_x or hi_y < lo_y:
        return None
    best = None
    nx = max(1, int((hi_x - lo_x) / step) + 1)
    ny = max(1, int((hi_y - lo_y) / step) + 1)
    for i in range(nx):
        cx = lo_x + i * step
        if cx > hi_x:
            cx = hi_x
        for j in range(ny):
            cy = lo_y + j * step
            if cy > hi_y:
                cy = hi_y
            ok = True
            for x0, x1, y0, y1 in blockers:
                if x0 < cx + r - EPS and x1 > cx - r + EPS                         and y0 < cy + r - EPS and y1 > cy - r + EPS:
                    ok = False
                    break
            if ok:
                d = abs(cx - W / 2) + abs(cy - D / 2)
                if best is None or d < best[0]:
                    best = (d, cx, cy)
    return None if best is None else (best[1], best[2])


def books(cx, cy, z, n=2):
    """Стопка книг — мелочь, без которой кадр выглядит нежилым."""
    p = []
    for k in range(n):
        p.append(P("книга_%d" % k, cx - 0.085, cx + 0.085, cy - 0.115,
                   cy + 0.115, z + k * 0.034, z + (k + 1) * 0.032,
                   "гор_акцент" if k % 2 else "гор_дерево_светлое"))
    return p


def vase(cx, cy, z):
    return [P("ваза", cx - 0.075, cx + 0.075, cy - 0.075, cy + 0.075,
              z, z + 0.24, "гор_фарфор", kind="cyl"),
            P("цветы", cx - 0.135, cx + 0.135, cy - 0.135, cy + 0.135,
              z + 0.24, z + 0.46, "гор_цветы", kind="cyl")]


def tray(cx, cy, z):
    p = [P("поднос", cx - 0.19, cx + 0.19, cy - 0.13, cy + 0.13, z,
           z + 0.016, "гор_акцент_латунь")]
    for k, dx in enumerate((-0.10, 0.10)):
        p.append(P("бокал_%d" % k, cx + dx - 0.035, cx + dx + 0.035,
                   cy - 0.035, cy + 0.035, z + 0.016, z + 0.17,
                   "гор_стекло_каюты", kind="cyl"))
    return p


def art(x0, x1, y_wall, z0=1.12, h=0.64, t=0.035):
    """Картина на переборке коридора."""
    return [P("картина", x0, x1, y_wall - t, y_wall, z0, z0 + h,
              "гор_картина")]


def bathmat(x0, y0, w=0.60, d=0.42):
    return [P("коврик", x0, x0 + w, y0, y0 + d, 0.004, 0.018,
              "гор_ковёр")]


def layout(W, D, kind="стандарт", window=True, accessible=False, balcony=False):
    """Расстановка каюты. Возвращает список объёмов без пересечений."""
    t = T_WALL
    ix1, iy1 = W - t, D - t
    BW = {"эконом": 1.30, "стандарт": 1.55, "бизнес": 1.75, "люкс": 2.30,
          "экипаж": 1.25}[kind]
    BD = {"эконом": 1.45, "стандарт": 1.55, "бизнес": 1.60, "люкс": 2.05,
          "экипаж": 1.30}[kind]
    if accessible:
        BW, BD = max(BW, 2.05), max(BD, 1.95)
    door_w = 0.90 if accessible else 0.80
    door_x0 = min(t + BW + 0.22, ix1 - door_w - 0.12)
    parts = shell(W, D, door_x0, door_w, window and not balcony, balcony)
    parts += bathroom(t, iy1 - BD, BW, BD, roll_in=accessible)

    bx0 = t + BW + 0.12                      # начало свободной зоны
    free_w = ix1 - bx0
    tv_x = t + BW
    parts.append(P("телевизор", tv_x, tv_x + 0.045, iy1 - BD + 0.30,
                   iy1 - BD + 1.20, 1.22, 1.74, "гор_экран"))

    if kind == "экипаж":
        bed_w = min(0.95, free_w - 0.06)
        parts += bed2(bx0 + 0.03, t + 0.16, bed_w, 1.90, "y0", twin=True)
        parts += wardrobe(t, iy1 - BD - 0.66, min(0.56, BW - 0.06), 0.56)
        ww2 = min(0.56, BW - 0.06)
        dw = min(1.05, BW - ww2 - 0.12)
        if dw > 0.55:
            parts += desk(t + BW - dw, t + 0.02, dw, 0.46, chair=True, tv=False,
                          chair_side=1)
        parts += lights(bx0, ix1, t, iy1 - BD, 1)
        return parts

    if kind == "люкс":
        bed_w = 1.80
        bx = t + BW + 0.42
        parts += bed2(bx, t + 0.55, bed_w, 2.05, "y0")
        parts += nightstand(bx - 0.50, t + 0.60)
        parts += nightstand(bx + bed_w + 0.08, t + 0.60)
        parts += wardrobe(t, iy1 - BD - 0.78, 1.05, 0.62)
        parts += [P("банкетка", bx + 0.12, bx + bed_w - 0.12, t + 2.70, t + 3.12,
                    0.0, 0.44, "гор_текстиль"),
                  P("банкетка_плед", bx + 0.20, bx + bed_w - 0.20, t + 2.76,
                    t + 3.06, 0.44, 0.50, "гор_текстиль_тёплый")]
        # гостиная зона у коридорной переборки
        sx = bx + bed_w + 0.72
        sw_ = min(2.10, ix1 - sx - 0.55)
        parts += [P("диван_основание", sx, sx + sw_, iy1 - 0.92, iy1 - 0.08,
                    0.014, 0.40, "гор_дерево"),
                  P("диван_сиденье", sx + 0.03, sx + sw_ - 0.03, iy1 - 0.90,
                    iy1 - 0.26, 0.40, 0.50, "гор_текстиль"),
                  P("диван_спинка", sx + 0.03, sx + sw_ - 0.03, iy1 - 0.24,
                    iy1 - 0.08, 0.40, 0.88, "гор_текстиль"),
                  P("диван_подушка_л", sx + 0.12, sx + 0.54, iy1 - 0.44, iy1 - 0.28,
                    0.50, 0.80, "гор_текстиль_тёплый"),
                  P("диван_подушка_п", sx + sw_ - 0.54, sx + sw_ - 0.12, iy1 - 0.44,
                    iy1 - 0.28, 0.50, 0.80, "гор_текстиль_тёплый"),
                  P("ковёр", sx - 0.25, sx + sw_ + 0.25, iy1 - 2.60, iy1 - 0.05,
                    0.0, 0.012, "гор_ковёр"),
                  P("столик", sx + sw_ / 2 - 0.48, sx + sw_ / 2 + 0.48,
                    iy1 - 1.78, iy1 - 1.14, 0.016, 0.42, "гор_дерево_светлое"),
                  P("кресло_осн", sx + 0.18, sx + 0.96, iy1 - 2.72, iy1 - 1.94,
                    0.014, 0.40, "гор_дерево"),
                  P("кресло_сид", sx + 0.21, sx + 0.93, iy1 - 2.54, iy1 - 1.96,
                    0.40, 0.50, "гор_текстиль"),
                  P("кресло_спин", sx + 0.21, sx + 0.93, iy1 - 2.70, iy1 - 2.56,
                    0.40, 0.92, "гор_текстиль"),
                  P("торшер", sx + sw_ + 0.10, sx + sw_ + 0.34, iy1 - 0.62,
                    iy1 - 0.38, 0.014, 1.58, "гор_акцент_латунь", kind="cyl"),
                  P("зелень", min(sx + sw_ + 0.10, ix1 - 0.44),
                    min(sx + sw_ + 0.10, ix1 - 0.44) + 0.40,
                    t + 0.18, t + 0.58, 0.0, 1.05, "гор_зелень", kind="cyl")]
        parts += tray(sx + sw_ / 2 + 0.14, iy1 - 1.46, 0.42)
        parts += books(sx + sw_ / 2 - 0.30, iy1 - 1.46, 0.42)
        aw0 = min(door_x0 + door_w + 0.20, ix1 - 0.95)
        if aw0 > t + BW + 0.10:
            parts += art(aw0, aw0 + 0.80, iy1)
        dw = min(1.40, BW - 1.05 - 0.14)
        parts += desk(t + BW - dw, t + 0.04, dw, 0.52, chair=not accessible,
                      tv=False, chair_side=1)
        parts += lights(bx0, ix1, t, iy1, 3)
        if accessible:
            c = free_circle(parts, W, D, 0.75)
            if c is not None:
                parts.append(P("круг_разворота", c[0] - 0.75, c[0] + 0.75,
                               c[1] - 0.75, c[1] + 0.75, 0.0, 0.004,
                               "гор_разметка", kind="cyl"))
        return parts

    bed_w = {"эконом": 1.36, "стандарт": 1.60, "бизнес": 1.70}[kind]
    bed_w = min(bed_w, free_w - (0.55 if accessible else 0.10))
    bed_d = min(1.95, iy1 - t - 0.26)
    ww = min(0.72 if kind != "эконом" else 0.60, BW - 0.06)
    strip = (iy1 - BD) - t                       # глубина полосы у окна
    if accessible:
        # койка — к дальней переборке, между нею и санузлом остаётся круг 1,5 м
        bx = ix1 - 0.12 - bed_w
        parts += bed2(bx, t + 0.20, bed_w, bed_d, "y0")
        if bx - 0.50 > bx0:
            parts += nightstand(bx - 0.50, t + 0.22)
        ns_right = False
        parts += wardrobe(t, iy1 - BD - 0.60, ww, 0.56)
        # столик с подъездом коляски: без стула, свободное подстолье
        dw = min(1.15, BW - ww - 0.14)
        if dw > 0.55 and strip >= 0.56:
            parts += desk(t + BW - dw, t + 0.02, dw, 0.46, chair=False, tv=False)
        parts += lights(bx0, ix1, t, iy1 - BD, 2 if W < 5 else 3)
        mx = t + BW + 0.16
        if mx + 0.60 < min(door_x0 - 0.10, bx - 0.20):
            parts += [P("консоль", mx, mx + 0.60, iy1 - 0.36, iy1 - 0.04, 0.72,
                        0.78, "гор_дерево"),
                      P("зеркало_каюты", mx + 0.04, mx + 0.56, iy1 - 0.03,
                        iy1 - 0.012, 0.90, 1.66, "гор_экран")]
            parts += vase(mx + 0.30, iy1 - 0.20, 0.78)
        c = free_circle(parts, W, D, 0.75)
        if c is None:
            c = free_circle(parts, W, D, 0.70)
        if c is not None:
            parts.append(P("круг_разворота", c[0] - 0.75, c[0] + 0.75,
                           c[1] - 0.75, c[1] + 0.75, 0.0, 0.004,
                           "гор_разметка", kind="cyl"))
        return parts
    bx = bx0 + 0.06
    parts += bed2(bx, t + 0.16, bed_w, bed_d, "y0")
    ns_x = bx + bed_w + 0.06
    ns_right = False
    if ns_x + 0.42 < ix1 - 0.02:
        parts += nightstand(ns_x, t + 0.18)
        ns_right = True
    if bx - 0.48 > bx0:
        parts += nightstand(bx - 0.48, t + 0.18)
    parts += wardrobe(t, iy1 - BD - 0.66, ww, 0.56)
    if strip >= 1.06:
        dw = min(1.15, BW - ww - 0.12)
        parts += desk(t + BW - dw, t + 0.02, dw, 0.46, chair=True, tv=False,
                      chair_side=1)
    else:
        dx = (ns_x + 0.42 + 0.14) if ns_right else (bx + bed_w + 0.12)
        dw = min(1.15, ix1 - dx - 0.04)
        if dw > 0.7:
            parts += desk(dx, t + 0.02, dw, 0.46, chair=True, tv=False,
                          chair_side=1)
    parts += lights(bx0, ix1, t, iy1 - BD, 2 if W < 5 else 3)
    bench_y0 = t + 0.16 + bed_d + 0.14
    if not accessible and bench_y0 + 0.40 < iy1 - 0.70:
        parts += [P("банкетка", bx + 0.10, bx + bed_w - 0.10, bench_y0,
                    bench_y0 + 0.40, 0.0, 0.42, "гор_текстиль"),
                  P("банкетка_плед", bx + 0.18, bx + bed_w - 0.18, bench_y0 + 0.06,
                    bench_y0 + 0.34, 0.42, 0.48, "гор_текстиль_тёплый")]
    aw0 = door_x0 + door_w + 0.18
    if aw0 + 0.66 < ix1 - 0.06:
        parts += art(aw0, aw0 + 0.66, iy1)
    mx = t + BW + 0.16
    if mx + 0.60 < door_x0 - 0.10:
        parts += [P("консоль", mx, mx + 0.60, iy1 - 0.36, iy1 - 0.04, 0.72, 0.78,
                    "гор_дерево"),
                  P("зеркало_каюты", mx + 0.04, mx + 0.56, iy1 - 0.03, iy1 - 0.012,
                    0.90, 1.66, "гор_экран")]
        parts += books(mx + 0.16, iy1 - 0.20, 0.78)
        parts += vase(mx + 0.45, iy1 - 0.20, 0.78)
    if kind == "бизнес" and not accessible:
        sx = bx + bed_w + 0.55
        if sx + 0.80 < ix1 - 0.04:
            parts += [P("кресло_осн", sx, sx + 0.78, t + 0.24, t + 1.02, 0.0, 0.40,
                        "гор_дерево"),
                      P("кресло_сид", sx + 0.03, sx + 0.75, t + 0.38, t + 1.00,
                        0.40, 0.50, "гор_текстиль"),
                      P("кресло_спин", sx + 0.03, sx + 0.75, t + 0.24, t + 0.38,
                        0.40, 0.92, "гор_текстиль"),
                      P("торшер", sx + 0.86, sx + 1.10, t + 0.30, t + 0.54,
                        0.0, 1.55, "гор_акцент_латунь", kind="cyl")]
    return parts


# ------------------------------------------------------------- эталоны -----
TYPES = [
    # имя, W, D, вид, окно, доступная, балкон
    ("эталон_эконом",            3.00, 3.00, "эконом",   True,  False, False),
    ("эталон_эконом_вн",         3.00, 3.00, "эконом",   False, False, False),
    ("эталон_стандарт",          4.30, 3.00, "стандарт", True,  False, False),
    ("эталон_стандарт_дост",     6.00, 3.00, "стандарт", True,  True,  False),
    ("эталон_бизнес",            6.00, 3.00, "бизнес",   True,  False, False),
    ("эталон_бизнес_дост",       6.00, 3.00, "бизнес",   True,  True,  False),
    ("эталон_люкс",              8.00, 5.00, "люкс",     True,  False, False),
    ("эталон_люкс_дост",         8.00, 5.00, "люкс",     True,  True,  False),
    ("эталон_экипаж_1",          2.00, 3.00, "экипаж",   True,  False, False),
    ("эталон_экипаж_1_вн",       2.00, 3.00, "экипаж",   False, False, False),
    ("эталон_экипаж_2",          2.90, 3.00, "экипаж",   True,  False, False),
    ("эталон_экипаж_2_вн",       2.90, 3.00, "экипаж",   False, False, False),
]


def rebuild_prototypes(verbose=True):
    """Собрать все эталоны, предварительно проверив их на пересечения."""
    report = {}
    col = bpy.data.collections.get("20_Эталоны_кают")
    if col:
        for o in list(col.objects):
            bpy.data.objects.remove(o, do_unlink=True)
    gx, gy = -60.0, -30.0
    for i, (name, W, D, kind, win, acc, bal) in enumerate(TYPES):
        parts = layout(W, D, kind, win, acc, bal)
        bad = check(parts)
        report[name] = dict(parts=len(parts), overlaps=bad, W=W, D=D)
        if bad:
            continue
        ox = gx + (i % 4) * 11.0
        oy = gy + (i // 4) * 7.0
        build(name, parts, origin=(ox, oy, 0.0))
    if verbose:
        for k, v in report.items():
            print(("%-24s частей %3d  пересечений %d" % (k, v["parts"], len(v["overlaps"])))
                  + ("" if not v["overlaps"] else "  " + str(v["overlaps"][:4])))
    return report


# ------------------------------------------------- расстановка на судне ----
def _wall_limit(walls, deck, side, x0, x1):
    """Наружная грань продольной выгородки на участке [x0, x1] или None."""
    if not walls:
        return None
    best = None
    for (d, s_, wx0, wx1, ymax) in walls:
        if d != deck or s_ != side:
            continue
        if wx1 <= x0 + 0.01 or wx0 >= x1 - 0.01:
            continue
        best = ymax if best is None else max(best, ymax)
    return best



def place_all(rows, walls=None, margin=0.30, verbose=True):
    """Пересобрать все каюты судна по их габаритам из rows.

    rows — список словарей: name, deck, side, kind, dost, x0, x1, D, y_out, z.
    walls — продольные выгородки служебного блока: (палуба, борт, x0, x1, |y|).
    Каюта у борта отодвигается внутрь под новый обвод, а её внутренняя
    переборка садится точно на стенку выгородки: коридор не сужается и
    каюта ни во что не влезает.
    """
    import sys as _s
    if ROOT_SRC not in _s.path:
        _s.path.insert(0, ROOT_SRC)
    from lib import gorizont_hydro as H
    LEV = {"первая": 1.40, "главная": 4.20, "верхняя": 7.00, "шлюпочная": 9.80}
    col = bpy.data.collections.get("10_Каюты")
    if col is None:
        col = bpy.data.collections.new("10_Каюты")
        bpy.context.scene.collection.children.link(col)
    for o in list(col.objects):
        bpy.data.objects.remove(o, do_unlink=True)
    cache = {}
    made, moved, bad = [], 0, []
    for r in rows:
        W = round(r["x1"] - r["x0"], 3)
        D = round(r["D"], 3)
        kind = r["kind"]
        base = kind if kind in ("эконом", "стандарт", "бизнес", "люкс") else "экипаж"
        lev = LEV.get(r["deck"], r["z"])
        n = 8
        if lev < 4.1:
            lim = min(H.half_breadth(r["x0"] + (r["x1"] - r["x0"]) * i / n, lev + 0.06)
                      for i in range(n + 1))
        else:
            lim = min(H.super_half_breadth(r["x0"] + (r["x1"] - r["x0"]) * i / n)
                      for i in range(n + 1))
        outboard = (lim - abs(r["y_out"])) < 0.45
        if outboard:
            y_out = lim - margin
            if abs(abs(r["y_out"]) - y_out) > 0.005:
                moved += 1
        else:
            y_out = abs(r["y_out"])
        yw = _wall_limit(walls, r["deck"], r["side"], r["x0"], r["x1"])
        if yw is not None:
            D = round(max(y_out - yw, 2.20), 3)
        window = outboard or base == "люкс"
        key = (W, D, base, window, bool(r["dost"]))
        if key not in cache:
            parts = layout(W, D, base, window, bool(r["dost"]))
            ov = check(parts)
            if ov:
                bad.append((r["name"], ov[:3]))
                continue
            tmp = build("_tmp_%d" % len(cache), parts, collection="10_Каюты")
            cache[key] = tmp.data
            bpy.data.objects.remove(tmp, do_unlink=True)
        me = cache[key]
        o = bpy.data.objects.new(r["name"], me)
        col.objects.link(o)
        if r["side"] == "п":
            o.location = (r["x1"], y_out, lev)
            o.rotation_euler = (0.0, 0.0, math.pi)
        else:
            o.location = (r["x0"], -y_out, lev)
            o.rotation_euler = (0.0, 0.0, 0.0)
        made.append(o.name)
    if verbose:
        print("кают %d, сеток %d, сдвинуто внутрь %d, с пересечениями %d"
              % (len(made), len(cache), moved, len(bad)))
    return dict(made=made, meshes=len(cache), moved=moved, bad=bad)
