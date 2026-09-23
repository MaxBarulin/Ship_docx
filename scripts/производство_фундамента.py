# -*- coding: utf-8 -*-
"""Производство узла ВГ-2026.46.00: мощности, кооперация, участок, освоение (КЗ 4.3–4.6).

    python scripts/производство_фундамента.py

Всё — из lib.gorizont_twistlock: трудоёмкость по маршрутам, свободный фонд цехов,
цепочка кооперации, планировка участков и график, привязанный к дорожной карте Лены.
Картинки — renders/горизонт_2026/схемы/07…10_узел_*.png.
"""
import os, sys, textwrap, datetime as dt
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.patches import FancyBboxPatch, FancyArrowPatch, Rectangle
from lib import gorizont_twistlock as T, gorizont_build as B

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "схемы")
os.makedirs(OUT, exist_ok=True)
plt.rcParams.update({"font.family": "DejaVu Sans", "font.size": 9})
INK, INK2, MUTED, GRID, SURF = "#0b0b0b", "#52514e", "#8a8983", "#e6e5e0", "#fcfcfb"
#: Цвет цеха — категориальная палитра в фиксированном порядке по ходу процесса (проверена на дальтонизм).
ЦЕХ = {"ЛЦ": "#2a78d6", "ТО": "#eb6834", "ОТК": "#1baf7a", "МЦ": "#eda100", "СЦ": "#e87ba4", "К": "#008300"}
ИМЯ = {"ЛЦ": "литейный цех", "ТО": "термический участок", "ОТК": "служба качества", "МЦ": "механический цех",
       "СЦ": "сборочный участок", "К": "кооперация"}


def ф(x, nd=0):
    return (("%." + str(nd) + "f") % x).replace(".", ",")


def мощности():
    м = T.мощности()
    fig, ax = plt.subplots(figsize=(10.5, 4.4), dpi=150)
    fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    for i, r in enumerate(м):
        c = ЦЕХ[r["цех"]]
        ax.barh(i, r["свободно"], height=0.56, color="white", edgecolor=MUTED, lw=0.8, zorder=2)
        ax.barh(i, r["часы"], height=0.56, color=c, edgecolor=SURF, lw=2, zorder=3)
        ax.text(r["свободно"] + 12, i, "%s н·ч из %s свободных — %s %%" % (ф(r["часы"]), ф(r["свободно"]), ф(r["доля"], 1)),
                va="center", fontsize=8.5, color=INK)
    ax.set_yticks(range(len(м)))
    ax.set_yticklabels(["%s — %s" % (r["цех"], ИМЯ[r["цех"]]) for r in м], color=INK)
    ax.invert_yaxis()
    ax.set_xlabel("нормо-часы на партию %d шт (заливка — трудоёмкость, контур — свободный годовой фонд цеха)" % T.программа()["всего"], color=INK2)
    ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlim(0, max(r["свободно"] for r in м) * 1.55)
    ax.set_title("Загрузка своих мощностей партией фундаментов: хватает с запасом", loc="left", color=INK, fontsize=11)
    fig.text(0.01, 0.01, "Фонд рабочего места %s ч в год в одну смену; текущая загрузка цехов другими заказами — 55…75 %%." % ф(T.ФОНД_Ч),
             fontsize=7.5, color=INK2)
    fig.tight_layout(rect=(0, 0.04, 1, 1))
    p = os.path.join(OUT, "10_узел_мощности.png"); fig.savefig(p, facecolor=SURF); plt.close(fig)
    return p


