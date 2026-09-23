# -*- coding: utf-8 -*-
"""VG-2026.46.00 cast twistlock foundation for the sun-deck modules - 3D model (build123d).

    python CAD/src/twistlock.py

Every dimension comes from lib.gorizont_twistlock - the same numbers drive the
drawings, the strength check, the casting technology and the Blender scene.
Units are millimetres; node frame: X along the ship, Y across, Z up from the
underside of the cast body. Outputs:

    CAD/STEP/VG-2026_46_00_twistlock.step      assembly with labelled parts
    CAD/STEP/VG-2026_46_01_body.step           cast body, machined
    CAD/STEP/VG-2026_46_01_casting.step        casting with allowances and riser (for the pattern)
    CAD/STEP/VG-2026_46_01_core.step           cavity core with the window print
    CAD/STL/...                                 the same as STL
    CAD/GLB/VG-2026_46_00_twistlock_open.glb    assembly for Blender, parts as named nodes, lever open
"""
import math
import os
import sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import build123d as bd
from lib import gorizont_twistlock as T

K, Z, P, B, O = T.КОРПУС, T.ЗАМОК, T.ПРИПУСКИ, T.БОЛТ, T.ОПОРА
C = (bd.Align.CENTER, bd.Align.CENTER, bd.Align.MIN)          # centred in plan, base on z
Z_HEAD = K["H"] + T.ФИТИНГ_ДНО + T.ЗАЗОР_ГОЛОВКИ               # underside of the cone head
Z_CBORE = K["H"] + K["упор"][2] - K["d_выточка"][1]            # floor of the counterbore in the lug
Z_CAV = K["H"] - K["t_верх"]                                   # underside of the top wall
Z_SQ_TOP = Z_CAV - Z["l_резьбы"]                               # thread ends, square begins
Z_SQ_BOT = Z_SQ_TOP - Z["l_квадрата"]


def cyl(d, z0, z1, x=0.0, y=0.0):
    return bd.Pos(x, y, z0) * bd.Cylinder(d / 2.0, z1 - z0, align=C)


def prism(face, z0, h):
    return bd.extrude(bd.Pos(0, 0, z0) * face, h)


def wedge(a0, a1, r, z0, z1, n=24):
    pts = [(0.0, 0.0)] + [(r * math.cos(math.radians(a0 + (a1 - a0) * i / n)),
                           r * math.sin(math.radians(a0 + (a1 - a0) * i / n))) for i in range(n + 1)]
    return prism(bd.Polygon(*pts, align=None), z0, z1 - z0)


def rib(sign, z_top):
    y0, y1 = sign * (K["D_н"] / 2.0 - 5.0), sign * (K["L_y"] / 2.0 - 5.0)
    face = bd.Plane.YZ.offset(-K["ребро"][0] / 2.0) * bd.Polygon((y0, K["t_фл"] - 1.0), (y0, z_top), (y1, K["t_фл"] - 1.0), align=None)
    return bd.extrude(face, K["ребро"][0])


def bolt_xy():
    return [(sx * K["болт_x"], sy * K["болт_y"]) for sx in (-1, 1) for sy in (-1, 1)]


def plunger_xy():
    r = K["фиксатор_r"]
    return [(r * math.cos(math.radians(a)), r * math.sin(math.radians(a))) for a in K["фиксатор_углы"]]


def body_blank(bottom=0.0, top=0.0):
    """Outer shape of the body: flange, cup, ribs, bosses; bottom/top grow the machined faces."""
    fl = prism(bd.RectangleRounded(K["L_x"], K["L_y"], K["R_фл"]), -bottom, K["t_фл"] + bottom)
    cup = cyl(K["D_н"], -bottom, K["H"] + top)
    s = fl + cup + rib(1, K["t_фл"] + K["ребро"][1]) + rib(-1, K["t_фл"] + K["ребро"][1])
    for x, y in plunger_xy():
        s += cyl(K["прилив"][0], K["t_фл"] - 1.0, K["t_фл"] + K["прилив"][1], x, y)
    s -= cyl(K["D_в"], -bottom - 1.0, Z_CAV)
    z0, z1, span = K["окно"]
    s -= wedge(180.0 - span / 2.0, 180.0 + span / 2.0, K["D_н"] / 2.0 + 5.0, z0, z1)
    return s


