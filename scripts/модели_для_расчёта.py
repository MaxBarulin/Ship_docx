# -*- coding: utf-8 -*-
"""Расчётные модели корпуса для CAD и МКЭ (ANSYS, SpaceClaim, Rhino).

Строятся по той же плазовой таблице, что и все расчёты проекта, поэтому
геометрия в ANSYS и геометрия в рендере - одна и та же поверхность.

    python scripts/модели_для_расчёта.py

Что получается в CAD/:
  ВГ-2026_корпус_оболочка.stl / .obj   - корпус до палубы, замкнутая оболочка
  ВГ-2026_корпус_с_ярусами.stl / .obj  - то же плюс надстройка и рубка
  ВГ-2026_обводы_3D.dxf                - шпангоуты, ватерлинии и батоксы
                                         3D-полилиниями под лофт в CAD
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import ezdxf
from lib import gorizont as G, gorizont_hydro as H, gorizont_mesh as M

OUT = os.path.join(ROOT, "CAD")
os.makedirs(OUT, exist_ok=True)
K = 1000.0                     # метры -> миллиметры


def scaled(verts):
    return [(v[0] * K, v[1] * K, v[2] * K) for v in verts]


def dump(name, verts, faces, title):
    verts, faces = M.weld(verts, faces)
    chk = M.check(verts, faces)
    vs = scaled(verts)
    n1 = M.write_stl(os.path.join(OUT, name + ".stl"), vs, faces, title)
    n2 = M.write_obj(os.path.join(OUT, name + ".obj"), vs, faces, title)
    print("%-34s вершин %6d  граней %6d  треугольников %6d  замкнута - %s"
          % (name, chk["verts"], chk["faces"], n1, "да" if chk["closed"] else "НЕТ"))
    return chk


def lines_dxf():
    doc = ezdxf.new("R2013", setup=True)
    doc.units = ezdxf.units.MM
    doc.header["$INSUNITS"] = 4
    for nm, col in (("ШПАНГОУТЫ", 5), ("ВАТЕРЛИНИИ", 3), ("БАТОКСЫ", 1),
                    ("ПАЛУБА", 7), ("КИЛЬ", 2)):
        if nm not in doc.layers:
            doc.layers.add(name=nm, color=col)
    msp = doc.modelspace()
    # шпангоуты - по узлам плазовой таблицы
    for n, x, zk, bk, zb, bb, ys in G.OFFSETS:
        zs = [zk + (zb - zk) * (k / 60) ** 1.35 for k in range(61)]
        pts = [(x * K, bk * K, zk * K)]
        pts += [(x * K, H.half_breadth(x, z) * K, z * K) for z in zs]
        for s in (1, -1):
            msp.add_polyline3d([(p[0], s * p[1], p[2]) for p in pts],
                               dxfattribs={"layer": "ШПАНГОУТЫ"})
    xs = [i * 0.5 for i in range(int(G.LOA * 2) + 1)]
    for z in G.WATERLINES:
        pts = [(x * K, H.half_breadth(x, z) * K, z * K) for x in xs
               if H.half_breadth(x, z) > 0.002]
        if len(pts) > 2:
            for s in (1, -1):
                msp.add_polyline3d([(p[0], s * p[1], p[2]) for p in pts],
                                   dxfattribs={"layer": "ВАТЕРЛИНИИ"})
    for y in (0.5, 1.5, 2.5, 3.5, 4.5, 5.5, 6.5, 7.5, 8.0):
        pts = []
        for x in xs:
            zk, bk, zb, bb, _ = H._column(x)
            if H.half_breadth(x, zb) < y:
                continue
            lo, hi = zk, zb
            for _ in range(40):
                m = 0.5 * (lo + hi)
                if H.half_breadth(x, m) < y:
                    lo = m
                else:
                    hi = m
            pts.append((x * K, y * K, 0.5 * (lo + hi) * K))
        if len(pts) > 2:
            for s in (1, -1):
                msp.add_polyline3d([(p[0], s * p[1], p[2]) for p in pts],
                                   dxfattribs={"layer": "БАТОКСЫ"})
    for s in (1, -1):
        msp.add_polyline3d([(x * K, s * H._column(x)[3] * K, H._column(x)[2] * K)
                            for x in xs], dxfattribs={"layer": "ПАЛУБА"})
    msp.add_polyline3d([(x * K, 0.0, H._column(x)[0] * K) for x in xs],
                       dxfattribs={"layer": "КИЛЬ"})
    p = os.path.join(OUT, "ВГ-2026_обводы_3D.dxf")
    doc.saveas(p)
    return p


def main():
    v, f = M.build(tiers=False)
    dump("ВГ-2026_корпус_оболочка", v, f, "korpus")
    for nm, fn, title in (("ВГ-2026_надстройка", M.super_solid, "nadstroika"),
                          ("ВГ-2026_рубка", M.wheel_solid, "rubka")):
        vv, ff = fn()
        dump(nm, vv, ff, title)
    print(os.path.basename(lines_dxf()))
    print("\nМодель «с ярусами» собирается объединением трёх тел:")
    print("  python -  (в Blender)  scripts/blender_расчётные_модели.py")


if __name__ == "__main__":
    main()
