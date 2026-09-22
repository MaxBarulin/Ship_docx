# -*- coding: utf-8 -*-
"""Документы узла ВГ-2026.46.00: спецификация и технологический процесс по ЕСКД/ЕСТД.

    python scripts/документы_фундамента.py

В renders/горизонт_2026/чертежи/:
  46_спецификация_лист1…      — ГОСТ 2.106-2019, из gorizont_twistlock.спецификация_ГОСТ();
  46_МК_корпус, 46_МК_замок, 46_МК_сборка — маршрутные карты ГОСТ 3.1118-82;
  46_ОК005_стержни, 46_ОК010_формовка, 46_ОК015_плавка — операционные карты ГОСТ 3.1404-86 форма 3
                                по подготовке формы, стержня и металла;
  46_КЭ010_форма              — карта эскизов ГОСТ 3.1105-84: форма в сборе с грузом;
  46_ККИ_контроль             — карта контроля ГОСТ 3.1502-85.
"""
import os, sys, math, importlib
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import matplotlib
matplotlib.use("Agg")
from matplotlib.patches import Polygon as MPoly, Rectangle, FancyArrowPatch
from shapely import affinity
from shapely.ops import unary_union
from shapely.geometry import box
from lib import gorizont_twistlock as T, spec, eskd_tp
Ч = importlib.import_module("чертёж_фундамента")

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
os.makedirs(OUT, exist_ok=True)
INK, ACC, GRY, SAND, CORE, METAL = "#16202f", "#b02634", "#6b7482", "#e9e1cf", "#cdb98c", "#8f97a3"
м = T.массы()
ДЕТ_КОРПУС = dict(mark="ВГ-2026.46.01", name="Корпус", assembly=T.MARK, assembly_name=T.NAME,
                  material="Сталь 20ГЛ ГОСТ 977-88", profile="отливка ХТС", mass_kg=м["корпус"])
ДЕТ_ЗАМОК = dict(mark="ВГ-2026.46.02", name="Замок", assembly=T.MARK, assembly_name=T.NAME,
                 material="Сталь 40Х ГОСТ 4543-2016", profile="поковка КП 590", mass_kg=м["замок"])
ДЕТ_УЗЕЛ = dict(mark=T.MARK, name=T.NAME, assembly="ВГ-2026", assembly_name="Судно «Волжский Горизонт»",
                material="—", profile="сборочная единица", mass_kg=м["узел"])


def ф(x, nd=2):
    return ("%." + str(nd) + "f") % x


def маршрут(ops, det, name, title_note):
    sh = eskd_tp.TechSheet("МК   ГОСТ 3.1118-82 форма 1", det["mark"] + " МК", det)
    п = T.программа()["всего"]
    rows = [[o["no"], o["цех"], o["уч"], o["имя"], o["содерж"], o["обор"], ф(o["tpz"]), ф(o["tsht"])] for o in ops]
    tpz, tsht = sum(o["tpz"] for o in ops), sum(o["tsht"] for o in ops)
    rows.append(["", "", "", "", "Итого на деталь при партии %d шт" % п, "", ф(tpz), ф(tsht)])
    sh.table([("Опер.", 9), ("Цех", 8), ("Уч.", 7), ("Наименование", 22), ("Содержание операции", 72), ("Оборудование, оснастка", 38),
              ("Тпз", 8), ("Тшт", 8)], rows, row_h=12.5 if len(ops) > 8 else 10.0, head_h=8.0, size=1.75, center=(0, 1, 2, 6, 7))
    sh.block("Примечания", title_note, size=2.2, gap=4.6)
    return sh.save(os.path.join(OUT, name))


def операционная(ok, op, det, name, требования):
    sh = eskd_tp.TechSheet("ОК   ГОСТ 3.1404-86 форма 3", "%s ОК%s" % (det["mark"], op["no"]), det)
    sh.table([("Опер.", 10), ("Наименование операции", 40), ("Цех", 8), ("Уч.", 8), ("Оборудование, оснастка", 88), ("Тпз", 10), ("Тшт", 10)],
             [[op["no"], op["имя"], op["цех"], op["уч"], op["обор"], ф(op["tpz"]), ф(op["tsht"])]],
             row_h=10.0, head_h=8.0, size=1.9, center=(0, 2, 3, 5, 6))
    sh.block("Содержание переходов", ok["переходы"], size=2.25, gap=4.9)
    sh.table([("Параметр режима", 62), ("Значение", 112)], [[k, v] for k, v in ok["режимы"]], y=sh.top - 2.0, row_h=7.0, head_h=8.0, size=2.1)
    sh.block("Требования по операции", требования, size=2.2, gap=4.8)
    return sh.save(os.path.join(OUT, name))


