# -*- coding: utf-8 -*-
r"""Аудит сцены: пересечения объектов и выход за обвод корпуса.

Два независимых теста.

1.  Пересечения.  Широкая фаза — габаритные параллелепипеды в мировых
    координатах.  Узкая — BVHTree.overlap() по треугольникам.  Касание
    поверхностей (палуба под каютой, набор к обшивке) пересечением не
    считается: пара попадает в отчёт, только если реальная глубина
    взаимного проникновения больше DEPTH (25 мм).  Глубина меряется так:
    точки одной сетки, оказавшиеся внутри другой (чётность пересечений
    луча в двух направлениях), отодвигаются до ближайшей грани — берётся
    максимум.

2.  Выход за обвод.  Каждая вершина сравнивается с полуширотой корпуса
    (ниже 4,1 м) или надстройки (выше) на своей абсциссе и высоте.

Запуск внутри Blender:
    exec(open(r"E:\Ship_docx\scripts\blender_аудит.py", encoding="utf-8").read())
    audit()
"""
import bpy, sys, math, os
from mathutils import Vector
from mathutils.bvhtree import BVHTree

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont_hydro as H
from lib import gorizont as G

DEPTH = 0.025          # допустимая глубина взаимного проникновения, м
OUT_TOL = 0.02         # допустимый выход за обвод, м
Z_SUPER = 4.10         # выше этой отметки обвод задаёт надстройка
APPEND_HALF = 4.00     # предел для выступающих частей ниже киля

# Сварной корпус: обшивка, набор, палубы и переборки цистерн по определению
# примыкают друг к другу — взаимное касание пересечением не считается.
TOUCHING = ("40_Набор_корпуса", "01_Корпус", "03_Палубы", "02_Надстройка", "41_Переборки", "33_Общественные")
# Коллекции, которые вообще не участвуют в проверке обвода.
NO_HULL = ("60_Окружение", "20_Эталоны_кают")
SKIP = ("20_Эталоны_кают", "60_Окружение")
# Оболочки: находиться внутри них — норма, поэтому «точка внутри» для них
# пересечением не считается. Выход наружу ловит проверка обвода.
ENCLOSURE = ("корпус", "надстройка", "рубка", "настил_", "палуба_",
             "платформа_", "второе_дно", "обшивка", "портал_")
# Надстройку проверяем по её борту только для внутреннего насыщения.
INSIDE_SUPER = ("10_Каюты", "30_Общественные", "31_Мебель", "32_Служебные")


def _mesh_objs(collections=None):
    out = []
    for c in bpy.data.collections:
        if c.name in SKIP:
            continue
        if collections and c.name not in collections:
            continue
        for o in c.objects:
            if o.type == "MESH" and len(o.data.polygons) and o.visible_get():
                out.append((c.name, o))
    return out


def _world_tris(o, dg):
    ev = o.evaluated_get(dg)
    me = ev.to_mesh()
    mw = o.matrix_world
    vs = [mw @ v.co for v in me.vertices]
    tris = []
    for p in me.polygons:
        vi = list(p.vertices)
        for k in range(1, len(vi) - 1):
            tris.append((vi[0], vi[k], vi[k + 1]))
    ev.to_mesh_clear()
    return vs, tris


def _aabb(vs):
    xs = [v.x for v in vs]; ys = [v.y for v in vs]; zs = [v.z for v in vs]
    return (min(xs), max(xs), min(ys), max(ys), min(zs), max(zs))


# Штатные проходы сквозь конструкцию: линии вала в дейдвудных трубах,
# баллеры рулей в гельмпортовых трубах, туннели подруливающих устройств.
# В металле это не пересечение, а вырез с уплотнением, поэтому такие пары
# в отчёт не идут.
PENETRATIONS = (
    ("дрк_", ("корпус", "набор_", "настил_", "цистерны_")),
    ("мо_гребные_электродвигатели", ("корпус", "набор_", "настил_")),
    ("устр_подрул", ("корпус", "набор_", "настил_")),
)


def _penetration(a, b):
    for pref, others in PENETRATIONS:
        if a.startswith(pref) and b.startswith(others):
            return True
        if b.startswith(pref) and a.startswith(others):
            return True
    return False


