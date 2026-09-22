# -*- coding: utf-8 -*-
"""Проекция «корпус» крупно и таблица плазовых ординат.

Таблица — настоящая плазовая: 25 теоретических шпангоутов (20 основных
через L/20 = 6,95 м и полушпангоуты 0,5 / 1,5 / 18,5 / 19,5 в оконечностях)
на 13 ватерлиний. Ординаты в миллиметрах, как их и снимают с плаза.
Прочерк значит, что ватерлиния лежит ниже килевой линии этого шпангоута,
то есть на нём её просто нет. Под ординатами — параметры сечения, по
которым оно построено: высота килевой линии, полуширота днища, высота и
полуширота по борту, радиус скулы и развал борта.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import gorizont as G, gorizont_hydro as H

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "расчёты")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
INK, ACC, SEA = "#16202f", "#b02634", "#1c5c8a"
ROWS = G.offsets_rows()
# ординаты — с нишей колеса: на шпангоутах 9 и 10 борт срезан стенкой ниши
for r in ROWS:
    yn = H.niche_half(r["x"])
    r["y"] = [None if y is None else min(y, yn) for y in r["y"]]
    r["b_brt"] = min(r["b_brt"], yn)
WL = list(G.WATERLINES)
T = H.equilibrium()["T"]

fig = plt.figure(figsize=(19.6, 11.6))
fig.suptitle("Проекция «корпус» и таблица плазовых ординат", fontsize=17,
             fontweight="bold", x=0.010, ha="left", y=0.988)
fig.text(0.010, 0.958,
         "Слева кормовые шпангоуты 0…9, справа носовые 10…20. "
         "Ординаты в миллиметрах от диаметральной плоскости; "
         "прочерк — ватерлиния ниже килевой линии шпангоута.",
         fontsize=10, color="#56627a")
fig.text(0.990, 0.972, "«Волжский Горизонт» · проект 2026 · УЖЦ ОСК",
         fontsize=10, color="#56627a", ha="right")

ax = fig.add_axes([0.03, 0.50, 0.94, 0.44])
ax.set_aspect("equal")
ax.axis("off")
for y in range(-8, 9):
    ax.plot([y, y], [0, G.DEPTH], color="#eef1f5", lw=0.7)
for z in WL:
    ax.plot([-8.9, 8.9], [z, z], color="#dde2e9", lw=0.7)
    ax.text(-9.15, z, "%.2f" % z, fontsize=7.5, color="#56627a",
            ha="right", va="center")
sides = {1: [], -1: []}
for r in ROWS:
    n, x = r["n"], r["x"]
    s = 1 if n >= 10 else -1
    pts = [p for p in H.profile(x) if p[0] <= G.DEPTH + 1e-9]
    yd = H.half_breadth(x, G.DEPTH)
    ys = [0] + [s * p[1] for p in pts] + [s * yd, 0]
    zs = [pts[0][0]] + [p[0] for p in pts] + [G.DEPTH, G.DEPTH]
    lw = 1.35 if float(n) == int(n) else 0.8
    ax.plot(ys, zs, color=ACC if s > 0 else INK, lw=lw)
    # фальшборт над палубой — штрихом
    zb = H.side_height(x)
    if zb > G.DEPTH + 0.01:
        zz = [G.DEPTH + (min(zb, 4.90) - G.DEPTH) * k / 6 for k in range(7)]
        ax.plot([s * H.half_breadth(x, z) for z in zz], zz,
                color=ACC if s > 0 else INK, lw=0.7, ls=(0, (3, 2)))
    sides[s].append((n, yd))

# номера шпангоутов выносим в строку над палубой и соединяем выноской
for s, items in sides.items():
    items.sort(key=lambda t: t[1])
    m = len(items)
    for i, (n, yd) in enumerate(items):
        lx = s * (1.2 + (10.0 - 1.2) * (i + 0.5) / m)
        ly = 5.02 if i % 2 == 0 else 4.72
        ax.plot([s * yd, lx], [G.DEPTH + 0.03, ly - 0.10], color="#b9c2cf",
                lw=0.5)
        ax.text(lx, ly, "%g" % n, fontsize=7, color="#56627a", ha="center",
                va="bottom")
ax.plot([-8.9, 8.9], [T, T], color=SEA, lw=1.7)
ax.text(8.95, T, " ВЛ %.2f" % T, fontsize=8.5, color=SEA, va="center")
ax.plot([0, 0], [-0.15, G.DEPTH + 0.5], color=INK, lw=1.2)
ax.text(0, G.DEPTH + 0.62, "ДП", fontsize=9, color=INK, ha="center")
ax.set_xlim(-10.6, 10.6)
ax.set_ylim(-0.45, 5.55)

# --- таблица плазовых ординат
ax2 = fig.add_axes([0.012, 0.015, 0.976, 0.455])
ax2.axis("off")


def mm(v):
    return "—" if v is None else "%d" % round(v * 1000)


cols = ["ВЛ, м"] + ["%g" % r["n"] for r in ROWS]
# Плазовые ватерлинии плюс две наши: фактическая посадка (из нагрузки масс)
# и расчётная осадка, по которой построены обводы. Ординаты на них считаются
# той же геометрией сечения, что и остальные строки, с нишей колеса.
ДОП_ВЛ = [(T, "%.2f факт" % T), (G.DRAFT, "%.2f расч." % G.DRAFT)]


def _орд(r, z):
    """Полуширота шпангоута r на высоте z, м; None — ниже килевой линии."""
    if z < r["z_kil"] - 1e-6:
        return None
    return min(H.half_breadth(r["x"], min(z, r["z_brt"])), H.niche_half(r["x"]))


строки = [(z, "%.2f" % z, [r["y"][k] for r in ROWS]) for k, z in enumerate(WL)]
for z, имя in ДОП_ВЛ:
    if all(abs(z - w) > 0.005 for w in WL):
        строки.append((z, имя, [_орд(r, z) for r in ROWS]))
строки.sort(key=lambda t: t[0])
ВЫДЕЛИТЬ = {i for i, (z, имя, _) in enumerate(строки) if "факт" in имя or "расч" in имя}
body = []
for z, имя, ys in строки:
    body.append([имя] + [mm(y) for y in ys])
body.append(["z киля, мм"] + ["%d" % round(r["z_kil"] * 1000) for r in ROWS])
body.append(["полушир. днища"] + ["%d" % round(r["b_kil"] * 1000) for r in ROWS])
body.append(["z борта, мм"] + ["%d" % round(r["z_brt"] * 1000) for r in ROWS])
body.append(["полушир. борта"] + ["%d" % round(r["b_brt"] * 1000) for r in ROWS])
body.append(["радиус скулы, мм"] + ["%d" % round(r["r"] * 1000) for r in ROWS])
body.append(["развал борта, °"] + ["%.1f" % r["phi"] for r in ROWS])

tbl = ax2.table(cellText=body, colLabels=cols, loc="upper center",
                cellLoc="center", colLoc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(6.4)
tbl.scale(1, 1.14)
nw = len(строки)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#c8cfd9")
    cell.set_linewidth(0.5)
    if r == 0:
        cell.set_facecolor("#eef1f5")
        cell.set_text_props(fontweight="bold", color=INK, fontsize=6.6)
    elif c == 0:
        cell.set_facecolor("#f6f8fa")
        cell.set_text_props(fontweight="bold", color=INK, fontsize=6.2)
    elif r > nw:
        cell.set_facecolor("#fbfcfd")
        cell.set_text_props(color="#3c4757")
    if 1 <= r <= nw and (r - 1) in ВЫДЕЛИТЬ:
        # наши ватерлинии: фактическая посадка и расчётная осадка — выделены
        cell.set_facecolor("#e3eef7" if c else "#cfe0ef")
        cell.set_text_props(color=SEA, fontweight="bold")
    if c == 0:
        cell.set_width(0.072)
ax2.text(0.0, 1.035,
         "Таблица плазовых ординат: строки — ватерлинии, столбцы — номера "
         "теоретических шпангоутов; теоретическая шпация L/20 = %.3f м" % (G.LOA / 20),
         transform=ax2.transAxes, fontsize=9.5, color="#56627a")
ax2.text(1.0, 1.035,
         "Сечение: плоское днище — скуловая дуга, касательная к днищу и к "
         "борту, — прямой борт с развалом",
         transform=ax2.transAxes, fontsize=9.5, color="#56627a", ha="right")
fig.savefig(os.path.join(OUT, "01б_корпус_и_ординаты.png"), dpi=165,
            bbox_inches="tight")
from lib import fig2dxf
fig2dxf.save_dxf(fig, os.path.join(ROOT, "CAD", "расчёты", "01б_корпус_и_ординаты.dxf"),
                 title="проекция «корпус» и таблица плазовых ординат",
                 note="выделенные строки — ватерлинии %.2f (факт) и %.2f (расчётная)" % (T, G.DRAFT))
print(os.path.join(OUT, "01б_корпус_и_ординаты.png"))
