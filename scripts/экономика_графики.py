# -*- coding: utf-8 -*-
"""Графики экономики судна для записки - как диаграммы Excel.

    python scripts/экономика_графики.py

* схемы/13_экономика_себестоимость.png - структура полной себестоимости головного судна по статьям;
* схемы/13а_экономика_окупаемость.png - денежный поток программы и накопленный поток, простой и дисконтированный.
Числа - lib.gorizont_economy.
"""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from lib import plain as P, gorizont_economy as E

OUT = os.path.join(ROOT, "renders", "горизонт_2026", "схемы")


def себестоимость():
    к = E.калькуляция()
    в = к["всего"]
    статьи = [("Материалы", в["материалы"]), ("ПКИ", в["пки"]), ("ТЗР", в["тзр"]), ("Основная ЗП", в["озп"]),
              ("Дополнительная ЗП", в["дзп"]), ("Страховые взносы", в["страх"]), ("ОПР", в["опр"]), ("ОХР", в["охр"]),
              ("Коммерческие", в["ком"]), ("Прибыль", к["прибыль"])]
    with P.excel():
        fig, ax = plt.subplots(figsize=(8.0, 4.2))
        имена = [s for s, _ in статьи][::-1]
        v = [x / 1e6 for _, x in статьи][::-1]
        b = ax.barh(имена, v, color=P.OFFICE[0], height=0.6)
        for r, x in zip(b, v):
            ax.text(r.get_width() + 8, r.get_y() + r.get_height() / 2, P.ч(x, 1), va="center", fontsize=9, color=P.ПОДПИСЬ)
        P.оси(ax, сетка="x")
        ax.set_xlabel("млн руб.")
        ax.set_xlim(0, max(v) * 1.15)
        P.запятая(ax, "x")
        fig.tight_layout()
        P.рамка(fig)
        return P.сохранить(fig, os.path.join(OUT, "13_экономика_себестоимость.png"))


def окупаемость():
    д = E.денежный_поток()
    годы = [r["год"] for r in д["годы"]]
    with P.excel():
        fig, ax = plt.subplots(figsize=(8.0, 4.2))
        ax.bar(годы, [r["поток"] / 1e6 for r in д["годы"]], color=P.OFFICE[0], width=0.6, label="Денежный поток")
        ax.plot(годы, [r["накоп"] / 1e6 for r in д["годы"]], color=P.OFFICE[1], lw=2, marker="o", ms=4, label="Накопленный поток")
        ax.plot(годы, [r["накоп_д"] / 1e6 for r in д["годы"]], color=P.OFFICE[2], lw=2, marker="o", ms=4,
                label="Накопленный дисконтированный поток")
        ax.axhline(0, color=P.ОСЬ, lw=0.8)
        P.оси(ax)
        ax.set_ylabel("млн руб.")
        ax.set_xticks(годы)
        P.запятая(ax, "y")
        P.легенда(ax, ncol=3, dy=-0.12)
        fig.tight_layout()
        P.рамка(fig)
        return P.сохранить(fig, os.path.join(OUT, "13а_экономика_окупаемость.png"))


if __name__ == "__main__":
    for f in (себестоимость, окупаемость):
        print(f())