def body():
    """VG-2026.46.01 cast body after machining."""
    s = body_blank()
    Lu, Wu, hu = K["упор"]
    s += prism(bd.SlotOverall(Lu, Wu), K["H"] - 1.0, hu + 1.0)
    s -= cyl(K["d_вал"], Z_CAV - 1.0, K["H"] + hu + 1.0)
    s -= cyl(K["d_выточка"][0], Z_CBORE, K["H"] + hu + 1.0)
    for x, y in bolt_xy():
        s -= cyl(K["d_отв"], -1.0, K["t_фл"] + 1.0, x, y)
        s -= cyl(K["цековка"][0], K["t_фл"] - K["цековка"][1], K["t_фл"] + 30.0, x, y)
    for x, y in plunger_xy():
        s -= cyl(K["d_фикс"], K["t_фл"] - 10.0, K["t_фл"] + K["прилив"][1] + 1.0, x, y)
    # grease: M10x1 tap drill 9 into the cup wall on +X, channel 5 into the shaft bore
    s -= bd.Pos(K["D_н"] / 2.0 - 12.0, 0, K["маслёнка_z"]) * bd.Rot(0, 90, 0) * bd.Cylinder(4.5, 30.0)
    s -= bd.Pos(K["D_в"] / 2.0 / 2.0 + 10.0, 0, K["маслёнка_z"]) * bd.Rot(0, 90, 0) * bd.Cylinder(2.5, K["D_н"] / 2.0)
    w, d = K["дренаж"]
    s -= bd.Pos(K["D_в"] / 2.0 + (K["L_x"] / 2.0 - K["D_в"] / 2.0) / 2.0, 0, -1.0) * bd.Box(K["L_x"] / 2.0 - K["D_в"] / 2.0 + 20.0, w, d + 1.0, align=C)
    s.label = "pos.1 body VG-2026.46.01 (cast 20GL)"
    return s


def casting():
    """Casting: allowances on the machined faces, holes not cast, riser as an obround on the pad."""
    s = body_blank(bottom=P["подошва"], top=P["площадка"])
    o = T.отливка()
    s += prism(bd.SlotOverall(o["прибыль_D"], o["прибыль_W"]), K["H"] + P["площадка"] - 1.0, o["прибыль_H"] + 1.0)
    s.label = "VG-2026.46.01 casting with riser"
    return s


def core():
    """Cavity core: the cup cavity, the tongue in the window and the print leg outside the cup.

    The leg runs from the window up to the top of the pattern: a print only as tall as the window
    would be an undercut, and the pattern could not be drawn out of the cope."""
    z_bot = -P["подошва"] - T.ЗНАК_НИЗ
    c = cyl(K["D_в"] - 0.5, z_bot, Z_CAV)
    z0, z1, span = K["окно"]
    tongue = wedge(180.0 - span / 2.0, 180.0 + span / 2.0, K["D_н"] / 2.0 + 0.5, z0, z1)
    leg = wedge(180.0 - span / 2.0, 180.0 + span / 2.0, K["D_н"] / 2.0 + T.ЗНАК_ОКНА, z0, K["H"] + P["площадка"]) - cyl(K["D_н"], z0 - 1.0, K["H"] + P["площадка"] + 1.0)
    c += (tongue - cyl(K["D_в"] - 10.0, z0 - 1.0, z1 + 1.0)) + leg
    c.label = "core VG-2026.46.01-C"
    return c


