# -*- coding: utf-8 -*-
"""Растровые копии DXF-чертежей для записки, листа проекта и быстрой проверки.

Листы ОР из CAD/, расчётно-теоретические РТ из CAD/расчёты/, модульное решение МР из CAD/модули/ и КД узла из CAD/узел/ - в одну папку
renders/горизонт_2026/чертежи_dxf/, имена файлов те же.

Два правила, без которых растр нечитаем (поймано 22.09.2026):
  * `MatplotlibBackend(adjust_figure=False)` - иначе ezdxf сам ужимает фигуру до ~900 px,
    и текст 2,5 мм на листе А1 превращается в три пикселя, лист рисуется на `ДЛИННАЯ_СТОРОНА_PX`
    по длинной стороне, текст 2,5 мм на А1 выходит около 24 px;
  * ACI-цвета слоёв AutoCAD рассчитаны на чёрный экран - жёлтые оси и голубая обшивка на белом
    не видны, поэтому перед отрисовкой цвета слоёв подменяются тёмными оттенками (`ТЁМНЫЕ`),
    в DXF это не пишется.
"""
import os, glob, time
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf import bbox as _bb
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "CAD")
OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи_dxf")
os.makedirs(OUT, exist_ok=True)
ДЛИННАЯ_СТОРОНА_PX = 9000
DPI = 100
CFG = Configuration(color_policy=ColorPolicy.COLOR, background_policy=BackgroundPolicy.WHITE, min_lineweight=0.18)
#: ACI-цвет слоя → тёмный оттенок того же цвета для белого фона
ТЁМНЫЕ = {1: (170, 20, 30), 2: (150, 110, 0), 3: (0, 120, 40), 4: (0, 110, 140), 5: (20, 50, 170), 6: (150, 20, 130),
          7: (0, 0, 0), 8: (90, 90, 90), 9: (120, 120, 120), 30: (190, 90, 0), 252: (110, 110, 110)}


#: Масштабы и ширины форматов, в которых листы нарисованы в DXF (лист в пространстве модели в масштабе чертежа)
МАСШТАБЫ = (1, 2, 2.5, 4, 5, 10, 15, 20, 25, 40, 50, 75, 100, 150, 200, 250, 400, 500)
ШИРИНЫ_ФОРМАТОВ = (1189, 841, 594, 420, 297, 210)


def масштаб_листа(w):
    """Масштаб листа: ширина по DXF / ширина формата - ближайший стандартный, при равенстве - меньший."""
    лучший = None
    for F in ШИРИНЫ_ФОРМАТОВ:
        k = w / F
        n = min(МАСШТАБЫ, key=lambda s: abs(k / s - 1.0))
        err = abs(k / n - 1.0)
        if лучший is None or err < лучший[0] - 1e-4 or (abs(err - лучший[0]) <= 1e-4 and n < лучший[1]):
            лучший = (err, n)
    return лучший[1]


def _фигура(dxf, натуральная=False):
    """Лист DXF на фигуре matplotlib. натуральная - размер фигуры равен формату листа (для PDF), иначе -
    ДЛИННАЯ_СТОРОНА_PX по длинной стороне (для растра)."""
    doc = ezdxf.readfile(dxf)
    for layer in doc.layers:
        if layer.color in ТЁМНЫЕ:
            layer.rgb = ТЁМНЫЕ[layer.color]
    msp = doc.modelspace()
    ext = _bb.extents(msp)
    (x0, y0, _), (x1, y1, _) = ext.extmin, ext.extmax
    w, h = x1 - x0, y1 - y0
    if натуральная:
        n = масштаб_листа(w)
        fig_w, fig_h = w / n / 25.4, h / n / 25.4
    else:
        fig_w = ДЛИННАЯ_СТОРОНА_PX / DPI * (1.0 if w >= h else w / h)
        fig_h = fig_w * h / w
    fig = plt.figure(figsize=(fig_w, fig_h), dpi=DPI)
    ax = fig.add_axes([0, 0, 1, 1])
    ax.set_facecolor("white")
    Frontend(RenderContext(doc), MatplotlibBackend(ax, adjust_figure=False), config=CFG).draw_layout(msp, finalize=True)
    ax.set_xlim(x0, x1)
    ax.set_ylim(y0, y1)
    return fig, fig_w, fig_h


def в_pdf(dxfs, путь, автор=None):
    """Листы DXF в один векторный PDF, каждый лист - страница в натуральную величину формата.
    В свойствах файла - название и автор, без Creator и Producer программы."""
    from matplotlib.backends.backend_pdf import PdfPages
    tmp = os.path.join(os.path.dirname(путь), "_tmp_листы.pdf")
    meta = {"Title": os.path.splitext(os.path.basename(путь))[0], "Author": автор, "Creator": None, "Producer": None}
    with PdfPages(tmp, metadata=meta) as pp:
        for dxf in dxfs:
            fig, _, _ = _фигура(dxf, натуральная=True)
            pp.savefig(fig, facecolor="white")
            plt.close(fig)
    os.replace(tmp, путь)
    return путь


def растр(dxf, png):
    fig, fig_w, fig_h = _фигура(dxf)
    # Windows иногда отвечает EINVAL на запись большого PNG по кириллическому пути (индексатор держит файл):
    # пишем во временный ASCII-файл рядом и переименовываем, с повтором
    tmp = os.path.join(os.path.dirname(png), "_tmp_render.png")
    for попытка in range(4):
        try:
            fig.savefig(tmp, facecolor="white")
            os.replace(tmp, png)
            break
        except OSError:
            if попытка == 3:
                raise
            time.sleep(1.5)
    plt.close(fig)
    return int(fig_w * DPI), int(fig_h * DPI)


def main():
    files = (sorted(glob.glob(os.path.join(SRC, "*.dxf"))) + sorted(glob.glob(os.path.join(SRC, "расчёты", "*.dxf")))
             + sorted(glob.glob(os.path.join(SRC, "модули", "*.dxf"))) + sorted(glob.glob(os.path.join(SRC, "узел", "*.dxf"))))
    for p in files:
        name = os.path.splitext(os.path.basename(p))[0] + ".png"
        w, h = растр(p, os.path.join(OUT, name))
        print("%-52s %d x %d  %d КБ" % (name, w, h, os.path.getsize(os.path.join(OUT, name)) // 1024))


if __name__ == "__main__":
    main()
