# -*- coding: utf-8 -*-
"""Планировка кают: геометрия, эргономика и проверки — без Blender.

Каюта описывается списком именованных объёмов в местной системе координат:
    x — вдоль борта (длина каюты), y — от борта внутрь, z — от пола.

Две проверки, и обе обязательные:
    check()        — ни один предмет не влезает в другой глубже 5 мм;
    check_access() — от двери можно дойти до окна, до койки, до шкафа и до
                     санузла проходом нормативной ширины.

Планировка строится от прохода: сначала резервируется проход, и только то,
что осталось, отдаётся мебели. Если с раздельным санузлом прохода не
выходит — берётся совмещённый, он уже на 0,25…0,45 м. Если и так не
выходит — койка разворачивается вдоль окна или санузел выносится из каюты.

Этот модуль не знает про Blender: по нему строятся и модель
(scripts/blender_каюты.py), и чертежи планировок (scripts/чертёж_каюты.py).
"""
import math

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


def bathroom(x0, y0, w, d, roll_in=False, door_at="x0"):
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
    dx0 = ix0 + 0.05 if door_at == "x0" else ix1 - 0.05 - dw
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
          1.00, 1.86, "гор_зеркало"),
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


def wardrobe(x0, y0, w, d, h=2.02, face="y1"):
    """Шкаф. face — куда открываются створки: y1, y0 или x1."""
    x1, y1 = x0 + w, y0 + d
    p = [P("шкаф_корпус", x0, x1, y0, y1, 0.0, h, "гор_дерево")]
    if face == "x1":
        p += [
            P("шкаф_дверь_1", x1, x1 + 0.02, y0 + 0.01, (y0 + y1) / 2 - 0.005,
              0.03, h - 0.03, "гор_дерево_светлое"),
            P("шкаф_дверь_2", x1, x1 + 0.02, (y0 + y1) / 2 + 0.005, y1 - 0.01,
              0.03, h - 0.03, "гор_дерево_светлое"),
            P("шкаф_ручки", x1 + 0.02, x1 + 0.05, (y0 + y1) / 2 - 0.02,
              (y0 + y1) / 2 + 0.02, 1.00, 1.30, "гор_акцент_латунь"),
        ]
        return p
    if face == "y1":
        fy0, fy1, hy0, hy1 = y1, y1 + 0.02, y1 + 0.02, y1 + 0.05
    else:
        fy0, fy1, hy0, hy1 = y0 - 0.02, y0, y0 - 0.05, y0 - 0.02
    p += [
        P("шкаф_дверь_1", x0 + 0.01, x0 + w / 2 - 0.005, fy0, fy1,
          0.03, h - 0.03, "гор_дерево_светлое"),
        P("шкаф_дверь_2", x0 + w / 2 + 0.005, x1 - 0.01, fy0, fy1,
          0.03, h - 0.03, "гор_дерево_светлое"),
        P("шкаф_ручки", x0 + w / 2 - 0.02, x0 + w / 2 + 0.02, hy0, hy1,
          1.00, 1.30, "гор_акцент_латунь"),
    ]
    return p


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
        p.append(P("одеяло", x0 + 0.02, x1 - 0.02, y0 + 0.52, y1 - 0.02, 0.50,
                   0.58, "гор_бельё"))
        p.append(P("дорожка", x0 + 0.02, x1 - 0.02, y1 - 0.58, y1 - 0.04,
                   0.58, 0.60, "гор_текстиль_тёплый"))
        py0, py1 = y0 + 0.08, y0 + 0.46
        p.append(P("изголовье", x0 - 0.02, x1 + 0.02, y0 - 0.06, y0, 0.34, 1.15,
                   "гор_текстиль"))
    else:
        p.append(P("одеяло", x0 + 0.02, x1 - 0.02, y0 + 0.02, y1 - 0.52, 0.50,
                   0.58, "гор_бельё"))
        p.append(P("дорожка", x0 + 0.02, x1 - 0.02, y0 + 0.04, y0 + 0.58,
                   0.58, 0.60, "гор_текстиль_тёплый"))
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


# --------------------------------------------------------------- эргономика --
# Нормы прохода и подходов. Они и определяют планировку: сначала
# резервируется проход, и только в оставшееся ставится мебель, а не
# наоборот. Числа — из практики пассажирских судов и СП 59.13330 для
# доступных кают.
PASS = {"эконом": 0.55, "стандарт": 0.70, "бизнес": 0.75, "люкс": 0.85,
        "экипаж": 0.55}
PASS_ACC = 0.90            # проход в доступной каюте
BED_SIDE = 0.55            # подход к койке сбоку
BED_SIDE_ACC = 1.20        # подход к койке в доступной каюте
FRONT_WARDROBE = 0.55      # перед шкафом, чтобы открыть створку
FRONT_BATH = 0.65          # перед дверью санузла
DOOR_CLEAR = 0.70          # свободная зона за входной дверью
CELL = 0.05                # шаг сетки проверки проходов
H_BLOCK = 1.10             # ниже этой высоты предмет мешает идти


