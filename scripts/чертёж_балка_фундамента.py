# -*- coding: utf-8 -*-
"""Чертёж детали ВГ-2026.16.01 «Балка продольная» и маршрутная карта.

Деталь узла ВГ-2026.16.00: сварной тавр, на который опираются лапы
аппаратов установки очистки. Показаны три вида, сечение, разделка кромок
под сварку, таблица технических требований и маршрутная карта изготовления
с нормой времени.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle, Polygon as MPoly
from lib import gorizont_awts as A
from lib import eskd

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
INK, ACC, SEA, GRY, GRN = "#16202f", "#b02634", "#1c5c8a", "#9aa4b4", "#1f7a5a"

HW, TW, BF, TF = A.LONG_SECTION          # 140, 8, 100, 10 мм
L = (A.X1 - A.X0) * 1000.0               # длина балки, мм
N_FEET = 3                               # подушек на балку
HOLE_D = 22.0
B = A.LONG_BEAM


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
        ax.text(x0 + off - 14, (y0 + y1) / 2, txt, rotation=90, ha="right",
                va="center", fontsize=fs, color=INK)
    else:
        ax.annotate("", (x0, y0 + off), (x1, y1 + off),
                    arrowprops=dict(arrowstyle="<->", color=INK, lw=0.7))
        ax.text((x0 + x1) / 2, y0 + off + 8, txt, ha="center", va="bottom",
                fontsize=fs, color=INK)


# Лист А1 по ГОСТ 2.301 с основной надписью 2.104 формы 1: раньше чертёж
# был плакатом — заголовок сверху, подпись справа, ни рамки, ни штампа.
SH = eskd.Sheet("A1", mark="ВГ-2026.16.01",
                name="Балка продольная" + chr(10) + "фундамента",
                material="Сталь %s" % A.STEEL,
                mass=B["mass_kg_m"] * (A.X1 - A.X0), scale="1:5",
                sheet_no=1, sheets=1)
fig = SH.fig


def _ax(x, y, w, h):
    return SH.axes_frac(x, y, w, h)


ax = _ax(*[0.030, 0.640, 0.640, 0.250])
frame(ax, "Вид сбоку")
ax.add_patch(Rectangle((0, 0), L, HW, facecolor="#c9d3e0", edgecolor=INK,
                       lw=1.3))
ax.add_patch(Rectangle((0, HW), L, TF, facecolor="#8c99ab", edgecolor=INK,
                       lw=1.3))
step = L / (N_FEET + 1)
for k in range(1, N_FEET + 1):
    x = step * k
    ax.plot([x, x], [-30, HW + TF + 34], color=SEA, lw=0.6,
            ls=(0, (7, 3, 1, 3)))
    for dx in (-70, 70):
        ax.add_patch(Circle((x + dx, HW + TF / 2), HOLE_D / 2,
                            facecolor="white", edgecolor=INK, lw=0.9))
    ax.text(x, HW + TF + 42, "лапа %d" % k, ha="center", fontsize=7.5,
            color=SEA)
for k in range(1, 5):
    x = L * k / 5
    ax.add_patch(MPoly([(x - 26, 0), (x + 26, 0), (x, 44)], closed=True,
                       facecolor="#dfe5ee", edgecolor=INK, lw=0.7))
ax.text(L * 0.5, -58, "вырезы под рёбра настила, 4 шт", fontsize=7.5,
        color="#56627a", ha="center")
dim(ax, (0, 0), (L, 0), "%.0f" % L, -104)
dim(ax, (step, 0), (step * 2, 0), "%.0f" % step, -166, fs=7.5)
ax.set_xlim(-160, L + 160)
ax.set_ylim(-230, HW + TF + 90)

# ------------------------------------------------------------- сечение -----
ax = _ax(*[0.700, 0.640, 0.140, 0.250])
frame(ax, "Сечение А–А")
ax.add_patch(Rectangle((-TW / 2, 0), TW, HW, facecolor="#c9d3e0",
                       edgecolor=INK, lw=1.4))
ax.add_patch(Rectangle((-BF / 2, HW), BF, TF, facecolor="#8c99ab",
                       edgecolor=INK, lw=1.4))
for s in (-1, 1):
    ax.add_patch(MPoly([(s * TW / 2, HW), (s * (TW / 2 + 9), HW),
                        (s * TW / 2, HW - 9)], closed=True, facecolor=ACC,
                       edgecolor=ACC, lw=0.6))
dim(ax, (-TW / 2, 0), (-TW / 2, HW), "%d" % HW, -62, vert=True)
dim(ax, (-BF / 2, HW + TF), (BF / 2, HW + TF), "%d" % BF, 26)
ax.text(70, HW * 0.5, "стенка %d" % TW, fontsize=8.5, color=INK, va="center")
ax.text(70, HW + TF / 2, "поясок %d" % TF, fontsize=8.5, color=INK,
        va="center")
ax.text(28, HW + TF + 26, "6", fontsize=10, color=ACC, ha="center",
        fontweight="bold")
ax.set_xlim(-130, 190)
ax.set_ylim(-70, HW + TF + 60)

# --------------------------------------------------------- вид сверху ------
ax = _ax(*[0.030, 0.415, 0.640, 0.190])
frame(ax, "Вид сверху")
ax.add_patch(Rectangle((0, -BF / 2), L, BF, facecolor="#8c99ab",
                       edgecolor=INK, lw=1.3))
ax.add_patch(Rectangle((0, -TW / 2), L, TW, facecolor="none", edgecolor=INK,
                       lw=0.7, ls=(0, (5, 3))))
for k in range(1, N_FEET + 1):
    x = step * k
    for dx in (-70, 70):
        for dy in (-32, 32):
            ax.add_patch(Circle((x + dx, dy), HOLE_D / 2, facecolor="white",
                                edgecolor=INK, lw=0.9))
dim(ax, (0, BF / 2), (L, BF / 2), "%.0f" % L, 46)
dim(ax, (step - 70, -BF / 2), (step + 70, -BF / 2), "140", -46, fs=7.5)
ax.text(L * 0.62, -BF / 2 - 58,
        "12 отв. ⌀%.0f под болт М20 кл. 8.8" % HOLE_D, fontsize=8,
        color=INK)
ax.set_xlim(-160, L + 160)
ax.set_ylim(-150, 120)

# ------------------------------------------------- технические требования --
ax = _ax(*[0.700, 0.415, 0.288, 0.190])
ax.axis("off")
ax.text(0.0, 1.0, "Технические требования", transform=ax.transAxes,
        fontsize=11, color=INK, fontweight="bold")
tt = [
    "1. Сталь %s, лист по ГОСТ 19903-2015." % A.STEEL,
    "2. Сварка полуавтоматическая в среде CO\u2082, проволока Св-08Г2С.",
    "3. Поясной шов двусторонний, катет 6 мм, сплошной.",
    "4. Отклонение от прямолинейности не более 1 мм на 1 м длины,",
    "    общее — не более 3 мм.",
    "5. Отверстия сверлить в сборе с подушками поз. 6.",
    "6. Кромки после резки зачистить, притупить 1×45°.",
    "7. Поверхность подготовить до Sa 2½, грунт 2 слоя, 80 мкм.",
    "8. Приёмка — по РД5Р.9083; швы контролировать визуально 100 %,",
    "    выборочно УЗК 10 % длины.",
]
for i, line in enumerate(tt):
    ax.text(0.0, 0.86 - i * 0.092, line, transform=ax.transAxes, fontsize=8.4,
            color="#3c4757")

# ----------------------------------------------------- маршрутная карта ----
ax = _ax(*[0.030, 0.040, 0.640, 0.330])
ax.axis("off")
ax.text(0.0, 1.0, "Маршрутная карта изготовления", transform=ax.transAxes,
        fontsize=11, color=INK, fontweight="bold")
ops = [
    ("005", "Заготовительная", "Плазменная резка стенки и пояска из листа, "
     "раскрой с припуском 2 мм", "УТП-1", 0.35),
    ("010", "Слесарная", "Зачистка кромок, притупление, правка листа",
     "верстак", 0.25),
    ("015", "Сборочная", "Сборка тавра в кондукторе, прихватки через 300 мм",
     "кондуктор СБ-16", 0.40),
    ("020", "Сварочная", "Сварка поясных швов в среде CO\u2082, катет 6, "
     "двусторонний, обратноступенчато", "п/а MIG-350", 0.85),
    ("025", "Правильная", "Правка грибовидности пояска на прессе",
     "пресс 100 тс", 0.30),
    ("030", "Слесарная", "Вырезы под рёбра настила, зачистка швов",
     "УШМ", 0.35),
    ("035", "Сверлильная", "Сверление 12 отв. ⌀22 в сборе с подушками",
     "радиально-сверлильный", 0.45),
    ("040", "Контрольная", "Обмер, визуальный контроль швов, УЗК выборочно",
     "ОТК", 0.20),
    ("045", "Окрасочная", "Дробеструйная очистка Sa 2½, грунт 2 слоя",
     "камера", 0.55),
]
rows = [[n, nm, tx, eq, "%.2f" % t] for n, nm, tx, eq, t in ops]
rows.append(["", "", "Итого на одну балку", "",
             "%.2f" % sum(o[4] for o in ops)])
rows.append(["", "", "На узел, 4 балки", "",
             "%.2f" % (4 * sum(o[4] for o in ops))])
tbl = ax.table(cellText=rows,
               colLabels=["Опер.", "Наименование", "Содержание", "Оборудование",
                          "Т, н·ч"],
               loc="upper center", cellLoc="left", colLoc="center",
               bbox=[0, 0.0, 1, 0.92])
tbl.auto_set_font_size(False)
tbl.set_fontsize(7.6)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#c8cfd9")
    cell.set_linewidth(0.5)
    if r == 0:
        cell.set_facecolor("#eef1f5")
        cell.set_text_props(fontweight="bold", color=INK, ha="center")
    elif r > len(rows) - 2:
        cell.set_facecolor("#f3f6fa")
        cell.set_text_props(fontweight="bold", color=INK)
    if c in (0, 4):
        cell.set_text_props(ha="center")
    cell.set_width({0: 0.07, 1: 0.18, 2: 0.47, 3: 0.19, 4: 0.09}[c])

# ------------------------------------------------------------ параметры ----
ax = _ax(*[0.700, 0.040, 0.288, 0.330])
ax.axis("off")
ax.text(0.0, 1.0, "Расчётные данные детали", transform=ax.transAxes,
        fontsize=11, color=INK, fontweight="bold")
bc = A.beam_check()
wc = A.weld_check()
rows = [
    ["Площадь сечения A", "%.1f см²" % (B["A"] * 1e4)],
    ["Момент инерции I", "%.0f см⁴" % (B["I"] * 1e8)],
    ["Момент сопротивления W", "%.0f см³" % (B["W_min"] * 1e6)],
    ["Погонная масса", "%.1f кг/м" % B["mass_kg_m"]],
    ["Масса детали", "%.1f кг" % (B["mass_kg_m"] * L / 1000.0)],
    ["Расчётный пролёт", "%.2f м" % bc["L"]],
    ["Погонная нагрузка q", "%.1f кН/м" % bc["q"]],
    ["Изгибающий момент M", "%.1f кН·м" % bc["M"]],
    ["Напряжение σ", "%.1f МПа" % bc["sigma"]],
    ["Эквивалентное σ_экв", "%.1f МПа при [σ] %.0f" % (bc["sigma_eq"],
                                                      bc["sigma_allow"])],
    ["Прогиб", "%.3f мм при [f] %.2f" % (bc["f_mm"], bc["f_allow"])],
    ["Касательное в шве", "%.1f МПа при [τ] %.0f" % (wc["tau_flange"],
                                                     wc["allow"])],
]
tbl = ax.table(cellText=rows, loc="upper center", cellLoc="left",
               colLoc="left", bbox=[0, 0.18, 1, 0.76])
tbl.auto_set_font_size(False)
tbl.set_fontsize(8.0)
for (r, c), cell in tbl.get_celld().items():
    cell.set_edgecolor("#c8cfd9")
    cell.set_linewidth(0.5)
    cell.set_width(0.55 if c == 0 else 0.45)
    if c == 0:
        cell.set_facecolor("#f6f8fa")
        cell.set_text_props(color=INK)
ax.text(0.0, 0.0,
        "Случай нагружения — «%s». Сечение подобрано по жёсткости:\n"
        "напряжение вдесятеро ниже допускаемого, зато собственная частота\n"
        "блока отстроена от возбуждения ГДГ и винтов." % bc["case"],
        transform=ax.transAxes, fontsize=8.2, color="#56627a", va="bottom")

# технические требования уже выведены на поле чертежа выше
p = os.path.join(OUT, "07_балка_фундамента.png")
SH.save(p)
print(p)
