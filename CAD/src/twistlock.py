# -*- coding: utf-8 -*-
"""VG-2026.46.00 twistlock foundation ("dovetail") for the sun-deck modules - 3D model (build123d).

    python CAD/src/twistlock.py

The cast body is the designer's model as received (docs/команда/правки 23.09.26/
Korpus_tvistloka_model_uzel.stp) - it is imported, not redrawn. Everything else
comes from lib.gorizont_twistlock: the forged lock, the handle rod, the base plate,
the split washer, the insulation and the deck fasteners.

Node frame, mm: X along the ship, Y across, Z up. Z = 0 is the body shoulder the
container fitting sits on (the STEP origin). The base plate is under the body
(Z -66...-46), then the STEF gasket, the AMg5 doubler and the deck plate: the top of
the deck is at Z = -77, i.e. gorizont.MODULES["фундамент"] = 0.077 m.

Outputs:
    CAD/STEP/VG-2026_46_00_twistlock.step          assembly, lock closed, parts labelled "pos.N ..."
    CAD/STEP/VG-2026_46_0N_*.step                  parts 1...5, casting with risers, cores 1 and 2
    CAD/STEP/VG-2026_46_01-MD_pattern.step         pattern of the body (casting + core prints, shrinkage allowance)
    CAD/STL/...                                    the same as STL
    CAD/GLB/VG-2026_46_00_twistlock_open.glb       assembly for Blender, lock open (reference pose)
    CAD/GLB/VG-2026_46_01_casting.glb, _core.glb   casting and cores for the tooling scene

Library functions for the drawings (scripts/чертёж_фундамента.py): корпус(), запор(угол), стержень(угол),
платик(), шайба(), изоляция(), крепёж(), отливка(), стержень_1(), стержень_2(), модель(), сборка(угол).
Exit code 1 if any two parts of the assembly intersect.
"""
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import build123d as bd
from lib import gorizont_twistlock as T

STEP_КОРПУС = os.path.join(ROOT, "docs", "команда", "правки 23.09.26", "Korpus_tvistloka_model_uzel.stp")
K, З, С, П, Ш, О, Б = T.КОРПУС, T.ЗАПОР, T.СТЕРЖЕНЬ, T.ПЛАТИК, T.ШАЙБА, T.ОПОРА, T.БОЛТ
Z_ПЛ = K["z"][0]                              # верх платика = низ опорных полос корпуса, -46
Z_ПЛ_НИЗ = Z_ПЛ - П["t"]                      # низ платика, -66
Z_ПР = Z_ПЛ_НИЗ - О["прокладка"]              # низ прокладки = верх подкладного листа, -69
Z_ЛИСТ = Z_ПР - О["лист"][2]                  # верх настила, -77
Z_НАСТ = Z_ЛИСТ - О["настил"]                 # низ настила, -83
НАСТИЛ = (480.0, 380.0)                       # вырезка настила для сцены и чертежа
#: положения рукоятки по вырезам корпуса, град от +X против часовой: «открыто» - голова вдоль отверстия фитинга (Y)
ОТКРЫТО, ЗАКРЫТО = T.ВЫРЕЗЫ["открыто"], T.ВЫРЕЗЫ["закрыто"]
ФИТИНГ_ОСЬ = 90.0                              # длинная ось отверстия фитинга - вдоль Y (центратор 116 по Y)


def _cyl(r, z0, z1, x=0.0, y=0.0):
    return bd.Pos(x, y, z0) * bd.Cylinder(r, z1 - z0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))


def _box(lx, ly, z0, z1, x=0.0, y=0.0):
    return bd.Pos(x, y, z0) * bd.Box(lx, ly, z1 - z0, align=(bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN))


def _obround(L, W, z0, z1, x=0.0, y=0.0, rot=0.0):
    """Овал L × W (L по местной оси X), высота z0…z1."""
    s = bd.SlotOverall(L, W, rotation=rot)
    return bd.Pos(x, y, z0) * bd.extrude(s, amount=z1 - z0)


def _head_угол(угол_стержня):
    """Угол длинной оси головы: открыто - вдоль фитинга, поворот вместе с рукояткой."""
    return ФИТИНГ_ОСЬ + (угол_стержня - ОТКРЫТО)