def кооперация():
    fig, ax = plt.subplots(figsize=(15, 7.2), dpi=150)
    fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    ax.set_xlim(0, 150); ax.set_ylim(-2, 70); ax.axis("off")
    п = T.программа()
    узлы = {
        "МТО": (9, 46, "МТО верфи", "лом, ферросплавы,\nпесок, смола, краска", None),
        "ЛЦ": (30, 46, "Литейный цех", "стержни, формовка ХТС,\nплавка, выбивка", "ЛЦ"),
        "ТО": (51, 46, "Термический участок", "нормализация\n+ отпуск", "ТО"),
        "ОТК": (72, 46, "ОТК", "ВИК, МПД, РК,\nмеханика и KCU", "ОТК"),
        "МЦ": (93, 46, "Механический цех", "корпус — 2 установки,\nзамок — токарная, ОЦ", "МЦ"),
        "ТДЦ": (114, 46, "Цинкование ТДЦ", "кооперация,\n40 мкм", "К"),
        "СЦ": (135, 46, "Сборочный участок", "сборка, стенд 250 кН,\nупаковка по 6 шт", "СЦ"),
        "КУЗ": (93, 22, "Кузнечный цех", "кооперация: поковки\n40Х, КП 590", "К"),
        "МТО2": (114, 22, "МТО верфи", "крепёж А4-80, фиксаторы,\nСТЭФ, герметик", None),
        "СКЛ": (135, 4, "Склад МСЧ", "комплекты на слот", None),
        "КОРП": (51, 4, "Корпусный цех", "подкладные листы АМг5\nна настил при постройке", None),
        "СУД": (93, 4, "Судно: солнечная палуба", "установка %d узлов\nв достройку" % п["на_судно"], None),
    }
    W, Hh = 16.5, 10.0
    for k, (x, y, tt, d, цех) in узлы.items():
        c = ЦЕХ.get(цех, MUTED) if цех else MUTED
        ax.add_patch(FancyBboxPatch((x - W / 2, y - Hh / 2), W, Hh, boxstyle="round,pad=0.3,rounding_size=1.2",
                                    facecolor="white", edgecolor=c, lw=2.2 if цех else 1.0, zorder=2))
        ax.text(x, y + 2.4, tt, ha="center", va="center", fontsize=8.0, color=INK, weight="bold", zorder=3)
        ax.text(x, y - 1.8, d, ha="center", va="center", fontsize=7.0, color=INK2, zorder=3, linespacing=1.15)
    def край(x, y, dx, dy):
        L = (dx * dx + dy * dy) ** 0.5
        ux, uy = dx / L, dy / L
        tt = min((W / 2 + 0.8) / abs(ux) if ux else 1e9, (Hh / 2 + 0.8) / abs(uy) if uy else 1e9)
        return x + ux * tt, y + uy * tt
    def arrow(a, b, txt):
        xa, ya = узлы[a][:2]; xb, yb = узлы[b][:2]
        p0, p1 = край(xa, ya, xb - xa, yb - ya), край(xb, yb, xa - xb, ya - yb)
        ax.add_patch(FancyArrowPatch(p0, p1, arrowstyle="-|>", mutation_scale=11, color=INK2, lw=1.0, zorder=1))
        mx, my = (p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2
        гор = abs(p1[0] - p0[0]) > abs(p1[1] - p0[1])
        if гор:
            # между блоками всего несколько единиц — подпись над рядом блоков, по оси зазора, в одну строку
            ax.text(mx, my + Hh / 2 + 1.0, txt, ha="center", va="bottom", fontsize=6.6, color=INK2)
            ax.plot([mx, mx], [my + 0.8, my + Hh / 2 + 0.8], color=INK2, lw=0.4, ls=":", zorder=1)
        else:
            ax.text(mx + 1.2, my, "\n".join(textwrap.wrap(txt, 12)), ha="left", va="center", fontsize=6.6,
                    color=INK2, linespacing=1.05)
    arrow("МТО", "ЛЦ", "шихта, смесь")
    arrow("ЛЦ", "ТО", "%d отливок" % п["всего"])
    arrow("ТО", "ОТК", "садки по 40")
    arrow("ОТК", "МЦ", "годные, паспорт")
    arrow("МЦ", "ТДЦ", "корпуса, замки")
    arrow("ТДЦ", "СЦ", "детали с ТДЦ")
    arrow("КУЗ", "МЦ", "%d поковок" % п["всего"])
    arrow("МТО2", "СЦ", "покупные изделия")
    arrow("СЦ", "СКЛ", "%d узлов" % (п["на_судно"] + п["зип"]))
    arrow("СКЛ", "СУД", "комплекты")
    arrow("КОРП", "СУД", "листы на настиле")
    ax.text(0, 67.5, "Производственная цепочка и кооперация: фундамент-замок ВГ-2026.46.00", fontsize=12, color=INK, weight="bold")
    ax.text(0, 64.2, "Программа на головное судно: %d на палубу + %d ЗИП + %d на разрушающие испытания = %d отливок; установочная партия — %d шт." % (
        п["на_судно"], п["зип"], п["разрушающие"], п["всего"], п["установочная"]), fontsize=8.5, color=INK2)
    for i, цех in enumerate(("ЛЦ", "ТО", "ОТК", "МЦ", "СЦ", "К")):
        y0 = 30.0 - i * 3.0
        ax.add_patch(Rectangle((1, y0), 2.0, 2.0, facecolor="white", edgecolor=ЦЕХ[цех], lw=2.0))
        ax.text(3.8, y0 + 1.0, ИМЯ[цех], fontsize=7.5, va="center", color=INK)
    ax.text(1, 11.0, "Серая рамка — службы верфи вне узла;\nцветная — цех, где идёт операция.", fontsize=7.5, color=INK2, va="top")
    fig.tight_layout()
    p = os.path.join(OUT, "07_узел_кооперация.png"); fig.savefig(p, facecolor=SURF); plt.close(fig)
    return p


def участок():
    fig, ax = plt.subplots(figsize=(14, 11.5), dpi=150)
    fig.patch.set_facecolor(SURF); ax.set_facecolor(SURF)
    ax.set_aspect("equal"); ax.axis("off")
    mx, my, mw, mh = T.МЕХ_ПРОЛЁТ
    ax.add_patch(Rectangle((0, 0), 48, 18, facecolor="none", edgecolor=INK, lw=1.6))
    ax.add_patch(Rectangle((mx, my), mw, mh, facecolor="none", edgecolor=INK, lw=1.6))
    for x in range(0, 49, 6):
        ax.plot([x, x], [-0.5, 18.5], color=GRID, lw=0.6, zorder=0); ax.text(x, 18.9, "%d" % (x // 6 + 1), ha="center", fontsize=7, color=MUTED)
    центры = {}
    for цех, имя, x, y, w, h in T.УЧАСТОК:
        c = ЦЕХ[цех]
        ax.add_patch(Rectangle((x + 0.15, y + 0.15), w - 0.3, h - 0.3, facecolor="white", edgecolor=c, lw=1.8, zorder=2))
        ax.text(x + w / 2, y + h / 2 + 0.2, "\n".join(textwrap.wrap(имя, 16)), ha="center", va="center", fontsize=6.4, color=INK, zorder=6,
                linespacing=1.1, bbox=dict(boxstyle="round,pad=0.12", facecolor="white", edgecolor="none", alpha=0.85))
        ax.text(x + 0.45, y + h - 0.55, "%s м²" % ф(w * h), ha="left", va="top", fontsize=6.0, color=INK2, zorder=6)
        центры[имя] = (x + w / 2, y + h / 2)
    # подпись потока — на вершине дуги своей стрелки (arc3: середина хорды + rad/2 по нормали), а не в середине
    # хорды: у соседних стрелок хорды почти совпадали, и плашка одной подписи закрывала другую
    занято = []
    for a, b, txt in T.ПОДВОД_УЧАСТКА:
        (xa, ya), (xb, yb) = центры[a], центры[b]
        ax.add_patch(FancyArrowPatch((xa, ya), (xb, yb), arrowstyle="-|>", mutation_scale=10, color=MUTED, lw=1.0, ls=(0, (4, 2)),
                                     shrinkA=18, shrinkB=18, connectionstyle="arc3,rad=0.15", zorder=3))
        px, py = (xa + xb) / 2 + 0.075 * (yb - ya), (ya + yb) / 2 - 0.075 * (xb - xa)
        while any(abs(px - qx) < 0.35 * (len(txt) + len(qt)) * 0.18 and abs(py - qy) < 0.8 for qx, qy, qt in занято):
            py += 0.8
        занято.append((px, py, txt))
        ax.text(px, py, txt, fontsize=6.3, color=INK2, ha="center", va="center", zorder=7,
                bbox=dict(boxstyle="round,pad=0.1", facecolor=SURF, edgecolor="none"))
    м = T.МАРШРУТ_УЧАСТКА
    for i, (a, b) in enumerate(zip(м, м[1:]), 1):
        (xa, ya), (xb, yb) = центры[a], центры[b]
        ax.add_patch(FancyArrowPatch((xa, ya), (xb, yb), arrowstyle="-|>", mutation_scale=12, color="#c0392b", lw=1.4,
                                     shrinkA=16, shrinkB=16, connectionstyle="arc3,rad=0.1", zorder=4, alpha=0.9))
        ax.text((xa + xb) / 2, (ya + yb) / 2, str(i), fontsize=7, color="white", ha="center", va="center", zorder=8,
                bbox=dict(boxstyle="circle,pad=0.2", facecolor="#c0392b", edgecolor="none"))
    ax.text(0, 20.2, "Литейный пролёт 48 × 18 м, кран 5 т; колонны через 6 м", fontsize=9, color=INK)
    ax.text(mx + mw / 2, -2.0, "проезд 4 м — электрокар, тара по 6 отливок", ha="center", fontsize=7.5, color=INK2)
    ax.text(mx + mw / 2, my - 1.2, "Механический цех: участок %s × %s м" % (ф(mw), ф(mh, 1)), ha="center", fontsize=9, color=INK)
    s_л = sum(w * h for ц, _, _, _, w, h in T.УЧАСТОК if ц in ("ЛЦ", "ТО", "ОТК"))
    s_м = sum(w * h for ц, _, _, _, w, h in T.УЧАСТОК if ц in ("МЦ", "СЦ"))
    ax.text(0, -21.0, "Площадь под оборудованием: литейный пролёт %s м², механический %s м². Красные стрелки 1…%d — маршрут корпуса; пунктир — подвод стержней," % (
        ф(s_л), ф(s_м), len(м) - 1), fontsize=8, color=INK2)
    ax.text(0, -22.4, "металла, смеси и замков. Участки действующие: под узел добавляются модельный комплект, ящик, приспособление ЧПУ и стенд 250 кН.", fontsize=8, color=INK2)
    ax.text(0, -23.8, "Планировка — по типовой литейке со стальным литьём в ХТС.", fontsize=8, color=INK2)
    x0 = 0
    for цех in ("ЛЦ", "ТО", "ОТК", "МЦ", "СЦ"):
        ax.add_patch(Rectangle((x0, -26.0), 0.9, 0.9, facecolor="white", edgecolor=ЦЕХ[цех], lw=1.8))
        ax.text(x0 + 1.3, -25.55, ИМЯ[цех], fontsize=7.5, va="center", color=INK)
        x0 += 2.0 + len(ИМЯ[цех]) * 0.42
    ax.set_xlim(-0.5, 48.5); ax.set_ylim(-26.8, 21.5)
    ax.set_title("Компоновка производства фундаментов: оборудование, площади, поток деталей", loc="left", color=INK, fontsize=12)
    fig.tight_layout()
    p = os.path.join(OUT, "08_узел_участок.png"); fig.savefig(p, facecolor=SURF); plt.close(fig)
    return p


def освоение():
    г = T.график()
    карта = {t[0]: t for t in B.ЛЕНА}
    фон = [(24, "7.4 Оснастка"), (38, "10.4 Изделия МСЧ"), (41, "10.6 Корпус на стапеле"), (45, "11 Достройка")]
    fig = plt.figure(figsize=(15, 8.6), dpi=150)
    fig.patch.set_facecolor(SURF)
    ax = fig.add_axes([0.30, 0.40, 0.66, 0.50]); ax.set_facecolor(SURF)
    цвет = lambda кто: ЦЕХ["ЛЦ"] if "ЛЦ" in кто else ЦЕХ["МЦ"] if "МЦ" in кто else ЦЕХ["ОТК"] if "ОТК" in кто else MUTED
    строки = [(e["этап"], e["начало"], e["конец"], цвет(e["кто"]), e["кто"]) for e in г]
    n = len(строки)
    for i, (имя, d0, d1, c, кто) in enumerate(строки):
        ax.barh(i, (d1 - d0).days + 1, left=mdates.date2num(d0), height=0.55, color=c, edgecolor=SURF, lw=2, zorder=3)
        поздно = d1 > dt.date(2028, 12, 1)
        ax.text(mdates.date2num(d0 if поздно else d1) + (-6 if поздно else 6), i, "%s — %s · %s" % (d0.strftime("%d.%m.%y"), d1.strftime("%d.%m.%y"), кто),
                va="center", ha="right" if поздно else "left", fontsize=7.2, color=INK2)
    for j, (ид, имя) in enumerate(фон):
        t = карта[ид]; d0 = t[3]; d1 = B._раб(d0, t[4])
        ax.axvspan(mdates.date2num(d0), mdates.date2num(d1), color="#f0efec", zorder=0)
        ax.text(mdates.date2num(d0) + 3, -0.75 - 0.42 * (j % 2), "карта постройки: " + имя, fontsize=7, color=MUTED, va="bottom")
    ax.set_yticks(range(n)); ax.set_yticklabels([s[0] for s in строки], fontsize=8, color=INK)
    ax.set_ylim(n - 0.5, -1.4)
    ax.xaxis_date(); ax.xaxis.set_major_locator(mdates.MonthLocator(interval=3)); ax.xaxis.set_major_formatter(mdates.DateFormatter("%m.%Y"))
    ax.grid(axis="x", color=GRID, lw=0.7, zorder=0)
    for s in ("top", "right"):
        ax.spines[s].set_visible(False)
    ax.set_xlim(mdates.date2num(dt.date(2026, 12, 1)), mdates.date2num(dt.date(2029, 6, 1)))
    ax.tick_params(axis="x", labelsize=7.5, colors=INK2)
    fig.text(0.02, 0.95, "Сроки подготовки и освоения производства фундаментов, программа выпуска и испытаний", fontsize=12, color=INK, weight="bold")
    fig.text(0.02, 0.92, "Привязка к дорожной карте постройки судна: серия готова к %s — за год до начала достройки." % next(
        e for e in г if e["этап"].startswith("Мехобработка, покрытие"))["конец"].strftime("%d.%m.%Y"), fontsize=8.5, color=INK2)
    п = T.программа()
    н = T.нагрузки()
    лев = ["Программа выпуска на головное судно",
           "  на палубу — %d (18 слотов × 4)" % п["на_судно"], "  ЗИП — %d (5 %%)" % п["зип"],
           "  разрушающие испытания — %d" % п["разрушающие"], "  всего отливок и замков — %d" % п["всего"],
           "  установочная партия — %d, серийная — %d" % (п["установочная"], п["серийная"]),
           "", "Рабочая нагрузка на опору (SWL)",
           "  отрыв %s · сжатие %s · сдвиг %s кН" % (ф(н["SWL"]["отрыв"]), ф(н["SWL"]["сжатие"]), ф(н["SWL"]["сдвиг"])),
           "  предельная: %s · %s · %s кН" % (ф(н["предельный"]["отрыв"]), ф(н["предельный"]["сжатие"]), ф(н["предельный"]["сдвиг"]))]
    fig.text(0.02, 0.31, "\n".join(лев), fontsize=8.5, color=INK, va="top", linespacing=1.45)
    прав = ["Программа испытаний (ВГ-2026.46.00 ПМ)"] + ["\n   ".join(textwrap.wrap("• %s: %s" % (a, b), 105)) for a, b in T.ИСПЫТАНИЯ]
    fig.text(0.36, 0.31, "\n".join(прав), fontsize=8.2, color=INK, va="top", linespacing=1.45)
    x0 = 0.30
    for цех, t in (("ЛЦ", "литейный цех"), ("МЦ", "механический цех"), ("ОТК", "ОТК и РРР")):
        fig.patches.append(Rectangle((x0, 0.345), 0.012, 0.016, transform=fig.transFigure, facecolor=ЦЕХ[цех], edgecolor="none"))
        fig.text(x0 + 0.016, 0.353, t, fontsize=7.8, color=INK, va="center"); x0 += 0.11
    fig.patches.append(Rectangle((x0, 0.345), 0.012, 0.016, transform=fig.transFigure, facecolor=MUTED, edgecolor="none"))
    fig.text(x0 + 0.016, 0.353, "ПБ, ТУ, корпусный и достроечный цеха", fontsize=7.8, color=INK, va="center")
    p = os.path.join(OUT, "09_узел_освоение.png"); fig.savefig(p, facecolor=SURF); plt.close(fig)
    return p


def main():
    for f in (мощности, кооперация, участок, освоение):
        print("  ", os.path.relpath(f(), ROOT))


if __name__ == "__main__":
    main()
