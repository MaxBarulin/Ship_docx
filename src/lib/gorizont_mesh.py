# -*- coding: utf-8 -*-
"""Геометрия корпуса в виде замкнутых сеток — для расчётов в CAD и МКЭ.

Поверхность строится по той же плазовой таблице, что и все расчёты
(`gorizont.OFFSETS`), поэтому модель для ANSYS и модель для рендера — это
буквально одна и та же поверхность, а не две похожие.

Сетка замкнутая и манифолдная: каждое ребро принадлежит ровно двум граням.
"""
import math
from . import gorizont as G
from . import gorizont_hydro as H

Z_SUPER_TOP = 12.60          # крыша четвёртого яруса
Z_WHEEL_TOP = 15.40          # крыша рулевой рубки
WHEEL_X0, WHEEL_X1 = 115.40, 131.00
WHEEL_HALF = 5.50


def default_xs(step_end=0.5, step_mid=1.0):
    """Сетка сечений по длине: гуще в оконечностях."""
    xs, x = [], 0.0
    while x <= G.LOA + 1e-9:
        xs.append(round(x, 3))
        x += step_end if (x < 22.0 or x > 108.0) else step_mid
    for r in G.OFFSETS:
        xs.append(round(r[1], 3))
    for xb in (G.SUPER_START, G.SUPER_END, WHEEL_X0, WHEEL_X1):
        xs += [round(xb - 0.02, 3), round(xb + 0.02, 3)]
    return sorted(set(v for v in xs if 0.0 <= v <= G.LOA))


def _deck(x):
    """Параметры сечения с плоской главной палубой.

    Подъём борта выше D — это фальшборт, а не палуба (см.
    scripts/blender_фальшборт.py), поэтому расчётная оболочка обрывается
    на высоте борта D = G.DEPTH м по всей длине.
    """
    zk, bk, zb, bb, phi = H._column(x)
    zd = min(zb, G.DEPTH)
    return zk, bk, zd, H.half_breadth(x, zd)


def _shell(x, nu):
    """Точки обвода от киля до палубы: [(y, z), ...], nu + 1 штук."""
    zk, bk, zb, bb = _deck(x)
    pts = []
    for k in range(nu + 1):
        u = (k / nu) ** 1.5
        z = zk + (zb - zk) * u
        pts.append((bk if k == 0 else H.half_breadth(x, z), z))
    pts[-1] = (bb, zb)
    return pts


def _wheel_half(x):
    return WHEEL_HALF if WHEEL_X0 <= x <= WHEEL_X1 else 0.0


def ring(x, nu=24, nd=10, tiers=False, nw=6):
    """Замкнутый контур сечения (по часовой от киля через правый борт)."""
    zk, bk, zb, bb = _deck(x)
    stb = _shell(x, nu)
    pts = [(0.0, zk)] + stb
    if not tiers:
        pts += [(bb * (nd - j) / nd, zb) for j in range(1, nd)]
        pts.append((0.0, zb))
        pts += [(-bb * j / nd, zb) for j in range(1, nd)]
    else:
        bs = H.super_half_breadth(x)
        bw = _wheel_half(x)
        pts += [(bb + (bs - bb) * j / nd, zb) for j in range(1, nd + 1)]
        pts += [(bs, zb + (Z_SUPER_TOP - zb) * j / nw) for j in range(1, nw + 1)]
        pts += [(bs + (bw - bs) * j / nd, Z_SUPER_TOP) for j in range(1, nd + 1)]
        pts += [(bw, Z_SUPER_TOP + (Z_WHEEL_TOP - Z_SUPER_TOP) * j / nw)
                for j in range(1, nw + 1)]
        pts.append((0.0, Z_WHEEL_TOP))
        mid = pts[len(stb) + 1:-1]
        pts += [(-y, z) for (y, z) in reversed(mid)]
    if not tiers:
        pts += [(-y, z) for (y, z) in reversed(stb)]
    else:
        pts += [(-y, z) for (y, z) in reversed(stb)]
    return pts


def build(xs=None, nu=24, nd=10, tiers=False, nw=6):
    """Замкнутая сетка: (вершины [(x,y,z)], грани [(i0,i1,i2,i3)])."""
    xs = xs or default_xs()
    rings, verts = [], []
    for x in xs:
        idx = []
        for (y, z) in ring(x, nu, nd, tiers, nw):
            idx.append(len(verts))
            verts.append((x, y, z))
        rings.append(idx)
    n = len(rings[0])
    faces = []
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((a[k], a[k2], b[k2], b[k]))
    faces.append(tuple(reversed(rings[0])))
    faces.append(tuple(rings[-1]))
    return verts, faces


