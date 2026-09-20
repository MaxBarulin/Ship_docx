# -*- coding: utf-8 -*-
r"""Модель узла ВГ-2026.16.00 «Фундамент установки очистки сточных вод».

Строится по gorizont_awts: поддон с комингсом, продольные и поперечные
балки-тавры, подушки под лапы, стопоры-ограничители, амортизаторы и
площадка обслуживания. Размеры и количество берутся из модуля расчёта,
поэтому чертёж, спецификация и модель не могут разойтись.

    exec(open(r"E:\Ship_docx\scripts\blender_фундамент_очистки.py", encoding="utf-8").read())
    build_foundation()
"""
import bpy, bmesh, math, sys

ROOT_SRC = r"E:\Ship_docx\src"
if ROOT_SRC not in sys.path:
    sys.path.insert(0, ROOT_SRC)
from lib import gorizont_awts as A

COL = "34_Фундамент_очистки"


def _col():
    c = bpy.data.collections.get(COL)
    if c is None:
        c = bpy.data.collections.new(COL)
        bpy.context.scene.collection.children.link(c)
    return c


def _box(bm, x0, x1, y0, y1, z0, z1):
    v = [bm.verts.new(p) for p in
         ((x0, y0, z0), (x1, y0, z0), (x1, y1, z0), (x0, y1, z0),
          (x0, y0, z1), (x1, y0, z1), (x1, y1, z1), (x0, y1, z1))]
    for f in ((0, 1, 2, 3), (7, 6, 5, 4), (0, 4, 5, 1),
              (1, 5, 6, 2), (2, 6, 7, 3), (3, 7, 4, 0)):
        bm.faces.new([v[k] for k in f])


def _cyl(bm, cx, cy, z0, z1, r, seg=16):
    rings = []
    for z in (z0, z1):
        rings.append([bm.verts.new((cx + r * math.cos(2 * math.pi * k / seg),
                                    cy + r * math.sin(2 * math.pi * k / seg), z))
                      for k in range(seg)])
    for k in range(seg):
        k2 = (k + 1) % seg
        bm.faces.new([rings[0][k], rings[1][k], rings[1][k2], rings[0][k2]])
    bm.faces.new(rings[0][::-1])
    bm.faces.new(rings[1])


def _obj(name, bm, mat):
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new(name)
    bm.to_mesh(me)
    bm.free()
    o = bpy.data.objects.new(name, me)
    m = bpy.data.materials.get(mat)
    if m:
        o.data.materials.append(m)
    _col().objects.link(o)
    return o


def unit_feet():
    """Координаты лап оборудования (точек опирания) по каждому аппарату."""
    from lib import gorizont_mach as Mch
    boxes = {e[0]: e[3] for e in Mch.EQUIPMENT
             if e[0] in ("МБР", "БИО", "УФ", "СЕП")}
    out = []
    for code, dry, liq, n in A.UNITS:
        x0, x1, y0, y1, z0, z1 = boxes[code]
        dx, dy = (x1 - x0) * 0.16, (y1 - y0) * 0.16
        if n == 4:
            pts = [(x0 + dx, y0 + dy), (x1 - dx, y0 + dy),
                   (x1 - dx, y1 - dy), (x0 + dx, y1 - dy)]
        else:
            pts = [(x0 + dx, (y0 + y1) / 2), (x1 - dx, (y0 + y1) / 2)]
        out.append((code, pts))
    return out


def cut_tank_top():
    """Вырезать в настиле второго дна колодец под поддон фундамента."""
    g = A.report()["geometry"]
    tgt = bpy.data.objects.get("настил_второго_дна")
    if tgt is None:
        return False
    bm = bmesh.new()
    _box(bm, g["x0"] - 0.12, g["x1"] + 0.12, g["y0"] - 0.12, g["y1"] + 0.12,
         g["z_tray"] - 0.10, g["z_tank_top"] + 0.05)
    bmesh.ops.recalc_face_normals(bm, faces=bm.faces)
    me = bpy.data.meshes.new("_well")
    bm.to_mesh(me)
    bm.free()
    cut = bpy.data.objects.new("_well", me)
    _col().objects.link(cut)
    md = tgt.modifiers.new("колодец", "BOOLEAN")
    md.operation = "DIFFERENCE"
    md.solver = "EXACT"
    md.object = cut
    bpy.context.view_layer.objects.active = tgt
    try:
        bpy.ops.object.modifier_apply(modifier=md.name)
        ok = True
    except RuntimeError:
        tgt.modifiers.remove(md)
        ok = False
    bpy.data.objects.remove(cut, do_unlink=True)
    return ok


