#!/usr/bin/env python
"""Аудит модели судна: что торчит за борт и что висит в воздухе.

Глазами такое не ловится. Леер, уехавший за обвод в носу, на перспективе
читается как часть силуэта, а на виде сверху его закрывает палуба. Поэтому
проверяем геометрией: каждую деталь сверяем с полуширотой корпуса на её
собственной длине и ищем опору под ней.

    python scripts/audit_model.py
"""

from __future__ import annotations

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / "src"))

from scipy.interpolate import PchipInterpolator  # noqa: E402

from lib import ship, vessel  # noqa: E402

OVERHANG_TOLERANCE = 60.0  # мм: обшивка и привальный брус
SUPPORT_GAP = 900.0  # мм: на сколько деталь может отстоять от опоры под ней

# Проверяем по ВЕРШИНАМ детали, а не по её габаритной коробке. У панели,
# развёрнутой по обводу, коробка много шире самой панели, и проверка по
# коробке объявляет нарушителем каждый второй поручень. Вершины же лежат
# ровно там, где деталь.
CONTOUR_BUILT = ("корпус",)


def hull_half_beam():
    """Полуширота корпуса по палубе как функция длины."""
    xs = [row[0] for row in ship.STATIONS]
    ys = [row[3] for row in ship.STATIONS]
    curve = PchipInterpolator(xs, ys)

    def at(x):
        return float(curve(min(max(x, xs[0]), xs[-1])))

    return at


def audit(solid=None):
    solid = vessel.build() if solid is None else solid
    half_beam = hull_half_beam()

    deck_levels = sorted({round(level) for level in vessel.DECK_LEVEL.values()})
    parts = []
    for part in solid.leaves:
        points = [(vertex.X, vertex.Y, vertex.Z) for vertex in part.vertices()]
        parts.append((part.label or "без имени", part.bounding_box(), points))

    # Деталь проверяется ПО ДЛИНЕ, а не по краям: длинный леер вдоль всего
    # борта на миделе в обвод укладывается, а в носу уезжает наружу, и
    # проверка по двум крайним точкам этого не увидит.
    overhang = []
    for label, box, points in parts:
        if any(word in label.lower() for word in CONTOUR_BUILT):
            continue
        worst, worst_x = 0.0, 0.0
        for x, y, _z in points:
            excess = abs(y) - half_beam(x)
            if excess > worst:
                worst, worst_x = excess, x
        if worst > OVERHANG_TOLERANCE:
            overhang.append((label, worst, worst_x))

    # Опорой считается ЛЮБАЯ деталь под ногами, а не только палубный настил:
    # фриз борта стоит на остеклении, остекление на цоколе, и требовать под
    # каждым из них палубу — значит утопить отчёт в ложных срабатываниях.
    floating = []
    boxes = [box for _, box, _ in parts]
    for index, (label, box, _points) in enumerate(parts):
        if box.min.Z <= ship.DEPTH + 200:
            continue
        supported = False
        for other_index, other in enumerate(boxes):
            if other_index == index:
                continue
            # допуск на касание: деталь, стоящая ровно на другой, из-за
            # округления получает верх опоры на доли миллиметра выше
            if (other.max.Z < box.min.Z - SUPPORT_GAP
                    or other.max.Z > box.min.Z + 30):
                continue
            if (other.max.X < box.min.X or other.min.X > box.max.X
                    or other.max.Y < box.min.Y or other.min.Y > box.max.Y):
                continue
            supported = True
            break
        if not supported:
            below = [level for level in deck_levels if level <= box.min.Z + 1]
            floating.append((label, box.min.Z, max(below) if below else 0))

    slabs = {label for label, _, _ in parts if "палуба" in label}
    return {"overhang": overhang, "floating": floating, "slabs": sorted(slabs),
            "parts": len(parts), "cabins": cabins_outside_hull()}


def cabins_outside_hull():
    """Каюты, выходящие за обвод надстройки.

    Каюты расставляются по прямой на |y| = CABIN_EDGE, а обвод палубы к носу
    и корме сужается. Где обвод уже каюты, каюта торчит наружу сквозь борт —
    на виде сверху это незаметно, потому что борт её и закрывает.
    """
    from lib import arrangement as ar
    from lib import vessel

    bad = []
    for deck_name, level in vessel.INTERIOR_DECKS.items():
        if deck_name not in vessel.DECK_SHAPE:
            continue
        stations = vessel.deck_stations(*vessel.DECK_SHAPE[deck_name])
        curve = PchipInterpolator([x for x, _ in stations],
                                  [y for _, y in stations])
        x_lo, x_hi = stations[0][0], stations[-1][0]
        for cabin in ar.cabin_numbers(deck_name):
            for x in (cabin["x0"], cabin["x0"] + cabin["width"]):
                half = float(curve(min(max(x, x_lo), x_hi)))
                if ship.CABIN_EDGE > half + 50:
                    bad.append((deck_name, cabin["number"],
                                ship.CABIN_EDGE - half, x))
                    break
    return bad


