# -*- coding: utf-8 -*-
"""Модельный ряд «Волжского Горизонта»: три версии на одном корпусе.

Корпус, набор, энергетическая установка, системы и все расчёты общие —
меняется только насыщение жилых ярусов. Суммарная площадь кают у всех
трёх версий держится в пределах построенной: перегородки переставляются
по той же сетке шпаций 550 мм, магистрали и шахты не трогаются.

Базовая версия «Классик» — то, что построено в модели.
"""
from . import gorizont as G
from . import gorizont_ga as GA

CREW_TYPES = GA.CREW_TYPES

# площадь кают пассажиров в построенной версии, м2
CLASSIC_AREA = sum(c * G.CABIN_TYPES[k]["area"]
                   for k, c in GA.cabin_counts().items() if k in G.CABIN_TYPES)

VERSIONS = [
    dict(
        code="ВГ-139-Э", name="Эконом",
        idea="Максимальная вместимость: массовые маршруты выходного дня",
        cabins={"эконом": 60, "стандарт": 54, "бизнес": 10, "люкс": 4},
        crew=58,
        boats=[(21.0, 8.6, 100), (44.6, 8.6, 100), (53.4, 8.0, 100), (94.1, 7.0, 70)],
        public_delta=-2.4,
        note="Кормовая пара люксов на шлюпочной палубе уступает место "
             "четвёртой паре шлюпок — иначе вместимости шлюпок одного борта "
             "не хватает на всех.",
    ),
    dict(
        code="ВГ-139-К", name="Классик",
        idea="Базовая версия, построена в модели: баланс цены и комфорта",
        cabins={"эконом": 40, "стандарт": 38, "бизнес": 18, "люкс": 10},
        crew=57,
        boats=list(GA.BOATS),
        public_delta=0.0,
        note="Все чертежи, расчёты и рендеры проекта выполнены для этой версии.",
    ),
    dict(
        code="ВГ-139-П", name="Премиум",
        idea="Минимум кают, максимум общественных пространств и балконов",
        cabins={"эконом": 8, "стандарт": 20, "бизнес": 24, "люкс": 18},
        crew=52,
        boats=list(GA.BOATS),
        public_delta=+92.2,
        note="Освободившиеся 92 м2 идут в лаундж верхней палубы и расширение спа.",
    ),
]


def _stats(v):
    cab = v["cabins"]
    n = sum(cab.values())
    berths = sum(c * G.CABIN_TYPES[k]["berths"] for k, c in cab.items())
    area = sum(c * G.CABIN_TYPES[k]["area"] for k, c in cab.items())
    boats = sum(b[2] for b in v["boats"])
    onboard = berths + v["crew"]
    return dict(
        code=v["code"], name=v["name"], idea=v["idea"], note=v["note"],
        cabins=cab, n_cabins=n, berths=berths, crew=v["crew"], onboard=onboard,
        cabin_area=round(area, 1),
        area_delta=round(area - CLASSIC_AREA, 1),
        public_delta=v["public_delta"],
        area_per_berth=round(area / berths, 2),
        boats_per_side=boats, boats_n=len(v["boats"]),
        boats_ok=boats >= onboard,
        margin=boats - onboard,
    )


def table():
    return [_stats(v) for v in VERSIONS]


def check():
    """Все ли версии проходят по вместимости шлюпок и по площади кают."""
    out = []
    for s in table():
        out.append(dict(code=s["code"], name=s["name"],
                        boats_ok=s["boats_ok"], margin=s["margin"],
                        area_ok=abs(s["area_delta"]) <= 0.06 * CLASSIC_AREA,
                        area_delta=s["area_delta"]))
    return out