def _pass_width(kind, accessible):
    return PASS_ACC if accessible else PASS.get(kind, 0.60)


def wet_unit(x0, y0, w, d, door_w=0.62, rail=False, door_at="x0"):
    """Совмещённый санузел: унитаз, раковина и душ без поддона в одном
    объёме, слив в полу.

    Так делают в каютах, где на раздельный душ места нет: пол с уклоном к
    трапу, штора по направляющей отделяет мокрую зону на время душа, а в
    остальное время помещение работает как обычный туалет с умывальником.
    Выигрыш против раздельного санузла — 0,25…0,45 м ширины, а это как раз
    та ширина, которой не хватает на проход вдоль койки.
    """
    t = 0.04
    x1, y1 = x0 + w, y0 + d
    ix0, ix1 = x0, x1 - t
    iy0, iy1 = y0 + t, y1
    IW = ix1 - ix0
    dw = min(door_w, IW - 0.30)
    dx0 = ix0 + 0.04 if door_at == "x0" else ix1 - 0.04 - dw
    p = [
        P("су_стена_x", x1 - t, x1, y0, y1, 0.0, H_ROOM, "гор_плитка"),
        P("су_стена_y_л", x0, dx0, y0, y0 + t, 0.0, H_ROOM, "гор_плитка"),
        P("су_стена_y_п", dx0 + dw, x1 - t, y0, y0 + t, 0.0, H_ROOM, "гор_плитка"),
        P("су_стена_y_над", dx0, dx0 + dw, y0, y0 + t, 2.03, H_ROOM, "гор_плитка"),
        P("су_дверь", dx0 + 0.01, dx0 + dw - 0.01, y0 + t * 0.3, y0 + t * 0.7,
          0.0, 2.02, "гор_стекло_каюты"),
        P("су_пол", ix0, ix1, iy0, iy1, 0.0, 0.020, "гор_плитка"),
        P("су_трап", ix0 + IW / 2 - 0.06, ix0 + IW / 2 + 0.06,
          iy0 + (iy1 - iy0) / 2 - 0.06, iy0 + (iy1 - iy0) / 2 + 0.06,
          0.020, 0.024, "гор_металл"),
    ]
    # раковина подвесная у входа — пол под ней свободен
    bw_ = min(0.46, IW - 0.50)
    p += [
        P("су_раковина", ix0 + 0.03, ix0 + 0.03 + bw_, iy0 + 0.03, iy0 + 0.37,
          0.76, 0.86, "гор_бельё"),
        P("су_смеситель", ix0 + 0.03 + bw_ / 2 - 0.025, ix0 + 0.03 + bw_ / 2 + 0.025,
          iy0 + 0.05, iy0 + 0.10, 0.86, 1.00, "гор_металл", kind="cyl"),
        P("су_зеркало", ix0 + 0.03, ix0 + 0.03 + bw_, iy0 + 0.004, iy0 + 0.018,
          1.02, 1.74, "гор_зеркало"),
        P("су_полка", ix0 + 0.03, ix0 + 0.03 + bw_, iy0 + 0.02, iy0 + 0.16,
          1.76, 1.80, "гор_дерево_светлое"),
    ]
    # унитаз у дальней стенки
    wc_x1 = ix1 - 0.03
    wc_x0 = wc_x1 - 0.37
    wc_y1 = iy1 - 0.05
    wc_y0 = wc_y1 - 0.54
    p += [
        P("унитаз_бак", wc_x0, wc_x1, wc_y1 - 0.17, wc_y1, 0.24, 0.88, "гор_бельё"),
        P("унитаз_чаша", wc_x0 + 0.02, wc_x1 - 0.02, wc_y0, wc_y1 - 0.19,
          0.02, 0.41, "гор_бельё"),
        P("унитаз_крышка", wc_x0 + 0.02, wc_x1 - 0.02, wc_y0, wc_y1 - 0.19,
          0.41, 0.45, "гор_бельё"),
    ]
    # душ: лейка и смеситель на стенке, штора по направляющей
    p += [
        P("душ_лейка", ix0 + 0.05, ix0 + 0.17, iy1 - 0.22, iy1 - 0.10,
          1.94, 2.00, "гор_металл"),
        P("душ_смеситель", ix0 + 0.04, ix0 + 0.11, iy1 - 0.26, iy1 - 0.16,
          1.02, 1.20, "гор_металл", kind="cyl", axis="Y"),
        P("душ_направляющая", ix0 + 0.04, ix1 - 0.04, iy1 - 0.44, iy1 - 0.40,
          1.98, 2.02, "гор_металл", kind="cyl"),
        P("душ_штора", ix0 + 0.06, ix0 + 0.30, iy1 - 0.44, iy1 - 0.40,
          1.20, 1.98, "гор_бельё"),
        P("су_крючки", ix0 + 0.05, ix0 + 0.19, iy0 + 0.40, iy0 + 0.45,
          1.52, 1.60, "гор_металл"),
        P("су_полотенце", ix0 + 0.05, ix0 + 0.27, iy0 + 0.46, iy0 + 0.51,
          0.94, 1.20, "гор_бельё"),
    ]
    if rail:
        p += [
            P("поручень_унитаз", wc_x0 - 0.07, wc_x0 - 0.03, wc_y0 - 0.02,
              wc_y1 - 0.14, 0.83, 0.87, "гор_металл", kind="cyl", axis="Y"),
            P("кнопка_вызова", ix0 + 0.04, ix0 + 0.10, iy1 - 0.52, iy1 - 0.46,
              0.88, 0.96, "гор_акцент"),
        ]
    return p


