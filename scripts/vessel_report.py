#!/usr/bin/env python
"""Виды судна и таблица ТТХ — то, что уходит в пояснительную записку.

Характеристики считаются ПО ГЕОМЕТРИИ модели, а не переписываются из
таблицы размерений: водоизмещение — объём отсечённой подводной части,
ширина — фактический габарит с учётом того, что сглаженный лофт выпучивает
борт между шпангоутами. Расхождение модели и записки так невозможно.

    python scripts/vessel_report.py [--no-render]
"""

from __future__ import annotations

import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
CADGEN = ROOT / ".venv" / "bin" / "cadgen"
OUT = ROOT / "renders"
sys.path.insert(0, str(ROOT / "src"))

VIEWS = [
    ("vessel", "профиль", "0:0"),
    ("vessel", "план", "top"),
    ("vessel", "нос", "285:12"),
    ("vessel", "корма", "105:12"),
    ("vessel", "перспектива", "215:16"),
    ("vessel_exploded", "взрыв-схема", "215:16"),
]


def render():
    OUT.mkdir(exist_ok=True)
    for model, name, camera in VIEWS:
        step = ROOT / "STEP" / f"{model}.step"
        if not step.exists():
            print(f"  нет {step.name} — сначала: python src/{model}.py")
            continue
        path = OUT / f"судно_{name}.png"
        done = subprocess.run(
            [str(CADGEN), "step", "snapshot", str(step), str(path),
             "--camera", camera, "--width", "2200",
             "--height", "1400" if name in ("взрыв-схема", "план") else "1000"],
            capture_output=True, text=True, cwd=ROOT)
        print(f"  {name:12} -> {path.relative_to(ROOT)}"
              if done.returncode == 0 else f"  {name}: {done.stderr.strip()[:120]}")


def specs():
    from lib import hull, ship

    body = hull.hull_solid()
    box = body.bounding_box()
    d = hull.displacement(body)

    mix = {"econom": 10, "standard": 8, "business": 4, "lux": 1}
    cap = ship.capacity(mix)

    print("\nОСНОВНЫЕ ХАРАКТЕРИСТИКИ")
    rows = [
        ("Длина наибольшая", f"{box.size.X / 1000:.1f} м"),
        ("Длина по КВЛ", f"{d['length_wl']:.1f} м"),
        ("Ширина наибольшая", f"{box.size.Y / 1000:.2f} м"),
        ("Высота борта", f"{ship.DEPTH / 1000:.1f} м"),
        ("Осадка", f"{ship.DRAFT / 1000:.1f} м"),
        ("Надводный борт", f"{ship.FREEBOARD / 1000:.1f} м"),
        ("Водоизмещение", f"{d['mass']:.0f} т"),
        ("Коэффициент общей полноты", f"{d['cb']:.3f}"),
        ("Высота с заваленной мачтой", f"{ship.air_draft(0) / 1000:.1f} м"),
        ("Палуб всего", f"{len(ship.DECK_LEVELS)}"),
        ("Палуб с каютами", f"{ship.CABIN_DECKS}"),
        ("Кают", f"{cap['cabins']}"),
        ("Пассажировместимость", f"{cap['passengers']} чел."),
    ]
    for name, value in rows:
        print(f"  {name:32} {value:>12}")

    print("\nПРОВЕРКИ ПО ОГРАНИЧЕНИЯМ ТРАССЫ")
    for name, value, limit, ok in hull.checks(body):
        mark = "проходит" if ok else "НЕ ПРОХОДИТ"
        print(f"  {'✓' if ok else '✗'} {name:34} "
              f"{value / 1000:6.2f} / {limit / 1000:5.2f} м   {mark}")

    print("\nРАСКЛАДКА КАЮТ на борт одной палубы")
    for category, count in mix.items():
        print(f"  {category:10} x{count:2}  "
              f"{count * ship.cabin_width(category) / 1000:6.2f} м  "
              f"по {ship.clear_area(category):5.2f} м²")
    print(f"  занято {cap['length_used'] / 1000:.1f} м "
          f"из {cap['length_available'] / 1000:.0f} м доступных — "
          f"{'влезает' if cap['fits'] else 'НЕ ВЛЕЗАЕТ'}")


def main():
    if "--no-render" not in sys.argv:
        print("виды:")
        render()
    specs()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
