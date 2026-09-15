# -*- coding: utf-8 -*-
"""Чертёж детали: кница спонсона шлюпочной палубы ВГ-2026.15.01 + DXF."""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from lib import gorizont_struct as S, gorizont_strength as St

OUT = r"E:\Ship_docx\renders\горизонт_2026\чертежи"
CAD = os.path.join(ROOT, "CAD")
os.makedirs(CAD, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
os.makedirs(OUT, exist_ok=True)
INK, ACC, SEA, GRY = "#16202f", "#b02634", "#1c5c8a", "#9aa4b4"

B = St.BRACKET
chk = St.bracket_check()
chk_c = St.bracket_check(corroded=True)
A = B["a"] * 1000.0
HR = B["h_root"] * 1000.0
HT = B["h_tip"] * 1000.0
TW = B["t"]
BF, TF = B["flange_b"], B["flange_t"]
SC = 30.0
HOLE = 120.0
WEB = [(0, 0), (A, 0), (A, -HT), (SC, -HR), (0, -HR + SC)]


def dim(ax, p0, p1, txt, off=0, vert=False, fs=9):
    x0, y0 = p0
    x1, y1 = p1
    if vert:
        ax.annotate("", (x0 + off, y0), (x1 + off, y1),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
        ax.text(x0 + off - 22, (y0 + y1) / 2, txt, rotation=90, ha="right",
                va="center", fontsize=fs, color=INK)
        ax.plot([x0, x0 + off], [y0, y0], color=GRY, lw=0.6)
        ax.plot([x1, x1 + off], [y1, y1], color=GRY, lw=0.6)
    else:
        ax.annotate("", (x0, y0 + off), (x1, y1 + off),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
        ax.text((x0 + x1) / 2, y0 + off + 14, txt, ha="center", fontsize=fs, color=INK)
        ax.plot([x0, x0], [y0, y0 + off], color=GRY, lw=0.6)
        ax.plot([x1, x1], [y1, y1 + off], color=GRY, lw=0.6)


fig = plt.figure(figsize=(16.6, 11.2))
fig.suptitle("Кница спонсона шлюпочной палубы   ·   ВГ-2026.15.01",
             fontsize=17, fontweight="bold", x=0.012, ha="left", y=0.982)
fig.text(0.012, 0.951,
         "Консоль спонсона несёт шлюпку на 100 человек и шлюпбалку. "
         "13 книц на борт с шагом 2200 мм. Размеры в миллиметрах",
         fontsize=10, color="#56627a")
fig.text(0.988, 0.968, "«Волжский Горизонт» · проект 2026 · УЖЦ ОСК",
         fontsize=10, color="#56627a", ha="right")

ax = fig.add_axes([0.035, 0.44, 0.56, 0.46])
ax.set_aspect("equal")
ax.axis("off")
ax.add_patch(plt.Polygon(WEB, closed=True, fc="#e9edf3", ec=INK, lw=2.0))
ax.add_patch(Circle((A * 0.44, -HR * 0.46), HOLE / 2, fc="white", ec=INK, lw=1.4))
ax.plot([SC, A], [-HR - TF / 2, -HT - TF / 2], color=SEA, lw=5, solid_capstyle="butt")
ax.text(A * 0.52, -HR - 72, "поясок 80x10, приварной", fontsize=9, color=SEA)
ax.plot([-70, 0], [0, 0], color=GRY, lw=3)
ax.plot([0, A + 90], [22, 22], color=GRY, lw=3)
ax.text(-75, 12, "борт надстройки", fontsize=8.5, color="#56627a", ha="right")
ax.text(A + 95, 30, "настил спонсона 6 мм", fontsize=8.5, color="#56627a")
ax.plot([0, 0], [-HR - 120, 60], color=INK, lw=0.8, ls="-.")
dim(ax, (0, 22), (A, 22), "%.0f" % A, off=105)
dim(ax, (0, 0), (0, -HR), "%.0f" % HR, off=-95, vert=True)
dim(ax, (A, 0), (A, -HT), "%.0f" % HT, off=95, vert=True)
ax.annotate("R%.0f вырез под шов" % SC, (SC * 0.6, -HR + SC * 0.6),
            (330, -HR - 120), fontsize=8.5, color=INK,
            arrowprops=dict(arrowstyle="-", color=GRY, lw=0.8))
ax.annotate("отв. %.0f облегчающее" % HOLE, (A * 0.44 + HOLE / 2, -HR * 0.46),
            (A * 0.64, -HR * 0.16), fontsize=8.5, color=INK,
            arrowprops=dict(arrowstyle="-", color=GRY, lw=0.8))
ax.plot([-40, 60], [-HR * 0.55, -HR * 0.55 + 90], color=INK, lw=0.8)
ax.plot([-40, -190], [-HR * 0.55, -HR * 0.55], color=INK, lw=0.8)
ax.text(-196, -HR * 0.55 + 6, "6", fontsize=10, color=INK, ha="right")
ax.text(-196, -HR * 0.55 - 36, "двусторонний", fontsize=8, color="#56627a", ha="right")
ax.plot([A * 0.44, A * 0.44], [70, -HR - 70], color=ACC, lw=1.0, ls=(0, (7, 3, 1, 3)))
ax.text(A * 0.44, 96, "А", fontsize=12, color=ACC, ha="center", fontweight="bold")
ax.text(A * 0.44, -HR - 106, "А", fontsize=12, color=ACC, ha="center", fontweight="bold")
ax.set_xlim(-340, A + 250)
ax.set_ylim(-HR - 220, 200)

ax2 = fig.add_axes([0.63, 0.50, 0.33, 0.40])
ax2.set_aspect("equal")
ax2.axis("off")
h = HR * 0.72
ax2.add_patch(Rectangle((-TW / 2, 0), TW, h, fc="#dfe6ee", ec=INK, lw=1.6))
ax2.add_patch(Rectangle((-BF / 2, -TF), BF, TF, fc="#dfe6ee", ec=INK, lw=1.6))
dim(ax2, (-BF / 2, -TF), (BF / 2, -TF), "%.0f" % BF, off=-58)
dim(ax2, (BF / 2, -TF), (BF / 2, 0), "%.0f" % TF, off=52, vert=True)
dim(ax2, (TW / 2, 0), (TW / 2, h), "стенка %.0f" % TW, off=110, vert=True)
ax2.text(0, h + 44, "А — А   масштаб 1:2", fontsize=11, ha="center",
         color=ACC, fontweight="bold")
ax2.set_xlim(-200, 240)
ax2.set_ylim(-150, h + 100)

ax3 = fig.add_axes([0.035, 0.05, 0.56, 0.34])
ax3.axis("off")
ax3.text(0, 1.0, "Расчёт на прочность", fontsize=12, fontweight="bold",
         color=INK, transform=ax3.transAxes)
lines = [
    "Шлюпка на 100 чел. массой %.1f т распределена на %d кницы, коэффициент %.1f"
    % (B["boat_mass"], chk["n_brackets"], B["k_dyn"]),
    "  испытательная нагрузка спускового устройства — %.1f кН на кницу" % chk["p_boat"],
    "Толпа на спонсоне %.0f кПа на площади %.2f x %.2f м — %.1f кН"
    % (B["crowd"], B["a"], B["pitch"], chk["p_deck"]),
    "Сила P = %.1f кН, плечо до корня %.2f м, момент M = %.1f кН*м"
    % (chk["P"], chk["arm"], chk["M"]),
    "",
    "Сечение в корне: A = %.1f см2, I = %.0f см4, W = %.0f см3"
    % (chk["A_cm2"], chk["I_cm4"], chk["W_cm3"]),
    "Нормальное напряжение M / W = %.1f МПа" % chk["sigma"],
    "Касательное P / A стенки = %.1f МПа" % chk["tau"],
    "Эквивалентное по энергетической теории = %.1f МПа" % chk["sigma_eq"],
    "Допускаемое 0.65 ReH = %.0f МПа, запас %.1f"
    % (chk["sigma_allow"], chk["sigma_allow"] / chk["sigma_eq"]),
    "Критическое напряжение устойчивости стенки %.0f МПа — не достигается"
    % chk["sigma_cr"],
    "Шов катет 6 мм двусторонний: %.1f МПа при допускаемых %.0f МПа"
    % (chk["tau_weld"], 0.6 * chk["tau_allow"] * 2),
    "",
    "С припуском на коррозию 1.5 мм за срок службы: %.1f МПа, запас %.1f"
    % (chk_c["sigma_eq"], chk_c["sigma_allow"] / chk_c["sigma_eq"]),
]
for i, t in enumerate(lines):
    ax3.text(0, 0.90 - i * 0.068, t, fontsize=9,
             color=INK if i < 4 else "#2c3a4e", transform=ax3.transAxes)

ax4 = fig.add_axes([0.63, 0.05, 0.33, 0.40])
ax4.axis("off")
ax4.add_patch(Rectangle((0, 0), 1, 1, transform=ax4.transAxes, fill=False,
                        ec="#8d97a6", lw=1.2))
rows = [("Обозначение", "ВГ-2026.15.01"),
        ("Наименование", "Кница спонсона"),
        ("Материал", "Лист 10 ГОСТ 19903, 09Г2С-15"),
        ("Поясок", "Полоса 80x10 ГОСТ 103, 09Г2С"),
        ("Масса детали", "%.1f кг" % chk["mass_kg"]),
        ("Количество", "26 шт., 13 на борт"),
        ("Заготовка", "Лазерная резка листа"),
        ("Сварка", "РДС, катет 6 мм, двусторонний"),
        ("Покрытие", "Грунт ЭП-0199, эмаль ЭП-1155"),
        ("Масштаб", "1 : 5"),
        ("Разработал", "команда УЖЦ ОСК 2026")]
for i, (k, v) in enumerate(rows):
    y = 0.94 - i * 0.085
    ax4.text(0.03, y, k, fontsize=8.4, color="#56627a", transform=ax4.transAxes)
    ax4.text(0.37, y, v, fontsize=8.6, color=INK, fontweight="bold",
             transform=ax4.transAxes)
fig.savefig(os.path.join(OUT, "03_кница_спонсона.png"), dpi=150, bbox_inches="tight")
print("чертёж готов")

import ezdxf
doc = ezdxf.new("R2010", setup=True)
doc.units = ezdxf.units.MM
msp = doc.modelspace()
for name, col in (("KONTUR", 7), ("OTVERSTIYA", 1), ("POYASOK", 5), ("TEXT", 3)):
    doc.layers.add(name, color=col)
msp.add_lwpolyline(WEB, close=True, dxfattribs={"layer": "KONTUR"})
msp.add_circle((A * 0.44, -HR * 0.46), HOLE / 2, dxfattribs={"layer": "OTVERSTIYA"})
ln = math.hypot(A - SC, HR - HT)
msp.add_lwpolyline([(0, -HR - 150), (ln, -HR - 150), (ln, -HR - 150 + BF),
                    (0, -HR - 150 + BF)], close=True, dxfattribs={"layer": "POYASOK"})
msp.add_text("VG-2026.15.01 KNICA SPONSONA  LIST 10  09G2S  26 SHT",
             dxfattribs={"layer": "TEXT", "height": 25}).set_placement((0, 150))
msp.add_text("POYASOK 80x10 L=%.0f  09G2S  26 SHT" % ln,
             dxfattribs={"layer": "TEXT", "height": 20}).set_placement((0, -HR - 215))
doc.saveas(os.path.join(CAD, "VG-2026.15.01_knica_sponsona.dxf"))
print("dxf готов", round(ln))
