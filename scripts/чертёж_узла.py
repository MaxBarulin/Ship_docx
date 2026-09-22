# -*- coding: utf-8 -*-
"""Сборочный чертёж узла ВГ-2026.31.00 СБ «Ось плицы с кривошипом» — DXF и PNG.

    python scripts/чертёж_узла.py

Размеры — из `lib.gorizont_node` (те же, что у 3D-модели CAD/src/ось_плицы.py).
Лист А1, масштаб 1:5: главный вид (взгляд по нормали к полотну плицы),
разрез А-А по ступице, вид Б на кривошип, выносной элемент В — цапфа в
подшипнике диска. Позиции — по спецификации ВГ-2026.31.00.
"""
import os, sys, math
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
sys.path.insert(0, os.path.join(ROOT, "scripts"))
import ezdxf
from ezdxf.enums import TextEntityAlignment as TA
from lib import gorizont_node as N
import importlib
D = importlib.import_module("чертежи_dxf")

OUT = os.path.join(ROOT, "CAD")
PNG = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
os.makedirs(OUT, exist_ok=True); os.makedirs(PNG, exist_ok=True)
SC = 5.0                    # масштаб листа 1:5 — размеры на листе в мм модели
L_ = dict(layer="01_ОБШИВКА")
LT = dict(layer="02_ПАЛУБЫ")       # тонкие линии
LA = dict(layer="07_ОСИ")
LH = dict(layer="10_НАБОР")        # штриховка


def hatch(msp, x0, y0, x1, y1, step=8.0, layer="10_НАБОР"):
    """Штриховка прямоугольника под 45°."""
    w, h = x1 - x0, y1 - y0
    d = -h
    while d < w:
        xa, ya = x0 + max(d, 0.0), y0 + max(-d, 0.0)
        xb, yb = x0 + min(d + h, w), y0 + min(h, w - d)
        if xb > xa:
            msp.add_line((xa, ya), (xb, yb), dxfattribs={"layer": layer})
        d += step