def shelf_rail(x0, x1, y0, y1, z=1.32):
    """Ниша с штангой и полкой — замена шкафу там, где шкаф съест проход."""
    return [
        P("шкаф_полка", x0 + 0.03, x1 - 0.03, y0, y1, z + 0.62, z + 0.66,
          "гор_дерево"),
        P("шкаф_боковина_л", x0, x0 + 0.03, y0, y1, z, z + 0.66, "гор_дерево"),
        P("шкаф_боковина_п", x1 - 0.03, x1, y0, y1, z, z + 0.66, "гор_дерево"),
        P("шкаф_штанга", x0 + 0.03, x1 - 0.03, (y0 + y1) / 2 - 0.015,
          (y0 + y1) / 2 + 0.015, z + 0.54, z + 0.58, "гор_акцент_латунь",
          kind="cyl"),
    ]


# ------------------------------------------------- проверка проходимости ----
def _blockers(parts):
    """Предметы, которые мешают идти: стоят на полу и выше щиколотки."""
    out = []
    for q in parts:
        x0, x1, y0, y1, z0, z1 = q.box
        if q.name.startswith(("пол", "подволок", "су_пол", "ковёр", "коврик",
                              "круг", "светильник", "карниз", "душ_направляющая",
                              "душ_штора", "су_трап", "разметка")):
            continue
        if z0 >= H_BLOCK or z1 <= 0.12:
            continue
        out.append((x0, x1, y0, y1))
    return out


def _grid(parts, W, D):
    """Сетка занятости пола: True — пройти нельзя."""
    nx, ny = int(round(W / CELL)), int(round(D / CELL))
    occ = [[False] * ny for _ in range(nx)]
    for (x0, x1, y0, y1) in _blockers(parts):
        i0 = max(0, int(math.floor(x0 / CELL)))
        i1 = min(nx, int(math.ceil(x1 / CELL)))
        j0 = max(0, int(math.floor(y0 / CELL)))
        j1 = min(ny, int(math.ceil(y1 / CELL)))
        for i in range(i0, i1):
            for j in range(j0, j1):
                occ[i][j] = True
    return occ, nx, ny


def _clearance(occ, nx, ny):
    """Расстояние от каждой свободной клетки до ближайшей занятой или до
    границы каюты — волновым обходом по восьми соседям."""
    INF = 10 ** 6
    dist = [[INF] * ny for _ in range(nx)]
    q = []
    for i in range(nx):
        for j in range(ny):
            if occ[i][j]:
                dist[i][j] = 0
                q.append((i, j))
    head = 0
    nb = ((1, 0, 1.0), (-1, 0, 1.0), (0, 1, 1.0), (0, -1, 1.0),
          (1, 1, 1.4142), (1, -1, 1.4142), (-1, 1, 1.4142), (-1, -1, 1.4142))
    while head < len(q):
        i, j = q[head]
        head += 1
        d0 = dist[i][j]
        for di, dj, w in nb:
            a, b = i + di, j + dj
            if 0 <= a < nx and 0 <= b < ny and dist[a][b] > d0 + w:
                dist[a][b] = d0 + w
                q.append((a, b))
    return dist


def _flood(occ, dist, nx, ny, starts, rc):
    """Клетки, достижимые из starts по клеткам с запасом не меньше rc."""
    seen = [[False] * ny for _ in range(nx)]
    q = [c for c in starts if 0 <= c[0] < nx and 0 <= c[1] < ny
         and not occ[c[0]][c[1]] and dist[c[0]][c[1]] >= rc]
    for i, j in q:
        seen[i][j] = True
    head = 0
    while head < len(q):
        i, j = q[head]
        head += 1
        for di, dj in ((1, 0), (-1, 0), (0, 1), (0, -1)):
            a, b = i + di, j + dj
            if 0 <= a < nx and 0 <= b < ny and not seen[a][b] \
                    and not occ[a][b] and dist[a][b] >= rc:
                seen[a][b] = True
                q.append((a, b))
    return seen