def lock(angle=135.0):
    """VG-2026.46.02 cone with shaft (40Kh forging); angle is the lever angle: 135 open (cone along X), 225 closed."""
    L, W, hs, hc, (Lt, Wt) = Z["голова"]
    head = prism(bd.SlotOverall(L, W), Z_HEAD, hs)
    top = bd.loft([bd.Pos(0, 0, Z_HEAD + hs) * bd.SlotOverall(L, W), bd.Pos(0, 0, Z_HEAD + hs + hc) * bd.SlotOverall(Lt, Wt)])
    s = head + top
    s += cyl(Z["шейка"][0], Z_CBORE, Z_HEAD + 0.5)
    s += cyl(Z["вал"], Z_CAV - 0.5, Z_CBORE + 0.5)
    s += cyl(33.0, Z_SQ_TOP, Z_CAV)
    s += bd.Pos(0, 0, Z_SQ_BOT) * bd.Box(Z["квадрат"], Z["квадрат"], Z["l_квадрата"], align=C)
    s -= cyl(6.8, Z_SQ_BOT - 1.0, Z_SQ_BOT + 16.0)          # M8 tapped hole for the end screw
    s = bd.Rot(0, 0, angle - 135.0) * s
    s.label = "pos.2 cone with shaft VG-2026.46.02 (40Kh)"
    return s


def lever(angle):
    """VG-2026.46.03 lever on the square, arm out of the window; angle 135 = open, 225 = closed."""
    R = T.РЫЧАГ
    hub = cyl(R["ступица"][0], Z_SQ_BOT, Z_SQ_BOT + R["ступица"][1])
    hub -= bd.Pos(0, 0, Z_SQ_BOT - 1.0) * bd.Box(Z["квадрат"] + 0.2, Z["квадрат"] + 0.2, R["ступица"][1] + 2.0, align=C)
    b, t = R["плечо"]
    L = R["r_конца"] - R["ступица"][0] / 2.0 + 2.0
    arm = bd.Pos(R["ступица"][0] / 2.0 - 2.0 + L / 2.0, 0, R["z_оси"] - t / 2.0) * bd.Box(L, b, t, align=C)
    arm += cyl(b, R["z_оси"] - t / 2.0, R["z_оси"] + t / 2.0, R["r_конца"], 0)
    arm -= cyl(14.0, R["z_оси"] - t / 2.0 - 1.0, R["z_оси"] + t / 2.0 + 1.0, K["фиксатор_r"], 0)   # M16x1.5 for the plunger
    knob = cyl(24.0, R["z_оси"] + t / 2.0 - 0.5, R["z_оси"] + t / 2.0 + 50.0, R["r_конца"] - 6.0, 0)
    # the square hole stays aligned with the shaft square: the arm sits at 135 deg in the shaft frame,
    # and lever and shaft turn together by (angle - 135)
    s = bd.Rot(0, 0, angle - 135.0) * (hub + bd.Rot(0, 0, 135.0) * (arm + knob))
    s.label = "pos.3 lever VG-2026.46.03 (09G2S)"
    return s


def plunger(angle):
    R = T.РЫЧАГ
    zt = R["z_оси"] + R["плечо"][1] / 2.0
    p = cyl(24.0, zt, zt + 12.0, K["фиксатор_r"], 0) + cyl(16.0, zt + 12.0, zt + 30.0, K["фиксатор_r"], 0)
    p += cyl(10.0, K["t_фл"] + K["прилив"][1] - 8.0, zt, K["фиксатор_r"], 0)
    p += bd.Pos(K["фиксатор_r"], 0, zt + 34.0) * bd.Rot(90, 0, 0) * bd.Torus(10.0, 2.0)
    s = bd.Rot(0, 0, angle) * p
    s.label = "pos.16 spring plunger"
    return s


def greaser():
    """pos.15 grease nipple M10x1 GOST 19853-74, straight: thread in the tap hole of the cup wall on +X
    (drill 9 = thread shown at its tap diameter), hex 11 on the wall, neck and ball head."""
    z, r = K["маслёнка_z"], K["D_н"] / 2.0
    ax = bd.Rot(0, 90, 0)                                   # local +Z -> +X
    s = bd.Pos(r - 8.0, 0, z) * ax * bd.Cylinder(4.5, 8.0, align=C)
    s += bd.Pos(r, 0, z) * ax * bd.extrude(bd.RegularPolygon(11.0 / math.sqrt(3.0), 6), 7.0)
    s += bd.Pos(r + 7.0, 0, z) * ax * bd.Cylinder(3.0, 4.0, align=C)
    s += bd.Pos(r + 13.0, 0, z) * bd.Sphere(3.5)
    s.label = "pos.15 grease nipple M10x1"
    return s