def dim_h(msp, x0, x1, y, txt, off=60.0):
    """Горизонтальный размер со стрелками-засечками."""
    msp.add_line((x0, y), (x1, y), dxfattribs={"layer": "09_РАЗМЕРЫ"})
    for x in (x0, x1):
        msp.add_line((x, y - off), (x, y + 6), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        msp.add_line((x - 6, y - 6), (x + 6, y + 6), dxfattribs={"layer": "09_РАЗМЕРЫ"})
    D.text(msp, 0.5 * (x0 + x1), y + 12, txt, 3.5, SC, "09_РАЗМЕРЫ")


def dim_v(msp, y0, y1, x, txt, off=60.0):
    msp.add_line((x, y0), (x, y1), dxfattribs={"layer": "09_РАЗМЕРЫ"})
    for y in (y0, y1):
        msp.add_line((x - off, y), (x + 6, y), dxfattribs={"layer": "09_РАЗМЕРЫ"})
        msp.add_line((x - 6, y - 6), (x + 6, y + 6), dxfattribs={"layer": "09_РАЗМЕРЫ"})
    D.text(msp, x + 12, 0.5 * (y0 + y1), txt, 3.5, SC, "09_РАЗМЕРЫ", rot=90)


def pos(msp, x, y, xe, ye, n):
    """Позиция: полка с кружком и выноска к точке (x, y)."""
    msp.add_line((x, y), (xe, ye), dxfattribs={"layer": "09_РАЗМЕРЫ"})
    msp.add_circle((x, y), 6.0, dxfattribs={"layer": "09_РАЗМЕРЫ"})
    msp.add_circle((xe, ye), 3.0 * SC, dxfattribs={"layer": "08_ТЕКСТ"})
    D.text(msp, xe, ye, str(n), 4.0, SC, "08_ТЕКСТ")


def main_view(msp, ox, oy):
    """Главный вид: ось вдоль X, плица под ней (взгляд по нормали к полотну)."""
    r = N.D_AXIS / 2.0
    L = N.L_AXIS
    zj = N.DISC_Y - N.DISC_T / 2.0 - 5.0
    # ось
    D.rect(msp, ox - zj, oy - r, ox + zj, oy + r, "01_ОБШИВКА")
    for s in (1, -1):
        rj = N.D_JOURNAL / 2.0
        x0, x1 = sorted((ox + s * zj, ox + s * (zj + N.L_JOURNAL)))
        D.rect(msp, x0, oy - rj, x1, oy + rj, "01_ОБШИВКА")
    D.rect(msp, ox + zj + N.L_JOURNAL, oy - 40, ox + zj + N.L_JOURNAL + 45, oy + 40, "01_ОБШИВКА")
    D.rect(msp, ox + zj + N.L_JOURNAL + 2, oy - 60, ox + zj + N.L_JOURNAL + 42, oy + 60, "01_ОБШИВКА")   # гайка
    msp.add_line((ox - L / 2 - 80, oy), (ox + L / 2 + 80, oy), dxfattribs=LA)
    # диски обода — обрыв: показаны по 300 мм
    for s in (1, -1):
        xc = ox + s * N.DISC_Y
        D.rect(msp, xc - N.DISC_T / 2, oy - 300, xc + N.DISC_T / 2, oy + 300, "02_ПАЛУБЫ")
        D.rect(msp, xc - N.BUSH_L / 2, oy - N.BUSH_D_OUT / 2, xc + N.BUSH_L / 2, oy + N.BUSH_D_OUT / 2, "01_ОБШИВКА")
        for yy in (oy - 300, oy + 300):
            msp.add_line((xc - N.DISC_T / 2 - 10, yy - 12), (xc + N.DISC_T / 2 + 10, yy + 12), dxfattribs=LT)
    # ступицы и плица
    for y in N.HUB_Y:
        for s in (1, -1):
            xc = ox + s * y
            D.rect(msp, xc - N.HUB_L / 2, oy - N.HUB_D / 2, xc + N.HUB_L / 2, oy + N.HUB_D / 2, "01_ОБШИВКА")
            D.rect(msp, xc - N.HUB_L / 2, oy - (N.BLADE_H - 40) / 2, xc + N.HUB_L / 2, oy + (N.BLADE_H - 40) / 2, "02_ПАЛУБЫ")
            for sz in (1, -1):
                msp.add_circle((xc + sz * 45.0, oy + N.HUB_D / 2 + 12), 8.5, dxfattribs=LT)
                msp.add_circle((xc + sz * 45.0, oy - N.HUB_D / 2 - 12), 8.5, dxfattribs=LT)
    # панели плицы (верхняя и нижняя), за осью — тонкими линиями
    D.rect(msp, ox - N.BLADE_SPAN / 2, oy + N.HUB_D / 2 + 30, ox + N.BLADE_SPAN / 2, oy + N.BLADE_H / 2, "02_ПАЛУБЫ")
    D.rect(msp, ox - N.BLADE_SPAN / 2, oy - N.BLADE_H / 2, ox + N.BLADE_SPAN / 2, oy - N.HUB_D / 2 - 30, "02_ПАЛУБЫ")
    # кривошип — торцом (полоса 30 мм) с пальцем
    xc = ox + N.CRANK_Y
    D.rect(msp, xc - N.CRANK_T / 2, oy - N.CRANK_HUB_D / 2, xc + N.CRANK_T / 2, oy + N.CRANK_L + N.CRANK_W / 2, "01_ОБШИВКА")
    D.rect(msp, xc - 40, oy - N.CRANK_HUB_D / 2, xc + 40, oy + N.CRANK_HUB_D / 2, "01_ОБШИВКА")
    D.rect(msp, xc - N.PIN_L + N.CRANK_T / 2, oy + N.CRANK_L - N.PIN_D / 2, xc + N.CRANK_T / 2 + 22, oy + N.CRANK_L + N.PIN_D / 2, "01_ОБШИВКА")
    # размеры
    dim_h(msp, ox - L / 2, ox + L / 2, oy - N.BLADE_H / 2 - 120, "%.0f" % L)
    dim_h(msp, ox - N.DISC_Y, ox + N.DISC_Y, oy - N.BLADE_H / 2 - 60, "%.0f" % (2 * N.DISC_Y))
    dim_h(msp, ox - N.HUB_Y[1], ox + N.HUB_Y[1], oy + N.BLADE_H / 2 + 60, "%.0f" % (2 * N.HUB_Y[1]))
    dim_h(msp, ox - N.HUB_Y[0], ox + N.HUB_Y[0], oy + N.BLADE_H / 2 + 120, "%.0f" % (2 * N.HUB_Y[0]))
    dim_h(msp, ox - N.BLADE_SPAN / 2, ox + N.BLADE_SPAN / 2, oy - N.BLADE_H / 2 - 180, "%.0f (плица)" % N.BLADE_SPAN)
    dim_v(msp, oy - r, oy + r, ox - zj - 250, "Ø%.0f h7" % N.D_AXIS)
    dim_v(msp, oy, oy + N.CRANK_L, ox + N.CRANK_Y + 130, "%.0f" % N.CRANK_L)
    # позиции
    pos(msp, ox - 600, oy + 20, ox - 700, oy + 420, 1)
    pos(msp, ox + N.HUB_Y[0], oy + N.HUB_D / 2, ox + N.HUB_Y[0] + 120, oy + 460, 2)
    pos(msp, ox + N.CRANK_Y, oy + 400, ox + N.CRANK_Y - 200, oy + 760, 3)
    pos(msp, ox + N.CRANK_Y - 40, oy + N.CRANK_L, ox + N.CRANK_Y + 200, oy + 760, 4)
    pos(msp, ox - N.DISC_Y, oy + N.BUSH_D_OUT / 2, ox - N.DISC_Y - 150, oy + 460, 5)
    pos(msp, ox + zj + N.L_JOURNAL + 20, oy + 60, ox + zj + 260, oy + 320, 14)
    D.text(msp, ox, oy + N.BLADE_H / 2 + 200, "Главный вид (взгляд по нормали к полотну плицы; диски обода показаны с обрывом)", 4.0, SC)
    # метки сечений
    xa = ox + N.HUB_Y[0]
    for yy in (oy - 450, oy + 450):
        msp.add_line((xa, yy - 30), (xa, yy + 30), dxfattribs={"layer": "08_ТЕКСТ"})
        D.text(msp, xa + 40, yy, "А", 5.0, SC, "08_ТЕКСТ")
    xb = ox + N.CRANK_Y
    for yy in (oy - 450,):
        msp.add_line((xb, yy - 30), (xb, yy + 30), dxfattribs={"layer": "08_ТЕКСТ"})
        D.text(msp, xb + 40, yy, "Б", 5.0, SC, "08_ТЕКСТ")


def section_hub(msp, ox, oy):
    """Разрез А-А по ступице: ось, хомут, фланец-проушина, панели плицы."""
    r = N.D_AXIS / 2.0
    msp.add_circle((ox, oy), r, dxfattribs=L_)
    msp.add_circle((ox, oy), N.HUB_D / 2.0, dxfattribs=L_)
    hatch_ring(msp, ox, oy, r, N.HUB_D / 2.0)
    # разъём хомута
    msp.add_line((ox - N.HUB_D / 2, oy - 2), (ox + N.HUB_D / 2, oy - 2), dxfattribs=LT)
    msp.add_line((ox - N.HUB_D / 2, oy + 2), (ox + N.HUB_D / 2, oy + 2), dxfattribs=LT)
    # приливы под болты
    for sx in (1, -1):
        D.rect(msp, ox + sx * (N.HUB_D / 2 + 12) - 20, oy - 30, ox + sx * (N.HUB_D / 2 + 12) + 20, oy + 30, "01_ОБШИВКА")
        msp.add_line((ox + sx * (N.HUB_D / 2 + 12), oy - 30), (ox + sx * (N.HUB_D / 2 + 12), oy + 30), dxfattribs=LA)
    # фланец-проушина спереди оси (x = +50…+62) и панели плицы
    hz = (N.BLADE_H - 40) / 2.0
    D.rect(msp, ox + 50, oy - hz, ox + 50 + N.LUG_T, oy + hz, "01_ОБШИВКА")
    hatch(msp, ox + 50, oy - hz, ox + 50 + N.LUG_T, oy + hz, 6.0)
    x_pl = ox + 50 + N.LUG_T
    D.rect(msp, x_pl, oy + N.HUB_D / 2 + 30, x_pl + N.BLADE_T, oy + N.BLADE_H / 2, "02_ПАЛУБЫ")
    D.rect(msp, x_pl, oy - N.BLADE_H / 2, x_pl + N.BLADE_T, oy - N.HUB_D / 2 - 30, "02_ПАЛУБЫ")
    for yy in (oy + 200, oy + 300, oy - 200, oy - 300):
        msp.add_line((ox + 30, yy), (x_pl + N.BLADE_T + 30, yy), dxfattribs=LA)     # болты М16 панелей
    # шпонка
    b, h, l = N.KEY
    D.rect(msp, ox - b / 2, oy + r - h / 2, ox + b / 2, oy + r + h / 2, "01_ОБШИВКА")
    dim_v(msp, oy - N.BLADE_H / 2, oy + N.BLADE_H / 2, x_pl + N.BLADE_T + 90, "%.0f" % N.BLADE_H)
    dim_h(msp, ox, x_pl + N.BLADE_T / 2, oy - N.BLADE_H / 2 - 60, "%.0f" % (50 + N.LUG_T + N.BLADE_T / 2))
    D.text(msp, ox, oy + N.BLADE_H / 2 + 120, "А-А (1:5)", 5.0, SC)
    D.text(msp, ox, oy + N.BLADE_H / 2 + 60, "хомут поз.2 с фланцем-проушиной; панели плицы условно", 3.0, SC)
    pos(msp, ox + 50 + N.LUG_T / 2, oy + 120, ox - 150, oy + 260, 2)
    pos(msp, ox + 25, oy + r - 5, ox - 150, oy + 160, 13)


def hatch_ring(msp, ox, oy, r0, r1, n=36):
    for i in range(n):
        a = 2 * math.pi * i / n
        msp.add_line((ox + r0 * math.cos(a), oy + r0 * math.sin(a)), (ox + r1 * math.cos(a), oy + r1 * math.sin(a)),
                     dxfattribs=LH)


def view_crank(msp, ox, oy):
    """Вид Б на кривошип: ступица, щека, глаз с пальцем."""
    r = N.D_AXIS / 2.0
    msp.add_circle((ox, oy), r, dxfattribs=L_)
    msp.add_circle((ox, oy), N.CRANK_HUB_D / 2.0, dxfattribs=L_)
    msp.add_line((ox - N.CRANK_W / 2, oy), (ox - N.CRANK_W / 2, oy + N.CRANK_L), dxfattribs=L_)
    msp.add_line((ox + N.CRANK_W / 2, oy), (ox + N.CRANK_W / 2, oy + N.CRANK_L), dxfattribs=L_)
    msp.add_circle((ox, oy + N.CRANK_L), N.CRANK_W / 2.0, dxfattribs=L_)
    msp.add_circle((ox, oy + N.CRANK_L), N.PIN_D / 2.0, dxfattribs=L_)
    msp.add_circle((ox, oy + N.CRANK_L), N.PIN_D / 2.0 + 12, dxfattribs=LT)
    msp.add_line((ox, oy - 140), (ox, oy + N.CRANK_L + 120), dxfattribs=LA)
    msp.add_line((ox - 140, oy), (ox + 140, oy), dxfattribs=LA)
    b, h, l = N.KEY
    D.rect(msp, ox - b / 2, oy + r - h / 2, ox + b / 2, oy + r + h / 2, "01_ОБШИВКА")
    dim_v(msp, oy, oy + N.CRANK_L, ox + N.CRANK_W / 2 + 90, "%.0f" % N.CRANK_L)
    dim_h(msp, ox - N.CRANK_W / 2, ox + N.CRANK_W / 2, oy - 100, "%.0f" % N.CRANK_W)
    D.text(msp, ox, oy + N.CRANK_L + 170, "Б (1:5)", 5.0, SC)
    D.text(msp, ox + 140, oy + N.CRANK_L + 60, "Ø%.0f H7" % N.PIN_D, 3.5, SC, "09_РАЗМЕРЫ", TA.MIDDLE_LEFT)
    D.text(msp, ox + 140, oy - 40, "Ø%.0f H7/h7" % N.D_AXIS, 3.5, SC, "09_РАЗМЕРЫ", TA.MIDDLE_LEFT)
    pos(msp, ox + N.CRANK_W / 2, oy + 300, ox + 220, oy + 420, 3)
    pos(msp, ox, oy + N.CRANK_L + N.PIN_D / 2, ox - 220, oy + N.CRANK_L + 90, 4)


def detail_journal(msp, ox, oy):
    """Выносной элемент В: цапфа в подшипнике диска обода (2:1 не нужен — 1:5, крупно 1:2)."""
    k = 2.5   # 1:2 относительно листа 1:5
    rj = N.D_JOURNAL / 2 * k; rb = N.BUSH_D_OUT / 2 * k; r = N.D_AXIS / 2 * k
    L = N.BUSH_L * k; t = N.DISC_T * k
    D.rect(msp, ox - t / 2, oy - 260, ox + t / 2, oy + 260, "02_ПАЛУБЫ")        # диск
    D.rect(msp, ox - L / 2, oy - rb, ox + L / 2, oy + rb, "01_ОБШИВКА")           # втулка
    hatch(msp, ox - L / 2, oy + rj, ox + L / 2, oy + rb, 6.0)
    hatch(msp, ox - L / 2, oy - rb, ox + L / 2, oy - rj, 6.0)
    D.rect(msp, ox - 300, oy - r, ox - t / 2 - 8, oy + r, "01_ОБШИВКА")           # ось до буртика
    D.rect(msp, ox - t / 2 - 8, oy - rj, ox + 300, oy + rj, "01_ОБШИВКА")        # цапфа
    for sx in (1, -1):
        D.rect(msp, ox + sx * (L / 2 + 6) - 6, oy - rb, ox + sx * (L / 2 + 6) + 6, oy + rb, "02_ПАЛУБЫ")   # уплотнения поз.7
    msp.add_line((ox - 320, oy), (ox + 320, oy), dxfattribs=LA)
    D.text(msp, ox, oy + 300, "В (1:2)", 5.0, SC)
    D.text(msp, ox, oy - 320, "цапфа Ø%.0f в втулке поз.5, диск обода, уплотнения поз.7, маслёнка" % N.D_JOURNAL, 3.0, SC)
    dim_h(msp, ox - L / 2, ox + L / 2, oy + rb + 40, "%.0f" % N.BUSH_L)
    dim_v(msp, oy - rj, oy + rj, ox + 340, "Ø%.0f f7" % N.D_JOURNAL)
    pos(msp, ox + L / 4, oy + rb - 5, ox + 200, oy + 200, 5)
    pos(msp, ox + L / 2 + 6, oy + rb - 5, ox + 300, oy + 140, 7)


def main():
    doc = D.newdoc(); msp = doc.modelspace()
    # компоновка листа А1 в масштабе 1:5: поле 791 x 569 мм → 3955 x 2845 мм модели
    ox, oy = 0.0, 1400.0
    main_view(msp, ox, oy)
    section_hub(msp, -1300.0, 300.0)
    view_crank(msp, -300.0, 100.0)
    detail_journal(msp, 900.0, 300.0)
    s = N.strength(); l = N.loads(); m = N.mass()
    notes = ("Размеры для справок. Неуказанные предельные отклонения: валы h14, отверстия H14, прочие ±IT14/2.",
             "Ось поз.1: сталь 40Х, улучшение 28…32 HRC; цапфы Ø%.0f f7, шероховатость Ra 0,8." % N.D_JOURNAL,
             "Втулки поз.5 запрессовать в бобышки дисков обода с натягом H7/s6; смазка — забортная вода, маслёнки для консервации.",
             "Ступицы поз.2 ставить на шпонках, стянуть болтами М16 кл. 8.8 моментом 180 Н·м; панели плицы крепить болтами М16 через фланец.",
             "Расчётная нагрузка на плицу %.0f кН (удар при входе в воду с динамикой %.1f); напряжение в оси %.0f МПа, запас %.1f." % (l["F_расчётная"], N.K_DYN, s["sigma_экв"], s["n_ось"]),
             "Масса узла %.0f кг. Спецификация — ВГ-2026.31.00; тяга с срезным пальцем — узел ВГ-2026.32.00." % m["всего"])
    bbox = (-2000.0, -1200.0, 1960.0, 2650.0)
    D.frame(msp, "A1", int(SC), bbox, N.MARK + " СБ", N.NAME + ". Сборочный чертёж",
            "Гребное колесо ВГ-2026.30.00 · плица шарнирная · 12 шт. на колесо", notes,
            material="Сталь 40Х ГОСТ 4543 / 09Г2С ГОСТ 19281")
    p = os.path.join(OUT, N.MARK.replace(".", "_") + "_СБ_ось_плицы.dxf")
    doc.saveas(p)
    print(os.path.basename(p), os.path.getsize(p) // 1024, "КБ")
    # растровая копия
    try:
        import matplotlib
        matplotlib.use("Agg")
        import matplotlib.pyplot as plt
        from ezdxf.addons.drawing import RenderContext, Frontend
        from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
        from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy
        fig = plt.figure(figsize=(23.4, 16.5), dpi=130)
        ax = fig.add_axes([0, 0, 1, 1]); ax.set_axis_off()
        ctx = RenderContext(doc)
        Frontend(ctx, MatplotlibBackend(ax), config=Configuration(color_policy=ColorPolicy.COLOR, background_policy=BackgroundPolicy.WHITE)).draw_layout(msp, finalize=True)
        out = os.path.join(PNG, "10_узел_ось_плицы_СБ.png")
        fig.savefig(out, dpi=130); plt.close(fig)
        print(out)
    except Exception as e:
        print("png:", e)


if __name__ == "__main__":
    main()