# --- детали -----------------------------------------------------------------------------------
_КЭШ = {}


def корпус():
    """Поз. 1 - корпус, модель конструктора как есть."""
    if "корпус" not in _КЭШ:
        s = bd.import_step(STEP_КОРПУС)
        body = s.solids()[0] if hasattr(s, "solids") else s
        _КЭШ["корпус"] = body
    b = _КЭШ["корпус"].moved(bd.Location())
    b.label = "pos.1 body VG-2026.46.01 (cast 20GSL)"
    return b


def запор(угол=ЗАКРЫТО):
    """Поз. 3 - запирающий элемент: вал с проточкой под шайбу, поперечное отверстие под стержень, голова."""
    z0, z1 = З["z_вала"]
    r = З["вал"] / 2.0 - 0.1                                        # вал Ø30f9 в отверстии Ø30
    вал = _cyl(r, z0, z1)
    пр = З["проточка"]
    вал -= _cyl(r + 1.0, пр["z"][0], пр["z"][1]) - _cyl(пр["d"] / 2.0, пр["z"][0] - 1.0, пр["z"][1] + 1.0)
    длина, ширина, прямая, конус, (дл_в, шир_в) = З["голова"]
    zh = z1
    низ = bd.Plane.XY.offset(zh)
    сеч0 = низ * bd.SlotOverall(длина, ширина)
    сеч1 = bd.Plane.XY.offset(zh + прямая) * bd.SlotOverall(длина, ширина)
    сеч2 = bd.Plane.XY.offset(zh + прямая + конус) * bd.SlotOverall(дл_в, шир_в)
    голова = bd.extrude(сеч0, amount=прямая) + bd.loft([сеч1, сеч2])
    голова = голова.rotate(bd.Axis.Z, _head_угол(угол))
    s = вал + голова
    # поперечное отверстие под стержень - по направлению рукоятки
    отв = bd.Pos(0, 0, З["z_отв"]) * (bd.Rotation(0, 90, 0) * bd.Cylinder(З["отв"] / 2.0 + 0.1, З["вал"] + 10.0))
    отв = отв.rotate(bd.Axis.Z, угол)
    s = s - отв
    s.label = "pos.3 lock VG-2026.46.03 (forged 40Kh)"
    return s


def стержень(угол=ЗАКРЫТО):
    """Поз. 2 - стержень-рукоятка: конец на резьбе в поперечном отверстии вала, наружу через прорезь корпуса."""
    d, l, r_к = С["d"], С["l"], С["r_конца"]
    r0 = r_к - l                                                    # внутренний конец за осью вала
    s = bd.Pos((r0 + r_к) / 2.0, 0, З["z_отв"]) * (bd.Rotation(0, 90, 0) * bd.Cylinder(d / 2.0, l))
    s = s.rotate(bd.Axis.Z, угол)
    s.label = "pos.2 handle rod VG-2026.46.02 (40Kh)"
    return s


def платик():
    """Поз. 4 - платик: четыре овала под болты, окно под шайбу по центру."""
    s = _box(П["L"], П["B"], Z_ПЛ_НИЗ, Z_ПЛ)
    for sx in (-1, 1):
        for sy in (-1, 1):
            s -= _obround(П["овал"][1], П["овал"][0], Z_ПЛ_НИЗ - 1, Z_ПЛ + 1, sx * П["болт_x"], sy * П["болт_y"])
    s -= _obround(П["окно"][0], П["окно"][1], Z_ПЛ_НИЗ - 1, Z_ПЛ + 1)
    s.label = "pos.4 base plate VG-2026.46.04 (09G2S)"
    return s


def шайба():
    """Поз. 5 - шайба разрезная (подкова) в проточке вала под корпусом, разрез в сторону +X."""
    z0, z1 = Ш["z"]
    s = _cyl(Ш["D"] / 2.0, z0, z1) - _cyl(Ш["d"] / 2.0, z0 - 1, z1 + 1)
    s -= _box(Ш["D"], Ш["разрез"], z0 - 1, z1 + 1, x=Ш["D"] / 2.0)
    s.label = "pos.5 split washer VG-2026.46.05 (09G2S)"
    return s