def small_parts():
    """Washers, round nut, end screw, bolts, nuts, isolation, doubler plate."""
    parts = []
    def add(shape, label):
        shape.label = label
        parts.append(shape)
    add(cyl(58.0, Z_CAV - 2.0, Z_CAV) - cyl(36.5, Z_CAV - 3.0, Z_CAV + 1.0), "pos.4 thrust washer BrAZh9-4")
    add(cyl(56.0, Z_CAV - 3.5, Z_CAV - 2.0) - cyl(33.5, Z_CAV - 4.0, Z_CAV - 1.0), "pos.13 tab washer 33")
    nut = cyl(52.0, Z_CAV - 13.5, Z_CAV - 3.5) - cyl(33.0, Z_CAV - 14.0, Z_CAV - 3.0)
    for a in range(0, 360, 90):
        nut -= bd.Rot(0, 0, a) * bd.Pos(26.0, 0, Z_CAV - 8.5) * bd.Box(10.0, 8.0, 12.0)
    add(nut, "pos.12 slotted round nut M33x1.5")
    add(cyl(40.0, Z_SQ_BOT - 4.0, Z_SQ_BOT) - cyl(8.5, Z_SQ_BOT - 5.0, Z_SQ_BOT + 1.0), "pos.14 end washer 40x4")
    add(cyl(13.0, Z_SQ_BOT - 12.0, Z_SQ_BOT - 4.0), "pos.14 screw M8x16")
    tg, (dl, dw, dt), td = O["прокладка"], O["лист"], O["настил"]
    gasket = prism(bd.RectangleRounded(K["L_x"], K["L_y"], K["R_фл"]), -tg, tg)
    for x, y in bolt_xy():
        gasket -= cyl(K["d_отв"], -tg - 1.0, 1.0, x, y)
    gasket -= cyl(K["D_в"], -tg - 1.0, 1.0)
    add(gasket, "pos.5 insulating gasket STEF")
    plate = prism(bd.Rectangle(dl, dw), -tg - dt, dt)
    for x, y in bolt_xy():
        plate -= cyl(B["втулка"][0], -tg - dt - 1.0, -tg + 1.0, x, y)
    add(plate, "pos.8 doubler plate AMg5")
    z_head = K["t_фл"] - K["цековка"][1]
    z_under = -tg - dt - td
    for i, (x, y) in enumerate(bolt_xy()):
        add(cyl(B["втулка"][0] - 0.2, z_under, -tg, x, y) - cyl(B["втулка"][1], z_under - 1.0, -tg + 1.0, x, y), "pos.6 insulating bush %d" % (i + 1))
        dw_, di_, tw_ = B["шайба_изол"]
        add(cyl(dw_, z_under - tw_, z_under, x, y) - cyl(di_, z_under - tw_ - 1.0, z_under + 1.0, x, y), "pos.7 insulating washer %d" % (i + 1))
        add(cyl(44.0, z_under - tw_ - 4.0, z_under - tw_, x, y) - cyl(25.0, z_under - tw_ - 5.0, z_under - tw_ + 1.0, x, y), "pos.11 washer under nut %d" % (i + 1))
        add(cyl(44.0, z_head, z_head + 4.0, x, y) - cyl(25.0, z_head - 1.0, z_head + 5.0, x, y), "pos.11 washer under head %d" % (i + 1))
        head = bd.Pos(x, y, z_head + 4.0) * bd.extrude(bd.RegularPolygon(36.0 / math.sqrt(3.0), 6), 15.0)
        z_end = z_under - tw_ - 4.0 - 24.0 - 3.0
        add(head + cyl(B["d"], z_end, z_head + 4.0, x, y), "pos.9 bolt M24x%d A4-80 %d" % (B["длина"], i + 1))
        add(bd.Pos(x, y, z_under - tw_ - 4.0 - 24.0) * bd.extrude(bd.RegularPolygon(36.0 / math.sqrt(3.0), 6), 24.0)
            - cyl(B["d"] + 0.4, z_end - 1.0, z_under, x, y), "pos.10 nut M24 A4-80 %d" % (i + 1))
    return parts


