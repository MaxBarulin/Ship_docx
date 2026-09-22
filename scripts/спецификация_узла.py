# -*- coding: utf-8 -*-
"""Спецификация узла ВГ-2026.31.00 «Ось плицы с кривошипом» по ГОСТ 2.106-2019.

    python scripts/спецификация_узла.py

Разделы и позиции — из `lib.gorizont_node.specification()`, форма 1 и
листы продолжения — `lib.spec`.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
from lib import gorizont_node as N, spec

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "чертежи")
os.makedirs(OUT, exist_ok=True)

if __name__ == "__main__":
    made = spec.draw(N.specification(), N.MARK, N.NAME,
                     dict(people=None), os.path.join(OUT, "11_спецификация_узла_лист%d.png"))
    for p in made:
        print(p)
