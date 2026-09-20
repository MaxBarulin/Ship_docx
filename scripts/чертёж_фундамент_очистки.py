# -*- coding: utf-8 -*-
"""Чертёж общего вида узла ВГ-2026.16.00 «Фундамент установки очистки
сточных вод» со спецификацией, таблицей нагрузок и проверками."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon as MPoly
from lib import gorizont_awts as A, gorizont_mach as Mch

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
INK, ACC, SEA, GRY, GRN = "#16202f", "#b02634", "#1c5c8a", "#9aa4b4", "#1f7a5a"
R = A.report()
G_ = R["geometry"]
X0, X1, Y0, Y1 = G_["x0"], G_["x1"], G_["y0"], G_["y1"]
ZT, ZTOP, ZEQ, ZTT = G_["z_tray"], G_["z_top"], G_["z_equip"], G_["z_tank_top"]
UNITS = {e[0]: e[3] for e in Mch.EQUIPMENT if e[0] in ("МБР", "БИО", "УФ", "СЕП")}
NAMES = {e[0]: e[1] for e in Mch.EQUIPMENT}


def feet(code):
    x0, x1, y0, y1, z0, z1 = UNITS[code]
    n = dict(A.UNITS and {u[0]: u[3] for u in A.UNITS})[code]
    dx, dy = (x1 - x0) * 0.16, (y1 - y0) * 0.16
    if n == 4:
        return [(x0 + dx, y0 + dy), (x1 - dx, y0 + dy),
                (x1 - dx, y1 - dy), (x0 + dx, y1 - dy)]
    return [(x0 + dx, (y0 + y1) / 2), (x1 - dx, (y0 + y1) / 2)]


def frame(ax, title, sub=""):
    ax.set_aspect("equal")
    ax.axis("off")
    ax.set_title(title + ("   " + sub if sub else ""), fontsize=11, loc="left",
                 color=INK, fontweight="bold")


def dim(ax, p0, p1, txt, off=0.0, vert=False, fs=8.0):
    x0, y0 = p0
    x1, y1 = p1
    if vert:
        ax.annotate("", (x0 + off, y0), (x1 + off, y1),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=0.7))
        ax.text(x0 + off - 0.06, (y0 + y1) / 2, txt, rotation=90, ha="right",
                va="center", fontsize=fs, color=INK)
    else:
        ax.annotate("", (x0, y0 + off), (x1, y1 + off),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=0.7))
        ax.text((x0 + x1) / 2, y0 + off + 0.03, txt, ha="center", va="bottom",
                fontsize=fs, color=INK)


def pos(ax, x, y, n, dx=0.0, dy=0.45, r=0.13):
    ax.plot([x, x + dx], [y, y + dy], color=GRY, lw=0.6, zorder=5)
    ax.add_patch(Circle((x + dx, y + dy), r, facecolor="white", edgecolor=INK,
                        lw=0.8, zorder=6))
    ax.text(x + dx, y + dy, str(n), ha="center", va="center", fontsize=7.5,
            color=INK, zorder=7)


fig = plt.figure(figsize=(17.2, 11.6))
fig.suptitle("Фундамент установки очистки сточных вод   ·   %s ВО" % A.MARK,
             fontsize=17, fontweight="bold", x=0.012, ha="left", y=0.983)
fig.text(0.012, 0.953,
         "Общая сварная рама четырёх аппаратов AWTS в машинном отделении: "
         "поддон с комингсом, балки по флорам и стрингерам, амортизаторы и "
         "стопоры-ограничители. Материал %s" % A.STEEL,
         fontsize=10, color="#56627a")
fig.text(0.988, 0.969, "«Волжский Горизонт» · УЖЦ ОСК 2026", fontsize=10,
         color="#56627a", ha="right")

# ------------------------------------------------------------- план --------
ax = fig.add_axes([0.030, 0.545, 0.425, 0.370])
frame(ax, "План", "вид сверху, отметка верха рамы %.3f м" % ZTOP)
ax.add_patch(Rectangle((X0 - 0.10, Y0 - 0.10), (X1 - X0) + 0.20,
                       (Y1 - Y0) + 0.20, facecolor="#eef2f7", edgecolor=INK,
                       lw=1.6))
for i in range(G_["n_long"]):
    y = Y0 + G_["pitch_long"] * i
    ax.add_patch(Rectangle((X0, y - 0.05), X1 - X0, 0.10, facecolor="#c9d3e0",
                           edgecolor=INK, lw=1.0))
for j in range(G_["n_cross"]):
    x = X0 + G_["pitch_cross"] * j
    ax.add_patch(Rectangle((x - 0.04, Y0), 0.08, Y1 - Y0, facecolor="#dbe6f1",
                           edgecolor=INK, lw=0.8))
for code, box in UNITS.items():
    x0, x1, y0, y1 = box[0], box[1], box[2], box[3]
    ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor="none",
                           edgecolor=ACC, lw=1.1, ls=(0, (5, 3))))
    ax.text((x0 + x1) / 2, (y0 + y1) / 2, code, ha="center", va="center",
            fontsize=9.5, color=ACC, fontweight="bold")
    for (px, py) in feet(code):
        ax.add_patch(Circle((px, py), 0.075, facecolor="#ffd9b0",
                            edgecolor=INK, lw=0.8, zorder=4))
for sx in (X0 + 0.12, X1 - 0.12):
    for sy in (Y0 + 0.12, Y1 - 0.12):
        ax.add_patch(Rectangle((sx - 0.06, sy - 0.06), 0.12, 0.12,
                               facecolor=GRN, edgecolor=INK, lw=0.7, zorder=4))
ax.add_patch(Circle((X1 - 0.02, Y0 + 0.30), 0.10, facecolor="white",
                    edgecolor=SEA, lw=1.2, zorder=5))
pos(ax, X0 + 0.9, Y0 + G_["pitch_long"], 1, 0.0, 0.42)
pos(ax, X0 + G_["pitch_cross"], Y1 - 0.9, 2, 0.0, 0.42)
pos(ax, X0 - 0.10, Y1 - 1.8, 3, -0.45, 0.0, 0.13)
pos(ax, X0 + 1.4, Y1 + 0.10, 4, 0.0, 0.42)
pos(ax, feet("МБР")[0][0], feet("МБР")[0][1], 11, -0.55, -0.35)
pos(ax, X0 + 0.12, Y0 + 0.12, 7, -0.50, -0.30)
pos(ax, X1 - 0.02, Y0 + 0.30, 10, 0.55, -0.20)
dim(ax, (X0, Y0 - 0.10), (X1, Y0 - 0.10), "%.0f" % ((X1 - X0) * 1000), -0.42)
dim(ax, (X0 - 0.10, Y0), (X0 - 0.10, Y1), "%.0f" % ((Y1 - Y0) * 1000),
    -0.45, vert=True)
dim(ax, (X0, Y0), (X0, Y0 + G_["pitch_long"]),
    "%.0f" % (G_["pitch_long"] * 1000), X1 - X0 + 0.55, vert=True, fs=7.5)
dim(ax, (X0, Y1 + 0.10), (X0 + G_["pitch_cross"], Y1 + 0.10),
    "%.0f" % (G_["pitch_cross"] * 1000), 0.30, fs=7.5)
ax.plot([X0 - 0.7, X1 + 0.7], [Y0 + (Y1 - Y0) / 2] * 2, color=SEA, lw=0.9,
        ls=(0, (8, 3, 1, 3)))
ax.text(X0 - 0.8, Y0 + (Y1 - Y0) / 2, "А", fontsize=11, color=SEA,
        fontweight="bold", ha="right", va="center")
ax.text(X1 + 0.8, Y0 + (Y1 - Y0) / 2, "А", fontsize=11, color=SEA,
        fontweight="bold", va="center")
ax.set_xlim(X0 - 1.5, X1 + 1.5)
ax.set_ylim(Y0 - 1.1, Y1 + 1.1)

# ------------------------------------------------------- разрез А–А --------
ax = fig.add_axes([0.487, 0.560, 0.310, 0.355])
frame(ax, "Разрез А–А", "поперёк судна")
ax.add_patch(Rectangle((Y0 - 1.2, ZTT - 0.008), (Y1 - Y0) + 2.4, 0.008,
                       facecolor="#c9d3e0", edgecolor=INK, lw=1.0))
ax.add_patch(Rectangle((Y0 - 0.10, ZT - 0.006), (Y1 - Y0) + 0.20, 0.006,
                       facecolor="#c9d3e0", edgecolor=INK, lw=1.2))
for yy in (Y0 - 0.10, Y1 + 0.092):
    ax.add_patch(Rectangle((yy, ZT), 0.008, G_["coaming"], facecolor="#c9d3e0",
                           edgecolor=INK, lw=1.0))
for yy in (Y0 - 0.108, Y1 + 0.10):
    ax.add_patch(Rectangle((yy, ZT), 0.008, ZTT - ZT, facecolor="#dfe5ee",
                           edgecolor=INK, lw=0.9))
for i in range(G_["n_long"]):
    y = Y0 + G_["pitch_long"] * i
    ax.add_patch(Rectangle((y - 0.004, ZT), 0.008, ZTOP - ZT - 0.010,
                           facecolor="#8c99ab", edgecolor=INK, lw=0.8))
    ax.add_patch(Rectangle((y - 0.050, ZTOP - 0.010), 0.100, 0.010,
                           facecolor="#8c99ab", edgecolor=INK, lw=0.8))
for code, box in UNITS.items():
    y0, y1, z0, z1 = box[2], box[3], box[4], box[5]
    if code in ("УФ", "СЕП"):
        continue
    ax.add_patch(Rectangle((y0, z0), y1 - y0, min(z1, ZEQ + 1.15) - z0,
                           facecolor="#f6e6dd", edgecolor=ACC, lw=1.1))
    ax.text((y0 + y1) / 2, z0 + 1.15, code, ha="center", fontsize=10.5,
            color=ACC, fontweight="bold")
    for (px, py) in feet(code):
        ax.add_patch(Rectangle((py - 0.09, ZTOP), 0.18, 0.016,
                               facecolor="#c9d3e0", edgecolor=INK, lw=0.7))
        ax.add_patch(Rectangle((py - 0.075, ZTOP + 0.016), 0.15, 0.070,
                               facecolor="#ffd9b0", edgecolor=INK, lw=0.8))
        ax.add_patch(Rectangle((py - 0.085, ZTOP + 0.086), 0.17, 0.012,
                               facecolor="#c9d3e0", edgecolor=INK, lw=0.7))
dim(ax, (Y1 + 0.14, ZT), (Y1 + 0.14, ZTT), "%.0f" % ((ZTT - ZT) * 1000),
    0.55, vert=True, fs=7.5)
ax.text(Y0 - 0.32, ZTT + 0.10, "2-е дно %.3f" % ZTT, fontsize=8,
        color="#56627a", ha="right")
ax.text(Y0 - 0.32, ZT - 0.22, "поддон %.3f" % ZT, fontsize=8,
        color="#56627a", ha="right")
ax.text(Y0 - 0.32, ZEQ + 0.44, "опорная плоскость %.3f" % ZEQ, fontsize=8,
        color="#56627a", ha="right")
pos(ax, Y0 + G_["pitch_long"], ZTOP - 0.005, 1, -1.90, 0.72)
pos(ax, Y1 + 0.096, ZT + G_["coaming"], 4, 1.30, -0.10)
pos(ax, feet("БИО")[1][1], ZTOP + 0.05, 11,
    Y1 + 0.90 - feet("БИО")[1][1], 0.58)
pos(ax, feet("МБР")[0][1], ZTOP + 0.008, 6, -0.55, -0.42)
ax.set_xlim(Y0 - 2.1, Y1 + 2.1)
ax.set_ylim(ZT - 0.80, ZEQ + 1.45)

# -------------------------------------------------- узел балки (выноска) ---
ax = fig.add_axes([0.812, 0.545, 0.176, 0.370])
frame(ax, "Узел Б", "сечение балки и шов")
b = A.LONG_BEAM
hw, tw, bf, tf = 0.140, 0.008, 0.100, 0.010
ax.add_patch(Rectangle((-tw / 2, 0), tw, hw, facecolor="#8c99ab",
                       edgecolor=INK, lw=1.2))
ax.add_patch(Rectangle((-bf / 2, hw), bf, tf, facecolor="#8c99ab",
                       edgecolor=INK, lw=1.2))
for s in (-1, 1):
    ax.add_patch(MPoly([(s * tw / 2, hw), (s * tw / 2 + s * 0.006, hw),
                        (s * tw / 2, hw - 0.006)], closed=True,
                       facecolor=ACC, edgecolor=ACC, lw=0.6))
ax.add_patch(Rectangle((-0.075, -0.006), 0.150, 0.006, facecolor="#c9d3e0",
                       edgecolor=INK, lw=1.0))
dim(ax, (-tw / 2, 0), (-tw / 2, hw), "140", -0.055, vert=True, fs=8)
dim(ax, (-bf / 2, hw + tf), (bf / 2, hw + tf), "100", 0.030, fs=8)
ax.text(0.085, hw * 0.5, "стенка 8", fontsize=8.5, color=INK, va="center")
ax.text(0.085, hw + tf / 2, "поясок 10", fontsize=8.5, color=INK, va="center")
ax.text(0.085, -0.004, "поддон 6", fontsize=8.5, color=INK, va="center")
ax.text(-0.085, hw - 0.012, "6", fontsize=9, color=ACC, ha="right",
        fontweight="bold")
ax.text(0.0, -0.075,
        "A = %.1f см²   I = %.0f см⁴   W = %.0f см³"
        % (b["A"] * 1e4, b["I"] * 1e8, b["W_min"] * 1e6),
        fontsize=8.5, color="#56627a", ha="center")
ax.set_xlim(-0.20, 0.30)
ax.set_ylim(-0.13, 0.26)

# ------------------------------------------------------ спецификация -------
ax = fig.add_axes([0.030, 0.045, 0.455, 0.465])
ax.axis("off")
ax.text(0.0, 1.01, "Спецификация", transform=ax.transAxes, fontsize=11,
        color=INK, fontweight="bold")
rows = [[str(r["pos"]), r["mark"], r["name"], str(r["n"]),
         "%.1f" % r["mass"], "%.1f" % r["total"]] for r in R["spec"]]
rows.append(["", "", "Итого металл узла", "", "", "%.1f" % R["steel_mass"]])
rows.append(["", "", "Итого узел с покупными", "", "", "%.1f" % R["total_mass"]])
tbl = ax.table(cellText=rows,
               colLabels=["Поз.", "Обозначение", "Наименование", "Кол.",
                          "Масса ед., кг", "Всего, кг"],
               loc="upper center", cellLoc="left", colLoc="center")
tbl.auto_set_font_size(False)
tbl.set_fontsize(7.6)
tbl.scale(1, 1.30)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#c8cfd9")
    cell.set_linewidth(0.5)
    if r == 0:
        cell.set_facecolor("#eef1f5")
        cell.set_text_props(fontweight="bold", color=INK)
    elif r > len(rows) - 2:
        cell.set_facecolor("#f3f6fa")
        cell.set_text_props(fontweight="bold", color=INK)
    if c in (0, 3, 4, 5):
        cell.set_text_props(ha="center")
    cell.set_width({0: 0.05, 1: 0.17, 2: 0.48, 3: 0.07, 4: 0.12, 5: 0.11}[c])

# ------------------------------------------------------- нагрузки ----------
ax = fig.add_axes([0.505, 0.285, 0.483, 0.225])
ax.axis("off")
ax.text(0.0, 1.03, "Расчётные нагрузки", transform=ax.transAxes, fontsize=11,
        color=INK, fontweight="bold")
ax.text(0.0, 0.93,
        "Масса блока: сухая %.1f т, рабочая заправка %.1f т, металл рамы "
        "%.2f т, поддон %.2f т. Перегрузки — по нормам РРР для класса «О»"
        % (R["masses"]["dry"], R["masses"]["liquid"], R["masses"]["steel"],
           R["masses"]["tray"]),
        transform=ax.transAxes, fontsize=8.5, color="#56627a")
lrows = [[c["case"], "%.2f" % c["nz"], "%.2f" % c["ny"], "%.1f" % c["heel"],
          "%.1f" % c["mass"], "%.0f" % c["Fz"], "%.0f" % c["Fy"],
          "%.1f" % c["per_isolator"]] for c in R["loads"]]
tbl = ax.table(cellText=lrows,
               colLabels=["Случай", "n_z", "n_y", "крен, °", "масса, т",
                          "F_z, кН", "F_y, кН", "на аморт., кН"],
               loc="upper center", cellLoc="center", colLoc="center",
               bbox=[0, 0.05, 1, 0.80])
tbl.auto_set_font_size(False)
tbl.set_fontsize(8.0)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#c8cfd9")
    cell.set_linewidth(0.5)
    if r == 0:
        cell.set_facecolor("#eef1f5")
        cell.set_text_props(fontweight="bold", color=INK)
    if c == 0:
        cell.set_text_props(ha="left")
        cell.set_width(0.24)

# -------------------------------------------------------- проверки ---------
ax = fig.add_axes([0.505, 0.045, 0.483, 0.215])
ax.axis("off")
ax.text(0.0, 1.03, "Проверки", transform=ax.transAxes, fontsize=11,
        color=INK, fontweight="bold")
crows = [[n, ("%.2f" if u == "мм" else "%.1f") % v,
          ("%.2f" if u == "мм" else "%.1f") % a, u,
          "ок" if ok else "не проходит"] for n, v, a, u, ok in A.checks()]
tbl = ax.table(cellText=crows,
               colLabels=["Проверка", "Расчёт", "Допуск", "Ед.", "Итог"],
               loc="upper center", cellLoc="center", colLoc="center",
               bbox=[0, 0.02, 1, 0.92])
tbl.auto_set_font_size(False)
tbl.set_fontsize(7.8)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#c8cfd9")
    cell.set_linewidth(0.5)
    if r == 0:
        cell.set_facecolor("#eef1f5")
        cell.set_text_props(fontweight="bold", color=INK)
    else:
        if c == 0:
            cell.set_text_props(ha="left")
            cell.set_width(0.42)
        if c == 4:
            ok = crows[r - 1][4] == "ок"
            cell.set_text_props(color=GRN if ok else ACC, fontweight="bold")

iso = R["isolator"]
fig.text(0.505, 0.0,
         "Амортизатор %s: статическая доля %.0f кгс при номинале %.0f кгс, "
         "осадка %.1f мм, собственная частота блока %.2f Гц — "
         "в %.1f раза ниже частоты ГДГ (%.1f Гц) и в %.1f раза ниже "
         "лопастной (%.1f Гц)."
         % (iso["type"], iso["static"], iso["rated"], iso["delta_mm"],
            iso["f0"], iso["ratio_dg"], iso["f_dg"], iso["ratio_blade"],
            iso["f_blade"]),
         fontsize=8.5, color="#56627a")
fig.text(0.030, 0.014,
         "Фундамент подобран по жёсткости и отстройке по частоте, а не по "
         "напряжению: запас по эквивалентному напряжению %.0f-кратный, "
         "прогиб балки %.3f мм при допуске %.2f мм."
         % (R["beam"]["sigma_allow"] / max(R["beam"]["sigma_eq"], 1e-6),
            R["beam"]["f_mm"], R["beam"]["f_allow"]),
         fontsize=8.5, color="#56627a")

p = os.path.join(OUT, "06_фундамент_очистки.png")
fig.savefig(p, dpi=165, bbox_inches="tight")
print(p)
