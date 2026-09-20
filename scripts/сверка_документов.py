# -*- coding: utf-8 -*-
r"""Сверка чисел в документах с моделью и библиотеками.

    python scripts/сверка_документов.py

Записка и сверка с описанием пишутся руками, и числа в них устаревают молча:
класс судна сменили с «О» на «М», посадку в залах пересчитали по проходам, а
в документах остались прежние значения. Скрипт берёт факты из библиотек и из
счёта модели, ищет их в документах и сообщает о расхождениях.

Проверяется не «есть ли число», а «нет ли противоречащего»: для каждого
факта задан список запрещённых строк — прежних значений, которые не должны
встречаться.
"""

import io, json, os, sys

ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, os.path.join(ROOT, "src"))

from lib import gorizont as G
from lib import gorizont_ga as GA
from lib import gorizont_hydro as H
from lib import gorizont_roll as RL

DOCS = [
    os.path.join(ROOT, "docs", "проект", "записка_горизонт.md"),
    os.path.join(ROOT, "docs", "проект", "сверка_с_описанием.md"),
]
SEATS = os.path.join(ROOT, "src", "lib", "gorizont_seats.json")


def _seats():
    try:
        with io.open(SEATS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def facts():
    """(что проверяем, текущее значение, запрещённые старые написания)."""
    e = H.equilibrium()
    w = H.weather_criterion()
    s = _seats()
    out = [
        # ищем утверждения о модели, а не цитаты описания: в левой колонке
        # сверки класс «О» стоит законно — так написано у Алексея
        ("класс РРР", G.RRR_CLASS,
         ["Класс РРР «О»", "нормы РРР класса «О»",
          "Лед 1 / Arc 4 | принят"]),
        ("осадка", "%.2f м" % e["T"], ["осадке 2.22 м", "**2.22 м**"]),
        ("водоизмещение", "%.0f т" % e["D"], ["весит 3990 т", "3990 т ("]),
        ("габаритная высота", "%.1f м" % G.AIR_DRAFT, []),
        ("пассажиров", str(GA.passengers()), []),
        ("экипаж", str(GA.crew()), []),
        ("критерий погоды", "%.1f" % w["K"], ["Критерий погоды 14.9"]),
        ("метацентрическая высота", "%.2f м" % w["h"],
         ["h = 7.84 м", "h = 7.69 м"]),
        ("период бортовой качки", "%.2f с" % H.roll_period(), []),
        ("пассажирских кают", str(GA.passenger_cabins()), []),
    ]
    out.append(("успокоительные цистерны",
                "%.1f т, период %.2f с"
                % (RL.water()["mass"], RL.tank_period()), []))
    for obj, ru, old in (("мебель_ресторан", "ресторан", ["(168 мест)"]),
                         ("мебель_театр", "театр", ["(216 мест)"]),
                         ("мебель_бистро", "бистро",
                          ["бистро на 60 мест", "(60 мест)"])):
        if obj in s:
            out.append(("посадка: " + ru, "%d" % s[obj], old))
    return out


def check(verbose=True):
    bad = []
    texts = {}
    for p in DOCS:
        if os.path.exists(p):
            texts[p] = io.open(p, encoding="utf-8").read()
    for name, now, forbidden in facts():
        for p, t in texts.items():
            for f in forbidden:
                if f in t:
                    bad.append((os.path.basename(p), name, f, now))
    if verbose:
        print("документов проверено: %d" % len(texts))
        for name, now, _ in facts():
            print("  %-28s %s" % (name, now))
        if bad:
            print("!! устаревшие места:")
            for d, name, f, now in bad:
                print("   %-26s %-22s «%s» → должно быть %s"
                      % (d, name, f, now))
        else:
            print("расхождений с моделью нет")
    return bad


if __name__ == "__main__":
    sys.exit(1 if check() else 0)