def _cells(x0, x1, y0, y1, nx, ny):
    i0 = max(0, int(math.floor(x0 / CELL)))
    i1 = min(nx, int(math.ceil(x1 / CELL)))
    j0 = max(0, int(math.floor(y0 / CELL)))
    j1 = min(ny, int(math.ceil(y1 / CELL)))
    return [(i, j) for i in range(i0, i1) for j in range(j0, j1)]


def _named(parts, name):
    for q in parts:
        if q.name == name:
            return q.box
    return None


def check_access(parts, W, D, kind="стандарт", accessible=False, door=None):
    """Проверка эргономики каюты: есть ли проход и подходы к оборудованию.

    Пол разбивается на сетку 50 мм, для каждой клетки считается расстояние
    до ближайшего предмета или переборки, и от входной двери пускается
    волна по клеткам, где до обеих сторон прохода не меньше половины
    нормы. Человек может стоять вплотную к переборке, поэтому целевые зоны
    берутся не у самой поверхности, а на полшага от неё — там, где он
    реально стоит.
    """
    pw = _pass_width(kind, accessible)
    r = pw / 2.0
    rc = r / CELL
    occ, nx, ny = _grid(parts, W, D)
    dist = _clearance(occ, nx, ny)
    bad = []
    dx0, dw = door if door else (W * 0.4, 0.8)

    def free(cells):
        return [(i, j) for i, j in cells
                if 0 <= i < nx and 0 <= j < ny and not occ[i][j]]

    def best(cells):
        f = free(cells)
        if not f:
            return None
        return max(f, key=lambda c: dist[c[0]][c[1]])

    # точка стояния сразу за дверью
    band = _cells(dx0 + 0.03, dx0 + dw - 0.03, D - T_WALL - r - 0.12,
                  D - T_WALL - r + 0.12, nx, ny)
    seed = best(band)
    if seed is None:
        return [("вход", "дверной проём заставлен")]
    if dist[seed[0]][seed[1]] < rc:
        bad.append(("вход", "проход у двери уже %.2f м" % pw))
        rc = dist[seed[0]][seed[1]]
    seen = _flood(occ, dist, nx, ny, [seed], rc)

    def ok(cells):
        return any(seen[i][j] for i, j in cells
                   if 0 <= i < nx and 0 <= j < ny)

    if not ok(_cells(dx0, dx0 + dw, D - T_WALL - DOOR_CLEAR,
                     D - T_WALL - r, nx, ny)):
        bad.append(("вход", "нет свободной зоны %.2f м за дверью" % DOOR_CLEAR))
    bed = _named(parts, "матрас") or _named(parts, "матрас_0")
    at_window = bed and bed[2] < 0.25
    if not at_window and not ok(_cells(0.12, W - 0.12, T_WALL + r + 0.01,
                                       T_WALL + r + 0.45, nx, ny)):
        bad.append(("борт", "к окну не пройти"))
    if bed:
        bx0, bx1, by0, by1 = bed[0], bed[1], bed[2], bed[3]
        need = BED_SIDE_ACC if accessible else BED_SIDE
        sides = [_cells(bx0 - need, bx0 - r, by0, by1, nx, ny),
                 _cells(bx1 + r, bx1 + need, by0, by1, nx, ny),
                 _cells(bx0, bx1, by1 + r, by1 + need, nx, ny)]
        if not any(ok(c) for c in sides):
            bad.append(("койка", "нет подхода шириной %.2f м" % need))
    wr = _named(parts, "шкаф_корпус")
    dv = _named(parts, "шкаф_дверь_1")
    if wr and dv:
        wx0, wx1, wy0, wy1 = wr[0], wr[1], wr[2], wr[3]
        if dv[0] >= wx1 - 1e-6:
            front = _cells(wx1 + r, wx1 + FRONT_WARDROBE + r, wy0, wy1, nx, ny)
        elif dv[2] >= wy1 - 1e-6:
            front = _cells(wx0, wx1, wy1 + r, wy1 + FRONT_WARDROBE + r, nx, ny)
        else:
            front = _cells(wx0, wx1, wy0 - FRONT_WARDROBE - r, wy0 - r, nx, ny)
        if not ok(front):
            bad.append(("шкаф", "не открыть створку"))
    bd = _named(parts, "су_дверь")
    if bd:
        sx0, sx1, sy0 = bd[0], bd[1], bd[2]
        if not ok(_cells(sx0, sx1, sy0 - FRONT_BATH - r, sy0 - r, nx, ny)):
            bad.append(("санузел", "не подойти к двери"))
    ch = _named(parts, "кресло_сиденье")
    if _named(parts, "стол") and ch:
        cx0, cx1, cy0, cy1 = ch[0], ch[1], ch[2], ch[3]
        near = _cells(cx0 - 0.45, cx1 + 0.45, cy1 + 0.02, cy1 + 0.50, nx, ny)             + _cells(cx1 + 0.02, cx1 + 0.50, cy0, cy1, nx, ny)             + _cells(cx0 - 0.50, cx0 - 0.02, cy0, cy1, nx, ny)
        if not ok(near):
            bad.append(("стол", "к стулу не подойти"))
    return bad


