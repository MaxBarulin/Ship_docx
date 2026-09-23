# -*- coding: utf-8 -*-
"""Пересчёт плазовой таблицы по геометрии сечения.

Шпангоут строится так, как его строит плазовщик:

    * плоское днище от ДП до полушироты днища b_дн на высоте килевой
      линии z_к;
    * скуловая дуга радиуса r, касательная к днищу и к борту;
    * прямой борт с углом развала phi от вертикали, проходящий через
      точку по борту (b_брт, z_брт).

Из условия касания радиус однозначен:

    r = [(b_брт - b_дн)*cos(phi) - (z_брт - z_к)*sin(phi)] / (1 - sin(phi))

Свободный параметр один - развал борта phi. Он восстанавливается по
имеющейся таблице методом наименьших квадратов на каждом шпангоуте,
затем сглаживается по длине, и по нему пересчитываются все ординаты.

Зачем - в прежней таблице ординаты ватерлиний, лежащих ниже килевой линии,
хранились нулями, а сплайн по длине протаскивал эти нули в оконечности.
В итоге между шпангоутами полуширота проваливалась почти до нуля там, где
обвод на самом деле полный. Сечение, построенное по геометрии, такого дать
не может - ниже килевой линии ватерлинии просто нет, и в таблице стоит
прочерк.

    python scripts/пересчёт_ординат.py           # отчёт без записи
    python scripts/пересчёт_ординат.py --write   # записать в gorizont.py
"""
import os, sys, math, io

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from lib import gorizont as G

WL = G.WATERLINES


def bilge_radius(bk, bb, zk, zb, phi):
    s, c = math.sin(phi), math.cos(phi)
    return ((bb - bk) * c - (zb - zk) * s) / (1.0 - s)


def section_y(z, zk, bk, zb, bb, phi):
    """Полуширота сечения на высоте z (None ниже килевой линии)."""
    if z < zk - 1e-9:
        return None
    if z >= zb - 1e-9:
        return bb
    r = bilge_radius(bk, bb, zk, zb, phi)
    if r <= 1e-6:
        t = (z - zk) / max(zb - zk, 1e-9)
        return bk + (bb - bk) * t
    z_t = zk + r * (1.0 - math.sin(phi))       # верх скуловой дуги
    if z <= z_t:
        d = z - zk - r
        return bk + math.sqrt(max(r * r - d * d, 0.0))
    return bk + r * math.cos(phi) + (z - z_t) * math.tan(phi)


def fit_phi(zk, bk, zb, bb, ys):
    """Развал борта, наилучшим образом отвечающий ординатам таблицы."""
    pts = [(zw, ys[k]) for k, zw in enumerate(WL)
           if zk + 0.02 < zw < zb - 0.02 and ys[k] > 1e-6]
    best, bphi = None, 0.0
    lo, hi = 0.0, math.radians(55.0)
    for it in range(60):
        phi = lo + (hi - lo) * it / 59.0
        if bilge_radius(bk, bb, zk, zb, phi) < 0.0:
            continue
        e = 0.0
        for zw, y in pts:
            m = section_y(zw, zk, bk, zb, bb, phi)
            e += (m - y) ** 2
        if not pts:
            e = 0.0
        if best is None or e < best:
            best, bphi = e, phi
    n = max(len(pts), 1)
    return bphi, math.sqrt((best or 0.0) / n)


def smooth(vals, w=0.25, rounds=2):
    v = list(vals)
    for _ in range(rounds):
        out = list(v)
        for i in range(1, len(v) - 1):
            out[i] = (1 - 2 * w) * v[i] + w * v[i - 1] + w * v[i + 1]
        v = out
    return v


def rebuild(verbose=True):
    phis, rms = [], []
    for n, x, zk, bk, zb, bb, ys in G.OFFSETS:
        p, e = fit_phi(zk, bk, zb, bb, ys)
        phis.append(p)
        rms.append(e)
    phis_s = smooth(phis)
    rows, report = [], []
    for i, (n, x, zk, bk, zb, bb, ys) in enumerate(G.OFFSETS):
        phi = phis_s[i]
        r = bilge_radius(bk, bb, zk, zb, phi)
        new = tuple(section_y(zw, zk, bk, zb, bb, phi) for zw in WL)
        dmax = 0.0
        for k, zw in enumerate(WL):
            if new[k] is None or ys[k] <= 1e-6:
                continue
            dmax = max(dmax, abs(new[k] - ys[k]))
        rows.append((n, x, zk, bk, zb, bb, new, math.degrees(phi), r))
        report.append((n, x, math.degrees(phis[i]), math.degrees(phi), r,
                       rms[i], dmax))
    if verbose:
        print("%-6s %8s %8s %8s %8s %8s %8s" %
              ("шп", "x", "phi исх", "phi сгл", "r скулы", "невязка", "Δ макс"))
        for n, x, p0, p1, r, e, dm in report:
            print("%-6s %8.3f %8.2f %8.2f %8.3f %8.3f %8.3f"
                  % (n, x, p0, p1, r, e, dm))
    return rows, report


def render_offsets(rows):
    """Текст константы OFFSETS для gorizont.py."""
    out = ["OFFSETS = [",
           "    # (№ шп., x, z киля, полуширота днища, z борта, полуширота борта,",
           "    #  13 ординат по ватерлиниям, None - ватерлиния ниже килевой линии)"]
    for n, x, zk, bk, zb, bb, ys, phi, r in rows:
        nn = ("%g" % n)
        ords = ", ".join("None" if v is None else "%.3f" % v for v in ys)
        out.append("    (%6s, %8.3f, %6.3f, %6.3f, %6.3f, %6.3f," % (nn, x, zk, bk, zb, bb))
        out.append("     (%s))," % ords)
    out.append("]")
    out.append("")
    out.append("# Развал борта (град.) и радиус скулы (м) на каждом шпангоуте -")
    out.append("# по ним и строится сечение, ординаты выше лишь его отсчёты.")
    out.append("SECTION_SHAPE = {")
    for n, x, zk, bk, zb, bb, ys, phi, r in rows:
        out.append("    %6s - (%6.2f, %6.3f)," % ("%g" % n, phi, r))
    out.append("}")
    return "\n".join(out) + "\n"


if __name__ == "__main__":
    rows, rep = rebuild(verbose=True)
    worst = max(r[6] for r in rep)
    print()
    print("максимальное изменение ординаты - %.3f м" % worst)
    print("максимальная невязка подгонки -   %.3f м" % max(r[5] for r in rep))
    if "--write" in sys.argv:
        p = os.path.join(ROOT, "src", "lib", "gorizont.py")
        s = io.open(p, encoding="utf-8").read()
        i0 = s.index("OFFSETS = [")
        i1 = s.index("\n]", i0) + 3
        tail = s[i1:]
        if "SECTION_SHAPE = {" in tail:
            j0 = tail.index("# Развал борта")
            j1 = tail.index("\n}", j0) + 3
            tail = tail[:j0] + tail[j1:]
        s = s[:i0] + render_offsets(rows) + "\n" + tail
        io.open(p, "w", encoding="utf-8", newline="\n").write(s)
        print("записано в", p)
