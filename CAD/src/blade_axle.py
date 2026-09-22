# -*- coding: utf-8 -*-
"""VG-2026.31.00 blade axle with crank (paddle wheel feathering blade) - STEP model.

    python CAD/src/blade_axle.py

Dimensions come from lib.gorizont_node - the same library that drives the
assembly drawing (CAD/VG-2026_31_00_SB*.dxf), the specification and the
strength calculation, so the drawing and the 3D model cannot diverge.
Model axis is Z, units are millimetres. This file is ASCII-only on purpose:
cadgen reads the script with the locale encoding and chokes on Cyrillic.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from cadgen import build123d as bd
from cadgen import step
from lib import gorizont_node as N


def _c():
    return (bd.Align.CENTER, bd.Align.CENTER, bd.Align.CENTER)


def _cyl(r, z0, z1, x=0.0, y=0.0):
    """Cylinder along Z from z0 to z1."""
    h = z1 - z0
    return bd.Pos(x, y, z0 + h / 2.0) * bd.Cylinder(r, h, align=_c())


def _tube(r_out, r_in, z0, z1):
    return _cyl(r_out, z0, z1) - _cyl(r_in, z0 - 1.0, z1 + 1.0)


def _axle():
    jl = N.L_JOURNAL
    zj = N.DISC_Y - N.DISC_T / 2.0 - 5.0          # journal starts just before the rim disc
    body = _cyl(N.D_AXIS / 2.0, -zj, zj)
    j1 = _cyl(N.D_JOURNAL / 2.0, zj - 1.0, zj + jl)
    j2 = _cyl(N.D_JOURNAL / 2.0, -zj - jl, -zj + 1.0)
    tail = _cyl(40.0, zj + jl - 1.0, zj + jl + 45.0)        # M80 threaded tail
    axle = body + j1 + j2 + tail
    # keyways: crank and each hub
    b, h, l = N.KEY
    for zc in [N.CRANK_Y] + [s * y for y in N.HUB_Y for s in (1, -1)]:
        axle = axle - (bd.Pos(N.D_AXIS / 2.0 - h / 2.0 + 0.5, 0, zc) * bd.Box(h, b, l, align=_c()))
    axle.label = "pos.1 blade axle"
    return axle


def _hub(zc):
    """Split clamp hub with a lug flange for the blade panels."""
    sleeve = _tube(N.HUB_D / 2.0, N.D_AXIS / 2.0 + 0.2, zc - N.HUB_L / 2.0, zc + N.HUB_L / 2.0)
    flange = bd.Pos(50.0 + N.LUG_T / 2.0, 0, zc) * bd.Box(N.LUG_T, N.BLADE_H - 40.0, N.HUB_L, align=_c())
    flange = flange - _cyl(N.HUB_D / 2.0 - 0.1, zc - N.HUB_L / 2.0 - 1.0, zc + N.HUB_L / 2.0 + 1.0)
    cut = bd.Pos(0, 0, zc) * bd.Box(N.HUB_D + 2.0, 4.0, N.HUB_L + 2.0, align=_c())
    hub = (sleeve + flange) - cut
    for sx in (1, -1):
        for sz in (1, -1):
            hub = hub + (bd.Pos(sx * (N.HUB_D / 2.0 + 12.0), 0, zc + sz * 45.0) * bd.Box(40.0, 60.0, 30.0, align=_c()))
            hub = hub - _cyl(8.5, zc + sz * 45.0 - 16.0, zc + sz * 45.0 + 16.0, x=sx * (N.HUB_D / 2.0 + 12.0))
    hub.label = "pos.2 blade hub"
    return hub


def _crank():
    zc = N.CRANK_Y
    hub = _tube(N.CRANK_HUB_D / 2.0, N.D_AXIS / 2.0 + 0.2, zc - 40.0, zc + 40.0)
    arm = bd.Pos(0, N.CRANK_L / 2.0, zc) * bd.Box(N.CRANK_W, N.CRANK_L, N.CRANK_T, align=_c())
    eye = _cyl(N.CRANK_W / 2.0, zc - N.CRANK_T / 2.0, zc + N.CRANK_T / 2.0, y=N.CRANK_L)
    crank = (hub + arm + eye) - _cyl(N.PIN_D / 2.0 + 0.2, zc - 60.0, zc + 60.0, y=N.CRANK_L)
    b, h, l = N.KEY
    crank = crank - (bd.Pos(N.D_AXIS / 2.0 + h / 2.0 - 0.5, 0, zc) * bd.Box(h, b, 90.0, align=_c()))
    crank.label = "pos.3 crank"
    return crank


def _pin():
    zc = N.CRANK_Y
    pin = _cyl(N.PIN_D / 2.0, zc - N.PIN_L + N.CRANK_T / 2.0, zc + N.CRANK_T / 2.0 + 10.0, y=N.CRANK_L)
    head = _cyl(N.PIN_D / 2.0 + 12.0, zc + N.CRANK_T / 2.0 + 10.0, zc + N.CRANK_T / 2.0 + 22.0, y=N.CRANK_L)
    p = pin + head
    p.label = "pos.4 crank pin"
    return p


def _bushing(sign):
    zc = sign * N.DISC_Y
    t = _tube(N.BUSH_D_OUT / 2.0, N.D_JOURNAL / 2.0 + 0.1, zc - N.BUSH_L / 2.0, zc + N.BUSH_L / 2.0)
    t.label = "pos.5 bearing bushing"
    return t


def _key(zc):
    b, h, l = N.KEY
    k = bd.Pos(N.D_AXIS / 2.0, 0, zc) * bd.Box(h, b, l, align=_c())
    k.label = "key %dx%dx%d GOST 23360" % (b, h, l)
    return k


def _nut():
    zj = N.DISC_Y - N.DISC_T / 2.0 - 5.0 + N.L_JOURNAL
    nut = bd.Pos(0, 0, zj + 22.0) * bd.extrude(bd.RegularPolygon(120.0 / 2.0 / 0.866, 6), 40.0 / 2.0, both=True)
    nut = nut - _cyl(40.0 + 0.2, zj - 1.0, zj + 50.0)
    nut.label = "nut M80x3 GOST 5915"
    return nut


@step(out="../STEP/VG-2026_31_00_blade_axle.step")
def blade_axle():
    parts = [_axle()]
    for y in N.HUB_Y:
        parts.append(_hub(y)); parts.append(_hub(-y))
    parts += [_crank(), _pin(), _bushing(1), _bushing(-1), _key(N.CRANK_Y), _nut()]
    return bd.Compound(label="VG-2026.31.00 blade axle with crank", children=parts)


def _fallback_export():
    """cadgen's STEP writer needs a matching OCP build; when it is missing,
    write the STEP straight from build123d (same geometry, plain export)."""
    import build123d as b3d
    out = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "STEP", "VG-2026_31_00_blade_axle.step")
    out = os.path.abspath(out)
    os.makedirs(os.path.dirname(out), exist_ok=True)
    # rebuild the geometry with plain build123d so nothing depends on cadgen
    global bd
    bd = b3d
    shape = blade_axle.__wrapped__() if hasattr(blade_axle, "__wrapped__") else None
    if shape is None:
        parts = [_axle()]
        for y in N.HUB_Y:
            parts.append(_hub(y)); parts.append(_hub(-y))
        parts += [_crank(), _pin(), _bushing(1), _bushing(-1), _key(N.CRANK_Y), _nut()]
        shape = b3d.Compound(label="VG-2026.31.00 blade axle with crank", children=parts)
    b3d.export_step(shape, out)
    vol = sum(p.volume for p in shape.children) if shape.children else shape.volume
    print("STEP:", out, "volume %.0f mm3, mass ~%.1f kg (steel)" % (vol, vol * 7.85e-6))
    stl = os.path.join(os.path.dirname(out), "..", "STL", "VG-2026_31_00_blade_axle.stl")
    b3d.export_stl(shape, os.path.abspath(stl))
    print("STL:", os.path.abspath(stl))
    return out


if __name__ == "__main__":
    # cadgen's own STEP writer needs an OCP build that matches its pin; on
    # this machine it does not, so the model is exported straight from
    # build123d. `python blade_axle.py --cadgen` tries the cadgen path.
    if "--cadgen" in sys.argv:
        blade_axle()
    else:
        _fallback_export()