def _encl(d):
    # Имена оболочек с заглавной («Надстройка_главная», «Палуба_главная»),
    # префиксы — строчные: сравниваем без учёта регистра, иначе всё, что
    # стоит внутри яруса, считается пересекающим его.
    return d["obj"].name.lower().startswith(ENCLOSURE)


def _contains(outer, inner, m=0.05):
    ox0, ox1, oy0, oy1, oz0, oz1 = outer
    ix0, ix1, iy0, iy1, iz0, iz1 = inner
    return (ox0 <= ix0 + m and ox1 >= ix1 - m and oy0 <= iy0 + m
            and oy1 >= iy1 - m and oz0 <= iz0 + m and oz1 >= iz1 - m)


def _inside(bvh, p, span):
    """Точка внутри замкнутой сетки? Чётность пересечений в двух лучах."""
    hits = 0
    for d in (Vector((0, 0, 1)), Vector((0, 0, -1))):
        n, o, cnt = 0, p + d * 1e-4, 0
        pos = o.copy()
        while cnt < 64:
            hit = bvh.ray_cast(pos, d, span)
            if hit[0] is None:
                break
            n += 1
            pos = hit[0] + d * 1e-4
            cnt += 1
        if n % 2 == 1:
            hits += 1
    return hits == 2


def pairs(depth=DEPTH, collections=None, verbose=True):
    """Список пар объектов, реально влезающих друг в друга."""
    dg = bpy.context.evaluated_depsgraph_get()
    objs = _mesh_objs(collections)
    data = []
    for cname, o in objs:
        vs, tris = _world_tris(o, dg)
        if not tris:
            continue
        data.append(dict(col=cname, obj=o, vs=vs, tris=tris, bb=_aabb(vs),
                         bvh=None))
    bad = []
    n = len(data)
    for i in range(n):
        a = data[i]
        for j in range(i + 1, n):
            b = data[j]
            if a["col"] in TOUCHING and b["col"] in TOUCHING:
                continue
            if _penetration(a["obj"].name, b["obj"].name):
                continue
            ax0, ax1, ay0, ay1, az0, az1 = a["bb"]
            bx0, bx1, by0, by1, bz0, bz1 = b["bb"]
            if (ax0 > bx1 - depth or bx0 > ax1 - depth
                    or ay0 > by1 - depth or by0 > ay1 - depth
                    or az0 > bz1 - depth or bz0 > az1 - depth):
                continue
            if a["bvh"] is None:
                a["bvh"] = BVHTree.FromPolygons(a["vs"], a["tris"], all_triangles=True)
            if b["bvh"] is None:
                b["bvh"] = BVHTree.FromPolygons(b["vs"], b["tris"], all_triangles=True)
            if not a["bvh"].overlap(b["bvh"]):
                continue
            span = max(ax1 - ax0, ay1 - ay0, az1 - az0,
                       bx1 - bx0, by1 - by0, bz1 - bz0) * 2 + 1.0
            # Объект, габарит которого вмещает другой, — оболочка (корпус,
            # надстройка, палуба). Находиться внутри неё нормально, поэтому
            # в эту сторону глубину не меряем.
            dirs = []
            if not _contains(b["bb"], a["bb"]) and not _encl(b):
                dirs.append((a, b))
            if not _contains(a["bb"], b["bb"]) and not _encl(a):
                dirs.append((b, a))
            if not dirs:
                continue
            dmax, dpt = 0.0, None
            for src, dst in dirs:
                for p in src["vs"]:
                    if not _inside(dst["bvh"], p, span):
                        continue
                    nr = dst["bvh"].find_nearest(p)
                    if nr[0] is None:
                        continue
                    d = (nr[0] - p).length
                    if d > dmax:
                        dmax, dpt = d, (round(p.x, 2), round(p.y, 2), round(p.z, 2))
                if dmax > depth:
                    break
            if dmax > depth:
                bad.append((a["obj"].name, b["obj"].name, round(dmax, 4), dpt))
                if verbose:
                    print("  %-34s x %-34s %.0f мм %s"
                          % (a["obj"].name, b["obj"].name, dmax * 1000, dpt))
    bad.sort(key=lambda t: -t[2])
    if verbose:
        print("объектов %d, пар с проникновением > %.0f мм: %d"
              % (n, depth * 1000, len(bad)))
    return bad