def эскиз_формы():
    """Карта эскизов: форма в сборе — разрез по оси двух отливок."""
    op = next(o for o in T.ТП_КОРПУС if o["no"] == "010")
    sh = eskd_tp.TechSheet("КЭ   ГОСТ 3.1105-84 форма 7", "ВГ-2026.46.01 КЭ010", ДЕТ_КОРПУС)
    sh.table([("Опер.", 10), ("Наименование операции", 50), ("Оснастка", 114)],
             [[op["no"], op["имя"], "плита модельная ВГ-2026.46.01-МП, ящик стержневой -СЯ, опоки, скобы"]], row_h=8.0, head_h=8.0, size=2.1, center=(0,))
    л, о, г = T.ЛИТЬЁ, T.отливка(), T.груз_на_форму()
    Lf, Bf, Hв, Hн = л["опока"]
    xc = Lf / 4.0
    ax = sh.sh.axes(eskd_tp.eskd.MARGIN_L + 2, sh.top - 128.0, 172.0, 124.0)
    ax.set_xlim(-470, 470); ax.set_ylim(-230, 470); ax.set_aspect("equal"); ax.axis("off")
    def patch(g, fc, ec=INK, lw=0.6, z=2):
        for p in (g.geoms if hasattr(g, "geoms") else [g]):
            if p.is_empty:
                continue
            ax.add_patch(MPoly(list(p.exterior.coords), closed=True, facecolor=fc, edgecolor=ec, lw=lw, zorder=z))
            for i in p.interiors:
                ax.add_patch(MPoly(list(i.coords), closed=True, facecolor=SAND, edgecolor=ec, lw=lw, zorder=z + 0.1))
    patch(box(-Lf / 2, -Hн, Lf / 2, Hв), SAND, lw=0.5, z=1)
    for sx in (-1, 1):
        patch(box(sx * Lf / 2, -Hн, sx * (Lf / 2 + 22), Hв), "#9aa3b0", z=3)
        cast = affinity.translate(affinity.scale(Ч.корпус_XZ(отливка=True), sx, 1, origin=(0, 0)), sx * xc, T.ПРИПУСКИ["подошва"])
        core = affinity.translate(affinity.scale(Ч.стержень_XZ(), sx, 1, origin=(0, 0)), sx * xc, T.ПРИПУСКИ["подошва"])
        patch(cast, METAL, z=4)
        patch(core, CORE, z=5)
        ax.text(sx * xc, 45, "Ст. 1", ha="center", va="center", fontsize=6.5, color=INK, zorder=8)
    patch(box(-о["d_стояка"] / 2, 0, о["d_стояка"] / 2, Hв + 30), METAL, z=4)
    patch(box(-(xc - T.КОРПУС["L_x"] / 2), 0, xc - T.КОРПУС["L_x"] / 2, 12), METAL, z=4)      # коллектор и питатели до торцов фланцев
    patch(box(-60, Hв, 60, Hв + 45).difference(box(-о["d_стояка"] / 2, Hв, о["d_стояка"] / 2, Hв + 45)), "#9aa3b0", z=3)
    ax.plot([-Lf / 2 - 40, Lf / 2 + 40], [0, 0], color=ACC, lw=1.1, ls=(0, (8, 2, 2, 2)), zorder=7)
    ax.text(Lf / 2 + 30, 14, "В", color=ACC, fontsize=8, ha="center"); ax.text(Lf / 2 + 30, -26, "Н", color=ACC, fontsize=8, ha="center")
    ax.text(-Lf / 2 - 34, 8, "МФ", color=ACC, fontsize=7, ha="center")
    ax.add_patch(Rectangle((-Lf / 2 + 40, Hв + 2), 150, 40, facecolor="#5d6776", edgecolor=INK, lw=0.6, zorder=6))
    ax.text(-Lf / 2 + 115, Hв + 22, "груз %d кг" % г["груз_кг"], color="white", fontsize=6.3, ha="center", va="center", zorder=7)
    for x, z, t in ((xc, Hв - 20, "прибыль, утепл. засыпка"), (0, Hв + 60, "чаша и стояк Ø%d" % о["d_стояка"]),
                    (-xc, -Hн + 30, "полуформа низа %d" % Hн), (xc, -Hн + 30, "знак стержня"), (-xc - 10, Hв - 20, "полуформа верха %d" % Hв)):
        ax.text(x, z, t, ha="center", va="center", fontsize=6.0, color=INK, zorder=9,
                bbox=dict(boxstyle="round,pad=0.2", facecolor="white", edgecolor="none", alpha=0.8))
    ax.annotate("", (Lf / 2 + 22, -Hн - 25), (-Lf / 2 - 22, -Hн - 25), arrowprops=dict(arrowstyle="<->", color=INK, lw=0.6))
    ax.text(0, -Hн - 45, "опока %d × %d × %d/%d" % л["опока"], ha="center", fontsize=6.5, color=INK)
    sh.top = sh.top - 132.0
    sh.block("Порядок сборки формы и контроль", [
        "Стержни Ст. 1 ставить в знаки низа, ногу-знак окна — в паз верха; зазор по знакам 0,5…1,0 мм, проверять шаблоном.",
        "Подъёмная сила металла %s кН (с запасом 1,3) больше веса верха %s кН — форму нагрузить %d кг или скрепить четырьмя скобами." % (
            ф(г["F_кН"], 1).replace(".", ","), ф(г["вес_верха_кН"], 1).replace(".", ","), г["груз_кг"]),
        "Холодильники Х1…Х4 в полуформе верха — у корней рёбер и у приливов фиксатора (лист ЛФ).",
        "Форма заливается не позднее 24 ч после сборки; при хранении — закрыть чашу и зеркала прибылей."], size=2.2, gap=4.8)
    return sh.save(os.path.join(OUT, "46_КЭ010_форма.png"))