def berth_x(x0, y0, w, d):
    """Койка вдоль окна: изголовье у ближней переборки, длинная сторона по x."""
    x1, y1 = x0 + w, y0 + d
    return [
        P("койка_основание", x0, x1, y0, y1, 0.06, 0.34, "гор_дерево"),
        P("койка_цоколь", x0 + 0.04, x1 - 0.04, y0 + 0.04, y1 - 0.04,
          0.0, 0.06, "гор_металл"),
        P("матрас", x0 + 0.01, x1 - 0.01, y0 + 0.01, y1 - 0.01, 0.34, 0.50,
          "гор_бельё"),
        P("одеяло", x0 + 0.52, x1 - 0.02, y0 + 0.02, y1 - 0.02, 0.50, 0.58,
          "гор_бельё"),
        P("дорожка", x1 - 0.52, x1 - 0.04, y0 + 0.02, y1 - 0.02, 0.58, 0.60,
          "гор_текстиль_тёплый"),
        P("подушка", x0 + 0.06, x0 + 0.46, y0 + 0.06, y1 - 0.06, 0.50, 0.62,
          "гор_бельё"),
        P("изголовье", x0 - 0.05, x0, y0 - 0.02, y1 + 0.02, 0.34, 1.05,
          "гор_текстиль"),
        P("спинка", x0, x1, y1, y1 + 0.05, 0.34, 0.86, "гор_текстиль"),
    ]


def bunk(x0, y0, w, d, ladder="x0"):
    """Двухъярусная койка: два спальных места в габарите одного.

    Трап ставится со стороны прохода: у дальней переборки ему места нет.
    """
    p = []
    x1, y1 = x0 + w, y0 + d
    p.append(P("койка_каркас_л", x0, x0 + 0.05, y0, y1, 0.0, 2.02, "гор_металл"))
    p.append(P("койка_каркас_п", x1 - 0.05, x1, y0, y1, 0.0, 2.02, "гор_металл"))
    for k, z in ((0, 0.34), (1, 1.36)):
        p.append(P("койка_основание_%d" % k, x0 + 0.05, x1 - 0.05, y0, y1,
                   z - 0.06, z, "гор_дерево"))
        p.append(P("матрас_%d" % k, x0 + 0.06, x1 - 0.06, y0 + 0.01, y1 - 0.01,
                   z, z + 0.16, "гор_бельё"))
        p.append(P("одеяло_%d" % k, x0 + 0.07, x1 - 0.07, y0 + 0.52, y1 - 0.02,
                   z + 0.16, z + 0.23, "гор_бельё"))
        p.append(P("дорожка_%d" % k, x0 + 0.07, x1 - 0.07, y1 - 0.46,
                   y1 - 0.04, z + 0.23, z + 0.25, "гор_текстиль_тёплый"))
        p.append(P("подушка_%d" % k, x0 + 0.12, x1 - 0.12, y0 + 0.08, y0 + 0.46,
                   z + 0.16, z + 0.27, "гор_бельё"))
        p.append(P("бортик_%d" % k, x0 + 0.05, x1 - 0.05, y1, y1 + 0.04,
                   z, z + 0.26, "гор_дерево"))
        p.append(P("светильник_койки_%d" % k, x0 + 0.07, x0 + 0.19,
                   y0 + 0.16, y0 + 0.28, z + 0.60, z + 0.70, "гор_щит"))
    # трап в ногах койки: сбоку он съел бы проход, ради которого всё и затевалось
    lx0 = x0 + 0.03 if ladder == "x0" else x1 - 0.27
    for k in range(4):
        p.append(P("трап_ступень_%d" % k, lx0 + 0.035, lx0 + 0.205,
                   y1 + 0.06 + k * 0.008, y1 + 0.17 + k * 0.008,
                   0.34 + k * 0.30, 0.38 + k * 0.30, "гор_металл"))
    p.append(P("трап_тетива_л", lx0, lx0 + 0.03, y1 + 0.05, y1 + 0.19,
               0.30, 1.72, "гор_металл"))
    p.append(P("трап_тетива_п", lx0 + 0.21, lx0 + 0.24, y1 + 0.05, y1 + 0.19,
               0.30, 1.72, "гор_металл"))
    return p


def _bed_block(x0, y0, w, d, kind, twin, ladder="x0"):
    """Койка выбранного типа: двухъярусная, двуспальная или одинарная."""
    if twin:
        return bunk(x0, y0, w, d, ladder), 2
    return bed2(x0, y0, w, d, "y0"), (2 if w >= 1.20 else 1)


# габариты санузлов: раздельный и совмещённый
BATH_SEP = {"эконом": (1.30, 1.45), "стандарт": (1.55, 1.55),
            "бизнес": (1.75, 1.60), "люкс": (2.30, 2.05),
            "экипаж": (1.25, 1.30)}
