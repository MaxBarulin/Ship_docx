# -*- coding: utf-8 -*-
"""Лист модельного ряда - три версии на одном корпусе."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.patches import Rectangle
from lib import gorizont as G, gorizont_ga as GA, gorizont_range as R

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "схемы")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"axes.unicode_minus": False, "font.family": "DejaVu Sans", "font.size": 9,
                     "figure.facecolor": "white", "savefig.facecolor": "white"})
INK, ACC, SEA, GRY, GRN = "#16202f", "#b02634", "#1c5c8a", "#8d97a6", "#1f7a5a"
COL = {"эконом": "#8fb8d8", "семейная": "#a9c9e2", "стандарт": "#4f8fbe", "стандарт М4": "#3a7aae", "бизнес": "#1c5c8a", "люкс": "#0d3350"}

rows = R.table()
fig = plt.figure(figsize=(16.8, 9.6))
_R = fig.canvas.get_renderer()


def перенос(s, ширина_доля, fontsize):
    """Перенос по словам под ширину в долях фигуры - по измеренному тексту, а не по числу знаков."""
    предел = ширина_доля * fig.bbox.width
    строки, тек = [], ""
    for слово in s.split():
        проба = (тек + " " + слово).strip()
        t_ = fig.text(0, 0, проба, fontsize=fontsize)
        w_ = t_.get_window_extent(_R).width
        t_.remove()
        if тек and w_ > предел:
            строки.append(тек); тек = слово
        else:
            тек = проба
    if тек:
        строки.append(тек)
    return строки

fig.suptitle("Модельный ряд «Волжский Горизонт» - три версии на одном корпусе",
             fontsize=18, fontweight="bold", x=0.012, ha="left", y=0.975)
for k_, стр in enumerate(перенос("Корпус, набор, энергетическая установка, системы и все расчёты общие. "
                                  "Меняется только насыщение жилых ярусов - перегородки переставляются по сетке "
                                  "шпаций 550 мм, магистрали и шахты не трогаются.", 0.80, 10.5)):
    fig.text(0.012, 0.938 - k_ * 0.024, стр, fontsize=10.5, color="#56627a")
fig.text(0.988, 0.962, "ВГ-2026 · модельный ряд", fontsize=10, color="#56627a", ha="right")

# --- полосы кают ------------------------------------------------------------
# название версии - над полосой, выноски узких сегментов - под ней в два уровня:
# над полосой они ложились на название версии
ШАГ = 1.7
ax = fig.add_axes([0.035, 0.44, 0.62, 0.44])
ax.set_xlim(0, max(s["cabin_area"] for s in rows) * 1.13)
ax.set_ylim(-0.75, (len(rows) - 1) * ШАГ + 1.05)
ax.invert_yaxis()
ax.axis("off")
for i_, s in enumerate(rows):
    i = i_ * ШАГ
    x, narrow = 0.0, 0
    for k in ("эконом", "семейная", "стандарт", "стандарт М4", "бизнес", "люкс"):
        n = s["cabins"].get(k, 0)
        if not n:
            continue
        w = n * R._площадь(k)
        ax.add_patch(Rectangle((x, i - 0.26), w, 0.52, facecolor=COL[k],
                               edgecolor="white", lw=1.4))
        lab = "%s - %d кают, %d мест" % (k, n, n * GA.КАЮТЫ[k]["мест"])
        if w >= 215:
            ax.text(x + w / 2, i, lab.replace(" - ", chr(10)).replace(", ", " · "),
                    ha="center", va="center", color="white", fontsize=9.5)
        else:
            dy = 0.40 + 0.24 * (narrow % 2)
            ax.plot([x + w / 2, x + w / 2], [i + 0.26, i + dy - 0.04],
                    color=COL[k], lw=0.9)
            ax.text(x + w / 2, i + dy, lab, ha="center", va="top",
                    color=COL[k], fontsize=8.5)
            narrow += 1
        x += w
    ax.text(0, i - 0.36, "%s  «%s»" % (s["code"], s["name"]),
            fontsize=12, fontweight="bold", color=INK, va="bottom")
    ax.text(x + 18, i, "%.0f м²" % s["cabin_area"], va="center", fontsize=10, color=GRY)
ax.text(0, (len(rows) - 1) * ШАГ + 1.0, "Справа от полосы - площадь пассажирских кают, м²",
        fontsize=9.5, color=GRY)

# --- столбики мест ----------------------------------------------------------
ax2 = fig.add_axes([0.70, 0.44, 0.275, 0.44])
xs = range(len(rows))
ax2.bar([i - 0.2 for i in xs], [s["berths"] for s in rows], width=0.38,
        color=SEA, label="пассажирских мест")
ax2.bar([i + 0.2 for i in xs], [s["m4"] * 10 for s in rows], width=0.38,
        color=GRN, alpha=0.75, label="мест М4 (x10)")
ax2.axhline(200, color=ACC, lw=1.2, ls="--")
ax2.text(len(rows) - 0.55, 206, "КЗ - не менее 200 мест", fontsize=8.5, color=ACC, ha="right")
for i, s in enumerate(rows):
    ax2.text(i - 0.2, s["berths"] + 6, str(s["berths"]), ha="center", fontsize=9, color=SEA)
    ax2.text(i + 0.2, s["m4"] * 10 + 6, str(s["m4"]), ha="center", fontsize=9, color=GRN)
    ax2.text(i, -34, "на борту %d" % s["onboard"], ha="center", fontsize=9, color=GRY)
ax2.set_xticks(list(xs))
ax2.set_xticklabels([s["name"] for s in rows], fontsize=10)
ax2.set_ylim(0, 430)
ax2.legend(fontsize=8.5, loc="upper left")
ax2.set_title("Пассажирских мест и мест М4 (норма 5 %)", fontsize=10, loc="left")
for sp in ("top", "right"):
    ax2.spines[sp].set_visible(False)

# --- таблица ----------------------------------------------------------------
ax3 = fig.add_axes([0.035, 0.055, 0.94, 0.33])
ax3.axis("off")
head = ["Версия", "Шифр", "Кают", "Мест", "Экипаж", "На борту", "Площадь кают, м²",
        "м² на место", "Δ площади, м²", "Мест М4", "КЗ ≥ 200"]
w = [0.085, 0.075, 0.048, 0.048, 0.055, 0.062, 0.10, 0.075, 0.105, 0.10, 0.065]
x0 = 0.0
for hname, ww in zip(head, w):
    ax3.text(x0 + 0.004, 0.93, hname, fontsize=9.5, fontweight="bold", color=INK)
    x0 += ww
ax3.plot([0, sum(w)], [0.885, 0.885], color=INK, lw=1.2)
for i, s in enumerate(rows):
    y = 0.82 - i * 0.14
    vals = [s["name"], s["code"], s["n_cabins"], s["berths"], s["crew"], s["onboard"],
            "%.1f" % s["cabin_area"], "%.2f" % s["area_per_berth"],
            "%+.1f" % s["area_delta"], "%d %s" % (s["m4"], "ок" if s["m4_ok"] else "мало"),
            "да" if s["kz_ok"] else "НЕТ"]
    x0 = 0.0
    for v, ww in zip(vals, w):
        ax3.text(x0 + 0.004, y, str(v), fontsize=10,
                 color=INK if i == 1 else "#3d4a5e",
                 fontweight="bold" if i == 1 else "normal")
        x0 += ww
    ax3.plot([0, sum(w)], [y - 0.035, y - 0.035], color="#dde2ea", lw=0.8)
    for k_, стр in enumerate(перенос(s["idea"] + ". " + s["note"], 0.93, 9)):
        ax3.text(0.004, y - 0.062 - k_ * 0.028, стр, fontsize=9, color=GRY)
ax3.set_xlim(0, sum(w))
ax3.set_ylim(0.40, 1.0)
for k_, стр in enumerate(перенос("Базовая версия - «Классик» - по ней выполнены все чертежи, расчёты и рендеры. "
                                  "Спасательные средства - надувные плоты на всех, независимо от версии. "
                                  "Версии «Эконом» и «Премиум» отличаются только перегородками жилых палуб.", 0.94, 9.5)):
    fig.text(0.035, 0.036 - k_ * 0.02, стр, fontsize=9.5, color="#56627a")
p = os.path.join(OUT, "модельный_ряд.png")
fig.savefig(p, dpi=150)
print(p)