def outside_hull(tol=OUT_TOL, verbose=True):
    """Объекты, вылезающие за обшивку корпуса.

    Ниже высоты борта предел — полуширота обвода на своей высоте; выше
    (фальшборт, леера, шлюпбалки, надстройка) — полуширота по палубе:
    наружу за линию борта не должно выходить ничего.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    bad = []
    for cname, o in _mesh_objs():
        if cname in NO_HULL:
            continue
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        worst, wp = 0.0, None
        for v in me.vertices:
            p = mw @ v.co
            if p.x < -0.5 or p.x > G.LOA + 0.5:
                continue
            zb = H.side_height(p.x)
            zk = H.keel_height(p.x)
            if p.z < zk - 0.02:
                lim = APPEND_HALF      # выступающие части: винты, насадки, рули
            else:
                lim = H.half_breadth(p.x, min(max(p.z, zk), zb))
            d = abs(p.y) - lim
            if d > worst:
                worst, wp = d, (round(p.x, 2), round(p.y, 2), round(p.z, 2))
        ev.to_mesh_clear()
        if worst > tol:
            bad.append((o.name, cname, round(worst, 3), wp))
            if verbose:
                print("  %-40s %-20s +%.0f мм %s" % (o.name, cname, worst * 1000, wp))
    bad.sort(key=lambda t: -t[2])
    if verbose:
        print("за обводом корпуса: %d" % len(bad))
    return bad


def outside_super(tol=0.03, verbose=True):
    """Насыщение, вылезающее за борт надстройки (выше главной палубы)."""
    dg = bpy.context.evaluated_depsgraph_get()
    bad = []
    for cname, o in _mesh_objs(INSIDE_SUPER):
        ev = o.evaluated_get(dg)
        me = ev.to_mesh()
        mw = o.matrix_world
        worst, wp = 0.0, None
        for v in me.vertices:
            p = mw @ v.co
            if p.z < Z_SUPER or p.x < -0.5 or p.x > G.LOA + 0.5:
                continue
            lim = H.super_half_breadth(p.x)
            d = abs(p.y) - lim
            if d > worst:
                worst, wp = d, (round(p.x, 2), round(p.y, 2), round(p.z, 2))
        ev.to_mesh_clear()
        if worst > tol:
            bad.append((o.name, cname, round(worst, 3), wp))
            if verbose:
                print("  %-40s %-20s +%.0f мм %s" % (o.name, cname, worst * 1000, wp))
    bad.sort(key=lambda t: -t[2])
    if verbose:
        print("за бортом надстройки: %d" % len(bad))
    return bad


DECK_LEVELS = (0.55, 1.40, 4.20, 7.00, 9.80, 12.60)
FURNITURE = ("30_Общественные", "31_Мебель", "32_Служебные")

SUP_GAP = 0.060        # на сколько предмету позволено не доставать до опоры
SUP_SIDE = 0.080       # навеска: расстояние до переборки сбоку
SEAT_SIDE = (0.35, 0.62)   # сторона сиденья, м
SUP_SKIP = ("переборка", "пол_", "настил", "подволок", "занавес", "штора", "светильник", "люстра", "подвес", "экран",
            "проём", "дверь", "_над_", "трос", "леер", "флаг")


def _islands(bm):
    """Связные куски сетки."""
    seen, out = set(), []
    for v in bm.verts:
        if v in seen:
            continue
        stack, grp = [v], []
        seen.add(v)
        while stack:
            c = stack.pop()
            grp.append(c)
            for e in c.link_edges:
                o = e.other_vert(c)
                if o not in seen:
                    seen.add(o)
                    stack.append(o)
        out.append(grp)
    return out


def _scene_bvh(dg, collections=None):
    """Один BVH на всю обстановку: по нему ищем опору под предметом."""
    vs, ts = [], []
    for _, o in _mesh_objs(collections):
        ov, ot = _world_tris(o, dg)
        n = len(vs)
        vs += ov
        ts += [(a + n, b + n, c + n) for a, b, c in ot]
    return BVHTree.FromPolygons(vs, ts, all_triangles=True)


SUP_FLOOR = ("пол_", "настил", "палуба_", "помост", "ступен", "трап_",
             "подиум", "сцена", "эстрада", "площадка")


def _island_boxes(o, mw):
    """Габариты связных кусков сетки объекта."""
    import bmesh
    bm = bmesh.new()
    bm.from_mesh(o.data)
    out = []
    for grp in _islands(bm):
        ws = [mw @ v.co for v in grp]
        out.append((min(w.x for w in ws), max(w.x for w in ws),
                    min(w.y for w in ws), max(w.y for w in ws),
                    min(w.z for w in ws), max(w.z for w in ws)))
    bm.free()
    return out


def _sup_index():
    """Куски, на которые предмету законно опираться, и куски мебели.

    Возвращает (опоры, проверяемые). Опора — любой кусок мебели (ножка,
    тумба, ступень помоста) и любой настил, палуба, помост или трап. Корпус
    и переборки в опоры не идут: на них не ставят, к ним навешивают, и это
    проверяется отдельно боковым лучом.
    """
    sup, test = [], []
    for cname, o in _mesh_objs():
        low = o.name.lower()
        furn = cname in FURNITURE
        floor = low.startswith(SUP_FLOOR)
        if not (furn or floor):
            continue
        boxes = _island_boxes(o, o.matrix_world)
        sup += boxes
        if furn and not floor and not any(k in low for k in SUP_SKIP):
            test += [(o.name, cname, b) for b in boxes]
    return sup, test


def support(gap=SUP_GAP, verbose=True):
    """Предметы, которые ни на чём не стоят.

    Проверяется не объект целиком, а каждый связный кусок сетки: мебель зала —
    одна сетка на зал, и один улетевший стул в габарите 18 x 11 м не виден ни
    габаритом, ни центром масс, ни пересечениями.

    Кусок стоит законно, если под ним в пределах `gap` начинается другой
    кусок, чей верх доходит до его низа: палуба, помост, ступень, ножка,
    тумба. Лучами это не берётся — низ сиденья лежит ровно на верхе ножки, и
    луч, пущенный из точки внутри ножки, выходит уже под палубой; поэтому
    сравниваются габариты кусков.
    """
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = _scene_bvh(dg)
    sup, test = _sup_index()
    # раскладка опор по отметке верха: искать будем в узкой полосе
    buckets = {}
    for b in sup:
        buckets.setdefault(int(b[5] * 4), []).append(b)
    z_min = min(DECK_LEVELS)
    bad = []
    for name, cname, b in test:
        x0, x1, y0, y1, z0, z1 = b
        # низ на отметке палубы — предмет просто стоит на ней
        if min(abs(z0 - d) for d in DECK_LEVELS) <= gap:
            continue
        ok = False
        for k in range(int((z0 - gap) * 4), int((z0 + 4.0) * 4) + 2):
            for s2 in buckets.get(k, ()):
                if s2 is b:
                    continue
                # опора либо подходит верхом к низу куска, либо проходит
                # сквозь него насквозь (ствол в кроне, царга в сиденье)
                if s2[5] < z0 - gap or s2[4] > z0 + 0.006:
                    continue
                if s2[1] <= x0 + 0.002 or s2[0] >= x1 - 0.002:
                    continue
                if s2[3] <= y0 + 0.002 or s2[2] >= y1 - 0.002:
                    continue
                ok = True
                break
            if ok:
                break
        if not ok:
            cz = (z0 + z1) / 2
            for d in ((1, 0, 0), (-1, 0, 0), (0, 1, 0), (0, -1, 0)):
                sx = x1 + 0.002 if d[0] > 0 else x0 - 0.002 if d[0] < 0 \
                    else (x0 + x1) / 2
                sy = y1 + 0.002 if d[1] > 0 else y0 - 0.002 if d[1] < 0 \
                    else (y0 + y1) / 2
                if bvh.ray_cast(Vector((sx, sy, cz)), Vector(d),
                                SUP_SIDE)[0] is not None:
                    ok = True
                    break
        if not ok:
            # подвес к подволоку: вытяжной зонт камбуза висит именно так
            ok = bvh.ray_cast(Vector(((x0 + x1) / 2, (y0 + y1) / 2,
                                      z1 + 0.002)),
                              Vector((0, 0, 1)), 0.12)[0] is not None
        if not ok:
            deck = min(DECK_LEVELS, key=lambda d: abs(d - z0))
            bad.append((name, cname, round(z0 - deck, 3),
                        round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1),
                        round(z0, 2)))
    bad.sort(key=lambda t: -t[2])
    if verbose:
        print("висит в воздухе: %d кусков" % len(bad))
        agg = {}
        for r in bad:
            a = agg.setdefault(r[0], [0, 0.0])
            a[0] += 1
            a[1] = max(a[1], r[2])
        for n, (c, w) in sorted(agg.items(), key=lambda kv: -kv[1][0])[:15]:
            print("  %-34s %4d шт, до %+.0f мм" % (n, c, w * 1000))
    return bad


STILT = 0.80           # сиденье выше палубы: кресло на ходулях
STILT_SIDE = 0.42      # уже — барный табурет, ему высота положена


def stilts(limit=STILT, verbose=True):
    """Сиденья, поднятые над палубой ножками вместо помоста.

    Подъём рядов в зале делают ступенями помоста. Если ряд подняли, удлинив
    ножки, каждое кресло стоит на палках над пустым полом — в кадре это и
    читается как «кресла взлетают». Барные табуреты уже по габариту и в
    проверку не идут: им высота положена.
    """
    _, test = _sup_index()
    bad = []
    for name, cname, b in test:
        x0, x1, y0, y1, z0, z1 = b
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        if dz > 0.12 or not (STILT_SIDE <= dx <= SEAT_SIDE[1])                 or not (STILT_SIDE <= dy <= SEAT_SIDE[1]):
            continue
        deck = min(DECK_LEVELS, key=lambda d: abs(d - z0))
        if z0 - deck > limit:
            bad.append((name, cname, round(z0 - deck, 3),
                        round((x0 + x1) / 2, 1), round((y0 + y1) / 2, 1)))
    bad.sort(key=lambda t: -t[2])
    if verbose:
        print("сиденье на ходулях: %d" % len(bad))
        agg = {}
        for r in bad:
            a = agg.setdefault(r[0], [0, 0.0])
            a[0] += 1
            a[1] = max(a[1], r[2])
        for n, (c, w) in sorted(agg.items(), key=lambda kv: -kv[1][0])[:10]:
            print("  %-34s %4d шт, до %.2f м над палубой" % (n, c, w))
    return bad


SEAT_REACH = 0.80          # от кромки сиденья до кромки стола, м


def seating(reach=SEAT_REACH, verbose=True):
    """Стулья, повёрнутые от стола.

    Сиденье — плоский кусок со стороной 0,35..0,62 м на высоте 0,36..0,52 м
    над палубой; спинка — узкий кусок рядом и выше. Взгляд сидящего идёт от
    спинки к сиденью; столешница обязана лежать в этом полупространстве и не
    дальше `reach` от кромки сиденья.
    """
    import bmesh
    bad = []
    for cname, o in _mesh_objs(FURNITURE):
        bm = bmesh.new()
        bm.from_mesh(o.data)
        mw = o.matrix_world
        seats, backs, tables = [], [], []
        for grp in _islands(bm):
            ws = [mw @ v.co for v in grp]
            x0 = min(w.x for w in ws); x1 = max(w.x for w in ws)
            y0 = min(w.y for w in ws); y1 = max(w.y for w in ws)
            z0 = min(w.z for w in ws); z1 = max(w.z for w in ws)
            dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
            h = z0 - min(DECK_LEVELS, key=lambda d: abs(d - z0))
            c = Vector(((x0 + x1) / 2, (y0 + y1) / 2, 0.0))
            box = (x0, x1, y0, y1)
            if dz < 0.12 and SEAT_SIDE[0] <= dx <= SEAT_SIDE[1] \
                    and SEAT_SIDE[0] <= dy <= SEAT_SIDE[1] \
                    and 0.36 <= h <= 0.52:
                seats.append((c, box))
            elif dz > 0.25 and min(dx, dy) < 0.16 and 0.42 <= h <= 0.60:
                backs.append(c)
            elif dz < 0.12 and 0.62 <= h <= 0.82 and max(dx, dy) >= 0.50:
                tables.append((c, box))
        bm.free()
        if not seats or not tables:
            continue
        for c, box in seats:
            bk = min(backs, key=lambda b: (b - c).length) if backs else None
            if bk is None or (bk - c).length > 0.45:
                continue
            look = c - bk
            look.z = 0.0
            if look.length < 1e-6:
                continue
            look.normalize()
            best = None
            for tc, tb in tables:
                d = tc - c
                d.z = 0.0
                if d.length < 1e-6:
                    continue
                gapd = max(tb[0] - box[1], box[0] - tb[1],
                           tb[2] - box[3], box[2] - tb[3], 0.0)
                if gapd > reach:
                    continue
                cosa = d.normalized().dot(look)
                if best is None or cosa > best:
                    best = cosa
            if best is None or best < 0.35:
                bad.append((o.name, cname, round(c.x, 1), round(c.y, 1),
                            None if best is None else round(best, 2)))
    if verbose:
        print("стул повёрнут от стола: %d" % len(bad))
        agg = {}
        for r in bad:
            agg[r[0]] = agg.get(r[0], 0) + 1
        for n, c in sorted(agg.items(), key=lambda kv: -kv[1]):
            print("  %-34s %4d шт" % (n, c))
    return bad


def seats(verbose=True, save=True):
    """Сколько посадочных мест реально стоит в каждом помещении.

    Считаются сиденья: плоские куски со стороной 0,35…0,62 м на высоте
    0,36…0,52 м над палубой, плюс круглые сиденья барных табуретов. Нужно,
    чтобы вместимость в пояснительной записке не расходилась с моделью.
    """
    _, test = _sup_index()
    cnt = {}
    for name, cname, b in test:
        x0, x1, y0, y1, z0, z1 = b
        dx, dy, dz = x1 - x0, y1 - y0, z1 - z0
        h = z0 - min(DECK_LEVELS, key=lambda d: abs(d - z0))
        if dz > 0.10:
            continue
        # сиденье стула — 0,46 м в стороне; царга под ним 0,42 м и той же
        # толщины, поэтому нижняя граница жёсткая, иначе стул считается дважды
        if 0.44 <= dx <= 0.62 and 0.44 <= dy <= 0.62 and 0.20 <= h <= 1.20:
            cnt[name] = cnt.get(name, 0) + 1
        elif 0.30 <= dx <= 0.42 and 0.30 <= dy <= 0.42 and 0.62 <= h <= 0.95:
            cnt[name] = cnt.get(name, 0) + 1     # барный табурет
        elif 0.50 <= max(dx, dy) <= 1.15 and 0.40 <= min(dx, dy) <= 0.80                 and 0.30 <= h <= 0.52:
            cnt[name] = cnt.get(name, 0) + 1     # подушка дивана или кресла
    if save:
        import json
        with open(os.path.join(ROOT_SRC, "lib", "gorizont_seats.json"),
                  "w", encoding="utf-8") as f:
            json.dump(cnt, f, ensure_ascii=False, indent=1, sort_keys=True)
    if verbose:
        for n, c in sorted(cnt.items(), key=lambda kv: -kv[1]):
            print("  %-34s %4d мест" % (n, c))
        print("  всего %d" % sum(cnt.values()))
    return cnt


def enclosure(eye=1.60, rays=72, verbose=True):
    """Дыры в ограждении помещений.

    Из точек внутри каждой закрытой зоны на высоте глаз пускается веер лучей
    в горизонт и один вверх. Луч, ушедший дальше габарита судна, означает,
    что помещение открыто наружу: именно так с палубы носового салона стало
    видно горизонт.

    Пробные точки ставятся по измеренной полуширине, а не по габаритной
    ширине судна: точка на 6,9 м от диаметрали в носу оказывается снаружи
    обвода, и тогда «дыру» показывает любое помещение.
    """
    from lib import gorizont_ga as GA
    dg = bpy.context.evaluated_depsgraph_get()
    bvh = _scene_bvh(dg)
    far = G.LOA + G.BEAM
    bad = []
    for deck, zones in GA.DECKS.items():
        z = G.DECKS[deck] + eye
        for zone in zones:
            x0, x1, kind, name = zone[0], zone[1], zone[2], zone[3]
            if kind in ("open", "tech"):
                continue
            for fx in (0.12, 0.5, 0.88):
                px = x0 + (x1 - x0) * fx
                hw = far
                for d in (Vector((0, 1, 0)), Vector((0, -1, 0))):
                    hit = bvh.ray_cast(Vector((px, 0.0, z)), d, far)
                    if hit[0] is not None:
                        hw = min(hw, hit[3])
                if hw > G.BEAM or hw < 0.60:
                    continue          # диаметраль перегорожена шахтой
                for fy in (-0.55, 0.0, 0.55):
                    py = hw * fy
                    miss = []
                    for i in range(rays):
                        a = 2 * math.pi * i / rays
                        d = Vector((math.cos(a), math.sin(a), 0.0))
                        if bvh.ray_cast(Vector((px, py, z)), d,
                                        far)[0] is None:
                            miss.append(int(math.degrees(a)))
                    up = bvh.ray_cast(Vector((px, py, z)),
                                      Vector((0, 0, 1)), 6.0)[0] is None
                    if miss or up:
                        bad.append((deck, name, round(px, 1), round(py, 1),
                                    len(miss), up, miss[:6]))
    if verbose:
        print("дыр в ограждении: %d точек" % len(bad))
        for r in bad[:15]:
            print("  %-10s %-36s x=%6.1f y=%5.1f  мимо %3d%s  %s"
                  % (r[0], r[1][:36], r[2], r[3], r[4],
                     "  нет подволока" if r[5] else "", r[6]))
    return bad


def audit(depth=DEPTH, tol=OUT_TOL, verbose=True):
    if verbose:
        print("--- пересечения ---")
    ov = pairs(depth, verbose=verbose)
    if verbose:
        print("--- обвод ---")
    out = outside_hull(tol, verbose=verbose)
    if verbose:
        print("--- борт надстройки ---")
    sup = outside_super(verbose=verbose)
    if verbose:
        print("--- опора ---")
    fl = support(verbose=verbose)
    if verbose:
        print("--- посадочные места ---")
    st = seating(verbose=verbose)
    if verbose:
        print("--- ограждение ---")
    en = enclosure(verbose=verbose)
    return {"пересечения": ov, "за_обводом": out, "за_надстройкой": sup,
            "висящие": fl, "стулья": st, "ограждение": en,
            "чисто": not (ov or out or sup or fl or st or en)}


def watertight(collections=None, verbose=True):
    """Объекты с открытыми кромками: у ребра одна грань — значит, в сетке щель.

    Считается по сетке после модификаторов. Лист без толщины даёт открытые
    кромки по всему периметру; замкнутое тело — ноль. Норма — ноль везде:
    такие объекты можно править руками и резать булевыми операциями.
    """
    import bmesh
    dg = bpy.context.evaluated_depsgraph_get()
    bad = []
    for cname, o in _mesh_objs(collections):
        me = o.evaluated_get(dg).to_mesh()
        bm = bmesh.new()
        bm.from_mesh(me)
        n = sum(1 for e in bm.edges if e.is_boundary)
        bm.free()
        o.evaluated_get(dg).to_mesh_clear()
        if n:
            bad.append((o.name, n))
    bad.sort(key=lambda t: -t[1])
    if verbose:
        print("открытые кромки: %d объектов" % len(bad))
        for name, n in bad[:20]:
            print("   %-40s %d рёбер" % (name, n))
    return bad
