# -*- coding: utf-8 -*-
"""Спецификация узла ВГ-2026.16.00 по ГОСТ 2.106-2019.

    python scripts/спецификация_фундамента.py

Листы А4 с графами формы 1 и разделами в порядке стандарта. Содержимое
берётся из `gorizont_awts.specification()`, то есть из той же таблицы
деталей, по которой считаются массы узла, — руками ничего не набирается.
"""
import os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from lib import gorizont_awts as A
from lib import spec

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")


def build(verbose=True):
    sections = A.specification()
    made = spec.draw(
        sections, mark=A.MARK,
        name="Фундамент установки\nочистки сточных вод",
        sheets_data=dict(material=None, mass=None, lit="У"),
        path_fmt=os.path.join(OUT, "09_спецификация_лист%d.png"))
    if verbose:
        n = sum(len(r) for _, r in sections)
        print("спецификация: %d позиций на %d листах" % (n, len(made)))
        for p in made:
            print("  ", os.path.basename(p))
    return made


if __name__ == "__main__":
    build()
