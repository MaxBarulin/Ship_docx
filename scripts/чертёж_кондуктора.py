# -*- coding: utf-8 -*-
"""Чертёж сварочного кондуктора для кницы ВГ-2026.15.01 и маршрутная карта."""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from lib import gorizont_strength as St
from lib import eskd

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
CAD = os.path.join(ROOT, "CAD")
os.makedirs(OUT, exist_ok=True)
os.makedirs(CAD, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
INK, ACC, SEA, GRY = "#16202f", "#b02634", "#1c5c8a", "#9aa4b4"
B = St.BRACKET
A = B["a"] * 1000.0
HR, HT = B["h_root"] * 1000.0, B["h_tip"] * 1000.0
BF, TF, TW = B["flange_b"], B["flange_t"], B["t"]
SC = 30.0
PLATE = (A + 300.0, HR + 300.0)     # плита основания кондуктора

# Лист по ГОСТ 2.301 с основной надписью 2.104 формы 1:
# заголовок и подпись сверху ушли в штамп
SH = eskd.Sheet('A1', mark="ВГ-2026.15.02",
                name="Кондуктор сборочный" + chr(10) + "шлюпочного поста",
                material="Сталь 09Г2С ГОСТ 19281-2014",
                mass=None, scale="1:5",
                sheet_no=1, sheets=1)
fig = SH.fig


def _ax(x, y, w, h):
    return SH.axes_frac(x, y, w, h)


# --- вид сверху
ax = _ax(*[0.035, 0.46, 0.55, 0.44])
ax.set_aspect("equal")
ax.axis("off")
ax.add_patch(Rectangle((-150, -150), PLATE[0], PLATE[1], fc="#eef1f5", ec=INK, lw=2))
ax.text(-150, -265, "Плита основания 1450×720, лист 20, Ст3",
        fontsize=9, color=INK, va="top")
# контур детали в кондукторе
web = [(0, 0), (A, 0), (A, HR - HT), (SC, 0 + 0), (0, 0)]
ax.add_patch(plt.Polygon([(0, HR), (A, HR), (A, HR - HT), (SC, 0), (0, SC)],
                         closed=True, fc="#dbe4ee", ec=ACC, lw=1.8))
ax.text(A * 0.45, HR * 0.62, "кница ВГ-2026.15.01", fontsize=9.5, color=ACC)
# упоры и прижимы
stops = [(0, HR, "упор базовый"), (A, HR, "упор торцевой"),
         (A * 0.62, HR + 60, "прижим винтовой М16"),
         (A * 0.18, -70, "прижим эксцентриковый"),
         (A * 0.78, -70, "прижим эксцентриковый")]
for x, y, t in stops:
    ax.add_patch(Circle((x, y), 26, fc="white", ec=SEA, lw=2))
    ax.annotate(t, (x, y), (x + 40, y + 120 if y > 0 else y - 130), fontsize=8.5,
                color=SEA, arrowprops=dict(arrowstyle="-", color=GRY, lw=0.8))
# поясок в гнезде
ax.add_patch(Rectangle((SC, -TF - 22), A - SC, TF + 22, fc="#cfdae6", ec=SEA, lw=1.4))
ax.text(A * 0.45, -108, "гнездо пояска 80×10 с зазором 1 мм под шов",
        fontsize=8.5, color=SEA, ha="center")
for i in range(6):
    xx = 60 + i * (A - 120) / 5
    ax.add_patch(Circle((xx, HR + 130), 12, fc="white", ec=INK, lw=1.2))
ax.text(A * 0.5, HR + 250, "отв. ⌀24 под пальцы фиксации, шаг 214",
        fontsize=8.5, color=INK, ha="center")
ax.annotate("", (-150, -205), (PLATE[0] - 150, -205),
            arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
ax.text((PLATE[0] - 300) / 2, -198, "%.0f" % PLATE[0], ha="center", fontsize=9, va="bottom")
ax.annotate("", (PLATE[0] - 120, -150), (PLATE[0] - 120, PLATE[1] - 150),
            arrowprops=dict(arrowstyle="<->", color=INK, lw=0.9))
ax.text(PLATE[0] - 100, (PLATE[1] - 300) / 2, "%.0f" % PLATE[1], rotation=90,
        fontsize=9, va="center")
ax.text(0, PLATE[1] + 60, "Вид сверху", fontsize=12, color=INK, fontweight="bold")
ax.set_xlim(-260, PLATE[0] + 60)
ax.set_ylim(-320, PLATE[1] + 130)

# --- разрез по прижиму
ax2 = _ax(*[0.61, 0.52, 0.36, 0.38])
ax2.set_aspect("equal")
ax2.axis("off")
ax2.add_patch(Rectangle((-260, -20), 520, 20, fc="#eef1f5", ec=INK, lw=1.6))
ax2.add_patch(Rectangle((-TW / 2, 0), TW, 300, fc="#dbe4ee", ec=ACC, lw=1.6))
ax2.add_patch(Rectangle((-BF / 2, -20 - TF), BF, TF, fc="#dbe4ee", ec=ACC, lw=1.6))
ax2.add_patch(Rectangle((-200, 0), 120, 60, fc="#d6dde6", ec=SEA, lw=1.4))
ax2.add_patch(Rectangle((80, 0), 120, 60, fc="#d6dde6", ec=SEA, lw=1.4))
ax2.plot([0, 0], [300, 420], color=SEA, lw=6)
ax2.add_patch(Rectangle((-70, 420), 140, 28, fc="#d6dde6", ec=SEA, lw=1.4))
ax2.text(90, 430, "винт М16 с рукояткой", fontsize=8.5, color=SEA)
ax2.text(-250, 90, "призматические\nупоры 120×60", fontsize=8.5, color=SEA)
ax2.text(210, -60, "плита основания, лист 20", fontsize=8.5, color=INK)
ax2.text(20, 200, "стенка кницы", fontsize=8.5, color=ACC)
ax2.text(-295, -20 - TF - 30, "поясок в гнезде", fontsize=8.5, color=ACC)
ax2.text(-260, 470, "Разрез по прижиму", fontsize=12, color=INK, fontweight="bold")
ax2.set_xlim(-300, 360)
ax2.set_ylim(-120, 520)

# --- маршрутная карта
ax3 = _ax(*[0.035, 0.035, 0.93, 0.40])
ax3.axis("off")
ax3.text(0, 1.0, "Маршрутная карта изготовления кницы ВГ-2026.15.01",
         fontsize=12, fontweight="bold", color=INK, transform=ax3.transAxes)
rows = [
    ["005", "Заготовительная", "Лазерная резка контура и отв. ⌀120 из листа 10 ГОСТ 19903",
     "Станок лазерной резки 4 кВт", "6"],
    ["010", "Заготовительная", "Резка полосы 80×10 в размер 1150", "Гильотина", "2"],
    ["015", "Слесарная", "Зачистка кромок, снятие грата, притупление 1×45°",
     "Шлифмашина", "5"],
    ["020", "Сборочная", "Установка стенки и пояска в кондуктор ВГ-2026.15.90",
     "Кондуктор сварочный", "4"],
    ["025", "Сварочная", "Прихватка пояска по 4 точкам", "Полуавтомат МП-350", "3"],
    ["030", "Сварочная", "Шов угловой К6 двусторонний по всей длине пояска",
     "Полуавтомат МП-350", "11"],
    ["035", "Контрольная", "Визуально-измерительный контроль шва по РД 03-606-03",
     "Шаблон УШС-3", "4"],
    ["040", "Слесарная", "Правка после сварки, контроль плоскостности 1 мм на 1000",
     "Плита поверочная", "6"],
    ["045", "Малярная", "Обезжиривание, грунт ЭП-0199 40 мкм, эмаль ЭП-1155 2 слоя",
     "Камера окраски", "8"],
    ["050", "Контрольная", "Приёмка ОТК, маркировка, комплектация",
     "—", "3"],
]
tbl = ax3.table(cellText=rows,
                colLabels=["№", "Операция", "Содержание", "Оборудование", "t, мин"],
                colWidths=[0.05, 0.14, 0.47, 0.22, 0.07],
                loc="upper center", cellLoc="left")
tbl.auto_set_font_size(False)
tbl.set_fontsize(8.6)
tbl.scale(1, 1.42)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#ccd3dd")
    cell.set_linewidth(0.5)
    if r == 0:
        cell.set_facecolor("#eef1f5")
        cell.set_text_props(fontweight="bold")
    if c in (0, 4):
        cell.set_text_props(ha="center")
tot = sum(int(r[4]) for r in rows)
ax3.text(0, -0.05, "Штучное время %d мин на деталь, партия 26 шт — %.1f нормо-часа. "
         "Кондуктор окупается с первой партии: без него только сборка и правка "
         "занимают втрое больше." % (tot, tot * 26 / 60.0),
         fontsize=9.5, color="#2c3a4e", transform=ax3.transAxes)
SH.save(os.path.join(OUT, "04_кондуктор_и_техпроцесс.png"))
print("готово")
