# -*- coding: utf-8 -*-
"""Модельный ряд «Волжского Горизонта» - три версии на одном корпусе.

Корпус, набор, энергетическая установка, колёса, системы и все расчёты
общие - меняется только насыщение жилых палуб. Фронт кают по бортам у всех
версий один и тот же (перегородки переставляются по сетке шпаций 550 мм,
магистрали и шахты не трогаются), поэтому версия задаётся набором типов
кают на тех же рядах. Базовая версия «Классик» - то, что построено в
модели (gorizont_ga.расстановка()).
"""
from . import gorizont as G
from . import gorizont_ga as GA

#: Глубина внутренних кают (без окна): по коридору
ГЛУБИНА_ВНУТР = 2.25


def _площадь(тип):
    к = GA.КАЮТЫ[тип]
    return к["фронт"] * (к["глубина"] or ГЛУБИНА_ВНУТР)


def _классик():
    """Каюты построенной версии - из расстановки ГА."""
    cab = {}
    for c in GA.расстановка():
        if c["тип"].startswith("экипаж"):
            continue
        cab[c["тип"]] = cab.get(c["тип"], 0) + 1
    return cab


CLASSIC = _классик()
CLASSIC_AREA = sum(n * _площадь(t) for t, n in CLASSIC.items())

VERSIONS = [
    dict(
        code="ВГ-140-Э", name="Эконом",
        idea="Максимальная вместимость - короткие маршруты выходного дня и корпоративные рейсы",
        # бортовые люксы и бизнес режутся на стандарты (4 места), семейные - на эконом
        cabins={"стандарт": 40, "стандарт М4": 6, "эконом": 36, "семейная": 4},
        note="Тот же фронт бортов - люксы 6,0 м и бизнес 5,0 м заменены стандартами 4,0 м с "
             "откидными верхними койками. Внутренние семейные - двухместными эконом.",
    ),
    dict(
        code="ВГ-140-К", name="Классик",
        idea="Базовая версия, построена в модели - баланс цены и комфорта",
        cabins=dict(CLASSIC),
        note="Все чертежи, расчёты и рендеры проекта выполнены для этой версии.",
    ),
    dict(
        code="ВГ-140-П", name="Премиум",
        idea="Минимум кают, максимум площади на пассажира и общественных пространств",
        cabins={"люкс": 14, "бизнес": 14, "стандарт М4": 6, "семейная": 8},
        note="Бортовые ряды - только люкс и бизнес по 2 места. Внутренние эконом объединены "
             "в семейные и лаунжи палуб, спа расширяется на освободившийся ряд.",
    ),
]


def _stats(v):
    cab = v["cabins"]
    n = sum(cab.values())
    berths = sum(c * GA.КАЮТЫ[k]["мест"] for k, c in cab.items())
    area = sum(c * _площадь(k) for k, c in cab.items())
    m4 = sum(c * GA.КАЮТЫ[k]["мест"] for k, c in cab.items() if GA.КАЮТЫ[k].get("М4"))
    onboard = berths + G.CREW
    return dict(
        code=v["code"], name=v["name"], idea=v["idea"], note=v["note"],
        cabins=cab, n_cabins=n, berths=berths, crew=G.CREW, onboard=onboard,
        m4=m4, m4_ok=m4 >= -(-berths * 5 // 100),
        cabin_area=round(area, 1),
        area_delta=round(area - CLASSIC_AREA, 1),
        area_per_berth=round(area / berths, 2),
        kz_ok=berths >= 200,
    )


def table():
    return [_stats(v) for v in VERSIONS]


def check():
    """Все ли версии проходят по вместимости, доле М4 и площади кают."""
    out = []
    for s in table():
        out.append(dict(code=s["code"], name=s["name"], berths=s["berths"], kz_ok=s["kz_ok"],
                        m4_ok=s["m4_ok"], area_ok=abs(s["area_delta"]) <= 0.10 * CLASSIC_AREA,
                        area_delta=s["area_delta"]))
    return out


if __name__ == "__main__":
    for s in table():
        print("%-8s %-10s кают %3d мест %3d М4 %2d площадь %.0f м² (%+.0f) %.2f м²/место"
              % (s["code"], s["name"], s["n_cabins"], s["berths"], s["m4"], s["cabin_area"],
                 s["area_delta"], s["area_per_berth"]))