BATH_WET = {"эконом": (1.05, 1.25), "стандарт": (1.10, 1.30),
            "бизнес": (1.20, 1.35), "люкс": (1.30, 1.45),
            "экипаж": (1.00, 1.20)}
BED_WIDTHS = {"эконом": (1.36, 1.20, 0.90), "стандарт": (1.60, 1.40, 1.20),
              "бизнес": (1.70, 1.60, 1.40), "люкс": (1.80, 1.60),
              "экипаж": (0.90, 0.80)}


def _plan(W, D, kind, accessible):
    """Подбор санузла и койки под ширину каюты.

    Сначала резервируется проход нормативной ширины, и только то, что
    осталось, отдаётся под койку. Если с раздельным санузлом прохода не
    выходит — берётся совмещённый: он уже на 0,25…0,45 м, и этого как раз
    хватает. Если и так не выходит — койка разворачивается вдоль окна.
    """
    t = T_WALL
    ix1, iy1 = W - t, D - t
    pw = _pass_width(kind, accessible)
    for wet in (False, True):
        bw_, bd_ = (BATH_WET if wet else BATH_SEP)[kind]
        if accessible:
            if wet:
                continue
            bw_, bd_ = max(bw_, 2.05), max(bd_, 1.95)
        if iy1 - t - bd_ < 0.30:
            continue
        mx0 = t + bw_ + 0.12
        for bedw in BED_WIDTHS[kind]:
            twin = (bedw < 1.10 and (kind == "эконом" or W >= 2.45))
            # для двухъярусной койки в ногах нужен трап
            bl = min(2.00, iy1 - (t + 0.20) - (0.26 if twin else 0.10))
            if bl < 1.88:
                continue
            pass_w = (ix1 - 0.04 - bedw) - mx0
            if pass_w >= pw - 1e-9:
                return dict(plan="A", wet=wet, BW=bw_, BD=bd_, mx0=mx0,
                            bed_w=bedw, bed_l=bl, pass_w=pass_w, twin=twin)
    # план В: одноместная каюта экипажа без своего санузла — душ и туалет
    # общие на блок кают. Иначе в 2,0 м ширины койка, санузел и проход
    # не укладываются: на проход остаётся 0,0 м.
    if kind == "экипаж" and W < 2.45:
        bedw = min(0.90, ix1 - t - _pass_width(kind, accessible) - 0.06)
        bl = min(2.00, iy1 - (t + 0.20) - 0.10)
        if bedw >= 0.74 and bl >= 1.88:
            return dict(plan="C", wet=False, BW=0.0, BD=0.0, mx0=t,
                        bed_w=bedw, bed_l=bl,
                        pass_w=ix1 - t - bedw - 0.04, twin=False)
    # план Б: койка вдоль окна
    bl = min(2.00, ix1 - t - 0.12)
    if bl < 1.82:
        return None
    bw_, bd_ = BATH_WET[kind]
    bd_ = min(bd_, iy1 - (t + 0.86) - 0.70)
    if bd_ < 1.05:
        return None
    return dict(plan="B", wet=True, BW=bw_, BD=bd_, bed_w=bl, bed_l=0.82,
                pass_w=ix1 - bw_ - t, twin=False)