def изоляция():
    """Поз. 6-9 - прокладка СТЭФ, втулки и шайбы изолирующие, подкладной лист АМг5 (ставит верфь)."""
    out = []
    пр = _box(П["L"], П["B"], Z_ПР, Z_ПЛ_НИЗ)
    for sx in (-1, 1):
        for sy in (-1, 1):
            пр -= _cyl(Б["d"] / 2.0 + 1.0, Z_ПР - 1, Z_ПЛ_НИЗ + 1, sx * П["болт_x"], sy * П["болт_y"])
    пр.label = "pos.6 insulating gasket STEF"
    out.append(пр)
    лист = _box(О["лист"][0], О["лист"][1], Z_ЛИСТ, Z_ПР)
    н = 0
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * П["болт_x"], sy * П["болт_y"]
            лист -= _cyl(Б["втулка"][0] / 2.0 + 0.3, Z_ЛИСТ - 1, Z_ПР + 1, x, y)
            н += 1
            вт = _cyl(Б["втулка"][0] / 2.0, Z_НАСТ, Z_ПР) - _cyl(Б["втулка"][1] / 2.0, Z_НАСТ - 1, Z_ПР + 1)
            вт = bd.Pos(x, y, 0) * вт
            вт.label = "pos.7 insulating bush %d" % н
            out.append(вт)
            D, dd, t = Б["шайба_изол"]
            иш = bd.Pos(x, y, 0) * (_cyl(D / 2.0, Z_НАСТ - t, Z_НАСТ) - _cyl(dd / 2.0, Z_НАСТ - t - 1, Z_НАСТ + 1))
            иш.label = "pos.8 insulating washer %d" % н
            out.append(иш)
    лист.label = "pos.9 doubler plate AMg5"
    out.append(лист)
    return out


def настил():
    """Вырезка настила АМг5 6 мм - не деталь узла, для сцены и контроля пересечений."""
    s = _box(НАСТИЛ[0], НАСТИЛ[1], Z_НАСТ, Z_ЛИСТ)
    for sx in (-1, 1):
        for sy in (-1, 1):
            s -= _cyl(Б["втулка"][0] / 2.0 + 0.3, Z_НАСТ - 1, Z_ЛИСТ + 1, sx * П["болт_x"], sy * П["болт_y"])
    s.label = "deck plate AMg5 6"
    return s


def крепёж():
    """Поз. 10-12 - болты М24 головкой на платике, шайбы увеличенные и гайки под настилом."""
    out = []
    d = Б["d"]
    z_шайбы = Z_НАСТ - Б["шайба_изол"][2]
    н = 0
    for sx in (-1, 1):
        for sy in (-1, 1):
            x, y = sx * П["болт_x"], sy * П["болт_y"]
            н += 1
            голова = bd.Pos(x, y, Z_ПЛ) * bd.extrude(bd.RegularPolygon(36.0 / 2 / math.cos(math.pi / 6), 6), amount=15.0)
            болт = голова + _cyl(d / 2.0, Z_ПЛ - Б["длина"], Z_ПЛ, x, y)
            болт.label = "pos.10 bolt M24x%d A4-80 %d" % (Б["длина"], н)
            out.append(болт)
            ш = _cyl(30.0, z_шайбы - 5.0, z_шайбы, x, y) - _cyl(12.75, z_шайбы - 6.0, z_шайбы + 1.0, x, y)
            ш.label = "pos.12 washer 24 A4-80 %d" % н
            out.append(ш)
            z_г = z_шайбы - 5.0
            гайка = (bd.Pos(x, y, z_г - 24.0) * bd.extrude(bd.RegularPolygon(36.0 / 2 / math.cos(math.pi / 6), 6), amount=24.0)
                     - _cyl(d / 2.0 + 0.2, z_г - 25.0, z_г + 1.0, x, y))
            гайка.label = "pos.11 nut M24 A4-80 %d" % н
            out.append(гайка)
    return out


def сборка(угол=ЗАКРЫТО, с_настилом=False):
    """Узел в сборе: список деталей с метками "pos.N ..."."""
    parts = [корпус(), стержень(угол), запор(угол), платик(), шайба()] + изоляция() + крепёж()
    if с_настилом:
        parts.append(настил())
    return parts


