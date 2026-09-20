# -*- coding: utf-8 -*-
"""Планировки кают: планы всех типов с размерами и проверкой эргономики.

Планы рисуются по тому же списку объёмов, по которому собирается модель,
поэтому чертёж не может разойтись с судном. Под каждым планом — ширина
прохода, тип санузла и число мест, а внизу листа сводная таблица с
нормами и фактом.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle, Circle
from lib import gorizont_cabins as C
from lib import eskd

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 8,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
INK, ACC, SEA, GRY, GRN = "#16202f", "#b02634", "#1c5c8a", "#9aa4b4", "#1f7a5a"

# что и как заливать на плане
FILL = [
    (("су_",), "#dbe7f0", "#7f95ab"),
    (("унитаз", "душ", "поручень"), "#eef3f8", "#7f95ab"),
    (("койка", "матрас", "одеяло", "подушка", "кровать", "изголовье",
      "спинка", "бортик"), "#f3e6de", "#b8896d"),
    (("трап_",), "#e6e9ee", "#8792a3"),
    (("шкаф",), "#e9e2d4", "#a2916b"),
    (("стол", "полка_стола", "консоль", "кресло", "тумба"), "#e7efe8", "#7ca386"),
    (("диван", "банкетка", "ковёр", "столик"), "#efe7ef", "#a08aa0"),
    (("окно", "стекло"), "#d8ecf6", "#5f93b3"),
    (("дверь",), "#f0e7d8", "#b09a6b"),
]
SKIP = ("пол", "подволок", "светильник", "карниз", "штора", "телевизор",
        "зеркало", "картина", "су_зеркало", "лампа", "книга", "ваза",
        "цветы", "поднос", "бокал", "торшер", "зелень", "экран")


def _style(name):
    for keys, fc, ec in FILL:
        if name.startswith(keys):
            return fc, ec
    return "#eceff3", "#93a0b0"


def plan(ax, name, W, D, kind, win, acc, bal, title):
    parts = C.layout(W, D, kind, win, acc, bal)
    info = C.layout_info(W, D, kind, acc)
    ax.set_aspect("equal")
    ax.axis("off")
    ax.add_patch(Rectangle((0, 0), W, D, facecolor="#fbfcfd", edgecolor=INK,
                           lw=1.6, zorder=1))
    order = sorted(parts, key=lambda q: q.box[4])
    for q in order:
        if q.name.startswith(SKIP):
            continue
        x0, x1, y0, y1, z0, z1 = q.box
        if z0 > 1.75:
            continue
        fc, ec = _style(q.name)
        if q.kind == "cyl":
            ax.add_patch(Circle(((x0 + x1) / 2, (y0 + y1) / 2),
                                max(x1 - x0, y1 - y0) / 2, facecolor=fc,
                                edgecolor=ec, lw=0.5, zorder=3))
        else:
            ax.add_patch(Rectangle((x0, y0), x1 - x0, y1 - y0, facecolor=fc,
                                   edgecolor=ec, lw=0.5, zorder=3))
    if acc:
        for q in parts:
            if q.name == "круг_разворота":
                cx = (q.box[0] + q.box[1]) / 2
                cy = (q.box[2] + q.box[3]) / 2
                ax.add_patch(Circle((cx, cy), 0.75, facecolor="none",
                                    edgecolor=GRN, lw=1.1, ls=(0, (5, 3)),
                                    zorder=6))
    # габариты
    ax.annotate("", (0, -0.20), (W, -0.20),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=0.7))
    ax.text(W / 2, -0.30, "%.0f" % (W * 1000), ha="center", va="top",
            fontsize=7.5, color=INK)
    ax.annotate("", (-0.20, 0), (-0.20, D),
                arrowprops=dict(arrowstyle="<->", color=INK, lw=0.7))
    ax.text(-0.30, D / 2, "%.0f" % (D * 1000), ha="right", va="center",
            rotation=90, fontsize=7.5, color=INK)
    ax.text(0, D + 0.46, title, fontsize=10, color=INK, fontweight="bold")
    ax.text(0, D + 0.22,
            "%.1f м²  ·  %d мест  ·  %s с/у"
            % (info["площадь"], info["мест"],
               {"раздельный": "разд.", "совмещённый": "совм.",
                "общий на блок": "общий"}[info["санузел"]]),
            fontsize=7.5, color="#56627a")
    ax.text(W / 2, -0.52, "проход %.2f м" % info["проход"], ha="center",
            va="top", fontsize=8, color=GRN, fontweight="bold")
    ax.set_xlim(-0.62, W + 0.12)
    ax.set_ylim(-0.86, D + 0.80)
    return info


SHEET = [
    ("эталон_люкс", "Люкс"),
    ("эталон_люкс_дост", "Люкс, доступная"),
    ("эталон_бизнес", "Бизнес"),
    ("эталон_бизнес_дост", "Бизнес, доступная"),
    ("эталон_стандарт", "Стандарт"),
    ("эталон_стандарт_дост", "Стандарт, доступная"),
    ("эталон_эконом", "Эконом"),
    ("эталон_эконом_вн", "Эконом внутренняя"),
    ("эталон_экипаж_2", "Экипаж, двухместная"),
    ("эталон_экипаж_1", "Экипаж, одноместная"),
]
BY_NAME = {t[0]: t for t in C.TYPES}

# Лист по ГОСТ 2.301 с основной надписью 2.104 формы 1:
# заголовок и подпись сверху ушли в штамп
_SHEET = eskd.Sheet('A1', mark="ВГ-2026.20.00",
                    name="Планировки кают" + chr(10) + "пяти категорий",
                    material=None,
                    mass=None, scale="1:25",
                    sheet_no=1, sheets=1)
fig = _SHEET.fig


def _ax(x, y, w, h):
    return _SHEET.axes_frac(x, y, w, h)


def _ftext(x, y, s, **kw):
    """Надпись в долях свободного поля листа, а не всей фигуры."""
    fx0, fy0, fx1, fy1 = _SHEET.field()
    return fig.__class__.text(fig, (fx0 + x * (fx1 - fx0)) / _SHEET.W,
                    (fy0 + y * (fy1 - fy0)) / _SHEET.H, s, **kw)

# Каждый план вписывается в свою ячейку по фактическому соотношению
# сторон: иначе широкий люкс вылезает за ячейку и наезжает на соседа.
COLS, ROWS = 5, 2
CELL_W, CELL_H = 0.192, 0.315
X0, Y0 = 0.016, 0.620
FIG_W, FIG_H = 17.4, 12.0
infos = []
for k, (key, title) in enumerate(SHEET):
    _, W, D, kind, win, acc, bal = BY_NAME[key]
    dw, dh = W + 0.74, D + 1.66
    aw = CELL_W * FIG_W
    ah = CELL_H * FIG_H
    sc = min(aw / dw, ah / dh)
    w = dw * sc / FIG_W
    h = dh * sc / FIG_H
    cx = X0 + (k % COLS) * CELL_W + (CELL_W - w) / 2
    cy = Y0 - (k // COLS) * CELL_H + (CELL_H - h) / 2
    ax = _ax(*[cx, cy, w, h])
    infos.append((title, kind, acc, plan(ax, key, W, D, kind, win, acc, bal,
                                         title)))

ax = _ax(*[0.016, 0.035, 0.968, 0.238])
ax.axis("off")
ax.text(0.0, 1.02, "Проверка эргономики", transform=ax.transAxes, fontsize=11,
        color=INK, fontweight="bold")
rows = []
for title, kind, acc, info in infos:
    need = C.PASS_ACC if acc else C.PASS[kind]
    bed_need = C.BED_SIDE_ACC if acc else C.BED_SIDE
    rows.append([title, "%.1f" % info["площадь"], info["санузел"],
                 info["койка"], str(info["мест"]),
                 "%.2f" % info["проход"], "%.2f" % need,
                 "%.2f" % bed_need, "%.2f" % C.FRONT_BATH,
                 "проходит" if info["проход"] >= need - 1e-9 else "нет"])
tbl = ax.table(cellText=rows,
               colLabels=["Каюта", "Площадь, м²", "Санузел", "Койка", "Мест",
                          "Проход факт, м", "Проход норма, м",
                          "Подход к койке, м", "Перед санузлом, м", "Итог"],
               loc="upper center", cellLoc="center", colLoc="center",
               bbox=[0, 0.0, 1, 0.92])
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
            cell.set_width(0.17)
        if c == 9:
            good = rows[r - 1][9] == "проходит"
            cell.set_text_props(color=GRN if good else ACC, fontweight="bold")
_ftext(0.016, 0.012,
         "Проход проверяется не на глаз: пол разбивается на сетку 50 мм, для "
         "каждой клетки считается запас до ближайшего предмета, и от двери "
         "пускается волна по клеткам, где проход не уже нормы. Если до окна, "
         "койки, шкафа или двери санузла волна не дошла — планировка "
         "бракуется и каюта не собирается (src/lib/gorizont_cabins.py, "
         "check_access).", fontsize=8.2, color="#56627a")
p = os.path.join(OUT, "08_планировки_кают.png")
_SHEET.save(p)
print(p)