def layout(W, D, kind="стандарт", window=True, accessible=False, balcony=False):
    """Планировка каюты: сначала проход, потом мебель.

    План А — санузел в углу у коридорной переборки, койка у дальней
    переборки, между ними сквозной проход от двери к окну.
    План Б — для узких кают: койка вдоль окна, санузел в дальнем углу,
    проход вдоль ближнего борта.
    """
    t = T_WALL
    ix1, iy1 = W - t, D - t
    pl = _plan(W, D, kind, accessible)
    if pl is None:
        raise ValueError("каюта %.2f x %.2f (%s) не планируется" % (W, D, kind))
    BW, BD, wet = pl["BW"], pl["BD"], pl["wet"]
    door_w = 0.90 if accessible else (0.75 if kind == "экипаж" else 0.80)

    if pl["plan"] in ("A", "C"):
        has_bath = pl["plan"] == "A"
        door_x0 = min(t + BW + 0.16, ix1 - door_w - 0.10) if has_bath             else t + 0.10
        parts = shell(W, D, door_x0, door_w, window and not balcony, balcony)
        if has_bath:
            # дверь санузла — у края, обращённого к проходу
            if wet:
                parts += wet_unit(t, iy1 - BD, BW, BD, rail=accessible,
                                  door_at="x1")
            else:
                parts += bathroom(t, iy1 - BD, BW, BD, roll_in=accessible,
                                  door_at="x1")
        bx1 = ix1 - 0.04
        bx0 = bx1 - pl["bed_w"]
        by0 = t + 0.20
        bed_parts, berths = _bed_block(bx0, by0, pl["bed_w"], pl["bed_l"],
                                       kind, pl["twin"], ladder="x0")
        parts += bed_parts
        ns_x = bx0 - 0.46
        if not pl["twin"] and ns_x - 0.06 > pl["mx0"] + _pass_width(kind, accessible):
            parts += nightstand(ns_x, by0 + 0.06)
        if has_bath:
            tv_x = t + BW
            parts.append(P("телевизор", tv_x, tv_x + 0.045, t + 0.55, t + 1.45,
                           1.16, 1.70, "гор_экран"))
        else:
            parts.append(P("телевизор", t, t + 0.045, t + 0.55, t + 1.35,
                           1.16, 1.70, "гор_экран"))
        sy1 = iy1 - BD if has_bath else iy1
        strip_x1 = t + BW if has_bath else bx0 - _pass_width(kind, accessible) - 0.06
        strip = sy1 - t
        ww = min(0.60, strip_x1 - t - 0.04)
        # шкаф в полосе у окна, створки в сторону прохода
        if ww >= 0.42 and strip >= 1.30:
            parts += wardrobe(t, sy1 - 0.66, ww, 0.58, face="x1")
            free_y1 = sy1 - 0.66 - 0.06
        elif ww >= 0.42:
            parts += shelf_rail(t + 0.02, t + 0.02 + ww, sy1 - 0.62, sy1 - 0.04)
            free_y1 = sy1 - 0.66
        else:
            free_y1 = sy1 - 0.06
        # стол: со стулом, если полоса глубокая, иначе узкая консоль
        dw_ = min(1.10, strip_x1 - t - 0.08)
        if dw_ > 0.50:
            if free_y1 - (t + 0.16) >= 0.46 + 0.56:
                parts += desk(t + 0.04, t + 0.16, dw_, 0.46, chair=True,
                              tv=False, chair_side=1)
            else:
                parts.append(P("стол", t + 0.04, t + 0.04 + dw_, t + 0.02,
                               t + 0.26, 0.72, 0.76, "гор_дерево"))
                parts.append(P("полка_стола", t + 0.04, t + 0.04 + dw_,
                               t + 0.10, t + 0.26, 1.28, 1.32,
                               "гор_дерево_светлое"))
        if not has_bath:
            # умывальник в каюте: душ и туалет — общие на блок
            parts.append(P("су_раковина", t + 0.04, t + 0.48, sy1 - 0.42,
                           sy1 - 0.06, 0.76, 0.86, "гор_бельё"))
            parts.append(P("су_зеркало", t + 0.04, t + 0.48, sy1 - 0.045,
                           sy1 - 0.03, 1.02, 1.72, "гор_зеркало"))
        parts += lights(pl["mx0"], ix1, t, iy1, 2 if W < 5.0 else 3)
    else:
        door_x0 = t + 0.04
        parts = shell(W, D, door_x0, door_w, window and not balcony, balcony)
        parts += wet_unit(ix1 - BW, iy1 - BD, BW, BD, rail=accessible,
                          door_at="x0")
        bx0 = t + 0.08
        by0 = t + 0.10
        parts += berth_x(bx0, by0, pl["bed_w"], pl["bed_l"])
        parts += shelf_rail(bx0 + 0.10, bx0 + 0.72, by0 + 0.10, by0 + 0.66,
                            z=1.34)
        parts.append(P("телевизор", ix1 - 0.045, ix1, by0 + 0.22, by0 + 0.96,
                       1.20, 1.66, "гор_экран"))
        sx0 = ix1 - BW + 0.10
        parts.append(P("стол", sx0, ix1 - 0.04, by0 + pl["bed_l"] + 0.10,
                       by0 + pl["bed_l"] + 0.42, 0.72, 0.76, "гор_дерево"))
        parts += lights(t, ix1, t, iy1 - BD, 1)

    # --- гостиная зона люкса и кресло для отдыха в бизнес-каюте
    if kind == "люкс":
        zx0 = pl["mx0"] + 0.30
        zx1 = bx0 - 0.50
        if zx1 - zx0 > 2.6 and iy1 - t > 3.6:
            sx = min(zx0 + 1.10, zx1 - 2.10)
            sw_ = min(2.10, zx1 - sx)
            parts += [
                P("ковёр", sx - 0.20, sx + sw_ + 0.30, iy1 - 2.85, iy1 - 0.04,
                  0.0, 0.012, "гор_ковёр"),
                P("диван_основание", sx, sx + sw_, iy1 - 0.90, iy1 - 0.06,
                  0.014, 0.40, "гор_дерево"),
                P("диван_сиденье", sx + 0.03, sx + sw_ - 0.03, iy1 - 0.88,
                  iy1 - 0.24, 0.40, 0.50, "гор_текстиль"),
                P("диван_спинка", sx + 0.03, sx + sw_ - 0.03, iy1 - 0.22,
                  iy1 - 0.06, 0.40, 0.88, "гор_текстиль"),
                P("диван_подушка_л", sx + 0.12, sx + 0.54, iy1 - 0.42,
                  iy1 - 0.26, 0.50, 0.80, "гор_текстиль_тёплый"),
                P("диван_подушка_п", sx + sw_ - 0.54, sx + sw_ - 0.12,
                  iy1 - 0.42, iy1 - 0.26, 0.50, 0.80, "гор_текстиль_тёплый"),
                P("столик", sx + 0.55, sx + 1.55, iy1 - 1.78, iy1 - 1.14,
                  0.016, 0.42, "гор_дерево_светлое"),
                P("кресло_осн", sx + 0.30, sx + 1.08, iy1 - 2.62, iy1 - 1.84,
                  0.014, 0.40, "гор_дерево"),
                P("кресло_сид", sx + 0.33, sx + 1.05, iy1 - 2.46, iy1 - 1.88,
                  0.40, 0.50, "гор_текстиль"),
                P("кресло_спин", sx + 0.33, sx + 1.05, iy1 - 2.60, iy1 - 2.48,
                  0.40, 0.92, "гор_текстиль"),
                P("торшер_основание", sx + sw_ + 0.06, sx + sw_ + 0.32,
                  iy1 - 0.63, iy1 - 0.37, 0.014, 0.05, "гор_акцент_латунь",
                  kind="cyl"),
                P("торшер_стойка", sx + sw_ + 0.17, sx + sw_ + 0.21,
                  iy1 - 0.52, iy1 - 0.48, 0.05, 1.42, "гор_акцент_латунь",
                  kind="cyl"),
                P("торшер_абажур", sx + sw_ + 0.02, sx + sw_ + 0.36,
                  iy1 - 0.67, iy1 - 0.33, 1.42, 1.70, "гор_щит", kind="cyl"),
                P("зелень", zx1 - 0.42, zx1 - 0.02, t + 0.30, t + 0.70,
                  0.0, 1.05, "гор_зелень", kind="cyl"),
            ]
            parts += tray(sx + 1.22, iy1 - 1.46, 0.42)
            parts += books(sx + 0.80, iy1 - 1.46, 0.42)
        # банкетка в ногах койки
        bfy = by0 + pl["bed_l"] + 0.14
        if bfy + 0.42 < iy1 - 0.10:
            parts += [
                P("банкетка", bx0 + 0.12, bx1 - 0.12, bfy, bfy + 0.40,
                  0.0, 0.44, "гор_текстиль"),
                P("банкетка_плед", bx0 + 0.20, bx1 - 0.20, bfy + 0.06,
                  bfy + 0.34, 0.44, 0.50, "гор_текстиль_тёплый"),
            ]
    if kind in ("бизнес", "стандарт", "люкс") and not pl["twin"]:
        # банкетка в ногах койки: кресло в этих каютах поставить некуда —
        # между бортом и переборкой санузла остаётся 1,30 м, и кресло
        # глубиной 0,78 м перекрыло бы проход к окну и к санузлу
        bfy = by0 + pl["bed_l"] + 0.14
        if kind != "люкс" and bfy + 0.40 < iy1 - 0.06:
            parts += [
                P("банкетка", bx0 + 0.12, bx1 - 0.12, bfy, bfy + 0.38,
                  0.0, 0.44, "гор_текстиль"),
                P("банкетка_плед", bx0 + 0.20, bx1 - 0.20, bfy + 0.06,
                  bfy + 0.32, 0.44, 0.50, "гор_текстиль_тёплый"),
            ]

    if accessible:
        c = free_circle(parts, W, D, 0.75) or free_circle(parts, W, D, 0.70)
        if c is not None:
            parts.append(P("круг_разворота", c[0] - 0.75, c[0] + 0.75,
                           c[1] - 0.75, c[1] + 0.75, 0.0, 0.004,
                           "гор_разметка", kind="cyl"))
    # мелочи для кадра: картина на коридорной переборке
    aw0 = door_x0 + door_w + 0.16
    if aw0 + 0.62 < ix1 - 0.06:
        parts += art(aw0, aw0 + 0.62, iy1)

    return parts


def layout_info(W, D, kind="стандарт", accessible=False):
    """Как спланирована каюта: план, санузел, койка и ширина прохода."""
    pl = _plan(W, D, kind, accessible)
    if pl is None:
        return None
    if pl["plan"] == "C":
        bath = "общий на блок"
    elif pl["wet"]:
        bath = "совмещённый"
    else:
        bath = "раздельный"
    return dict(plan={"A": "А", "B": "Б", "C": "В"}[pl["plan"]], санузел=bath,
                койка=("двухъярусная" if pl["twin"] else "%.2f м" % pl["bed_w"]),
                мест=(2 if pl["twin"] or pl["bed_w"] >= 1.20 else 1),
                проход=round(pl["pass_w"], 2),
                W=W, D=D, площадь=round(W * D, 1))


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