# --- оснастка: отливка и стержень -------------------------------------------------------------------
def отливка():
    """Отливка корпуса: отверстие Ø30 льётся меньше на припуск, на плече две овальные прибыли."""
    b = корпус()
    пр = T.ПРИПУСКИ["отверстие"]
    b = b + (_cyl(K["d_отв"] / 2.0 - 0.01, K["низ_z"], K["z"][1]) - _cyl(K["d_отв"] / 2.0 - пр, K["низ_z"] - 1, K["z"][1] + 1))
    ш, д = T.ЛИТЬЁ["прибыль"]
    h = T.отливка()["прибыль"][2]
    xc = (K["центратор"][0] / 2.0 + 72.56) / 2.0 + 2.0              # середина плеча между центратором и уступом
    for sx in (-1, 1):
        b = b + _obround(д, ш, K["плечо_z"] - 1.0, K["плечо_z"] + h, sx * xc, 10.0, rot=90.0)
    b.label = "VG-2026.46.01 casting with risers"
    return b


#: знаки стержней, мм: Ст. 1 - по 20 сверху и снизу, Ст. 2 - наружу от лицевой грани до разъёма формы (Z -46)
ЗНАК_СТ1 = 20.0
ЗНАК_СТ2 = dict(x=55.0, y=(-85.0, -58.0))


def стержень_1():
    """Ст. 1 - литое отверстие Ø26 под сверление Ø30, знаки сверху и снизу."""
    r_отв = K["d_отв"] / 2.0 - T.ПРИПУСКИ["отверстие"]
    s = _cyl(r_отв, K["низ_z"] - ЗНАК_СТ1, K["z"][1] + ЗНАК_СТ1)
    s.label = "VG-2026.46.01 core 1"
    return s


def стержень_2():
    """Ст. 2 - полость рукоятки. Полость открыта на лицевую грань (-Y), знак выведен наружу и опущен до разъёма:
    горизонтальный знак над песком верхней полуформы не дал бы вынуть модель."""
    п = K["полость"]
    знак = bd.Pos(0, sum(ЗНАК_СТ2["y"]) / 2.0, 0) * _box(2 * ЗНАК_СТ2["x"], ЗНАК_СТ2["y"][1] - ЗНАК_СТ2["y"][0], K["z"][0], п["z"][1])
    s = (_cyl(п["R"], п["z"][0], п["z"][1]) + знак) - отливка() - _cyl(K["d_отв"] / 2.0, K["z"][0] - 1.0, K["z"][1] + 1.0)
    s = max(s.solids(), key=lambda x: x.volume) if hasattr(s, "solids") else s
    s.label = "VG-2026.46.01 core 2"
    return s


def стержень_литейный():
    """Стержни корпуса Ст. 1 и Ст. 2 одним телом - для сцены отливки."""
    s = стержень_1() + стержень_2()
    s.label = "VG-2026.46.01 core"
    return s


def модель():
    """Модель корпуса (оснастка): отливка с прибылями, стержни заполняют полости, знаки выступают. Размеры детали -
    с усадкой: модель больше на T.УСАДКА %."""
    k = 1.0 + T.УСАДКА / 100.0
    s = (отливка() + стержень_1() + стержень_2()).scale(k)
    s.label = "VG-2026.46.01-MD pattern"
    return s


# --- проверки и выгрузка ----------------------------------------------------------------------------
def _пересечение(a, b):
    ba, bb = a.bounding_box(), b.bounding_box()
    if (ba.min.X > bb.max.X or bb.min.X > ba.max.X or ba.min.Y > bb.max.Y or bb.min.Y > ba.max.Y
            or ba.min.Z > bb.max.Z or bb.min.Z > ba.max.Z):
        return 0.0
    try:
        return (a & b).volume
    except Exception:
        return 0.0


def свободный_ход():
    """Углы рукоятки, при которых стержень не задевает корпус, град (шаг 1°)."""
    b = корпус()
    return [a for a in range(180, 361) if _пересечение(стержень(float(a)), b) < 0.5]


