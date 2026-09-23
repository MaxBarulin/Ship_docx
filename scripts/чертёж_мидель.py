# -*- coding: utf-8 -*-
"""Конструктивный чертёж мидель-шпангоута."""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Polygon as MPoly, Rectangle
from lib import gorizont as G, gorizont_hydro as H, gorizont_struct as S, gorizont_strength as St
from lib import eskd

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
plt.rcParams.update({"axes.unicode_minus": False, "font.family": "DejaVu Sans", "font.size": 9,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
os.makedirs(OUT, exist_ok=True)
INK, ACC, SEA, GRY = "#16202f", "#b02634", "#1c5c8a", "#8d97a6"
X = S.X_MID
b_dn, b_sk, b_pal, z_sk, z_kil, z_brt = H._station(X)
T = H.equilibrium()["T"]
DB = S.DB_HEIGHT
SP = S.SPACING

# Лист по ГОСТ 2.301 с основной надписью 2.104 формы 1:
# заголовок и подпись сверху ушли в штамп
SH = eskd.Sheet('A1', mark="ВГ-2026.00.00 СБ",
                name="Мидель-шпангоут" + chr(10) + "конструктивный",
                material="Сталь 09Г2С ГОСТ 19281-2014",
                mass=None, scale="1:25",
                sheet_no=1, sheets=1)
fig = SH.fig


def _ax(x, y, w, h):
    return SH.axes_frac(x, y, w, h)



ax = _ax(*[0.02, 0.545, 0.63, 0.345])
ax.set_aspect("equal")
ax.axis("off")


def plate(y0, z0, y1, z1, t_mm, col=INK, lw=2.6):
    ax.plot([y0, y1], [z0, z1], color=col, lw=lw, solid_capstyle="butt")


def stiff(y, z, hw, tw, bf, tf, ang=90, col=SEA):
    """Профиль - стенка длиной hw под углом ang, поясок bf."""
    a = math.radians(ang)
    dy, dz = math.cos(a) * hw, math.sin(a) * hw
    ax.plot([y, y + dy], [z, z + dz], color=col, lw=1.8)
    if bf:
        py, pz = -math.sin(a) * bf / 2, math.cos(a) * bf / 2
        ax.plot([y + dy - py, y + dy + py], [z + dz - pz, z + dz + pz],
                color=col, lw=2.4)


# --- обшивка (только правый борт, слева осевая)
plate(0, z_kil, b_dn, z_kil, 9)                         # днище
plate(b_dn, z_kil, b_sk, z_sk, 10)                      # скула
plate(b_sk, z_sk, b_pal, z_brt, 8)                      # борт
plate(0, DB, b_sk - 0.30, DB, 8)                        # второе дно
plate(0, z_brt, b_pal, z_brt, 8)                        # главная палуба
ax.plot([0, 0], [z_kil - 0.1, z_brt + 0.35], color=INK, lw=1.0, ls="-.")
ax.text(0, z_brt + 0.45, "ДП", ha="center", fontsize=10, color=INK)

# --- вертикальный киль и стрингеры
for y in (0.0, 2.75, 5.50):
    ax.plot([y, y], [z_kil, DB], color=SEA, lw=2.6)
# --- продольные рёбра днища
for j in range(1, 13):
    y = j * SP
    if y < b_dn - 0.35 and abs(y - 2.75) > 0.15 and abs(y - 5.50) > 0.15:
        stiff(y, z_kil, 0.14, 8, 0.06, 10)
# --- рёбра второго дна
for j in range(1, 14):
    y = j * SP
    if y < b_sk - 0.55:
        stiff(y, DB, 0.12, 8, 0.05, 8, ang=-90)
# --- рёбра главной палубы
for j in range(1, 14):
    y = j * SP
    if y < b_pal - 0.75 and abs(y - 4.10) > 0.2:
        stiff(y, z_brt, 0.12, 8, 0.05, 8, ang=-90)
# --- карлингсы
for y in (0.0, 4.10):
    ax.plot([y, y], [z_brt - 0.60, z_brt], color=SEA, lw=2.6)
    ax.plot([y - 0.09, y + 0.09], [z_brt - 0.60, z_brt - 0.60], color=SEA, lw=2.8)
# --- шпангоут и бортовой стрингер
ax.plot([b_sk - 0.12, b_pal - 0.12], [z_sk, z_brt], color=SEA, lw=1.8)
ax.plot([b_sk - 0.52, b_sk - 0.12], [2.60, 2.60], color=SEA, lw=2.2)
ax.plot([b_sk - 0.52, b_sk - 0.52], [2.55, 2.65], color=SEA, lw=2.6)
# --- скуловая кница и бракета
ax.add_patch(MPoly([(b_sk - 0.12, DB), (b_sk - 0.12, DB + 0.85),
                    (b_sk - 1.05, DB)], closed=True, fill=False, ec=ACC, lw=1.6))
ax.add_patch(MPoly([(b_pal - 0.13, z_brt), (b_pal - 0.13, z_brt - 0.80),
                    (b_pal - 1.00, z_brt)], closed=True, fill=False, ec=ACC, lw=1.6))
# --- ватерлиния
ax.plot([-0.2, b_pal + 0.4], [T, T], color=SEA, lw=1.1, ls="--")
ax.text(b_pal + 0.5, T, "ВЛ %.2f" % T, fontsize=8.5, color=SEA, va="center")

# --- размеры
def dim(y0, y1, z, txt, off=0.0):
    ax.annotate("", (y0, z + off), (y1, z + off),
                arrowprops=dict(arrowstyle="<->", color=GRY, lw=1.0))
    ax.text((y0 + y1) / 2, z + off + 0.07, txt, ha="center", fontsize=8.5, color="#56627a")


dim(0, b_pal, z_brt + 0.75, "полуширота %.2f м" % b_pal)
dim(0, b_dn, z_kil - 0.55, "плоское днище %.2f м" % b_dn)
ax.annotate("", (b_pal + 0.85, z_kil), (b_pal + 0.85, z_brt),
            arrowprops=dict(arrowstyle="<->", color=GRY, lw=1.0))
ax.text(b_pal + 0.95, (z_kil + z_brt) / 2, "H = %.2f м" % G.DEPTH, fontsize=8.5,
        color="#56627a", rotation=90, va="center")
ax.annotate("", (b_pal + 0.45, z_kil), (b_pal + 0.45, DB),
            arrowprops=dict(arrowstyle="<->", color=GRY, lw=1.0))
ax.text(b_pal + 0.38, DB / 2, "h дв. дна %.2f" % DB, fontsize=8, color="#56627a",
        rotation=90, va="center", ha="right")

# --- выноски
POS = [
    ("Горизонтальный киль 1800×12", 0.45, z_kil, -1.6, -0.95),
    ("Обшивка днища 9 мм", 3.4, z_kil, 0.4, -1.30),
    ("Вертикальный киль 1200×12", 0.0, 0.62, -2.2, -0.35),
    ("Днищевые стрингеры 1200×10", 2.75, 0.62, -2.5, 0.42),
    ("Рёбра днища 140×8/60×10, шаг 550", 4.4, 0.14, 0.2, -1.22),
    ("Настил второго дна 8 мм", 6.4, DB, 2.0, 1.55),
    ("Рёбра второго дна 120×8/50×8", 1.65, DB - 0.14, -3.1, 0.62),
    ("Скуловой пояс 10 мм", (b_dn + b_sk) / 2, z_sk / 2, 3.4, -0.55),
    ("Обшивка борта 8 мм, пояс ВЛ 9 мм", b_pal, 1.55, 2.5, -0.75),
    ("Шпангоут 120×8/50×8, шаг 550", b_pal - 0.12, 2.95, 2.7, -0.55),
    ("Бортовой стрингер 400×9/100×10", b_sk - 0.5, 2.60, -3.6, -0.15),
    ("Настил главной палубы 8 мм", 6.6, z_brt, 2.3, 0.72),
    ("Рёбра палубы 120×8/50×8, шаг 550", 2.2, z_brt - 0.13, -3.6, 0.55),
    ("Карлингс 600×10/180×12", 4.10, z_brt - 0.60, -3.3, -0.62),
    ("Скуловая кница, лист 10 мм", b_sk - 0.7, DB + 0.45, -3.9, 0.35),
    ("Палубная кница 10 мм", b_pal - 0.5, z_brt - 0.45, 2.6, -0.28),
]
for txt, y, z, dy, dz in POS:
    ax.annotate(txt, (y, z), (y + dy, z + dz), fontsize=8.5, color=INK,
                ha="left" if dy > 0 else "right",
                arrowprops=dict(arrowstyle="-", color=GRY, lw=0.8,
                                shrinkA=0, shrinkB=2))
ax.set_xlim(-5.8, 14.4)
ax.set_ylim(-1.55, 5.75)

# ---------------- спецификация связей и результаты расчёта
g = S.equivalent_girder()
r = St.stresses()
ax2 = _ax(*[0.655, 0.34, 0.325, 0.56])
ax2.axis("off")
ax2.text(0, 1.0, "Спецификация связей эквивалентного бруса",
         fontsize=11, fontweight="bold", color=INK, transform=ax2.transAxes)
rows = [(n, "%.0f" % a, "%.2f" % z) for n, a, z, i in g["elements"]]
tbl = ax2.table(cellText=rows, colLabels=["связь", "A, см²", "z, м"],
                colWidths=[0.66, 0.18, 0.16], loc="upper center", cellLoc="left")
tbl.auto_set_font_size(False)
tbl.set_fontsize(7.6)
tbl.scale(1, 1.18)
for (rr, cc), cell in tbl.get_celld().items():
    cell.set_edgecolor("#ccd3dd")
    cell.set_linewidth(0.5)
    if rr == 0:
        cell.set_facecolor("#eef1f5")
        cell.set_text_props(fontweight="bold")
    if cc > 0:
        cell.set_text_props(ha="right")

ax3 = _ax(*[0.03, 0.045, 0.60, 0.43])
ax3.axis("off")
ax3.text(0, 1.0, "Результаты расчёта общей продольной прочности",
         fontsize=11, fontweight="bold", color=INK, transform=ax3.transAxes)
lines = [
    "Площадь сечения эквивалентного бруса A = %.0f см² = %.3f м²" % (g["A"], g["A"] * 1e-4),
    "Нейтральная ось z₀ = %.3f м от основной плоскости" % g["z0"],
    "Момент инерции I = %.3f м⁴" % g["I_m4"],
    "Момент сопротивления палубы W = %.3f м³, днища W = %.3f м³" % (g["W_deck_m3"], g["W_bot_m3"]),
    "",
]
for row in r["rows"]:
    lines.append("%-14s M = %8.1f МН·м   σ палубы = %5.1f МПа   σ днища = %5.1f МПа   %s"
                 % (row["condition"], row["M"] / 1000.0, row["sigma_deck"],
                    row["sigma_bot"], "проходит" if row["ok"] else "НЕ ПРОХОДИТ"))
lines += ["",
          "Материал основных связей - сталь %s, предел текучести %.0f МПа" %
          (r["steel"]["name"], r["steel"]["ReH"]),
          "Допускаемое напряжение 0.60·ReH = %.0f МПа, использовано %.0f %%" %
          (r["sigma_allow"], 100 * max(x["sigma_deck"] for x in r["rows"]) / r["sigma_allow"]),
          "Волна класса «%s» - высота %.1f м, длина равна длине судна"
          % (H.CLASS, H.WAVE_HEIGHT[H.CLASS])]
for i, s_ in enumerate(lines):
    ax3.text(0, 0.92 - i * 0.055, s_, fontsize=8.8, color=INK if i < 4 else "#3a4658",
             family="DejaVu Sans", transform=ax3.transAxes)

# штамп
# свой информационный блок убран: те же данные стоят в основной
# надписи листа, и два штампа на чертеже противоречили друг другу

SH.save(os.path.join(OUT, "01_мидель_шпангоут.png"))
print("готово")