def build_foundation(verbose=True):
    for o in list(_col().objects):
        bpy.data.objects.remove(o, do_unlink=True)
    g = A.report()["geometry"]
    x0, x1, y0, y1 = g["x0"], g["x1"], g["y0"], g["y1"]
    z_tray, z_top, h = g["z_tray"], g["z_top"], g["h_beam"]
    made = []

    # поддон с комингсом
    bm = bmesh.new()
    _box(bm, x0 - 0.10, x1 + 0.10, y0 - 0.10, y1 + 0.10, z_tray - 0.006, z_tray)
    c = g["coaming"]
    for a, b, cc, d in ((x0 - 0.10, x0 - 0.092, y0 - 0.10, y1 + 0.10),
                        (x1 + 0.092, x1 + 0.10, y0 - 0.10, y1 + 0.10),
                        (x0 - 0.10, x1 + 0.10, y0 - 0.10, y0 - 0.092),
                        (x0 - 0.10, x1 + 0.10, y1 + 0.092, y1 + 0.10)):
        _box(bm, a, b, cc, d, z_tray, z_tray + c)
    made.append(_obj("фнд_очистки_поддон", bm, "гор_металл"))

    # балки фундамента
    bm = bmesh.new()
    zb0, zb1 = z_top - h, z_top
    for i in range(g["n_long"]):
        y = y0 + g["pitch_long"] * i
        _box(bm, x0, x1, y - 0.004, y + 0.004, zb0, zb1 - 0.010)      # стенка
        _box(bm, x0, x1, y - 0.050, y + 0.050, zb1 - 0.010, zb1)      # поясок
    for j in range(g["n_cross"]):
        x = x0 + g["pitch_cross"] * j
        _box(bm, x - 0.003, x + 0.003, y0, y1, zb0, zb1 - 0.028)
        _box(bm, x - 0.040, x + 0.040, y0, y1, zb1 - 0.028, zb1 - 0.020)
    made.append(_obj("фнд_очистки_рама", bm, "гор_набор_палуба"))

    # подушки, амортизаторы, стопоры
    bm_p, bm_a, bm_s = bmesh.new(), bmesh.new(), bmesh.new()
    for code, pts in unit_feet():
        for (px, py) in pts:
            _box(bm_p, px - 0.09, px + 0.09, py - 0.09, py + 0.09,
                 z_top, z_top + 0.016)
            _cyl(bm_a, px, py, z_top + 0.016, z_top + 0.086, 0.075)
            _box(bm_a, px - 0.085, px + 0.085, py - 0.085, py + 0.085,
                 z_top + 0.086, g["z_equip"])
    # стопоры ставятся вплотную к лапам блока, но с зазором: они ограничивают
    # перемещение на амортизаторах, а не подпирают аппарат
    for sx in (x0 + 0.12, x1 - 0.12):
        for sy in (y0 + 0.12, y1 - 0.12):
            _box(bm_s, sx - 0.06, sx + 0.06, sy - 0.012, sy + 0.012,
                 z_top, g["z_equip"] + 0.05)
            _box(bm_s, sx - 0.012, sx + 0.012, sy - 0.06, sy + 0.06,
                 z_top, g["z_equip"] + 0.05)
    made.append(_obj("фнд_очистки_подушки", bm_p, "гор_металл"))
    made.append(_obj("фнд_очистки_амортизаторы", bm_a, "гор_устройство"))
    made.append(_obj("фнд_очистки_стопоры", bm_s, "гор_металл"))

    # площадка обслуживания вдоль блока
    bm = bmesh.new()
    zp = g["z_tank_top"]
    _box(bm, x0 - 0.90, x0 - 0.14, y0 - 0.10, y1 + 0.10, zp, zp + 0.004)
    for sy in (y0, (y0 + y1) / 2, y1):
        _box(bm, x0 - 0.86, x0 - 0.80, sy - 0.03, sy + 0.03, z_tray, zp)
    made.append(_obj("фнд_очистки_площадка", bm, "гор_трап"))
    cut_tank_top()
    if verbose:
        print("узел собран: %s" % ", ".join(o.name for o in made))
    return [o.name for o in made]