# Пары, где перекрытие заложено конструкцией, а не является ошибкой.
# Панели обвода длиннее сегмента на толщину, иначе на каждом изломе контура
# остаётся щель; простенок окна лежит поверх ленты остекления, потому что
# он и есть накладная перемычка между окнами.
EXPECTED_OVERLAPS = {
    frozenset({"цоколь борта", "цоколь борта"}),
    frozenset({"фриз борта", "фриз борта"}),
    frozenset({"остекление", "остекление"}),
    frozenset({"ограждение", "ограждение"}),
    frozenset({"труба", "труба"}),
    frozenset({"остекление рубки", "остекление рубки"}),
    frozenset({"поручень", "поручень"}),
    frozenset({"ступень", "ступень"}),
    frozenset({"ступень", "площадка трапа"}),
    frozenset({"ступень", "поручень трапа"}),
    frozenset({"ступень", "косоур"}),
    frozenset({"карниз", "карниз"}),
}


def interference(step_path):
    """Пересечения из cadgen, разделённые на ожидаемые и настоящие."""
    import json
    import subprocess

    done = subprocess.run(
        [str(ROOT / ".venv" / "bin" / "cadgen"), "step", "inspect", "interfere",
         str(step_path), "--format", "json", "--tolerance", "20000",
         "--max-pairs", "60000"],
        capture_output=True, text=True, cwd=ROOT)
    # Ненулевой код возврата здесь штатный: cadgen сигналит им сам факт
    # найденных пересечений, а разбирать их — как раз наша работа.
    try:
        data = json.loads(done.stdout)
    except json.JSONDecodeError:
        return None

    def name_of(side):
        # cadgen отдаёт имена в JSON побайтно, поэтому кириллица приезжает
        # как latin-1 и её надо перекодировать обратно
        raw = (side or {}).get("name", "")
        try:
            return raw.encode("latin1").decode("utf-8")
        except (UnicodeEncodeError, UnicodeDecodeError):
            return raw

    clashes = data.get("clashes") or []
    expected, real = 0, []
    for row in clashes:
        first, second = name_of(row.get("a")), name_of(row.get("b"))
        if frozenset({first, second}) in EXPECTED_OVERLAPS:
            expected += 1
        else:
            real.append((first, second, row.get("volume", 0)))
    return {"expected": expected, "real": real, "total": len(clashes)}


def main():
    result = audit()
    print(f"деталей в модели: {result['parts']}")

    print(f"\nЗА ОБВОД КОРПУСА: {len(result['overhang'])}")
    seen = {}
    for label, excess, x in result["overhang"]:
        if label not in seen or excess > seen[label][0]:
            seen[label] = (excess, x)
    for label, (excess, x) in sorted(seen.items(), key=lambda kv: -kv[1][0]):
        count = sum(1 for row in result["overhang"] if row[0] == label)
        print(f"  {label:26} на {excess / 1000:5.2f} м  "
              f"в сечении x={x / 1000:.0f} м  ×{count}")

    print(f"\nБЕЗ ОПОРЫ СНИЗУ: {len(result['floating'])}")
    grouped = {}
    for label, z, support in result["floating"]:
        grouped.setdefault(label, []).append(z - support)
    for label, gaps in sorted(grouped.items(), key=lambda kv: -max(kv[1])):
        print(f"  {label:26} зазор до {max(gaps) / 1000:5.2f} м  ×{len(gaps)}")

    print(f"\nКАЮТЫ ЗА ОБВОДОМ НАДСТРОЙКИ: {len(result['cabins'])}")
    by_deck = {}
    for deck_name, number, excess, x in result["cabins"]:
        by_deck.setdefault(deck_name, []).append((excess, number, x))
    for deck_name, rows in by_deck.items():
        worst = max(rows)
        print(f"  {deck_name:12} ×{len(rows):3}  худшая каюта {worst[1]} "
              f"на {worst[0] / 1000:.2f} м  x={worst[2] / 1000:.0f} м")

    print(f"\nПАЛУБНЫЕ НАСТИЛЫ: {len(result['slabs'])}")
    for name in result["slabs"]:
        print(f"  {name}")

    deck = ROOT / "STEP" / "deck_middle.step"
    if deck.exists():
        found = interference(deck)
        if found:
            print(f"\nПЕРЕСЕЧЕНИЯ на образцовой палубе: {found['total']}")
            print(f"  конструктивных перекрытий: {found['expected']}")
            print(f"  требуют разбора: {len(found['real'])}")
            seen = {}
            for first, second, volume in found["real"]:
                key = (first, second)
                seen[key] = max(seen.get(key, 0), volume)
            for (first, second), volume in sorted(seen.items(),
                                                  key=lambda kv: -kv[1])[:6]:
                print(f"    {first} × {second}: {volume / 1e6:.1f} млн мм³")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