def box_solid(x0, x1, half_fn, z_bot_fn, z_top, n_x=90, n_z=6, n_y=8):
    """Замкнутая призма: план по half_fn(x), низ по z_bot_fn(x), верх z_top."""
    xs = [x0 + (x1 - x0) * i / n_x for i in range(n_x + 1)]
    verts, rings = [], []
    for x in xs:
        b = max(half_fn(x), 0.05)
        zb0 = z_bot_fn(x)
        pts = [(0.0, zb0)]
        pts += [(b * j / n_y, zb0) for j in range(1, n_y + 1)]
        pts += [(b, zb0 + (z_top - zb0) * j / n_z) for j in range(1, n_z + 1)]
        pts += [(b * (n_y - j) / n_y, z_top) for j in range(1, n_y + 1)]
        pts.append((0.0, z_top))
        mid = pts[1:-1]
        pts += [(-y, z) for (y, z) in reversed(mid)]
        idx = []
        for (y, z) in pts:
            idx.append(len(verts)); verts.append((x, y, z))
        rings.append(idx)
    n = len(rings[0])
    faces = []
    for i in range(len(rings) - 1):
        a, b = rings[i], rings[i + 1]
        for k in range(n):
            k2 = (k + 1) % n
            faces.append((a[k], a[k2], b[k2], b[k]))
    faces.append(tuple(reversed(rings[0])))
    faces.append(tuple(rings[-1]))
    return verts, faces


def super_solid():
    """Надстройка от палубы до крыши четвёртого яруса, замкнутая."""
    return box_solid(G.SUPER_START + 0.05, G.SUPER_END - 0.05,
                     H.super_half_breadth,
                     lambda x: H._column(x)[2] - 0.05, Z_SUPER_TOP, n_x=140)


def wheel_solid():
    """Рулевая рубка, замкнутая."""
    return box_solid(WHEEL_X0, WHEEL_X1, lambda x: WHEEL_HALF,
                     lambda x: Z_SUPER_TOP - 0.05, Z_WHEEL_TOP, n_x=24)


def weld(verts, faces, tol=1e-4):
    """Сварка совпадающих вершин и удаление вырожденных граней."""
    key = {}
    remap = [0] * len(verts)
    out = []
    q = 1.0 / tol
    for i, v in enumerate(verts):
        k = (round(v[0] * q), round(v[1] * q), round(v[2] * q))
        j = key.get(k)
        if j is None:
            j = len(out); key[k] = j; out.append(v)
        remap[i] = j
    nf = []
    for f in faces:
        g = []
        for i in f:
            r = remap[i]
            if not g or g[-1] != r:
                g.append(r)
        if len(g) > 2 and g[0] == g[-1]:
            g.pop()
        if len(g) >= 3:
            nf.append(tuple(g))
    return out, nf


def check(verts, faces):
    """Манифолдность: каждое ребро ровно у двух граней."""
    from collections import Counter
    c = Counter()
    for f in faces:
        for i in range(len(f)):
            a, b = f[i], f[(i + 1) % len(f)]
            c[(a, b) if a < b else (b, a)] += 1
    bad = sum(1 for v in c.values() if v != 2)
    return dict(verts=len(verts), faces=len(faces), edges=len(c),
                non_manifold=bad, closed=(bad == 0),
                euler=len(verts) - len(c) + len(faces))


def _tris(faces):
    for f in faces:
        for k in range(1, len(f) - 1):
            yield (f[0], f[k], f[k + 1])


def write_stl(path, verts, faces, name="gorizont"):
    import struct
    tris = list(_tris(faces))
    with open(path, "wb") as fh:
        fh.write(("%-80s" % name[:79]).encode("ascii", "replace"))
        fh.write(struct.pack("<I", len(tris)))
        for (a, b, c) in tris:
            pa, pb, pc = verts[a], verts[b], verts[c]
            ux, uy, uz = (pb[0]-pa[0], pb[1]-pa[1], pb[2]-pa[2])
            vx, vy, vz = (pc[0]-pa[0], pc[1]-pa[1], pc[2]-pa[2])
            nx, ny, nz = (uy*vz-uz*vy, uz*vx-ux*vz, ux*vy-uy*vx)
            L = math.sqrt(nx*nx+ny*ny+nz*nz) or 1.0
            fh.write(struct.pack("<12fH", nx/L, ny/L, nz/L,
                                 *pa, *pb, *pc, 0))
    return len(tris)


def write_obj(path, verts, faces, name="gorizont"):
    with open(path, "w", encoding="utf-8", newline="\n") as fh:
        fh.write("# «Волжский Горизонт» — обводы по плазовой таблице\n")
        fh.write("o %s\n" % name)
        for v in verts:
            fh.write("v %.4f %.4f %.4f\n" % v)
        for f in faces:
            fh.write("f " + " ".join(str(i + 1) for i in f) + "\n")
    return len(faces)