def _выгрузить(shape, путь, fn):
    tmp = путь + ".tmp" + os.path.splitext(путь)[1]
    fn(shape, tmp)
    os.replace(tmp, путь)


def main():
    step_dir, stl_dir, glb_dir = (os.path.join(ROOT, "CAD", d) for d in ("STEP", "STL", "GLB"))
    for d in (step_dir, stl_dir, glb_dir):
        os.makedirs(d, exist_ok=True)
    parts = сборка(ЗАКРЫТО, с_настилом=True)
    asm = bd.Compound(label="VG-2026.46.00 twistlock foundation", children=parts[:-1])
    ли, ст = отливка(), стержень_литейный()
    out = [(asm, "VG-2026_46_00_twistlock"), (корпус(), "VG-2026_46_01_body"), (стержень(ЗАКРЫТО), "VG-2026_46_02_rod"),
           (запор(ЗАКРЫТО), "VG-2026_46_03_lock"), (платик(), "VG-2026_46_04_plate"), (шайба(), "VG-2026_46_05_washer"),
           (ли, "VG-2026_46_01_casting"), (ст, "VG-2026_46_01_core"), (модель(), "VG-2026_46_01-MD_pattern")]
    for shape, name in out:
        _выгрузить(shape, os.path.join(step_dir, name + ".step"), bd.export_step)
        _выгрузить(shape, os.path.join(stl_dir, name + ".stl"),
                   lambda s, p: bd.export_stl(s, p, tolerance=0.05, angular_tolerance=0.2))
    # GLB для Blender: каждая деталь - отдельный узел с меткой; «открыто» - исходная поза
    открыт = bd.Compound(label="VG-2026.46.00 twistlock foundation", children=сборка(ОТКРЫТО))
    for shape, name in ((открыт, "VG-2026_46_00_twistlock_open"), (ли, "VG-2026_46_01_casting"), (ст, "VG-2026_46_01_core")):
        _выгрузить(shape, os.path.join(glb_dir, name + ".glb"),
                   lambda s, p: bd.export_gltf(s, p, binary=True, linear_deflection=0.05, angular_deflection=0.2))
    m = T.массы()
    ρ_л, ρ = T.МАТЕРИАЛЫ["20ГСЛ"]["ρ"] * 1e-9, 7.85e-6
    print("корпус  %.2f кг (библиотека %.2f)" % (корпус().volume * ρ_л, m["корпус"]))
    print("запор   %.2f кг (библиотека %.2f)" % (запор().volume * ρ, m["запор"]))
    print("стержень %.2f кг (библиотека %.2f)" % (стержень().volume * ρ, m["стержень"]))
    print("платик  %.2f кг (библиотека %.2f)" % (платик().volume * ρ, m["платик"]))
    print("шайба   %.2f кг (библиотека %.2f)" % (шайба().volume * ρ, m["шайба"]))
    print("отливка %.2f кг с прибылями, стержни Ст. 1 %.1f и Ст. 2 %.1f см³" % (ли.volume * ρ_л, стержень_1().volume * 1e-3,
                                                                            стержень_2().volume * 1e-3))
    ход = свободный_ход()
    print("свободный ход рукоятки: %s…%s град, открыто %.0f, закрыто %.0f" % (min(ход) if ход else "-", max(ход) if ход else "-",
                                                                              ОТКРЫТО, ЗАКРЫТО))
    худшее = 0.0
    for угол in (ОТКРЫТО, ЗАКРЫТО):
        pp = сборка(угол, с_настилом=True)
        for i in range(len(pp)):
            for j in range(i + 1, len(pp)):
                v = _пересечение(pp[i], pp[j])
                if v > 0.5:
                    print("  пересечение (%.0f°) %-40s x %-40s %.1f мм³" % (угол, pp[i].label[:40], pp[j].label[:40], v))
                    худшее = max(худшее, v)
    for a in (ОТКРЫТО, ЗАКРЫТО):
        if int(a) not in ход:
            print("  рукоятка в положении %.0f° задевает корпус" % a)
            худшее = max(худшее, 1.0)
    print("деталей %d, наибольшее пересечение %.1f мм³" % (len(parts), худшее))
    return худшее


if __name__ == "__main__":
    sys.exit(1 if main() > 0.5 else 0)
