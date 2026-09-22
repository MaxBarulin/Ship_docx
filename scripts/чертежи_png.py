# -*- coding: utf-8 -*-
"""Растровые копии DXF-чертежей для записки, листа проекта и быстрой проверки.

Листы ОР из CAD/ и расчётно-теоретические РТ из CAD/расчёты/ — в одну папку
renders/горизонт_2026/чертежи_dxf/, имена файлов те же.
"""
import os, glob
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
import ezdxf
from ezdxf.addons.drawing import RenderContext, Frontend
from ezdxf.addons.drawing.matplotlib import MatplotlibBackend
from ezdxf.addons.drawing.config import Configuration, ColorPolicy, BackgroundPolicy

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
SRC = os.path.join(ROOT, "CAD")
OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи_dxf")
os.makedirs(OUT, exist_ok=True)
CFG = Configuration(color_policy=ColorPolicy.COLOR,
                    background_policy=BackgroundPolicy.WHITE)


def main():
    files = sorted(glob.glob(os.path.join(SRC, "*.dxf"))) + sorted(glob.glob(os.path.join(SRC, "расчёты", "*.dxf")))
    for p in files:
        doc = ezdxf.readfile(p)
        msp = doc.modelspace()
        fig = plt.figure(figsize=(23.4, 16.5), dpi=130)
        ax = fig.add_axes([0, 0, 1, 1])
        ax.set_facecolor("white")
        Frontend(RenderContext(doc), MatplotlibBackend(ax), config=CFG).draw_layout(
            msp, finalize=True)
        name = os.path.splitext(os.path.basename(p))[0] + ".png"
        fig.savefig(os.path.join(OUT, name), facecolor="white")
        plt.close(fig)
        print(name)


if __name__ == "__main__":
    main()