def контроль():
    sh = eskd_tp.TechSheet("ККИ   ГОСТ 3.1502-85 форма 2", "ВГ-2026.46.01 ККИ", ДЕТ_КОРПУС)
    sh.table([("Опер.", 12), ("Объект", 16), ("Контролируемый параметр", 52), ("Средство контроля", 36), ("Объём", 28), ("НД", 34)],
             [list(r) for r in T.КОНТРОЛЬ], row_h=9.5, head_h=8.0, size=1.9, center=(0,))
    sh.block("Порядок приёмки", [
        "Отливки принимаются по плавкам: механические свойства и KCU — по клиновой пробе, до термообработки партии.",
        "Отливка с трещиной в сопряжении стакана бракуется; раковины исправляются заваркой по ГОСТ 977-88 с повторным МПД.",
        "РК первых 6 отливок подтверждает технологию формы; при усадочной пористости в верхней стенке — увеличить прибыль и повторить.",
        "Узлы предъявляются представителю РРР с актом испытаний пробной нагрузкой и паспортом плавки."], size=2.2, gap=4.8)
    return sh.save(os.path.join(OUT, "46_ККИ_контроль.png"))


def main():
    made = spec.draw(T.спецификация_ГОСТ(), T.MARK, T.NAME, dict(people=None), os.path.join(OUT, "46_спецификация_лист%d.png"))
    made.append(маршрут(T.ТП_КОРПУС, ДЕТ_КОРПУС, "46_МК_корпус.png",
                        ["Литьё — своя литейка: ХТС альфа-сет в опоках, две отливки в форме; мехобработка — обрабатывающий центр, две установки.",
                         "Нормы времени укрупнённые, Тпз — на партию %d шт; покрытие ТДЦ — кооперация." % T.программа()["всего"]]))
    made.append(маршрут(T.ТП_ЗАМОК, ДЕТ_ЗАМОК, "46_МК_замок.png",
                        ["Поковка — кузнечный цех по кооперации; мехобработка и контроль — механический цех верфи."]))
    made.append(маршрут(T.ТП_СБОРКА, ДЕТ_УЗЕЛ, "46_МК_сборка.png",
                        ["Монтаж на судне: " + "; ".join("%s) %s" % (n, t) for n, t in T.ТП_МОНТАЖ) + "."]))
    ст, фо, пл = T.режимы_операций()
    tp = {o["no"]: o for o in T.ТП_КОРПУС}
    made.append(операционная(ст, tp["005"], ДЕТ_КОРПУС, "46_ОК005_стержни.png", [
        "Смесь готовить непрерывно, живучесть 8 мин: засыпать ящик одной порцией, без перерыва.",
        "Стержень без трещин и осыпаемости; нога-знак цела по всей высоте — иначе брак.",
        "Хранить окрашенные стержни не более 48 ч при влажности воздуха до 70 %."]))
    made.append(операционная(фо, tp["010"], ДЕТ_КОРПУС, "46_ОК010_формовка.png", [
        "Способ ХТС выбран вместо ПГС: точнее отливка (класс 10 против 12…13), нет сушки, смесь регенерируется на 90 %.",
        "Модели протягивать строго вертикально; нога-знак окна выведена до верха модели — поднутрения нет.",
        "Полуформы без обвалов и трещин; окраска сплошная; выпоры над окном прочищены.",
        "Форма собирается по штырям опок; смещение полуформ не более 1 мм (См. 1,6 по ГОСТ Р 53464-2009)."]))
    made.append(операционная(пл, tp["015"], ДЕТ_КОРПУС, "46_ОК015_плавка.png", [
        "Заливать одной струёй, не прерывая; чаша полная до конца заливки — шлак не должен попасть в стояк.",
        "Перегрев выше 1600 °С в ковше не допускается — пригар и горячие трещины в сопряжениях.",
        "От каждой плавки — проба на химсостав и клиновая проба; номер плавки выбить на отливках."]))
    made.append(эскиз_формы())
    made.append(контроль())
    for p in made:
        print("  ", os.path.relpath(p, ROOT))


if __name__ == "__main__":
    main()