def assembly(angle=225.0):
    parts = [body(), lock(angle), lever(angle), plunger(angle), greaser()] + small_parts()
    return bd.Compound(label="VG-2026.46.00 cast twistlock foundation", children=parts), parts


def main():
    step_dir = os.path.join(ROOT, "CAD", "STEP")
    stl_dir = os.path.join(ROOT, "CAD", "STL")
    os.makedirs(step_dir, exist_ok=True)
    os.makedirs(stl_dir, exist_ok=True)
    asm, parts = assembly()
    b, c, k = body(), casting(), core()
    out = [(asm, "VG-2026_46_00_twistlock"), (b, "VG-2026_46_01_body"), (c, "VG-2026_46_01_casting"), (k, "VG-2026_46_01_core"),
           (lock(135.0), "VG-2026_46_02_lock"), (lever(135.0), "VG-2026_46_03_lever")]
    for shape, name in out:
        bd.export_step(shape, os.path.join(step_dir, name + ".step"))
        bd.export_stl(shape, os.path.join(stl_dir, name + ".stl"), tolerance=0.05, angular_tolerance=0.2)
    # GLB for Blender: every part a separate named node; "open" = lever at 135 deg, the reference pose
    glb_dir = os.path.join(ROOT, "CAD", "GLB")
    os.makedirs(glb_dir, exist_ok=True)
    asm_open, _ = assembly(135.0)
    for shape, name in ((asm_open, "VG-2026_46_00_twistlock_open"), (c, "VG-2026_46_01_casting"), (k, "VG-2026_46_01_core")):
        bd.export_gltf(shape, os.path.join(glb_dir, name + ".glb"), binary=True, linear_deflection=0.05, angular_deflection=0.2)
    rho = T.МАТЕРИАЛЫ["20ГЛ"]["ρ"] * 1e-9
    m = T.массы()
    print("body  : volume %.0f mm3, mass %.2f kg (library %.2f, diff %+.1f %%)" % (b.volume, b.volume * rho, m["корпус"], 100.0 * (b.volume * rho / m["корпус"] - 1.0)))
    print("cast  : volume %.0f mm3, mass %.2f kg incl. riser (library casting %.2f + riser %.2f)" % (
        c.volume, c.volume * rho, m["отливка"], T.отливка()["масса_прибыли"]))
    print("lock  : mass %.2f kg (library %.2f)" % (lock().volume * 7.82e-6, m["замок"]))
    print("core  : volume %.2f dm3" % (k.volume * 1e-6))
    # interference check between parts of the assembly (touching faces are allowed)
    worst = 0.0
    for i in range(len(parts)):
        for j in range(i + 1, len(parts)):
            bi, bj = parts[i].bounding_box(), parts[j].bounding_box()
            if (bi.min.X > bj.max.X or bj.min.X > bi.max.X or bi.min.Y > bj.max.Y or bj.min.Y > bi.max.Y
                    or bi.min.Z > bj.max.Z or bj.min.Z > bi.max.Z):
                continue
            v = (parts[i] & parts[j]).volume
            if v > 1.0:
                print("  overlap %-40s x %-40s %.1f mm3" % (parts[i].label[:40], parts[j].label[:40], v))
                worst = max(worst, v)
    print("parts %d, worst overlap %.1f mm3" % (len(parts), worst))
    for name in [n for _, n in out]:
        print("  ", os.path.join("CAD", "STEP", name + ".step"))
    return worst


if __name__ == "__main__":
    sys.exit(1 if main() > 1.0 else 0)
